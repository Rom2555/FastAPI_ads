# Advertisements API

API для работы с объявлениями, построенная на FastAPI и PostgreSQL.

## Особенности

- CRUD операции для объявлений
- Поиск объявлений по заголовку, автору и цене
- Валидация данных с Pydantic
- Автоматическая документация API (Swagger UI, ReDoc)
- Контейнеризация с Docker и Docker Compose

## Требования

- Docker и Docker Compose (для запуска в контейнерах)

## Запуск с Docker

1. Склонируйте репозиторий:
   git clone <URL репозитория>
   cd FastAPI_ads

2. Скопируйте пример файла окружения и настройте его:
   cp .env_example .env.

3. Отредактируйте .env, указав свои данные для PostgreSQL

4. Запустите приложение:
   docker-compose up --build

5. API будет доступно по адресу: http://localhost:8080


## Документация API

После запуска приложения откройте:
- Swagger UI: http://localhost:8080/docs
- ReDoc: http://localhost:8080/redoc

## Структура проекта

- `app/` - основной код приложения
  - `app.py` - точка входа и настройка FastAPI
  - `models.py` - SQLAlchemy модели
  - `schemas.py` - Pydantic схемы
  - `database.py` - настройка базы данных
  - `dependencies.py` - зависимости для эндпоинтов
- `requirements.txt` - зависимости Python
- `Dockerfile` - образ для приложения
- `docker-compose.yml` - конфигурация для Docker Compose
- `.env_example` - пример файла окружения

## Примечание

Это учебный проект и создан в рамках курса "Python разработчик" от netology.ru