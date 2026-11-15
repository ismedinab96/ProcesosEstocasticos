"""Tests del motor de indicadores (desacumulación, anualización y ratios)."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
from src.indicators.calculadora import calcular_indicadores, panel_ancho


def _panel(meses: int = 25) -> pd.DataFrame:
    fechas = [str(p) for p in pd.period_range("2020-01", periods=meses, freq="M")]
    filas = []
    for fecha in fechas:
        mes = int(fecha[5:7])
        utilidad = 10 * mes
        filas.append(
            {
                "fecha": fecha,
                "banco_id": "demo",
                "activo_total": 1000.0,
                "pasivo_total": 900.0,
                "patrimonio_total": 100.0,
                "cartera_bruta": 500.0,
                "cartera_mora": 25.0,
                "prevision_incobrables": 20.0,
                "disponibilidades": 100.0,
                "inversiones_temporarias": 50.0,
                "obligaciones_corto_plazo": 300.0,
                "utilidad_neta": float(utilidad),
                "depositos": 400.0,
            }
        )
    return pd.DataFrame(filas)


def _valor(largo: pd.DataFrame, indicador: str, fecha: str) -> float:
    fila = largo[(largo["indicador_id"] == indicador) & (largo["fecha"] == fecha)]
    return float(fila["valor"].iloc[0])


def test_ratios_basicos():
    largo = calcular_indicadores(_panel())
    assert _valor(largo, "mora", "2020-06") == pytest.approx(5.0)
    assert _valor(largo, "cobertura", "2020-06") == pytest.approx(80.0)
    assert _valor(largo, "liquidez", "2020-06") == pytest.approx(50.0)


def test_desacumulacion_y_anualizacion():
    largo = calcular_indicadores(_panel())
    assert np.isnan(_valor(largo, "roa", "2020-11"))
    assert _valor(largo, "roa", "2020-12") == pytest.approx(12.0)
    assert _valor(largo, "roe", "2020-12") == pytest.approx(120.0)


def test_enero_reinicia_flujo_sin_negativos():
    panel = _panel()
    panel.loc[panel["fecha"] == "2021-01", "utilidad_neta"] = 10.0
    largo = calcular_indicadores(panel)
    assert _valor(largo, "roa", "2021-01") == pytest.approx(12.0)


def test_crecimiento_interanual():
    largo = calcular_indicadores(_panel())
    assert _valor(largo, "crec_cartera", "2021-01") == pytest.approx(0.0)
    assert np.isnan(_valor(largo, "crec_cartera", "2020-12"))


def test_division_por_cero_no_genera_infinitos():
    panel = _panel()
    panel["cartera_bruta"] = 0.0
    largo = calcular_indicadores(panel)
    assert np.isnan(_valor(largo, "mora", "2020-06"))


def test_panel_ancho_una_fila_por_banco_mes():
    ancho = panel_ancho(calcular_indicadores(_panel()))
    assert len(ancho) == 25
    assert "mora" in ancho.columns
