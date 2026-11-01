#!/bin/sh
set -e

# Crea/actualiza las tablas de scraping en la misma base que usa la API .NET.
alembic upgrade head

exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
