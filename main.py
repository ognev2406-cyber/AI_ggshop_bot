import asyncio
import logging
import sys
import os
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from config import BOT_TOKEN
from services.tts_service import tts_service

# Импортируем обработчики
from handlers import router
from middlewares import register_middlewares

# Создаем папку logs, если ее нет
os.makedirs("logs", exist_ok=True)

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("logs/bot.log", encoding="utf-8", mode="a")
    ]
)
logger = logging.getLogger(__name__)


async def main():
    """Основная функция запуска бота"""
    # Проверяем наличие токена
    if not BOT_TOKEN:
        logger.error("❌ BOT_TOKEN не установлен. Проверьте .env файл")
        sys.exit(1)
    
    logger.info("🚀 Запуск бота...")
    
    # Инициализируем базу данных
    from database import init_db
    await init_db()
    logger.info("✅ База данных инициализирована")
    
    # Создаем бота и диспетчер
    bot = Bot(token=BOT_TOKEN)
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)
    
    # Регистрируем middleware
    register_middlewares(dp)
    
    # Регистрируем роутер
    dp.include_router(router)
    
    # Проверяем доступность Ollama
    try:
        from services.ai_service import ai_service
        is_accessible = await ai_service.check_api_access()
        if is_accessible:
            logger.info("✅ AI сервис доступен")
        else:
            logger.warning("⚠️ AI сервис недоступен! Некоторые функции могут не работать.")
    except Exception as e:
        logger.error(f"❌ Ошибка проверки AI сервиса: {e}")
    
    # Запускаем бота
    logger.info("🤖 Бот запущен и готов к работе!")
    
    try:
        await dp.start_polling(bot)
    except KeyboardInterrupt:
        logger.info("🛑 Бот остановлен пользователем")
    except Exception as e:
        logger.error(f"❌ Критическая ошибка: {e}")
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())