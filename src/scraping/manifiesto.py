"""Manifiesto de descargas con hashes SHA-256 e idempotencia."""

from __future__ import annotations

import csv
import hashlib
import os
import tempfile
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

COLUMNAS = ("url", "ruta_local", "timestamp", "sha256", "bytes", "status")


def sha256_bytes(contenido: bytes) -> str:
    """Calcula el hash SHA-256 de un bloque de bytes."""
    return hashlib.sha256(contenido).hexdigest()


def sha256_archivo(ruta: str | Path, bloque: int = 1 << 20) -> str:
    """Calcula el hash SHA-256 de un archivo por bloques."""
    digest = hashlib.sha256()
    with Path(ruta).open("rb") as fh:
        while True:
            trozo = fh.read(bloque)
            if not trozo:
                break
            digest.update(trozo)
    return digest.hexdigest()


@dataclass(frozen=True)
class RegistroManifiesto:
    url: str
    ruta_local: str
    timestamp: str
    sha256: str
    bytes: int
    status: str

    def como_fila(self) -> dict[str, str | int]:
        return asdict(self)


class Manifiesto:
    """Gestiona data/raw/manifest.csv de forma idempotente y atómica."""

    def __init__(self, ruta: str | Path) -> None:
        self.ruta = Path(ruta)
        self.ruta.parent.mkdir(parents=True, exist_ok=True)
        self._registros: dict[str, RegistroManifiesto] = {}
        self.cargar()

    def cargar(self) -> None:
        self._registros.clear()
        if not self.ruta.exists():
            return
        with self.ruta.open("r", encoding="utf-8", newline="") as fh:
            lector = csv.DictReader(fh)
            nombres = set(lector.fieldnames or [])
            if not set(COLUMNAS).issubset(nombres):
                raise ValueError(f"Manifiesto con columnas inválidas: {sorted(nombres)}")
            for fila in lector:
                registro = RegistroManifiesto(
                    url=fila["url"],
                    ruta_local=fila["ruta_local"],
                    timestamp=fila["timestamp"],
                    sha256=fila["sha256"],
                    bytes=int(fila["bytes"]),
                    status=fila["status"],
                )
                self._registros[registro.sha256] = registro

    @property
    def registros(self) -> list[RegistroManifiesto]:
        return list(self._registros.values())

    def contiene_hash(self, sha256: str) -> bool:
        return sha256 in self._registros

    def ruta_por_hash(self, sha256: str) -> Path | None:
        registro = self._registros.get(sha256)
        return Path(registro.ruta_local) if registro else None

    def registrar(
        self,
        url: str,
        ruta_local: str | Path,
        sha256: str,
        bytes_: int,
        status: str = "descargado",
    ) -> bool:
        """Registra una descarga. Devuelve False si el hash ya existía."""
        if sha256 in self._registros:
            return False
        registro = RegistroManifiesto(
            url=url,
            ruta_local=str(Path(ruta_local).as_posix()),
            timestamp=datetime.now(UTC).isoformat(timespec="seconds"),
            sha256=sha256,
            bytes=bytes_,
            status=status,
        )
        self._registros[sha256] = registro
        self.guardar()
        return True

    def registrar_archivo(
        self, url: str, ruta_local: str | Path, status: str = "descargado"
    ) -> bool:
        ruta = Path(ruta_local)
        return self.registrar(
            url=url,
            ruta_local=ruta,
            sha256=sha256_archivo(ruta),
            bytes_=ruta.stat().st_size,
            status=status,
        )

    def actualizar_ruta(
        self, sha256: str, nueva_ruta: str | Path, status: str | None = None
    ) -> bool:
        """Actualiza la ruta local (por ejemplo, tras corregir la extensión)."""
        registro = self._registros.get(sha256)
        if registro is None:
            return False
        self._registros[sha256] = RegistroManifiesto(
            url=registro.url,
            ruta_local=str(Path(nueva_ruta).as_posix()),
            timestamp=registro.timestamp,
            sha256=registro.sha256,
            bytes=registro.bytes,
            status=status or registro.status,
        )
        self.guardar()
        return True

    def guardar(self) -> None:
        """Escritura atómica: archivo temporal + reemplazo."""
        fd, temporal = tempfile.mkstemp(dir=self.ruta.parent, suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8", newline="") as fh:
                escritor = csv.DictWriter(fh, fieldnames=list(COLUMNAS))
                escritor.writeheader()
                for registro in sorted(self._registros.values(), key=lambda r: r.timestamp):
                    escritor.writerow(registro.como_fila())
            os.replace(temporal, self.ruta)
        finally:
            if os.path.exists(temporal):
                os.remove(temporal)


def columnas_manifiesto() -> tuple[str, ...]:
    return COLUMNAS
