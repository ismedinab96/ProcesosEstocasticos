"""Regresión de series de tiempo con tendencia, dummies mensuales y errores HAC."""

from __future__ import annotations

import warnings

import numpy as np
import statsmodels.api as sm
from scipy import stats
from statsmodels.stats.diagnostic import acorr_ljungbox, het_arch
from statsmodels.stats.stattools import durbin_watson

from .utilidades import a_primitivo


def regresion_ols(fechas: list[str], valores: list[float]) -> dict:
    y = np.asarray(valores, dtype=float)
    n = len(y)
    meses = np.array([int(f[5:7]) for f in fechas])
    if n < 24 or np.std(y) == 0:
        return a_primitivo(
            {
                "r2_adj": None,
                "dw_stat": None,
                "ljung_box_pval": None,
                "arch_lm_pval": None,
                "tendencia": [],
                "estacionalidad": [],
            }
        )

    t = np.arange(n, dtype=float)
    tc = t - t.mean()
    columnas = [np.ones(n), tc, tc**2]
    nombres = ["constante", "t", "t2"]
    presentes = sorted(set(meses))
    for mes in presentes[1:]:
        if np.sum(meses == mes) >= 2:
            columnas.append((meses == mes).astype(float))
            nombres.append(f"mes_{mes:02d}")

    X = np.column_stack(columnas)
    if np.linalg.matrix_rank(X) < X.shape[1]:
        X = X[:, :-1]
        nombres = nombres[:-1]

    try:
        modelo = sm.OLS(y, X).fit(cov_type="HAC", cov_kwds={"maxlags": max(1, min(12, n // 2))})
        residuos = np.asarray(modelo.resid)
        dw = float(durbin_watson(residuos))
        lb = acorr_ljungbox(residuos, lags=[min(12, n // 2)], return_df=True)
        ljung = float(lb["lb_pvalue"].iloc[0])
        arch = float(het_arch(residuos, nlags=min(12, n // 2))[1])
        tendencia = [
            {
                "termino": nombre,
                "coef": float(modelo.params[i]),
                "pval": float(modelo.pvalues[i]),
            }
            for i, nombre in enumerate(nombres)
            if nombre in {"constante", "t", "t2"}
        ]
        estacionalidad = [
            {
                "mes": int(nombre.split("_")[1]),
                "coef": float(modelo.params[i]),
                "pval": float(modelo.pvalues[i]),
            }
            for i, nombre in enumerate(nombres)
            if nombre.startswith("mes_")
        ]
        return a_primitivo(
            {
                "r2_adj": float(modelo.rsquared_adj),
                "dw_stat": dw,
                "ljung_box_pval": ljung,
                "arch_lm_pval": arch,
                "tendencia": tendencia,
                "estacionalidad": estacionalidad,
            }
        )
    except (ValueError, np.linalg.LinAlgError):
        return a_primitivo(
            {
                "r2_adj": None,
                "dw_stat": None,
                "ljung_box_pval": None,
                "arch_lm_pval": None,
                "tendencia": [],
                "estacionalidad": [],
            }
        )


def verificar_normalidad(residuos: np.ndarray) -> dict:
    residuos = np.asarray(residuos, dtype=float)
    residuos = residuos[np.isfinite(residuos)]
    if len(residuos) < 8 or np.std(residuos) == 0:
        return {
            "jarque_bera_pval": None,
            "shapiro_pval": None,
            "asimetria": None,
            "curtosis": None,
            "qq_teorico": [],
            "qq_muestral": [],
        }
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        jb_p = float(stats.jarque_bera(residuos).pvalue)
        shapiro_p = float(stats.shapiro(residuos).pvalue) if len(residuos) >= 8 else None
    estandarizados = (residuos - residuos.mean()) / residuos.std(ddof=1)
    ordenados = np.sort(estandarizados)
    cuantiles = stats.norm.ppf((np.arange(1, len(ordenados) + 1) - 0.5) / len(ordenados))
    return {
        "jarque_bera_pval": jb_p,
        "shapiro_pval": shapiro_p,
        "asimetria": float(stats.skew(residuos)),
        "curtosis": float(stats.kurtosis(residuos)),
        "qq_teorico": [float(v) for v in cuantiles],
        "qq_muestral": [float(v) for v in ordenados],
    }
