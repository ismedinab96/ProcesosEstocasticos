# Guía para dummies: Sistema de Alerta Temprana Estocástica

*Guía de estudio y defensa · Procesos Estocásticos · Estados financieros de bancos múltiples (ASFI Bolivia, 2019–2025)*

> **Regla de oro (memorízala):** el sistema mide desviaciones y anomalías en indicadores financieros. **No predice quiebras ni insolvencias.** Repítelo al inicio y al cierre de la defensa.

## 0. Cómo usar esta guía

Esta guía no reemplaza el informe ni la metodología: los traduce a lenguaje cotidiano para que puedas estudiar y defender el trabajo sin perderte en la jerga.

- **Si tienes 15 minutos:** lee los capítulos 1 y 2 y la hoja resumen del final.
- **Si vas a estudiar en serio:** lee los capítulos 3 y 4 en orden. Cada concepto sigue la misma estructura.
- **Si la defensa está cerca:** ve directo a las preguntas del tribunal y a las frases recomendadas.

Cada concepto se explica con cuatro piezas:

- **Analogía:** la idea con una imagen cotidiana.
- **En el proyecto:** qué hace y con qué datos reales.
- **Cómo decirlo en la defensa:** una frase lista para usar.
- **Error típico:** lo que suele salir mal.

## 1. El proyecto en dos minutos

**La analogía del monitor del hospital.** Imagina que cada banco es un paciente y que cada indicador (mora, liquidez, rentabilidad…) es un signo vital: pulso, presión, temperatura. Un monitor no predice si el paciente se va a enfermar. Lo que hace es avisar cuando un signo vital se sale de lo que es normal **para ese paciente**. Nuestro sistema es ese monitor, pero para bancos.

**El recorrido completo, en seis pasos:**

1. **Descargar** los estados financieros mensuales de los bancos múltiples desde el portal de la ASFI.
2. **Validar** que la contabilidad cuadre (la balanza debe cerrar).
3. **Calcular indicadores** comparables en el tiempo (mora, cobertura, liquidez, ROA, ROE, crecimientos).
4. **Aprender el comportamiento normal** de cada serie con modelos estocásticos.
5. **Comparar** el dato nuevo contra lo que el modelo esperaba.
6. **Avisar** cuando el dato se aleja demasiado, y explicar por qué.

**Los números del proyecto:** 84 meses continuos (enero 2019 a diciembre 2025), 12 bancos, 1.008 observaciones banco-mes, 7 indicadores por banco, es decir 84 series modeladas.

**Cómo decirlo en la defensa:** «Nuestro sistema no responde si un banco va a quebrar. Responde otra pregunta, más humilde y más honesta: el último dato de este indicador, ¿se parece a lo que su propio historial hacía esperar?»

## 2. Mapa de conceptos

Todo el proyecto responde preguntas sencillas. Cada herramienta técnica existe para contestar una de ellas.

| Pregunta en lenguaje normal | Concepto | Herramienta |
| --- | --- | --- |
| ¿La serie se comporta de forma estable en el tiempo? | Estacionariedad | ADF, KPSS, ACF/PACF |
| ¿Hay una tendencia y un patrón por mes del año? | Regresión de series de tiempo | MCO con errores HAC |
| ¿Qué rango es normal para los próximos meses? | Pronóstico | SARIMA |
| ¿Ese modelo sirve de verdad? | Evaluación fuera de muestra | Backtesting walk-forward |
| ¿En qué nivel de mora está el banco y cuánto suele quedarse ahí? | Cadena de Markov | Matriz de transición |
| ¿El dato nuevo es raro? | Detección de anomalías | z-score, bandas, CUSUM, alertas |

## 3. Los datos y los indicadores

### 3.1 De dónde salen

La fuente es la ASFI (Autoridad de Supervisión del Sistema Financiero). Cada mes publica un archivo comprimido con los estados financieros de los bancos múltiples: filas son cuentas contables y columnas son bancos. El proyecto descarga los archivos de forma responsable (con pausas, reintentos y una huella SHA-256 para comprobar que no cambiaron) y guarda los originales sin tocarlos.

**Analogía:** es como guardar el recibo original de cada compra en una caja y trabajar siempre con fotocopias. Si algo falla, el original sigue intacto.

### 3.2 La balanza que debe cuadrar

