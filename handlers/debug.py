from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
import logging

router = Router()
logger = logging.getLogger(__name__)


@router.message(F.text == "/debug")
async def debug_command(message: Message, state: FSMContext):
    """Команда для отладки"""
    current_state = await state.get_state()
    await message.answer(
        f"🔍 <b>Отладочная информация:</b>\n\n"
        f"👤 ID пользователя: {message.from_user.id}\n"
        f"📝 Текст: {message.text}\n"
        f"🔄 Состояние: {current_state}\n"
        f"🤖 Бот активен",
        parse_mode="HTML"
    )


@router.message(F.text)
async def debug_all_messages(message: Message, state: FSMContext):
    """Логирование всех текстовых сообщений"""
    current_state = await state.get_state()
    logger.info(
        f"📨 Получено сообщение от {message.from_user.id}: "
        f"'{message.text[:50]}...' | Состояние: {current_state}"
    )


@router.callback_query(F.data)
async def debug_all_callbacks(callback: CallbackQuery, state: FSMContext):
    """Логирование всех callback-запросов"""
    current_state = await state.get_state()
    logger.info(
        f"🔘 Получен callback от {callback.from_user.id}: "
        f"'{callback.data}' | Состояние: {current_state}"
    )