"""Selección y ajuste SARIMA por grilla acotada, pronóstico y diagnósticos."""

from __future__ import annotations

import warnings
from itertools import product

import numpy as np
import pandas as pd
from statsmodels.stats.diagnostic import acorr_ljungbox
from statsmodels.tsa.statespace.sarimax import SARIMAX

from ..backtest.walkforward import evaluar_walkforward
from .estacionariedad import analizar_estacionariedad
from .regresion import regresion_ols, verificar_normalidad
from .utilidades import a_primitivo, limpiar_serie


def _combinaciones(config: dict, d: int, D: int) -> list[tuple]:
    grilla = config["sarima"]["grilla"]
    s = int(config["sarima"].get("s", 12))
    max_pq = int(config["sarima"].get("max_pq_total", 3))
    max_PQ = int(config["sarima"].get("max_PQ_total", 1))
    combos = []
    for p, q in product(grilla["p"], grilla["q"]):
        if p + q > max_pq:
            continue
        for P, Q in product(grilla["P"], grilla["Q"]):
            if P + Q > max_PQ:
                continue
            combos.append(((p, d, q), (P, D, Q, s)))
    return combos


def _ajustar(y: np.ndarray, order: tuple, seasonal_order: tuple, config: dict):
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        modelo = SARIMAX(
            y,
            order=order,
            seasonal_order=seasonal_order,
            enforce_stationarity=bool(config["sarima"].get("enforce_stationarity", False)),
            enforce_invertibility=bool(config["sarima"].get("enforce_invertibility", False)),
        )
        return modelo.fit(disp=False, maxiter=int(config["sarima"].get("maxiter", 50)))


def seleccionar_modelo(y: np.ndarray, config: dict, d: int, D: int) -> dict:
    """Ajusta la grilla acotada y devuelve el mejor modelo y el top 3 por AIC."""
    candidatos = []
    for order, seasonal_order in _combinaciones(config, d, D):
        try:
            resultado = _ajustar(y, order, seasonal_order, config)
        except Exception:
            continue
        aic = float(resultado.aic)
        bic = float(resultado.bic)
        if not np.isfinite(aic):
            continue
        candidatos.append(
            {
                "orden": list(order),
                "orden_estacional": list(seasonal_order),
                "aic": aic,
                "bic": bic,
                "resultado": resultado,
            }
        )
    if not candidatos:
        return {"mejor": None, "top3": [], "modelos_evaluados": 0}
    candidatos.sort(key=lambda c: c["aic"])
    top3 = [
        {
            "orden": c["orden"],
            "orden_estacional": c["orden_estacional"],
            "aic": c["aic"],
            "bic": c["bic"],
        }
        for c in candidatos[:3]
    ]
    return {
        "mejor": candidatos[0],
        "top3": top3,
        "modelos_evaluados": len(candidatos),
    }


