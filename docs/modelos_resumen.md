# Resumen del motor estocástico — Compuerta 3

> **Descargo metodológico:** este sistema mide desviaciones estocásticas y anomalías en
> indicadores financieros. No predice quiebras ni insolvencias bancarias.

## Muestra y fuente

- **Fuente:** Estados Financieros mensuales de Bancos Múltiples publicados por la ASFI.
- **Período:** 2019-01 → 2025-12 (84 meses continuos).
- **Entidades:** 12 bancos; **1.008 observaciones banco-mes**, sin huecos.
- **Modo:** datos reales (`modo_demo = false`); el panel sintético sigue disponible con `--demo`.

## Metodología aplicada

1. **Estacionariedad:** ADF (constante y tendencia) + KPSS (constante y tendencia), ACF/PACF
   hasta 24 rezagos y recomendación automática de `d` y `D` estacional.
2. **Regresión de series de tiempo:** MCO con tendencia lineal y cuadrática, 11 dummies
   mensuales y errores estándar HAC (Newey-West); diagnóstico Durbin-Watson, Ljung-Box y ARCH-LM.
3. **SARIMA:** grilla acotada `p,q ≤ 2`, `d ∈ {0,1}`, `P,Q ≤ 1`, `D ∈ {0,1}`, `s = 12`,
   con `p+q ≤ 3`, `P+Q ≤ 1`, `enforce_stationarity=False`, `enforce_invertibility=False`,
   `maxiter=50`. Selección por AIC y reporte del top 3. Pronóstico a 12 meses con bandas
   al 80 % y 95 %.
4. **Backtesting walk-forward:** ventana expansiva sobre los últimos 12 meses, reajustando
   el orden seleccionado en cada paso; comparación contra Naive y Seasonal Naive con RMSE,
   MAE y sMAPE.
5. **Markov:** 4 estados (*Baja, Media, Alta, Crítica*) con umbrales de mora
   `1,5 % / 2,5 % / 4,0 %`, suavizado de Laplace `α = 10⁻³`, distribución estacionaria,
   tiempo medio de permanencia, probabilidades a 1/3/6/12 meses y prueba de razón de
   verosimilitud Orden 1 vs Orden 2.
6. **Alertas deterministas:** banda de predicción al 95 % (un paso), `|z| > 2` y `|z| > 3`,
   racha de deterioro ≥ 3 meses con cambio acumulado ≥ 0,5 desviaciones estándar, salto
   ascendente de estado markoviano y CUSUM con banda 5,0.

## Resultados por banco

| Banco | Semáforo | Score anomalía | Mora 2025-12 (%) | π(Crítica) | P(Crítica a 3m) |
|---|---|---:|---:|---:|---:|
| bisa | rojo | 2,15 | 3,07 | 0,210 | 0,141 |
| bnb | verde | 0,88 | 3,49 | 0,093 | 0,110 |
| bun | rojo | 3,45 | 3,45 | 0,000 | 0,000 |
| bme | verde | 1,22 | 3,81 | 0,089 | 0,088 |
| bcr | naranja | 0,67 | 2,58 | 0,000 | 0,000 |
| bga | amarillo | 1,56 | 2,46 | 0,000 | 0,000 |
| bec | rojo | 2,47 | 2,79 | 0,000 | 0,000 |
| bsol | rojo | 2,08 | 1,50 | 0,000 | 0,000 |
| bna | verde | 1,58 | 0,00 | 0,000 | 0,000 |
| bfie | verde | 0,77 | 2,63 | 0,000 | 0,000 |
| bfort | rojo | 4,06 | 5,76 | 0,995 | 0,9997 |
| bpro | amarillo | 1,64 | 1,11 | 0,000 | 0,000 |

El caso de **bfort** ilustra una mora estructuralmente alta: la cadena de Markov lo ubica
casi permanentemente en el estado *Crítica*, por lo que su probabilidad de permanencia es
más informativa que una “transición” puntual.

## Verificación estacionaria

| Veredicto | Series |
|---|---:|
| Inconclusa | 44 |
| Raíz Unitaria Pura | 35 |
| Estacionaria | 4 |
| Estacionaria en Tendencia | 1 |

La categoría *Inconclusa* refleja rechazo simultáneo de ADF y KPSS, frecuente en series
cortas con estacionalidad marcada; se documenta sin forzar una conclusión.

## Órdenes SARIMA más frecuentes

| Orden | Orden estacional | Series |
|---|---|---:|
| (0,1,2) | (0,1,1)₁₂ | 25 |
| (0,1,2) | (0,0,1)₁₂ | 12 |
| (1,1,2) | (0,0,1)₁₂ | 9 |

Se evaluaron 84/84 series. El resto de combinaciones seleccionadas aparece con frecuencia ≤ 4.

## Backtesting (últimos 12 meses)

| Indicador | Supera Naive |
|---|---:|
| mora | 6 / 12 |
| cobertura | 4 / 12 |
| liquidez | 7 / 12 |
| roa | 4 / 12 |
| roe | 3 / 12 |
| crec_cartera | 2 / 12 |
| crec_depositos | 0 / 12 |
| **Total** | **26 / 84** |

El resultado se reporta sin maquillaje: en 58 de 84 series el SARIMA no superó al Naive
en RMSE. El dashboard muestra `supera_baseline` para cada serie y la interpretación
metodológica correspondiente.

## Alertas generadas

| Severidad | Cantidad |
|---|---:|
| Crítica | 268 |
| Alerta | 213 |
| Vigilancia | 592 |
| **Total** | **1.073** |

Señales más frecuentes: racha de deterioro (651), fuera de banda 95 % (275), `|z| ≥ 2` (265),
CUSUM (237), `|z| ≥ 3` (150) y salto de estado markoviano (59). En los últimos tres meses
de la muestra se concentran 18 alertas.

## Reproducción

```bash
python -m src.etl.pipeline
python -m src.models.pipeline
python -m src.export.exportador  # disponible para revalidar el contrato
```

Salidas: `dashboard/data.json`, `dashboard/data.js`, `data/processed/modelos_meta.json`.

## Limitaciones

- La banda de un paso se estima con la desviación estándar de los residuos del modelo
  (aproximación gaussiana), no con una simulación completa de la incertidumbre de parámetros.
- Los indicadores ROA/ROE requieren 12 meses de historia para anualizar; las primeras
  observaciones se excluyen y se reportan como faltantes, no se imputan.
- La muestra de 84 meses es suficiente para estacionalidad anual, pero limita la potencia
  de las pruebas de orden markoviano y de normalidad.
- Las cifras dependen de la calidad y de las reclasificaciones contables de la ASFI.
