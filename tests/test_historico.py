"""Tests de la descarga histórica mensual (sin red)."""

from __future__ import annotations

import pytest
from src.scraping.configuracion import cargar_config
from src.scraping.historico import construir_tareas, meses_entre


def test_meses_entre_es_inclusivo():
    assert meses_entre("2024-12", "2025-02") == [
        ("2024", "12"),
        ("2025", "01"),
        ("2025", "02"),
    ]


def test_meses_entre_rechaza_rango_invertido():
    with pytest.raises(ValueError):
        meses_entre("2025-02", "2024-12")


def test_construir_tareas_usa_plantilla_verificada():
    config = cargar_config()
    tareas = construir_tareas(config, "eeff", "2024-11", "2024-12")
    assert len(tareas) == 2
    assert tareas[0].url == (
        "https://www.asfi.gob.bo/sites/default/files/estadisticaif/bancos_multiples/"
        "2024/11/202411_BMU_EstadosFinancieros.zip"
    )
    assert tareas[1].tipo_entidad == "eeff"


def test_construir_tareas_indicadores():
    config = cargar_config()
    tareas = construir_tareas(config, "indicadores", "2025-01", "2025-01")
    assert "IndicadoresFinancieros" in tareas[0].url
