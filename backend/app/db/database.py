import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base

# ★★★ binary_prefix 제거 ★★★
SQLALCHEMY_DATABASE_URL = "mysql+aiomysql://root:12345@db:3306/project_v1_db?charset=utf8mb4"

engine = create_async_engine(
    SQLALCHEMY_DATABASE_URL,
    echo=True,
    connect_args={
        "charset": "utf8mb4",
        "use_unicode": True
    },
    pool_pre_ping=True
)

AsyncSessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)

Base = declarative_base()

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
