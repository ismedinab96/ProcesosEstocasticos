"""Tests del parser de Estados Financieros BMU de ASFI."""

from __future__ import annotations

from io import BytesIO

import pandas as pd
import pytest
from src.etl.parser_bmu import normalizar, parsear_bmu

CONFIG = {
    "bancos": [
        {"id": "bnb", "codigo_asfi": "BNB"},
        {"id": "bisa", "codigo_asfi": "BIS"},
        {"id": "bun", "codigo_asfi": "BUN"},
        {"id": "bme", "codigo_asfi": "BME"},
        {"id": "bcr", "codigo_asfi": "BCR"},
    ]
}


def _fila(etiqueta: str, *valores: float) -> list:
    return [etiqueta, *valores]


def _dataframe(unidad: str = "(en miles de bolivianos)") -> pd.DataFrame:
    filas = [
        ["BANCOS MULTIPLES — ESTADO DE SITUACION PATRIMONIAL"],
        ["AL 31 DE DICIEMBRE DE 2024"],
        [unidad],
        [None, "BNB", "BIS", "BUN", "BME", "BCR", "TOTAL SISTEMA"],
        _fila("ACTIVO", 1000, 2000, 1500, 1200, 900, 6600),
        _fila("PASIVO", 700, 1500, 1100, 900, 650, 4850),
        _fila("PATRIMONIO", 300, 500, 400, 300, 250, 1750),
        _fila("DISPONIBILIDADES", 100, 200, 150, 120, 90, 660),
        _fila("INVERSIONES TEMPORARIAS", 50, 80, 60, 40, 30, 260),
        _fila("CARTERA", 500, 800, 700, 600, 450, 3050),
        _fila("CARTERA VENCIDA TOTAL", 50, 60, 40, 30, 20, 200),
        _fila("CARTERA EJECUCIÓN TOTAL", 10, 20, 10, 5, 5, 50),
        _fila("(PREVISIÓN PARA INCOBRABILIDAD DE CARTERA)", -40, -70, -35, -25, -18, -188),
        _fila("OBLIGACIONES CON EL PÚBLICO", 400, 900, 600, 500, 380, 2780),
        _fila("OBLIGACIONES CON INSTITUCIONES FISCALES", 10, 20, 10, 5, 5, 50),
        _fila("RESULTADO NETO DE LA GESTIÓN", 80, 150, 90, 60, 40, 420),
    ]
    return pd.DataFrame(filas)


def test_normalizar_quita_acentos_y_prefijos():
    assert normalizar("  (=) RESULTADO NETO DE LA GESTIÓN ") == "RESULTADO NETO DE LA GESTION"
    assert normalizar("(PREVISIÓN PARA INCOBRABILIDAD)") == "PREVISION PARA INCOBRABILIDAD"


def test_parseo_extrae_cuentas_y_agrega_mora():
    resultado = parsear_bmu(
        _dataframe(), CONFIG, nombre_archivo="eeff_202412_BMU_EstadosFinancieros.zip"
    )
    assert resultado.fecha == "2024-12"
    assert resultado.unidad == "miles_de_bolivianos"
    assert resultado.codigos == ["BCR", "BIS", "BME", "BNB", "BUN"]
    assert len(resultado.panel) == 5
    bnb = resultado.panel.set_index("banco_id").loc["bnb"]
    assert bnb["activo_total"] == 1000
    assert bnb["cartera_mora"] == 60
    assert bnb["prevision_incobrables"] == 40
    assert bnb["obligaciones_corto_plazo"] == 410
    assert bnb["utilidad_neta"] == 80
    assert resultado.diferencia_identidad_max == 0


def test_parseo_detecta_fecha_desde_metadatos_sin_nombre():
    resultado = parsear_bmu(_dataframe(), CONFIG, nombre_archivo="archivo.zip")
    assert resultado.fecha == "2024-12"


def test_parseo_escala_bolivianos_a_miles():
    resultado = parsear_bmu(_dataframe("(en bolivianos)"), CONFIG, nombre_archivo="x_202412.xls")
    assert resultado.unidad == "bolivianos"
    assert resultado.factor_unidad == pytest.approx(0.001)
    bnb = resultado.panel.set_index("banco_id").loc["bnb"]
    assert bnb["activo_total"] == pytest.approx(1.0)


def test_parseo_falla_si_no_hay_encabezado_reconocible():
    df = _dataframe()
    df.iloc[3] = [None] * df.shape[1]
    with pytest.raises(ValueError):
        parsear_bmu(df, CONFIG, nombre_archivo="eeff_202412_BMU_EstadosFinancieros.zip")


def test_parseo_acepta_xlsx_en_bytes():
    buffer = BytesIO()
    _dataframe().to_excel(buffer, header=False, index=False, engine="openpyxl")
    resultado = parsear_bmu(
        buffer.getvalue(), CONFIG, nombre_archivo="eeff_202412_BMU_EstadosFinancieros.xlsx"
    )
    assert resultado.fecha == "2024-12"
    assert resultado.panel.set_index("banco_id").loc["bisa", "cartera_mora"] == 80


def test_parseo_acepta_html_disfrazado_de_xls():
    html = _dataframe().to_html(header=False, index=False).encode("utf-8")
    resultado = parsear_bmu(html, CONFIG, nombre_archivo="eeff_202412_BMU_EstadosFinancieros.xls")
    assert len(resultado.panel) == 5
    assert resultado.panel.set_index("banco_id").loc["bnb", "activo_total"] == 1000
