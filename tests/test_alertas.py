"""Tests del motor determinista de alertas."""

from __future__ import annotations

import pandas as pd
from src.models.alertas import generar_alertas

CONFIG = {
    "bancos": [{"id": "b1", "nombre": "Banco Uno"}],
    "indicadores": [
        {
            "id": "mora",
            "nombre": "Índice de Morosidad",
            "direccion_riesgo": "ascendente",
        }
    ],
    "alertas": {
        "cusum_banda": 5.0,
        "z_vigilancia": 2.0,
        "z_alerta": 3.0,
        "racha_meses": 3,
        "prob_critico_3m_umbral": 0.25,
    },
    "markov": {"estados": ["Baja", "Media", "Alta", "Crítica"]},
}


def _fechas(n: int) -> list[str]:
    return [str(p) for p in pd.period_range("2023-01", periods=n, freq="M")]


def _serie(observado: list[float], z: list[float], inf: float, sup: float) -> dict:
    fechas = _fechas(len(observado))
    return {
        "fechas": fechas,
        "observado": observado,
        "sarima": {"orden": [1, 0, 0]},
        "residuos_estandarizados": z,
        "prediccion_un_paso": {
            "fechas": fechas,
            "media": [2.0] * len(fechas),
            "ic95_inf": [inf] * len(fechas),
            "ic95_sup": [sup] * len(fechas),
        },
    }


def _markov(n: int) -> dict:
    return {
        "estados": ["Baja", "Media", "Alta", "Crítica"],
        "por_banco": {
            "b1": {
                "secuencia_estados": [0] * n,
                "prob_critico_h": {"m1": 0.01, "m3": 0.02, "m6": 0.03, "m12": 0.05},
            }
        },
    }


def test_anomalia_inyectada_genera_alerta_critica():
    n = 30
    observado = [2.0] * n
    z = [0.1] * n
    observado[20] = 5.0
    z[20] = 3.6
    series = {"b1": {"mora": _serie(observado, z, 1.9, 2.1)}}
    alertas = generar_alertas(series, _markov(n), CONFIG)
    assert len(alertas) == 1
    alerta = alertas[0]
    assert alerta["fecha"] == _fechas(n)[20]
    assert alerta["severidad"] == "critica"
    assert "residuo_z_3" in alerta["senales_activadas"]
    assert "fuera_banda_95" in alerta["senales_activadas"]


def test_serie_normal_no_genera_alertas():
    n = 24
    series = {"b1": {"mora": _serie([2.0] * n, [0.2] * n, 1.0, 3.0)}}
    assert generar_alertas(series, _markov(n), CONFIG) == []


def test_racha_sostenida_genera_vigilancia():
    observado = [2.0, 2.1, 2.25, 2.45, 2.7, 3.0]
    z = [0.1] * len(observado)
    fechas = _fechas(len(observado))
    series = {
        "b1": {
            "mora": {
                "fechas": fechas,
                "observado": observado,
                "sarima": {"orden": [1, 0, 0]},
                "residuos_estandarizados": z,
                "prediccion_un_paso": {
                    "fechas": fechas,
                    "media": [2.0] * len(fechas),
                    "ic95_inf": [0.0] * len(fechas),
                    "ic95_sup": [10.0] * len(fechas),
                },
            }
        }
    }
    alertas = generar_alertas(series, _markov(len(observado)), CONFIG)
    assert any("racha_deterioro" in a["senales_activadas"] for a in alertas)
    assert all(a["severidad"] == "vigilancia" for a in alertas)


def test_indice_ascendente_ignora_mejoras():
    obs = [3.0, 2.9, 2.8, 2.7, 2.6]
    z = [0.0] * len(obs)
    fechas = _fechas(len(obs))
    series = {
        "b1": {
            "mora": {
                "fechas": fechas,
                "observado": obs,
                "sarima": {"orden": [1, 0, 0]},
                "residuos_estandarizados": z,
                "prediccion_un_paso": {
                    "fechas": fechas,
                    "media": [3.0] * len(fechas),
                    "ic95_inf": [0.0] * len(fechas),
                    "ic95_sup": [10.0] * len(fechas),
                },
            }
        }
    }
    assert generar_alertas(series, _markov(len(obs)), CONFIG) == []


def test_z_se_calcula_con_numpy_sin_romper_listas_nulas():
    n = 20
    z = [None] * n
    z[-1] = 3.1
    series = {"b1": {"mora": _serie([2.0] * n, z, 1.0, 3.0)}}
    alertas = generar_alertas(series, _markov(n), CONFIG)
    assert len(alertas) == 1
    assert alertas[0]["z_score"] == 3.1
