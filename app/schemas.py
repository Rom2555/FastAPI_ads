from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import Select


# Схемы Pydantic

class AdSchema(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(min_length=1, max_length=300)
    price: int = Field(ge=0, description="Цена не может быть отрицательной")
    author: str = Field(min_length=1, max_length=100)

    @field_validator("title", "description", "author", mode="before")
    @classmethod
    def strip_ws(cls, v):
        if isinstance(v, str):
            v = v.strip()
        if not v:
            raise ValueError("Поле не может быть пустым или состоять из пробелов")
        return v


class AdCreate(AdSchema):
    pass


class AdUpdate(BaseModel):
    # Все поля опциональны для PATCH
    title: str | None = Field(None, min_length=1, max_length=200)
    description: str | None = Field(None, min_length=1, max_length=300)
    price: int | None = Field(None, ge=0)
    author: str | None = Field(None, min_length=1, max_length=100)


class AdResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    title: str
    description: str
    price: int
    author: str
    created_at: datetime | None


class AdFilter(BaseModel):
    """Схема для фильтрации объявлений."""
    title: Optional[str] = Field(None, description="Поиск по заголовку (частичное совпадение)")
    author: Optional[str] = Field(None, description="Поиск по автору (точное совпадение)")
    min_price: Optional[int] = Field(None, ge=0, description="Минимальная цена")
    max_price: Optional[int] = Field(None, ge=0, description="Максимальная цена")

    def filter_query(self, query: Select) -> Select:
        """Применяет фильтры к sqlalchemy запросу, если они переданы"""
        filters = self.model_dump(exclude_unset=True)

        for key, value in filters.items():
            if key == "title":
                # Поиск по вхождению исключая регистр
                query = query.where(Advertisement.title.ilike(f"%{value}%"))
            elif key == "min_price":
                query = query.where(Advertisement.price >= value)
            elif key == "max_price":
                query = query.where(Advertisement.price <= value)
            else:
                # Для остальных полей (например author) - точное совпадение
                column = getattr(Advertisement, key, None)
                if column is not None:
                    query = query.where(column == value)

        return query
