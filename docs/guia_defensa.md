# Guía de defensa oral — 10 minutos

> **Regla de oro:** el sistema mide desviaciones estocásticas y anomalías. No predice quiebras ni insolvencias. Repetir este descargo al inicio y al cierre.

## 1. Guion sugerido

### 0:00–1:00 · Problema y alcance

- Pregunta: ¿cómo saber si el último dato de un indicador bancario se aleja del proceso que lo generaba?
- Fuente: estados financieros mensuales de Bancos Múltiples de ASFI.
- Muestra: 84 meses continuos (2019-01 a 2025-12), 12 bancos, 1.008 observaciones banco-mes.
- Aclaración: no se predice quiebra; se describen desviaciones y se activan señales explicables.

### 1:00–2:30 · Datos y validación

- Descarga verificada, manifiesto SHA-256 y modo `--demo` con banner fijo.
- Parser para `.xls`, `.xlsx`, ZIP y HTML disfrazado de Excel.
- Identidad contable: 0 fallos, diferencia máxima 0,001620 miles de BOB.
- Indicadores: mora, cobertura, liquidez, ROA, ROE y crecimientos.
- Desacumulación de utilidad neta y anualización móvil de 12 meses.

### 2:30–4:00 · Estacionariedad y regresión

- ADF + KPSS, ACF/PACF antes y después de diferenciar.
- Resultado: 44 inconclusas, 35 raíz unitaria pura, 4 estacionarias, 1 en tendencia.
- Regresión con tendencia, 11 dummies y errores HAC.
- Diagnóstico: Durbin-Watson, Ljung-Box y ARCH-LM.
- Mensaje: no se fuerza una conclusión cuando los contrastes discrepan.

### 4:00–6:00 · SARIMA y backtesting

- Grilla acotada, selección por AIC, top 3.
- 84/84 series modeladas; pronóstico a 12 meses con bandas 80 % y 95 %.
- Backtesting walk-forward de 12 meses contra Naive y Seasonal Naive.
- Resultado honesto: el SARIMA supera a Naive en 26/84 series; 58 casos se reportan como no superación.

### 6:00–7:30 · Markov y alertas

- Cuatro estados de mora con umbrales 1,5 % / 2,5 % / 4,0 %.
- Matriz de transición con suavizado de Laplace, distribución estacionaria y potencias \(P^h\).
- `bfort`: probabilidad de Crítica a 3 meses de 0,9997; es una mora estructural, no una predicción.
- Alertas: banda 95 %, \(|z|>2\), \(|z|>3\), racha, salto de estado y CUSUM.
- 1.073 alertas: 268 críticas, 213 de alerta y 592 de vigilancia.

### 7:30–8:30 · Dashboard

- Abrir `dashboard/index.html` directamente.
- Mostrar: radar de bancos, serie con bandas, diagnóstico, matriz Markov interactiva, slider \(P^h\), tabla de alertas y glosario KaTeX.
- Señalar que `data.js` se carga localmente; los CDN solo aportan estilos y librerías.
- Activar el modo claro y el filtro de alertas.

### 8:30–9:30 · Limitaciones

- Banda de un paso con aproximación gaussiana.
- 84 meses: buena estacionalidad, potencia limitada para pruebas de orden y normalidad.
- Reclasificaciones contables de ASFI.
- Cambio estructural no equivale automáticamente a anomalía.
- El sistema no predice insolvencia.

### 9:30–10:00 · Cierre

- Reproducibilidad: ETL → modelos → export → tests.
- 81 pruebas automatizadas y validación Pydantic del contrato.
- Contribución: trazabilidad y honestidad estadística, no una bola de cristal.

## 2. Preguntas probables del tribunal

### 1. ¿Por qué no decir que el modelo predice quiebras?

Porque el objeto estimado es la distribución de un indicador financiero, no la probabilidad de un evento de insolvencia. Una observación fuera de banda puede deberse a un cambio contable, una reclasificación o un choque macro. Afirmar causalidad o quiebra excedería los datos y el modelo.

### 2. ¿Qué significa que una serie sea “inconclusa”?

