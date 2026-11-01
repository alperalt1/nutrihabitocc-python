from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import (
    BigInteger, Boolean, DateTime, ForeignKey, Index, Integer, MetaData,
    Numeric, String, Text, UniqueConstraint, func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from config.settings import DB_SCHEMA

_PFX = f"{DB_SCHEMA}." if DB_SCHEMA else ""
# Integer en SQLite (autoincrement), BigInteger en Postgres
_PK = BigInteger().with_variant(Integer, "sqlite")


class Base(DeclarativeBase):
    metadata = MetaData(schema=DB_SCHEMA)


class Producto(Base):
    __tablename__ = "producto"
    __table_args__ = (
        UniqueConstraint("tienda", "sku", name="uq_producto_tienda_sku"),
        Index("ix_producto_tienda_categoria", "tienda", "categoria"),
        Index("ix_producto_nombre", "nombre"),
    )

    id: Mapped[int] = mapped_column(_PK, primary_key=True, autoincrement=True)
    tienda: Mapped[str] = mapped_column(String(30), nullable=False)
    sku: Mapped[str] = mapped_column(String(120), nullable=False)
    nombre: Mapped[str] = mapped_column(String(300), nullable=False)
    marca: Mapped[Optional[str]] = mapped_column(String(120))
    categoria: Mapped[Optional[str]] = mapped_column(String(120))
    subcategoria: Mapped[Optional[str]] = mapped_column(String(120))
    presentacion: Mapped[Optional[str]] = mapped_column(String(60))
    precio: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2))
    precio_regular: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2))
    precio_unidad: Mapped[Optional[str]] = mapped_column(String(60))
    url: Mapped[Optional[str]] = mapped_column(Text)
    imagen_url: Mapped[Optional[str]] = mapped_column(Text)
    imagen_key: Mapped[Optional[str]] = mapped_column(Text)
    descripcion: Mapped[Optional[str]] = mapped_column(Text)
    disponible: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    revisar: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    primera_vez_visto: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    ultima_vez_visto: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    ultima_actualizacion: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    historial: Mapped[list["PrecioHistorial"]] = relationship(
        back_populates="producto", cascade="all, delete-orphan"
    )


class PrecioHistorial(Base):
    __tablename__ = "precio_historial"
    __table_args__ = (Index("ix_precio_historial_producto_fecha", "producto_id", "fecha"),)

    id: Mapped[int] = mapped_column(_PK, primary_key=True, autoincrement=True)
    producto_id: Mapped[int] = mapped_column(
        _PK, ForeignKey(f"{_PFX}producto.id", ondelete="CASCADE"), nullable=False
    )
    precio: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2))
    precio_regular: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2))
    fecha: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    producto: Mapped[Producto] = relationship(back_populates="historial")


class CorridaScraping(Base):
    __tablename__ = "corrida_scraping"

    id: Mapped[int] = mapped_column(_PK, primary_key=True, autoincrement=True)
    tienda: Mapped[str] = mapped_column(String(30), nullable=False)
    inicio: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    fin: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    estado: Mapped[str] = mapped_column(String(20), default="en_curso")  # en_curso|ok|error|parcial
    vistos: Mapped[int] = mapped_column(Integer, default=0)
    nuevos: Mapped[int] = mapped_column(Integer, default=0)
    actualizados: Mapped[int] = mapped_column(Integer, default=0)
    no_disponibles: Mapped[int] = mapped_column(Integer, default=0)
    errores: Mapped[int] = mapped_column(Integer, default=0)
    detalle: Mapped[Optional[str]] = mapped_column(Text)
