# Metodología del Sistema de Alerta Temprana Estocástica

> **Descargo metodológico:** este sistema mide desviaciones estocásticas y anomalías en indicadores financieros. No predice quiebras, insolvencias ni calificaciones de riesgo. Una señal estadística no sustituye el análisis financiero, la supervisión regulatoria ni el juicio profesional.

## 1. Objetivo y alcance

El proyecto construye un pipeline reproducible que:

1. descarga y valida estados financieros mensuales de bancos múltiples publicados por la ASFI;
2. calcula indicadores contables comparables en el tiempo;
3. estima un proceso generador de datos para cada serie;
4. detecta observaciones compatibles con una desviación del proceso estimado;
5. comunica los resultados en un dashboard estático y en materiales académicos.

El alcance es **descriptivo y académico**. La unidad de análisis es la serie mensual banco-indicador; no se modela la probabilidad de quiebra ni se emite una recomendación de inversión.

## 2. Datos y trazabilidad

- **Fuente:** Estados Financieros mensuales de Bancos Múltiples, ASFI Bolivia.
- **Ruta verificada:** `sites/default/files/estadisticaif/bancos_multiples/{AAAA}/{MM}/{AAAA}{MM}_BMU_EstadosFinancieros.zip`.
- **Período utilizado:** 2019-01 a 2025-12, 84 meses continuos.
- **Entidades:** 12 bancos múltiples, 1.008 observaciones banco-mes.
- **Registro de descargas:** `data/raw/manifest.csv` con URL, ruta local, timestamp, SHA-256, bytes y estado.
- **Evidencia de exploración:** `docs/exploracion_asfi.md`.
- **Reporte de calidad:** `docs/calidad_datos.md`.

Cada archivo se procesa sin modificar el original. El ETL genera `data/interim/*.parquet`, `data/processed/panel_contable.parquet` y `data/processed/panel_indicadores.parquet`.

### 2.1 Validaciones contables

Para cada registro se comprueba:

\[
\left| \text{Activo}_t - \left(\text{Pasivo}_t + \text{Patrimonio}_t\right) \right| \le \epsilon
\]

con \(\epsilon = 1\) miles de bolivianos. También se detectan valores negativos imposibles, duplicados banco-mes y cambios de unidad de medida. En la muestra real se obtuvo **0 fallos de identidad** y una diferencia máxima de **0,001620 miles de BOB**.

La interpolación se limita a huecos aislados de hasta dos meses. Los huecos mayores truncan la serie al tramo continuo más reciente. Una serie con menos de 60 observaciones se marca como insuficiente y no se fuerza su modelado.

## 3. Ingeniería de indicadores

### 3.1 Indicadores de stock

- **Mora:** \(\text{Cartera en Mora} / \text{Cartera Bruta}\).
- **Cobertura de previsiones:** \(\text{Previsión para Incobrables} / \text{Cartera en Mora}\).
- **Liquidez:** \((\text{Disponibilidades} + \text{Inversiones Temporarias}) / \text{Obligaciones a Corto Plazo}\).
- **Crecimiento interanual de cartera:** \((C_t - C_{t-12}) / C_{t-12}\).
- **Crecimiento interanual de depósitos:** \((D_t - D_{t-12}) / D_{t-12}\).

### 3.2 Indicadores de flujo: ROA y ROE

La utilidad neta mensual de ASFI suele reportarse acumulada desde enero. Para obtener un flujo mensual se desacumula:

\[
\Delta U_t = U_t - U_{t-1}, \qquad t > \text{enero}
\]

y en enero se usa el valor acumulado del mes. Luego se anualiza con una suma móvil de 12 meses:

\[
\widetilde{U}_t = \sum_{k=0}^{11} \Delta U_{t-k}
\]

Finalmente:

\[
\text{ROA}_t = \frac{\widetilde{U}_t}{\overline{A}_{t,12}},
\qquad
\text{ROE}_t = \frac{\widetilde{U}_t}{\overline{P}_{t,12}}
\]

donde \(\overline{A}_{t,12}\) y \(\overline{P}_{t,12}\) son los promedios móviles de 12 meses del activo y del patrimonio. Las primeras observaciones se excluyen y se reportan como faltantes; no se imputan.

## 4. Estacionariedad

Para cada serie se aplican dos contrastes complementarios:

