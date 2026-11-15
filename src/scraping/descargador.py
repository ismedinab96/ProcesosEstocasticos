"""Descargador resiliente de archivos de la ASFI con manifiesto SHA-256.

No contiene URLs cableadas: recibe las rutas ya validadas (por el script de
reconocimiento o por carga manual) y respeta la convención de nombres
`data/raw/{AAAA}/{MM}/{tipo_entidad}_{archivo}.{ext}`.
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import unquote, urlparse

from ..etl.deteccion import detectar_formato
from .cliente_http import ClienteHTTP, ResultadoDescarga
from .configuracion import cargar_config, ruta_raiz
from .manifiesto import Manifiesto

EXTENSIONES = {
    "xlsx": ".xlsx",
    "xls": ".xls",
    "html": ".xls",
    "zip": ".zip",
    "csv": ".csv",
    "pdf": ".pdf",
    "desconocido": ".bin",
}
PATRON_PERIODO = re.compile(r"(20\d{2})[/_-]?(\d{1,2})")
PATRON_YYYYMM = re.compile(r"(20\d{2})(0[1-9]|1[0-2])")


@dataclass
class TareaDescarga:
    url: str
    tipo_entidad: str = "eeff"
    destino_relativo: str | None = None


def _periodo_desde_url(url: str) -> tuple[str, str]:
    """Prioriza el período del nombre del archivo (YYYYMM) sobre la carpeta."""
    nombre = unquote(Path(urlparse(url).path).name)
    coincidencia_nombre = PATRON_YYYYMM.search(nombre)
    if coincidencia_nombre:
        return coincidencia_nombre.group(1), coincidencia_nombre.group(2)

    coincidencia = PATRON_PERIODO.search(url)
    if coincidencia:
        anio, mes = coincidencia.group(1), int(coincidencia.group(2))
        if 1 <= mes <= 12:
            return anio, f"{mes:02d}"
    ahora = datetime.now(UTC)
    return f"{ahora.year}", f"{ahora.month:02d}"


def _nombre_limpio(url: str) -> str:
    ruta = unquote(urlparse(url).path)
    nombre = Path(ruta).name
    nombre = re.sub(r"[^A-Za-z0-9._-]+", "_", nombre).strip("._")
    return nombre or "archivo"


def _destino(base: Path, tarea: TareaDescarga) -> Path:
    if tarea.destino_relativo:
        return base / tarea.destino_relativo
    anio, mes = _periodo_desde_url(tarea.url)
    nombre = _nombre_limpio(tarea.url)
    tallo = Path(nombre).stem
    sufijo = Path(nombre).suffix or ".bin"
    return base / anio / mes / f"{tarea.tipo_entidad}_{tallo}{sufijo}"


def _validar_host(url: str, permitir_otros: bool) -> None:
    host = urlparse(url).hostname or ""
    esquema = urlparse(url).scheme
    if esquema not in {"http", "https"}:
        raise ValueError(f"URL no soportada: {url}")
    if not permitir_otros and "asfi.gob.bo" not in host:
        raise ValueError(
            f"Por seguridad solo se descargan hosts *.asfi.gob.bo (recibido: {host}). "
            "Usa --permitir-otros si es intencional."
        )


def descargar(
    tareas: list[TareaDescarga],
    permitir_otros: bool = False,
    verbose: bool = True,
) -> list[ResultadoDescarga]:
    config = cargar_config()
    base = ruta_raiz()
    scraping = config["scraping"]
    manifiesto = Manifiesto(base / scraping["directorio_cache"] / "manifest.csv")
    cliente = ClienteHTTP(scraping, manifiesto=manifiesto)

    resultados: list[ResultadoDescarga] = []
    for tarea in tareas:
        _validar_host(tarea.url, permitir_otros)
        destino = _destino(base / scraping["directorio_cache"], tarea)
        if verbose:
            print(f"[descarga] {tarea.url} -> {destino.relative_to(base)}")
        resultado = cliente.descargar(tarea.url, destino)
        if resultado.estado == "descargado" and resultado.ruta_local is not None:
            formato = detectar_formato(resultado.ruta_local, resultado.ruta_local.name)
            extension = EXTENSIONES.get(formato, resultado.ruta_local.suffix)
            if resultado.ruta_local.suffix.lower() != extension:
                final = resultado.ruta_local.with_suffix(extension)
                resultado.ruta_local.replace(final)
                resultado.ruta_local = final
                if resultado.sha256:
                    manifiesto.actualizar_ruta(
                        resultado.sha256, final, status=f"descargado:{formato}"
                    )
            resultado.detalle = f"formato detectado: {formato}"
        resultados.append(resultado)
        if verbose:
            detalle = f" ({resultado.detalle})" if resultado.detalle else ""
            print(f"[descarga]   estado={resultado.estado}{detalle}")
    return resultados


def _leer_lista(ruta: str | Path) -> list[TareaDescarga]:
    tareas: list[TareaDescarga] = []
    for linea in Path(ruta).read_text(encoding="utf-8").splitlines():
        limpia = linea.strip()
        if not limpia or limpia.startswith("#"):
            continue
        partes = [parte.strip() for parte in limpia.split(",")]
        destino = partes[2] if len(partes) >= 3 and partes[2] else None
        tareas.append(
            TareaDescarga(
                url=partes[0],
                tipo_entidad=partes[1] if len(partes) >= 2 and partes[1] else "eeff",
                destino_relativo=destino,
            )
        )
    return tareas


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Descarga resiliente de archivos ASFI")
    parser.add_argument("--url", action="append", default=[], help="URL a descargar (repetible)")
    parser.add_argument("--lista", type=str, default=None, help="Archivo CSV: url,tipo,destino")
    parser.add_argument(
        "--permitir-otros",
        action="store_true",
        help="Permite hosts distintos de asfi.gob.bo (desactivado por seguridad)",
    )
    parser.add_argument("--silencioso", action="store_true", help="Oculta el progreso")
    args = parser.parse_args(argv)

    tareas = [TareaDescarga(url=url) for url in args.url]
    if args.lista:
        tareas.extend(_leer_lista(args.lista))
    if not tareas:
        print(
            "No se recibieron URLs. Este descargador NO adivina rutas de la ASFI.\n"
            "Opciones:\n"
            "  a) Ejecuta antes: python -m src.scraping.reconocimiento\n"
            "  b) Pasa una lista validada: python -m src.scraping.descargador --lista urls.txt\n"
            "  c) Coloca archivos manualmente en data/raw/ siguiendo la convención.",
            file=sys.stderr,
        )
        return 2

    resultados = descargar(tareas, permitir_otros=args.permitir_otros, verbose=not args.silencioso)
    errores = [r for r in resultados if r.estado == "error"]
    print(
        f"Resumen: {sum(r.estado == 'descargado' for r in resultados)} descargados, "
        f"{sum(r.estado == 'omitido' for r in resultados)} omitidos (caché), "
        f"{len(errores)} errores."
    )
    return 1 if errores else 0


if __name__ == "__main__":
    raise SystemExit(main())