En contabilidad siempre se cumple que **Activo = Pasivo + Patrimonio**. El ETL comprueba esto en cada banco y cada mes. Resultado: **0 fallos** en 1.008 registros; la diferencia máxima fue de 0,00162 miles de bolivianos, es decir, un redondeo.

**Cómo decirlo en la defensa:** «Antes de modelar nada verificamos que los datos cuadraran contablemente; si no cuadran, los números no merecen un modelo.»

### 3.3 Los siete indicadores

| Indicador | En palabras simples | Ejemplo real |
| --- | --- | --- |
| **Mora** | De cada 100 bolivianos prestados, cuántos están atrasados | BISA, dic. 2025: 3,07 %. Es decir, Bs 3,07 de cada Bs 100 |
| **Cobertura de previsiones** | Cuánto colchón tiene el banco guardado frente a esos créditos atrasados | Más colchón, mejor |
| **Liquidez** | Cuánto efectivo y activos rápidos tiene frente a lo que debe pagar pronto | Qué tan fácil le sería responder a retiros |
| **ROA** | Cuánto gana por cada boliviano de activos | Rentabilidad sobre lo que tiene |
| **ROE** | Cuánto gana por cada boliviano de los dueños | Rentabilidad sobre el patrimonio |
| **Crecimiento de cartera** | Cuánto crecieron los préstamos frente al mismo mes del año anterior | Compara contra hace 12 meses |
| **Crecimiento de depósitos** | Cuánto crecieron los ahorros de la gente frente al mismo mes del año anterior | Compara contra hace 12 meses |

### 3.4 El truco del odómetro (desacumulación de la utilidad)

La ASFI reporta la utilidad **acumulada desde enero**, igual que el odómetro de un auto marca los kilómetros totales y no los de hoy. Para saber cuánto se ganó **en un mes**, se resta el acumulado del mes anterior. Luego se suman los últimos 12 meses (utilidad anualizada) y se divide entre el activo o patrimonio promedio de 12 meses. Por eso ROA y ROE solo existen desde diciembre de 2019 en adelante: hacen falta 12 meses de historia.

**Error típico:** dividir la utilidad acumulada directamente entre el activo. En marzo tendrías tres meses de utilidad y en diciembre doce, y la serie subiría y bajaría por puro calendario.

## 4. Los conceptos, uno por uno

### 4.1 Serie de tiempo y proceso estocástico

**Analogía:** una serie de tiempo es la grabación de los latidos de un paciente: un valor por cada momento. Un proceso estocástico es la «máquina» que genera esos latidos, con parte de regla y parte de azar. Nunca vemos la máquina, solo los latidos. Modelar es adivinar cómo es la máquina a partir de lo que grabó.

**En el proyecto:** cada combinación banco-indicador es una serie mensual de 84 puntos (por ejemplo, la mora de BISA). Suponemos que cada una nace de su propio proceso.

**Cómo decirlo en la defensa:** «Tratamos cada indicador de cada banco como la realización de un proceso estocástico y estimamos ese proceso para saber qué valores son esperables.»

**Error típico:** confundir la serie (los datos observados) con el proceso (el mecanismo que no vemos).

### 4.2 Estacionariedad

**Analogía:** un río tranquilo es estacionario: sube y baja un poco pero su nivel promedio y su agitación son siempre parecidos. Un río con deshielo es no estacionario: su nivel de base va cambiando con el tiempo.

**Por qué importa:** muchos modelos solo funcionan bien con series «tranquilas». Si no lo son, hay que trabajar con los cambios (diferenciar) en lugar de los niveles.

**En el proyecto:** se evalúa cada una de las 84 series antes de modelarla y se decide si hay que diferenciar una vez (d = 1) y/o estacionalmente (D = 1).

**Cómo decirlo en la defensa:** «Antes de modelar verificamos si la serie conserva su media y su variabilidad en el tiempo; si no, la transformamos.»

**Error típico:** creer que estacionaria significa «que no se mueve». Se mueve, pero alrededor de un nivel estable.

### 4.3 Raíz unitaria

**Analogía:** la caminata del borracho. Cada paso parte de donde quedó el anterior y nada lo atrae de vuelta al punto de partida, así que puede alejarse indefinidamente. Eso es una raíz unitaria: la serie «no tiene memoria de dónde debería estar».

**Contraste:** una serie estacionaria es como un perro con correa. Se aleja, pero la correa lo trae de vuelta.

