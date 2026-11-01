import os, sys, tempfile
os.environ["DATABASE_URL"] = "sqlite:///" + tempfile.mktemp(suffix=".db")
os.environ["IMAGE_STORAGE"] = "local"
os.environ["API_KEY"] = "clave-test"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from decimal import Decimal
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import select, func

HTML_TIA = """
<ol><li class="item product product-item">
 <a class="product-item-link" href="/queso-mozzarella-nestle-150001000.html" title="QUESO MOZZARELLA NESTLE 400 G">QUESO MOZZARELLA NESTLE 400 G</a>
 <span class="special-price"><span class="price">$4,50</span></span><span class="old-price"><span class="price">$5,20</span></span>
 <div>Marca  NESTLE</div><img src="https://www.tia.com.ec/media/catalog/product/q/u/queso.jpg?optimize=medium&height=112&width=112"></li>
 <li class="item product product-item"><a class="product-item-link" href="/detergente-ariel-150002000.html">DETERGENTE ARIEL 1KG</a><span class="price">$3,00</span></li>
 <li class="item product product-item"><a class="product-item-link" href="/yogurt-toni-150003000.html">YOGURT TONI 1L</a><span class="price">$2,10</span><div>Marca  TONI</div></li></ol>"""

HTML_TUTI = """
<div class="grid"><div class="card"><a href="https://tuti.com.ec/producto/galletas-dulces-maria/"><img src="https://tuti.com.ec/a.jpg"></a>
<a href="https://tuti.com.ec/producto/galletas-dulces-maria/">Galletas dulces María</a><p>NESTLÉ</p><p>172g</p><p>$0.99</p><p>Precio por 100g $0.58</p></div>
<div class="card"><a href="https://tuti.com.ec/producto/cerveza-gold/">Cerveza gold</a><p>MARTENS</p><p>330ml</p><p>$0.75</p></div>
<div class="card"><a href="https://tuti.com.ec/producto/detergente-x/">Detergente líquido</a><p>X</p><p>$1.69</p></div></div>"""


def test_todo():
    from scrapers.base import parse_precio
    assert parse_precio("$259,00") == Decimal("259.00") and parse_precio("$0.99") == Decimal("0.99")
    assert parse_precio("$1.299,50") == Decimal("1299.50")

    from scrapers.tia import parse_listado
    tia = parse_listado(HTML_TIA, "https://www.tia.com.ec", "Lácteos", "Quesos")
    assert [p.sku for p in tia] == ["150001000", "150003000"], tia   # detergente excluido
    assert tia[0].precio == Decimal("4.50") and tia[0].precio_regular == Decimal("5.20")
    assert tia[0].marca == "NESTLE" and "?" not in tia[0].imagen_url

    from scrapers.tuti import parse_tarjetas
    tuti = parse_tarjetas(HTML_TUTI, "https://tuti.com.ec")
    assert [p.sku for p in tuti] == ["galletas-dulces-maria"], [p.sku for p in tuti]  # cerveza y detergente fuera
    g = tuti[0]
    assert (g.marca, g.presentacion, g.precio, g.precio_unidad) == ("NESTLÉ", "172g", Decimal("0.99"), "Precio por 100g $0.58"), g

    # migración real (alembic) sobre sqlite temporal
    cfg = Config(os.path.join(os.path.dirname(__file__), "..", "alembic.ini"))
    cfg.set_main_option("script_location", os.path.join(os.path.dirname(__file__), "..", "migrations"))
    command.upgrade(cfg, "head")

    from storage import repository as repo
    from storage.db import SessionLocal
    from storage.models import Producto, PrecioHistorial
    s = SessionLocal()

    c1 = repo.iniciar_corrida(s, "tia"); repo.upsert_productos(s, c1, tia + [], None)
    repo.marcar_no_disponibles(s, c1); repo.cerrar_corrida(s, c1, "ok")
    assert (c1.nuevos, c1.actualizados) == (2, 0)

    # 2ª corrida: cambia el precio de uno, el otro desaparece, aparece uno nuevo
    import copy, time; time.sleep(1.1)
    nuevo = copy.deepcopy(tia[0]); nuevo.precio = Decimal("4.99")
    extra = copy.deepcopy(tia[0]); extra.sku = "150009000"; extra.nombre = "QUESO NUEVO"
    c2 = repo.iniciar_corrida(s, "tia"); repo.upsert_productos(s, c2, [nuevo, extra], None)
    repo.marcar_no_disponibles(s, c2); repo.cerrar_corrida(s, c2, "ok")
    assert (c2.nuevos, c2.actualizados, c2.no_disponibles) == (1, 1, 1), (c2.nuevos, c2.actualizados, c2.no_disponibles)
    assert s.scalar(select(func.count()).select_from(Producto)) == 3          # NADA se borró ni se duplicó
    p = s.scalar(select(Producto).where(Producto.sku == "150001000"))
    assert p.precio == Decimal("4.99") and p.disponible
    assert s.scalar(select(func.count()).select_from(PrecioHistorial).where(PrecioHistorial.producto_id == p.id)) == 2
    assert s.scalar(select(Producto.disponible).where(Producto.sku == "150003000")) is False
    s.close()

    from app.main import app
    c = TestClient(app)
    assert c.get("/health").json()["status"] == "ok"
    status = c.get("/status").json()
    assert status["total_productos"] == 3
    assert status["ultimas_corridas"]
    assert c.post("/scrape/tia").status_code == 401
    assert c.post("/scrape/xx", headers={"X-API-Key": "clave-test"}).status_code == 404
    print("TODO OK")

if __name__ == "__main__":
    test_todo()
