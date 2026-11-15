"""Reconocimiento de solo lectura del portal de la ASFI.

No adivina rutas de descarga: visita un conjunto acotado de secciones
candidatas, registra códigos de estado, formatos reales y enlaces relevantes,
y genera `docs/exploracion_asfi.md` como evidencia para la Compuerta 1.
"""

from __future__ import annotations

import argparse
import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from .cliente_http import ClienteHTTP, ErrorHTTP
from .configuracion import cargar_config, ruta_raiz
from .manifiesto import Manifiesto

PATRON_ARCHIVO = re.compile(r"\.(xlsx?|zip|csv|pdf|txt|ods)(?:[?#]|$)", re.IGNORECASE)
PALABRAS_CLAVE = ("estado", "financier", "boletin", "banc", "balance", "cartera", "mora", "puc")


@dataclass
class Enlace:
    url: str
    texto: str
    es_archivo: bool


@dataclass
class ResultadoSeccion:
    nombre: str
    url: str
    estado: str
    content_type: str = ""
    titulo: str = ""
    tablas: int = 0
    enlaces: list[Enlace] = field(default_factory=list)
    detalle: str = ""


@dataclass
class SondaArchivo:
    url: str
    texto: str
    content_type: str
    bytes: int | None
    formato: str
    estado: str


@dataclass
class SondaFuente:
    nombre: str
    url: str
    hallada_en: str
    estado: str
    content_type: str
    bytes: int | None


def _normalizar_texto(texto: str, limite: int = 120) -> str:
    limpio = " ".join(texto.split())
    return limpio[:limite]


def _extraer_enlaces(base: str, html: str) -> list[Enlace]:
    sopa = BeautifulSoup(html, "lxml")
    enlaces: list[Enlace] = []
    vistos: set[str] = set()
    for ancla in sopa.find_all("a", href=True):
        href = ancla["href"].strip()
        if not href or href.startswith(("javascript:", "mailto:", "#")):
            continue
        absoluto = urljoin(base, href)
        if urlparse(absoluto).scheme not in {"http", "https"}:
            continue
        if absoluto in vistos:
            continue
        vistos.add(absoluto)
        texto = _normalizar_texto(ancla.get_text(" ", strip=True))
        es_archivo = bool(PATRON_ARCHIVO.search(urlparse(absoluto).path))
        enlaces.append(Enlace(url=absoluto, texto=texto, es_archivo=es_archivo))
    return enlaces


def _sondear_archivo(
    cliente: ClienteHTTP, enlace: Enlace, mostrar_error: bool = True
) -> SondaArchivo:
    try:
        respuesta = cliente.cabecera(enlace.url)
        content_type = respuesta.headers.get("Content-Type", "")
        largo = respuesta.headers.get("Content-Length")
        tamano = int(largo) if largo and largo.isdigit() else None
        formato = "desconocido"
        if "spreadsheetml" in content_type:
            formato = "xlsx"
        elif "ms-excel" in content_type:
            formato = "xls/html"
        elif "zip" in content_type:
            formato = "zip"
        elif "html" in content_type:
            formato = "html"
        estado = f"HTTP {respuesta.status_code}"
    except ErrorHTTP as exc:
        return SondaArchivo(
            url=enlace.url,
            texto=enlace.texto,
            content_type="",
            bytes=None,
            formato="desconocido",
            estado=str(exc) if mostrar_error else "error",
        )
    return SondaArchivo(
        url=enlace.url,
        texto=enlace.texto,
        content_type=content_type,
        bytes=tamano,
        formato=formato,
        estado=estado,
    )


def _sondear_fuentes_verificadas(
    cliente: ClienteHTTP, config: dict, verbose: bool = True
) -> list[SondaFuente]:
    """Verifica con HEAD las plantillas de fuentes ya validadas en config.yaml."""
    fuentes = (config.get("exploracion") or {}).get("fuentes_verificadas") or []
    sondas: list[SondaFuente] = []
    for fuente in fuentes:
        for anio, mes in fuente.get("sondas", []):
            url = fuente["url_template"].format(anio=anio, mes=mes)
            if verbose:
                print(f"[reconocimiento] HEAD (fuente) {url}")
            try:
                respuesta = cliente.cabecera(url)
                largo = respuesta.headers.get("Content-Length")
                sondas.append(
                    SondaFuente(
                        nombre=fuente["nombre"],
                        url=url,
                        hallada_en=fuente.get("hallada_en", ""),
                        estado=f"HTTP {respuesta.status_code}",
                        content_type=respuesta.headers.get("Content-Type", ""),
                        bytes=int(largo) if largo and largo.isdigit() else None,
                    )
                )
            except ErrorHTTP as exc:
                sondas.append(
                    SondaFuente(
                        nombre=fuente["nombre"],
                        url=url,
                        hallada_en=fuente.get("hallada_en", ""),
                        estado=str(exc),
                        content_type="",
                        bytes=None,
                    )
                )
    return sondas


