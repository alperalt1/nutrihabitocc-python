# Despliegue en Dokploy

Este servicio se despliega como una aplicación independiente dentro del mismo
proyecto/entorno de Dokploy que la API .NET y la web.

## 1. Variables de entorno

| Variable | Ejemplo / descripción |
| --- | --- |
| `DATABASE_URL` | `postgresql+psycopg2://usuario:clave@host/base?sslmode=require` |
| `DB_SCHEMA` | `public` |
| `IMAGE_STORAGE` | `s3` |
| `S3_BUCKET` | `assets` |
| `S3_PREFIX` | `nutrihabit/productos` |
| `S3_ADDRESSING_STYLE` | `path` |
| `AWS_ENDPOINT_URL_S3` | Endpoint S3-compatible de Neon |
| `AWS_ACCESS_KEY_ID` | Credencial S3 |
| `AWS_SECRET_ACCESS_KEY` | Credencial S3 |
| `AWS_REGION` | `us-east-2` |
| `API_KEY` | Clave larga y aleatoria para `POST /scrape` |
| `SCRAPE_DELAY` | `1.5` |
| `PORT` | `8000` (opcional) |

No subas `.env` al repositorio. La configuración de producción debe ir en Dokploy.

## 2. Crear la aplicación en Dokploy

1. Crea una aplicación dentro del proyecto `nutrihabit`.
2. Source: GitHub, repositorio `nutrihabitocc-python`, branch `main`.
3. Build Type: **Dockerfile**.
4. Dockerfile Path: `Dockerfile`, Context Path: `.`.
5. Puerto del contenedor: `8000`.
6. No agregues dominio público si solo la usarás para tareas programadas. Si
   necesitas lanzar scraping desde fuera, agrega un dominio y protege el endpoint
   con `X-API-Key`.

## 3. Tareas programadas

En Dokploy, crea una tarea programada (Schedule) para la corrida completa:

```bash
python -m jobs.run_scrape --tienda all --full
```

Así la corrida no depende de que el proceso web siga vivo.
