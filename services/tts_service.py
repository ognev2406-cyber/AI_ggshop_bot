# services/tts_service.py
import os
import logging
import asyncio
import edge_tts
from typing import Optional, Tuple
import tempfile
import uuid

logger = logging.getLogger(__name__)


class TextToSpeechService:
    def __init__(self):
        self.temp_dir = "temp_audio"
        os.makedirs(self.temp_dir, exist_ok=True)
        
        # Голоса по языкам
        self.voices = {
            'ru': 'ru-RU-SvetlanaNeural',
            'en': 'en-US-JennyNeural',
            'uk': 'uk-UA-PolinaNeural',
        }
        
        self.default_voice = 'ru-RU-SvetlanaNeural'
    
    async def text_to_speech(self, text: str, language: str = 'ru') -> Tuple[str, Optional[bytes]]:
        """Преобразует текст в аудио"""
        try:
            if not text or len(text.strip()) == 0:
                return "❌ Текст пустой", None
            
            # Ограничиваем длину
            if len(text) > 3000:
                text = text[:3000]
            
            logger.info(f"🔊 Конвертация текста в аудио ({len(text)} символов)...")
            
            # Выбираем голос
            voice = self.voices.get(language, self.default_voice)
            
            # Создаем временный файл
            with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as tmp:
                temp_file = tmp.name
            
            try:
                # Генерируем аудио
                communicate = edge_tts.Communicate(text=text, voice=voice)
                await communicate.save(temp_file)
                
                # Читаем файл
                with open(temp_file, 'rb') as f:
                    audio_bytes = f.read()
                
                logger.info(f"✅ Аудио создано: {len(audio_bytes)} байт")
                return "✅ Аудио успешно создано", audio_bytes
                
            finally:
                if os.path.exists(temp_file):
                    os.unlink(temp_file)
            
        except Exception as e:
            logger.error(f"❌ Ошибка TTS: {e}", exc_info=True)
            return f"❌ Ошибка: {str(e)[:100]}", None
    
    def detect_language(self, text: str) -> str:
        """Простое определение языка"""
        import re
        if re.search('[а-яА-Я]', text):
            return 'ru'
        elif re.search('[a-zA-Z]', text):
            return 'en'
        else:
            return 'ru'


# Глобальный экземпляр
tts_service = TextToSpeechService()
