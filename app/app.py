import os

from fastapi import FastAPI
from sqlalchemy import Column, DateTime, Integer, String, Text, func, select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# Настройка подключения к PostgreSQL
database_url = os.environ.get("DATABASE_URL")
if database_url:
    if database_url.startswith("postgresql://"):
        database_url = database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
else:
    user = os.environ.get("POSTGRES_USER", "postgres")
    password = os.environ.get("POSTGRES_PASSWORD", "postgres")
    host = os.environ.get("POSTGRES_HOST", "localhost")
    port = os.environ.get("POSTGRES_PORT", "5432")
    db = os.environ.get("POSTGRES_DB", "ads_db")
    database_url = f"postgresql+asyncpg://{user}:{password}@{host}:{port}/{db}"

# Асинхронный движок
engine = create_async_engine(database_url, echo=False)
# Фабрика сессий
async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

Base = declarative_base()


# Модель база данных
class Ad(Base):
    __tablename__ = "ads"

    id = Column(Integer, primary_key=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=False)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    owner = Column(String(100), nullable=False)

app = FastAPI()

# Запуск приложения
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8080)