**Cómo decirlo en la defensa:** «Una raíz unitaria significa que los choques son permanentes: la serie no regresa sola a un nivel de equilibrio.»

### 4.4 Las pruebas ADF y KPSS

**Analogía de los dos testigos.** Imagina dos testigos que arrancan con versiones opuestas por defecto:

- **ADF** parte de que «hay raíz unitaria» (la serie es la caminata del borracho). Solo cambia de opinión si encuentra evidencia fuerte en contra.
- **KPSS** parte de lo contrario: «la serie es estacionaria». Solo cambia de opinión si la evidencia es fuerte.

Usar los dos juntos evita decidir con un solo testigo.

**Cómo se leen juntos:**

| ADF | KPSS | Lectura |
| --- | --- | --- |
| No rechaza | No rechaza | Inconclusa (los datos no alcanzan para decidir) |
| No rechaza | Rechaza | Raíz unitaria pura |
| Rechaza | No rechaza | Estacionaria |
| Rechaza | Rechaza | Inconclusa o con tendencia, según la especificación |

**Resultados del proyecto (84 series):** 44 inconclusas, 35 con raíz unitaria pura, 4 estacionarias y 1 estacionaria en tendencia.

**Cómo decirlo en la defensa:** «Usamos pruebas con hipótesis nulas opuestas. Cuando discrepan, lo reportamos como inconcluso en vez de forzar una respuesta: es honestidad estadística.»

**Error típico:** decir que el p-valor «demuestra» algo. Solo indica si hay evidencia suficiente para rechazar la hipótesis de partida.

### 4.5 ACF y PACF

**Analogía:** el eco. La **ACF** mide cuánto se parece la serie a sí misma hace 1, 2, 3… meses, como un eco que rebota en varias paredes. La **PACF** mide solo el eco directo de cada mes, descontando los rebotes intermedios.

**Cómo se usan:** sirven de pista para elegir cuánta memoria darle al modelo (los números p y q de SARIMA). Un pico fuerte en el rezago 12 delata un patrón anual (estacionalidad).

**En el proyecto:** se calculan hasta 24 rezagos, antes y después de diferenciar, para ver si el modelo «limpió» la memoria de la serie.

**Cómo decirlo en la defensa:** «La ACF y la PACF nos muestran la estructura de memoria de la serie y orientan el orden del modelo.»

### 4.6 Regresión de series de tiempo con errores HAC

**Analogía:** es como descomponer la factura de luz en tres partes: lo que sube con el tiempo (tendencia), lo que cambia con la estación del año (efecto mensual) y lo imprevisible (residuo).

**En el proyecto:** se ajusta una regresión con tendencia lineal y cuadrática y 11 variables ficticias de mes. Sirve como **diagnóstico**, no para pronosticar.

**¿Y HAC?** Los datos de meses vecinos se parecen entre sí, y eso engaña a la regresión clásica haciéndola sentir más segura de lo que debería. Los errores estándar HAC (Newey-West) corrigen eso: son como añadir un margen de seguridad extra porque sabes que tus datos no son independientes.

**Los tres chequeos de los residuos:**

- **Durbin-Watson:** ¿los errores de un mes arrastran al siguiente?
- **Ljung-Box:** ¿queda alguna memoria sin explicar en los residuos?
- **ARCH-LM:** ¿la volatilidad viene en rachas (meses agitados seguidos de meses agitados)?

**Cómo decirlo en la defensa:** «La regresión no pronostica; nos dice si hay tendencia y estacionalidad, y los errores HAC protegen la inferencia frente a la autocorrelación.»

**Error típico:** presentar la regresión como el modelo principal de pronóstico. El pronóstico lo hace SARIMA.

### 4.7 SARIMA

**Analogía:** es una receta con ingredientes de memoria.

- **AR (autorregresivo, p):** el valor de hoy depende de los valores de los meses pasados.
- **I (integrado, d):** en lugar de mirar los niveles, miramos los cambios mes a mes.
- **MA (media móvil, q):** el valor de hoy depende de los errores que el modelo cometió recientemente.
- **S (estacional, s = 12):** lo mismo, pero mirando el mismo mes de años anteriores.

La notación es **SARIMA (p, d, q)(P, D, Q)₁₂**. Las mayúsculas son la versión estacional.

