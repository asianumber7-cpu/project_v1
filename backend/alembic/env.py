# backend/alembic/env.py 

from logging.config import fileConfig
from app.db.database import Base
from sqlalchemy import engine_from_config
from sqlalchemy import pool
from app.models import user, product, product_vector
from alembic import context
import os

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

#  환경변수에서 DATABASE_URL 가져오기 
docker_db_url = os.environ.get("DATABASE_URL")

if docker_db_url:
    # asyncmy → pymysql 치환
    alembic_db_url = docker_db_url.replace("mysql+asyncmy://", "mysql+pymysql://")
    alembic_db_url = alembic_db_url.replace("mysql+aiomysql://", "mysql+pymysql://")  # ← 추가!
    config.set_main_option('sqlalchemy.url', alembic_db_url)
    print(f"✅ Using DATABASE_URL: {alembic_db_url}")  # ← 디버깅용
else:
    print("⚠️ Using alembic.ini URL")  # ← 디버깅용


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, 
            target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()