"""Validación del contrato con Pydantic y exportación a data.json / data.js."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from ..models.utilidades import a_primitivo
from ..scraping.configuracion import ruta_raiz
from .esquema import Contrato


def validar_contrato(datos: dict) -> Contrato:
    return Contrato.model_validate(a_primitivo(datos))


def exportar(
    datos: dict,
    salida_json: str | Path = "dashboard/data.json",
    salida_js: str | Path = "dashboard/data.js",
    validar: bool = True,
) -> dict[str, Path]:
    contrato = validar_contrato(datos) if validar else None
    limpio = a_primitivo(contrato.model_dump() if contrato else datos)
    texto = json.dumps(limpio, ensure_ascii=False, allow_nan=False, separators=(",", ":"))

    raiz = ruta_raiz()
    ruta_json = Path(salida_json)
    ruta_js = Path(salida_js)
    if not ruta_json.is_absolute():
        ruta_json = raiz / ruta_json
    if not ruta_js.is_absolute():
        ruta_js = raiz / ruta_js
    ruta_json.parent.mkdir(parents=True, exist_ok=True)
    ruta_js.parent.mkdir(parents=True, exist_ok=True)

    ruta_json.write_text(json.dumps(limpio, ensure_ascii=False, indent=2), encoding="utf-8")
    ruta_js.write_text("window.ASFI_DATA = " + texto + ";\n", encoding="utf-8")
    return {"json": ruta_json, "js": ruta_js}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Valida y reexporta el contrato del dashboard")
    parser.add_argument("--entrada", default="dashboard/data.json")
    parser.add_argument("--salida-json", default="dashboard/data.json")
    parser.add_argument("--salida-js", default="dashboard/data.js")
    args = parser.parse_args(argv)

    ruta = Path(args.entrada)
    if not ruta.is_absolute():
        ruta = ruta_raiz() / ruta
    if not ruta.exists():
        print(f"ERROR: no existe {ruta}. Ejecuta antes `python -m src.models.pipeline`.")
        return 2
    datos = json.loads(ruta.read_text(encoding="utf-8"))
    rutas = exportar(datos, args.salida_json, args.salida_js, validar=True)
    print(f"Contrato v?lido: {rutas['json']}")
    print(f"JS: {rutas['js']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
