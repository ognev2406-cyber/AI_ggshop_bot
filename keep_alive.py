from flask import Flask, request
from threading import Thread
import time
import logging
import os

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

@app.route('/')
def home():
    """Основная страница для проверки работы"""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Telegram Bot Status</title>
        <style>
            body { font-family: Arial, sans-serif; text-align: center; padding: 50px; }
            .status { color: green; font-size: 24px; }
        </style>
    </head>
    <body>
        <h1>🤖 Telegram Bot Status</h1>
        <p class="status">✅ Бот работает исправно</p>
        <p>Время сервера: {}</p>
        <p>Для проверки доступности используйте /health</p>
    </body>
    </html>
    """.format(time.strftime('%Y-%m-%d %H:%M:%S'))

@app.route('/health')
def health_check():
    """Эндпоинт для проверки здоровья (используется UptimeRobot)"""
    return {
        "status": "healthy",
        "timestamp": time.time(),
        "service": "telegram-bot",
        "message": "Bot is running"
    }, 200

@app.route('/ping')
def ping():
    """Простой пинг для внешних сервисов"""
    return "pong", 200

def run_web_server():
    """Запуск Flask веб-сервера"""
    port = int(os.environ.get('PORT', 8080))
    logger.info(f"Starting web server on port {port}")
    app.run(host='0.0.0.0', port=port, debug=False)

class KeepAlive:
    """Класс для управления поддержанием активности"""
    
    def __init__(self):
        self.webserver_thread = None
        self.ping_thread = None
        self.is_running = False
        
    def start(self):
        """Запуск всех механизмов поддержания активности"""
        self.is_running = True
        
        # Запускаем веб-сервер в отдельном потоке
        self.webserver_thread = Thread(target=run_web_server, daemon=True)
        self.webserver_thread.start()
        logger.info("Web server thread started")
        
        # Запускаем пинг-сервис (опционально)
        self.ping_thread = Thread(target=self._ping_service, daemon=True)
        self.ping_thread.start()
        logger.info("Ping service started")
        
        return self
    
    def _ping_service(self):
        """Сервис для периодического пинга самого себя"""
        import requests
        
        # Получаем URL Replit из переменных окружения
        repl_url = os.environ.get('REPLIT_URL')
        if not repl_url:
            # Пытаемся определить URL автоматически
            try:
                repl_owner = os.environ.get('REPL_OWNER', 'unknown')
                repl_slug = os.environ.get('REPL_SLUG', 'unknown')
                repl_url = f"https://{repl_slug}.{repl_owner}.repl.co"
            except:
                logger.warning("Cannot determine Replit URL, skipping ping service")
                return
        
        logger.info(f"Ping service targeting: {repl_url}")
        
        while self.is_running:
            try:
                response = requests.get(f"{repl_url}/ping", timeout=10)
                if response.status_code == 200:
                    logger.debug(f"Self-ping successful: {response.text}")
                else:
                    logger.warning(f"Self-ping failed with status: {response.status_code}")
            except requests.exceptions.RequestException as e:
                logger.error(f"Self-ping error: {e}")
            except Exception as e:
                logger.error(f"Unexpected error in ping service: {e}")
            
            # Ждем 4.5 минуты (меньше чем 5 минут сна Replit)
            for _ in range(9):
                if not self.is_running:
                    break
                time.sleep(30)  # Проверяем каждые 30 секунд
    
    def stop(self):
        """Остановка всех сервисов"""
        self.is_running = False
        logger.info("KeepAlive services stopping...")

# Создаем глобальный экземпляр
keep_alive_manager = KeepAlive()

# Функция для обратной совместимости
def keep_alive():
    """Старая функция для совместимости"""
    return keep_alive_manager.start()

# Быстрый запуск при импорте
if __name__ != "__main__":
    # Автоматически запускаем при импорте (если не основной файл)
    keep_alive_manager.start()
