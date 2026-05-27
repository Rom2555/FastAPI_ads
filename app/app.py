import os
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select

import auth
from database import Base, engine, async_session
from dependencies import AdDep, DBDep, UserDep, CurrentUserDep, get_db
from models import Advertisement, User
from schemas import (
    AdCreate, AdFilter, AdResponse, AdUpdate,
    UserCreate, UserUpdate, UserResponse,
    TokenResponse
)

# Описание тегов для Swagger UI
tags_metadata = [
    {
        "name": "Advertisements",
        "description": "Операции с объявлениями: создание, поиск, обновление, удаление.",
    },
    {
        "name": "Users",
        "description": "Операции с пользователями: регистрация, просмотр, редактирование, логин.",
    },
    {
        "name": "System",
        "description": "Системные эндпоинты: проверка статуса.",
    },
]


# Функция жизненного цикла приложения
@asynccontextmanager
async def lifespan(_app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Автосоздание администратора при первом старте
    async with async_session() as session:
        # Проверяем, есть ли хоть один админ в базе
        result = await session.execute(select(User).where(User.role == "admin"))
        admin_exists = result.scalars().first()

        if not admin_exists:
            admin_username = os.environ.get("ADMIN_USERNAME", "admin")
            admin_password = os.environ.get("ADMIN_PASSWORD", "admin")
            hashed_password = auth.get_password_hash(admin_password)
            new_admin = User(
                username=admin_username,
                password_hash=hashed_password,
                role="admin"
            )
            session.add(new_admin)
            await session.commit()
            print(f"Создан администратор по умолчанию: {admin_username}")

    yield

    # Код, выполняемый при выключении приложения


# Передаем lifespan в приложение
app = FastAPI(
    title="Advertisements API",
    description="API для работы с объявлениями.",
    version="2.0.0",
    lifespan=lifespan,
    openapi_tags=tags_metadata
)


# Системные роуты

@app.get(
    "/health",
    tags=["System"],
    summary="Проверка здоровья сервера",
    description="Возвращает статус сервера. Если сервер работает - вернет `ok`.",
)
async def health():
    return {"status": "ok"}


# Роуты ползователей и авторизации


@app.post(
    "/login",
    response_model=TokenResponse,
    tags=["Users"],
    summary="Авторизация пользователя",
)
async def login(db: DBDep, form_data: OAuth2PasswordRequestForm = Depends()):
    query = select(User).where(User.username == form_data.username)
    res = await db.execute(query)
    user = res.scalars().first()

    if not user or not auth.verify_password(form_data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Неверный логин или пароль")

    token = auth.create_access_token({"sub": str(user.id)})
    return TokenResponse(access_token=token)


@app.post(
    "/user",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Users"],
    summary="Создать пользователя (Регистрация)",
    description="Доступно без авторизации. Создает нового пользователя.",
)
async def create_user(data: UserCreate, db: DBDep):
    # Хэшируем пароль перед сохранением
    hashed_password = auth.get_password_hash(data.password)

    # Создаем объект модели, подставляя хэш вместо чистого пароля
    user_data = data.model_dump()
    user_data.pop("password")  # Удаляем чистый пароль из словаря

    new_user = User(**user_data, password_hash=hashed_password)
    db.add(new_user)
    await db.flush()
    return new_user


@app.get(
    "/user/{user_id}",
    response_model=UserResponse,
    tags=["Users"],
    summary="Получить пользователя по ID",
    description="Доступно без авторизации.",
)
async def get_user(user: UserDep):
    # Зависимость UserDep уже достала пользователя или выдала 404
    return user


@app.patch(
    "/user/{user_id}",
    response_model=UserResponse,
    tags=["Users"],
    summary="Обновить данные пользователя",
    description="Пользователь может обновить только себя. Админ может обновить любого.",
)
async def update_user(data: UserUpdate, user: UserDep, current_user: CurrentUserDep, db: DBDep):
    # Проверка прав: либо админ, либо пользователь редактирует сам себя
    if current_user.role != "admin" and current_user.id != user.id:
        raise HTTPException(status_code=403, detail="Недостаточно прав для редактирования этого пользователя")

    update_data = data.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(status_code=400, detail="Нет данных для обновления")

    # Если в обновлениях есть пароль, его нужно хэшировать
    if "password" in update_data:
        update_data["password_hash"] = auth.get_password_hash(update_data.pop("password"))

    # Если обычный юзер пытается сменить себе роль — запрещаем (только админ может)
    if "role" in update_data and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Только администратор может менять роли")

    for k, v in update_data.items():
        setattr(user, k, v)
    return user


@app.delete(
    "/user/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["Users"],
    summary="Удалить пользователя",
    description="Пользователь может удалить только себя. Админ может удалить любого.",
)
async def delete_user(user: UserDep, current_user: CurrentUserDep, db: DBDep):
    # Проверка прав: либо админ, либо пользователь удаляет сам себя
    if current_user.role != "admin" and current_user.id != user.id:
        raise HTTPException(status_code=403, detail="Недостаточно прав для удаления этого пользователя")

    await db.delete(user)
    return None


# Роуты объявлений с правами

@app.get(
    "/advertisement/{advertisement_id}",
    tags=["Advertisements"],
    response_model=AdResponse,
    summary="Получить объявление по ID",
    description="""
    Возвращает полную информацию об одном объявлении.

    - Если объявление существует, вернет его данные.
    - Если ID не существует, вернет ошибку **404 Not Found**.
    """,
)
async def get_advertisement(ad: AdDep):
    # Доступно всем, токен не нужен
    return ad


@app.post(
    "/advertisement",
    response_model=AdResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Advertisements"],
    summary="Создать объявление",
    description="""
    Создает новое объявление и сохраняет его в базу данных.
    Требуется авторизация. Владелец объявления определяется по токену.
    
    Все поля обязательны для заполнения. Строки, состоящие только из пробелов, не пройдут валидацию.
    При успешном создании возвращается статус **201 Created** и полный объект объявления с присвоенным ID и датой создания.
    """,
)
async def create_advertisement(data: AdCreate, db: DBDep, current_user: CurrentUserDep):
    ad = Advertisement(**data.model_dump(), owner_id=current_user.id)
    db.add(ad)
    await db.flush()
    return ad


@app.patch(
    "/advertisement/{advertisement_id}",
    response_model=AdResponse,
    tags=["Advertisements"],
    summary="Обновить объявление",
    description="""
    Частично обновляет существующее объявление.
    Пользователь может обновлять только свои объявления. Админ — любые.

    - Нужно передать **только те поля**, которые вы хотите изменить.
    - Поля `title`, `description` и `author` проходят строгую проверку: пустые строки или строки из пробелов вызовут ошибку **400 Bad Request**.
    - Если не передать ни одного поля, сервер вернет ошибку **400 Bad Request**.
    - Если объявление не найдено, вернется ошибка **404 Not Found**.
    """,
)
async def update_advertisement(data: AdUpdate, ad: AdDep, current_user: CurrentUserDep):
    # Проверка прав: либо админ, либо владелец объявления
    if current_user.role != "admin" and ad.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Недостаточно прав для редактирования чужого объявления")

    update_data = data.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(status_code=400, detail="Нет данных для обновления")

    for k, v in update_data.items():
        setattr(ad, k, v)
    return ad


@app.delete(
    "/advertisement/{advertisement_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["Advertisements"],
    summary="Удалить объявление",
    description="""
    Безвозвратно удаляет объявление из базы данных по его ID.
    Пользователь может удалять только свои объявления. Админ — любые.
    
    - В случае успеха возвращает статус **204 No Content** (пустой ответ).
    - Если объявление с таким ID не найдено, вернет ошибку **404 Not Found**.
    """,
)
async def delete_advertisement(ad: AdDep, current_user: CurrentUserDep, db: DBDep):
    # Проверка прав: либо админ, либо владелец объявления
    if current_user.role != "admin" and ad.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Недостаточно прав для удаления чужого объявления")

    await db.delete(ad)
    return None


# Поиск. ( ?title=Кошак&min_price=100 )
@app.get(
    "/advertisement",
    response_model=list[AdResponse],
    tags=["Advertisements"],
    summary="Поиск объявлений",
    description="""
**Правила поиска:**

- `title` - ищет **частичное совпадение** без учета регистра. Например, запрос `кош` найдет объявления со словами *Кошка*, *хорошая кошка*, *Кошелек*.
- `author` - ищет **строгое совпадение**. Запрос `Иван` не найдет `Иван Иванов`.
- `min_price` / `max_price` - фильтруют по диапазону цены включительно.

Параметры можно комбинировать. Если параметры не переданы - вернет все объявления.
Доступно всем без авторизации.
""",
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
