# nutrihabitocc-python

Servicio de scraping de productos de Tía, Tuti, Supermaxi y Megamaxi. Guarda los
productos, el historial de precios y las imágenes en la misma base PostgreSQL y
bucket S3 que usa la API .NET. La consulta de productos se expone desde .NET.

## Estructura

```
app/            API FastAPI (/health, /status, /scrape/{tienda})
config/         configuración y categorías de scraping
jobs/           ejecución del scraping y exportaciones opcionales
migrations/     migraciones Alembic de las tablas de scraping
scrapers/       implementaciones por tienda
storage/        modelos SQLAlchemy, repositorio e imágenes
tests/          prueba de flujo
```

## Desarrollo local

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Completar DATABASE_URL, credenciales S3 y API_KEY
alembic upgrade head
uvicorn app.main:app --reload
```

## Scraping

```bash
# Prueba sin guardar
python -m jobs.run_scrape --tienda tia --limit 5 --dry-run

# Corrida completa real
python -m jobs.run_scrape --tienda all --full
```

`--limit` es solo para pruebas. `--full` recorre todo el catálogo y deja la corrida
como completa si no hubo errores.

## API

- `GET /health`
- `GET /status`
- `POST /scrape/{tienda}` con header `X-API-Key`

`POST /scrape` ejecuta el scraping en segundo plano. Para producción se recomienda
lanzar la corrida completa como tarea programada de Dokploy usando el comando CLI.

## Docker

```bash
docker build -t nutrihabit-scraper .
docker run --rm --env-file .env -p 8000:8000 nutrihabit-scraper
```

El contenedor aplica `alembic upgrade head` al iniciar. No expongas este servicio
públicamente sin `API_KEY`.
