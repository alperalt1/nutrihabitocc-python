from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

DATABASE_URL = os.environ.get("DATABASE_URL", f"sqlite:///{DATA_DIR / 'nutrihabit.db'}")
IS_POSTGRES = DATABASE_URL.startswith("postgresql")
# "public" o vacío significa el schema público de Postgres.
_raw_schema = (os.environ.get("DB_SCHEMA", "") or "").strip()
DB_SCHEMA = (
    _raw_schema
    if IS_POSTGRES and _raw_schema and _raw_schema.lower() != "public"
    else None
)

IMAGE_STORAGE = os.environ.get("IMAGE_STORAGE", "local")  # "s3" | "local"
S3_BUCKET = os.environ.get("S3_BUCKET", "assets")
S3_PREFIX = os.environ.get("S3_PREFIX", "nutrihabit/productos").strip("/")
S3_ADDRESSING_STYLE = os.environ.get("S3_ADDRESSING_STYLE", "path")
AWS_ENDPOINT_URL_S3 = os.environ.get("AWS_ENDPOINT_URL_S3")
AWS_ACCESS_KEY_ID = os.environ.get("AWS_ACCESS_KEY_ID", "")
AWS_SECRET_ACCESS_KEY = os.environ.get("AWS_SECRET_ACCESS_KEY", "")
AWS_REGION = os.environ.get("AWS_REGION", "us-east-2")
LOCAL_IMAGES_DIR = DATA_DIR / "imagenes"

API_KEY = os.environ.get("API_KEY", "")
SCRAPE_DELAY = float(os.environ.get("SCRAPE_DELAY", "1.5"))
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)