**Ejemplo real:** el modelo más repetido del proyecto (25 de 84 series) fue (0,1,2)(0,1,1)₁₂. En palabras: diferencia una vez, usa los dos últimos errores, diferencia estacionalmente una vez y usa el error del mismo mes del año anterior.

**¿Cómo se eligió?** Se probó una grilla acotada de combinaciones (p, q hasta 2; d, D de 0 a 1; P, Q hasta 1) y se eligió por **AIC**: un puntaje que premia el buen ajuste pero castiga la complejidad, como en el golf, **menos es mejor**. Se guarda el top 3 de cada serie.

**Lo que produce:** un pronóstico a 12 meses con bandas del 80 % y 95 %. Ejemplo real: para la mora de BISA, el pronóstico a 6 meses es 3,87 % con una banda del 95 % entre 2,24 % y 5,30 %. Esa banda es el «rango normal esperado».

**Cómo decirlo en la defensa:** «SARIMA es un modelo estándar, interpretable y adecuado para series mensuales con estacionalidad. Lo elegimos justamente por su transparencia.»

**Error típico:** leer la banda como una garantía. La banda describe la incertidumbre del proceso estimado, no un rango que el dato jamás pueda romper.

### 4.8 Backtesting (walk-forward)

**Analogía:** es el examen sorpresa del modelo. En vez de juzgarlo con los mismos datos con los que aprendió, se le «tapan» los últimos meses, se le pide que pronostique y luego se destapan para comparar.

**Cómo funciona aquí:** ventana expansiva sobre los últimos 12 meses. En cada paso el modelo se vuelve a ajustar con todo lo conocido hasta ese momento, pronostica el mes siguiente y se compara con lo que realmente pasó. Así nunca «ve el futuro» (no hay fuga de información).

**Los rivales a vencer (baselines):**

- **Naive:** el mes que viene será igual que este mes. Parece ingenuo, pero en finanzas es muy difícil de ganar.
- **Naive estacional:** el mes que viene será igual que el mismo mes del año pasado.

**Métricas:** RMSE, MAE y sMAPE, tres formas de medir qué tan lejos cayó el pronóstico del dato real. Menos es mejor en las tres.

**Resultado real y honesto:** el SARIMA superó al Naive en **26 de 84 series**. En 58 no lo superó, y el proyecto lo reporta sin esconderlo.

| Indicador | Series donde SARIMA supera a Naive |
| --- | --- |
| Mora | 6 de 12 |
| Cobertura | 4 de 12 |
| Liquidez | 7 de 12 |
| ROA | 4 de 12 |
| ROE | 3 de 12 |
| Crecimiento de cartera | 2 de 12 |
| Crecimiento de depósitos | 0 de 12 |
| **Total** | **26 de 84** |

**Ejemplo:** para la mora de BISA, el RMSE del SARIMA fue 0,401 y el del Naive 0,367. Ganó el Naive.

**Cómo decirlo en la defensa:** «El backtesting es la prueba más exigente del proyecto y no siempre salimos bien parados. Lo reportamos porque un modelo que solo muestra sus victorias no es evaluación, es propaganda. Además, en este sistema el modelo se usa para definir el rango esperado y detectar desviaciones, no como una bola de cristal.»

**Error típico:** esconder los casos en que el modelo pierde, o decir que «el modelo funciona» sin matices.

### 4.9 Cadenas de Markov

**Analogía:** el juego de mesa de casillas. Estás en una casilla (estado) y lanzas un dado cargado que decide a qué casilla pasas. Lo importante: la probabilidad de moverte depende **solo de la casilla en que estás ahora**, no de cómo llegaste. Eso es la propiedad de Markov: el sistema «no tiene memoria larga».

**En el proyecto:** la mora de cada banco se convierte en cuatro estados.

| Estado | Regla (mora) |
| --- | --- |
| Baja | menos de 1,5 % |
| Media | entre 1,5 % y 2,5 % |
| Alta | entre 2,5 % y 4,0 % |
| Crítica | más de 4,0 % |

Con la historia de cada banco se cuenta cuántas veces pasó de un estado a otro y eso arma la **matriz de transición**: una tabla 4×4 donde cada fila dice «estando hoy aquí, ¿con qué probabilidad estaré mañana en cada estado?». Cada fila suma 100 %.

