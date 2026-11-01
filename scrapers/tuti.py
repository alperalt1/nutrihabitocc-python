"""Tuti (WordPress). Productos en /producto/<slug>, con marca, gramaje y precio en la tarjeta."""
from __future__ import annotations

import re
from pathlib import Path
from typing import Iterator, Optional
from urllib.parse import urljoin

import yaml
from bs4 import BeautifulSoup

from scrapers.base import BaseScraper, ProductoRaw, parse_precio
from scrapers.filtros import clasificar

_CFG = yaml.safe_load((Path(__file__).resolve().parent.parent / "config" / "categorias.yaml").read_text("utf-8"))["tuti"]

_RE_PRECIO = re.compile(r"^\$\s?\d")
_RE_POR_UNIDAD = re.compile(r"^Precio\s+(por|x)\s+", re.I)
_RE_PRESENTACION = re.compile(r"^\d+([.,]\d+)?\s?(g|kg|ml|l|lt|oz|unidad(es)?|u|und)\b", re.I)


def _slug_desde_url(url: str) -> Optional[str]:
    m = re.search(r"/producto/([^/]+)/?", url)
    return m.group(1) if m else None


def parse_tarjetas(html: str, base_url: str) -> list[ProductoRaw]:
    soup = BeautifulSoup(html, "lxml")
    out, vistos = [], set()
    for a in soup.select("a[href*='/producto/']"):
        url = urljoin(base_url, a["href"])
        slug = _slug_desde_url(url)
        if not slug or slug in vistos:
            continue

        # La tarjeta actual es <li class="product ...">. En HTML de prueba
        # puede ser un <div class="card">, así que se usa un fallback.
        cont = a.find_parent("li", class_=lambda c: c and "product" in c.split())
        if cont is None or cont.select_one("span.price") is None:
            cont = a
            for _ in range(6):
                if cont.parent is None:
                    break
                cont = cont.parent
                if cont.select_one("span.price") or "$" in cont.get_text():
                    break
        if cont is None or "$" not in cont.get_text():
            continue

        lineas = [l.strip() for l in cont.stripped_strings if l.strip()]

        title_el = cont.select_one("h2.woocommerce-loop-product__title")
        nombre = title_el.get_text(" ", strip=True) if title_el else ""
        if not nombre:
            nombre = a.get_text(" ", strip=True)
        if not nombre:
            nombre = next((l for l in lineas if not _RE_PRECIO.match(l) and l != "$"
                           and not _RE_POR_UNIDAD.match(l) and not _RE_PRESENTACION.match(l)), None)
        if not nombre:
            continue

        brand_el = cont.select_one("p.product_brand")
        marca = brand_el.get_text(" ", strip=True) if brand_el else None

        presentacion_el = cont.select_one("p.udm:not(.gramaje)")
        presentacion = presentacion_el.get_text(" ", strip=True) if presentacion_el else None

        unit_price_el = cont.select_one("p.udm.gramaje")
        precio_unidad = unit_price_el.get_text(" ", strip=True) if unit_price_el else None

        price_el = cont.select_one("span.price")
        precio = parse_precio(price_el.get_text(" ", strip=True)) if price_el else None

        # Fallbacks para HTML sin clases de WooCommerce (tests/otros layouts).
        if precio is None:
            for i, l in enumerate(lineas):
                if l == "$" and i + 1 < len(lineas):
                    precio = parse_precio("$" + lineas[i + 1])
                    break
                if _RE_PRECIO.match(l):
                    precio = parse_precio(l)
                    break

        for l in lineas:
            if not _RE_POR_UNIDAD.match(l) and _RE_PRECIO.match(l):
                continue
            if not _RE_POR_UNIDAD.match(l) and _RE_PRESENTACION.match(l):
                if not presentacion:
                    presentacion = l
                continue
            if _RE_POR_UNIDAD.match(l):
                if not precio_unidad:
                    precio_unidad = l
                continue
            if not marca and l != nombre and l.upper() == l and l not in ("$",):
                marca = l

        if not marca:
            marca = "Sin marca" if "Sin marca" in lineas else None

        img = cont.select_one("img")
        img_url = None
        if img:
            img_url = img.get("data-src") or img.get("data-lazy-src") or img.get("src")
            if img_url and (img_url.startswith("data:") or img_url.endswith("dummy.png")):
                img_url = None
            elif img_url:
                img_url = urljoin(base_url, img_url)

        decision, revisar = clasificar(nombre)
        if decision == "excluir":
            continue
        vistos.add(slug)
        out.append(ProductoRaw(
            tienda="tuti", sku=slug, nombre=nombre, url=url, marca=marca,
            presentacion=presentacion, precio=precio, precio_unidad=precio_unidad,
            imagen_url=img_url, revisar=revisar,
        ))
    return out


class TutiScraper(BaseScraper):
    tienda = "tuti"

    def productos(self) -> Iterator[ProductoRaw]:
        base = _CFG["base_url"]
        vistos = set()
        for listado in _CFG["listados"]:
            pagina = 1
            while True:
                url = f"{base}{listado}" + (f"/page/{pagina}/" if pagina > 1 else "")
                html = self.get(url)
                if not html:
                    break
                lista = parse_tarjetas(html, base)
                nuevos = [p for p in lista if p.sku not in vistos]
                if not nuevos:
                    break
                for p in nuevos:
                    vistos.add(p.sku)
                    yield p
                    if self.limit and len(vistos) >= self.limit:
                        return
                pagina += 1
