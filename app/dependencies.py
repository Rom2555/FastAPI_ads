from typing import Annotated, AsyncGenerator

from fastapi import Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from database import async_session
from models import Advertisement


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Зависимость для получения сессии БД с автоматическим коммитом/откатом."""
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def get_ad_obj(advertisement_id: int, db: AsyncSession = Depends(get_db)) -> Advertisement:
    """Извлекает объявление по ID или выбрасывает 404."""
    ad = await db.get(Advertisement, advertisement_id)
    if not ad:
        raise HTTPException(status_code=404, detail="Объявление не найдено")
    return ad


# Типизация для внедрения зависимостей
DBDep = Annotated[AsyncSession, Depends(get_db)]
AdDep = Annotated[Advertisement, Depends(get_ad_obj)]
