import asyncio
import logging
import sys
import os
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from config import BOT_TOKEN

# Импортируем обработчики
from handlers import router
from middlewares import register_middlewares

# Импортируем keep_alive
from keep_alive import keep_alive

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


async def setup_bot():
    """Настройка и запуск бота"""
    # Проверяем наличие токена
    if not BOT_TOKEN:
        logger.error("❌ BOT_TOKEN не установлен. Проверьте .env файл")
        sys.exit(1)
    
    logger.info("🚀 Настройка бота...")
    
    # Инициализируем базу данных
    try:
        from database import init_db
        await init_db()
        logger.info("✅ База данных инициализирована")
    except Exception as e:
        logger.error(f"❌ Ошибка инициализации БД: {e}")
    
    # Создаем бота и диспетчер
    bot = Bot(token=BOT_TOKEN)
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)
    
    # Регистрируем middleware
    try:
        register_middlewares(dp)
        logger.info("✅ Middleware зарегистрированы")
    except Exception as e:
        logger.error(f"❌ Ошибка регистрации middleware: {e}")
    
    # Регистрируем роутер
    dp.include_router(router)
    
    # Проверяем доступность сервисов
    await check_services()
    
    return bot, dp


async def check_services():
    """Проверка доступности всех сервисов"""
    logger.info("🔍 Проверка доступности сервисов...")
    
    # Проверяем AI сервис
    try:
        from services.ai_service import ai_service
        is_accessible = await ai_service.check_api_access()
        if is_accessible:
            logger.info("✅ AI сервис доступен")
        else:
            logger.warning("⚠️ AI сервис недоступен! Некоторые функции могут не работать.")
    except Exception as e:
        logger.error(f"❌ Ошибка проверки AI сервиса: {e}")
    
    # Проверяем TTS сервис
    try:
        from services.tts_service import tts_service
        logger.info("✅ TTS сервис инициализирован")
    except Exception as e:
        logger.error(f"❌ Ошибка инициализации TTS сервиса: {e}")
    
    logger.info("🔍 Проверка сервисов завершена")


async def main():
    """Основная функция запуска бота"""
    # Запускаем keep-alive сервисы
    logger.info("🔗 Запуск keep-alive сервисов...")
    keep_alive.start()
    
    try:
        # Настраиваем бота
        bot, dp = await setup_bot()
        
        logger.info("🤖 Бот запущен и готов к работе!")
        logger.info("📱 Перейдите в Telegram и начните общение с ботом")
        
        # Запускаем polling
        await dp.start_polling(bot)
        
    except KeyboardInterrupt:
        logger.info("🛑 Бот остановлен пользователем")
    except Exception as e:
        logger.error(f"❌ Критическая ошибка: {e}", exc_info=True)
    finally:
        # Корректное завершение
        try:
            if 'bot' in locals():
                await bot.session.close()
                logger.info("📴 Сессия бота закрыта")
        except:
            pass
        
        # Останавливаем keep-alive
        keep_alive.stop()
        logger.info("🛑 Все сервисы остановлены")


if __name__ == "__main__":
    # Настройка переменных окружения для Replit
    if os.environ.get('REPLIT'):
        logger.info("🌐 Запуск в среде Replit")
        
        # Автоматическое определение порта
        if 'PORT' not in os.environ:
            os.environ['PORT'] = '8080'
        
        # Показываем ссылку на веб-интерфейс
        repl_owner = os.environ.get('REPL_OWNER', '')
        repl_slug = os.environ.get('REPL_SLUG', '')
        if repl_owner and repl_slug:
            logger.info(f"🌍 Веб-интерфейс: https://{repl_slug}.{repl_owner}.repl.co")
    
    # Запускаем бота
    try:
        asyncio.run(main())
    except Exception as e:
        logger.error(f"💥 Фатальная ошибка: {e}", exc_info=True)
        sys.exit(1)
