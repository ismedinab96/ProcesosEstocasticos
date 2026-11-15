"""Tests del contrato Pydantic y de la exportación JSON/JS."""

from __future__ import annotations

import json

import pytest
from pydantic import ValidationError
from src.export.exportador import exportar, validar_contrato


def _contrato(semaforo: str = "verde") -> dict:
    return {
        "meta": {
            "generado_utc": "2026-01-01T00:00:00+00:00",
            "fuente": "ASFI Bolivia",
            "modo_demo": False,
            "rango_fechas": ["2024-01", "2024-02"],
            "total_observaciones": 2,
        },
        "bancos": [
            {
                "id": "b1",
                "nombre": "Banco Uno",
                "tipo": "Multiple",
                "semaforo": semaforo,
                "score_anomalia": float("nan"),
                "cobertura_meses": 2,
                "sparkline_mora": [2.0, 2.1],
            }
        ],
        "indicadores_meta": [
            {
                "id": "mora",
                "nombre": "Mora",
                "formula_latex": "x",
                "unidad": "%",
                "direccion_riesgo": "ascendente",
            }
        ],
        "series": {
            "b1": {
                "mora": {
                    "fechas": ["2024-01", "2024-02"],
                    "observado": [2.0, 2.1],
                    "estacionariedad": {"veredicto": "Estacionaria"},
                    "regresion_ols": {},
                    "sarima": None,
                    "backtest": None,
                }
            }
        },
        "markov": {
            "estados": ["Baja", "Media", "Alta", "Crítica"],
            "umbrales": [0.015, 0.025, 0.04],
            "por_banco": {
                "b1": {
                    "matriz_transicion": [
                        [0.9, 0.1, 0.0, 0.0],
                        [0.0, 0.9, 0.1, 0.0],
                        [0.0, 0.0, 0.9, 0.1],
                        [0.0, 0.0, 0.0, 1.0],
                    ],
                    "dist_estacionaria": [0.0, 0.0, 0.0, 1.0],
                    "tiempo_permanencia_meses": [10.0, 10.0, 10.0, 1000.0],
                    "prob_critico_h": {"m1": 0.0, "m3": 0.0, "m6": 0.0},
                }
            },
            "sistema_agregado": {
                "matriz_transicion": [[1.0, 0.0, 0.0, 0.0]] * 4,
                "dist_estacionaria": [1.0, 0.0, 0.0, 0.0],
            },
        },
        "alertas": [],
    }


def test_contrato_valido():
    contrato = validar_contrato(_contrato())
    assert contrato.bancos[0].semaforo == "verde"


def test_contrato_rechaza_semaforo_invalido():
    with pytest.raises(ValidationError):
        validar_contrato(_contrato("morado"))


def test_exportar_escribe_json_y_js_sin_nan(tmp_path):
    rutas = exportar(
        _contrato(),
        salida_json=tmp_path / "data.json",
        salida_js=tmp_path / "data.js",
    )
    datos = json.loads(rutas["json"].read_text(encoding="utf-8"))
    assert datos["bancos"][0]["score_anomalia"] is None
    texto_js = rutas["js"].read_text(encoding="utf-8")
    assert texto_js.startswith("window.ASFI_DATA = ")
    assert "NaN" not in texto_js
