"""Generación automática del reporte docs/calidad_datos.md."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pandas as pd


def _tabla(cabeceras: list[str], filas: list[list[object]]) -> str:
    if not filas:
        return "_Sin registros._\n"
    lineas = [
        "| " + " | ".join(cabeceras) + " |",
        "|" + "|".join(["---"] * len(cabeceras)) + "|",
    ]
    for fila in filas:
        celdas = [str(c).replace("|", "\\|") for c in fila]
        lineas.append("| " + " | ".join(celdas) + " |")
    return "\n".join(lineas) + "\n"


def _num(valor: object, decimales: int = 2) -> str:
    if valor is None or (isinstance(valor, float) and pd.isna(valor)):
        return "—"
    if isinstance(valor, (int,)) and not isinstance(valor, bool):
        return str(valor)
    try:
        return f"{float(valor):,.{decimales}f}"
    except (TypeError, ValueError):
        return str(valor)


def generar_reporte_calidad(
    destino: str | Path,
    panel_contable: pd.DataFrame,
    panel_largo: pd.DataFrame,
    tabla_identidad: pd.DataFrame,
    resumen_id: dict,
    violaciones: pd.DataFrame,
    duplicados_df: pd.DataFrame,
    cobertura: pd.DataFrame,
    resumen_ind: pd.DataFrame,
    archivos: list[dict],
    meses_minimos: int,
    modo_demo: bool,
    tolerancia_identidad: float,
) -> Path:
    destino = Path(destino)
    destino.parent.mkdir(parents=True, exist_ok=True)
    generado = datetime.now(UTC).isoformat(timespec="seconds")

    lineas: list[str] = []
    lineas.append("# Reporte de calidad de datos — EEFF Bancarios ASFI\n")
    lineas.append(f"- **Generado (UTC):** {generado}")
    lineas.append(
        f"- **Modo demostración:** {'SÍ — DATOS SINTÉTICOS' if modo_demo else 'no (datos reales)'}"
    )
    lineas.append(f"- **Archivos procesados:** {len(archivos)}")
    if not panel_contable.empty:
        lineas.append(
            f"- **Rango temporal:** {panel_contable['fecha'].min()} → {panel_contable['fecha'].max()}"
        )
        lineas.append(f"- **Bancos:** {panel_contable['banco_id'].nunique()}")
        lineas.append(f"- **Observaciones banco-mes:** {len(panel_contable)}")
        lineas.append(
            f"- **Indicadores calculados:** {panel_largo['indicador_id'].nunique() if not panel_largo.empty else 0}\n"
        )
    if modo_demo:
        lineas.append(
            "> **MODO DEMOSTRACIÓN — DATOS SINTÉTICOS.** Este reporte no describe datos oficiales de ASFI.\n"
        )

    lineas.append("## Archivos y formatos\n")
    filas_archivos = [
        [
            a.get("archivo", "—"),
            a.get("fecha", "—"),
            a.get("unidad", "—"),
            a.get("codigos", "—"),
            _num(a.get("diferencia_identidad_max"), 4),
        ]
        for a in archivos
    ]
    lineas.append(
        _tabla(
            ["Archivo", "Período", "Unidad", "Entidades detectadas", "Máx. |Δ identidad|"],
            filas_archivos,
        )
    )

    lineas.append("## Cobertura mensual por banco\n")
    filas_cob = [
        [
            fila["banco_id"],
            fila["observaciones"],
            fila["primer_mes"],
            fila["ultimo_mes"],
            fila["huecos"],
            f"{fila['cobertura_pct']:.2f} %",
            "Sí" if fila["apta_para_modelado"] else "No",
        ]
        for _, fila in cobertura.iterrows()
    ]
    lineas.append(
        _tabla(
            [
                "Banco",
                "Meses",
                "Primer mes",
                "Último mes",
                "Huecos",
                "Cobertura",
                f"≥ {meses_minimos} meses",
            ],
            filas_cob,
        )
    )
    aptas = cobertura[cobertura["apta_para_modelado"]]["banco_id"].tolist()
    insuficientes = cobertura[~cobertura["apta_para_modelado"]]["banco_id"].tolist()
    lineas.append(f"- **Aptos para modelado:** {', '.join(aptas) if aptas else 'ninguno'}")
    lineas.append(
        f"- **Insuficientes (< {meses_minimos} meses):** {', '.join(insuficientes) if insuficientes else 'ninguno'}\n"
    )

    lineas.append("## Identidad contable\n")
    lineas.append(
        f"Se verificó |Activo − (Pasivo + Patrimonio)| ≤ {tolerancia_identidad:g} "
        "miles de bolivianos en cada observación banco-mes.\n"
    )
    lineas.append(
        _tabla(
            ["Registros", "Fallos", "Diferencia máxima"],
            [
                [
                    resumen_id.get("registros", 0),
                    resumen_id.get("fallos", 0),
                    _num(resumen_id.get("diferencia_max"), 6),
                ]
            ],
        )
    )
    if resumen_id.get("fallos", 0):
        fallos = tabla_identidad[~tabla_identidad["cumple"]].head(15)
        lineas.append("**Primeras discrepancias detectadas:**\n")
        lineas.append(
            _tabla(
                ["Fecha", "Banco", "Activo", "Pasivo + Patrimonio", "Diferencia"],
                [
                    [
                        f["fecha"],
                        f["banco_id"],
                        _num(f["activo_total"]),
                        _num(f["pasivo_mas_patrimonio"]),
                        _num(f["diferencia"], 4),
                    ]
                    for _, f in fallos.iterrows()
                ],
            )
        )

    lineas.append("## Valores imposibles y duplicados\n")
    lineas.append(f"- Valores no positivos en cuentas de stock: **{len(violaciones)}**")
    lineas.append(f"- Registros banco-mes duplicados: **{len(duplicados_df)}**\n")
    if not violaciones.empty:
        lineas.append(
            _tabla(
                ["Fecha", "Banco", "Cuenta", "Valor"],
                [
                    [v["fecha"], v["banco_id"], v["cuenta"], _num(v["valor"], 4)]
                    for _, v in violaciones.head(15).iterrows()
                ],
            )
        )

    lineas.append("## Resumen de indicadores\n")
    filas_ind = [
        [
            fila["indicador_id"],
            fila["observaciones_validas"],
            fila["faltantes"],
            _num(fila["media"], 4),
            _num(fila["desv_est"], 4),
            _num(fila["minimo"], 4),
            _num(fila["maximo"], 4),
        ]
        for _, fila in resumen_ind.iterrows()
    ]
    lineas.append(
        _tabla(
            ["Indicador", "Válidos", "Faltantes", "Media", "Desv. est.", "Mínimo", "Máximo"],
            filas_ind,
        )
    )

    lineas.append("## Método de cálculo\n")
    lineas.append(
        "- **Mora:** Cartera en Mora / Cartera Bruta × 100, donde Cartera en Mora = "
        "Cartera Vencida Total + Cartera en Ejecución Total.\n"
        "- **Cobertura:** Previsión para Incobrabilidad de Cartera / Cartera en Mora × 100 "
        "(la previsión se toma en valor absoluto).\n"
        "- **Liquidez:** (Disponibilidades + Inversiones Temporarias) / Obligaciones de corto "
        "plazo × 100. Las obligaciones de corto plazo se aproximan como la suma de obligaciones "
        "con el público, instituciones fiscales, empresas públicas, bancos y entidades de "
        "financiamiento, otras cuentas por pagar y valores en circulación.\n"
        "- **ROA / ROE:** la Utilidad Neta acumulada se desacumula (ΔU mensual) y se anualiza "
        "con suma móvil de 12 meses; se divide entre el Activo o Patrimonio promedio de 12 "
        "meses y se multiplica por 100. Los primeros 11 meses de cada serie quedan como "
        "faltantes hasta completar la ventana.\n"
        "- **Crecimiento interanual:** variación porcentual a 12 meses de cartera bruta y "
        "depósitos.\n"
        "- Los huecos aislados de hasta 2 meses podrán interpolarse en la fase de modelado; "
        "huecos mayores truncan la serie al tramo continuo más reciente.\n"
    )

    lineas.append(
        "\n> **Descargo metodológico:** este sistema mide desviaciones estocásticas y "
        "anomalías en indicadores financieros. No predice quiebras ni insolvencias "
        "bancarias. Las cifras provienen de los archivos publicados por la ASFI y su "
        "calidad depende de la fuente.\n"
    )

    destino.write_text("\n".join(lineas), encoding="utf-8")
    return destino
