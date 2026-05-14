from sqlalchemy import Column, DateTime, Integer, String, Text, func

from app.database import Base


# Модель база данных
class Advertisement(Base):
    __tablename__ = "advertisements"

    id = Column(Integer, primary_key=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=False)
    price = Column(Integer, nullable=False)
    author = Column(String(100), nullable=False)
    created_at = Column(DateTime, default=func.now(), nullable=False)
