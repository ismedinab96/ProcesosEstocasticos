"""Generador de datos sintéticos realistas para desarrollo sin red.

Los datos solo se generan con el flag explícito ``--demo``. El dashboard deberá
mostrar de forma fija el banner: "MODO DEMOSTRACIÓN — DATOS SINTÉTICOS".

La calibración imita magnitudes y dinámica de la banca múltiple boliviana:
crecimiento mensual moderado, estacionalidad de diciembre, mora con reversión
a la media y choques simulados en bancos específicos.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pandas as pd

from ..scraping.configuracion import cargar_config, ruta_raiz

COLUMNAS = [
    "fecha",
    "banco_id",
    "activo_total",
    "pasivo_total",
    "patrimonio_total",
    "cartera_bruta",
    "cartera_mora",
    "prevision_incobrables",
    "disponibilidades",
    "inversiones_temporarias",
    "obligaciones_corto_plazo",
    "utilidad_neta",
    "depositos",
    "es_demo",
]

# Choques simulados: banco -> (indice_inicio, indice_fin, tipo, magnitud)
CHOQUES_POR_DEFECTO: dict[str, tuple[int, int, str, float]] = {
    "bga": (46, 56, "mora", 0.014),
    "bsol": (58, 68, "liquidez", 0.045),
    "bpro": (30, 40, "mora", 0.008),
}


def _perfil_banco(indice: int) -> dict[str, float]:
    """Parámetros estables por banco (tamaño, mora base, apalancamiento)."""
    perfiles = [
        {"activo": 28.0, "mora": 0.018, "apalancamiento": 0.905, "cartera": 0.68},
        {"activo": 22.0, "mora": 0.016, "apalancamiento": 0.900, "cartera": 0.64},
        {"activo": 20.0, "mora": 0.015, "apalancamiento": 0.912, "cartera": 0.61},
        {"activo": 17.0, "mora": 0.014, "apalancamiento": 0.908, "cartera": 0.60},
        {"activo": 12.0, "mora": 0.021, "apalancamiento": 0.890, "cartera": 0.66},
        {"activo": 10.0, "mora": 0.027, "apalancamiento": 0.880, "cartera": 0.72},
        {"activo": 9.0, "mora": 0.024, "apalancamiento": 0.885, "cartera": 0.70},
        {"activo": 7.0, "mora": 0.019, "apalancamiento": 0.895, "cartera": 0.63},
        {"activo": 6.0, "mora": 0.031, "apalancamiento": 0.875, "cartera": 0.74},
        {"activo": 5.0, "mora": 0.026, "apalancamiento": 0.882, "cartera": 0.69},
        {"activo": 4.5, "mora": 0.023, "apalancamiento": 0.887, "cartera": 0.67},
        {"activo": 4.0, "mora": 0.029, "apalancamiento": 0.879, "cartera": 0.71},
    ]
    perfil = dict(perfiles[indice % len(perfiles)])
    # El activo se expresa en millones de bolivianos y se escala a miles.
    perfil["activo"] *= 1_000_000
    return perfil


def _serie_banco(
    banco_id: str,
    indice: int,
    periodo: pd.PeriodIndex,
    semilla: int,
    choques: dict[str, tuple[int, int, str, float]],
) -> pd.DataFrame:
    rng = np.random.default_rng(semilla + 101 * indice)
    n = len(periodo)
    perfil = _perfil_banco(indice)
    meses = periodo.month.to_numpy()

    crecimiento = rng.normal(0.0080, 0.0016, n)
    crecimiento[0] = 0.0
    estacional_activo = 1.0 + 0.010 * (meses == 12) - 0.004 * (meses == 1)
    activo = perfil["activo"] * np.exp(np.cumsum(crecimiento)) * estacional_activo

    cartera_share = np.clip(
        perfil["cartera"] + 0.02 * np.sin(np.arange(n) / 9) + rng.normal(0, 0.006, n),
        0.45,
        0.80,
    )
    cartera_bruta = activo * cartera_share * (1.0 + 0.012 * (meses == 12))

    # Mora con reversión a la media, estacionalidad y choques.
    phi = 0.82
    base_mora = perfil["mora"]
    sigma = 0.0011
    serie_mora = np.empty(n)
    anterior = base_mora + rng.normal(0, 0.0015)
    shock_info = choques.get(banco_id)
    for i in range(n):
        choque = 0.0
        if shock_info and shock_info[2] == "mora" and shock_info[0] <= i <= shock_info[1]:
            progreso = (i - shock_info[0] + 1) / (shock_info[1] - shock_info[0] + 1)
            choque = shock_info[3] * progreso
        estacional = 0.0005 * (meses[i] == 12) + 0.0002 * (meses[i] in (1, 2))
        valor = base_mora * (1 - phi) + phi * anterior + rng.normal(0, sigma) + choque + estacional
        serie_mora[i] = valor
        anterior = valor
    serie_mora = np.clip(serie_mora, 0.004, 0.12)
    cartera_mora = cartera_bruta * serie_mora

    cobertura = np.clip(
        1.45 + 0.25 * np.sin(np.arange(n) / 7) + rng.normal(0, 0.06, n) + 0.35 * serie_mora,
        0.55,
        3.2,
    )
    prevision = cartera_mora * cobertura

    pasivo = activo * np.clip(perfil["apalancamiento"] + rng.normal(0, 0.006, n), 0.78, 0.95)
    patrimonio = activo - pasivo

    disponibilidad_share = np.clip(
        0.135 + 0.02 * np.sin(np.arange(n) / 6) + rng.normal(0, 0.008, n), 0.06, 0.24
    )
    if shock_info and shock_info[2] == "liquidez":
        inicio, fin, _, magnitud = shock_info
        for i in range(inicio, min(fin + 1, n)):
            disponibilidad_share[i] -= magnitud * (0.5 + 0.5 * (i - inicio) / max(fin - inicio, 1))
        disponibilidad_share = np.clip(disponibilidad_share, 0.02, 0.24)
    disponibilidades = activo * disponibilidad_share
    inversiones = activo * np.clip(
        0.055 + 0.015 * np.sin(np.arange(n) / 11) + rng.normal(0, 0.006, n), 0.01, 0.16
    )

    obligaciones_cp = pasivo * np.clip(0.62 + rng.normal(0, 0.03, n), 0.45, 0.80)
    depositos = pasivo * np.clip(0.79 + 0.02 * (meses == 12) + rng.normal(0, 0.02, n), 0.60, 0.92)

    roa_anual = np.clip(0.016 + rng.normal(0, 0.004, n), 0.002, 0.030)
    flujo_mensual = activo * roa_anual / 12.0 * rng.normal(1.0, 0.10, n)
    utilidad = np.empty(n)
    acumulado = 0.0
    for i in range(n):
        if meses[i] == 1 or i == 0:
            acumulado = flujo_mensual[i]
        else:
            acumulado += flujo_mensual[i]
        utilidad[i] = acumulado

    marco = pd.DataFrame(
        {
            "fecha": periodo.strftime("%Y-%m"),
            "banco_id": banco_id,
            "activo_total": np.round(activo, 2),
            "pasivo_total": np.round(pasivo, 2),
            "patrimonio_total": np.round(patrimonio, 2),
            "cartera_bruta": np.round(cartera_bruta, 2),
            "cartera_mora": np.round(cartera_mora, 2),
            "prevision_incobrables": np.round(prevision, 2),
            "disponibilidades": np.round(disponibilidades, 2),
            "inversiones_temporarias": np.round(inversiones, 2),
            "obligaciones_corto_plazo": np.round(obligaciones_cp, 2),
            "utilidad_neta": np.round(utilidad, 2),
            "depositos": np.round(depositos, 2),
            "es_demo": True,
        }
    )
    return marco


def generar_panel_demo(
    bancos: list[str] | None = None,
    meses: int = 84,
    semilla: int = 42,
    fecha_fin: str = "2025-12",
    choques: dict[str, tuple[int, int, str, float]] | None = None,
) -> pd.DataFrame:
    """Genera un panel mensual sintético con identidad contable exacta."""
    config = cargar_config()
    catalogo = [banco["id"] for banco in config["bancos"]]
    seleccion = bancos or catalogo
    desconocidos = sorted(set(seleccion) - set(catalogo))
    if desconocidos:
        raise ValueError(f"Bancos no reconocidos en config.yaml: {desconocidos}")
    if meses < 12:
        raise ValueError("Se requieren al menos 12 meses para la estacionalidad.")

    periodo = pd.period_range(end=pd.Period(fecha_fin, freq="M"), periods=meses, freq="M")
    mapa_choques = CHOQUES_POR_DEFECTO if choques is None else choques
    marcos = [
        _serie_banco(banco_id, catalogo.index(banco_id), periodo, semilla, mapa_choques)
        for banco_id in seleccion
    ]
    panel = pd.concat(marcos, ignore_index=True)
    panel = panel[COLUMNAS]
    return panel.sort_values(["fecha", "banco_id"]).reset_index(drop=True)


def escribir_demo(
    salida: str | Path | None = None,
    meses: int = 84,
    semilla: int = 42,
    fecha_fin: str = "2025-12",
    forzar: bool = False,
) -> tuple[Path, Path]:
    raiz = ruta_raiz()
    destino = (
        Path(salida) if salida else raiz / "data" / "raw" / "demo" / "panel_sintetico_demo.csv"
    )
    destino.parent.mkdir(parents=True, exist_ok=True)
    if destino.exists() and not forzar:
        raise FileExistsError(f"El archivo {destino} ya existe. Usa --forzar para regenerarlo.")

    panel = generar_panel_demo(meses=meses, semilla=semilla, fecha_fin=fecha_fin)
    panel.to_csv(destino, index=False, encoding="utf-8")

    meta = {
        "modo_demo": True,
        "banner": "MODO DEMOSTRACIÓN — DATOS SINTÉTICOS",
        "generado_utc": datetime.now(UTC).isoformat(timespec="seconds"),
        "semilla": semilla,
        "meses": meses,
        "fecha_fin": fecha_fin,
        "bancos": sorted(panel["banco_id"].unique().tolist()),
        "filas": int(len(panel)),
        "archivo": destino.name,
    }
    meta_ruta = destino.with_name("demo_meta.json")
    meta_ruta.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    return destino, meta_ruta


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Generador de datos sintéticos. Requiere el flag --demo."
    )
    parser.add_argument("--demo", action="store_true", help="Confirma el modo demostración")
    parser.add_argument("--salida", type=str, default=None, help="Ruta del CSV de salida")
    parser.add_argument("--meses", type=int, default=84, help="Meses a generar (mínimo 12)")
    parser.add_argument("--semilla", type=int, default=42, help="Semilla reproducible")
    parser.add_argument("--fecha-fin", type=str, default="2025-12", help="Último mes (YYYY-MM)")
    parser.add_argument("--forzar", action="store_true", help="Sobrescribe si ya existe")
    args = parser.parse_args(argv)

    if not args.demo:
        print(
            "ERROR: este generador crea datos SINTÉTICOS. Debes pasar --demo explícitamente.\n"
            "Uso: python -m src.etl.synth --demo",
            file=sys.stderr,
        )
        return 2

    try:
        ruta, meta_ruta = escribir_demo(
            salida=args.salida,
            meses=args.meses,
            semilla=args.semilla,
            fecha_fin=args.fecha_fin,
            forzar=args.forzar,
        )
    except FileExistsError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print(
        "MODO DEMOSTRACIÓN — DATOS SINTÉTICOS\n"
        f"Panel escrito en: {ruta}\n"
        f"Metadatos: {meta_ruta}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
