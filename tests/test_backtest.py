"""Tests del backtesting walk-forward contra baselines."""

from __future__ import annotations

import numpy as np
from src.backtest.walkforward import evaluar_walkforward


def test_backtest_devuelve_metricas_comparables():
    rng = np.random.default_rng(6)
    y = 10 + 0.05 * np.arange(72) + rng.normal(scale=0.2, size=72)
    resultado = evaluar_walkforward(list(y), (0, 0, 0), (0, 0, 0, 12), ventana=6)
    assert resultado["observaciones_eval"] == 6
    for clave in (
        "rmse_modelo",
        "mae_modelo",
        "smape_modelo",
        "rmse_naive",
        "rmse_snaive",
    ):
        assert resultado[clave] is not None
        assert resultado[clave] >= 0
    assert isinstance(resultado["supera_baseline"], bool)


def test_serie_corta_no_evalua():
    resultado = evaluar_walkforward([1.0, 2.0, 3.0], (0, 0, 0), (0, 0, 0, 12))
    assert resultado["observaciones_eval"] == 0
    assert resultado["supera_baseline"] is None
