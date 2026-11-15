from src.scraping.reconocimiento import (
    Enlace,
    ResultadoSeccion,
    SondaArchivo,
    _extraer_enlaces,
    _redactar_informe,
)


def test_extrae_enlaces_absolutos():
    html = """
    <html><body>
      <a href="/boletines/2024/eeff.xls">EEFF enero</a>
      <a href="https://www.asfi.gob.bo/estados-financieros">Sección</a>
      <a href="javascript:void(0)">Ignorar</a>
      <a href="/boletines/2024/eeff.xls">Duplicado</a>
    </body></html>
    """
    enlaces = _extraer_enlaces("https://www.asfi.gob.bo/index.php", html)
    assert len(enlaces) == 2
    assert enlaces[0].url == "https://www.asfi.gob.bo/boletines/2024/eeff.xls"
    assert enlaces[0].es_archivo is True
    assert enlaces[1].es_archivo is False


def test_informe_contiene_secciones_y_archivos():
    resultados = [
        ResultadoSeccion(
            nombre="boletines",
            url="https://www.asfi.gob.bo/boletines",
            estado="HTTP 200",
            content_type="text/html",
            titulo="Boletines",
            tablas=2,
            enlaces=[Enlace("https://www.asfi.gob.bo/a.xlsx", "Archivo", True)],
        )
    ]
    sondas = [
        SondaArchivo(
            url="https://www.asfi.gob.bo/a.xlsx",
            texto="Archivo",
            content_type="application/vnd.ms-excel",
            bytes=2048,
            formato="xls",
            estado="HTTP 200",
        )
    ]
    informe = _redactar_informe(
        generado="2025-01-01T00:00:00+00:00",
        base="https://www.asfi.gob.bo",
        robots={"https://www.asfi.gob.bo": "permitido"},
        resultados=resultados,
        sondas=sondas,
        max_enlaces=8,
    )
    assert "# Exploración del portal de la ASFI" in informe
    assert "Robots.txt" in informe
    assert "a.xlsx" in informe
    assert "Descargo" in informe
