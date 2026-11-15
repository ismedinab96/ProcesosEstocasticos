"""Esquema Pydantic del contrato de salida `data.json` / `window.ASFI_DATA`."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class Flexible(BaseModel):
    model_config = ConfigDict(extra="allow")


class Meta(Flexible):
    generado_utc: str
    fuente: str
    modo_demo: bool
    rango_fechas: list[str]
    total_observaciones: int


class Banco(Flexible):
    id: str
    nombre: str
    tipo: str
    semaforo: Literal["verde", "amarillo", "naranja", "rojo"]
    score_anomalia: float | None = None
    cobertura_meses: int = 0
    sparkline_mora: list[float | None] = Field(default_factory=list)


class IndicadorMeta(Flexible):
    id: str
    nombre: str
    formula_latex: str
    unidad: str
    direccion_riesgo: str


class Pronostico(Flexible):
    fechas: list[str]
    media: list[float | None]
    ic80_inf: list[float | None]
    ic80_sup: list[float | None]
    ic95_inf: list[float | None]
    ic95_sup: list[float | None]


class Estacionariedad(Flexible):
    adf_stat: float | None = None
    adf_pval: float | None = None
    kpss_stat: float | None = None
    kpss_pval: float | None = None
    d_recomendado: int | None = None
    D_estacional: int | None = None
    veredicto: str
    acf_orig: list[float | None] = Field(default_factory=list)
    pacf_orig: list[float | None] = Field(default_factory=list)
    acf_diff: list[float | None] = Field(default_factory=list)
    pacf_diff: list[float | None] = Field(default_factory=list)


class RegresionOLS(Flexible):
    r2_adj: float | None = None
    dw_stat: float | None = None
    ljung_box_pval: float | None = None
    arch_lm_pval: float | None = None
    tendencia: list[dict[str, Any]] = Field(default_factory=list)
    estacionalidad: list[dict[str, Any]] = Field(default_factory=list)


class Sarima(Flexible):
    orden: list[int]
    orden_estacional: list[int]
    aic: float | None = None
    bic: float | None = None
    top3_modelos: list[dict[str, Any]] = Field(default_factory=list)
    ljung_box_pval: float | None = None
    jarque_bera_pval: float | None = None
    shapiro_pval: float | None = None
    asimetria: float | None = None
    curtosis: float | None = None
    qq_teorico: list[float | None] = Field(default_factory=list)
    qq_muestral: list[float | None] = Field(default_factory=list)


class Backtest(Flexible):
    rmse_modelo: float | None = None
    mae_modelo: float | None = None
    smape_modelo: float | None = None
    rmse_naive: float | None = None
    rmse_snaive: float | None = None
    supera_baseline: bool | None = None


class Serie(Flexible):
    fechas: list[str]
    observado: list[float | None]
    momentos: dict[str, Any] | None = None
    ajuste_in_sample: list[float | None] | None = None
    residuos_estandarizados: list[float | None] | None = None
    pronostico: Pronostico | None = None
    estacionariedad: Estacionariedad
    regresion_ols: RegresionOLS
    sarima: Sarima | None = None
    backtest: Backtest | None = None
    prediccion_un_paso: dict[str, Any] | None = None
    apta_modelado: bool | None = None
    motivo: str | None = None


class ProbCritico(Flexible):
    m1: float | None = None
    m3: float | None = None
    m6: float | None = None
    m12: float | None = None


class MarkovBanco(Flexible):
    matriz_transicion: list[list[float | None]]
    dist_estacionaria: list[float | None]
    tiempo_permanencia_meses: list[float | None]
    prob_critico_h: ProbCritico
    test_orden_1_vs_2_pval: float | None = None
    cumple_propiedad_markov: bool | None = None


class SistemaAgregado(Flexible):
    matriz_transicion: list[list[float | None]]
    dist_estacionaria: list[float | None]


class Markov(Flexible):
    estados: list[str]
    umbrales: list[float]
    por_banco: dict[str, MarkovBanco]
    sistema_agregado: SistemaAgregado


class Alerta(Flexible):
    id: str
    fecha: str
    banco_id: str
    indicador_id: str
    severidad: Literal["vigilancia", "alerta", "critica"]
    z_score: float | None = None
    senales_activadas: list[str] = Field(default_factory=list)
    explicacion_clara: str


class Contrato(Flexible):
    meta: Meta
    bancos: list[Banco]
    indicadores_meta: list[IndicadorMeta]
    series: dict[str, dict[str, Serie]]
    markov: Markov
    alertas: list[Alerta]
