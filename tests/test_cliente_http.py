from pathlib import Path

import pytest
from src.scraping.cliente_http import ClienteHTTP, ErrorHTTP
from src.scraping.manifiesto import Manifiesto


class RespuestaFalsa:
    def __init__(self, status_code=200, content=b"", headers=None, text=""):
        self.status_code = status_code
        self.content = content
        self.headers = headers or {}
        self.text = text or content.decode("utf-8", errors="ignore")

    def raise_for_status(self):
        if self.status_code >= 400:
            import requests

            raise requests.HTTPError(f"HTTP {self.status_code}")


class SesionFalsa:
    def __init__(self, respuestas=None, errores=None):
        self.headers = {}
        self.respuestas = list(respuestas or [])
        self.errores = list(errores or [])
        self.llamadas = []

    def get(self, url, **kwargs):
        self.llamadas.append(("GET", url))
        if self.errores:
            raise self.errores.pop(0)
        return self.respuestas.pop(0)

    def head(self, url, **kwargs):
        self.llamadas.append(("HEAD", url))
        return self.respuestas.pop(0)


def _config(**cambios):
    base = {
        "user_agent": "ASFI-Test/0.1",
        "rate_limit_segundos": 1.0,
        "reintentos": 3,
        "backoff_factor": 2.0,
        "timeout_segundos": 1,
        "respetar_robots": False,
    }
    base.update(cambios)
    return base


def test_rate_limit_entre_peticiones():
    dormidas = []
    reloj = iter([0.0, 0.0, 0.2, 0.2, 0.2])
    sesion = SesionFalsa(respuestas=[RespuestaFalsa(), RespuestaFalsa()])
    cliente = ClienteHTTP(
        _config(), sesion=sesion, dormir=dormidas.append, reloj=lambda: next(reloj)
    )
    cliente.obtener("https://www.asfi.gob.bo/a")
    cliente.obtener("https://www.asfi.gob.bo/b")
    assert dormidas and pytest.approx(dormidas[0]) == 1.0


def _reloj_avanzado():
    estado = {"t": 0.0}

    def reloj():
        estado["t"] += 100.0
        return estado["t"]

    return reloj


def test_backoff_exponencial_y_exito():
    dormidas = []
    import requests

    errores = [requests.ConnectionError("x"), requests.ConnectionError("y")]
    sesion = SesionFalsa(respuestas=[RespuestaFalsa()], errores=errores)
    cliente = ClienteHTTP(_config(), sesion=sesion, dormir=dormidas.append, reloj=_reloj_avanzado())
    respuesta = cliente.obtener("https://www.asfi.gob.bo/a")
    assert respuesta.status_code == 200
    assert dormidas == [1.0, 2.0]


def test_agota_reintentos():
    import requests

    sesion = SesionFalsa(errores=[requests.ConnectionError("x")] * 3)
    cliente = ClienteHTTP(_config(), sesion=sesion, dormir=lambda _: None, reloj=_reloj_avanzado())
    with pytest.raises(ErrorHTTP):
        cliente.obtener("https://www.asfi.gob.bo/a")


def test_robots_prohibe_ruta():
    robots = RespuestaFalsa(text="User-agent: *\nDisallow: /privado\n")
    sesion = SesionFalsa(respuestas=[robots])
    cliente = ClienteHTTP(
        _config(respetar_robots=True), sesion=sesion, dormir=lambda _: None, reloj=lambda: 0.0
    )
    with pytest.raises(ErrorHTTP, match="robots"):
        cliente.obtener("https://www.asfi.gob.bo/privado/dato.xls")


def test_descarga_idempotente_por_hash(tmp_path):
    contenido = b"columna,valor\nactivo,10\n"
    sesion = SesionFalsa(
        respuestas=[
            RespuestaFalsa(content=contenido),
            RespuestaFalsa(content=contenido),
        ]
    )
    manifiesto = Manifiesto(tmp_path / "manifest.csv")
    cliente = ClienteHTTP(
        _config(),
        manifiesto=manifiesto,
        sesion=sesion,
        dormir=lambda _: None,
        reloj=_reloj_avanzado(),
    )
    destino = tmp_path / "dato.csv"

    primero = cliente.descargar("https://www.asfi.gob.bo/dato.csv", destino)
    assert primero.estado == "descargado"
    assert destino.read_bytes() == contenido

    segundo = cliente.descargar("https://www.asfi.gob.bo/dato.csv", destino)
    assert segundo.estado == "omitido"
    assert len(manifiesto.registros) == 1
    assert not Path(str(destino) + ".part").exists()


def test_descarga_error_reporta(tmp_path):
    import requests

    sesion = SesionFalsa(errores=[requests.ConnectionError("x")] * 3)
    cliente = ClienteHTTP(_config(), sesion=sesion, dormir=lambda _: None, reloj=_reloj_avanzado())
    resultado = cliente.descargar("https://www.asfi.gob.bo/a.xls", tmp_path / "a.xls")
    assert resultado.estado == "error"
    assert resultado.ruta_local is None
