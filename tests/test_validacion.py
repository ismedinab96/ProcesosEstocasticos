"""Tests de validaciones contables y cobertura."""

from __future__ import annotations

import pandas as pd
from src.etl.validacion import (
    duplicados,
    resumen_cobertura,
    resumen_identidad,
    validar_identidad,
    violaciones_positivas,
)


def _panel() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "fecha": "2024-01",
                "banco_id": "a",
                "activo_total": 100.0,
                "pasivo_total": 70.0,
                "patrimonio_total": 30.0,
                "cartera_bruta": 50.0,
                "depositos": 40.0,
                "obligaciones_corto_plazo": 35.0,
            },
            {
                "fecha": "2024-02",
                "banco_id": "a",
                "activo_total": 100.5,
                "pasivo_total": 70.0,
                "patrimonio_total": 30.0,
                "cartera_bruta": 50.0,
                "depositos": 40.0,
                "obligaciones_corto_plazo": 35.0,
            },
            {
                "fecha": "2024-04",
                "banco_id": "b",
                "activo_total": -1.0,
                "pasivo_total": 10.0,
                "patrimonio_total": 5.0,
                "cartera_bruta": 0.0,
                "depositos": 4.0,
                "obligaciones_corto_plazo": 3.0,
            },
        ]
    )


def test_identidad_detecta_discrepancias_fuera_de_tolerancia():
    tabla = validar_identidad(_panel(), tolerancia=1.0)
    assert len(tabla) == 3
    assert list(tabla["cumple"]) == [True, True, False]
    resumen = resumen_identidad(tabla)
    assert resumen["fallos"] == 1
    assert resumen["diferencia_max"] == 16.0


def test_violaciones_positivas():
    violaciones = violaciones_positivas(_panel())
    assert len(violaciones) == 2
    assert set(violaciones["cuenta"]) == {"activo_total", "cartera_bruta"}


def test_cobertura_cuenta_huecos_y_umbral():
    cobertura = resumen_cobertura(_panel(), meses_minimos=2).set_index("banco_id")
    assert cobertura.loc["a", "observaciones"] == 2
    assert cobertura.loc["a", "huecos"] == 0
    assert bool(cobertura.loc["a", "apta_para_modelado"]) is True
    assert cobertura.loc["b", "huecos"] == 0
    assert bool(cobertura.loc["b", "apta_para_modelado"]) is False


def test_duplicados():
    panel = pd.concat([_panel(), _panel().iloc[[0]]], ignore_index=True)
    assert len(duplicados(panel)) == 2
