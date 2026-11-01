"""Genera data/productos.json y data/productos.xlsx desde la base de datos."""
from __future__ import annotations

import io
import json
from decimal import Decimal
from typing import Optional

import pandas as pd
from sqlalchemy import select

from config.settings import DATA_DIR
from storage.db import get_session
from storage.images import get_image_store
from storage.models import Producto

COLUMNAS = ["id", "tienda", "sku", "nombre", "marca", "categoria", "subcategoria", "presentacion",
            "precio", "precio_regular", "precio_unidad", "url", "imagen_url", "descripcion",
            "disponible", "revisar", "primera_vez_visto", "ultima_actualizacion"]


def producto_a_dict(p: Producto, store=None, expira: int = 3600) -> dict:
    d = {c: getattr(p, c) for c in COLUMNAS}
    for k in ("precio", "precio_regular"):
        d[k] = float(d[k]) if isinstance(d[k], Decimal) else d[k]
    for k in ("primera_vez_visto", "ultima_actualizacion"):
        d[k] = d[k].isoformat() if d[k] else None
    d["imagen_url_origen"] = d.pop("imagen_url")
    d["imagen"] = store.url(p.imagen_key, expira) if (store and p.imagen_key) else None
    return d


def todos(solo_disponibles: bool = False, expira: int = 7 * 24 * 3600) -> list[dict]:
    store = get_image_store()
    with get_session() as s:
        q = select(Producto).order_by(Producto.tienda, Producto.categoria, Producto.nombre)
        if solo_disponibles:
            q = q.where(Producto.disponible.is_(True))
        return [producto_a_dict(p, store, expira) for p in s.scalars(q)]


def exportar_json(ruta=None) -> str:
    ruta = ruta or DATA_DIR / "productos.json"
    datos = todos()
    with open(ruta, "w", encoding="utf-8") as f:
        json.dump({"total": len(datos), "productos": datos}, f, ensure_ascii=False, indent=2)
    return str(ruta)


def excel_bytes() -> bytes:
    df = pd.DataFrame(todos())
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as w:
        df.to_excel(w, index=False, sheet_name="Productos")
    return buf.getvalue()


def exportar_excel(ruta=None) -> str:
    ruta = ruta or DATA_DIR / "productos.xlsx"
    with open(ruta, "wb") as f:
        f.write(excel_bytes())
    return str(ruta)
