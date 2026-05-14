from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, status, HTTPException, Query
from sqlalchemy import select

from database import Base, engine
from dependencies import DBDep, AdDep
from models import Advertisement
from schemas import AdCreate, AdResponse, AdUpdate


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
async def search_advertisements(
        db: DBDep,
        title: Optional[str] = Query(None, description="Поиск по заголовку (точное совпадение)"),
        author: Optional[str] = Query(None, description="Поиск по автору"),
        min_price: Optional[int] = Query(None, ge=0, description="Минимальная цена"),
        max_price: Optional[int] = Query(None, ge=0, description="Максимальная цена"),
):
    """Поиск объявлений по полям через query-параметры."""
    query = select(Advertisement)

    if title is not None:
        query = query.where(Advertisement.title.ilike(f"%{title}%"))
    if author is not None:
        query = query.where(Advertisement.author == author)
    if min_price is not None:
        query = query.where(Advertisement.price >= min_price)
    if max_price is not None:
        query = query.where(Advertisement.price <= max_price)

    res = await db.execute(query)
    ads = res.scalars().all()
    return ads


# Запуск приложения
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8080)
