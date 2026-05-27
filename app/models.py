from sqlalchemy import (Column, DateTime, ForeignKey, Integer, String, Text,
                        func)
from sqlalchemy.orm import relationship

from database import Base


# Модель пользователя
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    # имя пользователя
    username = Column(String(100), unique=True, nullable=False, index=True)
    # Хеш пароля
    password_hash = Column(String(255), nullable=False)
    # Роль пользователя
    role = Column(String(50), nullable=False, default="user")

    created_at = Column(DateTime, default=func.now(), nullable=False)
    # Связь с объявлениями
    ads = relationship("Advertisement", back_populates="owner")


# Модель объявления
class Advertisement(Base):
    __tablename__ = "advertisements"

    id = Column(Integer, primary_key=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=False)
    price = Column(Integer, nullable=False)
    author = Column(String(100), nullable=False)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    # ID владельца
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    # Связь с пользователем
    owner = relationship("User", back_populates="ads")
