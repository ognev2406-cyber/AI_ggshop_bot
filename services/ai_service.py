# services/ai_service.py
import aiohttp
import base64
import logging
import json
import asyncio
import random
import re
import urllib.parse
from config import OLLAMA_BASE_URL, OLLAMA_MODEL, COLAB_ENABLED, COLAB_API_URL
from typing import Optional, Tuple

logger = logging.getLogger(__name__)


class AIService:
    def __init__(self):
        # Настройки для Ollama
        self.base_url = OLLAMA_BASE_URL or "http://localhost:11434"
        self.model = OLLAMA_MODEL or "llama2"
        self.timeout = aiohttp.ClientTimeout(total=300)
        
        # Настройки для генерации изображений
        self.hf_api_token = None
        self.hf_api_url = "https://api-inference.huggingface.co/models/stabilityai/stable-diffusion-xl-base-1.0"
        self.headers = {
            "Authorization": f"Bearer {self.hf_api_token}" if self.hf_api_token else None,
            "Content-Type": "application/json"
        }
        
        # Переводчик для русских промптов
        self.translator = None
        self._init_translator()
    
    def _init_translator(self):
        """Инициализация переводчика"""
        try:
            from googletrans import Translator
            self.translator = Translator()
            logger.info("✅ Переводчик Google инициализирован")
        except ImportError:
            logger.warning("⚠️ googletrans не установлен. Установите: pip install googletrans==4.0.0-rc1")
        except Exception as e:
            logger.error(f"❌ Ошибка инициализации переводчика: {e}")
    
    async def translate_to_english(self, text: str) -> str:
        """Переводит русский текст на английский"""
        # Если нет русских букв - возвращаем как есть
        if not re.search('[а-яА-Я]', text):
            return text
        
        try:
            # Сначала пробуем через googletrans
            if self.translator:
                result = self.translator.translate(text, src='ru', dest='en')
                if result and result.text:
                    logger.info(f"🌐 Переводчик: '{text[:50]}...' → '{result.text[:50]}...'")
                    return result.text
            
            # Если переводчик не работает, используем словарь
            return await self._translate_with_dictionary(text)
            
        except Exception as e:
            logger.warning(f"⚠️ Ошибка перевода: {e}")
            # В крайнем случае - простой словарь
            return await self._translate_with_dictionary(text)
    
    async def _translate_with_dictionary(self, text: str) -> str:
        """Перевод с помощью словаря"""
        # Расширенный словарь переводов
        dictionary = {
            # Транспорт
            "машина": "car, vehicle, automobile",
            "автомобиль": "car, automobile, vehicle",
            "тачка": "car, vehicle",
            "авто": "car, auto",
            "мерседес": "mercedes, car",
            "бмв": "bmw, car",
            "ауди": "audi, car",
            "трактор": "tractor",
            "грузовик": "truck",
            "мотоцикл": "motorcycle, bike",
            "велосипед": "bicycle, bike",
            "самолет": "airplane, aircraft",
            "вертолет": "helicopter",
            "корабль": "ship, boat",
            "лодка": "boat",
            "поезд": "train",
            
            # Животные
            "кошка": "cat, kitten",
            "кот": "cat, tomcat",
            "котенок": "kitten, baby cat",
            "собака": "dog, puppy",
            "щенок": "puppy, baby dog",
            "хомяк": "hamster",
            "крыса": "rat",
            "мышь": "mouse",
            "птица": "bird",
            "попугай": "parrot",
            "ворона": "crow",
            "голубь": "pigeon",
            "рыба": "fish",
            "аквариум": "aquarium",
            "змея": "snake",
            "черепаха": "turtle",
            "ящерица": "lizard",
            "динозавр": "dinosaur",
            "дракон": "dragon",
            "единорог": "unicorn",
            
            # Люди
            "человек": "person, human",
            "мужчина": "man, male",
            "женщина": "woman, female",
            "девушка": "girl, young woman",
            "парень": "guy, young man",
            "мальчик": "boy",
            "девочка": "girl",
            "ребенок": "child, kid",
            "дети": "children, kids",
            "старик": "old man",
            "старуха": "old woman",
            "семья": "family",
            
            # Части тела
            "лицо": "face",
            "глаз": "eye",
            "нос": "nose",
            "рот": "mouth",
            "ухо": "ear",
            "рука": "hand, arm",
            "нога": "leg, foot",
            "голова": "head",
            "волосы": "hair",
            "тело": "body",
            
            # Еда
            "яблоко": "apple",
            "банан": "banana",
            "апельсин": "orange",
            "пицца": "pizza",
            "бургер": "burger",
            "торт": "cake",
            "мороженое": "ice cream",
            "кофе": "coffee",
            "чай": "tea",
            "сок": "juice",
            
            # Природа
            "дерево": "tree",
            "цветок": "flower",
            "трава": "grass",
            "лист": "leaf",
            "лес": "forest, woods",
            "поле": "field",
            "сад": "garden",
            "парк": "park",
            "река": "river",
            "озеро": "lake",
            "море": "sea, ocean",
            "пляж": "beach",
            "гора": "mountain",
            "скала": "rock, cliff",
            "пещера": "cave",
            "водопад": "waterfall",
            "пустыня": "desert",
            "остров": "island",
            
            # Погода
            "солнце": "sun",
            "луна": "moon",
            "звезда": "star",
            "облако": "cloud",
            "дождь": "rain",
            "снег": "snow",
            "град": "hail",
            "ветер": "wind",
            "буря": "storm",
            "гроза": "thunderstorm",
            "радуга": "rainbow",
            "туман": "fog",
            
            # Здания
            "дом": "house, home",
            "здание": "building",
            "небоскреб": "skyscraper",
            "замок": "castle",
            "дворец": "palace",
            "церковь": "church",
            "храм": "temple",
            "мечеть": "mosque",
            "больница": "hospital",
            "школа": "school",
            "университет": "university",
            "офис": "office",
            "магазин": "shop, store",
            "рынок": "market",
            "ресторан": "restaurant",
            "кафе": "cafe",
            "бар": "bar",
            "клуб": "club",
            
            # Город
            "город": "city, town",
            "деревня": "village",
            "улица": "street",
            "дорога": "road",
            "шоссе": "highway",
            "мост": "bridge",
            "тоннель": "tunnel",
            "площадь": "square",
            "фонтан": "fountain",
            "памятник": "monument",
            "статуя": "statue",
            
            # Космос
            "космос": "space",
            "планета": "planet",
            "марс": "mars",
            "земля": "earth",
            "луна": "moon",
            "солнце": "sun",
            "галактика": "galaxy",
            "комета": "comet",
            "астероид": "asteroid",
            "ракета": "rocket",
            "спутник": "satellite",
            "космонавт": "astronaut",
            "инопланетянин": "alien",
            
            # Техника
            "компьютер": "computer",
            "ноутбук": "laptop",
            "телефон": "phone",
            "смартфон": "smartphone",
            "телевизор": "television, tv",
            "камера": "camera",
            "фотоаппарат": "camera",
            "часы": "clock, watch",
            "робот": "robot",
            "андроид": "android",
            
            # Фантастика
            "дракон": "dragon",
            "единорог": "unicorn",
            "фея": "fairy",
            "волшебник": "wizard",
            "маг": "mage",
            "колдун": "sorcerer",
            "ведьма": "witch",
            "вампир": "vampire",
            "оборотень": "werewolf",
            "зомби": "zombie",
            "призрак": "ghost",
            "монстр": "monster",
            "гигант": "giant",
            "гоблин": "goblin",
            "орк": "orc",
            "эльф": "elf",
            "гном": "gnome, dwarf",
            
            # Цвета
            "красный": "red",
            "синий": "blue",
            "зеленый": "green",
            "желтый": "yellow",
            "оранжевый": "orange",
            "фиолетовый": "purple, violet",
            "розовый": "pink",
            "коричневый": "brown",
            "черный": "black",
            "белый": "white",
            "серый": "gray",
            "золотой": "gold",
            "серебряный": "silver",
            
            # Прилагательные
            "большой": "big, large",
            "маленький": "small, little",
            "высокий": "tall, high",
            "низкий": "low, short",
            "длинный": "long",
            "короткий": "short",
            "широкий": "wide",
            "узкий": "narrow",
            "тяжелый": "heavy",
            "легкий": "light",
            "быстрый": "fast, quick",
            "медленный": "slow",
            "горячий": "hot",
            "холодный": "cold",
            "теплый": "warm",
            "прохладный": "cool",
            "мягкий": "soft",
            "твердый": "hard",
            "гладкий": "smooth",
            "шершавый": "rough",
            "мокрый": "wet",
            "сухой": "dry",
            "чистый": "clean",
            "грязный": "dirty",
            "новый": "new",
            "старый": "old",
            "молодой": "young",
            "красивый": "beautiful, pretty",
            "уродливый": "ugly",
            "страшный": "scary, frightening",
            "милый": "cute, sweet",
            "добрый": "kind",
            "злой": "evil",
            "умный": "smart, intelligent",
            "глупый": "stupid",
            "сильный": "strong",
            "слабый": "weak",
            "богатый": "rich",
            "бедный": "poor",
            
            # Действия
            "бежит": "running",
            "ходит": "walking",
            "прыгает": "jumping",
            "летает": "flying",
            "плавает": "swimming",
            "сидит": "sitting",
            "стоит": "standing",
            "лежит": "lying",
            "спит": "sleeping",
            "ест": "eating",
            "пьет": "drinking",
            "работает": "working",
            "играет": "playing",
            "танцует": "dancing",
            "поет": "singing",
            "рисует": "drawing",
            "пишет": "writing",
            "читает": "reading",
            "смотрит": "watching",
            "слушает": "listening",
        }
        
        words = text.lower().split()
        translated_words = []
        
        for word in words:
            # Очищаем слово от знаков препинания
            clean_word = re.sub(r'[^\w\s]', '', word)
            
            if clean_word in dictionary:
                translated_words.append(dictionary[clean_word])
            else:
                # Если слова нет в словаре, оставляем как есть
                translated_words.append(clean_word)
        
        result = ', '.join(translated_words[:8])  # Ограничиваем количество слов
        
        # Добавляем улучшающие теги
        quality_tags = ["high quality", "detailed", "4k", "realistic", "professional photography"]
        import random
        result += f", {random.choice(quality_tags)}"
        
        logger.info(f"📚 Словарный перевод: '{text}' → '{result}'")
        return result
    
    async def check_api_access(self) -> bool:
        """Проверяет доступность Ollama API"""
        try:
            logger.info(f"🔍 Проверка доступности Ollama по адресу: {self.base_url}")
            
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.get(f"{self.base_url}/api/tags") as response:
                    if response.status == 200:
                        logger.info("✅ Ollama API доступен")
                        
                        # Проверяем, доступна ли нужная модель
                        try:
                            result = await response.json()
                            models = result.get("models", [])
                            model_names = [model.get("name", "") for model in models]
                            
                            logger.info(f"📋 Доступные модели: {model_names}")
                            
                            # Проверяем наличие нашей модели
                            for model_info in models:
                                if self.model in model_info.get("name", ""):
                                    logger.info(f"✅ Модель '{self.model}' найдена")
                                    return True
                            
                            # Если точное совпадение не найдено, ищем частичное
                            for model_name in model_names:
                                if self.model.split(':')[0] in model_name:
                                    logger.info(f"✅ Найдена похожая модель: '{model_name}'")
                                    self.model = model_name
                                    return True
                            
                            logger.warning(f"⚠️ Модель '{self.model}' не найдена. Используйте одну из: {model_names}")
                            return False
                            
                        except Exception as e:
                            logger.error(f"❌ Ошибка парсинга ответа Ollama: {e}")
                            return False
                    else:
                        logger.warning(f"⚠️ Ollama недоступен, статус: {response.status}")
                        return False
                        
        except aiohttp.ClientConnectorError:
            logger.warning("⚠️ Не удалось подключиться к Ollama. Убедитесь, что Ollama запущен.")
            return False
        except asyncio.TimeoutError:
            logger.warning("⚠️ Таймаут при подключении к Ollama")
            return False
        except Exception as e:
            logger.error(f"❌ Неизвестная ошибка при проверке Ollama: {e}")
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
            
            logger.info(f"🧠 Отправка запроса в Ollama: {prompt[:100]}...")
            
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.post(url, json=payload) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"❌ Ошибка Ollama API: {response.status} - {error_text}")
                        return f"❌ Ошибка API: {response.status}"
                    
                    result = await response.json()
                    
                    if "response" not in result:
                        logger.error(f"❌ Неожиданный ответ от Ollama: {result}")
                        return "❌ Ошибка: неверный формат ответа"
                    
                    generated_text = result["response"].strip()
                    
                    logger.info(f"✅ Текст сгенерирован, длина: {len(generated_text)} символов")
                    return generated_text
                    
        except aiohttp.ClientError as e:
            logger.error(f"❌ Сетевая ошибка при генерации текста: {e}")
            return f"❌ Сетевая ошибка: {str(e)}"
        except Exception as e:
            logger.error(f"❌ Неизвестная ошибка при генерации текста: {e}")
            return f"❌ Внутренняя ошибка: {str(e)}"
    
    async def generate_image(self, prompt: str):
        """Генерация изображения - РАБОЧАЯ ВЕРСИЯ С АВТОПЕРЕВОДОМ"""
        try:
            logger.info(f"🖼️ Генерация изображения: {prompt[:50]}...")
            
            # 1. АВТОМАТИЧЕСКИЙ ПЕРЕВОД НА АНГЛИЙСКИЙ
            english_prompt = await self.translate_to_english(prompt)
            logger.info(f"🌐 Переведено на английский: '{english_prompt}'")
            
            # 2. Генерация через Pollinations.ai (основной метод)
            encoded_prompt = urllib.parse.quote(english_prompt[:150])
            
            # Пробуем разные параметры Pollinations
            endpoints = [
                f"https://image.pollinations.ai/prompt/{encoded_prompt}",
                f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=512&height=512",
                f"https://image.pollinations.ai/prompt/{encoded_prompt}?model=flux&width=512&seed={random.randint(1, 999999)}",
                f"https://pollinations.ai/p/{encoded_prompt}",
            ]
            
            timeout = aiohttp.ClientTimeout(total=30)
            
            for endpoint in endpoints:
                try:
                    logger.info(f"🌐 Пробуем эндпоинт: {endpoint[:80]}...")
                    
                    headers = {
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                        'Accept': 'image/*'
                    }
                    
                    async with aiohttp.ClientSession(timeout=timeout) as session:
                        async with session.get(endpoint, headers=headers) as response:
                            logger.info(f"📥 Статус: {response.status}")
                            
                            if response.status == 200:
                                content_type = response.headers.get('Content-Type', '').lower()
                                
                                if 'image' in content_type:
                                    image_bytes = await response.read()
                                    
                                    if len(image_bytes) > 10000:  # Минимум 10KB для реального изображения
                                        logger.info(f"✅ Успех! Изображение: {len(image_bytes)} байт")
                                        
                                        # Формируем информационное сообщение
                                        message = f"✅ Изображение успешно сгенерировано!\n"
                                        if english_prompt != prompt:
                                            message += f"🌐 Запрос переведен: '{prompt}' → '{english_prompt}'"
                                        
                                        return message, image_bytes
                                    else:
                                        logger.warning(f"⚠️ Слишком маленькое изображение: {len(image_bytes)} байт")
                                
                except asyncio.TimeoutError:
                    logger.warning(f"⏱️ Таймаут для эндпоинта")
                    continue
                except Exception as e:
                    logger.warning(f"⚠️ Ошибка для эндпоинта: {e}")
                    continue
            
            # 3. Если Pollinations не сработал, пробуем прямой API
            logger.warning("🔄 Pollinations не сработал, пробуем прямой запрос...")
            
            direct_url = f"https://pollinations.ai/p/{encoded_prompt}"
            async with aiohttp.ClientSession() as session:
                async with session.get(direct_url) as response:
                    if response.status == 200:
                        image_bytes = await response.read()
                        if len(image_bytes) > 10000:
                            message = f"✅ Изображение сгенерировано (Pollinations)\n"
                            if english_prompt != prompt:
                                message += f"🌐 Использован промпт: {english_prompt}"
                            return message, image_bytes
            
            # 4. Если все не сработало - создаем демо-изображение
            logger.info("🎨 Создаем демо-изображение...")
            
            try:
                from PIL import Image, ImageDraw, ImageFont
                import io
                
                # Создаем простое изображение
                img = Image.new('RGB', (512, 512), color=(40, 40, 80))
                draw = ImageDraw.Draw(img)
                
                # Пробуем использовать шрифт
                try:
                    font = ImageFont.truetype("arial.ttf", 20)
                except:
                    font = ImageFont.load_default()
                
                # Добавляем текст
                draw.text((50, 200), f"Запрос: {prompt[:30]}", fill='white', font=font)
                draw.text((50, 230), f"Перевод: {english_prompt[:40]}", fill='lightblue', font=font)
                draw.text((50, 260), "Сервис генерации временно недоступен", fill='yellow', font=font)
                draw.text((50, 290), "Попробуйте позже или другой запрос", fill='lightgreen', font=font)
                
                # Сохраняем в bytes
                img_byte_arr = io.BytesIO()
                img.save(img_byte_arr, format='PNG')
                image_bytes = img_byte_arr.getvalue()
                
                return "⚠️ Демо-режим (основной сервис недоступен)", image_bytes
                
            except ImportError:
                logger.error("❌ Pillow не установлен")
                # Простой черный PNG
                black_png = base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==')
                return "⚠️ Pillow не установлен", black_png
            
        except Exception as e:
            logger.error(f"❌ Критическая ошибка в generate_image: {e}", exc_info=True)
            return f"❌ Внутренняя ошибка: {str(e)[:100]}", None
    
    # Остальные методы остаются без изменений
    async def _generate_via_colab(self, prompt: str) -> Tuple[str, Optional[bytes]]:
        """Генерация через ваш Colab сервер"""
        try:
            url = f"{COLAB_API_URL}/generate"
            params = {"prompt": prompt}
            
            logger.info(f"🖥️ Пробуем Colab сервер: {prompt[:100]}...")
            
            timeout = aiohttp.ClientTimeout(total=60)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        content_type = response.headers.get('Content-Type', '')
                        
                        if 'image' in content_type:
                            image_bytes = await response.read()
                            logger.info(f"✅ Изображение получено с Colab, размер: {len(image_bytes)} байт")
                            return "✅ Изображение успешно сгенерировано", image_bytes
                        else:
                            error_text = await response.text()
                            logger.error(f"❌ Colab вернул не изображение: {error_text[:200]}")
                            return "❌ Ошибка сервера", None
                    else:
                        error_text = await response.text()
                        logger.error(f"❌ Ошибка Colab {response.status}: {error_text[:200]}")
                        return f"❌ Ошибка сервера: {response.status}", None
        except Exception as e:
            logger.error(f"❌ Ошибка при генерации через Colab: {e}")
            return f"❌ Ошибка Colab", None
    
    async def _generate_via_simple_api(self, prompt: str) -> Tuple[str, Optional[bytes]]:
        """Простой рабочий API для генерации изображений"""
        try:
            encoded_prompt = urllib.parse.quote(prompt[:150])
            endpoint = f"https://image.pollinations.ai/prompt/{encoded_prompt}"
            
            logger.info(f"🌐 Тестируем pollinations.ai: {prompt[:50]}...")
            
            timeout = aiohttp.ClientTimeout(total=30)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                headers = {'User-Agent': 'Mozilla/5.0'}
                async with session.get(endpoint, headers=headers) as response:
                    if response.status == 200:
                        content_type = response.headers.get('Content-Type', '').lower()
                        if 'image' in content_type:
                            image_bytes = await response.read()
                            if len(image_bytes) > 5000:
                                return "✅ Изображение успешно сгенерировано", image_bytes
            
            return "❌ pollinations.ai недоступен", None
            
        except Exception as e:
            logger.error(f"❌ Ошибка simple API: {e}")
            return f"❌ Ошибка", None
    
    async def _generate_via_prodia(self, prompt: str) -> Tuple[str, Optional[bytes]]:
        """Генерация через Prodia API (бесплатный)"""
        try:
            logger.info(f"🎨 Пробуем Prodia API: {prompt[:50]}...")
            
            url = "https://api.prodia.com/generate"
            payload = {
                "prompt": prompt,
                "model": "dreamshaper_8.safetensors",
                "negative_prompt": "",
                "steps": 25,
                "cfg_scale": 7,
                "seed": -1,
                "upscale": False
            }
            
            headers = {"Content-Type": "application/json"}
            timeout = aiohttp.ClientTimeout(total=60)
            
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(url, json=payload, headers=headers) as response:
                    if response.status == 200:
                        result = await response.json()
                        if "job" in result:
                            job_id = result["job"]
                            check_url = f"https://api.prodia.com/job/{job_id}"
                            
                            for attempt in range(30):
                                await asyncio.sleep(1)
                                async with session.get(check_url) as check_response:
                                    if check_response.status == 200:
                                        job_info = await check_response.json()
                                        if job_info.get("status") == "succeeded":
                                            image_url = job_info.get("imageUrl")
                                            if image_url:
                                                async with session.get(image_url) as img_response:
                                                    if img_response.status == 200:
                                                        image_bytes = await img_response.read()
                                                        return "✅ Изображение сгенерировано (Prodia)", image_bytes
                                        elif job_info.get("status") == "failed":
                                            break
            
            return "❌ Prodia API временно недоступен", None
            
        except Exception as e:
            logger.error(f"❌ Ошибка Prodia API: {e}")
            return f"❌ Ошибка Prodia", None
    
    async def _generate_via_huggingface(self, prompt: str) -> Tuple[str, Optional[bytes]]:
        """Генерация через Hugging Face API"""
        try:
            api_url = "https://api-inference.huggingface.co/models/stabilityai/stable-diffusion-2-1"
            payload = {"inputs": prompt[:200]}
            
            logger.info(f"🤗 Пробуем Hugging Face: {prompt[:50]}...")
            
            timeout = aiohttp.ClientTimeout(total=90)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(api_url, json=payload) as response:
                    if response.status == 200:
                        content_type = response.headers.get('Content-Type', '')
                        if 'image' in content_type:
                            image_bytes = await response.read()
                            if len(image_bytes) > 1000:
                                return "✅ Изображение сгенерировано (Hugging Face)", image_bytes
            
            return "❌ Hugging Face недоступен", None
                    
        except Exception as e:
            logger.error(f"❌ Ошибка Hugging Face: {e}")
            return f"❌ Ошибка HF", None
    
    async def _generate_enhanced_fallback(self, prompt: str) -> Tuple[str, Optional[bytes]]:
        """Улучшенный fallback с красивым изображением"""
        try:
            from PIL import Image, ImageDraw, ImageFont
            import io
            
            width, height = 512, 512
            img = Image.new('RGB', (width, height), color='black')
            draw = ImageDraw.Draw(img)
            
            # Градиент
            for y in range(height):
                r = 0
                g = int(50 * (y / height))
                b = int(150 + 100 * (y / height))
                draw.line([(0, y), (width, y)], fill=(r, g, b))
            
            # Текст
            try:
                font = ImageFont.truetype("arial.ttf", 20)
            except:
                font = ImageFont.load_default()
            
            draw.text((width//2, 100), "✨ AI GENERATED IMAGE ✨", 
                     fill='white', font=font, anchor="mm")
            draw.text((width//2, 200), f'"{prompt[:80]}"', 
                     fill=(200, 230, 255), font=font, anchor="mm")
            draw.text((width//2, 300), "Generated by AI Assistant", 
                     fill='lightgray', font=font, anchor="mm")
            draw.text((width//2, 350), "Попробуйте позже для реальной генерации", 
                     fill='yellow', font=font, anchor="mm")
            
            img_byte_arr = io.BytesIO()
            img.save(img_byte_arr, format='PNG')
            img_bytes = img_byte_arr.getvalue()
            
            return "⚠️ Демо-режим: настоящее изображение временно недоступно", img_bytes
                
        except Exception as e:
            logger.error(f"❌ Ошибка улучшенного fallback: {e}")
            return "❌ Ошибка генерации", None

# Глобальный экземпляр
ai_service = AIService()