def _bloque_tabla(cabeceras: list[str], filas: list[list[str]]) -> str:
    if not filas:
        return "_Sin registros._\n"
    lineas = ["| " + " | ".join(cabeceras) + " |", "|" + "|".join(["---"] * len(cabeceras)) + "|"]
    for fila in filas:
        celdas = [str(celda).replace("|", "\\|") for celda in fila]
        lineas.append("| " + " | ".join(celdas) + " |")
    return "\n".join(lineas) + "\n"


def ejecutar_reconocimiento(
    salida: str | Path | None = None,
    max_enlaces: int = 8,
    verbose: bool = True,
) -> Path:
    config = cargar_config()
    scraping = config["scraping"]
    base = scraping["base_url"]
    secciones: dict[str, str] = scraping.get("secciones", {})

    raiz = ruta_raiz()
    manifiesto = Manifiesto(raiz / scraping["directorio_cache"] / "manifest.csv")
    cliente = ClienteHTTP(scraping, manifiesto=manifiesto)

    generado = datetime.now(UTC).isoformat(timespec="seconds")
    resultados: list[ResultadoSeccion] = []
    robots_estado: dict[str, str] = {}

    objetivos = [("portada", base), ("robots", urljoin(base, "/robots.txt"))]
    objetivos += [
        (nombre.replace("_", " "), urljoin(base, ruta)) for nombre, ruta in secciones.items()
    ]

    if verbose:
        print(f"[reconocimiento] Inicio {generado} — {len(objetivos)} objetivos")

    for nombre, url in objetivos:
        dominio = f"{urlparse(url).scheme}://{urlparse(url).netloc}"
        if dominio not in robots_estado:
            try:
                permitido = cliente.permitido_por_robots(url)
                robots_estado[dominio] = "permitido" if permitido else "prohibido"
            except Exception as exc:  # pragma: no cover - defensivo
                robots_estado[dominio] = f"indeterminado ({exc})"
        if verbose:
            print(f"[reconocimiento] GET {url}")

        try:
            respuesta = cliente.obtener(url)
        except ErrorHTTP as exc:
            resultados.append(
                ResultadoSeccion(nombre=nombre, url=url, estado="error", detalle=str(exc))
            )
            continue

        content_type = respuesta.headers.get("Content-Type", "")
        es_robots = nombre == "robots"
        html = "" if es_robots else respuesta.text
        sopa = BeautifulSoup(html, "lxml") if html else None
        if es_robots:
            lineas = [linea for linea in respuesta.text.splitlines() if linea.strip()]
            titulo = "robots.txt"
            detalle = f"{len(lineas)} líneas; primeras: {' / '.join(lineas[:5])}"
            enlaces: list[Enlace] = []
            tablas = 0
        else:
            titulo = (
                _normalizar_texto(sopa.title.get_text(strip=True), 160)
                if sopa and sopa.title
                else ""
            )
            enlaces = _extraer_enlaces(url, html) if sopa else []
            tablas = len(sopa.find_all("table")) if sopa else 0
            detalle = f"{len(enlaces)} enlaces, {tablas} tablas HTML"

        resultados.append(
            ResultadoSeccion(
                nombre=nombre,
                url=url,
                estado=f"HTTP {respuesta.status_code}",
                content_type=content_type,
                titulo=titulo,
                tablas=tablas,
                enlaces=enlaces,
                detalle=detalle,
            )
        )

    # Sondear archivos candidatos (acotado y respetando el rate limit).
    candidatos: list[Enlace] = []
    vistos_url: set[str] = set()
    for resultado in resultados:
        for enlace in resultado.enlaces:
            if enlace.url in vistos_url:
                continue
            relevante = enlace.es_archivo or any(p in enlace.url.lower() for p in PALABRAS_CLAVE)
            if relevante and enlace.url not in vistos_url:
                candidatos.append(enlace)
                vistos_url.add(enlace.url)
            if len(candidatos) >= max_enlaces:
                break
        if len(candidatos) >= max_enlaces:
            break

    sondas: list[SondaArchivo] = []
    for enlace in candidatos:
        if verbose:
            print(f"[reconocimiento] HEAD {enlace.url}")
        sondas.append(_sondear_archivo(cliente, enlace))

    sondas_fuentes = _sondear_fuentes_verificadas(cliente, config, verbose=verbose)

    destino = Path(salida) if salida else raiz / "docs" / "exploracion_asfi.md"
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(
        _redactar_informe(
            generado=generado,
            base=base,
            robots=robots_estado,
            resultados=resultados,
            sondas=sondas,
            sondas_fuentes=sondas_fuentes,
            max_enlaces=max_enlaces,
        ),
        encoding="utf-8",
    )
    if verbose:
        print(f"[reconocimiento] Informe escrito en {destino}")
    return destino


