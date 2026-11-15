"""Utilidades compartidas del motor estocástico (limpieza y serialización JSON)."""

from __future__ import annotations

import math
from typing import Any

import numpy as np
import pandas as pd


def a_primitivo(obj: Any) -> Any:
    """Convierte numpy/pandas y NaN/inf a tipos JSON estrictos."""
    if isinstance(obj, dict):
        return {str(k): a_primitivo(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [a_primitivo(v) for v in obj]
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating, float)):
        valor = float(obj)
        return valor if math.isfinite(valor) else None
    if isinstance(obj, (np.bool_,)):
        return bool(obj)
    if obj is pd.NaT:
        return None
    if isinstance(obj, pd.Timestamp):
        return obj.isoformat()
    return obj


def limpiar_serie(
    fechas: list[str],
    valores: list[float],
    meses_minimos: int = 60,
    max_hueco: int = 2,
) -> dict:
    """Recorta extremos, interpola huecos cortos y trunca huecos largos.

    Devuelve fechas/valores limpios y un diagnóstico del tratamiento aplicado.
    """
    serie = pd.Series(valores, index=pd.PeriodIndex(fechas, freq="M"), dtype=float)
    serie = serie.dropna()
    if serie.empty:
        return {
            "fechas": [],
            "valores": [],
            "estado": "sin_datos",
            "huecos_interpolados": 0,
            "meses_truncados": 0,
        }

    completo = serie.reindex(pd.period_range(serie.index.min(), serie.index.max(), freq="M"))
    faltantes = completo.isna()
    interpolar = int(faltantes.sum())
    if interpolar:
        huecos = _huecos_consecutivos(faltantes)
        if huecos and max(huecos) > max_hueco:
            completo = _tramo_continuo_mas_reciente(completo)
            interpolar = 0
        else:
            completo = completo.interpolate(method="linear", limit=max_hueco, limit_area="inside")

    limpio = completo.dropna()
    return {
        "fechas": [str(p) for p in limpio.index],
        "valores": [float(v) for v in limpio.to_numpy()],
        "estado": "ok" if len(limpio) >= meses_minimos else "insuficiente",
        "huecos_interpolados": interpolar,
        "meses_truncados": int(serie.index.min() != limpio.index.min())
        + int(serie.index.max() != limpio.index.max()),
    }


def _huecos_consecutivos(faltantes: pd.Series) -> list[int]:
    longitudes: list[int] = []
    actual = 0
    for valor in faltantes.to_numpy():
        if valor:
            actual += 1
        elif actual:
            longitudes.append(actual)
            actual = 0
    if actual:
        longitudes.append(actual)
    return longitudes


def _tramo_continuo_mas_reciente(serie: pd.Series) -> pd.Series:
    bloques: list[pd.Series] = []
    bloque: list[float] = []
    indices: list[pd.Period] = []
    for periodo, valor in serie.items():
        if pd.isna(valor):
            if bloque:
                bloques.append(pd.Series(bloque, index=indices, dtype=float))
                bloque, indices = [], []
        else:
            bloque.append(float(valor))
            indices.append(periodo)
    if bloque:
        bloques.append(pd.Series(bloque, index=indices, dtype=float))
    return bloques[-1] if bloques else serie
