"""Tests de estacionariedad ADF/KPSS y ACF/PACF."""

from __future__ import annotations

import numpy as np
from src.models.estacionariedad import analizar_estacionariedad


def _ar1(n: int = 240, phi: float = 0.5, semilla: int = 0) -> np.ndarray:
    rng = np.random.default_rng(semilla)
    ruido = rng.normal(size=n)
    serie = np.zeros(n)
    for i in range(1, n):
        serie[i] = phi * serie[i - 1] + ruido[i]
    return serie


def test_ar1_se_clasifica_estacionaria():
    resultado = analizar_estacionariedad(_ar1())
    assert resultado["adf_pval"] < 0.05
    assert resultado["d_recomendado"] == 0
    assert len(resultado["acf_orig"]) > 12
    assert len(resultado["acf_orig"]) == len(resultado["pacf_orig"])


def test_caminata_aleatoria_requiere_diferenciar():
    rng = np.random.default_rng(1)
    serie = np.cumsum(rng.normal(size=200))
    resultado = analizar_estacionariedad(serie)
    assert resultado["adf_pval"] > 0.05
    assert resultado["d_recomendado"] == 1


def test_serie_constante_es_inconclusa():
    resultado = analizar_estacionariedad([3.0] * 60)
    assert resultado["veredicto"] == "Inconclusa"
    assert resultado["acf_orig"] == []


def test_D_estacional_detecta_patron_anual():
    rng = np.random.default_rng(2)
    t = np.arange(180)
    serie = 10 + 2 * np.sin(2 * np.pi * t / 12) + rng.normal(scale=0.05, size=len(t))
    resultado = analizar_estacionariedad(serie)
    assert resultado["D_estacional"] == 1
