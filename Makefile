# =============================================================================
# Orquestación del pipeline. Requiere GNU Make (Windows: choco install make).
# Alternativa sin Make: ejecutar las mismas líneas con `python -m ...`.
# =============================================================================

PY ?= python
.DEFAULT_GOAL := help

.PHONY: help install explore scrape historico etl synth model export notebooks informe test lint format serve clean

help:  ## Muestra esta ayuda
	@echo "Objetivos disponibles:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-12s %s\n", $$1, $$2}'

install:  ## Instala dependencias (incluye dev)
	$(PY) -m pip install -e ".[dev]"

explore:  ## Reconocimiento del portal ASFI (solo lectura, no descarga masiva)
	$(PY) -m src.scraping.reconocimiento

scrape:  ## Descarga resiliente de EEFF/boletines con manifiesto SHA-256
	$(PY) -m src.scraping.descargador

historico:  ## Descarga la serie mensual verificada (2019-01 a 2025-12, 84 meses)
	$(PY) -m src.scraping.historico --tipo eeff --desde 2019-01 --hasta 2025-12

synth:  ## Genera datos sintéticos realistas (activa banner de demostración)
	$(PY) -m src.etl.synth --demo

etl:  ## Parsea data/raw/, normaliza y construye paneles en data/processed/
	$(PY) -m src.etl.pipeline

model:  ## Motor estocástico: estacionariedad, SARIMA, Markov, alertas
	$(PY) -m src.models.pipeline

export:  ## Valida esquema y exporta dashboard/data.json y dashboard/data.js
	$(PY) -m src.export.exportador

notebooks:  ## Ejecuta y guarda las salidas de los 4 notebooks
	$(PY) -m jupyter nbconvert --to notebook --execute --inplace --ExecutePreprocessor.timeout=240 notebooks/*.ipynb

informe:  ## Compila el informe LaTeX en docs/ y limpia auxiliares
	pdflatex -interaction=nonstopmode -halt-on-error -output-directory=docs docs/informe_final.tex
	pdflatex -interaction=nonstopmode -halt-on-error -output-directory=docs docs/informe_final.tex
	$(PY) -c "import pathlib; [p.unlink() for p in pathlib.Path('docs').glob('informe_final.*') if p.suffix in {'.aux', '.log', '.out', '.toc'}]"

test:  ## Ejecuta la suite de pruebas
	$(PY) -m pytest

lint:  ## Análisis estático con ruff
	$(PY) -m ruff check src tests notebooks

format:  ## Formatea con black e importa con ruff
	$(PY) -m black src tests
	$(PY) -m ruff check --fix src tests

serve:  ## Sirve el dashboard localmente (opcional; también abre con file://)
	$(PY) -m http.server 8000 --directory dashboard

clean:  ## Limpia artefactos temporales (conserva data/raw/)
	$(PY) -c "import shutil,pathlib; [shutil.rmtree(p, ignore_errors=True) for p in ['data/interim','data/processed','.pytest_cache','.ruff_cache']]"

