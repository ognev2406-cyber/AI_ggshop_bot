import os
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

# ========== БОТ ==========
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
STABLE_DIFFUSION_URL = "http://localhost:7860"
# Используем готовый сервер
COLAB_ENABLED = True
COLAB_API_URL = "https://casteless-factiously-julee.ngrok-free.dev"
REPLICATE_API_TOKEN = os.getenv("REPLICATE_API_TOKEN", "")
# Отключаем остальное
STABLE_DIFFUSION_ENABLED = False
PRODIA_ENABLED = False
TENSOR_ART_ENABLED = False
REPLICATE_API_TOKEN = os.getenv("REPLICATE_API_TOKEN", "")

# ========== РЕКЛАМА ==========
AD_REWARD_AMOUNT = 50  # Было 10
AD_WATCH_TIME = 40     # Можно оставить или изменить
MAX_ADS_PER_DAY = 15   # Было 3
AD_COOLDOWN_MINUTES = 0  # Можно смотреть сразу же, или поставить 5-10 минут
DAILY_BONUS_AMOUNT = 200  # Бонус за все 15 просмотров
DAILY_BONUS_THRESHOLD = 15  # Минимум просмотров для бонуса
# ========== OLLAMA ==========
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama2")
OLLAMA_TIMEOUT = 300  # 5 минут для генерации
OLLAMA_CHAT_TIMEOUT = 180  # 3 минуты для чат-запросов
GENERATION_TIMEOUT = 240
STABLE_DIFFUSION_URL = "http://localhost:7860"
IMAGE_MODEL = "dreamshaper_8.safetensors"  # или другая модель
IMAGE_WIDTH = 512
IMAGE_HEIGHT = 512
IMAGE_STEPS = 20
IMAGE_CFG_SCALE = 7.5 

# ========== МЕНЕДЖЕР ==========
MANAGER_USERNAME = os.getenv("MANAGER_USERNAME", "@ваш_менеджер")
MANAGER_ID = int(os.getenv("MANAGER_ID", "0")) if os.getenv("MANAGER_ID") else None
# ========== ПЛАТЕЖИ ==========
MIN_PAYMENT_AMOUNT = int(os.getenv("MIN_PAYMENT_AMOUNT", "100"))
MAX_PAYMENT_AMOUNT = int(os.getenv("MAX_PAYMENT_AMOUNT", "50000"))
PAYMENT_TIMEOUT_HOURS = int(os.getenv("PAYMENT_TIMEOUT_HOURS", "24"))
FREE_TRIAL_AMOUNT = int(os.getenv("FREE_TRIAL_AMOUNT", "50"))
# ========== ЦЕНЫ ==========
PRICE_CONFIG = {
    'text_generation': 15,
    'image_generation': 20,  # Новая цена для генерации изображений
    'image_sd': 15,
    'image_hd': 25,
    'image_4k': 40,
    'audio_short': 5,     # До 500 символов
    'audio_long': 10,
}

# ========== БАЗА ДАННЫХ ==========
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///database.db")

# ========== АДМИНИСТРАТОРЫ ==========
ADMIN_IDS = list(map(int, os.getenv("ADMIN_IDS", "").split(","))) if os.getenv("ADMIN_IDS") else []

# ========== ДРУГИЕ НАСТРОЙКИ ==========
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# ========== ГЕНЕРАЦИЯ ИЗОБРАЖЕНИЙ ==========
# Colab сервер (если есть)
COLAB_ENABLED = os.getenv("COLAB_ENABLED", "False").lower() == "true"
COLAB_API_URL = os.getenv("COLAB_API_URL", "")

# Hugging Face API
HF_API_TOKEN = os.getenv("HF_API_TOKEN", "")  # Необязательно для базового использования

# OpenRouter API (бесплатный)
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")

# Включаем генерацию изображений
STABLE_DIFFUSION_ENABLED = True  # Меняем на True

# config.py - добавьте в конец
# ========== ПРОВЕРКИ ==========
if not BOT_TOKEN:
    raise ValueError("❌ BOT_TOKEN не установлен. Проверьте .env файл")

if not OLLAMA_BASE_URL:
    print("⚠️ OLLAMA_BASE_URL не установлен, используется localhost:11434")

if not OLLAMA_MODEL:
    print("⚠️ OLLAMA_MODEL не установлен, используется llama2")