- **ADF** (Dickey-Fuller aumentado): \(H_0\): existe raíz unitaria.
- **KPSS** (Kwiatkowski-Phillips-Schmidt-Shin): \(H_0\): la serie es estacionaria.

La lectura conjunta permite clasificar la serie como:

| ADF | KPSS | Lectura |
|---|---|---|
| No rechaza \(H_0\) | No rechaza \(H_0\) | Inconclusa |
| No rechaza \(H_0\) | Rechaza \(H_0\) | Raíz unitaria pura |
| Rechaza \(H_0\) | No rechaza \(H_0\) | Estacionaria |
| Rechaza \(H_0\) | Rechaza \(H_0\) | Inconclusa o tendencia, según especificación |

También se calculan ACF y PACF hasta 24 rezagos, antes y después de diferenciar, y se sugiere \(d \in \{0,1\}\) y \(D \in \{0,1\}\) para la grilla SARIMA.

En la muestra se obtuvieron 44 series *Inconclusas*, 35 con *Raíz Unitaria Pura*, 4 *Estacionarias* y 1 *Estacionaria en Tendencia*. La categoría *Inconclusa* se conserva explícitamente; no se fuerza una conclusión que los datos no sostienen.

## 5. Regresión de series de tiempo con errores HAC

Se estima por MCO:

\[
y_t = \beta_0 + \beta_1 t + \beta_2 t^2 + \sum_{m=2}^{12}\gamma_m D_{mt} + \varepsilon_t
\]

donde \(D_{mt}\) son 11 dummies mensuales. Los errores estándar son **HAC (Newey-West)**, robustos a autocorrelación y heterocedasticidad.

Diagnósticos reportados:

- \(R^2\) ajustado;
- Durbin-Watson;
- Ljung-Box sobre residuos;
- ARCH-LM para efectos ARCH;
- coeficientes de tendencia lineal y cuadrática.

La regresión no se usa para pronosticar: funciona como diagnóstico de tendencia, estacionalidad y estructura de los residuos.

## 6. SARIMA y selección de modelos

El modelo es:

\[
\phi(B)\Phi(B^{12})(1-B)^d(1-B^{12})^D y_t
=
\theta(B)\Theta(B^{12})\varepsilon_t
\]

La grilla se acota para mantener un costo computacional razonable:

- \(p,q \in \{0,1,2\}\), \(d \in \{0,1\}\);
- \(P,Q \in \{0,1\}\), \(D \in \{0,1\}\);
- \(s=12\);
- \(p+q \le 3\), \(P+Q \le 1\);
- `enforce_stationarity=False`, `enforce_invertibility=False`, `maxiter=50`.

Se selecciona por AIC y se reporta el top 3. El pronóstico es a 12 meses con bandas al 80 % y 95 %. Las bandas describen incertidumbre del proceso estimado; no son una garantía de rango.

### 6.1 Backtesting walk-forward

Se evalúan los últimos 12 meses con ventana expansiva. En cada paso se reajusta el modelo y se compara contra:

- **Naive:** \(\hat{y}_{t+1}=y_t\).
- **Seasonal Naive:** \(\hat{y}_{t+1}=y_{t-11}\).

Métricas: RMSE, MAE y sMAPE. Si el SARIMA no supera al baseline, el contrato exporta `"supera_baseline": false`. En la muestra real, el SARIMA superó a Naive en **26 de 84 series**; los 58 casos restantes se reportan sin ocultarlos.

## 7. Cadena de Markov de la mora

La mora se discretiza en cuatro estados:

| Estado | Regla |
|---|---|
| Baja | \(m_t < 1,5\,\%\) |
| Media | \(1,5\,\% \le m_t < 2,5\,\%\) |
| Alta | \(2,5\,\% \le m_t < 4,0\,\%\) |
| Crítica | \(m_t \ge 4,0\,\%\) |

La matriz de transición se estima con suavizado de Laplace:

\[
P_{ij} = \frac{n_{ij} + \alpha}{\sum_{j=1}^{4} n_{ij} + 4\alpha},
\qquad \alpha = 10^{-3}
\]

Se calculan:

- distribución estacionaria \(\boldsymbol{\pi} = \boldsymbol{\pi}\mathbf{P}\);
- tiempo medio de permanencia \(1/(1-P_{ii})\);
- probabilidades de alcanzar el estado Crítica a 1, 3, 6 y 12 meses;
- prueba de razón de verosimilitud para orden 1 vs. orden 2.

