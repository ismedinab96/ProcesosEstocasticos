"""Tests de selección SARIMA, pronóstico y series con faltantes iniciales."""

from __future__ import annotations

import numpy as np
import pandas as pd
from src.models.sarima import _combinaciones, ajustar_serie

CONFIG = {
    "general": {
        "meses_minimos_serie": 36,
        "meses_pronostico": 6,
        "meses_ventana_backtest": 6,
    },
    "sarima": {
        "s": 12,
        "grilla": {
            "p": [0, 1],
            "d": [0, 1],
            "q": [0, 1],
            "P": [0],
            "D": [0, 1],
            "Q": [0],
        },
        "enforce_stationarity": False,
        "enforce_invertibility": False,
        "maxiter": 30,
        "max_pq_total": 2,
        "max_PQ_total": 0,
    },
}


def _datos(n: int = 72) -> tuple[list[str], list[float]]:
    fechas = [str(p) for p in pd.period_range("2017-01", periods=n, freq="M")]
    t = np.arange(n)
    rng = np.random.default_rng(7)
    valores = 10 + 0.03 * t + 0.5 * np.sin(2 * np.pi * t / 12) + rng.normal(scale=0.05, size=n)
    return fechas, [float(v) for v in valores]


def test_grilla_respeta_cotas():
    combos = _combinaciones(CONFIG, d=1, D=1)
    assert len(combos) == 4
    assert all(p + q <= 2 and P + Q <= 0 for (p, _, q), (P, _, Q, _) in combos)


def test_ajuste_completo_y_pronostico():
    fechas, valores = _datos()
    resultado = ajustar_serie(fechas, valores, CONFIG)
    assert resultado["sarima"] is not None
    assert resultado["apta_modelado"] is True
    assert len(resultado["pronostico"]["fechas"]) == 6
    assert len(resultado["pronostico"]["media"]) == 6
    assert len(resultado["residuos_estandarizados"]) == len(resultado["observado"])
    assert len(resultado["sarima"]["top3_modelos"]) <= 3
    assert resultado["sarima"]["modelos_evaluados"] >= 1
    assert resultado["backtest"]["observaciones_eval"] == 6


def test_faltantes_iniciales_se_recortan():
    fechas, valores = _datos(72)
    valores = [None] * 12 + valores[12:]
    resultado = ajustar_serie(fechas, valores, CONFIG)
    assert resultado["fechas"][0] == fechas[12]
    assert len(resultado["observado"]) == 60


def test_serie_constante_no_se_modela():
    fechas, _ = _datos(60)
    resultado = ajustar_serie(fechas, [1.0] * 60, CONFIG)
    assert resultado["sarima"] is None
    assert resultado["apta_modelado"] is False
