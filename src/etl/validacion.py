"""Validaciones duras del panel contable: identidad, signos, duplicados y cobertura."""

from __future__ import annotations

import numpy as np
import pandas as pd


def validar_identidad(panel: pd.DataFrame, tolerancia: float = 1.0) -> pd.DataFrame:
    """Comprueba |Activo - (Pasivo + Patrimonio)| <= tolerancia (miles de BOB)."""
    requeridas = {"fecha", "banco_id", "activo_total", "pasivo_total", "patrimonio_total"}
    faltantes = requeridas - set(panel.columns)
    if faltantes:
        raise ValueError(f"Faltan columnas para la identidad contable: {sorted(faltantes)}")
    suma = panel["pasivo_total"] + panel["patrimonio_total"]
    diferencia = (panel["activo_total"] - suma).abs()
    return pd.DataFrame(
        {
            "fecha": panel["fecha"],
            "banco_id": panel["banco_id"],
            "activo_total": panel["activo_total"],
            "pasivo_mas_patrimonio": suma,
            "diferencia": diferencia,
            "cumple": diferencia <= tolerancia,
        }
    )


def violaciones_positivas(panel: pd.DataFrame) -> pd.DataFrame:
    """Detecta cuentas que deben ser estrictamente positivas y no lo son."""
    cuentas_positivas = [
        "activo_total",
        "pasivo_total",
        "patrimonio_total",
        "cartera_bruta",
        "depositos",
        "obligaciones_corto_plazo",
    ]
    registros: list[dict] = []
    for cuenta in cuentas_positivas:
        if cuenta not in panel.columns:
            continue
        invalidos = panel[panel[cuenta].notna() & (panel[cuenta] <= 0)]
        for _, fila in invalidos.iterrows():
            registros.append(
                {
                    "fecha": fila["fecha"],
                    "banco_id": fila["banco_id"],
                    "cuenta": cuenta,
                    "valor": fila[cuenta],
                }
            )
    return pd.DataFrame(registros)


def duplicados(panel: pd.DataFrame) -> pd.DataFrame:
    mascara = panel.duplicated(subset=["fecha", "banco_id"], keep=False)
    return panel.loc[mascara, ["fecha", "banco_id"]].sort_values(["banco_id", "fecha"])


def resumen_cobertura(panel: pd.DataFrame, meses_minimos: int = 60) -> pd.DataFrame:
    """Cobertura mensual por banco, incluyendo huecos internos."""
    filas: list[dict] = []
    for banco, grupo in panel.groupby("banco_id", sort=True):
        fechas = pd.PeriodIndex(sorted(grupo["fecha"].unique()), freq="M")
        if len(fechas) == 0:
            continue
        esperados = len(pd.period_range(fechas.min(), fechas.max(), freq="M"))
        observados = len(fechas)
        filas.append(
            {
                "banco_id": banco,
                "observaciones": observados,
                "primer_mes": str(fechas.min()),
                "ultimo_mes": str(fechas.max()),
                "meses_esperados": esperados,
                "huecos": esperados - observados,
                "cobertura_pct": round(100 * observados / esperados, 2),
                "apta_para_modelado": observados >= meses_minimos,
            }
        )
    return pd.DataFrame(filas).sort_values("banco_id").reset_index(drop=True)


def resumen_indicadores(panel_largo: pd.DataFrame) -> pd.DataFrame:
    """Estadísticos descriptivos por indicador con conteo de valores válidos."""
    if panel_largo.empty:
        return pd.DataFrame()
    resumen = (
        panel_largo.groupby("indicador_id")["valor"]
        .agg(
            observaciones_validas=lambda s: int(s.notna().sum()),
            faltantes=lambda s: int(s.isna().sum()),
            media="mean",
            desv_est="std",
            minimo="min",
            maximo="max",
        )
        .reset_index()
    )
    return resumen.round(4)


def resumen_identidad(tabla: pd.DataFrame) -> dict[str, float | int]:
    if tabla.empty:
        return {"registros": 0, "fallos": 0, "diferencia_max": float("nan")}
    return {
        "registros": int(len(tabla)),
        "fallos": int((~tabla["cumple"]).sum()),
        "diferencia_max": float(np.nanmax(tabla["diferencia"].to_numpy())),
    }