En la muestra, la prueba no rechaza el orden 1 en ningún banco (\(p \approx 1\)). El caso `bfort` presenta una mora estructuralmente alta: su distribución estacionaria asigna aproximadamente 99,5 % al estado Crítica, por lo que la permanencia es más informativa que una transición puntual.

## 8. Motor determinista de alertas

Una alerta se activa si se cumple al menos una de estas señales:

1. **Fuera de banda:** la observación queda fuera del intervalo de predicción al 95 % de un paso, estimado con \(\hat{y}_t \pm 1,959964\,\hat{\sigma}_{\varepsilon}\).
2. **Residuo estandarizado:** \(|z_t| > 2\) (vigilancia) o \(|z_t| > 3\) (alerta).
3. **Racha de deterioro:** al menos 3 meses consecutivos en la dirección de riesgo, con cambio acumulado mínimo de 0,5 desviaciones estándar.
4. **Salto markoviano:** transición ascendente de estado o probabilidad de Crítica a 3 meses por encima del umbral configurado.
5. **CUSUM:** suma acumulada de residuos fuera de una banda de control de 5,0.

La severidad se asigna de forma determinista:

- `vigilancia`: señales de baja intensidad o una racha;
- `alerta`: residuo \(|z|>2\), CUSUM o combinación de señales;
- `critica`: residuo \(|z|>3\) o combinación de señales de alta intensidad.

El motor es transparente: cada alerta se puede reconstruir a partir de los residuos, las bandas, la racha, la matriz de Markov y el CUSUM.

## 9. Contrato de salida

El pipeline exporta `dashboard/data.json` y `dashboard/data.js` validados con Pydantic. La estructura raíz es:

```text
meta | bancos[] | indicadores_meta[] | series{banco}{indicador} | markov | alertas[]
```

Cada serie contiene observaciones, ajuste, residuos, pronóstico, estacionariedad, regresión, SARIMA, backtest y momentos. El dashboard funciona por `file://` cargando `window.ASFI_DATA` desde `data.js`.

## 10. Reproducibilidad

```bash
python -m src.scraping.historico --tipo eeff --desde 2019-01 --hasta 2025-12
python -m src.etl.pipeline
python -m src.models.pipeline
python -m src.export.exportador
python -m pytest -q
```

El modo demostración se activa únicamente con `--demo` y muestra el banner fijo `MODO DEMOSTRACIÓN — DATOS SINTÉTICOS`.

## 11. Limitaciones declaradas

- La banda de un paso usa una aproximación gaussiana basada en la desviación estándar de los residuos; no simula toda la incertidumbre de parámetros.
- La muestra de 84 meses permite estacionalidad anual, pero limita la potencia de pruebas de normalidad y de orden markoviano.
- Los indicadores dependen de la calidad, reclasificaciones y cambios de criterio contable de ASFI.
- Un cambio estructural no se distingue automáticamente de una anomalía; el sistema señala desviaciones, no causas.
- El dashboard requiere conexión para cargar CDN de Chart.js, Motion, Tailwind y KaTeX; los datos son locales.
- El sistema no predice quiebras ni insolvencias. Cualquier uso en ese sentido excede el alcance metodológico.

## 12. Referencias metodológicas

- Dickey, D. A. y Fuller, W. A. (1979). Distribution of the Estimators for Autoregressive Time Series with a Unit Root.
- Kwiatkowski, D., Phillips, P. C. B., Schmidt, P. y Shin, Y. (1992). Testing the Null Hypothesis of Stationarity against the Alternative of a Unit Root.
- Newey, W. K. y West, K. D. (1987). A Simple, Positive Semi-Definite, Heteroskedasticity and Autocorrelation Consistent Covariance Matrix.
- Ljung, G. M. y Box, G. E. P. (1978). On a Measure of Lack of Fit in Time Series Models.
- Engle, R. F. (1982). Autoregressive Conditional Heteroscedasticity with Estimates of the Variance of United Kingdom Inflation.
- Box, G. E. P., Jenkins, G. M., Reinsel, G. C. y Ljung, G. M. (2015). Time Series Analysis: Forecasting and Control.
- Hyndman, R. J. y Athanasopoulos, G. (2021). Forecasting: Principles and Practice.
- Hamilton, J. D. (1994). Time Series Analysis.
