"""Tests de la regresión OLS con errores HAC y dummies estacionales."""

from __future__ import annotations

import numpy as np
from src.models.regresion import regresion_ols, verificar_normalidad


def _fechas(n: int) -> list[str]:
    import pandas as pd

    return [str(p) for p in pd.period_range("2015-01", periods=n, freq="M")]


def test_detecta_tendencia_y_estacionalidad():
    rng = np.random.default_rng(3)
    n = 96
    t = np.arange(n)
    meses = np.array([int(f[5:7]) for f in _fechas(n)])
    y = 100 + 0.8 * t + 5 * (meses == 12) + rng.normal(scale=0.05, size=n)
    resultado = regresion_ols(_fechas(n), list(y))
    assert resultado["r2_adj"] > 0.98
    pendiente = next(x for x in resultado["tendencia"] if x["termino"] == "t")
    assert pendiente["coef"] > 0
    assert pendiente["pval"] < 0.05
    diciembre = next(x for x in resultado["estacionalidad"] if x["mes"] == 12)
    assert diciembre["coef"] > 0


def test_serie_corta_devuelve_nulos():
    resultado = regresion_ols(_fechas(10), [1.0] * 10)
    assert resultado["r2_adj"] is None
    assert resultado["tendencia"] == []


def test_normalidad_qq_tiene_puntos():
    rng = np.random.default_rng(4)
    datos = rng.normal(size=100)
    resultado = verificar_normalidad(datos)
    assert len(resultado["qq_teorico"]) == 100
    assert len(resultado["qq_muestral"]) == 100
    assert resultado["jarque_bera_pval"] > 0.01
