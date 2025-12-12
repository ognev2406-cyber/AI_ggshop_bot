from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart, Command
from keyboards import get_main_inline_menu

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message, user):
    """Обработчик команды /start"""
    welcome_text = (
        f"👋 Привет, {message.from_user.first_name}!\n\n"
        "🤖 Я - AI бот для генерации контента.\n"
        "Я могу:\n"
        "• 📝 Генерировать текст\n"
        "• 🖼️ Создавать изображения\n"
        "• 🎤 Текст в аудио\n\n"
        "💰 На ваш баланс начислено 50₽ для тестирования!\n"
        "Используйте кнопки ниже для навигации:"
    )
    
    await message.answer(welcome_text, reply_markup=get_main_inline_menu(user.is_admin))


@router.message(Command("help"))
async def cmd_help(message: Message):
    """Обработчик команды /help"""
    help_text = (
        "🆘 Помощь\n\n"
        "📝 <b>Генерация текста</b>:\n"
        "• Короткий текст (до 500 символов) - 10₽\n"
        "• Средний текст (до 2000 символов) - 25₽\n"
        "• Длинный текст (до 5000 символов) - 50₽\n\n"
        "🖼️ <b>Генерация изображений</b>:\n"
        "• SD качество - 30₽\n"
        "• HD качество - 50₽\n"
        "• 4K качество - 100₽\n\n"
        "🎤 <b>Текст в аудио</b>:\n"
        "• Короткое аудио (до 5 минут) - 15₽\n"
        "• Длинное аудио (до 30 минут) - 30₽\n\n"
        "💰 <b>Пополнение баланса</b>:\n"
        "1. Выберите сумму в разделе 'Мой баланс'\n"
        "2. Свяжитесь с менеджером для оплаты\n"
        "3. Получите пополнение после подтверждения\n\n"
        "👨‍💼 <b>Контакты</b>:\n"
        "• Для вопросов и пополнения: @ваш_менеджер"
    )
    
    await message.answer(help_text, parse_mode="HTML")


@router.callback_query(F.data == "back_to_main")
async def back_to_main(callback: CallbackQuery, user):
    """Возврат в главное меню"""
    await callback.message.edit_text(
        "🏠 Главное меню\n\n"
        "Выберите действие:",
        reply_markup=get_main_inline_menu(user.is_admin)
    )


@router.callback_query(F.data == "help")
async def show_help(callback: CallbackQuery):
    """Показать справку"""
    help_text = (
        "🆘 Помощь\n\n"
        "Выберите раздел для подробной информации."
    )
    await callback.message.edit_text(help_text, reply_markup=get_main_inline_menu())