**Ejemplo con BISA:** si hoy está en Alta, la probabilidad de seguir en Alta el mes siguiente es de aproximadamente 90 %. Eso implica que suele quedarse unos **10 meses** seguidos ahí (el tiempo medio de permanencia es 1 dividido entre la probabilidad de salir). En Crítica, la probabilidad de quedarse es de aproximadamente 76 %, lo que equivale a unos 4 meses.

**Cuatro ideas derivadas:**

- **Suavizado de Laplace (α = 0,001):** si un estado nunca se observó, su fila sería 0/0. El suavizado agrega una cantidad diminuta a cada casilla para que las filas siempre sumen 1. Ejemplo: BISA nunca estuvo en Baja, así que su fila Baja queda en 25 % para cada estado. No es un hallazgo, es el efecto del suavizado.
- **Distribución estacionaria (π):** a larguísimo plazo, ¿en qué porcentaje del tiempo estaría el banco en cada estado? Para BISA: Alta aproximadamente 74 % y Crítica aproximadamente 21 %.
- **Potencias P^h:** multiplicar la matriz por sí misma h veces responde «¿en qué estado estaré dentro de h meses?». Es lo que hace el simulador del dashboard con h de 1, 3, 6 y 12.
- **Prueba de orden 1 vs 2:** compara si basta con «la casilla de hoy» o si también importa la casilla de ayer. En la muestra no se rechaza el orden 1 en ningún banco, pero con 84 meses la prueba tiene poca potencia, así que eso no prueba que el orden 2 sea irrelevante.

**El caso BFORT:** su mora de diciembre 2025 fue 5,76 %. Su distribución estacionaria en Crítica es 99,5 % y la probabilidad de estar en Crítica a 3 meses es 99,97 %. Ojo: no es una predicción de quiebra. Es una **mora estructuralmente alta**: el banco lleva tanto tiempo en ese nivel que la cadena lo ve «atrapado» ahí.

**Cómo decirlo en la defensa:** «La cadena de Markov describe en qué nivel de mora suele estar cada banco y cuánto tiempo suele permanecer. No predice eventos; resume la dinámica histórica de los niveles.»

**Error típico:** leer 99,97 % como «probabilidad de quiebra». Es la probabilidad de permanecer en el estado de mora alta, nada más.

### 4.10 Residuos y z-score

**Analogía:** si en un curso el promedio es 14 con un desvío típico de 2, un 18 está a dos desvíos del promedio. No dices «está 4 puntos arriba» sino «está 2 desvíos arriba», porque eso se puede comparar entre cursos distintos.

**En el proyecto:** el **residuo** es la diferencia entre lo observado y lo que el modelo esperaba. El **z-score** es ese residuo dividido por su desviación típica. Así, un z de 2 significa lo mismo para la mora que para el ROA, aunque tengan escalas distintas.

**Regla de bolsillo:** con z cerca de 0 el dato es normal. Con |z| mayor que 2 empieza a ser inusual. Con |z| mayor que 3 es muy inusual.

**Error típico:** olvidar que mayor que 2 no es «anormal» por definición: incluso en una serie perfectamente normal, cerca de 1 de cada 20 datos lo superará por puro azar.

### 4.11 Alertas y CUSUM

**Analogía del CUSUM:** una alcancía. Una moneda sola no llama la atención, pero si cada mes cae una moneda en la misma alcancía, tarde o temprano pesa. CUSUM va sumando las pequeñas desviaciones en una misma dirección y avisa cuando el total supera un umbral (banda 5,0 en el proyecto). Detecta lo que un z-score aislado no ve: un cambio lento y sostenido.

**Las seis señales del motor de alertas:**

| Señal | Qué detecta | Alertas generadas |
| --- | --- | --- |
| Racha de deterioro | 3 o más meses seguidos empeorando, con cambio acumulado de al menos 0,5 desvíos | 651 |
| Fuera de banda 95 % | El dato cae fuera del rango esperado | 275 |
|  | z | mayor o igual a 2 |
| CUSUM | Desviaciones pequeñas acumuladas | 237 |
|  | z | mayor o igual a 3 |
| Salto de estado Markov | El banco sube de nivel de mora | 59 |

**Totales:** 1.073 alertas, de las cuales 268 son críticas, 213 de alerta y 592 de vigilancia. Cada una incluye una explicación en español de qué señal la activó.

**Cómo decirlo en la defensa:** «Las alertas son deterministas y explicables: cada una indica qué regla se activó y con qué magnitud. No hay una caja negra.»

