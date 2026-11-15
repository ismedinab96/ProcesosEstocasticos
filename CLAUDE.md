# CLAUDE.md — Memoria Persistente del Agente

> Este archivo resume las reglas, guardrails, skills y contratos que rigen el proyecto.
> Debe leerse al inicio de cada sesión. La especificación completa vive en `AGENTS.md`.

---

## 1. Identidad del Proyecto

**Sistema de Alerta Temprana Estocástica sobre Estados Financieros Bancarios (ASFI Bolivia).**

Stack: Python 3.11+ (pipeline) + SPA estática autocontenida (dashboard vía `file://`).
Todo el código, documentación, interfaz e informes en **español**.

---

## 2. Reglas Inmutables (Guardrails)

1. **Honestidad estadística:** Se miden *desviaciones estocásticas y anomalías* en indicadores financieros. **Prohibido** afirmar que el modelo predice insolvencias o quiebras. Todo texto/UI incluye el descargo metodológico.
2. **Integridad de fuentes:** Casos de estudio (ej. UENO, intervenciones históricas) requieren el marcador `[CITAR FUENTE VERIFICADA]`. Nada de afirmaciones fácticas no verificadas.
3. **Cero datos inventados silenciosos:** Prohibido interpolar en secreto o inventar si falla el scraper. Datos sintéticos **solo** con flag `--demo` y banner rojo fijo: `"MODO DEMOSTRACIÓN — DATOS SINTÉTICOS"`.
4. **Cero alucinación de rutas ASFI:** No adivinar URLs. Primero script de reconocimiento; soportar carga manual (*drop-in*) en `data/raw/`.
5. **Scraping responsable:** Respetar `robots.txt`, pausas (*rate limit*), `User-Agent` identificable, reintentos con *backoff* exponencial, caché local SHA-256.
6. **Protocolo de compuertas:** No iniciar Fase N+1 sin ejecutar la verificación de Fase N, mostrar el resumen y recibir confirmación explícita.

---

## 3. Skills Activos para la Fase 5 (Dashboard)

### Skill 1 — `executive-fintech-ui`
- Estética *Quantitative Fintech Terminal* (Bloomberg / Linear / Stripe Radar).
- Fondo `#060913` con malla de puntos CSS (`radial-gradient`), tarjetas *glassmorphic* (`backdrop-blur-xl`, borde `1px solid rgba(255,255,255,0.08)`, brillo interno `inset 0 1px 0 rgba(255,255,255,0.12)`), modo claro de alto contraste.
- Tipografía: `Inter` (UI) + `JetBrains Mono` con `font-variant-numeric: tabular-nums` (KPIs, p-valores, z-scores, fechas, matrices).
- *Command Dock* flotante: selector banco/indicador sincronizado, búsqueda de alertas (`Cmd/Ctrl+K`), toggle de tema, botón de glosario.

### Skill 2 — `motion-choreography`
- Librería **Motion** (`https://cdn.jsdelivr.net/npm/motion@11.11.13/+esm`).
- Física: UI `stiffness: 380, damping: 32`; transiciones `ease: [0.22, 1, 0.36, 1]`.
- Patrones: *Hero Stagger* (`stagger(0.06)`), contadores con `animate(prevVal, nextVal, {duration: 0.55})`, *Shared Layout Pill* deslizante, revelado por scroll (`inView`, `once: true`), pulso perimetral en bancos Alerta/Crítica, barra de progreso de lectura (`scroll()`).
- Solo animar `transform` y `opacity`. Si `prefers-reduced-motion: reduce` → duraciones a `0ms`.

### Skill 3 — `interactive-dataviz-craft`
- Chart.js: reciclar instancias, nunca destruir `<canvas>`; actualizar `chart.data.datasets` + `chart.update('active')`.
- Micro-sparklines (24 meses de Mora) en tarjetas de banco; clic selecciona el banco.
- *Cross-filtering*: clic en punto/fila resalta el mes, abre diagnóstico y hace scroll suave.
- Matriz de Markov en CSS Grid con hover fila/columna y tooltip natural.
- Simulador `P^h` en JS puro con slider `h ∈ {1,2,3,6,12}`.

### Skill 4 — `statistical-storytelling`
- Paneles de interpretación dinámica: *Cómo leer esta gráfica*, *Hallazgo estadístico actual* (interpolando p-valores, órdenes, RMSE vs. Naive), *Limitación metodológica*.
- Drawer lateral de glosario con KaTeX CDN: Estacionariedad, Raíz Unitaria, SARIMA, Intervalo de Predicción, Cadena de Markov, Distribución Estacionaria, Valor p.

---

## 4. Contrato de Datos (`data.json` / `window.ASFI_DATA`)

Esquema validado con Pydantic. Estructura raíz:

```
meta | bancos[] | indicadores_meta[] | series{banco}{indicador} | markov | alertas[]
```

