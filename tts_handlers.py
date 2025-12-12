# handlers/tts_handlers.py
import os
import logging
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, FSInputFile, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from services.tts_service import tts_service
import tempfile

logger = logging.getLogger(__name__)
router = Router()


class TTSStates(StatesGroup):
    waiting_for_text = State()
    waiting_for_language = State()
    waiting_for_gender = State()


@router.message(Command("tts", "text_to_speech", "аудио", "озвучка"))
async def cmd_tts(message: Message, state: FSMContext):
    """Команда для преобразования текста в аудио"""
    keyboard = InlineKeyboardBuilder()
    keyboard.add(
        InlineKeyboardButton(text="🇷🇺 Русский", callback_data="tts_lang_ru"),
        InlineKeyboardButton(text="🇺🇸 English", callback_data="tts_lang_en"),
        InlineKeyboardButton(text="🇺🇦 Українська", callback_data="tts_lang_uk"),
        InlineKeyboardButton(text="🇩🇪 Deutsch", callback_data="tts_lang_de"),
        InlineKeyboardButton(text="🇫🇷 Français", callback_data="tts_lang_fr"),
        InlineKeyboardButton(text="🇪🇸 Español", callback_data="tts_lang_es"),
        InlineKeyboardButton(text="🇮🇹 Italiano", callback_data="tts_lang_it"),
    )
    keyboard.adjust(2)
    
    await message.answer(
        "🎤 <b>Преобразование текста в аудио</b>\n\n"
        "Выберите язык текста:",
        reply_markup=keyboard.as_markup()
    )
    await state.set_state(TTSStates.waiting_for_language)


@router.callback_query(F.data.startswith("tts_lang_"))
async def process_tts_language(callback_query, state: FSMContext):
    """Обработка выбора языка"""
    language = callback_query.data.replace("tts_lang_", "")
    
    await state.update_data(language=language)
    
    # Предлагаем выбрать пол голоса
    keyboard = InlineKeyboardBuilder()
    keyboard.add(
        InlineKeyboardButton(text="👩 Женский голос", callback_data="tts_gender_female"),
        InlineKeyboardButton(text="👨 Мужской голос", callback_data="tts_gender_male"),
    )
    
    language_names = {
        'ru': 'русский',
        'en': 'английский',
        'uk': 'украинский',
        'de': 'немецкий',
        'fr': 'французский',
        'es': 'испанский',
        'it': 'итальянский'
    }
    
    await callback_query.message.edit_text(
        f"🌍 Выбран язык: <b>{language_names.get(language, language)}</b>\n"
        "Выберите тип голоса:",
        reply_markup=keyboard.as_markup()
    )
    await state.set_state(TTSStates.waiting_for_gender)


@router.callback_query(F.data.startswith("tts_gender_"))
async def process_tts_gender(callback_query, state: FSMContext):
    """Обработка выбора пола голоса"""
    gender = callback_query.data.replace("tts_gender_", "")
    
    await state.update_data(gender=gender)
    
    await callback_query.message.edit_text(
        "✅ Отлично! Теперь отправьте текст для озвучки:\n\n"
        "• Максимум 4000 символов\n"
        "• Поддерживаются все основные языки\n"
        "• Я автоматически определю язык, если не угадаю\n"
        "• Бот отправит голосовое сообщение"
    )
    await state.set_state(TTSStates.waiting_for_text)


@router.message(TTSStates.waiting_for_text, F.text)
async def process_tts_text(message: Message, state: FSMContext):
    """Обработка текста для TTS"""
    text = message.text.strip()
    user_data = await state.get_data()
    
    if len(text) > 4000:
        await message.answer("❌ Текст слишком длинный (максимум 4000 символов)")
        await state.clear()
        return
    
    # Отправляем уведомление о начале обработки
    processing_msg = await message.answer("🔊 Преобразую текст в аудио...")
    
    try:
        # Получаем выбранные настройки
        language = user_data.get('language', 'ru')
        gender = user_data.get('gender', 'female')
        
        # Автоматически определяем язык, если есть сомнения
        detected_language = await tts_service.detect_language(text)
        
        # Если автоматически определенный язык отличается от выбранного,
        # уведомляем пользователя
        final_language = detected_language if detected_language != language else language
        
        # Конвертируем текст в аудио
        result_text, audio_bytes = await tts_service.text_to_speech(
            text, 
            language=final_language,
            gender=gender
        )
        
        if audio_bytes:
            # Сохраняем временно в файл
            with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as tmp:
                tmp.write(audio_bytes)
                tmp_path = tmp.name
            
            try:
                # Отправляем как голосовое сообщение
                voice = FSInputFile(tmp_path)
                
                # Создаем информационное сообщение
                caption = (
                    f"📝 <b>Текст ({len(text)} символов):</b>\n"
                    f"{text[:150]}..."
                    f"{'...' if len(text) > 150 else ''}\n\n"
                    f"🌍 <b>Язык:</b> {final_language.upper()}\n"
                    f"👤 <b>Голос:</b> {'женский' if gender == 'female' else 'мужской'}"
                )
                
                await message.answer_voice(voice, caption=caption, parse_mode='HTML')
                
                # Удаляем сообщение о обработке
                await processing_msg.delete()
                
            finally:
                # Удаляем временный файл
                if os.path.exists(tmp_path):
                    os.unlink(tmp_path)
        else:
            await message.answer(f"❌ {result_text}")
            
    except Exception as e:
        logger.error(f"❌ Ошибка TTS: {e}", exc_info=True)
        await message.answer(f"❌ Произошла ошибка: {str(e)[:200]}")
    
    await state.clear()


