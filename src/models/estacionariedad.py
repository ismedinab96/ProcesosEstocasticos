"""Pruebas de estacionariedad, ACF/PACF y recomendación de diferenciación."""

from __future__ import annotations

import warnings

import numpy as np
from statsmodels.tools.sm_exceptions import InterpolationWarning
from statsmodels.tsa.stattools import acf, adfuller, kpss, pacf

from .utilidades import a_primitivo


def _adf(valores: np.ndarray, regression: str = "c") -> tuple[float, float]:
    try:
        estadistico, pval, *_ = adfuller(valores, regression=regression, autolag="AIC")
        return float(estadistico), float(pval)
    except (ValueError, np.linalg.LinAlgError):
        return float("nan"), float("nan")


def _kpss(valores: np.ndarray, regression: str = "c") -> tuple[float, float]:
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", InterpolationWarning)
            estadistico, pval, *_ = kpss(valores, regression=regression, nlags="auto")
        return float(estadistico), float(pval)
    except (ValueError, np.linalg.LinAlgError):
        return float("nan"), float("nan")


def _acf_pacf(valores: np.ndarray, nlags: int = 24) -> tuple[list[float], list[float]]:
    if len(valores) < 8 or np.nanstd(valores) == 0:
        return [], []
    limite = min(nlags, len(valores) // 2)
    try:
        valores_acf = acf(valores, nlags=limite, fft=False)
        valores_pacf = pacf(valores, nlags=limite, method="ywm")
        return [float(v) for v in valores_acf], [float(v) for v in valores_pacf]
    except (ValueError, np.linalg.LinAlgError):
        return [], []


def _clasificar(
    adf_c: tuple[float, float],
    kpss_c: tuple[float, float],
    adf_t: tuple[float, float],
    kpss_t: tuple[float, float],
) -> str:
    adf_p, kpss_p = adf_c[1], kpss_c[1]
    if np.isnan(adf_p) or np.isnan(kpss_p):
        return "Inconclusa"
    if adf_p < 0.05 and kpss_p > 0.05:
        return "Estacionaria"
    if adf_p >= 0.05 and kpss_p <= 0.05:
        if adf_t[1] < 0.05 and kpss_t[1] > 0.05:
            return "Estacionaria en Tendencia"
        return "Raíz Unitaria Pura"
    if adf_p < 0.05 and kpss_p <= 0.05:
        return "Estacionaria en Tendencia" if adf_t[1] < 0.05 else "Inconclusa"
    return "Inconclusa"


def _recomendar_d(adf_p: float, kpss_p: float) -> int:
    if np.isnan(adf_p) or np.isnan(kpss_p):
        return 1
    if adf_p < 0.05 and kpss_p > 0.05:
        return 0
    return 1


def analizar_estacionariedad(valores: list[float] | np.ndarray, s: int = 12) -> dict:
    """ADF + KPSS (nivel y tendencia), ACF/PACF y D estacional sugerido."""
    x = np.asarray(valores, dtype=float)
    x = x[np.isfinite(x)]
    if len(x) < 16 or np.std(x) == 0:
        return a_primitivo(
            {
                "adf_stat": None,
                "adf_pval": None,
                "kpss_stat": None,
                "kpss_pval": None,
                "d_recomendado": 1 if len(x) else None,
                "D_estacional": 0,
                "veredicto": "Inconclusa",
                "acf_orig": [],
                "pacf_orig": [],
                "acf_diff": [],
                "pacf_diff": [],
            }
        )

    adf_c = _adf(x, "c")
    kpss_c = _kpss(x, "c")
    adf_t = _adf(x, "ct")
    kpss_t = _kpss(x, "ct")
    veredicto = _clasificar(adf_c, kpss_c, adf_t, kpss_t)
    d = _recomendar_d(adf_c[1], kpss_c[1])

    diferenciada = np.diff(x, n=1) if d else x.copy()
    acf_orig, pacf_orig = _acf_pacf(x)
    acf_diff, pacf_diff = _acf_pacf(diferenciada)

    D = 0
    if len(diferenciada) >= 2 * s:
        acf12 = acf_diff[s] if len(acf_diff) > s else 0.0
        if abs(acf12) > 0.25:
            estacional = diferenciada - np.concatenate([np.full(s, np.nan), diferenciada[:-s]])
            pval_estacional = _adf(estacional[np.isfinite(estacional)], "c")[1]
            D = 1 if pval_estacional < 0.05 else 0

    return a_primitivo(
        {
            "adf_stat": adf_c[0],
            "adf_pval": adf_c[1],
            "kpss_stat": kpss_c[0],
            "kpss_pval": kpss_c[1],
            "d_recomendado": int(d),
            "D_estacional": int(D),
            "veredicto": veredicto,
            "acf_orig": acf_orig,
            "pacf_orig": pacf_orig,
            "acf_diff": acf_diff,
            "pacf_diff": pacf_diff,
        }
    )