Que ADF y KPSS no permiten una lectura única. Por ejemplo, ambos pueden rechazar sus respectivas hipótesis nulas. En series cortas con estacionalidad marcada es frecuente. Se reporta la discrepancia y se usa la diferenciación sugerida sin ocultar la incertidumbre.

### 3. ¿Por qué usar ADF y KPSS a la vez?

Porque tienen hipótesis nulas opuestas. ADF busca evidencia contra una raíz unitaria; KPSS busca evidencia contra la estacionariedad. Usarlos juntos reduce el riesgo de concluir solo por un contraste.

### 4. ¿Por qué SARIMA y no un modelo más complejo?

SARIMA es interpretable, estándar en series de tiempo y permite incorporar estacionalidad anual. La grilla se acota por costo computacional. El backtesting contra Naive y Seasonal Naive es una prueba exigente y honesta: el modelo no siempre gana.

### 5. ¿Cómo se eligió el orden SARIMA?

Por AIC dentro de una grilla acotada, con \(d\) y \(D\) sugeridos por ADF/KPSS. Se reporta el top 3. La selección no se basa en el desempeño fuera de muestra para evitar fuga de información; el backtesting se usa como evaluación, no como ajuste del orden.

### 6. ¿Qué mide el score de anomalía?

Es un resumen del sistema de alertas para el banco, no una probabilidad. Combina señales y su severidad para ordenar entidades en el radar. No debe interpretarse como probabilidad de quiebra ni como calificación regulatoria.

### 7. ¿Cómo se calcula ROA si la utilidad viene acumulada?

Se desacumula la utilidad mes a mes, se anualiza con suma móvil de 12 meses y se divide entre el activo promedio de 12 meses. Las primeras observaciones se excluyen porque no hay ventana completa.

### 8. ¿Por qué usar suavizado de Laplace en Markov?

Para evitar probabilidades nulas cuando un estado no tiene transiciones observadas. Con \(\alpha=10^{-3}\), las celdas imposibles quedan cerca de cero sin romper la propiedad de que cada fila suma uno.

### 9. ¿Qué valida el test de orden 1 vs 2?

Compara la verosimilitud de una cadena que depende solo del estado actual frente a una que depende de dos estados previos. En la muestra no se rechaza el orden 1 en ningún banco; eso no prueba que el orden 2 sea irrelevante en todos los contextos, solo que no hay evidencia suficiente con 84 meses.

### 10. ¿Cómo se evita el sobreajuste y la fuga de información?

La grilla es acotada, el backtesting usa ventana expansiva y reestima en cada paso, y los baselines son ingenuos pero exigentes. Además, los datos de validación no se usan para elegir el orden. Los resultados desfavorables se reportan.

### 11. ¿Qué pasa si ASFI cambia el formato o la unidad?

El parser detecta unidad y normaliza a miles de bolivianos. Si el formato cambia, el pipeline falla de forma visible o usa el archivo manual en `data/raw/`; no inventa datos. El modo sintético solo se activa con `--demo` y muestra un banner rojo.

### 12. ¿Por qué el dashboard funciona sin servidor?

Porque `data.js` asigna el contrato a `window.ASFI_DATA` y la SPA no hace peticiones `fetch`. Se puede abrir con `file://`. Chart.js, Motion y KaTeX se cargan por CDN; sin internet, los datos siguen locales pero algunas mejoras visuales pueden no cargar.

## 3. Comandos de respaldo

```bash
python -m pytest -q
python -m ruff check .
python -m black --check .
python -m src.export.exportador
```

Para regenerar el dashboard:

```bash
python -m src.etl.pipeline
python -m src.models.pipeline
```

## 4. Frases que conviene evitar

- “El modelo predice que el banco va a quebrar”.
- “La probabilidad de quiebra es X %”.
- “El banco está en riesgo crítico según el modelo”.
- “El p-valor demuestra que la hipótesis es falsa”.

## 5. Frases recomendadas

- “La observación se aleja del intervalo esperado por el proceso estimado”.
- “La señal es compatible con una anomalía; la causa requiere análisis adicional”.
- “El backtesting no siempre supera al baseline y se reporta sin ocultarlo”.
- “El sistema es una herramienta descriptiva, no una calificación de solvencia”.
