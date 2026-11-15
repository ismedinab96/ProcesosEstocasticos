"""Motor de cálculo de indicadores financieros a partir del panel contable.

Convención de flujos: la Utilidad Neta de ASFI se reporta acumulada desde enero
hasta el mes t. Para obtener un flujo mensual se aplica ΔU_t = U_t - U_{t-1}
para t > enero; en enero el flujo es igual al valor acumulado del mes. Luego se
anualiza con suma móvil de 12 meses y se divide entre el promedio móvil de 12
meses del Activo o Patrimonio. Los ratios se expresan en porcentaje.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

INDICADORES = [
    "mora",
    "cobertura",
    "liquidez",
    "roa",
    "roe",
    "crec_cartera",
    "crec_depositos",
]


def _dividir(numerador: pd.Series, denominador: pd.Series) -> pd.Series:
    resultado = numerador / denominador.replace(0, np.nan)
    return resultado.replace([np.inf, -np.inf], np.nan)


def calcular_indicadores(panel: pd.DataFrame) -> pd.DataFrame:
    """Devuelve un panel largo (fecha, banco_id, indicador_id, valor)."""
    requeridas = {
        "fecha",
        "banco_id",
        "activo_total",
        "patrimonio_total",
        "cartera_bruta",
        "cartera_mora",
        "prevision_incobrables",
        "disponibilidades",
        "inversiones_temporarias",
        "obligaciones_corto_plazo",
        "utilidad_neta",
        "depositos",
    }
    faltantes = requeridas - set(panel.columns)
    if faltantes:
        raise ValueError(f"Faltan columnas contables: {sorted(faltantes)}")

    df = panel.copy()
    df["fecha"] = df["fecha"].astype(str)
    df = df.sort_values(["banco_id", "fecha"]).reset_index(drop=True)
    df["mes"] = df["fecha"].str[5:7].astype(int)

    grupos = df.groupby("banco_id", sort=False)
    utilidad_previa = grupos["utilidad_neta"].shift(1)
    df["flujo_utilidad"] = np.where(
        df["mes"] == 1, df["utilidad_neta"], df["utilidad_neta"] - utilidad_previa
    )

    por_banco = df.groupby("banco_id", sort=False)
    df["utilidad_anualizada"] = por_banco["flujo_utilidad"].transform(
        lambda s: s.rolling(12, min_periods=12).sum()
    )
    df["activo_promedio"] = por_banco["activo_total"].transform(
        lambda s: s.rolling(12, min_periods=12).mean()
    )
    df["patrimonio_promedio"] = por_banco["patrimonio_total"].transform(
        lambda s: s.rolling(12, min_periods=12).mean()
    )

    df["mora"] = _dividir(df["cartera_mora"], df["cartera_bruta"]) * 100
    df["cobertura"] = _dividir(df["prevision_incobrables"], df["cartera_mora"]) * 100
    df["liquidez"] = (
        _dividir(
            df["disponibilidades"] + df["inversiones_temporarias"],
            df["obligaciones_corto_plazo"],
        )
        * 100
    )
    df["roa"] = _dividir(df["utilidad_anualizada"], df["activo_promedio"]) * 100
    df["roe"] = _dividir(df["utilidad_anualizada"], df["patrimonio_promedio"]) * 100
    df["crec_cartera"] = (
        _dividir(df["cartera_bruta"], por_banco["cartera_bruta"].shift(12)) - 1
    ) * 100
    df["crec_depositos"] = (_dividir(df["depositos"], por_banco["depositos"].shift(12)) - 1) * 100

    largo = df.melt(
        id_vars=["fecha", "banco_id"],
        value_vars=INDICADORES,
        var_name="indicador_id",
        value_name="valor",
    )
    largo = largo.replace([np.inf, -np.inf], np.nan)
    return largo.sort_values(["banco_id", "indicador_id", "fecha"]).reset_index(drop=True)


def panel_ancho(panel_largo: pd.DataFrame) -> pd.DataFrame:
    """Pivotea el panel largo a columnas por indicador."""
    return (
        panel_largo.pivot_table(index=["fecha", "banco_id"], columns="indicador_id", values="valor")
        .reset_index()
        .sort_values(["banco_id", "fecha"])
        .reset_index(drop=True)
    )