@router.message(Command("voices", "голоса", "voice_list"))
async def cmd_voices(message: Message):
    """Показать доступные голоса"""
    try:
        # Получаем список голосов
        voices = await tts_service.get_available_voices()
        
        if not voices:
            await message.answer("❌ Не удалось получить список голосов")
            return
        
        # Формируем сообщение
        response = "🎤 <b>Доступные голоса:</b>\n\n"
        
        # Группируем по языкам
        voices_by_lang = {}
        for voice in voices:
            lang = voice['locale'][:2]  # Первые 2 символа кода языка
            if lang not in voices_by_lang:
                voices_by_lang[lang] = []
            voices_by_lang[lang].append(voice)
        
        # Показываем по 2 голоса на язык
        for lang_code, lang_voices in voices_by_lang.items():
            lang_name = {
                'ru': '🇷🇺 Русский',
                'en': '🇺🇸 Английский',
                'uk': '🇺🇦 Украинский',
                'de': '🇩🇪 Немецкий',
                'fr': '🇫🇷 Французский',
                'es': '🇪🇸 Испанский',
                'it': '🇮🇹 Итальянский',
            }.get(lang_code, lang_code)
            
            response += f"<b>{lang_name}:</b>\n"
            for voice in lang_voices[:2]:  # По 2 голоса на язык
                gender = "👩" if voice['gender'] == 'Female' else "👨"
                response += f"  {gender} {voice['friendly_name']}\n"
            response += "\n"
        
        await message.answer(response, parse_mode='HTML')
        
    except Exception as e:
        logger.error(f"❌ Ошибка получения голосов: {e}")
        await message.answer(f"❌ Не удалось получить список голосов: {str(e)[:200]}")


@router.message(Command("tts_direct", "озвучить"))
async def cmd_tts_direct(message: Message):
    """Прямая озвучка текста (без выбора настроек)"""
    text = message.text.replace('/tts_direct', '').replace('/озвучить', '').strip()
    
    if not text:
        await message.answer(
            "🎤 Использование:\n"
            "/tts_direct [текст] - озвучить текст\n\n"
            "Пример:\n"
            "/tts_direct Привет! Как дела?"
        )
        return
    
    if len(text) > 4000:
        await message.answer("❌ Текст слишком длинный (максимум 4000 символов)")
        return
    
    processing_msg = await message.answer("🔊 Озвучиваю...")
    
    try:
        # Автоматически определяем язык и генерируем аудио
        result_text, audio_bytes = await tts_service.text_to_speech(text)
        
        if audio_bytes:
            with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as tmp:
                tmp.write(audio_bytes)
                tmp_path = tmp.name
            
            try:
                voice = FSInputFile(tmp_path)
                await message.answer_voice(
                    voice, 
                    caption=f"📝 Текст ({len(text)} символов): {text[:100]}..."
                )
                await processing_msg.delete()
            finally:
                if os.path.exists(tmp_path):
                    os.unlink(tmp_path)
        else:
            await message.answer(f"❌ {result_text}")
            
    except Exception as e:
        logger.error(f"❌ Ошибка прямой озвучки: {e}")
        await message.answer(f"❌ Ошибка: {str(e)[:200]}")


# Отмена операции
@router.message(Command("cancel", "отмена"))
async def cmd_cancel(message: Message, state: FSMContext):
    """Отмена текущей операции"""
    current_state = await state.get_state()
    if current_state is None:
        return
    
    await state.clear()
    await message.answer("✅ Операция отменена")


# Если пользователь отправляет что-то не то в состоянии ожидания текста
@router.message(TTSStates.waiting_for_text)
async def process_wrong_input(message: Message):
    """Обработка неправильного ввода"""
    await message.answer("❌ Пожалуйста, отправьте текст для озвучки")