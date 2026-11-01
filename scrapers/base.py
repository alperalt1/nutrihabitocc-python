from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from typing import Iterator, Optional

import requests

from config import settings


@dataclass
class ProductoRaw:
    tienda: str
    sku: str
    nombre: str
    url: Optional[str] = None
    marca: Optional[str] = None
    categoria: Optional[str] = None
    subcategoria: Optional[str] = None
    presentacion: Optional[str] = None
    precio: Optional[Decimal] = None
    precio_regular: Optional[Decimal] = None
    precio_unidad: Optional[str] = None
    imagen_url: Optional[str] = None
    descripcion: Optional[str] = None
    revisar: bool = False


def parse_precio(texto: Optional[str]) -> Optional[Decimal]:
    """'$259,00' -> 259.00 ; '$0.99' -> 0.99 ; '$1.299,50' -> 1299.50"""
    if not texto:
        return None
    m = re.search(r"\d[\d.,]*", texto)
    if not m:
        return None
    s = m.group(0).rstrip(".,")
    if "," in s and "." in s:
        dec = "," if s.rfind(",") > s.rfind(".") else "."
        mil = "." if dec == "," else ","
        s = s.replace(mil, "").replace(dec, ".")
    elif "," in s:
        s = s.replace(",", ".")
    try:
        return Decimal(s).quantize(Decimal("0.01"))
    except InvalidOperation:
        return None


class BaseScraper:
    tienda: str = ""

    def __init__(
        self,
        limit: Optional[int] = None,
        delay: Optional[float] = None,
        timeout: int = 30,
    ):
        self.limit = limit  # tope de productos por categoría (para pruebas)
        self.delay = settings.SCRAPE_DELAY if delay is None else delay
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": settings.USER_AGENT, "Accept-Language": "es-EC,es;q=0.9"})
        self.errores = 0

    def get(self, url: str, reintentos: int = 3) -> Optional[str]:
        for i in range(reintentos):
            try:
                time.sleep(self.delay)
                r = self.session.get(url, timeout=self.timeout)
                if r.status_code == 404:
                    return None
                r.raise_for_status()
                return r.text
            except Exception as e:  # noqa: BLE001
                print(f"  ! intento {i + 1}/{reintentos} falló en {url}: {e}")
                time.sleep(2 * (i + 1))
        self.errores += 1
        return None

    def productos(self) -> Iterator[ProductoRaw]:  # pragma: no cover
        raise NotImplementedError
