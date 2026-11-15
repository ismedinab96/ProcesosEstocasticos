"""Parser de los Estados Financieros mensuales de Bancos Múltiples (ASFI).

Los archivos publicados por ASFI son matrices transpuestas: cada fila es una
cuenta contable del PUC y cada columna una entidad identificada por su sigla
oficial. El parser extrae un panel largo por banco y mes con las cuentas
canónicas usadas por el motor de indicadores.
"""

from __future__ import annotations

import io
import re
import unicodedata
import zipfile
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

MESES_ES = {
    "ENERO": 1,
    "FEBRERO": 2,
    "MARZO": 3,
    "ABRIL": 4,
    "MAYO": 5,
    "JUNIO": 6,
    "JULIO": 7,
    "AGOSTO": 8,
    "SEPTIEMBRE": 9,
    "OCTUBRE": 10,
    "NOVIEMBRE": 11,
    "DICIEMBRE": 12,
}

ALIAS_CUENTAS: dict[str, list[str]] = {
    "activo_total": ["ACTIVO"],
    "pasivo_total": ["PASIVO"],
    "patrimonio_total": ["PATRIMONIO"],
    "disponibilidades": ["DISPONIBILIDADES"],
    "inversiones_temporarias": ["INVERSIONES TEMPORARIAS"],
    "cartera_bruta": ["CARTERA"],
    "cartera_mora": ["CARTERA VENCIDA TOTAL", "CARTERA EJECUCION TOTAL"],
    "prevision_incobrables": ["PREVISION PARA INCOBRABILIDAD DE CARTERA"],
    "utilidad_neta": ["RESULTADO NETO DE LA GESTION"],
    "depositos": ["OBLIGACIONES CON EL PUBLICO"],
    "obligaciones_corto_plazo": [
        "OBLIGACIONES CON EL PUBLICO",
        "OBLIGACIONES CON INSTITUCIONES FISCALES",
        "OBLIGACIONES CON EMPRESAS PUBLICAS",
        "OBLIGACIONES CON BANCOS Y ENTIDADES DE FINANCIAMIENTO",
        "OTRAS CUENTAS POR PAGAR",
        "VALORES EN CIRCULACION",
    ],
}

# Alternativas cuando la versión del archivo no trae los subtotales "TOTAL".
ALIAS_RESPALDO = {
    "cartera_mora": ["CARTERA VENCIDA", "CARTERA EN EJECUCION"],
}

CUENTAS_SALIDA = [
    "activo_total",
    "pasivo_total",
    "patrimonio_total",
    "disponibilidades",
    "inversiones_temporarias",
    "cartera_bruta",
    "cartera_mora",
    "prevision_incobrables",
    "utilidad_neta",
    "depositos",
    "obligaciones_corto_plazo",
]


def normalizar(texto: object) -> str:
    """Mayúsculas, sin acentos, sin espacios múltiples ni paréntesis externos."""
    if texto is None or (isinstance(texto, float) and pd.isna(texto)):
        return ""
    cadena = unicodedata.normalize("NFKD", str(texto))
    cadena = "".join(c for c in cadena if not unicodedata.combining(c))
    cadena = cadena.upper().replace("(", "").replace(")", "").strip()
    cadena = re.sub(r"^[^A-Z0-9]+", "", cadena)
    cadena = re.sub(r"\s+", " ", cadena)
    return cadena


def _a_numero(valor: object) -> float:
    if valor is None or (isinstance(valor, float) and pd.isna(valor)):
        return float("nan")
    if isinstance(valor, (int, float)):
        return float(valor)
    texto = str(valor).strip().replace(",", "")
    if not texto:
        return float("nan")
    try:
        return float(texto)
    except ValueError:
        return float("nan")


@dataclass
class ResultadoParseo:
    panel: pd.DataFrame
    fecha: str
    unidad: str
    factor_unidad: float
    codigos: list[str] = field(default_factory=list)
    diferencia_identidad_max: float = float("nan")


