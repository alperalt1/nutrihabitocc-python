"""Scraper común para Supermaxi y Megamaxi (WooCommerce + sitemap)."""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Iterator, Optional
from urllib.parse import urljoin, urlparse

import yaml
from bs4 import BeautifulSoup

from scrapers.base import BaseScraper, ProductoRaw, parse_precio
from scrapers.filtros import clasificar

_CFG = yaml.safe_load(
    (Path(__file__).resolve().parent.parent / "config" / "categorias.yaml").read_text("utf-8")
)
_RE_PRESENTACION = re.compile(
    r"\b\d+(?:[.,]\d+)?\s?(?:g|kg|ml|l|lt|oz|unidad(?:es)?|u|und)\b", re.I
)


def _presentacion(nombre: str) -> Optional[str]:
    m = _RE_PRESENTACION.search(nombre or "")
    return m.group(0) if m else None


def _jsonld_product(soup: BeautifulSoup) -> Optional[dict]:
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string or "")
        except Exception:  # noqa: BLE001
            continue

        objs = []
        if isinstance(data, dict):
            if "@graph" in data:
                objs.extend(data["@graph"])
            else:
                objs.append(data)
        elif isinstance(data, list):
            objs.extend(data)

        for obj in objs:
            if isinstance(obj, dict) and obj.get("@type") == "Product":
                return obj
    return None


def _precio_oferta(offers) -> tuple[Optional[object], Optional[object], str]:
    if isinstance(offers, list):
        offers = offers[0] if offers else {}
    if not isinstance(offers, dict):
        return None, None, "USD"

    precio = parse_precio(str(offers.get("price"))) if offers.get("price") is not None else None
    regular = None
    for key in ("highPrice", "listPrice", "priceBeforeDiscount"):
        if offers.get(key) is not None:
            regular = parse_precio(str(offers.get(key)))
            if regular is not None:
                break
    currency = offers.get("priceCurrency") or "USD"
    return precio, regular, currency


def _marca(prod: dict) -> Optional[str]:
    brand = prod.get("brand")
    if isinstance(brand, dict):
        return brand.get("name") or None
    if isinstance(brand, str):
        return brand or None
    if isinstance(brand, list) and brand:
        first = brand[0]
        if isinstance(first, dict):
            return first.get("name") or None
        return str(first)
    return None


def _breadcrumbs(soup: BeautifulSoup) -> list[tuple[str, str]]:
    nav = soup.find("nav", class_="woocommerce-breadcrumb")
    if not nav:
        return []

    items = []
    for a in nav.find_all("a"):
        text = a.get_text(" ", strip=True)
        href = a.get("href", "")
        if text and text.lower() not in ("home", "inicio"):
            items.append((text, href))
    return items


def _categoria_slugs(breadcrumbs: list[tuple[str, str]]) -> list[str]:
    slugs = []
    for _, href in breadcrumbs:
        m = re.search(r"/(?:product-category|categoria|category)/([^/]+)", href)
        if m:
            slugs.append(m.group(1).lower())
    return slugs


def _categorias_texto(breadcrumbs: list[tuple[str, str]]) -> tuple[Optional[str], Optional[str]]:
    cats = [
        (text, href)
        for text, href in breadcrumbs
        if re.search(r"/(?:product-category|categoria|category)/", href)
    ]
    if not cats:
        return None, None

    categoria = cats[0][0]
    subcategoria = cats[-1][0] if len(cats) > 1 else None
    return categoria, subcategoria


class WooCommerceSitemapScraper(BaseScraper):
    """Recorre el product-sitemap y parsea el JSON-LD de cada producto."""

    def __init__(
        self,
        tienda: str,
        limit: Optional[int] = None,
        delay: Optional[float] = None,
        timeout: int = 90,
    ):
        super().__init__(limit=limit, delay=delay, timeout=timeout)
        self.tienda = tienda
        cfg = _CFG[tienda]
        self.base_url = cfg["base_url"].rstrip("/")
        self.food_roots = {str(x).lower() for x in cfg.get("food_roots", [])}

    def _sitemaps(self) -> list[str]:
        xml = self.get(f"{self.base_url}/sitemap_index.xml")
        if not xml:
            return [f"{self.base_url}/product-sitemap.xml"]

        urls = re.findall(r"<loc>([^<]*product-sitemap[^<]*)</loc>", xml)
        return urls or [f"{self.base_url}/product-sitemap.xml"]

    def iter_product_urls(self):
        seen = set()

        for sitemap in self._sitemaps():
            xml = self.get(sitemap)
            if not xml:
                continue

            for match in re.finditer(r"<loc>([^<]+)</loc>", xml):
                url = match.group(1).strip()
                if not ("/producto/" in url or "/product/" in url):
                    continue
                path = urlparse(url).path.strip("/")
                if path in ("producto", "product", "productos"):
                    continue
                if url in seen:
                    continue
                seen.add(url)
                yield url

    def discover_product_urls(self) -> list[str]:
        return list(self.iter_product_urls())

    def _es_alimento(self, breadcrumbs: list[tuple[str, str]]) -> bool:
        if not self.food_roots:
            return True

        for slug in _categoria_slugs(breadcrumbs):
            if slug in self.food_roots:
                return True
            if any(slug.endswith("-" + root) for root in self.food_roots):
                return True
        return False

    def parse_product(self, url: str) -> Optional[ProductoRaw]:
        html = self.get(url)
        if not html:
            return None

        soup = BeautifulSoup(html, "lxml")
        prod = _jsonld_product(soup)
        if not prod:
            return None

        nombre = (prod.get("name") or "").strip()
        if not nombre:
            return None

        breadcrumbs = _breadcrumbs(soup)
        if not self._es_alimento(breadcrumbs):
            return None

        decision, revisar = clasificar(nombre)
        if decision == "excluir":
            return None

        sku = str(prod.get("sku") or "").strip()
        if not sku:
            sku = urlparse(url).path.rstrip("/").split("/")[-1]

        image = prod.get("image") or ""
        if isinstance(image, list):
            image = image[0] if image else ""
        image_url = urljoin(url, image) if image else None

        descripcion = prod.get("description") or ""
        if descripcion:
            descripcion = BeautifulSoup(str(descripcion), "lxml").get_text(" ", strip=True)
        if not descripcion:
            short = soup.find("div", class_="woocommerce-product-details__short-description")
            if short:
                descripcion = short.get_text(" ", strip=True)
        if not descripcion:
            meta = soup.find("meta", attrs={"name": "description"})
            if meta:
                descripcion = meta.get("content") or ""

        precio, precio_regular, _ = _precio_oferta(prod.get("offers"))
        categoria, subcategoria = _categorias_texto(breadcrumbs)

        return ProductoRaw(
            tienda=self.tienda,
            sku=sku,
            nombre=nombre,
            url=url,
            marca=_marca(prod),
            categoria=categoria,
            subcategoria=subcategoria,
            presentacion=_presentacion(nombre),
            precio=precio,
            precio_regular=precio_regular,
            imagen_url=image_url,
            descripcion=descripcion or None,
            revisar=revisar,
        )

    def productos(self) -> Iterator[ProductoRaw]:
        encontrados = 0
        for url in self.iter_product_urls():
            try:
                p = self.parse_product(url)
                if p:
                    yield p
                    encontrados += 1
                    if self.limit and encontrados >= self.limit:
                        return
            except Exception as exc:  # noqa: BLE001
                self.errores += 1
                print(f"[{self.tienda}] error parseando {url}: {exc}")