**Error típico:** presentar el score de anomalía como una probabilidad. Es un resumen para ordenar bancos, no una probabilidad de nada.

### 4.12 Valor p

**Analogía:** el sorprendidometro. Parte de una suposición (la hipótesis nula) y se pregunta: «Si esta suposición fuera cierta, ¿qué tan raro sería ver datos como los míos?». Un p-valor chico (por ejemplo 0,01) dice que sería muy raro, y por eso se duda de la suposición.

**Lo que NO es:** no es la probabilidad de que la hipótesis sea cierta, ni la probabilidad de equivocarse. Y un p-valor grande no demuestra que la hipótesis sea cierta, solo que no hay evidencia suficiente contra ella.

**Cómo decirlo en la defensa:** «El p-valor mide qué tan compatibles son los datos con la hipótesis nula; no prueba hipótesis.»

## 5. Cómo se conecta todo: el recorrido de un dato

Sigamos un caso real, la mora de BISA en diciembre de 2025.

1. **Descarga y validación.** El archivo de la ASFI se baja, se verifica con SHA-256 y se comprueba que Activo = Pasivo + Patrimonio.
2. **Indicador.** Cartera en mora dividida entre cartera bruta da **3,07 %**.
3. **Estacionariedad.** ADF y KPSS sugieren si hay que diferenciar. Con eso se fijan d y D.
4. **SARIMA.** Se elige el mejor modelo por AIC y se calcula el rango esperado. Para esa fecha, el modelo esperaba una banda del 95 % de aproximadamente 2,24 % a 5,30 % a 6 meses.
5. **Backtest.** Se mide qué tan bien lo hizo antes. En este caso el SARIMA no superó al Naive, así que el pronóstico debe leerse con prudencia.
6. **Markov.** 3,07 % cae en el estado Alta (entre 2,5 % y 4 %). Se calcula cuánto suele durar ahí (unos 10 meses) y cómo evolucionaría.
7. **Alertas.** Se calcula el z-score del dato y se revisan las seis señales. Si alguna se activa, se genera una alerta con su explicación.
8. **Dashboard.** Todo se resume en una tarjeta por banco para que una persona lo lea sin necesidad de abrir ningún modelo.

La idea central: **ninguna pieza por sí sola concluye nada**. Cada una aporta un fragmento de evidencia y el sistema los junta de forma transparente.

## 6. Preguntas probables del tribunal

Cada pregunta tiene una **versión simple** (para empezar a responder con naturalidad) y una **versión técnica** (para cuando el tribunal profundiza). Empieza siempre por la simple.

### 1. ¿Por qué no dicen que el modelo predice quiebras?

- **Simple:** porque no lo hace. Medimos si un dato es raro respecto al historial del propio banco, no si el banco va a quebrar.
- **Técnica:** el objeto estimado es la distribución de un indicador, no la probabilidad de un evento de insolvencia. Una observación fuera de banda puede deberse a un cambio contable, una reclasificación o un choque macro; afirmar quiebra o causalidad excede los datos y el modelo.

### 2. ¿Qué significa que una serie sea «inconclusa»?

- **Simple:** que los dos testigos (ADF y KPSS) no se ponen de acuerdo y los datos no alcanzan para desempatar.
- **Técnica:** ambas pruebas no permiten una lectura única; por ejemplo, las dos pueden rechazar su hipótesis nula. Es frecuente en series cortas con estacionalidad marcada. Se reporta la discrepancia y se usa la diferenciación sugerida sin ocultar la incertidumbre.

### 3. ¿Por qué usar ADF y KPSS a la vez?

- **Simple:** porque preguntar a un solo testigo es arriesgado; si los dos coinciden, la conclusión es más sólida.
- **Técnica:** tienen hipótesis nulas opuestas. ADF busca evidencia contra la raíz unitaria; KPSS busca evidencia contra la estacionariedad.

### 4. ¿Por qué SARIMA y no un modelo más complejo?

- **Simple:** porque es transparente y se puede explicar paso a paso. Y el backtest muestra que más complejidad no garantiza ganar.
- **Técnica:** SARIMA es interpretable, estándar en series de tiempo y captura estacionalidad anual. La grilla se acota por costo computacional. El backtesting contra Naive y Naive estacional es una prueba exigente.

### 5. ¿Cómo eligieron el orden del SARIMA?

