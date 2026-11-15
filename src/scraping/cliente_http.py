"""Cliente HTTP resiliente para el portal de la ASFI.

Características: User-Agent identificable, respeto de robots.txt, límite de
peticiones, reintentos con backoff exponencial y caché por hash SHA-256.
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser

import requests

from .manifiesto import Manifiesto, sha256_archivo


class ErrorHTTP(RuntimeError):
    """Error recuperable o definitivo durante una petición HTTP."""


@dataclass
class ResultadoDescarga:
    url: str
    ruta_local: Path | None
    estado: str  # descargado | omitido | error
    sha256: str | None = None
    bytes: int = 0
    detalle: str = ""


class ClienteHTTP:
    def __init__(
        self,
        config: dict[str, Any],
        manifiesto: Manifiesto | None = None,
        sesion: requests.Session | None = None,
        dormir=time.sleep,
        reloj=time.monotonic,
    ) -> None:
        self.config = config
        self.manifiesto = manifiesto
        self.sesion = sesion or requests.Session()
        self.sesion.headers.update(
            {
                "User-Agent": config.get("user_agent", "ASFI-AlertaTemprana/0.1"),
                "Accept": "text/html,application/xhtml+xml,application/xml,application/vnd.ms-excel,*/*",
                "Accept-Language": "es-BO,es;q=0.9,en;q=0.5",
            }
        )
        self.rate_limit = float(config.get("rate_limit_segundos", 2.5))
        self.reintentos = int(config.get("reintentos", 4))
        self.backoff = float(config.get("backoff_factor", 2.0))
        self.timeout = float(config.get("timeout_segundos", 45))
        self.respetar_robots = bool(config.get("respetar_robots", True))
        self._dormir = dormir
        self._reloj = reloj
        self._ultima_peticion: float | None = None
        self._robots: dict[str, RobotFileParser | None] = {}

    # ------------------------------------------------------------------ utils
    def _esperar_turno(self) -> None:
        if self._ultima_peticion is None:
            return
        transcurrido = self._reloj() - self._ultima_peticion
        espera = self.rate_limit - transcurrido
        if espera > 0:
            self._dormir(espera)

    def _marcar_peticion(self) -> None:
        self._ultima_peticion = self._reloj()

    def _robots_para(self, url: str) -> RobotFileParser | None:
        parsed = urlparse(url)
        origen = f"{parsed.scheme}://{parsed.netloc}"
        if origen in self._robots:
            return self._robots[origen]
        parser = RobotFileParser()
        parser.set_url(urljoin(origen, "/robots.txt"))
        try:
            respuesta = self.sesion.get(parser.url, timeout=self.timeout)
            if respuesta.status_code == 200:
                parser.parse(respuesta.text.splitlines())
                self._robots[origen] = parser
            else:
                self._robots[origen] = None
        except requests.RequestException:
            self._robots[origen] = None
        return self._robots[origen]

    def permitido_por_robots(self, url: str) -> bool:
        if not self.respetar_robots:
            return True
        parser = self._robots_para(url)
        if parser is None:
            return True
        return parser.can_fetch(self.sesion.headers.get("User-Agent", "*"), url)

    # ------------------------------------------------------------------- http
    def obtener(self, url: str, timeout: float | None = None) -> requests.Response:
        """GET con reintentos y backoff exponencial."""
        if not self.permitido_por_robots(url):
            raise ErrorHTTP(f"robots.txt prohíbe acceder a {url}")

        ultimo_error: Exception | None = None
        for intento in range(1, self.reintentos + 1):
            self._esperar_turno()
            try:
                self._marcar_peticion()
                respuesta = self.sesion.get(
                    url, timeout=timeout or self.timeout, allow_redirects=True
                )
                if respuesta.status_code in {429, 500, 502, 503, 504}:
                    raise ErrorHTTP(f"HTTP {respuesta.status_code} en {url}")
                respuesta.raise_for_status()
                return respuesta
            except (requests.RequestException, ErrorHTTP) as exc:
                ultimo_error = exc
                if intento >= self.reintentos:
                    break
                self._dormir(self.backoff ** (intento - 1))
        raise ErrorHTTP(f"Fallaron {self.reintentos} intentos para {url}: {ultimo_error}")

    def cabecera(self, url: str, timeout: float | None = None) -> requests.Response:
        """HEAD para inspeccionar tipo de contenido y tamaño sin descargar."""
        if not self.permitido_por_robots(url):
            raise ErrorHTTP(f"robots.txt prohíbe acceder a {url}")
        self._esperar_turno()
        self._marcar_peticion()
        try:
            return self.sesion.head(url, timeout=timeout or self.timeout, allow_redirects=True)
        except requests.RequestException as exc:
            raise ErrorHTTP(f"HEAD falló para {url}: {exc}") from exc

    # --------------------------------------------------------------- descarga
    def descargar(self, url: str, destino: str | Path) -> ResultadoDescarga:
        """Descarga a destino respetando la caché del manifiesto.

        Si el contenido ya existe en el manifiesto (mismo SHA-256), se omite la
        escritura y se devuelve la ruta existente.
        """
        destino = Path(destino)
        destino.parent.mkdir(parents=True, exist_ok=True)
        temporal = destino.with_suffix(destino.suffix + ".part")

        try:
            respuesta = self.obtener(url)
        except ErrorHTTP as exc:
            return ResultadoDescarga(url=url, ruta_local=None, estado="error", detalle=str(exc))

        try:
            with temporal.open("wb") as fh:
                fh.write(respuesta.content)
            sha = sha256_archivo(temporal)

            if self.manifiesto is not None and self.manifiesto.contiene_hash(sha):
                existente = self.manifiesto.ruta_por_hash(sha)
                temporal.unlink(missing_ok=True)
                return ResultadoDescarga(
                    url=url,
                    ruta_local=existente or destino,
                    estado="omitido",
                    sha256=sha,
                    bytes=respuesta.content.__len__(),
                    detalle="hash ya presente en el manifiesto",
                )

            os.replace(temporal, destino)
        finally:
            temporal.unlink(missing_ok=True)

        tamano = destino.stat().st_size
        if self.manifiesto is not None:
            self.manifiesto.registrar(url=url, ruta_local=destino, sha256=sha, bytes_=tamano)
        return ResultadoDescarga(
            url=url,
            ruta_local=destino,
            estado="descargado",
            sha256=sha,
            bytes=tamano,
        )
