# handlers/audio_handlers.py - обновленный обработчик
import os
import logging
import asyncio
import tempfile
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, FSInputFile, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from config import PRICE_CONFIG
from keyboards import get_cancel_inline_button, get_main_inline_menu

# Импортируем TTS сервис и необходимые модели
from services.tts_service import tts_service
from database import Order

logger = logging.getLogger(__name__)
router = Router()


class TTSStates(StatesGroup):
    waiting_for_text = State()


def calculate_tts_cost(text: str) -> int:
    """Рассчитать стоимость TTS на основе длины текста"""
    length = len(text)
    if length <= 500:
        return PRICE_CONFIG.get('audio_short', 5)
    else:
        return PRICE_CONFIG.get('audio_long', 10)


@router.callback_query(F.data == "tts_generation")
async def handle_tts_callback(callback: CallbackQuery, state: FSMContext, user, session):
    """Обработчик нажатия на inline-кнопку 'Текст в аудио' с проверкой баланса"""
    await callback.answer()
    
    # Проверяем баланс пользователя
    if user.balance < 5:  # Минимальная стоимость
        await callback.message.edit_text(
            "❌ <b>Недостаточно средств!</b>\n\n"
            f"Ваш баланс: {user.balance:.2f}₽\n"
            f"Минимальная стоимость озвучки: 5₽\n\n"
            "Пополните баланс через раздел '💰 Мой баланс'",
            parse_mode='HTML',
            reply_markup=get_main_inline_menu(user.is_admin)
        )
        await state.clear()
        return
    
    await callback.message.edit_text(
        "🎤 <b>Текст в аудио</b>\n\n"
        f"💳 <b>Стоимость:</b>\n"
        f"• До 500 символов: {PRICE_CONFIG.get('audio_short', 5)}₽\n"
        f"• Более 500 символов: {PRICE_CONFIG.get('audio_long', 10)}₽\n\n"
        f"💰 <b>Ваш баланс:</b> {user.balance:.2f}₽\n\n"
        "Отправьте текст для преобразования в голосовое сообщение:\n\n"
        "• До 3000 символов\n"
        "• Поддерживает русский и английский\n"
        "• Автоматически определяет язык",
        parse_mode='HTML',
        reply_markup=get_cancel_inline_button()
    )
    
    await state.set_state(TTSStates.waiting_for_text)
    logger.info(f"📝 Пользователь {user.telegram_id} начал TTS, баланс: {user.balance}")


