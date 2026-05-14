from contextlib import asynccontextmanager

from database import Base, engine
from dependencies import AdDep, DBDep
from fastapi import Depends, FastAPI, HTTPException, status
from models import Advertisement
from schemas import AdCreate, AdFilter, AdResponse, AdUpdate
from sqlalchemy import select


# Функция жизненного цикла приложения
@asynccontextmanager
async def lifespan(_app: FastAPI):
    # Код, выполняемый до старта приложения
    async with engine.begin() as conn:
        # Создаем все таблицы из моделей по схемам
        await conn.run_sync(Base.metadata.create_all)

    yield

    # Код, выполняемый при выключении приложения


# Передаем lifespan в приложение
app = FastAPI(
    title="Advertisements API",
    description="API для работы с объявлениями.",
    lifespan=lifespan,
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


@app.post(
    "/advertisement", response_model=AdResponse, status_code=status.HTTP_201_CREATED
)
async def create_advertisement(data: AdCreate, db: DBDep):
    """Создает новое объявление."""
    ad = Advertisement(**data.model_dump())
    db.add(ad)
    await db.flush()
    return ad


@app.patch("/advertisement/{advertisement_id}", response_model=AdResponse)
async def update_advertisement(data: AdUpdate, ad: AdDep):
    """Обновление информации в существующем объявлении"""
    update_data = data.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(status_code=400, detail="Нет данных для обновления")

    for k, v in update_data.items():
        setattr(ad, k, v)
    return ad


@app.delete("/advertisement/{advertisement_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_advertisement(ad: AdDep, db: DBDep):
    """Удаление объявления из базы"""
    await db.delete(ad)
    return None


# Поиск. ( ?title=Кошак&min_price=100 )
@app.get("/advertisement", response_model=list[AdResponse])
async def search_advertisements(db: DBDep, filters: AdFilter = Depends()):
    """Поиск объявлений по параметрам."""
    # Базовый запрос
    query = select(Advertisement)

    # Фильтрация через метод схемы
    query = filters.filter_query(query, Advertisement)

    # Выполнение и возврат результатов
    res = await db.execute(query)
    ads = res.scalars().all()
    return ads


# Запуск приложения
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8080)
