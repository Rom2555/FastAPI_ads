from typing import Annotated, AsyncGenerator, Optional

from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

import auth
from database import async_session
from models import Advertisement, User


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Зависимость для получения сессии БД с автоматическим коммитом/откатом."""
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def get_ad_obj(
    advertisement_id: int, db: AsyncSession = Depends(get_db)
) -> Advertisement:
    """Извлекает объявление по ID или выбрасывает 404."""
    ad = await db.get(Advertisement, advertisement_id)
    if not ad:
        raise HTTPException(status_code=404, detail="Объявление не найдено")
    return ad


async def get_user_obj(user_id: int, db: AsyncSession = Depends(get_db)) -> User:
    """Извлекает пользователя по ID или выбрасывает 404."""
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    return user


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login", auto_error=False)


# Вспомогательная функция
async def _decode_and_get_user(token: Optional[str], db: AsyncSession):
    if not token:
        return None
    payload = auth.decode_access_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Неверный или просроченный токен")

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Неверный токен")

    user = await db.get(User, int(user_id))
    if not user:
        raise HTTPException(status_code=401, detail="Пользователь не найден")
    return user


async def get_current_user(
    token: Optional[str] = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)
) -> User:
    """Строгая проверка: токен ОБЯЗАТЕЛЕН. Если его нет или он кривой - 401."""
    user = await _decode_and_get_user(token, db)
    if not user:
        raise HTTPException(status_code=401, detail="Требуется авторизация")
    return user


async def get_current_user_optional(
    token: Optional[str] = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)
) -> Optional[User]:
    """Мягкая проверка: если токена нет - вернет None. Если есть - проверит и вернет юзера."""
    return await _decode_and_get_user(token, db)


# Типизация для внедрения зависимостей
DBDep = Annotated[AsyncSession, Depends(get_db)]
AdDep = Annotated[Advertisement, Depends(get_ad_obj)]
UserDep = Annotated[User, Depends(get_user_obj)]
CurrentUserDep = Annotated[User, Depends(get_current_user)]
OptionalUserDep = Annotated[Optional[User], Depends(get_current_user_optional)]