@router.message(TTSStates.waiting_for_text, F.text)
async def process_tts_text(message: Message, state: FSMContext, user, session):
    """Обработка текста для преобразования в аудио с оплатой"""
    text = message.text.strip()
    
    # Проверки текста
    if len(text) == 0:
        await message.answer("❌ Текст пустой. Попробуйте снова.")
        await state.clear()
        return
    
    if len(text) > 3000:
        await message.answer("❌ Текст слишком длинный (максимум 3000 символов)")
        await state.clear()
        return
    
    # Рассчитываем стоимость
    cost = calculate_tts_cost(text)
    
    # Проверяем баланс
    if user.balance < cost:
        await message.answer(
            f"❌ <b>Недостаточно средств!</b>\n\n"
            f"💰 Ваш баланс: {user.balance:.2f}₽\n"
            f"💳 Требуется: {cost}₽\n"
            f"📝 Длина текста: {len(text)} символов\n\n"
            "Пополните баланс и попробуйте снова.",
            parse_mode='HTML'
        )
        await state.clear()
        return
    
    # Уведомление о начале обработки
    processing_msg = await message.answer(f"🔊 Преобразую текст в аудио... Списание: {cost}₽")
    
    try:
        # Определяем язык текста
        language = tts_service.detect_language(text)
        language_name = "русский" if language == 'ru' else "английский"
        
        # Создаем аудио
        result_text, audio_bytes = await tts_service.text_to_speech(text, language)
        
        if audio_bytes:
            # Списание средств
            user.balance -= cost
            
            # Сохраняем заказ в базу данных
            order = Order(
                user_id=user.id,
                product_type="audio",
                product_subtype="tts",
                prompt=text[:1000],  # Сохраняем промпт
                result=f"Аудио файл ({len(audio_bytes)} байт)",  # Или можно сохранить путь к файлу
                cost=cost
            )
            session.add(order)
            await session.commit()
            
            logger.info(f"💰 Списано {cost}₽ за TTS для пользователя {user.telegram_id}, баланс: {user.balance}")
            
            # Сохраняем временно в файл
            with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as tmp:
                tmp.write(audio_bytes)
                tmp_path = tmp.name
            
            try:
                # Отправляем голосовое сообщение
                voice = FSInputFile(tmp_path)
                
                # Создаем информационную подпись
                short_text = text[:100] + "..." if len(text) > 100 else text
                caption = (
                    f"✅ <b>Текст успешно озвучен!</b>\n\n"
                    f"📝 <b>Текст ({len(text)} символов):</b>\n"
                    f"{short_text}\n\n"
                    f"💳 <b>Стоимость:</b> {cost}₽\n"
                    f"💰 <b>Баланс:</b> {user.balance:.2f}₽\n"
                    f"🌍 <b>Язык:</b> {language_name}\n"
                    f"🎵 <b>Формат:</b> MP3"
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
        logger.error(f"❌ Ошибка при преобразовании текста в аудио: {e}")
        await message.answer(f"❌ Произошла ошибка: {str(e)[:200]}")
    
    await state.clear()


# Команда для прямого использования с оплатой
@router.message(Command("tts", "озвучка", "аудио"))
async def cmd_tts(message: Message, state: FSMContext, user, session):
    """Команда для быстрого преобразования текста в аудио с оплатой"""
    # Проверяем баланс
    if user.balance < 5:
        await message.answer(
            "❌ <b>Недостаточно средств!</b>\n\n"
            f"Ваш баланс: {user.balance:.2f}₽\n"
            "Пополните баланс через раздел '💰 Мой баланс'",
            parse_mode='HTML'
        )
        return
    
    # Если есть текст после команды
    if len(message.text.split()) > 1:
        text = ' '.join(message.text.split()[1:])
        
        # Проверки текста
        if len(text) > 3000:
            await message.answer("❌ Текст слишком длинный (максимум 3000 символов)")
            return
        
        # Рассчитываем стоимость
        cost = calculate_tts_cost(text)
        
        if user.balance < cost:
            await message.answer(f"❌ Недостаточно средств. Требуется: {cost}₽, ваш баланс: {user.balance:.2f}₽")
            return
        
        processing_msg = await message.answer(f"🔊 Озвучка... Списание: {cost}₽")
        
        try:
            language = tts_service.detect_language(text)
            result_text, audio_bytes = await tts_service.text_to_speech(text, language)
            
            if audio_bytes:
                # Списание средств
                user.balance -= cost
                
                # Сохраняем заказ
                order = Order(
                    user_id=user.id,
                    product_type="audio",
                    product_subtype="tts",
                    prompt=text[:1000],
                    result=f"Аудио файл ({len(audio_bytes)} байт)",
                    cost=cost
                )
                session.add(order)
                await session.commit()
                
                with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as tmp:
                    tmp.write(audio_bytes)
                    tmp_path = tmp.name
                
                try:
                    voice = FSInputFile(tmp_path)
                    caption = (
                        f"✅ <b>Озвучка готова!</b>\n\n"
                        f"💳 Списано: {cost}₽\n"
                        f"💰 Баланс: {user.balance:.2f}₽\n"
                        f"📝 Текст: {text[:100]}..."
                    )
                    
                    await message.answer_voice(voice, caption=caption, parse_mode='HTML')
                    await processing_msg.delete()
                finally:
                    if os.path.exists(tmp_path):
                        os.unlink(tmp_path)
            else:
                await message.answer(f"❌ {result_text}")
                
        except Exception as e:
            logger.error(f"❌ Ошибка TTS: {e}")
            await message.answer(f"❌ Ошибка: {str(e)[:200]}")
    else:
        # Если только команда - показываем инструкцию
        await handle_tts_callback(
            CallbackQuery(
                id="cmd",
                from_user=message.from_user,
                chat_instance="cmd",
                message=message
            ),
            state,
            user,
            session
        )
# handlers/audio_handlers.py - добавьте в КОНЕЦ файла:

@router.callback_query(F.data == "cancel_operation")
async def handle_cancel_callback(callback: CallbackQuery, state: FSMContext):
    """Обработка кнопки 'Отмена' для TTS"""
    try:
        # 1. Очищаем состояние
        current_state = await state.get_state()
        if current_state:
            await state.clear()
            logger.info(f"🗑️ Отмена TTS, состояние очищено для {callback.from_user.id}")
        
        # 2. Редактируем текущее сообщение (ВАЖНО: edit_text)
        await callback.message.edit_text(
            "❌ <b>Операция отменена</b>\n\n"
            "Вы вернулись в главное меню.",
            parse_mode='HTML',
            reply_markup=get_main_inline_menu(False)  # Убедитесь, что эта функция импортирована
        )
        
        # 3. Подтверждаем callback (убираем "часики")
        await callback.answer()
        
    except Exception as e:
        logger.error(f"❌ Ошибка при отмене TTS: {e}")
        # Если не удалось отредактировать, хотя бы ответим
        await callback.answer("Операция отменена", show_alert=False)