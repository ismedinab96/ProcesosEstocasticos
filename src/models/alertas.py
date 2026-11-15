"""Motor determinista y transparente de alertas tempranas."""

from __future__ import annotations

import math
import uuid

import numpy as np

from .utilidades import a_primitivo

SEVERIDAD_ORDEN = {"critica": 0, "alerta": 1, "vigilancia": 2}


def _valor(lista: list, indice: int) -> float | None:
    if indice < 0 or indice >= len(lista):
        return None
    valor = lista[indice]
    if valor is None:
        return None
    try:
        numero = float(valor)
    except (TypeError, ValueError):
        return None
    return numero if math.isfinite(numero) else None


def _cusum(z: list[float | None], banda: float, deriva: float = 0.5) -> list[bool]:
    positivos = 0.0
    negativos = 0.0
    marcas: list[bool] = []
    for valor in z:
        if valor is None:
            marcas.append(False)
            continue
        positivos = max(0.0, positivos + float(valor) - deriva)
        negativos = min(0.0, negativos + float(valor) + deriva)
        marcas.append(positivos > banda or negativos < -banda)
    return marcas


def _rachas(observado: list[float], ascendente: bool) -> list[int]:
    rachas = [0] * len(observado)
    for i in range(1, len(observado)):
        actual, anterior = observado[i], observado[i - 1]
        deterioro = actual > anterior if ascendente else actual < anterior
        rachas[i] = rachas[i - 1] + 1 if deterioro else 0
    return rachas


def _explicacion(
    banco_nombre: str,
    indicador_nombre: str,
    fecha: str,
    senales: list[str],
    z: float | None,
    p_critico: float | None,
) -> str:
    partes = [f"{banco_nombre} · {indicador_nombre} ({fecha}):"]
    if "fuera_banda_95" in senales:
        partes.append("el valor observado quedó fuera del intervalo de predicción al 95 %.")
    if z is not None:
        partes.append(f"residuo estandarizado z = {z:.2f}.")
    if "racha_deterioro" in senales:
        partes.append("racha de deterioro de al menos 3 meses consecutivos.")
    if "cusum" in senales:
        partes.append("el estadístico CUSUM superó la banda de control.")
    if "salto_estado" in senales:
        partes.append("salto ascendente en la cadena de Markov de morosidad.")
    if "estado_critico" in senales:
        partes.append("la mora se ubicó en el estado Crítico.")
    if p_critico is not None and p_critico > 0:
        partes.append(
            f"probabilidad markoviana de estado Crítico a 3 meses: {100 * p_critico:.1f} %."
        )
    return " ".join(partes)


def generar_alertas(
    series: dict[str, dict[str, dict]],
    markov: dict,
    config: dict,
) -> list[dict]:
    banda_cusum = float(config["alertas"].get("cusum_banda", 5.0))
    z_vigilancia = float(config["alertas"].get("z_vigilancia", 2.0))
    z_alerta = float(config["alertas"].get("z_alerta", 3.0))
    racha_minima = int(config["alertas"].get("racha_meses", 3))
    umbral_prob = float(config["alertas"].get("prob_critico_3m_umbral", 0.25))

    nombres_banco = {b["id"]: b["nombre"] for b in config["bancos"]}
    meta_indicadores = {i["id"]: i for i in config["indicadores"]}

    alertas: list[dict] = []
    for banco_id, indicadores in series.items():
        markov_banco = (markov.get("por_banco") or {}).get(banco_id, {})
        secuencia = markov_banco.get("secuencia_estados") or []
        prob_critico = (markov_banco.get("prob_critico_h") or {}).get("m3")
        for indicador_id, datos in indicadores.items():
            if not datos or not datos.get("sarima"):
                continue
            fechas = datos.get("fechas") or []
            observado = [float(v) for v in datos.get("observado") or []]
            z = datos.get("residuos_estandarizados") or []
            un_paso = datos.get("prediccion_un_paso") or {}
            ic_inf = un_paso.get("ic95_inf") or []
            ic_sup = un_paso.get("ic95_sup") or []
            meta = meta_indicadores.get(indicador_id, {})
            ascendente = meta.get("direccion_riesgo", "ascendente") == "ascendente"
            rachas = _rachas(observado, ascendente)
            cusum = _cusum(z, banda_cusum)
            es_mora = indicador_id == "mora" and bool(secuencia)

            for t, fecha in enumerate(fechas):
                z_t = _valor(z, t)
                obs_t = _valor(observado, t)
                inf_t, sup_t = _valor(ic_inf, t), _valor(ic_sup, t)
                senales: list[str] = []

                if (
                    obs_t is not None
                    and inf_t is not None
                    and sup_t is not None
                    and (obs_t < inf_t or obs_t > sup_t)
                ):
                    senales.append("fuera_banda_95")
                if z_t is not None and abs(z_t) >= z_vigilancia:
                    senales.append("residuo_z_2")
                if z_t is not None and abs(z_t) >= z_alerta:
                    senales.append("residuo_z_3")
                if rachas[t] >= racha_minima:
                    inicio = max(0, t - rachas[t])
                    cambio = (
                        abs(obs_t - observado[inicio])
                        if obs_t is not None and np.std(observado) > 0
                        else 0.0
                    )
                    if cambio >= 0.5 * float(np.std(observado)):
                        senales.append("racha_deterioro")
                if cusum[t]:
                    senales.append("cusum")

                p_actual = None
                if es_mora and t < len(secuencia):
                    estado = int(secuencia[t])
                    if t > 0 and estado > int(secuencia[t - 1]):
                        senales.append("salto_estado")
                    if t == len(fechas) - 1:
                        p_actual = prob_critico

                if not senales:
                    continue
                if p_actual is not None and p_actual > umbral_prob and "fuera_banda_95" in senales:
                    senales.append("prob_critico_3m")

                critica = (
                    "residuo_z_3" in senales
                    or ("fuera_banda_95" in senales and "residuo_z_2" in senales)
                    or ("fuera_banda_95" in senales and "racha_deterioro" in senales)
                )
                if critica:
                    severidad = "critica"
                elif any(
                    s in senales
                    for s in (
                        "fuera_banda_95",
                        "residuo_z_2",
                        "cusum",
                        "salto_estado",
                    )
                ):
                    severidad = "alerta"
                else:
                    severidad = "vigilancia"

                alertas.append(
                    a_primitivo(
                        {
                            "id": uuid.uuid4().hex,
                            "fecha": fecha,
                            "banco_id": banco_id,
                            "indicador_id": indicador_id,
                            "severidad": severidad,
                            "z_score": z_t,
                            "senales_activadas": senales,
                            "explicacion_clara": _explicacion(
                                nombres_banco.get(banco_id, banco_id),
                                meta.get("nombre", indicador_id),
                                fecha,
                                senales,
                                z_t,
                                p_actual,
                            ),
                        }
                    )
                )

    alertas.sort(key=lambda a: (a["fecha"], SEVERIDAD_ORDEN.get(a["severidad"], 9)), reverse=True)
    return alertas