- **Simple:** probando muchas combinaciones y quedando con la que tiene mejor puntaje AIC.
- **Técnica:** AIC dentro de una grilla acotada, con d y D sugeridos por ADF/KPSS; se reporta el top 3. No se elige por desempeño fuera de muestra, para evitar fuga de información: el backtest es evaluación, no ajuste.

### 6. ¿Qué mide el score de anomalía?

- **Simple:** es una nota para ordenar a los bancos por cuántas señales inusuales tienen. No es una probabilidad.
- **Técnica:** resume el sistema de alertas por banco, combinando señales y su severidad. No debe interpretarse como probabilidad de quiebra ni como calificación regulatoria.

### 7. ¿Cómo calculan el ROA si la utilidad viene acumulada?

- **Simple:** como el odómetro: restan el acumulado del mes anterior para saber cuánto se ganó cada mes, suman 12 meses y dividen entre el activo promedio.
- **Técnica:** desacumulación mensual, suma móvil de 12 meses como utilidad anualizada y división entre el activo promedio de 12 meses. Las primeras observaciones se excluyen porque no hay ventana completa.

### 8. ¿Por qué usan suavizado de Laplace en Markov?

- **Simple:** para que no haya divisiones 0/0 cuando un banco nunca estuvo en cierto estado.
- **Técnica:** evita probabilidades nulas o indefinidas. Con α = 0,001 las celdas sin evidencia quedan cerca de cero (o uniformes si la fila entera no tiene transiciones) y cada fila suma 1.

### 9. ¿Qué valida el test de orden 1 contra orden 2?

- **Simple:** revisa si basta con saber dónde está hoy el banco o si también importa dónde estuvo ayer.
- **Técnica:** compara verosimilitudes de cadenas de primer y segundo orden. No se rechaza el orden 1 en ningún banco, pero eso no prueba que el orden 2 sea irrelevante: con 84 meses la potencia de la prueba es limitada.

### 10. ¿Cómo evitan el sobreajuste y la fuga de información?

- **Simple:** el modelo nunca ve los datos que luego intenta pronosticar, y las derrotas se reportan.
- **Técnica:** grilla acotada, backtesting con ventana expansiva reestimando en cada paso, baselines exigentes, y datos de validación que no se usan para elegir el orden.

### 11. ¿Qué pasa si la ASFI cambia el formato o la unidad?

- **Simple:** el sistema falla de forma visible o acepta un archivo manual; nunca inventa datos.
- **Técnica:** el parser detecta la unidad y normaliza a miles de bolivianos. Los datos sintéticos solo existen con la opción de demostración y llevan un banner rojo fijo.

### 12. ¿Por qué el dashboard funciona sin servidor?

- **Simple:** porque los datos viajan dentro de la propia página y se abre con doble clic.
- **Técnica:** `data.js` asigna el contrato a una variable global y la aplicación no hace peticiones de red. *(Actualiza esta respuesta cuando el dashboard nuevo esté listo.)*

### 13. ¿Por qué hay tantas alertas (1.073)?

- **Simple:** porque el sistema prefiere avisar de más antes que quedarse corto. Más de la mitad (592) son del nivel más bajo, «vigilancia».
- **Técnica:** la regla de racha de deterioro genera 651 alertas y es la más sensible. Es una limitación reconocida; una mejora natural sería endurecer ese umbral o agrupar alertas consecutivas del mismo banco e indicador.

### 14. ¿Por qué un banco con mora baja sale en rojo y otro con mora alta en verde?

- **Simple:** porque el semáforo mide qué tan raro es el comportamiento reciente del banco **respecto a sí mismo**, no qué tan alta es su mora.
- **Técnica:** en los resultados, BSOL aparece en rojo con una mora de 1,50 % y BNB en verde con 3,49 %. El score combina desviaciones del proceso estimado de cada serie, no el nivel. Por eso conviene presentarlo como nivel de atención y no como calificación de riesgo.

### 15. ¿Qué significa el caso BFORT?

- **Simple:** que lleva mucho tiempo con una mora alta (5,76 % en diciembre de 2025) y el modelo lo ve «atrapado» en ese nivel.
- **Técnica:** su distribución estacionaria en el estado Crítica es 0,995 y la probabilidad de estar en Crítica a 3 meses es 0,9997. Es persistencia estructural, no una predicción de evento.

## 7. Frases para evitar y frases recomendadas

**Evita:**

