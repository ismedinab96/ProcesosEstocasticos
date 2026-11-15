"""Descarga de series históricas mensuales usando plantillas ya verificadas.

No inventa rutas: toma las plantillas de `config.yaml → exploracion.fuentes_verificadas`,
descubiertas y validadas en la Compuerta 1.
"""

from __future__ import annotations

import argparse
import sys

import pandas as pd

from .configuracion import cargar_config
from .descargador import TareaDescarga, descargar

TIPOS = {
    "eeff": "Estados Financieros",
    "indicadores": "Indicadores Financieros",
    "evolutivo": "Evolutivos",
}


def _seleccionar_fuente(config: dict, tipo: str) -> dict:
    nombre_buscado = TIPOS[tipo]
    fuentes = (config.get("exploracion") or {}).get("fuentes_verificadas") or []
    for fuente in fuentes:
        nombre = fuente["nombre"]
        if nombre_buscado in nombre and "BDR" not in nombre:
            if tipo == "eeff" and "Evolutivos" in nombre:
                continue
            return fuente
    raise ValueError(
        f"No hay plantilla verificada para el tipo '{tipo}'. "
        "Revisa config.yaml → exploracion.fuentes_verificadas."
    )


def meses_entre(desde: str, hasta: str) -> list[tuple[str, str]]:
    """Devuelve [(AAAA, MM)] inclusivos entre dos meses YYYY-MM."""
    inicio = pd.Period(desde, freq="M")
    fin = pd.Period(hasta, freq="M")
    if fin < inicio:
        raise ValueError("El mes final no puede ser anterior al inicial")
    return [(str(p.year), f"{p.month:02d}") for p in pd.period_range(inicio, fin, freq="M")]


def construir_tareas(config: dict, tipo: str, desde: str, hasta: str) -> list[TareaDescarga]:
    fuente = _seleccionar_fuente(config, tipo)
    tareas = []
    for anio, mes in meses_entre(desde, hasta):
        url = fuente["url_template"].format(anio=anio, mes=mes)
        tareas.append(TareaDescarga(url=url, tipo_entidad=tipo))
    return tareas


def descargar_historico(
    tipo: str = "eeff",
    desde: str = "2021-01",
    hasta: str = "2025-12",
    permitir_otros: bool = False,
    verbose: bool = True,
) -> list:
    config = cargar_config()
    tareas = construir_tareas(config, tipo, desde, hasta)
    if verbose:
        print(f"[histórico] {tipo}: {len(tareas)} archivos ({desde} -> {hasta})")
    return descargar(tareas, permitir_otros=permitir_otros, verbose=verbose)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Descarga histórica mensual de ASFI")
    parser.add_argument("--tipo", choices=sorted(TIPOS), default="eeff")
    parser.add_argument("--desde", default="2021-01")
    parser.add_argument("--hasta", default="2025-12")
    parser.add_argument("--permitir-otros", action="store_true")
    parser.add_argument("--silencioso", action="store_true")
    args = parser.parse_args(argv)

    try:
        resultados = descargar_historico(
            tipo=args.tipo,
            desde=args.desde,
            hasta=args.hasta,
            permitir_otros=args.permitir_otros,
            verbose=not args.silencioso,
        )
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    descargados = sum(r.estado == "descargado" for r in resultados)
    omitidos = sum(r.estado == "omitido" for r in resultados)
    errores = [r for r in resultados if r.estado == "error"]
    print(
        f"Resumen histórico: {descargados} descargados, {omitidos} omitidos, {len(errores)} errores"
    )
    if errores:
        for r in errores[:10]:
            print(f"  - {r.url}: {r.detalle}")
        if len(errores) > 10:
            print(f"  ... y {len(errores) - 10} errores más")
    return 1 if len(errores) == len(resultados) else 0


if __name__ == "__main__":
    raise SystemExit(main())
