from __future__ import annotations

import secrets
from typing import Optional

from fastapi import BackgroundTasks, Depends, FastAPI, Header, HTTPException
from sqlalchemy import func, select, text

from config import settings
from jobs.run_scrape import correr_tienda
from scrapers.registry import SCRAPERS
from storage.db import SessionLocal
from storage.models import CorridaScraping, Producto

app = FastAPI(
    title="NutriHábito - Scraping de productos",
    description="Servicio de extracción y almacenamiento. Los productos se consultan desde la API .NET.",
    version="2.0",
)


def db():
    s = SessionLocal()
    try:
        yield s
    finally:
        s.close()


def exigir_api_key(x_api_key: Optional[str] = Header(default=None)):
    if not settings.API_KEY:
        raise HTTPException(503, "API_KEY no configurada en el servidor")
    if not x_api_key or not secrets.compare_digest(x_api_key, settings.API_KEY):
        raise HTTPException(401, "API key inválida")


@app.get("/health")
def health(s=Depends(db)):
    s.execute(text("select 1"))
    return {
        "status": "ok",
        "database": "ok",
        "image_storage": settings.IMAGE_STORAGE,
    }


@app.get("/status")
def status(s=Depends(db)):
    corridas = s.scalars(
        select(CorridaScraping).order_by(CorridaScraping.id.desc()).limit(10)
    ).all()
    return {
        "total_productos": s.scalar(select(func.count()).select_from(Producto)),
        "ultimas_corridas": [
            {
                "tienda": c.tienda,
                "estado": c.estado,
                "inicio": c.inicio.isoformat() if c.inicio else None,
                "fin": c.fin.isoformat() if c.fin else None,
                "vistos": c.vistos,
                "nuevos": c.nuevos,
                "actualizados": c.actualizados,
                "no_disponibles": c.no_disponibles,
                "errores": c.errores,
            }
            for c in corridas
        ],
    }


@app.post("/scrape/{tienda}", dependencies=[Depends(exigir_api_key)])
def lanzar_scrape(
    tienda: str,
    background: BackgroundTasks,
    limit: Optional[int] = None,
    sin_imagenes: bool = False,
):
    if tienda != "all" and tienda not in SCRAPERS:
        raise HTTPException(
            404,
            f"Tienda desconocida. Opciones: {list(SCRAPERS)} o 'all'",
        )

    for t in (list(SCRAPERS) if tienda == "all" else [tienda]):
        background.add_task(correr_tienda, t, limit, False, sin_imagenes)

    return {
        "mensaje": "Scraping iniciado en segundo plano. Consulta /status.",
        "tienda": tienda,
        "limit": limit,
        "sin_imagenes": sin_imagenes,
    }
