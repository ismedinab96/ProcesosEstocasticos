"""Tests de la cadena de Markov sobre morosidad."""

from __future__ import annotations

import numpy as np
import pytest
from src.models.markov import (
    analizar_markov,
    contar_transiciones,
    discretizar,
    distribucion_estacionaria,
    estimar_matriz,
    prueba_orden,
)

CONFIG = {
    "markov": {
        "estados": ["Baja", "Media", "Alta", "Crítica"],
        "umbrales": [0.015, 0.025, 0.040],
        "laplace_alpha": 0.001,
    }
}


def test_discretizacion_usa_umbrales_en_fraccion():
    valores = [1.0, 1.4, 1.5, 2.0, 2.5, 4.0, 4.5]
    assert discretizar(valores, [0.015, 0.025, 0.040]).tolist() == [0, 0, 1, 1, 2, 3, 3]


def test_matriz_estocastica_con_suavizado():
    conteos = np.array([[10, 0, 0, 0], [0, 0, 0, 0]], dtype=float)
    matriz = estimar_matriz(conteos)
    assert np.allclose(matriz.sum(axis=1), 1.0)
    assert np.all(matriz > 0)


def test_distribucion_estacionaria_suma_uno():
    matriz = np.array([[0.8, 0.2], [0.3, 0.7]])
    pi = distribucion_estacionaria(matriz)
    assert pi.sum() == pytest.approx(1.0)
    assert np.allclose(pi @ matriz, pi)


def test_transiciones_cuentan_pares():
    estados = np.array([0, 1, 1, 2, 2, 2])
    conteos = contar_transiciones(estados, 4)
    assert conteos[0, 1] == 1
    assert conteos[1, 1] == 1
    assert conteos[1, 2] == 1
    assert conteos[2, 2] == 2


def test_analisis_completo_por_banco():
    rng = np.random.default_rng(5)
    mora = {"banco_a": list(2 + 0.5 * np.sin(np.arange(84) / 3) + rng.normal(scale=0.05, size=84))}
    resultado = analizar_markov(mora, CONFIG)
    banco = resultado["por_banco"]["banco_a"]
    matriz = np.asarray(banco["matriz_transicion"])
    assert np.allclose(matriz.sum(axis=1), 1.0)
    assert sum(banco["dist_estacionaria"]) == pytest.approx(1.0)
    assert set(banco["prob_critico_h"]) == {"m1", "m3", "m6", "m12"}
    assert min(banco["tiempo_permanencia_meses"]) >= 1.0
    assert 0 <= banco["test_orden_1_vs_2_pval"] <= 1
    assert sum(resultado["sistema_agregado"]["dist_estacionaria"]) == pytest.approx(1.0)


def test_prueba_orden_devuelve_nulo_con_poca_muestra():
    resultado = prueba_orden(np.array([0, 1, 2]), 4)
    assert resultado["pval"] is None
