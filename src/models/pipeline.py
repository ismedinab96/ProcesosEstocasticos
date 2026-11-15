"""Orquestador del motor estocástico y exportación del contrato del dashboard."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd
from joblib import Parallel, delayed

from ..export.exportador import exportar
from ..scraping.configuracion import cargar_config, ruta_raiz
from .alertas import generar_alertas
from .markov import analizar_markov
from .sarima import ajustar_serie

SEMAFOROS = ["verde", "amarillo", "naranja", "rojo"]


def _estacionariedad_vacia() -> dict:
    return {
        "adf_stat": None,
        "adf_pval": None,
        "kpss_stat": None,
        "kpss_pval": None,
        "d_recomendado": None,
        "D_estacional": None,
        "veredicto": "Inconclusa",
        "acf_orig": [],
        "pacf_orig": [],
        "acf_diff": [],
        "pacf_diff": [],
    }


def _regresion_vacia() -> dict:
    return {
        "r2_adj": None,
        "dw_stat": None,
        "ljung_box_pval": None,
        "arch_lm_pval": None,
        "tendencia": [],
        "estacionalidad": [],
    }


def _procesar_serie(
    banco_id: str,
    indicador_id: str,
    fechas: list[str],
    valores: list[float | None],
    config: dict,
    direccion: str,
) -> tuple[str, str, dict]:
    try:
        datos = ajustar_serie(fechas, valores, config, direccion)
        return banco_id, indicador_id, datos
    except Exception as exc:  # noqa: BLE001 - se reporta por serie sin abortar el lote
        return (
            banco_id,
            indicador_id,
            {
                "fechas": fechas,
                "observado": valores,
                "apta_modelado": False,
                "motivo": f"error:{type(exc).__name__}",
                "estacionariedad": _estacionariedad_vacia(),
                "regresion_ols": _regresion_vacia(),
                "sarima": None,
                "backtest": None,
                "prediccion_un_paso": None,
            },
        )


def _tareas(largo: pd.DataFrame, config: dict) -> list[tuple]:
    tareas = []
    for banco in config["bancos"]:
        for indicador in config["indicadores"]:
            sub = largo[
                (largo["banco_id"] == banco["id"]) & (largo["indicador_id"] == indicador["id"])
            ].sort_values("fecha")
            if sub.empty:
                continue
            fechas = sub["fecha"].astype(str).tolist()
            valores = [None if pd.isna(v) else float(v) for v in sub["valor"].to_numpy()]
            tareas.append(
                (
                    banco["id"],
                    indicador["id"],
                    fechas,
                    valores,
                    config,
                    indicador.get("direccion_riesgo", "ascendente"),
                )
            )
    return tareas


def _resumen_bancos(
    config: dict,
    series: dict[str, dict[str, dict]],
    alertas: list[dict],
    ultima_fecha: str,
) -> list[dict]:
    limite = str(pd.Period(ultima_fecha, freq="M") - 2)
    recientes = [a for a in alertas if a["fecha"] >= limite]
    bancos = []
    for banco in config["bancos"]:
        datos_banco = series.get(banco["id"], {})
        mora = datos_banco.get("mora") or {}
        observado = [float(v) for v in mora.get("observado") or []]
        cobertura = max((len(d.get("fechas") or []) for d in datos_banco.values()), default=0)
        score = 0.0
        for datos in datos_banco.values():
            z = [
                abs(float(v)) for v in (datos.get("residuos_estandarizados") or []) if v is not None
            ]
            if z:
                score = max(score, max(z[-6:]))
        severidades = {a["severidad"] for a in recientes if a["banco_id"] == banco["id"]}
        if "critica" in severidades:
            semaforo = "rojo"
        elif "alerta" in severidades:
            semaforo = "naranja"
        elif "vigilancia" in severidades:
            semaforo = "amarillo"
        else:
            semaforo = "verde"
        bancos.append(
            {
                "id": banco["id"],
                "nombre": banco["nombre"],
                "tipo": banco["tipo"],
                "semaforo": semaforo,
                "score_anomalia": round(float(score), 4),
                "cobertura_meses": int(cobertura),
                "sparkline_mora": observado[-24:],
            }
        )
    return bancos


def ejecutar_modelos(
    entrada: str | Path | None = None,
    n_jobs: int | None = None,
    salida_json: str | Path | None = None,
    salida_js: str | Path | None = None,
    verbose: int = 0,
) -> dict:
    config = cargar_config()
    raiz = ruta_raiz()
    ruta_indicadores = (
        Path(entrada) if entrada else raiz / "data" / "processed" / "panel_indicadores.parquet"
    )
    if not ruta_indicadores.is_absolute():
        ruta_indicadores = raiz / ruta_indicadores
    if not ruta_indicadores.exists():
        raise FileNotFoundError(
            f"No se encontró {ruta_indicadores}. Ejecuta primero `python -m src.etl.pipeline`."
        )
    largo = pd.read_parquet(ruta_indicadores)

    tareas = _tareas(largo, config)
    trabajos = n_jobs if n_jobs is not None else int(config["sarima"].get("n_jobs", -1))
    resultados = Parallel(n_jobs=trabajos, verbose=verbose, batch_size=1)(
        delayed(_procesar_serie)(*tarea) for tarea in tareas
    )

    series: dict[str, dict[str, dict]] = {}
    for banco_id, indicador_id, datos in resultados:
        series.setdefault(banco_id, {})[indicador_id] = datos

    mora_por_banco: dict[str, list[float]] = {}
    for banco in config["bancos"]:
        datos = series.get(banco["id"], {}).get("mora")
        if datos:
            mora_por_banco[banco["id"]] = [float(v) for v in datos["observado"]]
    markov = analizar_markov(mora_por_banco, config)

    alertas = generar_alertas(series, markov, config)

    etl_meta_ruta = raiz / "data" / "processed" / "etl_meta.json"
    etl_meta = {}
    if etl_meta_ruta.exists():
        etl_meta = json.loads(etl_meta_ruta.read_text(encoding="utf-8"))

    fechas_todas = largo["fecha"].astype(str)
    ultima_fecha = str(fechas_todas.max())
    bancos = _resumen_bancos(config, series, alertas, ultima_fecha)
    indicadores_meta = [
        {
            "id": ind["id"],
            "nombre": ind["nombre"],
            "formula_latex": ind["formula_latex"],
            "unidad": ind["unidad"],
            "direccion_riesgo": ind["direccion_riesgo"],
        }
        for ind in config["indicadores"]
    ]

    contrato = {
        "meta": {
            "generado_utc": datetime.now(UTC).isoformat(timespec="seconds"),
            "fuente": "ASFI Bolivia",
            "modo_demo": bool(etl_meta.get("modo_demo", False)),
            "rango_fechas": [str(fechas_todas.min()), ultima_fecha],
            "total_observaciones": int(
                etl_meta.get(
                    "observaciones", largo["fecha"].nunique() * largo["banco_id"].nunique()
                )
            ),
        },
        "bancos": bancos,
        "indicadores_meta": indicadores_meta,
        "series": series,
        "markov": markov,
        "alertas": alertas,
    }

    rutas = exportar(
        contrato,
        salida_json or config["export"]["salida_json"],
        salida_js or config["export"]["salida_js"],
        validar=bool(config["export"].get("validar_esquema", True)),
    )

    modeladas = sum(1 for fila in series.values() for d in fila.values() if d.get("sarima"))
    backtests = [
        d["backtest"] for fila in series.values() for d in fila.values() if d.get("backtest")
    ]
    superan = sum(1 for b in backtests if b.get("supera_baseline"))
    conteo_sev = {
        sev: sum(1 for a in alertas if a["severidad"] == sev)
        for sev in ("critica", "alerta", "vigilancia")
    }
    resumen = {
        "series_totales": len(tareas),
        "series_modeladas": modeladas,
        "backtests": len(backtests),
        "supera_naive": superan,
        "alertas": len(alertas),
        "severidades": conteo_sev,
        "semaforos": {s: sum(1 for b in bancos if b["semaforo"] == s) for s in SEMAFOROS},
        "json": str(rutas["json"]),
        "js": str(rutas["js"]),
    }
    (raiz / "data" / "processed" / "modelos_meta.json").write_text(
        json.dumps(resumen, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return resumen


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Motor estocástico ASFI")
    parser.add_argument("--entrada", default=None)
    parser.add_argument("--n-jobs", type=int, default=None)
    parser.add_argument("--salida-json", default=None)
    parser.add_argument("--salida-js", default=None)
    parser.add_argument("--verbose", type=int, default=5)
    args = parser.parse_args(argv)

    try:
        resumen = ejecutar_modelos(
            entrada=args.entrada,
            n_jobs=args.n_jobs,
            salida_json=args.salida_json,
            salida_js=args.salida_js,
            verbose=args.verbose,
        )
    except (FileNotFoundError, ValueError) as exc:
        print(f"ERROR MODELOS: {exc}", file=sys.stderr)
        return 2

    if resumen["semaforos"]["rojo"] or resumen["alertas"]:
        print("Recordatorio: las alertas miden anomalías estadísticas, no quiebras bancarias.")
    print(
        f"Series modeladas: {resumen['series_modeladas']}/{resumen['series_totales']}; "
        f"backtests que superan Naive: {resumen['supera_naive']}/{resumen['backtests']}"
    )
    print(
        "Alertas: "
        f"{resumen['alertas']} (crítica {resumen['severidades']['critica']}, "
        f"alerta {resumen['severidades']['alerta']}, "
        f"vigilancia {resumen['severidades']['vigilancia']})"
    )
    print("Semáforos: " + ", ".join(f"{s}={n}" for s, n in resumen["semaforos"].items()))
    print(f"Contrato: {resumen['json']}")
    print(f"JS: {resumen['js']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
