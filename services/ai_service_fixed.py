# services/ai_service_fixed.py
import aiohttp
import base64
import logging
import json
from typing import Optional, Tuple
import asyncio
import random
import urllib.parse
from config import OLLAMA_BASE_URL, OLLAMA_MODEL, COLAB_ENABLED, COLAB_API_URL, REPLICATE_API_TOKEN

logger = logging.getLogger(__name__)


class AIService:
    def __init__(self):
        # Настройки для Ollama
        self.base_url = OLLAMA_BASE_URL or "http://localhost:11434"
        self.model = OLLAMA_MODEL or "llama2"
        self.timeout = aiohttp.ClientTimeout(total=300)
        
        # Настройки для генерации изображений
        self.hf_api_token = None
    
    async def check_api_access(self) -> bool:
        """Проверяет доступность Ollama API"""
        try:
            logger.info(f"🔍 Проверка доступности Ollama: {self.base_url}")
            
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.get(f"{self.base_url}/api/tags") as response:
                    return response.status == 200
                        
        except Exception as e:
            logger.error(f"❌ Ошибка проверки Ollama: {e}")
            return False
    
    async def generate_text(
        self, 
        prompt: str, 
        system_prompt: Optional[str] = None,
        max_tokens: int = 2048,
        temperature: float = 0.7
    ) -> str:
        """Генерирует текст с помощью Ollama"""
        try:
            url = f"{self.base_url}/api/generate"
            
            payload = {
                "model": self.model,
                "prompt": prompt,
                "system": system_prompt,
                "options": {
                    "temperature": temperature,
                    "num_predict": max_tokens,
                },
                "stream": False
            }
            
            logger.info(f"🧠 Генерация текста: {prompt[:100]}...")
            
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.post(url, json=payload) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        return f"❌ Ошибка: {response.status}"
                    
                    result = await response.json()
                    return result.get("response", "❌ Пустой ответ").strip()
                    
        except Exception as e:
            logger.error(f"❌ Ошибка генерации текста: {e}")
            return f"❌ Ошибка: {str(e)}"
    
    # ВАЖНО: МЕТОД generate_image ДОЛЖЕН БЫТЬ ЗДЕСЬ
    async def generate_image(self, prompt: str) -> Tuple[str, Optional[bytes]]:
        """Генерация изображения - ОСНОВНОЙ МЕТОД"""
        logger.info(f"🖼️ Генерация изображения: {prompt[:50]}...")
        
        # Список методов в порядке приоритета
        methods = [
            self._generate_via_replicate,      # 1. Replicate
            self._generate_via_simple_api,     # 2. Pollinations
            self._generate_enhanced_fallback,  # 3. Fallback
        ]
        
        for i, method in enumerate(methods):
            try:
                logger.info(f"🔄 Попытка {i+1}: {method.__name__}")
                result_text, image_bytes = await method(prompt)
                
                if image_bytes and len(image_bytes) > 5000:
                    logger.info(f"✅ Успех: {method.__name__}")
                    return result_text, image_bytes
                    
            except Exception as e:
                logger.warning(f"⚠️ Ошибка {method.__name__}: {e}")
                continue
        
        return "❌ Все сервисы недоступны", None
    
    async def _generate_via_replicate(self, prompt: str) -> Tuple[str, Optional[bytes]]:
        """Генерация через Replicate.com"""
        if not REPLICATE_API_TOKEN:
            return "Replicate не настроен", None
        
        try:
            import replicate
            
            logger.info(f"🚀 Replicate: {prompt[:50]}...")
            
            client = replicate.Client(api_token=REPLICATE_API_TOKEN)
            
            # Простая модель для теста
            output = client.run(
                "stability-ai/stable-diffusion:ac732df83cea7fff18b8472768c88ad041fa750ff7682a21affe81863cbe77e4",
                input={
                    "prompt": prompt[:500],
                    "width": 512,
                    "height": 512,
                    "num_outputs": 1
                }
            )
            
            if output and len(output) > 0:
                image_url = output[0]
                
                # Скачиваем изображение
                async with aiohttp.ClientSession() as session:
                    async with session.get(image_url) as response:
                        if response.status == 200:
                            image_bytes = await response.read()
                            return "✅ Изображение сгенерировано (Replicate)", image_bytes
            
            return "❌ Replicate не вернул изображение", None
            
        except Exception as e:
            logger.error(f"❌ Ошибка Replicate: {e}")
            return f"❌ Ошибка Replicate", None
    
    async def _generate_via_simple_api(self, prompt: str) -> Tuple[str, Optional[bytes]]:
        """Генерация через простой API"""
        try:
            encoded_prompt = urllib.parse.quote(prompt[:150])
            url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=512&height=512"
            
            logger.info(f"🌐 Pollinations: {prompt[:50]}...")
            
            timeout = aiohttp.ClientTimeout(total=30)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        image_bytes = await response.read()
                        if len(image_bytes) > 5000:
                            return "✅ Изображение сгенерировано (Pollinations)", image_bytes
            
            return "❌ Pollinations недоступен", None
            
        except Exception as e:
            logger.error(f"❌ Ошибка Pollinations: {e}")
            return f"❌ Ошибка", None
    
    async def _generate_enhanced_fallback(self, prompt: str) -> Tuple[str, Optional[bytes]]:
        """Улучшенный fallback"""
        try:
            from PIL import Image, ImageDraw, ImageFont
            import io
            
            # Создаем изображение
            img = Image.new('RGB', (512, 512), color=(30, 30, 60))
            draw = ImageDraw.Draw(img)
            
            # Градиент
            for y in range(512):
                color = int(100 + 155 * (y / 512))
                draw.line([(0, y), (512, y)], fill=(30, 30, color))
            
            # Текст
            try:
                font = ImageFont.truetype("arial.ttf", 24)
            except:
                font = ImageFont.load_default()
            
            draw.text((256, 150), "✨ AI GENERATED IMAGE ✨", 
                     fill='white', font=font, anchor="mm")
            
            # Промпт
            short_prompt = prompt[:60] + "..." if len(prompt) > 60 else prompt
            draw.text((256, 220), short_prompt, 
                     fill=(200, 220, 255), font=font, anchor="mm")
            
            draw.text((256, 350), "Generated by AI Assistant", 
                     fill='lightgray', font=font, anchor="mm")
            
            # Сохраняем
            img_byte_arr = io.BytesIO()
            img.save(img_byte_arr, format='PNG')
            
            return "⚠️ Демо-режим генерации", img_byte_arr.getvalue()
            
        except ImportError:
            # Простой PNG если нет Pillow
            return "❌ Pillow не установлен", None
        except Exception as e:
            logger.error(f"❌ Ошибка fallback: {e}")
            return "❌ Ошибка", None


# Создаем глобальный экземпляр
ai_service = AIService()