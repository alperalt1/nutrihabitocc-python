"""Filtro de alimentos para tiendas con catálogo mezclado (p. ej. Tuti)."""
from __future__ import annotations

import re
import unicodedata
from pathlib import Path

import yaml

_CFG = yaml.safe_load((Path(__file__).resolve().parent.parent / "config" / "categorias.yaml").read_text("utf-8"))


def _norm(t: str) -> str:
    t = unicodedata.normalize("NFKD", t.lower())
    return "".join(c for c in t if not unicodedata.combining(c))


def _compilar(palabras, palabra_completa=False):
    fin = r"\b" if palabra_completa else ""
    return [re.compile(rf"\b{re.escape(_norm(p))}{fin}", re.I) for p in palabras]


_EXCLUIR = _compilar(_CFG["filtro_alimentos"]["excluir_palabras"])
_ALCOHOL = _compilar(_CFG["filtro_alimentos"]["alcohol"], True)
_MASCOTAS = _compilar(_CFG["filtro_alimentos"]["mascotas"], True)
_REVISAR = _compilar(_CFG["filtro_alimentos"]["revisar_palabras"])


def clasificar(nombre: str):
    """Devuelve ('incluir'|'excluir', revisar: bool)."""
    n = _norm(nombre)
    pol = _CFG["politica"]
    if any(r.search(n) for r in _EXCLUIR):
        return "excluir", False
    if pol.get("excluir_alcohol") and any(r.search(n) for r in _ALCOHOL):
        return "excluir", False
    if pol.get("excluir_mascotas") and any(r.search(n) for r in _MASCOTAS):
        return "excluir", False
    return "incluir", any(r.search(n) for r in _REVISAR)
