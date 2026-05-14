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


@app.get("/health", summary="Проверка здоровья сервера",
         description="Возвращает статус сервера. Если сервер работает - вернет `ok`.")
async def health():
    return {"status": "ok"}


@app.get(
    "/advertisement/{advertisement_id}",
    response_model=AdResponse,
    summary="Получить объявление по ID",
    description="""
    Возвращает полную информацию об одном объявлении.

    - Если объявление существует, вернет его данные.
    - Если ID не существует, вернет ошибку **404 Not Found**.
    """
)
async def get_advertisement(ad: AdDep):
    return ad


@app.post(
    "/advertisement",
    response_model=AdResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Создать объявление",
    description="""
    Создает новое объявление и сохраняет его в базу данных.

    Все поля обязательны для заполнения. Строки, состоящие только из пробелов, не пройдут валидацию.
    При успешном создании возвращается статус **201 Created** и полный объект объявления с присвоенным ID и датой создания.
    """
)
async def create_advertisement(data: AdCreate, db: DBDep):
    ad = Advertisement(**data.model_dump())
    db.add(ad)
    await db.flush()
    return ad


@app.patch(
    "/advertisement/{advertisement_id}",
    response_model=AdResponse,
    summary="Обновить объявление",
    description="""
    Частично обновляет существующее объявление.

    - Нужно передать **только те поля**, которые вы хотите изменить.
    - Поля `title`, `description` и `author` проходят строгую проверку: пустые строки или строки из пробелов вызовут ошибку **400 Bad Request**.
    - Если не передать ни одного поля, сервер вернет ошибку **400 Bad Request**.
    - Если объявление не найдено, вернется ошибка **404 Not Found**.
    """
)
async def update_advertisement(data: AdUpdate, ad: AdDep):
    update_data = data.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(status_code=400, detail="Нет данных для обновления")

    for k, v in update_data.items():
        setattr(ad, k, v)
    return ad


@app.delete(
    "/advertisement/{advertisement_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Удалить объявление",
    description="""
    Безвозвратно удаляет объявление из базы данных по его ID.

    - В случае успеха возвращает статус **204 No Content** (пустой ответ).
    - Если объявление с таким ID не найдено, вернет ошибку **404 Not Found**.
    """
)
async def delete_advertisement(ad: AdDep, db: DBDep):
    await db.delete(ad)
    return None


# Поиск. ( ?title=Кошак&min_price=100 )
@app.get(
    "/advertisement",
    response_model=list[AdResponse],
    summary="Поиск объявлений",
    description="""
**Правила поиска:**

- `title` - ищет **частичное совпадение** без учета регистра. Например, запрос `кош` найдет объявления со словами *Кошка*, *хорошая кошка*, *Кошелек*.
- `author` - ищет **строгое совпадение**. Запрос `Иван` не найдет `Иван Иванов`.
- `min_price` / `max_price` - фильтруют по диапазону цены включительно.

Параметры можно комбинировать. Если параметры не переданы - вернет все объявления.
"""
)
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
