"""Carga centralizada de la configuración del proyecto."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml


def ruta_raiz() -> Path:
    """Devuelve la raíz del proyecto (carpeta contenedora de config.yaml)."""
    return Path(__file__).resolve().parents[2]


def ruta_config() -> Path:
    return ruta_raiz() / "config.yaml"


@lru_cache(maxsize=1)
def cargar_config(ruta: str | Path | None = None) -> dict[str, Any]:
    """Carga config.yaml y valida claves mínimas."""
    destino = Path(ruta) if ruta is not None else ruta_config()
    if not destino.exists():
        raise FileNotFoundError(f"No se encontró el archivo de configuración: {destino}")
    with destino.open("r", encoding="utf-8") as fh:
        datos = yaml.safe_load(fh) or {}
    for clave in ("general", "scraping", "bancos", "indicadores", "markov", "sarima", "alertas"):
        if clave not in datos:
            raise ValueError(f"Falta la sección obligatoria '{clave}' en {destino}")
    return datos


def ruta_datos(*partes: str) -> Path:
    """Resuelve una ruta dentro de data/ y crea el directorio padre."""
    destino = ruta_raiz() / "data" / Path(*partes)
    destino.parent.mkdir(parents=True, exist_ok=True)
    return destino
