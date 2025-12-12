from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from config import PRICE_CONFIG, MANAGER_USERNAME


def get_main_inline_menu(is_admin: bool = False) -> InlineKeyboardMarkup:
    """Главное меню с inline-кнопками"""
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(text="📝 Генерация текста", callback_data="text_generation"),
        InlineKeyboardButton(text="🖼️ Генерация изображений", callback_data="image_generation")
    )
    builder.row(
        InlineKeyboardButton(text="🎤 Текст в аудио", callback_data="tts_generation"),
        InlineKeyboardButton(text="💰 Мой баланс", callback_data="balance")
    )
    builder.row(
        InlineKeyboardButton(text="📦 Мои заказы", callback_data="orders"),
        InlineKeyboardButton(text="🆘 Помощь", callback_data="help")
    )
    
    if is_admin:
        builder.row(
            InlineKeyboardButton(text="⚙️ Админ-панель", callback_data="admin_panel")
        )
    
    return builder.as_markup()


def get_back_button() -> InlineKeyboardMarkup:
    """Кнопка 'Назад'"""
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main"))
    return builder.as_markup()


def get_back_to_payments_button() -> InlineKeyboardMarkup:
    """Кнопка возврата к списку платежей"""
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="🔙 Назад к платежам", callback_data="admin_pending_payments"))
    return builder.as_markup()


def get_cancel_inline_button() -> InlineKeyboardMarkup:
    """Inline-кнопка отмены"""
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_operation"))
    return builder.as_markup()


def get_manager_contact_button() -> InlineKeyboardMarkup:
    """Кнопка для связи с менеджером"""
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="👨‍💼 Связаться с менеджером", url=f"https://t.me/{MANAGER_USERNAME.replace('@', '')}"))
    return builder.as_markup()


def get_admin_menu() -> InlineKeyboardMarkup:
    """Админ-меню"""
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats"),
        InlineKeyboardButton(text="👥 Пользователи", callback_data="admin_users")
    )
    builder.row(
        InlineKeyboardButton(text="💰 Управление платежами", callback_data="admin_payments"),
        InlineKeyboardButton(text="💳 Пополнить баланс", callback_data="admin_add_balance")
    )
    builder.row(
        InlineKeyboardButton(text="📢 Рассылка", callback_data="admin_broadcast"),
        InlineKeyboardButton(text="⚙️ Настройки", callback_data="admin_settings")
    )
    builder.row(
        InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main")
    )
    
    return builder.as_markup()


def get_admin_payments_menu() -> InlineKeyboardMarkup:
    """Меню управления платежами в админке"""
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(text="⏳ Ожидающие платежи", callback_data="admin_pending_payments"),
        InlineKeyboardButton(text="✅ Завершенные платежи", callback_data="admin_completed_payments")
    )
    builder.row(
        InlineKeyboardButton(text="📊 Статистика платежей", callback_data="admin_payments_stats"),
        InlineKeyboardButton(text="🔙 Назад в админку", callback_data="admin_panel")
    )
    
    return builder.as_markup()


def get_payment_menu() -> InlineKeyboardMarkup:
    """Меню пополнения баланса с бонусами"""
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(text="100₽", callback_data="payment_100"),
        InlineKeyboardButton(text="300₽", callback_data="payment_300"),
        InlineKeyboardButton(text="500₽", callback_data="payment_500")
    )
    builder.row(
        InlineKeyboardButton(text="1000₽", callback_data="payment_1000"),
        InlineKeyboardButton(text="5000₽", callback_data="payment_5000")
    )
    builder.row(
        InlineKeyboardButton(text="🎁 15×50₽ + бонус 200₽", callback_data="watch_ad"),
    )
    builder.row(
        InlineKeyboardButton(text="📊 Статистика", callback_data="ad_stats"),
        InlineKeyboardButton(text="🎁 Получить бонус", callback_data="claim_bonus")
    )
    builder.row(
        InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main")
    )
    
    return builder.as_markup()


def get_ad_confirmation_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для подтверждения просмотра рекламы"""
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(text="✅ Я посмотрел(а) рекламу", callback_data="confirm_ad"),
    )
    builder.row(
        InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_ad"),
    )
    
    return builder.as_markup()


def get_back_to_balance_button() -> InlineKeyboardMarkup:
    """Кнопка возврата в меню баланса"""
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="🔙 Назад к балансу", callback_data="balance"))
    return builder.as_markup()

def get_payment_management_menu(payment_id: int) -> InlineKeyboardMarkup:
    """Меню управления конкретным платежом"""
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"confirm_payment_{payment_id}"),
        InlineKeyboardButton(text="❌ Отклонить", callback_data=f"reject_payment_{payment_id}")
    )
    builder.row(
        InlineKeyboardButton(text="💬 Комментарий", callback_data=f"add_comment_{payment_id}"),
        InlineKeyboardButton(text="🔙 Назад к списку", callback_data="admin_pending_payments")
    )
    
    return builder.as_markup()
def get_waiting_keyboard(seconds_left: int, ad_id: str) -> InlineKeyboardMarkup:
    """Клавиатура ожидания для рекламы"""
    builder = InlineKeyboardBuilder()
    
    minutes = seconds_left // 60
    seconds = seconds_left % 60
    
    builder.row(
        InlineKeyboardButton(
            text=f"⏳ Ожидание... ({minutes}:{seconds:02d})", 
            callback_data="waiting"
        ),
    )
    builder.row(
        InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_ad"),
    )
    
    return builder.as_markup()


def get_ad_confirmation_keyboard(ad_id: str) -> InlineKeyboardMarkup:
    """Клавиатура для подтверждения просмотра рекламы"""
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(
            text="✅ Подтвердить просмотр", 
            callback_data=f"confirm_ad_{ad_id}"
        ),
    )
    builder.row(
        InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_ad"),
    )
    
    return builder.as_markup()
# keyboards.py - добавим кнопку помощи
def get_image_generation_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для генерации изображений"""
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(text="📖 Гид по промптам", callback_data="image_guide"),
        InlineKeyboardButton(text="🎨 Примеры", callback_data="image_examples")
    )
    builder.row(
        InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main"),
        InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_operation")
    )
    
    return builder.as_markup()