# Sistema de Alerta Temprana Estocástica sobre EEFF Bancarios (ASFI Bolivia)

Pipeline académico que detecta **desviaciones estocásticas y anomalías** en indicadores
financieros de bancos múltiples bolivianos publicados por la ASFI, con dashboard analítico
estático autocontenido.

> **Descargo metodológico:** este sistema NO predice quiebras ni insolvencias bancarias.
> Mide si el valor observado de un indicador se aleja del intervalo esperado por su
> proceso generador de datos.

**Estado:** Compuertas 0–4 completadas y aprobadas; entrega académica cerrada.

## Requisitos

- Python 3.11+
- GNU Make (opcional, para los atajos del `Makefile`)

## Instalación

```bash
python -m pip install -e ".[dev]"
```

## Flujo del pipeline

```bash
make explore   # Reconocimiento del portal ASFI (no descarga masiva)
make scrape    # Descarga resiliente con manifiesto SHA-256 y caché
make historico # Serie mensual verificada 2019-01 → 2025-12 (84 archivos)
make synth     # Alternativa: datos sintéticos con banner de demostración
make etl       # Parsers multi-formato + validación contable + indicadores
make model     # Estacionariedad, OLS-HAC, SARIMA, Markov, alertas
make export    # Valida esquema y genera dashboard/data.json y data.js
make notebooks # Ejecuta los 4 notebooks y guarda sus salidas
make informe   # Compila docs/informe_final.tex con pdflatex
make serve     # Sirve dashboard/ en http://localhost:8000 (opcional)
make test      # Suite pytest
```

Sin `make`, ejecutar los mismos módulos con `python -m ...` (ver `Makefile`).
El ETL genera `data/processed/panel_contable.parquet`,
`data/processed/panel_indicadores.parquet` y `docs/calidad_datos.md`.
El motor genera `data/processed/modelos_meta.json`, `dashboard/data.json` y
`dashboard/data.js`, validados con Pydantic.

## Dashboard

Abrir directamente `dashboard/index.html` (funciona por `file://`). El archivo
`dashboard/data.js` carga el contrato en `window.ASFI_DATA`; no se requiere servidor.

El tablero incluye radar de bancos con sparklines, serie observada y pronóstico con
bandas 80 % / 95 %, diagnóstico ADF/KPSS, ACF/PACF, Q-Q, regresión HAC, SARIMA,
backtesting, matriz de Markov interactiva con simulador \(P^h\), tabla de alertas y
glosario KaTeX. Chart.js, Motion, Tailwind y KaTeX se cargan por CDN; si no hay
internet, los datos siguen locales pero pueden faltar estilos o fórmulas.

## Notebooks y documentación

```bash
python -m jupyter nbconvert --to notebook --execute --inplace notebooks\*.ipynb
```

- `notebooks/01_estacionariedad.ipynb`: ADF, KPSS, ACF y PACF.
- `notebooks/02_arima_sarima.ipynb`: reestimación SARIMA, pronóstico y backtesting.
- `notebooks/03_cadenas_markov.ipynb`: matriz de transición, distribución estacionaria y potencias.
- `notebooks/04_motor_alertas.ipynb`: residuos, CUSUM y alertas.
- `docs/metodologia.md`: fórmulas, supuestos y limitaciones.
- `docs/informe_final.tex`: informe LaTeX listo para Overleaf.
- `docs/informe_final.pdf`: versión compilada del informe (6 páginas, 267.545 bytes).
- `docs/guia_defensa.md`: guion de 10 minutos y preguntas del tribunal.
- `docs/modelos_resumen.md`: resultados del motor estocástico.

## Resultados de la muestra real

- 84 meses continuos (2019-01 a 2025-12), 12 bancos, 1.008 observaciones banco-mes.
- Identidad contable: 0 fallos; diferencia máxima de 0,001620 miles de BOB.
- 84/84 series modeladas; el SARIMA supera a Naive en 26/84.
- 1.073 alertas: 268 críticas, 213 de alerta y 592 de vigilancia.
- Semáforos: 5 rojos, 1 naranja, 2 amarillos y 4 verdes.

## Estructura

```text
config.yaml            Catálogo de bancos, mapeo PUC, umbrales y grillas
data/raw/              Archivos originales inmutables + manifest.csv
data/interim/          Parquet normalizado por archivo
data/processed/        Paneles contables y de indicadores
docs/                  Exploración, calidad, metodología, defensa e informe LaTeX
src/scraping/          Cliente HTTP con backoff y caché
src/etl/               Parsers polimórficos y generador sintético
src/indicators/        Motor de cálculo financiero
src/models/            Motor econométrico y alertas
src/backtest/          Evaluación walk-forward vs baselines
src/export/            Validación Pydantic y exportación
notebooks/             Material de defensa oral
dashboard/             SPA estática (abrir index.html directamente)
```

## Modo demostración

Si el portal de la ASFI no está disponible, generar datos sintéticos:

```bash
python -m src.etl.synth --demo
python -m src.etl.pipeline --demo
```

El dashboard mostrará de forma fija el banner
`MODO DEMOSTRACIÓN — DATOS SINTÉTICOS`.

## Carga manual de datos

Colocar los archivos descargados manualmente en `data/raw/` respetando la convención
`{AAAA}/{MM}/{tipo_entidad}_{archivo}.{ext}`; el ETL los procesará sin necesidad de red.

## Fuentes verificadas de ASFI (Compuerta 1)

Los archivos mensuales de **Bancos Múltiples** se publican en la ruta descubierta en el
JavaScript público del portal (`bmu-bol.js`, ver `docs/exploracion_asfi.md`):

```text
https://www.asfi.gob.bo/sites/default/files/estadisticaif/bancos_multiples/{AAAA}/{MM}/{AAAA}{MM}_BMU_EstadosFinancieros.zip
https://www.asfi.gob.bo/sites/default/files/estadisticaif/bancos_multiples/{AAAA}/{MM}/{AAAA}{MM}_BMU_IndicadoresFinancieros.zip
https://www.asfi.gob.bo/sites/default/files/estadisticaif/bancos_multiples/{AAAA}/{MM}/{AAAA}{MM}_BMU_EstadosFinancieros_Evolutivo.zip
```

Disponibilidad confirmada: 2014-12 a 2025-12. Cada ZIP contiene `.xls` binario con
filas = cuentas PUC y columnas = entidades (siglas oficiales ASFI).

Ejemplo de descarga puntual (el descargador no inventa rutas ni descarga masivamente):

```bash
python -m src.scraping.descargador --url "<URL verificada>"
python -m src.scraping.historico --tipo eeff --desde 2019-01 --hasta 2025-12
```

`python -m src.scraping.reconocimiento` regenera la evidencia en
`docs/exploracion_asfi.md`.
