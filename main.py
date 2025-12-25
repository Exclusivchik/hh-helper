# main.py
import logging
import sys
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.routers import vacancies, ammap

# Настройка логирования с поддержкой UTF-8
file_handler = logging.FileHandler("app.log", encoding='utf-8')
stream_handler = logging.StreamHandler(sys.stdout)
stream_handler.stream.reconfigure(encoding='utf-8') if hasattr(stream_handler.stream, 'reconfigure') else None

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[file_handler, stream_handler]
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Запуск приложения
    logger.info("Starting application...")
    yield
    # Завершение работы приложения
    logger.info("Shutting down application...")


# Создание экземпляра FastAPI
app = FastAPI(
    title="HeadHunter API",
    description="API для поиска вакансий с поддержкой фильтров HeadHunter",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# Настройка CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "https://yourdomain.com"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"]
)

# Подключение статических файлов
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Подключение роутеров
app.include_router(vacancies.router)

app.include_router(ammap.router)  # Добавляем AmCharts карту

# Эндпоинт для проверки здоровья
@app.get("/health", tags=["health"])
async def health_check():
    """
    Проверка статуса работы API
    """
    return {
        "status": "healthy",
        "version": "1.0.0",
        "service": "HeadHunter API"
    }


# Эндпоинт для основной информации
@app.get("/", tags=["info"])
async def root():
    """
    Основная информация о API
    """
    return {
        "message": "HeadHunter Vacancies API",
        "version": "1.0.0",
        "docs": "/docs",
        "endpoints": {
            "vacancies": "/vacancies",
            "health": "/health"
        }
    }


# Эндпоинт для получения информации о версии
@app.get("/version", tags=["info"])
async def get_version():
    """
    Получение информации о версии API
    """
    return {"version": "1.0.0"}


if __name__ == "__main__":
    # Запуск сервера при прямом вызове файла
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
