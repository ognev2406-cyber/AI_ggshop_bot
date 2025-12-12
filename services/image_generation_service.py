# services/image_generation_service.py
import aiohttp
import base64
import logging
from typing import Optional, Tuple
import random

logger = logging.getLogger(__name__)


class ImageGenerationService:
    """Сервис для генерации изображений через разные API"""
    
    def __init__(self):
        self.services = [
            self._try_huggingface,
            self._try_openrouter,
            self._try_prodia,  # Еще один бесплатный сервис
        ]
    
    async def generate(self, prompt: str) -> Tuple[str, Optional[bytes]]:
        """Пробуем разные сервисы по очереди"""
        for service in self.services:
            try:
                result_text, image_bytes = await service(prompt)
                if image_bytes:
                    return result_text, image_bytes
            except Exception as e:
                logger.warning(f"Сервис {service.__name__} недоступен: {e}")
                continue
        
        return "❌ Все сервисы генерации изображений временно недоступны", None
    
    async def _try_huggingface(self, prompt: str) -> Tuple[str, Optional[bytes]]:
        """Пробуем Hugging Face"""
        # Используем публичную модель без API ключа
        model = random.choice([
            "stabilityai/stable-diffusion-2-1",
            "runwayml/stable-diffusion-v1-5",
        ])
        
        url = f"https://api-inference.huggingface.co/models/{model}"
        
        async with aiohttp.ClientSession() as session:
            payload = {"inputs": prompt}
            async with session.post(url, json=payload) as response:
                if response.status == 200:
                    return "✅ Изображение сгенерировано", await response.read()
        
        return "❌ Ошибка Hugging Face", None
    
    async def _try_openrouter(self, prompt: str) -> Tuple[str, Optional[bytes]]:
        """Пробуем OpenRouter"""
        url = "https://openrouter.ai/api/v1/generation"
        
        payload = {
            "model": "black-forest-labs/flux-schnell",
            "prompt": prompt,
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload) as response:
                if response.status == 200:
                    data = await response.json()
                    if "data" in data:
                        image_base64 = data["data"][0].get("url", "").split(",")[-1]
                        return "✅ Изображение сгенерировано", base64.b64decode(image_base64)
        
        return "❌ Ошибка OpenRouter", None
    
    async def _try_prodia(self, prompt: str) -> Tuple[str, Optional[bytes]]:
        """Пробуем Prodia (еще один бесплатный сервис)"""
        # Получаем список моделей
        async with aiohttp.ClientSession() as session:
            async with session.get("https://api.prodia.com/v1/sd/models") as response:
                if response.status == 200:
                    models = await response.json()
                    if models:
                        model = random.choice(models)
                        
                        # Генерируем изображение
                        generate_url = "https://api.prodia.com/v1/sd/generate"
                        payload = {
                            "model": model,
                            "prompt": prompt,
                            "width": 512,
                            "height": 512,
                        }
                        
                        async with session.post(generate_url, json=payload) as gen_response:
                            if gen_response.status == 200:
                                job_id = (await gen_response.json()).get("job")
                                
                                # Проверяем статус
                                check_url = f"https://api.prodia.com/v1/job/{job_id}"
                                for _ in range(30):  # Ждем до 30 секунд
                                    import asyncio
                                    await asyncio.sleep(1)
                                    
                                    async with session.get(check_url) as check_response:
                                        if check_response.status == 200:
                                            job_data = await check_response.json()
                                            if job_data.get("status") == "succeeded":
                                                image_url = job_data.get("imageUrl")
                                                if image_url:
                                                    async with session.get(image_url) as img_response:
                                                        if img_response.status == 200:
                                                            return "✅ Изображение сгенерировано", await img_response.read()
        
        return "❌ Ошибка Prodia", None


# Глобальный экземпляр
image_service = ImageGenerationService()