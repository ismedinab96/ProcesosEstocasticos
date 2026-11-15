import io
import zipfile

from src.etl.deteccion import detectar_formato, es_excel


def _xlsx_falso() -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as zf:
        zf.writestr("[Content_Types].xml", "<Types/>")
        zf.writestr("xl/workbook.xml", "<workbook/>")
    return buffer.getvalue()


def _zip_generico() -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as zf:
        zf.writestr("datos/archivo.csv", "a,b\n1,2\n")
    return buffer.getvalue()


def test_detecta_xlsx(tmp_path):
    ruta = tmp_path / "boletin.xls"  # extensión mentirosa
    ruta.write_bytes(_xlsx_falso())
    assert detectar_formato(ruta) == "xlsx"


def test_detecta_xls_binario(tmp_path):
    ruta = tmp_path / "antiguo.xls"
    ruta.write_bytes(bytes.fromhex("D0CF11E0A1B11AE1") + b"\x00" * 512)
    assert detectar_formato(ruta) == "xls"


def test_detecta_html_disfrazado(tmp_path):
    ruta = tmp_path / "tabla.xls"
    ruta.write_text(
        "<html><body><table><tr><td>Cuenta</td><td>Saldo</td></tr></table></body></html>",
        encoding="utf-8",
    )
    assert detectar_formato(ruta) == "html"
    assert es_excel("html")


def test_detecta_zip_generico(tmp_path):
    ruta = tmp_path / "paquete.zip"
    ruta.write_bytes(_zip_generico())
    assert detectar_formato(ruta) == "zip"


def test_detecta_csv_y_pdf():
    assert detectar_formato(b"cuenta,valor\nActivo,100\nPasivo,80\n") == "csv"
    assert detectar_formato(b"%PDF-1.7 contenido") == "pdf"


def test_desconocido():
    assert detectar_formato(b"\x00\x01\x02\x03") == "desconocido"
    assert detectar_formato(b"") == "desconocido"