def _hojas_eeff(names: list[str]) -> list[str]:
    return [
        n
        for n in names
        if n.lower().endswith((".xls", ".xlsx", ".xlsm")) and "evolutivo" not in n.lower()
    ]


def _leer_bytes_excel(fuente: str | Path | bytes) -> tuple[bytes, str]:
    """Devuelve (bytes del Excel, extensión) resolviendo ZIP y HTML disfrazado."""
    if isinstance(fuente, (str, Path)):
        ruta = Path(fuente)
        if ruta.suffix.lower() == ".zip":
            with zipfile.ZipFile(ruta) as zf:
                candidatos = _hojas_eeff(zf.namelist())
                if not candidatos:
                    raise ValueError(f"El ZIP {ruta} no contiene hojas de EEFF principales")
                nombre = candidatos[0]
                return zf.read(nombre), Path(nombre).suffix.lower()
        return ruta.read_bytes(), ruta.suffix.lower()

    datos = bytes(fuente)
    if datos.startswith(b"PK\x03\x04"):
        with zipfile.ZipFile(io.BytesIO(datos)) as zf:
            nombres = zf.namelist()
            candidatos = _hojas_eeff(nombres)
            if candidatos:
                nombre = candidatos[0]
                return zf.read(nombre), Path(nombre).suffix.lower()
            if any(n.startswith("xl/") for n in nombres):
                return datos, ".xlsx"
        raise ValueError("El ZIP no contiene hojas de EEFF principales")
    return datos, ".xls"


def _leer_dataframe(fuente: str | Path | bytes | pd.DataFrame) -> pd.DataFrame:
    if isinstance(fuente, pd.DataFrame):
        return fuente.copy()
    datos, extension = _leer_bytes_excel(fuente)
    buffer = io.BytesIO(datos)
    try:
        return pd.read_excel(buffer, header=None, engine="openpyxl")
    except Exception:
        buffer.seek(0)
        try:
            return pd.read_excel(buffer, header=None, engine="xlrd")
        except Exception:
            buffer.seek(0)
            texto = datos.decode("latin-1", errors="ignore")
            tablas = pd.read_html(io.StringIO(texto))
            if not tablas:
                raise ValueError(
                    "No se pudo interpretar el archivo como Excel ni como HTML"
                ) from None
            return tablas[0]


def _detectar_fecha(df: pd.DataFrame, nombre: str | None) -> str:
    if nombre:
        coincidencia = re.search(r"(20\d{2})(0[1-9]|1[0-2])", Path(nombre).name)
        if coincidencia:
            return f"{coincidencia.group(1)}-{coincidencia.group(2)}"
    for _, fila in df.head(8).iterrows():
        texto = normalizar(fila.iloc[0] if len(fila) else "")
        coincidencia = re.search(r"(\d{1,2}) DE ([A-Z]+) DE (20\d{2})", texto)
        if coincidencia and coincidencia.group(2) in MESES_ES:
            return f"{coincidencia.group(3)}-{MESES_ES[coincidencia.group(2)]:02d}"
    raise ValueError("No se pudo determinar la fecha del archivo BMU")


def _detectar_unidad(df: pd.DataFrame) -> tuple[str, float]:
    for _, fila in df.head(8).iterrows():
        texto = normalizar(fila.iloc[0] if len(fila) else "")
        if "EN MILES DE BOLIVIANOS" in texto:
            return "miles_de_bolivianos", 1.0
        if "EN BOLIVIANOS" in texto:
            return "bolivianos", 0.001
    return "miles_de_bolivianos", 1.0


def _detectar_encabezado(df: pd.DataFrame, codigos: set[str]) -> int:
    for indice in range(min(15, len(df))):
        valores = {normalizar(v) for v in df.iloc[indice].tolist() if normalizar(v)}
        if len(valores & codigos) >= min(5, len(codigos)):
            return indice
    raise ValueError("No se encontró la fila de encabezado con las siglas ASFI")


