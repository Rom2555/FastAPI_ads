from contextlib import asynccontextmanager

from fastapi import FastAPI, status

from database import Base, engine
from dependencies import DBDep, AdDep
from models import Advertisement
from schemas import AdCreate, AdResponse


# Функция жизненного цикла приложения
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Код, выполняемый до старта приложения
    async with engine.begin() as conn:
        # Создаем все таблицы из моделей по схемам
        await conn.run_sync(Base.metadata.create_all)

    yield

    # Код, выполняемый при выключении приложения
    pass


# Передаем lifespan в приложение
app = FastAPI(
    title='Advertisements API',
    description="API для работы с объявлениями.",
    lifespan=lifespan
)


# Роуты

@app.get("/health")
async def health():
    """Проверка работоспособности сервера"""
    return {"status": "ok"}


@app.get("/advertisement/{advertisement_id}", response_model=AdResponse)
async def get_advertisement(ad: AdDep):
    """Возвращает информацию об объявлении по ID."""
    return ad


@app.post("/advertisement", response_model=AdResponse, status_code=status.HTTP_201_CREATED)
async def create_advertisement(data: AdCreate, db: DBDep):
    """Создает новое объявление."""
    ad = Advertisement(**data.model_dump())
    db.add(ad)
    await db.flush()
    return ad


# Запуск приложения
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8080)