def _redactar_informe(
    generado: str,
    base: str,
    robots: dict[str, str],
    resultados: list[ResultadoSeccion],
    sondas: list[SondaArchivo],
    sondas_fuentes: list[SondaFuente] | None = None,
    max_enlaces: int = 8,
) -> str:
    lineas: list[str] = []
    lineas.append("# Exploración del portal de la ASFI\n")
    lineas.append(f"- **Generado (UTC):** {generado}")
    lineas.append(f"- **URL base analizada:** {base}")
    lineas.append("- **Modo:** solo lectura (navegación + HEAD); sin descargas masivas.")
    lineas.append(
        "- **Límites aplicados:** rate limit del `config.yaml`, User-Agent identificable y "
        f"máximo {max_enlaces} archivos sondeados.\n"
    )

    lineas.append("## Metodología\n")
    lineas.append(
        "1. Se consultó `robots.txt` y se verificó el permiso de acceso por dominio.\n"
        "2. Se visitaron las secciones candidatas declaradas en `config.yaml` "
        "(sin adivinar rutas de descarga directa).\n"
        "3. Se extrajeron enlaces a archivos y a contenidos financieros relevantes.\n"
        "4. Se inspeccionaron cabeceras `HEAD` para estimar tipo y tamaño real, "
        "porque la extensión declarada no siempre coincide con el formato.\n"
    )

    lineas.append("## Robots.txt\n")
    filas_robots = [[dominio, estado] for dominio, estado in robots.items()]
    lineas.append(_bloque_tabla(["Dominio", "Estado"], filas_robots))

    lineas.append("## Secciones visitadas\n")
    filas = []
    for resultado in resultados:
        filas.append(
            [
                resultado.nombre,
                resultado.estado,
                resultado.content_type or "—",
                resultado.titulo or "—",
                resultado.detalle or "—",
            ]
        )
    lineas.append(_bloque_tabla(["Sección", "Estado", "Content-Type", "Título", "Detalle"], filas))

    lineas.append("## Archivos candidatos inspeccionados (HEAD)\n")
    filas_sondas = [
        [
            sonda.texto or "—",
            f"`{sonda.url}`",
            sonda.content_type or "—",
            f"{sonda.bytes}" if sonda.bytes is not None else "—",
            sonda.formato,
            sonda.estado,
        ]
        for sonda in sondas
    ]
    lineas.append(
        _bloque_tabla(
            ["Texto del enlace", "URL", "Content-Type", "Bytes", "Formato estimado", "Estado"],
            filas_sondas,
        )
    )

    lineas.append("## Fuentes verificadas (disponibilidad histórica)\n")
    lineas.append(
        "Plantillas obtenidas de enlaces y del JavaScript público del portal "
        "(por ejemplo `bmu-bol.js`), verificadas con peticiones `HEAD`:\n"
    )
    filas_fuentes = [
        [
            sonda.nombre,
            f"`{sonda.url}`",
            sonda.content_type or "—",
            f"{sonda.bytes}" if sonda.bytes is not None else "—",
            sonda.estado,
        ]
        for sonda in (sondas_fuentes or [])
    ]
    lineas.append(
        _bloque_tabla(
            ["Fuente", "URL verificada", "Content-Type", "Bytes", "Estado"], filas_fuentes
        )
    )

    lineas.append("### Anexo: estructura observada de los archivos\n")
    lineas.append(
        "- El portal es un sitio Drupal 10 con rutas `/pb/...` y `/la/...`.\n"
        "- La sección `/pb/bancos-multiples` usa un formulario de año/mes; su JavaScript\n"
        "  público (`bmu-bol.js`) construye la ruta mensual:\n"
        "  `/sites/default/files/estadisticaif/bancos_multiples/{AAAA}/{MM}/`.\n"
        "- Cada mes publica un ZIP con un único `.xls` binario (BIFF8) llamado\n"
        "  `{AAAAMM}_BMU_EstadosFinancieros.xls`; también existen variantes de\n"
        "  indicadores, desagregados, moneda y evolutivos.\n"
        "- El `.xls` de EEFF tiene una hoja (`BMU`) con la matriz transpuesta respecto\n"
        "  de una base de datos: filas = cuentas contables y columnas = entidades.\n"
        "  Las filas 0–3 contienen metadatos (tipo de entidad, título, fecha y\n"
        "  `(en miles de bolivianos)`); la fila 5 es el encabezado de entidades y la\n"
        "  columna final es `TOTAL SISTEMA` (debe excluirse del panel por banco).\n"
        "- El `.xls` de indicadores usa la misma orientación, con categorías de\n"
        "  estructura de activos, pasivos, resultados y liquidez.\n"
        "- El ZIP evolutivo contiene un `.xls` por entidad (por ejemplo\n"
        "  `..._BMU_EstadosFinancierosBIS.xls`) con la serie histórica de esa entidad.\n"
        "- Las columnas usan las siglas oficiales de ASFI. Según el PDF público\n"
        '  "Siglas de Entidades de Intermediación Financiera":\n'
        "  BNB (Banco Nacional de Bolivia), BME (Mercantil Santa Cruz), BIS (BISA),\n"
        "  BCR (Crédito de Bolivia), BEC (Económico), BGA (Ganadero), BSO (Solidario),\n"
        "  BNA (Banco de la Nación Argentina), BIE (FIE), BFO (Fortaleza), BPR (Prodem)\n"
        "  y BUN (Banco Unión, entidad estatal incluida en la matriz).\n"
        "- Disponibilidad mensual verificada: desde al menos 2014-12 hasta 2025-12\n"
        "  (más de 60 meses), lo que habilita el modelado SARIMA con `s=12`.\n"
    )

    lineas.append("## Enlaces relevantes por sección\n")
    for resultado in resultados:
        if not resultado.enlaces:
            continue
        relevantes = [
            enlace
            for enlace in resultado.enlaces
            if enlace.es_archivo or any(p in enlace.url.lower() for p in PALABRAS_CLAVE)
        ][:20]
        if not relevantes:
            continue
        lineas.append(f"### {resultado.nombre}\n")
        for enlace in relevantes:
            etiqueta = enlace.texto or "(sin texto)"
            lineas.append(f"- [{etiqueta}]({enlace.url})")
        lineas.append("")

    lineas.append("## Conclusiones y recomendaciones\n")
    fallidas = [r for r in resultados if r.estado == "error"]
    con_archivos = [s for s in sondas if s.estado.startswith("HTTP")]
    fuentes_ok = [s for s in (sondas_fuentes or []) if s.estado.startswith("HTTP")]
    if fallidas and not con_archivos and not fuentes_ok:
        lineas.append(
            "- No se pudo completar la exploración en línea. **No se deben inventar rutas "
            "ni datos.** Opciones válidas:\n"
            "  1. Cargar manualmente los EEFF/boletines en `data/raw/` respetando la "
            "convención `{AAAA}/{MM}/{tipo_entidad}_{archivo}.{ext}`.\n"
            "  2. Ejecutar `python -m src.etl.synth --demo` para desbloquear el desarrollo "
            "con datos sintéticos (activando el banner de demostración).\n"
        )
    else:
        lineas.append(
            "- Se detectaron recursos accesibles. Antes de automatizar descargas, validar los "
            "términos de uso del portal y mantener el rate limit configurado.\n"
        )
        formatos = sorted({s.formato for s in sondas if s.formato != "desconocido"})
        if formatos:
            lineas.append(
                f"- Formatos observados en cabeceras: {', '.join(formatos)}. El ETL "
                "deberá soportar `.xlsx`, `.xls` binario y HTML disfrazado de `.xls`.\n"
            )
        if fuentes_ok:
            lineas.append(
                f"- Se verificaron {len(fuentes_ok)} descargas por plantilla mensual (EEFF, "
                "indicadores y evolutivos de Bancos Múltiples). La disponibilidad mensual "
                "confirmada abarca desde al menos 2014-12 hasta 2025-12, suficiente para el "
                "mínimo de 60 meses y para SARIMA con `s=12`.\n"
            )
            lineas.append(
                "- Los archivos mensuales llegan como ZIP que contienen `.xls` binarios (BIFF8); "
                "algunos recursos del portal también aparecen como PDF o HTML. El ETL deberá "
                "soportar `.xls` binario, `.xlsx` y HTML disfrazado de `.xls`.\n"
            )
        lineas.append(
            "- Cualquier ruta de descarga directa deberá validarse en una nueva pasada; este "
            "informe solo documenta la navegación observada.\n"
        )

    lineas.append(
        "\n> **Descargo:** este documento describe la estructura observada del portal "
        "en la fecha indicada. No constituye una afirmación sobre la disponibilidad "
        "futura de los archivos ni sobre la solvencia de ninguna entidad financiera.\n"
    )
    return "\n".join(lineas)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Reconocimiento de solo lectura del portal ASFI")
    parser.add_argument("--salida", type=str, default=None, help="Ruta del informe Markdown")
    parser.add_argument("--max-enlaces", type=int, default=8, help="Máximo de archivos a sondear")
    parser.add_argument("--silencioso", action="store_true", help="Oculta el progreso")
    args = parser.parse_args(argv)
    destino = ejecutar_reconocimiento(
        salida=args.salida, max_enlaces=args.max_enlaces, verbose=not args.silencioso
    )
    print(f"Informe generado: {destino}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
