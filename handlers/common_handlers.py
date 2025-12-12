# handlers/common_handlers.py
import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext
from keyboards import get_main_inline_menu

logger = logging.getLogger(__name__)
router = Router()

@router.callback_query(F.data == "back_to_main")
async def handle_back_to_main(callback: CallbackQuery, state: FSMContext):
    """Обработка кнопки 'Назад' в главное меню"""
    try:
        # Очищаем состояние FSM
        current_state = await state.get_state()
        if current_state:
            await state.clear()
            logger.info(f"🗑️ Очищено состояние для {callback.from_user.id}")
        
        # Возвращаем главное меню
        from database import get_user_by_id  # Или ваш способ проверки админа
        user = await get_user_by_id(callback.from_user.id)
        is_admin = user.is_admin if user else False
        
        await callback.message.edit_text(
            "🏠 *Главное меню*\n\n"
            "Выберите нужный раздел:",
            parse_mode="Markdown",
            reply_markup=get_main_inline_menu(is_admin)
        )
        await callback.answer()
        
    except Exception as e:
        logger.error(f"❌ Ошибка в back_to_main: {e}")
        await callback.answer("Произошла ошибка", show_alert=True)

@router.callback_query(F.data == "cancel_operation")
async def handle_cancel_operation(callback: CallbackQuery, state: FSMContext):
    """Обработка кнопки 'Отмена'"""
    current_state = await state.get_state()
    if current_state:
        await state.clear()
    
    await callback.message.edit_text(
        "❌ Операция отменена.\n"
        "Вы вернулись в главное меню.",
        reply_markup=get_main_inline_menu(False)
    )
    await callback.answer()