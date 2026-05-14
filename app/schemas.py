from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


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
