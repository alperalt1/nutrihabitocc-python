"""Actualización mensual: inserta nuevos, actualiza existentes, NO borra (marca no disponible)."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Iterable, Optional

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from scrapers.base import ProductoRaw
from storage.images import ImageStore
from storage.models import CorridaScraping, PrecioHistorial, Producto

CAMPOS = ["nombre", "marca", "categoria", "subcategoria", "presentacion",
          "precio_regular", "precio_unidad", "url", "descripcion", "revisar"]


def _ahora():
    return datetime.now(timezone.utc)


def iniciar_corrida(session: Session, tienda: str) -> CorridaScraping:
    c = CorridaScraping(tienda=tienda, inicio=_ahora(), estado="en_curso")
    session.add(c)
    session.commit()
    return c


def upsert_productos(
    session: Session,
    corrida: CorridaScraping,
    items: Iterable[ProductoRaw],
    store: Optional[ImageStore] = None,
    lote: int = 200,
) -> None:
    tienda = corrida.tienda
    existentes = {p.sku: p for p in session.scalars(select(Producto).where(Producto.tienda == tienda))}
    vistos_en_corrida = set()
    ahora = _ahora()
    pendientes = 0

    for it in items:
        if it.sku in vistos_en_corrida:  # duplicado dentro de la misma corrida
            continue
        vistos_en_corrida.add(it.sku)
        corrida.vistos += 1
        try:
            p = existentes.get(it.sku)
            if p is None:
                p = Producto(tienda=tienda, sku=it.sku, nombre=it.nombre, precio=it.precio,
                             primera_vez_visto=ahora, ultima_vez_visto=ahora,
                             ultima_actualizacion=ahora, disponible=True)
                for c in CAMPOS:
                    setattr(p, c, getattr(it, c, None) if c != "revisar" else it.revisar)
                p.imagen_url = it.imagen_url
                session.add(p)
                session.flush()
                session.add(PrecioHistorial(producto_id=p.id, precio=it.precio,
                                            precio_regular=it.precio_regular, fecha=ahora))
                existentes[it.sku] = p
                corrida.nuevos += 1
            else:
                cambio_precio = (p.precio != it.precio) or (p.precio_regular != it.precio_regular)
                cambio_datos = False
                for c in CAMPOS:
                    nuevo = it.revisar if c == "revisar" else getattr(it, c, None)
                    # no pisar datos buenos con vacíos
                    if nuevo is not None and getattr(p, c) != nuevo:
                        setattr(p, c, nuevo)
                        cambio_datos = True
                if cambio_precio and it.precio is not None:
                    p.precio = it.precio
                    session.add(PrecioHistorial(producto_id=p.id, precio=it.precio,
                                                precio_regular=it.precio_regular, fecha=ahora))
                if it.imagen_url and p.imagen_url != it.imagen_url:
                    p.imagen_url = it.imagen_url
                    p.imagen_key = None  # forzar nueva descarga
                    cambio_datos = True
                p.disponible = True
                p.ultima_vez_visto = ahora
                if cambio_precio or cambio_datos:
                    p.ultima_actualizacion = ahora
                    corrida.actualizados += 1

            if store and p.imagen_url and not p.imagen_key:
                p.imagen_key = store.guardar_desde_url(tienda, it.sku, p.imagen_url)
        except Exception as e:  # noqa: BLE001
            corrida.errores += 1
            print(f"  ! error con {it.sku}: {e}")
            session.rollback()
            continue

        pendientes += 1
        if pendientes >= lote:
            session.commit()
            pendientes = 0
    session.commit()


def marcar_no_disponibles(session: Session, corrida: CorridaScraping) -> int:
    """Productos de la tienda que no aparecieron en esta corrida -> disponible=False (sin borrar)."""
    res = session.execute(
        update(Producto)
        .where(Producto.tienda == corrida.tienda, Producto.ultima_vez_visto < corrida.inicio,
               Producto.disponible.is_(True))
        .values(disponible=False)
    )
    corrida.no_disponibles = res.rowcount or 0
    session.commit()
    return corrida.no_disponibles


def cerrar_corrida(session: Session, corrida: CorridaScraping, estado: str, detalle: str = "") -> None:
    corrida.fin = _ahora()
    corrida.estado = estado
    corrida.detalle = detalle[:2000] if detalle else None
    session.commit()
