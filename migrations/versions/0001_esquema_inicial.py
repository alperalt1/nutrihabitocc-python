"""esquema inicial: producto, precio_historial, corrida_scraping

Revision ID: 0001
Revises:
"""
import sqlalchemy as sa
from alembic import op

from config.settings import DB_SCHEMA

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None

S = DB_SCHEMA
PK = sa.BigInteger().with_variant(sa.Integer, "sqlite")
PFX = f"{S}." if S else ""


def upgrade():
    op.create_table(
        "producto",
        sa.Column("id", PK, primary_key=True, autoincrement=True),
        sa.Column("tienda", sa.String(30), nullable=False),
        sa.Column("sku", sa.String(120), nullable=False),
        sa.Column("nombre", sa.String(300), nullable=False),
        sa.Column("marca", sa.String(120)),
        sa.Column("categoria", sa.String(120)),
        sa.Column("subcategoria", sa.String(120)),
        sa.Column("presentacion", sa.String(60)),
        sa.Column("precio", sa.Numeric(10, 2)),
        sa.Column("precio_regular", sa.Numeric(10, 2)),
        sa.Column("precio_unidad", sa.String(60)),
        sa.Column("url", sa.Text),
        sa.Column("imagen_url", sa.Text),
        sa.Column("imagen_key", sa.Text),
        sa.Column("descripcion", sa.Text),
        sa.Column("disponible", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("revisar", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("primera_vez_visto", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("ultima_vez_visto", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("ultima_actualizacion", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("tienda", "sku", name="uq_producto_tienda_sku"),
        schema=S,
    )
    op.create_index("ix_producto_tienda_categoria", "producto", ["tienda", "categoria"], schema=S)
    op.create_index("ix_producto_nombre", "producto", ["nombre"], schema=S)

    op.create_table(
        "precio_historial",
        sa.Column("id", PK, primary_key=True, autoincrement=True),
        sa.Column("producto_id", PK, sa.ForeignKey(f"{PFX}producto.id", ondelete="CASCADE"), nullable=False),
        sa.Column("precio", sa.Numeric(10, 2)),
        sa.Column("precio_regular", sa.Numeric(10, 2)),
        sa.Column("fecha", sa.DateTime(timezone=True), server_default=sa.func.now()),
        schema=S,
    )
    op.create_index("ix_precio_historial_producto_fecha", "precio_historial", ["producto_id", "fecha"], schema=S)

    op.create_table(
        "corrida_scraping",
        sa.Column("id", PK, primary_key=True, autoincrement=True),
        sa.Column("tienda", sa.String(30), nullable=False),
        sa.Column("inicio", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("fin", sa.DateTime(timezone=True)),
        sa.Column("estado", sa.String(20), server_default="en_curso"),
        sa.Column("vistos", sa.Integer, server_default="0"),
        sa.Column("nuevos", sa.Integer, server_default="0"),
        sa.Column("actualizados", sa.Integer, server_default="0"),
        sa.Column("no_disponibles", sa.Integer, server_default="0"),
        sa.Column("errores", sa.Integer, server_default="0"),
        sa.Column("detalle", sa.Text),
        schema=S,
    )


def downgrade():
    op.drop_table("corrida_scraping", schema=S)
    op.drop_table("precio_historial", schema=S)
    op.drop_table("producto", schema=S)