Claves por serie: `fechas`, `observado`, `ajuste_in_sample`, `residuos_estandarizados`, `pronostico{...}`, `estacionariedad{...}`, `regresion_ols{...}`, `sarima{...}`, `backtest{...}`.

Ver `AGENTS.md` §2 para el esquema completo campo a campo.

---

## 5. Arquitectura de Módulos

| Módulo | Responsabilidad |
|---|---|
| `src/scraping/` | Cliente HTTP con backoff, caché SHA-256, fallback local, manifiesto |
| `src/etl/` | Parsers polimórficos (.xls BIFF8, .xlsx, HTML-xls), normalización PUC, validador contable, generador `--demo` |
| `src/indicators/` | Motor de cálculo financiero (desacumulación de flujos, promedios) |
| `src/models/` | Estacionariedad, OLS-HAC, SARIMA paralelizado, Markov, alertas |
| `src/backtest/` | Walk-forward vs Naive / Seasonal Naive |
| `src/export/` | Validador Pydantic → `data.json` y `data.js` |
| `dashboard/` | SPA estática autocontenida vía `file://` |

---

## 6. Decisiones y Convenciones

- **Modo de datos:** Exploración real del portal ASFI + generador `--demo` en paralelo.
- **Archivos locales:** Ninguno disponible al inicio; soportar *drop-in* manual.
- **Plazo:** Sin deadline fijo; prioridad al rigor sobre la velocidad.
- **Desacumulación de Utilidad Neta:** flujo mensual `ΔU_t = U_t − U_{t-1}` para `t > enero`, anualizado con suma móvil de 12 meses; dividir entre Activo/Patrimonio promedio de 12 meses. Documentar en `docs/metodologia.md`.
- **Interpolación:** solo huecos aislados ≤ 2 meses; huecos mayores truncan al tramo continuo más reciente (≥ 60 meses recomendados; marcar `"insuficiente"`).
- **Grilla SARIMA:** `p,q ∈ {0,1,2}`, `d ∈ {0,1}`, `P,Q ∈ {0,1}`, `D ∈ {0,1}`, `s=12`, `enforce_stationarity=False`, `enforce_invertibility=False`, `maxiter=50`. Paralelizar con `joblib.Parallel(n_jobs=-1)`.
- **Markov:** 4 estados (*Baja, Media, Alta, Crítica*), suavizado de Laplace `α = 10⁻³`.

---

## 7. Estado de Compuertas

- [x] **Compuerta 0:** `CLAUDE.md` + esqueleto + configuración base
- [x] **Compuerta 1:** Exploración ASFI + scraper + generador `--demo` *(aprobada)*
- [x] **Compuerta 2:** ETL + catálogo contable + indicadores + tests *(aprobada)*
- [x] **Compuerta 3:** Motor estocástico + backtest + export validado *(aprobada)*
- [x] **Compuerta 4:** Dashboard con skills + notebooks + LaTeX + guía de defensa *(aprobada)*

## 8. Hallazgos de la Compuerta 1

- Fuente real de Bancos Múltiples: `/sites/default/files/estadisticaif/bancos_multiples/{AAAA}/{MM}/{AAAA}{MM}_BMU_EstadosFinancieros.zip` (patrón hallado en el JS público `bmu-bol.js`).
- Disponibilidad mensual verificada: al menos 2014-12 → 2025-12 (133 meses), suficiente para `s=12`.
- Cada ZIP contiene un `.xls` BIFF8 con matriz transpuesta (filas = cuentas PUC, columnas = bancos por sigla ASFI).
- Siglas oficiales confirmadas en PDF ASFI: BNB, BUN, BME, BIS, BCR, BGA, BEC, BSO, BNA, BIE, BFO, BPR.
- El catálogo `config.yaml` ya tiene `codigo_asfi` alineado a esas siglas.
- Evidencia reproducible: `python -m src.scraping.reconocimiento` regenera `docs/exploracion_asfi.md`.
- Datos sintéticos listos: `data/raw/demo/panel_sintetico_demo.csv` (1.008 filas, 2019-01 → 2025-12).

## 9. Hallazgos de la Compuerta 2

