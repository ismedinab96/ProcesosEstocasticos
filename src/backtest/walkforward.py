"""Backtesting walk-forward de una serie contra baselines Naive y Seasonal Naive."""

from __future__ import annotations

import warnings

import numpy as np
from statsmodels.tsa.statespace.sarimax import SARIMAX

from ..models.utilidades import a_primitivo


def _rmse(real: np.ndarray, pred: np.ndarray) -> float:
    validos = np.isfinite(real) & np.isfinite(pred)
    if validos.sum() == 0:
        return float("nan")
    return float(np.sqrt(np.mean((real[validos] - pred[validos]) ** 2)))


def _mae(real: np.ndarray, pred: np.ndarray) -> float:
    validos = np.isfinite(real) & np.isfinite(pred)
    if validos.sum() == 0:
        return float("nan")
    return float(np.mean(np.abs(real[validos] - pred[validos])))


def _smape(real: np.ndarray, pred: np.ndarray) -> float:
    validos = np.isfinite(real) & np.isfinite(pred) & ((np.abs(real) + np.abs(pred)) > 0)
    if validos.sum() == 0:
        return float("nan")
    return float(
        100
        * np.mean(
            2
            * np.abs(real[validos] - pred[validos])
            / (np.abs(real[validos]) + np.abs(pred[validos]))
        )
    )


def evaluar_walkforward(
    valores: list[float],
    order: tuple[int, int, int],
    seasonal_order: tuple[int, int, int, int],
    ventana: int = 12,
    maxiter: int = 50,
) -> dict:
    y = np.asarray(valores, dtype=float)
    n = len(y)
    ventana = min(ventana, max(1, n - 24))
    if n < 24 or ventana <= 0:
        return a_primitivo(
            {
                "rmse_modelo": None,
                "mae_modelo": None,
                "smape_modelo": None,
                "rmse_naive": None,
                "rmse_snaive": None,
                "supera_baseline": None,
                "observaciones_eval": 0,
            }
        )

    predicciones: list[float] = []
    reales: list[float] = []
    for i in range(n - ventana, n):
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                modelo = SARIMAX(
                    y[:i],
                    order=order,
                    seasonal_order=seasonal_order,
                    enforce_stationarity=False,
                    enforce_invertibility=False,
                ).fit(disp=False, maxiter=maxiter)
                pronostico = float(modelo.forecast(steps=1)[0])
        except Exception:
            pronostico = float("nan")
        predicciones.append(pronostico)
        reales.append(y[i])

    real_arr = np.asarray(reales)
    pred_arr = np.asarray(predicciones)
    naive = y[n - ventana - 1 : n - 1]
    snaive = y[n - ventana - 12 : n - 12] if n - ventana - 12 >= 0 else np.full(ventana, np.nan)

    rmse_modelo = _rmse(real_arr, pred_arr)
    rmse_naive = _rmse(real_arr, naive)
    rmse_snaive = _rmse(real_arr, snaive)
    return a_primitivo(
        {
            "rmse_modelo": rmse_modelo,
            "mae_modelo": _mae(real_arr, pred_arr),
            "smape_modelo": _smape(real_arr, pred_arr),
            "rmse_naive": rmse_naive,
            "rmse_snaive": rmse_snaive,
            "supera_baseline": bool(
                np.isfinite(rmse_modelo) and np.isfinite(rmse_naive) and rmse_modelo < rmse_naive
            ),
            "observaciones_eval": int(np.isfinite(pred_arr).sum()),
        }
    )
