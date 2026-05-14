from datetime import datetime
from typing import Annotated, Optional

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field
from sqlalchemy import Select


# Вспомогательная функция
def strip_ws(v):
    """Обрезает пробелы и запрещает пустые строки."""
    if isinstance(v, str):
        v = v.strip()
    if not v:
        raise ValueError("Поле не может быть пустым или состоять из пробелов")
    return v


# Тип данных для схем. strip_ws выполнится до проверок Pydantiс
StrippedStr = Annotated[str, BeforeValidator(strip_ws)]


class AdSchema(BaseModel):
    title: StrippedStr = Field(min_length=1, max_length=200)
    description: StrippedStr = Field(min_length=1, max_length=300)
    price: int = Field(ge=0, description="Цена не может быть отрицательной")
    author: StrippedStr = Field(min_length=1, max_length=100)


class AdCreate(AdSchema):
    # Пример данных, который будет отображаться в Swagger
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "title": "Продам велосипед",
                    "description": "Отличный горный велосипед, почти новый.",
                    "price": 15000,
                    "author": "Иван Иванов",
                }
            ]
        }
    )


class AdUpdate(BaseModel):
    title: Optional[StrippedStr] = Field(None, min_length=1, max_length=200)
    description: Optional[StrippedStr] = Field(None, min_length=1, max_length=300)
    price: Optional[int] = Field(None, ge=0)
    author: Optional[StrippedStr] = Field(None, min_length=1, max_length=100)

    # Пример данных, который будет отображаться в Swagger
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [{"price": 12000, "description": "Цена снижена! Срочно!"}]
        }
    )


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

    title: Optional[str] = Field(
        None, description="Поиск по заголовку (частичное совпадение)"
    )
    author: Optional[str] = Field(
        None, description="Поиск по автору (точное совпадение)"
    )
    min_price: Optional[int] = Field(None, ge=0, description="Минимальная цена")
    max_price: Optional[int] = Field(None, ge=0, description="Максимальная цена")

    def filter_query(self, query: Select, model) -> Select:
        """Фильтрует запрос на основе данных из схемы фильтра."""
        filters = self.model_dump(exclude_unset=True, exclude_none=True)

        for key, value in filters.items():
            if key == "title":
                # Частичное совпадение. Регистр не влияет
                query = query.where(model.title.ilike(f"%{value}%"))

            elif key == "author":
                # Точное совпадение
                query = query.where(model.author == value)

            elif key == "min_price":
                query = query.where(model.price >= value)

            elif key == "max_price":
                query = query.where(model.price <= value)

        return query
