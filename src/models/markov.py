"""Cadenas de Markov en tiempo discreto sobre el Índice de Morosidad."""

from __future__ import annotations

import numpy as np
from scipy import stats

from .utilidades import a_primitivo


def discretizar(valores: list[float], umbrales_fraccion: list[float]) -> np.ndarray:
    """Clasifica mora (%) en 4 estados usando umbrales expresados en fracción."""
    cortes = np.round(np.asarray(umbrales_fraccion, dtype=float) * 100, 10)
    return np.digitize(np.asarray(valores, dtype=float), cortes, right=False).astype(int)


def contar_transiciones(estados: np.ndarray, k: int) -> np.ndarray:
    conteos = np.zeros((k, k), dtype=float)
    for actual, siguiente in zip(estados[:-1], estados[1:], strict=False):
        conteos[int(actual), int(siguiente)] += 1
    return conteos


def estimar_matriz(conteos: np.ndarray, alpha: float = 1e-3) -> np.ndarray:
    matriz = conteos + alpha
    totales = matriz.sum(axis=1, keepdims=True)
    return matriz / totales


def distribucion_estacionaria(matriz: np.ndarray) -> np.ndarray:
    valores, vectores = np.linalg.eig(matriz.T)
    indice = int(np.argmin(np.abs(valores - 1.0)))
    vector = np.real(vectores[:, indice])
    vector = np.abs(vector)
    total = vector.sum()
    return vector / total if total > 0 else np.full(matriz.shape[0], 1 / matriz.shape[0])


def tiempo_permanencia(matriz: np.ndarray) -> list[float]:
    diagonal = np.clip(np.diag(matriz), 0.0, 1.0 - 1e-9)
    return [float(1.0 / (1.0 - valor)) for valor in diagonal]


def _loglik(conteos: np.ndarray, matriz: np.ndarray) -> float:
    mascara = conteos > 0
    if not mascara.any():
        return 0.0
    return float(np.sum(conteos[mascara] * np.log(matriz[mascara])))


def prueba_orden(estados: np.ndarray, k: int, alpha: float = 1e-3) -> dict:
    """Razón de verosimilitudes Orden 1 vs Orden 2."""
    if len(estados) < 3 * k:
        return {"pval": None, "cumple": None}
    conteos1 = contar_transiciones(estados, k)
    matriz1 = estimar_matriz(conteos1, alpha)
    ll1 = _loglik(conteos1, matriz1)

    conteos2 = np.zeros((k * k, k), dtype=float)
    for i, j, m in zip(estados[:-2], estados[1:-1], estados[2:], strict=False):
        conteos2[int(i) * k + int(j), int(m)] += 1
    filas = conteos2.sum(axis=1)
    if np.count_nonzero(filas) < 2:
        return {"pval": None, "cumple": None}
    matriz2 = estimar_matriz(conteos2, alpha)
    ll2 = _loglik(conteos2, matriz2)

    grados_libertad = k * (k - 1) * (k - 1)
    estadistico = max(0.0, 2.0 * (ll2 - ll1))
    pval = float(stats.chi2.sf(estadistico, grados_libertad))
    return {"pval": pval, "cumple": bool(pval > 0.05)}


def _bloque(nombre: str, secuencia: np.ndarray, k: int, alpha: float) -> dict:
    conteos = contar_transiciones(secuencia, k)
    matriz = estimar_matriz(conteos, alpha)
    estacionaria = distribucion_estacionaria(matriz)
    ultimo = int(secuencia[-1])
    potencias = {}
    for horizonte, clave in ((1, "m1"), (3, "m3"), (6, "m6"), (12, "m12")):
        potencias[clave] = float(np.linalg.matrix_power(matriz, horizonte)[ultimo, k - 1])
    prueba = prueba_orden(secuencia, k, alpha)
    return {
        "banco_id": nombre,
        "matriz_transicion": [[float(v) for v in fila] for fila in matriz],
        "dist_estacionaria": [float(v) for v in estacionaria],
        "tiempo_permanencia_meses": tiempo_permanencia(matriz),
        "prob_critico_h": potencias,
        "test_orden_1_vs_2_pval": prueba["pval"],
        "cumple_propiedad_markov": prueba["cumple"],
        "estado_actual": ultimo,
        "secuencia_estados": [int(v) for v in secuencia],
    }


def analizar_markov(
    mora_por_banco: dict[str, list[float]],
    config: dict,
) -> dict:
    estados = list(config["markov"]["estados"])
    umbrales = [float(v) for v in config["markov"]["umbrales"]]
    alpha = float(config["markov"].get("laplace_alpha", 1e-3))
    k = len(estados)

    por_banco: dict[str, dict] = {}
    secuencias: list[np.ndarray] = []
    for banco, valores in mora_por_banco.items():
        if not valores:
            continue
        secuencia = discretizar(valores, umbrales)
        secuencias.append(secuencia)
        bloque = _bloque(banco, secuencia, k, alpha)
        bloque.pop("banco_id")
        por_banco[banco] = bloque

    conteos = np.zeros((k, k), dtype=float)
    for secuencia in secuencias:
        conteos += contar_transiciones(secuencia, k)
    matriz = estimar_matriz(conteos, alpha)
    agregado = {
        "matriz_transicion": [[float(v) for v in fila] for fila in matriz],
        "dist_estacionaria": [float(v) for v in distribucion_estacionaria(matriz)],
    }
    return a_primitivo(
        {
            "estados": estados,
            "umbrales": umbrales,
            "por_banco": por_banco,
            "sistema_agregado": agregado,
        }
    )


def umbrales_para_dashboard(config: dict) -> list[float]:
    return [float(v) for v in config["markov"]["umbrales"]]


def probabilidades_agregadas(matriz: np.ndarray, horizontes: list[int]) -> dict:
    potencias = {}
    for horizonte, clave in zip(horizontes, [f"m{h}" for h in horizontes], strict=False):
        potencias[clave] = [
            [float(v) for v in fila] for fila in np.linalg.matrix_power(matriz, horizonte)
        ]
    return potencias


__all__ = [
    "analizar_markov",
    "contar_transiciones",
    "discretizar",
    "distribucion_estacionaria",
    "estimar_matriz",
    "probabilidades_agregadas",
    "prueba_orden",
    "tiempo_permanencia",
    "umbrales_para_dashboard",
]