- «El modelo predice que el banco va a quebrar.»
- «La probabilidad de quiebra es X %.»
- «El banco está en riesgo crítico según el modelo.»
- «El p-valor demuestra que la hipótesis es falsa.»
- «El modelo funciona» (sin matices).

**Usa:**

- «La observación se aleja del intervalo esperado por el proceso estimado.»
- «La señal es compatible con una anomalía; la causa requiere análisis adicional.»
- «El backtesting no siempre supera al baseline y se reporta sin ocultarlo.»
- «El sistema es una herramienta descriptiva, no una calificación de solvencia.»
- «No forzamos una conclusión cuando los contrastes discrepan.»

## 8. Hoja resumen de una página

**Idea central:** un monitor que avisa cuando un indicador bancario se aleja de lo normal para ese banco. No predice quiebras.

| Concepto | En una frase |
| --- | --- |
| Serie de tiempo | Un valor por mes de un indicador de un banco |
| Proceso estocástico | La «máquina» con reglas y azar que genera la serie |
| Estacionariedad | La serie oscila alrededor de un nivel estable |
| Raíz unitaria | Caminata del borracho: los choques son permanentes |
| ADF / KPSS | Dos testigos con versiones opuestas por defecto |
| ACF / PACF | El eco de la serie: total y directo |
| Regresión HAC | Descompone tendencia y estacionalidad con errores corregidos |
| SARIMA | Receta con memoria de valores y de errores, con ciclo de 12 meses |
| AIC | Puntaje de ajuste que castiga la complejidad; menos es mejor |
| Backtesting | Examen sorpresa fuera de muestra contra rivales simples |
| Markov | Casillas de mora con probabilidades de pasar de una a otra |
| Laplace | Un granito de probabilidad para que ninguna fila quede en 0/0 |
| Distribución estacionaria | Porcentaje del tiempo en cada estado a muy largo plazo |
| z-score | Cuántos desvíos se aleja el dato de lo esperado |
| CUSUM | Alcancía que suma pequeñas desviaciones en la misma dirección |
| Valor p | Qué tan raros serían los datos si la hipótesis nula fuera cierta |

**Números para memorizar:**

- 84 meses (2019-01 a 2025-12), 12 bancos, 1.008 observaciones, 84 series.
- Balanza contable: 0 fallos.
- Estacionariedad: 44 inconclusas, 35 raíz unitaria pura, 4 estacionarias, 1 en tendencia.
- Modelo más frecuente: SARIMA (0,1,2)(0,1,1)₁₂ en 25 series.
- Backtest: SARIMA supera a Naive en 26 de 84 series.
- Markov: umbrales 1,5 % / 2,5 % / 4,0 %; Laplace α = 0,001.
- Alertas: 1.073 (268 críticas, 213 de alerta, 592 de vigilancia).
- BFORT: mora 5,76 %, π(Crítica) = 0,995.

## 9. Glosario

- **AIC:** criterio que equilibra ajuste y complejidad del modelo; menor es mejor.
- **Baseline:** método simple contra el que se compara un modelo para saber si aporta algo.
- **Banda o intervalo de predicción:** rango donde se espera que caiga el dato futuro según el modelo.
- **Diferenciar:** trabajar con los cambios entre meses en lugar de con los niveles.
- **Estacionalidad:** patrón que se repite cada cierto período (aquí, cada 12 meses).
- **Fuga de información:** que el modelo «vea» datos del futuro al entrenarse; invalida la evaluación.
- **Hipótesis nula:** la suposición de partida de una prueba estadística.
- **Mora:** proporción de la cartera de préstamos que está atrasada.
- **Naive:** pronóstico que repite el último dato observado.
- **Residuo:** diferencia entre el dato observado y el esperado por el modelo.
- **Sobreajuste:** modelo tan pegado a los datos pasados que falla con datos nuevos.
- **Walk-forward:** evaluación que avanza en el tiempo, reajustando el modelo en cada paso.

## 10. Plan de repaso en tres sesiones

1. **Sesión 1 (45 min):** capítulos 1 a 3. Al final, cuenta el proyecto en voz alta en dos minutos sin mirar.
2. **Sesión 2 (60 min):** capítulo 4. Para cada concepto, di la analogía y la frase de defensa de memoria.
3. **Sesión 3 (45 min):** capítulos 6 y 7. Responde en voz alta las 15 preguntas, primero en versión simple y luego en técnica, y repasa los números de la hoja resumen.