- Serie real descargada: 60 archivos mensuales BMU (2021-01 → 2025-12), 720 observaciones banco-mes, 12 bancos, sin huecos.
- `python -m src.scraping.historico --tipo eeff --desde 2021-01 --hasta 2025-12` usa la plantilla verificada y el manifiesto SHA-256.
- Parser BMU: normaliza etiquetas (sin acentos, sin paréntesis ni prefijos `(=)`/`(-)`), detecta encabezado por siglas ASFI y escala a miles de bolivianos.
- Cuentas canónicas: Mora = `CARTERA VENCIDA TOTAL` + `CARTERA EJECUCIÓN TOTAL`; obligaciones de corto plazo = suma de 6 rubros; previsión se toma en valor absoluto.
- Identidad contable real: 720/720 registros cumplen `|Activo − (Pasivo + Patrimonio)| ≤ 1` (máx. 0,00162 miles de BOB).
- Indicadores reales 2025-12 (mora %): bfort 5,76; bme 3,81; bnb 3,49; bun 3,45; bisa 3,07; bec 2,79; bfie 2,63; bcr 2,58; bga 2,46; bsol 1,50; bpro 1,11; bna 0,00.
- ROA/ROE disponibles desde 2021-12 (588 observaciones); crecimiento interanual desde 2022-01 (576).
- Verificación: `python -m pytest -q` → 54 passed; `ruff` y `black --check` limpios.
- Artefactos: `data/processed/panel_contable.parquet`, `data/processed/panel_indicadores.parquet`, `data/processed/etl_meta.json`, `docs/calidad_datos.md`.
- Resuelto en Compuerta 3: `statsmodels` y demás dependencias del motor instaladas.


## 10. Hallazgos de la Compuerta 3

- Serie ampliada a 84 meses reales (2019-01 → 2025-12); ROA/ROE y crecimientos ya cumplen el mínimo de 60 observaciones.
- Dependencias instaladas: `statsmodels 0.14.6`, `pmdarima 2.1.1`, `scipy`, `joblib`, `pydantic`, `tenacity`.
- SARIMA: grilla acotada con `p+q ≤ 3`, `P+Q ≤ 1` y `d/D` sugeridos por ADF/KPSS; 84/84 series modeladas; top 3 por AIC exportado.
- Backtest walk-forward (12 meses): el SARIMA supera al Naive en 26/84 series; `supera_baseline` se reporta sin ocultar los 58 casos desfavorables.
- Markov: umbrales `1,5 % / 2,5 % / 4,0 %`; bfort queda estructuralmente en estado Crítica (π≈0,995). El test de orden 2 no rechaza orden 1 en ningún banco (p≈1).
- Alertas: 1.073 (268 crítica, 213 alerta, 592 vigilancia). La banda de un paso usa `media ± 1,96 σ_residuos` para evitar intervalos demasiado estrechos de `get_prediction`.
- Semáforos: rojo 5 (bisa, bun, bec, bsol, bfort), naranja 1 (bcr), amarillo 2 (bga, bpro), verde 4 (bnb, bme, bna, bfie).
- Contrato validado con Pydantic en `src/export/esquema.py`; salidas `dashboard/data.json` (≈3,5 MB) y `dashboard/data.js` (≈2,0 MB).
- Verificación: 81 tests passed; `ruff` y `black --check` limpios.
- Documento de resultados: `docs/modelos_resumen.md`.
- Resuelto en Compuerta 4: dashboard, notebooks, informe LaTeX, guía de defensa y `docs/metodologia.md`.

## 11. Hallazgos de la Compuerta 4

- Dashboard creado en `dashboard/index.html` con estilos locales en `dashboard/assets/styles.css` y lógica en `dashboard/assets/app.js`; carga `data.js` por `file://`.
- Vistas implementadas: radar de 12 bancos con sparklines, KPIs, serie observada/ajuste/pronóstico con bandas 80/95, residuos, ACF/PACF/Q-Q, diagnóstico ADF/KPSS/OLS/SARIMA/backtest, matriz Markov interactiva con slider $P^h$, tabla de alertas con filtros y glosario KaTeX.
- Motion se carga por CDN como módulo y activa hero stagger, contadores, revelado por scroll, pastillas deslizantes y pulso CSS en bancos rojos/naranjas. Si falla el CDN o `prefers-reduced-motion`, la interfaz sigue operativa sin animación.
- Verificación headless con Chrome: 12 tarjetas, 16 celdas de matriz, 60 alertas iniciales, 17 gráficos Chart.js, sin errores de consola. Se probaron cambio de banco, indicador, slider Markov, clic en alerta, glosario y tema.
- Notebooks ejecutados con `nbconvert`: `01_estacionariedad`, `02_arima_sarima`, `03_cadenas_markov`, `04_motor_alertas`.
- Documentos nuevos: `docs/metodologia.md`, `docs/informe_final.tex`, `docs/guia_defensa.md`; `README.md` actualizado a 84 meses y Compuerta 4.
- `Makefile`: histórico 2019-01→2025-12, targets `notebooks` e `informe`, y `lint` incluye notebooks.
- `pyproject.toml` agrega `matplotlib` a dependencias de desarrollo para notebooks.
- Verificación: `pytest` 81 passed; `ruff` y `black --check` limpios (notebooks omitidos por black sin extra jupyter); `node --check` OK; `docs/informe_final.pdf` compilado (6 páginas, 267.545 bytes).
- Compuerta 4 aprobada explícitamente por el usuario; proyecto cerrado en su alcance académico definido.
- Preparación de despliegue: `render.yaml` define un sitio estático desde `dashboard/`; `dashboard/data.js` se versiona y `dashboard/data.json` sigue ignorado.
