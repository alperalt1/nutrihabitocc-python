from alembic import context
from sqlalchemy import text

from config.settings import DB_SCHEMA
from storage.db import engine
from storage.models import Base

target_metadata = Base.metadata


def run_migrations_online():
    with engine.connect() as connection:
        if DB_SCHEMA:
            connection.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{DB_SCHEMA}"'))
            connection.commit()
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            version_table_schema=DB_SCHEMA,
            include_schemas=bool(DB_SCHEMA),
        )
        with context.begin_transaction():
            context.run_migrations()


run_migrations_online()
