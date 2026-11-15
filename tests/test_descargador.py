import pytest
from src.scraping.descargador import (
    TareaDescarga,
    _destino,
    _periodo_desde_url,
    _validar_host,
)


def test_periodo_desde_url():
    assert _periodo_desde_url("https://www.asfi.gob.bo/2024/03/eeff.xls") == ("2024", "03")
    assert _periodo_desde_url("https://www.asfi.gob.bo/2023-11/eeff.xls") == ("2023", "11")


def test_periodo_prioriza_nombre_sobre_carpeta():
    url = "https://www.asfi.gob.bo/sites/default/files/2025-08/202412_BDR_EstadosFinancieros.xls"
    assert _periodo_desde_url(url) == ("2024", "12")


def test_periodo_invalido_usa_fecha_actual():
    anio, mes = _periodo_desde_url("https://www.asfi.gob.bo/2024/99/eeff.xls")
    assert anio.isdigit() and len(anio) == 4
    assert 1 <= int(mes) <= 12


def test_destino_respeta_convencion(tmp_path):
    tarea = TareaDescarga(url="https://www.asfi.gob.bo/2024/03/EEFF Marzo.xls")
    destino = _destino(tmp_path, tarea)
    assert destino.parent == tmp_path / "2024" / "03"
    assert destino.name == "eeff_EEFF_Marzo.xls"


def test_destino_relativo_explicito(tmp_path):
    tarea = TareaDescarga(url="https://x/y", destino_relativo="manual/archivo.csv")
    assert _destino(tmp_path, tarea) == tmp_path / "manual" / "archivo.csv"


def test_validar_host():
    with pytest.raises(ValueError):
        _validar_host("https://ejemplo.com/a.xls", permitir_otros=False)
    _validar_host("https://www.asfi.gob.bo/a.xls", permitir_otros=False)
    _validar_host("https://ejemplo.com/a.xls", permitir_otros=True)
    with pytest.raises(ValueError):
        _validar_host("ftp://www.asfi.gob.bo/a.xls", permitir_otros=True)
