from flask import Flask
from threading import Thread
import time
import os
import requests
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

class KeepAlive:
    def __init__(self):
        self.app = app
        self.thread = None
        self.is_running = False
        
        # Настройка маршрутов
        self.setup_routes()
    
    def setup_routes(self):
        @self.app.route('/')
        def home():
            return """
            <!DOCTYPE html>
            <html>
            <head>
                <title>🤖 AI Products Bot</title>
                <meta charset="utf-8">
                <meta name="viewport" content="width=device-width, initial-scale=1">
                <style>
                    body {
                        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                        color: white;
                        text-align: center;
                        padding: 50px;
                        min-height: 100vh;
                        display: flex;
                        flex-direction: column;
                        justify-content: center;
                        align-items: center;
                    }
                    .container {
                        background: rgba(255, 255, 255, 0.1);
                        backdrop-filter: blur(10px);
                        padding: 40px;
                        border-radius: 20px;
                        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3);
                        max-width: 600px;
                        width: 90%;
                    }
                    h1 {
                        font-size: 2.5em;
                        margin-bottom: 20px;
                    }
                    .status {
                        font-size: 1.5em;
                        color: #4CAF50;
                        margin: 20px 0;
                        padding: 10px;
                        background: rgba(76, 175, 80, 0.2);
                        border-radius: 10px;
                    }
                    .info {
                        margin: 20px 0;
                        line-height: 1.6;
                    }
                    .time {
                        font-size: 0.9em;
                        opacity: 0.8;
                        margin-top: 30px;
                    }
                </style>
            </head>
            <body>
                <div class="container">
                    <h1>🤖 AI Products Bot</h1>
                    <div class="status">✅ Сервер работает</div>
                    <div class="info">
                        <p>Telegram бот для создания и продажи AI продуктов</p>
                        <p>Бот активен и готов принимать команды</p>
                    </div>
                    <div class="time">
                        Серверное время: {time}
                    </div>
                </div>
                <script>
                    function updateTime() {{
                        const now = new Date();
                        const timeStr = now.toLocaleString('ru-RU');
                        document.querySelector('.time').innerHTML = 
                            `Серверное время: ${{timeStr}}`;
                    }}
                    setInterval(updateTime, 1000);
                    updateTime();
                </script>
            </body>
            </html>
            """.format(time=time.strftime('%Y-%m-%d %H:%M:%S'))
        
        @self.app.route('/health')
        def health():
            return {
                "status": "healthy",
                "service": "telegram-ai-bot",
                "timestamp": time.time(),
                "environment": os.environ.get('REPL_ID', 'production')
            }
        
        @self.app.route('/ping')
        def ping():
            return "pong"
    
    def start_server(self):
        """Запуск Flask сервера"""
        port = int(os.environ.get('PORT', 8080))
        logger.info(f"🚀 Запуск веб-сервера на порту {port}")
        self.app.run(
            host='0.0.0.0',
            port=port,
            debug=False,
            use_reloader=False
        )
    
    def start_ping_service(self):
        """Сервис для самопинга (чтобы Replit не засыпал)"""
        # Получаем URL Replit
        repl_owner = os.environ.get('REPL_OWNER', '')
        repl_slug = os.environ.get('REPL_SLUG', '')
        
        if not repl_owner or not repl_slug:
            logger.warning("⚠️ Не удалось определить URL Replit")
            return
        
        repl_url = f"https://{repl_slug}.{repl_owner}.repl.co"
        logger.info(f"🔗 URL Replit: {repl_url}")
        
        while self.is_running:
            try:
                # Пингуем себя каждые 4.5 минуты
                response = requests.get(f"{repl_url}/ping", timeout=5)
                if response.status_code == 200:
                    logger.debug("🔄 Самопинг успешен")
                else:
                    logger.warning(f"⚠️ Самопинг не удался: {response.status_code}")
            except Exception as e:
                logger.error(f"❌ Ошибка самопинга: {e}")
            
            # Ждем 270 секунд (4.5 минуты)
            for i in range(9):
                if not self.is_running:
                    break
                time.sleep(30)
    
    def start(self):
        """Запуск всех сервисов keep-alive"""
        self.is_running = True
        
        # Запускаем Flask сервер в отдельном потоке
        self.thread = Thread(target=self.start_server, daemon=True)
        self.thread.start()
        
        # Запускаем сервис самопинга в отдельном потоке
        ping_thread = Thread(target=self.start_ping_service, daemon=True)
        ping_thread.start()
        
        logger.info("✅ Keep-alive сервисы запущены")
        return self
    
    def stop(self):
        """Остановка всех сервисов"""
        self.is_running = False
        logger.info("🛑 Keep-alive сервисы остановлены")

# Создаем глобальный экземпляр
keep_alive = KeepAlive()
