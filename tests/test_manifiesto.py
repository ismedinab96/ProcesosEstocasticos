import hashlib

from src.scraping.manifiesto import (
    COLUMNAS,
    Manifiesto,
    RegistroManifiesto,
    sha256_archivo,
    sha256_bytes,
)


def test_sha256_bytes_y_archivo(tmp_path):
    contenido = b"contenido de prueba"
    esperado = hashlib.sha256(contenido).hexdigest()
    assert sha256_bytes(contenido) == esperado

    ruta = tmp_path / "archivo.bin"
    ruta.write_bytes(contenido)
    assert sha256_archivo(ruta) == esperado


def test_registro_tiene_columnas_contrato():
    registro = RegistroManifiesto(
        url="https://www.asfi.gob.bo/x.xls",
        ruta_local="data/raw/2024/01/eeff_x.xls",
        timestamp="2024-01-01T00:00:00+00:00",
        sha256="a" * 64,
        bytes=10,
        status="descargado",
    )
    assert set(registro.como_fila()) == set(COLUMNAS)


def test_manifiesto_idempotente_y_persistente(tmp_path):
    ruta = tmp_path / "manifest.csv"
    archivo = tmp_path / "dato.xls"
    archivo.write_bytes(b"datos")

    manifiesto = Manifiesto(ruta)
    assert manifiesto.registrar_archivo("https://www.asfi.gob.bo/dato.xls", archivo) is True
    sha = sha256_archivo(archivo)
    assert manifiesto.contiene_hash(sha)
    assert manifiesto.ruta_por_hash(sha) == archivo

    # Mismo contenido: no debe duplicarse.
    copia = tmp_path / "copia.xls"
    copia.write_bytes(b"datos")
    assert manifiesto.registrar_archivo("https://www.asfi.gob.bo/copia.xls", copia) is False
    assert len(manifiesto.registros) == 1

    recargado = Manifiesto(ruta)
    assert len(recargado.registros) == 1
    assert recargado.contiene_hash(sha)


def test_actualizar_ruta(tmp_path):
    ruta = tmp_path / "manifest.csv"
    archivo = tmp_path / "archivo.bin"
    archivo.write_bytes(b"contenido")
    manifiesto = Manifiesto(ruta)
    manifiesto.registrar_archivo("https://www.asfi.gob.bo/a", archivo)
    sha = sha256_archivo(archivo)

    nuevo = tmp_path / "archivo.xls"
    archivo.rename(nuevo)
    assert manifiesto.actualizar_ruta(sha, nuevo, status="descargado:html") is True
    registro = Manifiesto(ruta).registros[0]
    assert registro.ruta_local.endswith("archivo.xls")
    assert registro.status == "descargado:html"


def test_manifiesto_inexistente_es_vacio(tmp_path):
    manifiesto = Manifiesto(tmp_path / "no_existe.csv")
    assert manifiesto.registros == []
