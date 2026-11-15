"""Pipeline ETL: parseo BMU → validación contable → indicadores → reporte."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

from ..indicators.calculadora import calcular_indicadores
from ..scraping.configuracion import cargar_config, ruta_raiz
from .parser_bmu import parsear_bmu
from .reporte_calidad import generar_reporte_calidad
from .validacion import (
    duplicados,
    resumen_cobertura,
    resumen_identidad,
    resumen_indicadores,
    validar_identidad,
    violaciones_positivas,
)

PATRONES_REALES = [
    "data/raw/**/eeff_*_BMU_EstadosFinancieros.zip",
    "data/raw/**/eeff_*_BMU_EstadosFinancieros.xls",
]
ARCHIVO_DEMO = "data/raw/demo/panel_sintetico_demo.csv"


def _buscar_reales(raiz: Path) -> list[Path]:
    encontrados: list[Path] = []
    for patron in PATRONES_REALES:
        encontrados.extend(sorted(raiz.glob(patron)))
    return sorted({p for p in encontrados if "Evolutivo" not in p.name})


def _cargar_demo(raiz: Path) -> tuple[pd.DataFrame, bool]:
    ruta = raiz / ARCHIVO_DEMO
    if not ruta.exists():
        raise FileNotFoundError(
            "No hay archivos reales BMU ni panel demo. Ejecuta "
            "`python -m src.etl.synth --demo` o publica archivos en data/raw/."
        )
    panel = pd.read_csv(ruta)
    meta_ruta = ruta.with_name("demo_meta.json")
    modo_demo = True
    if meta_ruta.exists():
        meta = json.loads(meta_ruta.read_text(encoding="utf-8"))
        modo_demo = bool(meta.get("modo_demo", True))
    return panel, modo_demo


def ejecutar_etl(
    entrada: list[str] | None = None,
    demo: bool = False,
    meses_minimos: int | None = None,
    tolerancia_identidad: float = 1.0,
    salida: str | Path | None = None,
    reporte: str | Path | None = None,
) -> dict:
    config = cargar_config()
    raiz = ruta_raiz()
    meses_minimos = meses_minimos or int(config["general"]["meses_minimos_serie"])

    archivos_info: list[dict] = []
    paneles: list[pd.DataFrame] = []
    modo_demo = False

    rutas = [Path(p) for p in entrada] if entrada else _buscar_reales(raiz)
    interim = raiz / "data" / "interim"
    if rutas and not demo:
        interim.mkdir(parents=True, exist_ok=True)
        for ruta in rutas:
            resultado = parsear_bmu(ruta, config, nombre_archivo=ruta.name)
            paneles.append(resultado.panel)
            resultado.panel.to_parquet(
                interim / f"{resultado.fecha}_{ruta.stem}.parquet", index=False
            )
            archivos_info.append(
                {
                    "archivo": str(ruta.relative_to(raiz)),
                    "fecha": resultado.fecha,
                    "unidad": resultado.unidad,
                    "codigos": ", ".join(resultado.codigos),
                    "diferencia_identidad_max": resultado.diferencia_identidad_max,
                }
            )
    else:
        panel_demo, modo_demo = _cargar_demo(raiz)
        paneles.append(panel_demo)
        archivos_info.append(
            {
                "archivo": ARCHIVO_DEMO,
                "fecha": f"{panel_demo['fecha'].min()} → {panel_demo['fecha'].max()}",
                "unidad": config["general"]["unidad_base"],
                "codigos": "panel sintético (12 bancos)",
                "diferencia_identidad_max": float(
                    (
                        panel_demo["activo_total"]
                        - (panel_demo["pasivo_total"] + panel_demo["patrimonio_total"])
                    )
                    .abs()
                    .max()
                ),
            }
        )

    panel = pd.concat(paneles, ignore_index=True)
    panel = (
        panel.drop_duplicates(subset=["fecha", "banco_id"], keep="last")
        .sort_values(["banco_id", "fecha"])
        .reset_index(drop=True)
    )

    procesado = raiz / "data" / "processed"
    procesado.mkdir(parents=True, exist_ok=True)
    salida = Path(salida) if salida else procesado / "panel_contable.parquet"
    salida.parent.mkdir(parents=True, exist_ok=True)
    panel.to_parquet(salida, index=False)

    tabla_identidad = validar_identidad(panel, tolerancia=tolerancia_identidad)
    resumen_id = resumen_identidad(tabla_identidad)
    violaciones = violaciones_positivas(panel)
    duplicados_df = duplicados(panel)
    cobertura = resumen_cobertura(panel, meses_minimos=meses_minimos)

    panel_largo = calcular_indicadores(panel)
    salida_ind = procesado / "panel_indicadores.parquet"
    panel_largo.to_parquet(salida_ind, index=False)
    resumen_ind = resumen_indicadores(panel_largo)

    reporte = Path(reporte) if reporte else raiz / "docs" / "calidad_datos.md"
    generar_reporte_calidad(
        destino=reporte,
        panel_contable=panel,
        panel_largo=panel_largo,
        tabla_identidad=tabla_identidad,
        resumen_id=resumen_id,
        violaciones=violaciones,
        duplicados_df=duplicados_df,
        cobertura=cobertura,
        resumen_ind=resumen_ind,
        archivos=archivos_info,
        meses_minimos=meses_minimos,
        modo_demo=modo_demo,
        tolerancia_identidad=tolerancia_identidad,
    )

    meta = {
        "generado_utc": datetime.now(UTC).isoformat(timespec="seconds"),
        "modo_demo": modo_demo,
        "archivos": len(archivos_info),
        "observaciones": int(len(panel)),
        "bancos": int(panel["banco_id"].nunique()),
        "rango": [panel["fecha"].min(), panel["fecha"].max()],
        "identidad": resumen_id,
        "cobertura_apta": cobertura[cobertura["apta_para_modelado"]]["banco_id"].tolist(),
        "cobertura_insuficiente": cobertura[~cobertura["apta_para_modelado"]]["banco_id"].tolist(),
        "panel_contable": str(salida),
        "panel_indicadores": str(salida_ind),
        "reporte": str(reporte),
    }
    (procesado / "etl_meta.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return meta


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="ETL de EEFF BMU de ASFI")
    parser.add_argument("--entrada", nargs="*", default=None, help="Archivos o globs de entrada")
    parser.add_argument("--demo", action="store_true", help="Fuerza el panel sintético")
    parser.add_argument("--meses-minimos", type=int, default=None)
    parser.add_argument("--tolerancia-identidad", type=float, default=1.0)
    parser.add_argument("--salida", type=str, default=None)
    parser.add_argument("--reporte", type=str, default=None)
    args = parser.parse_args(argv)

    try:
        meta = ejecutar_etl(
            entrada=args.entrada,
            demo=args.demo,
            meses_minimos=args.meses_minimos,
            tolerancia_identidad=args.tolerancia_identidad,
            salida=args.salida,
            reporte=args.reporte,
        )
    except (FileNotFoundError, ValueError) as exc:
        print(f"ERROR ETL: {exc}", file=sys.stderr)
        return 2

    if meta["modo_demo"]:
        print("MODO DEMOSTRACIÓN — DATOS SINTÉTICOS")
    print(
        f"ETL completado: {meta['archivos']} archivos, {meta['observaciones']} observaciones, "
        f"{meta['bancos']} bancos, rango {meta['rango'][0]} -> {meta['rango'][1]}"
    )
    print(
        f"Identidad contable: {meta['identidad']['fallos']} fallos, "
        f"diferencia máxima {meta['identidad']['diferencia_max']:.6f}"
    )
    print(f"Panel contable: {meta['panel_contable']}")
    print(f"Panel indicadores: {meta['panel_indicadores']}")
    print(f"Reporte: {meta['reporte']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
