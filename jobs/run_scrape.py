"""
Uso:
  python -m jobs.run_scrape --tienda tia --limit 5 --dry-run     # prueba sin tocar BD ni imágenes
  python -m jobs.run_scrape --tienda tuti --limit 20             # prueba real pequeña
  python -m jobs.run_scrape --tienda all                         # corrida completa (mensual)
"""
from __future__ import annotations

import argparse
import json
import traceback
from decimal import Decimal

from jobs.export import exportar_excel, exportar_json
from scrapers.registry import SCRAPERS
from storage import repository as repo
from storage.db import SessionLocal
from storage.images import get_image_store


def correr_tienda(nombre: str, limit=None, dry_run=False, sin_imagenes=False) -> dict:
    scraper = SCRAPERS[nombre](limit=limit)

    if dry_run:
        muestra = []
        for p in scraper.productos():
            muestra.append({k: (str(v) if isinstance(v, Decimal) else v) for k, v in p.__dict__.items()})
            if len(muestra) >= (limit or 20) * 3:
                break
        print(json.dumps(muestra[:10], ensure_ascii=False, indent=2))
        print(f"\n[dry-run] {nombre}: {len(muestra)} productos parseados (nada guardado).")
        return {"tienda": nombre, "vistos": len(muestra)}

    store = None if sin_imagenes else get_image_store()
    session = SessionLocal()
    corrida = repo.iniciar_corrida(session, nombre)
    try:
        repo.upsert_productos(session, corrida, scraper.productos(), store)
        corrida.errores += scraper.errores
        completa = not limit and scraper.errores == 0
        if completa and corrida.vistos > 0:
            repo.marcar_no_disponibles(session, corrida)
        estado = "ok" if completa else "parcial"
        repo.cerrar_corrida(session, corrida, estado)
    except Exception:  # noqa: BLE001
        session.rollback()
        repo.cerrar_corrida(session, corrida, "error", traceback.format_exc())
        raise
    finally:
        res = {"tienda": nombre, "estado": corrida.estado, "vistos": corrida.vistos,
               "nuevos": corrida.nuevos, "actualizados": corrida.actualizados,
               "no_disponibles": corrida.no_disponibles, "errores": corrida.errores}
        session.close()
    print(res)
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tienda", default="all", help="tia | tuti | supermaxi | megamaxi | all")
    ap.add_argument("--limit", type=int, help="máx. productos por categoría (solo pruebas)")
    ap.add_argument("--full", action="store_true", help="recorre todo el catálogo e ignora --limit")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--sin-imagenes", action="store_true")
    ap.add_argument("--sin-export", action="store_true")
    a = ap.parse_args()

    limit = None if a.full else a.limit
    tiendas = list(SCRAPERS) if a.tienda == "all" else [a.tienda]
    for t in tiendas:
        try:
            correr_tienda(t, limit, a.dry_run, a.sin_imagenes)
        except Exception as e:  # una tienda que falla no detiene a las demás
            print(f"[{t}] FALLÓ: {e}")
    if not a.dry_run and not a.sin_export:
        print("JSON:", exportar_json())
        print("Excel:", exportar_excel())


if __name__ == "__main__":
    main()
