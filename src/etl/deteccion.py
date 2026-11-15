"""Detección del formato real de archivos descargados de portales gubernamentales.

Los boletines de la ASFI pueden llegar como `.xlsx`, `.xls` binario (BIFF8/OLE2),
ZIP o incluso tablas HTML guardadas con extensión `.xls`, por lo que la extensión
declarada no es confiable.
"""

from __future__ import annotations

import io
import zipfile
from pathlib import Path

FIRMA_OLE2 = bytes.fromhex("D0CF11E0A1B11AE1")
FIRMA_ZIP = b"PK\x03\x04"
FIRMA_PDF = b"%PDF"

FORMATOS = ("xlsx", "xls", "html", "zip", "csv", "pdf", "desconocido")


def _leer_cabecera(fuente: str | Path | bytes, limite: int = 8192) -> bytes:
    if isinstance(fuente, bytes):
        return fuente[:limite]
    with Path(fuente).open("rb") as fh:
        return fh.read(limite)


def _detectar_zip(fuente: str | Path | bytes) -> str:
    """Distingue un .xlsx (ZIP con estructura OOXML) de un ZIP genérico."""
    try:
        if isinstance(fuente, bytes):
            with zipfile.ZipFile(io.BytesIO(fuente)) as zf:
                nombres = set(zf.namelist())
        else:
            with zipfile.ZipFile(fuente) as zf:
                nombres = set(zf.namelist())
    except (zipfile.BadZipFile, OSError):
        return "zip"
    if "xl/workbook.xml" in nombres or "[Content_Types].xml" in nombres:
        return "xlsx"
    return "zip"


def _parece_html(contenido: bytes) -> bool:
    texto = contenido.lstrip().lower()
    marcadores = (b"<html", b"<!doctype html", b"<table", b"<head", b"<body")
    return any(marcador in texto[:4096] for marcador in marcadores)


def _parece_csv(contenido: bytes) -> bool:
    try:
        texto = contenido.decode("utf-8", errors="strict")
    except UnicodeDecodeError:
        texto = contenido.decode("latin-1", errors="ignore")
    primeras = [linea for linea in texto.splitlines()[:10] if linea.strip()]
    if len(primeras) < 2:
        return False
    separadores = (",", ";", "\t", "|")
    for separador in separadores:
        coincidencias = sum(1 for linea in primeras if separador in linea)
        if coincidencias >= max(2, len(primeras) - 1):
            return True
    return False


def detectar_formato(fuente: str | Path | bytes, nombre: str = "") -> str:
    """Devuelve una de las etiquetas de FORMATOS según el contenido real."""
    cabecera = _leer_cabecera(fuente)
    if not cabecera:
        return "desconocido"

    if cabecera.startswith(FIRMA_OLE2):
        return "xls"
    if cabecera.startswith(FIRMA_PDF):
        return "pdf"
    if cabecera.startswith(FIRMA_ZIP):
        return _detectar_zip(fuente)
    if _parece_html(cabecera):
        return "html"
    if _parece_csv(cabecera):
        return "csv"

    sufijo = Path(nombre).suffix.lower()
    if sufijo in {".xls", ".xlsx"}:
        return "desconocido"
    return "desconocido"


def es_excel(formato: str) -> bool:
    return formato in {"xls", "xlsx", "html"}
