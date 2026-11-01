"""Tía (Magento). HTML con el contenido ya renderizado -> requests + BeautifulSoup."""
from __future__ import annotations

import re
from pathlib import Path
from typing import Iterator, Optional
from urllib.parse import urljoin, urlsplit, urlunsplit

import yaml
from bs4 import BeautifulSoup

from scrapers.base import BaseScraper, ProductoRaw, parse_precio
from scrapers.filtros import clasificar

_CFG = yaml.safe_load((Path(__file__).resolve().parent.parent / "config" / "categorias.yaml").read_text("utf-8"))["tia"]


def _sku_desde_url(url: str) -> Optional[str]:
    # .../parlante-amplificador-300000w-england-sound-151126000.html -> 151126000
    m = re.search(r"-(\d{6,})\.html", url)
    return m.group(1) if m else None


def _limpiar_imagen(url: Optional[str]) -> Optional[str]:
    """Quita los parámetros de redimensionado (height=112...) para obtener la imagen original."""
    if not url or url.startswith("data:"):
        return None
    sp = urlsplit(url)
    return urlunsplit((sp.scheme, sp.netloc, sp.path, "", ""))


def parse_listado(html: str, base_url: str, categoria: str, subcategoria: str) -> list[ProductoRaw]:
    soup = BeautifulSoup(html, "lxml")
    items = soup.select("li.product-item, div.product-item, li.item.product")
    out = []
    for it in items:
        a = it.select_one("a.product-item-link") or it.select_one("a[href$='.html']")
        if not a or not a.get("href"):
            continue
        url = urljoin(base_url, a["href"])
        nombre = (a.get("title") or a.get_text(" ", strip=True) or "").strip()
        if not nombre:
            t = it.select_one(".product-item-name, strong, b")
            nombre = t.get_text(" ", strip=True) if t else ""
        sku = _sku_desde_url(url)
        if not (sku and nombre):
            continue

        # Precios: "Precio Especial $259,00 / Precio habitual $329,00" o un único precio
        especial = it.select_one(".special-price .price, [data-price-type='finalPrice'] .price")
        habitual = it.select_one(".old-price .price, [data-price-type='oldPrice'] .price")
        unico = it.select_one(".price")
        precio = parse_precio(especial.get_text() if especial else (unico.get_text() if unico else None))
        precio_reg = parse_precio(habitual.get_text()) if habitual else None
        if precio is None:  # respaldo por texto
            m = re.search(r"\$\s?\d[\d.,]*", it.get_text(" ", strip=True))
            precio = parse_precio(m.group(0)) if m else None

        texto = it.get_text(" ", strip=True)
        m = re.search(r"Marca\s+(.+?)(?:\s{2,}|$)", it.get_text("\n", strip=True).replace("\n", "  "))
        marca = m.group(1).strip() if m else None

        img = it.select_one("img")
        img_url = None
        if img:
            img_url = img.get("data-src") or img.get("data-original") or img.get("src")
            img_url = _limpiar_imagen(urljoin(base_url, img_url)) if img_url else None

        decision, revisar = clasificar(nombre)
        if decision == "excluir":
            continue
        out.append(ProductoRaw(
            tienda="tia", sku=sku, nombre=nombre, url=url, marca=marca,
            categoria=categoria, subcategoria=subcategoria, precio=precio,
            precio_regular=precio_reg, imagen_url=img_url, revisar=revisar,
        ))
    return out


class TiaScraper(BaseScraper):
    tienda = "tia"

    def productos(self) -> Iterator[ProductoRaw]:
        base = _CFG["base_url"]
        for cat in _CFG["categorias"]:
            vistos = set()
            pagina = 1
            print(f"[tia] {cat['categoria']} / {cat['subcategoria']}")
            while True:
                url = f"{base}{cat['ruta']}" + (f"?p={pagina}" if pagina > 1 else "")
                html = self.get(url)
                if not html:
                    break
                lista = parse_listado(html, base, cat["categoria"], cat["subcategoria"])
                nuevos = [p for p in lista if p.sku not in vistos]
                if not nuevos:
                    break
                for p in nuevos:
                    vistos.add(p.sku)
                    yield p
                    if self.limit and len(vistos) >= self.limit:
                        break
                if self.limit and len(vistos) >= self.limit:
                    break
                pagina += 1