def _momentos(y: np.ndarray) -> dict:
    if len(y) == 0:
        return {"media": None, "varianza": None, "autocovarianza": []}
    media = float(np.mean(y))
    varianza = float(np.var(y, ddof=1)) if len(y) > 1 else 0.0
    limite = min(24, len(y) // 3)
    autocovarianza = []
    for rezago in range(1, limite + 1):
        par = np.cov(y[:-rezago], y[rezago:], ddof=1)
        autocovarianza.append(float(par[0, 1]))
    return {"media": media, "varianza": varianza, "autocovarianza": autocovarianza}


def _fechas_futuras(ultima: str, pasos: int) -> list[str]:
    inicio = pd.Period(ultima, freq="M") + 1
    return [str(p) for p in pd.period_range(inicio, periods=pasos, freq="M")]


def ajustar_serie(
    fechas: list[str],
    valores: list[float],
    config: dict,
    direccion_riesgo: str = "ascendente",
) -> dict:
    s = int(config["sarima"].get("s", 12))
    minimo = int(config["general"].get("meses_minimos_serie", 60))
    limpio = limpiar_serie(fechas, valores, meses_minimos=minimo)
    y = np.asarray(limpio["valores"], dtype=float)
    fechas_limpias = limpio["fechas"]
    if len(y) < 24 or np.std(y) == 0:
        return a_primitivo(
            {
                "fechas": fechas_limpias,
                "observado": [float(v) for v in y],
                "momentos": _momentos(y),
                "apta_modelado": False,
                "motivo": (
                    limpio.get("estado", "sin_datos") if len(y) >= 24 else "menos_de_24_meses"
                ),
                "estacionariedad": analizar_estacionariedad(y, s),
                "regresion_ols": regresion_ols(fechas_limpias, y),
                "sarima": None,
                "backtest": None,
                "prediccion_un_paso": None,
            }
        )

    estacionariedad = analizar_estacionariedad(y, s)
    d = int(estacionariedad.get("d_recomendado") or 0)
    D = int(estacionariedad.get("D_estacional") or 0)
    seleccion = seleccionar_modelo(y, config, d, D)
    if seleccion["mejor"] is None:
        return a_primitivo(
            {
                "fechas": fechas_limpias,
                "observado": [float(v) for v in y],
                "momentos": _momentos(y),
                "apta_modelado": False,
                "motivo": "sin_modelo_convergente",
                "estacionariedad": estacionariedad,
                "regresion_ols": regresion_ols(fechas_limpias, y),
                "sarima": None,
                "backtest": None,
                "prediccion_un_paso": None,
            }
        )

    mejor = seleccion["mejor"]
    resultado = mejor["resultado"]
    residuos = np.asarray(resultado.resid, dtype=float)
    desviacion = float(np.nanstd(residuos))
    estandarizados = residuos / desviacion if desviacion > 0 else np.zeros_like(residuos)
    ajuste = np.asarray(resultado.fittedvalues, dtype=float)

    media_un_paso = ajuste
    ic_inf = media_un_paso - 1.959964 * desviacion
    ic_sup = media_un_paso + 1.959964 * desviacion

    pasos = int(config["general"].get("meses_pronostico", 12))
    pronostico = resultado.get_forecast(steps=pasos)
    media = np.asarray(pronostico.predicted_mean, dtype=float)
    ic80 = np.asarray(pronostico.conf_int(alpha=0.20), dtype=float)
    ic95 = np.asarray(pronostico.conf_int(alpha=0.05), dtype=float)

    lags_lb = min(24, max(8, len(residuos) // 2))
    try:
        ljung = float(acorr_ljungbox(residuos, lags=[lags_lb], return_df=True)["lb_pvalue"].iloc[0])
    except (ValueError, np.linalg.LinAlgError):
        ljung = float("nan")
    normalidad = verificar_normalidad(residuos)

    backtest = evaluar_walkforward(
        y,
        tuple(mejor["orden"]),
        tuple(mejor["orden_estacional"]),
        ventana=int(config["general"].get("meses_ventana_backtest", 12)),
        maxiter=int(config["sarima"].get("maxiter", 50)),
    )

    return a_primitivo(
        {
            "fechas": fechas_limpias,
            "observado": [float(v) for v in y],
            "momentos": _momentos(y),
            "apta_modelado": len(y) >= minimo,
            "motivo": limpio.get("estado", "ok"),
            "ajuste_in_sample": [float(v) for v in ajuste],
            "residuos_estandarizados": [float(v) for v in estandarizados],
            "pronostico": {
                "fechas": _fechas_futuras(fechas_limpias[-1], pasos),
                "media": [float(v) for v in media],
                "ic80_inf": [float(v) for v in ic80[:, 0]],
                "ic80_sup": [float(v) for v in ic80[:, 1]],
                "ic95_inf": [float(v) for v in ic95[:, 0]],
                "ic95_sup": [float(v) for v in ic95[:, 1]],
            },
            "estacionariedad": estacionariedad,
            "regresion_ols": regresion_ols(fechas_limpias, y),
            "sarima": {
                "orden": mejor["orden"],
                "orden_estacional": mejor["orden_estacional"],
                "aic": mejor["aic"],
                "bic": mejor["bic"],
                "top3_modelos": seleccion["top3"],
                "modelos_evaluados": seleccion["modelos_evaluados"],
                "ljung_box_pval": ljung,
                "jarque_bera_pval": normalidad["jarque_bera_pval"],
                "shapiro_pval": normalidad["shapiro_pval"],
                "asimetria": normalidad["asimetria"],
                "curtosis": normalidad["curtosis"],
                "qq_teorico": normalidad["qq_teorico"],
                "qq_muestral": normalidad["qq_muestral"],
            },
            "backtest": backtest,
            "prediccion_un_paso": {
                "fechas": fechas_limpias,
                "media": [float(v) for v in media_un_paso],
                "ic95_inf": [float(v) for v in ic_inf],
                "ic95_sup": [float(v) for v in ic_sup],
            },
            "direccion_riesgo": direccion_riesgo,
        }
    )