def _indice_etiqueta(df: pd.DataFrame, etiquetas: list[str]) -> int | None:
    objetivo = {normalizar(e) for e in etiquetas}
    for indice in range(len(df)):
        if normalizar(df.iat[indice, 0]) in objetivo:
            return indice
    return None


def _sumar_filas(
    df: pd.DataFrame, etiquetas: list[str], columna_por_codigo: dict[str, int]
) -> dict[str, float]:
    indices = [i for i in (_indice_etiqueta(df, [e]) for e in etiquetas) if i is not None]
    resultado: dict[str, float] = {}
    for codigo, columna in columna_por_codigo.items():
        if not indices:
            resultado[codigo] = float("nan")
            continue
        resultado[codigo] = float(sum(_a_numero(df.iat[i, columna]) for i in indices))
    return resultado


def _extraer_cuenta(
    df: pd.DataFrame, cuenta: str, columna_por_codigo: dict[str, int]
) -> dict[str, float]:
    if cuenta in {"cartera_mora", "obligaciones_corto_plazo"}:
        valores = _sumar_filas(df, ALIAS_CUENTAS[cuenta], columna_por_codigo)
        if cuenta == "cartera_mora" and all(pd.isna(v) for v in valores.values()):
            valores = _sumar_filas(df, ALIAS_RESPALDO[cuenta], columna_por_codigo)
        return valores
    indice = _indice_etiqueta(df, ALIAS_CUENTAS[cuenta])
    if indice is None:
        return {codigo: float("nan") for codigo in columna_por_codigo}
    return {
        codigo: _a_numero(df.iat[indice, columna]) for codigo, columna in columna_por_codigo.items()
    }


def parsear_bmu(
    fuente: str | Path | bytes | pd.DataFrame,
    config: dict,
    nombre_archivo: str | None = None,
) -> ResultadoParseo:
    """Parsea un archivo BMU y devuelve un panel largo por banco y mes."""
    df = _leer_dataframe(fuente)
    if df.empty:
        raise ValueError("El archivo BMU está vacío")

    mapa_codigos = {
        str(banco["codigo_asfi"]).upper(): banco["id"]
        for banco in config["bancos"]
        if banco.get("codigo_asfi")
    }
    encabezado = _detectar_encabezado(df, set(mapa_codigos))
    columna_por_codigo: dict[str, int] = {}
    for columna in range(1, df.shape[1]):
        celda = normalizar(df.iat[encabezado, columna])
        if celda in mapa_codigos:
            columna_por_codigo[celda] = columna
    if not columna_por_codigo:
        raise ValueError("Ninguna sigla del encabezado coincide con config.yaml")

    fecha = _detectar_fecha(df, nombre_archivo)
    unidad, factor = _detectar_unidad(df)

    filas: list[dict] = []
    for codigo, columna in columna_por_codigo.items():
        fila: dict[str, object] = {
            "fecha": fecha,
            "banco_id": mapa_codigos[codigo],
            "codigo_asfi": codigo,
        }
        for cuenta in CUENTAS_SALIDA:
            fila[cuenta] = _extraer_cuenta(df, cuenta, {codigo: columna})[codigo]
        if not pd.isna(fila["prevision_incobrables"]):
            fila["prevision_incobrables"] = abs(float(fila["prevision_incobrables"]))
        filas.append(fila)

    panel = pd.DataFrame(filas)
    for cuenta in CUENTAS_SALIDA:
        panel[cuenta] = panel[cuenta].astype(float) * factor

    diferencia = (panel["activo_total"] - (panel["pasivo_total"] + panel["patrimonio_total"])).abs()
    diferencia_max = float(diferencia.max()) if len(diferencia) else float("nan")

    return ResultadoParseo(
        panel=panel,
        fecha=fecha,
        unidad=unidad,
        factor_unidad=factor,
        codigos=sorted(columna_por_codigo),
        diferencia_identidad_max=diferencia_max,
    )
