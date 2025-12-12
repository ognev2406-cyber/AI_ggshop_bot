import httpx
from typing import Optional, Dict, Any
import logging
from urllib.parse import urlparse
from config import OLLAMA_BASE_URL, OLLAMA_MODEL

logger = logging.getLogger(__name__)


class OllamaService:
    """Сервис для работы с Ollama (бесплатный локальный AI)"""
    
    def __init__(self):
        self.base_url = OLLAMA_BASE_URL
        self.model = OLLAMA_MODEL
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=30.0
        )
        logger.info(f"✅ Сервис Ollama инициализирован: {self.base_url}, модель: {self.model}")
    
    async def check_api_access(self) -> bool:
        """Проверка доступности Ollama"""
        try:
            response = await self.client.get("/api/tags")
            if response.status_code == 200:
                logger.info("✅ Ollama доступен")
                return True
            return False
        except Exception as e:
            logger.error(f"❌ Ollama недоступен: {e}")
            return False
    
    async def generate_text(
        self, 
        prompt: str, 
        system_prompt: Optional[str] = None,
        temperature: float = 0.7
    ) -> str:
        """Генерация текста через Ollama"""
        try:
            messages = []
            
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            
            messages.append({"role": "user", "content": prompt})
            
            payload = {
                "model": self.model,
                "messages": messages,
                "stream": False,
                "options": {
                    "temperature": temperature,
                    "num_predict": 1000
                }
            }
            
            logger.info(f"📝 Генерация текста через Ollama: {self.model}")
            
            response = await self.client.post(
                "/api/chat",
                json=payload,
                timeout=60.0
            )
            
            if response.status_code == 200:
                result = response.json()["message"]["content"]
                logger.info(f"✅ Текст сгенерирован, длина: {len(result)} символов")
                return result.strip()
            else:
                error_msg = f"Ошибка Ollama: {response.status_code}"
                logger.error(error_msg)
                return f"❌ {error_msg}"
        
        except httpx.TimeoutException:
            logger.error("❌ Таймаут при генерации текста")
            return "❌ Превышено время ожидания. Попробуйте позже."
        except Exception as e:
            logger.error(f"❌ Ошибка при генерации текста: {e}")
            return f"❌ Произошла ошибка: {str(e)}"
    
    async def generate_image(
        self, 
        prompt: str,
        size: str = "1024x1024"
    ) -> Optional[str]:
        """Ollama не генерирует изображения, но можно использовать другие модели"""
        return "⚠️ Генерация изображений через Ollama недоступна. Используйте Stable Diffusion или другую модель."
    
    async def list_models(self) -> list:
        """Получить список доступных моделей"""
        try:
            response = await self.client.get("/api/tags")
            if response.status_code == 200:
                return [model["name"] for model in response.json().get("models", [])]
            return []
        except:
            return []


# Создаем глобальный экземпляр сервиса
ollama_service = OllamaService()