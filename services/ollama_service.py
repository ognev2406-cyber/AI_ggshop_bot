import httpx
import logging
import asyncio
from typing import Optional, Dict, Any, List
from config import OLLAMA_BASE_URL, OLLAMA_MODEL, OLLAMA_TIMEOUT

logger = logging.getLogger(__name__)


class OllamaService:
    """Сервис для работы с Ollama с улучшенными таймаутами"""
    
    def __init__(self):
        self.base_url = OLLAMA_BASE_URL
        self.model = OLLAMA_MODEL
        self.timeout = OLLAMA_TIMEOUT
        
        # Создаем клиент с большими таймаутами
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=30.0
        )
        logger.info(f"✅ Сервис Ollama инициализирован: {self.base_url}, модель: {self.model}, таймаут: {self.timeout}с")
    
    async def check_api_access(self) -> bool:
        """Проверка доступности Ollama"""
        try:
            response = await self.client.get("/api/tags")
            if response.status_code == 200:
                models_data = response.json().get("models", [])
                available_models = [m["name"] for m in models_data]
                
                # Проверяем точное совпадение
                if self.model in available_models:
                    logger.info(f"✅ Модель '{self.model}' найдена")
                    return True
                
                # Проверяем совпадение по префиксу
                model_prefix = self.model.split(':')[0]
                for available_model in available_models:
                    if available_model.startswith(model_prefix + ':'):
                        logger.info(f"✅ Модель найдена как '{available_model}'")
                        self.model = available_model
                        return True
                    elif available_model == model_prefix:
                        logger.info(f"✅ Модель найдена как '{available_model}'")
                        self.model = available_model
                        return True
                
                logger.warning(f"⚠️ Модель '{self.model}' не найдена. Доступные: {available_models}")
                return False
            return False
        except Exception as e:
            logger.error(f"❌ Ollama недоступен: {e}")
            return False
    
    async def generate_text(
        self, 
        prompt: str, 
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 500  # Уменьшим для скорости
    ) -> str:
        """Генерация текста с улучшенной обработкой ошибок"""
        try:
            messages = []
            
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            
            messages.append({"role": "user", "content": prompt})
            
            logger.info(f"📝 Генерация текста, модель: {self.model}, промпт: {prompt[:50]}...")
            
            # Используем более простой запрос для скорости
            payload = {
                "model": self.model,
                "messages": messages,
                "stream": False,
                "options": {
                    "temperature": temperature,
                    "num_predict": max_tokens  # Ограничим длину ответа
                }
            }
            
            # Отправляем запрос с таймаутом
            response = await asyncio.wait_for(
                self.client.post("/api/chat", json=payload),
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                result = response.json()
                generated_text = result.get("message", {}).get("content", "").strip()
                
                if not generated_text:
                    logger.warning("⚠️ Модель вернула пустой ответ")
                    return "❌ Модель вернула пустой ответ. Попробуйте другой запрос."
                
                logger.info(f"✅ Текст сгенерирован, длина: {len(generated_text)} символов")
                return generated_text
            else:
                error_msg = f"Ошибка Ollama: {response.status_code}"
                logger.error(f"{error_msg}, ответ: {response.text}")
                return f"❌ {error_msg}"
        
        except asyncio.TimeoutError:
            logger.error(f"⏱️ Таймаут при генерации текста ({self.timeout} сек)")
            return f"❌ Таймаут при генерации ({self.timeout} сек). Упростите запрос или попробуйте позже."
        except httpx.TimeoutException:
            logger.error(f"⏱️ Таймаут HTTP при генерации текста")
            return "❌ Таймаут соединения. Проверьте интернет и попробуйте позже."
        except Exception as e:
            logger.error(f"❌ Ошибка при генерации текста: {e}")
            return f"❌ Ошибка: {str(e)[:100]}"
    
    async def quick_test(self, prompt: str = "Привет! Ответь одним словом.") -> str:
        """Быстрый тест модели"""
        try:
            logger.info(f"⚡ Быстрый тест модели {self.model}...")
            
            payload = {
                "model": self.model,
                "messages": [{"role": "user", "content": prompt}],
                "stream": False,
                "options": {
                    "temperature": 0.7,
                    "num_predict": 20  # Очень короткий ответ
                }
            }
            
            # Быстрый таймаут для теста
            response = await asyncio.wait_for(
                self.client.post("/api/chat", json=payload),
                timeout=30.0  # 30 секунд для теста
            )
            
            if response.status_code == 200:
                result = response.json()
                return result.get("message", {}).get("content", "").strip()
            return "❌ Ошибка теста"
        except asyncio.TimeoutError:
            return "❌ Таймаут при тесте"
        except Exception as e:
            return f"❌ Ошибка: {str(e)}"


# Создаем глобальный экземпляр сервиса
ollama_service = OllamaService()