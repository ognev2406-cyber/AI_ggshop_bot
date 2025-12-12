from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext
from states import TextGeneration
from keyboards import (
    get_back_button
)

router = Router()

from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext
from states import ImageGeneration
from keyboards import get_back_button

router = Router()


# products.py - обновим обработчик image_generation
@router.callback_query(F.data == "image_generation")
async def handle_image_generation(callback: CallbackQuery, state: FSMContext):
    """Обработчик кнопки генерации изображений"""
    from config import PRICE_CONFIG, STABLE_DIFFUSION_ENABLED
    
    cost = PRICE_CONFIG.get('image_generation', 20)
    
    # Проверяем, доступна ли генерация изображений
    if not STABLE_DIFFUSION_ENABLED:
        await callback.message.edit_text(
            "🖼️ <b>Генерация изображений</b>\n\n"
            "В данный момент генерация изображений временно недоступна.\n\n"
            "Мы работаем над интеграцией новой модели.\n\n"
            "Скоро все будет готово!",
            parse_mode="HTML",
            reply_markup=get_back_button()
        )
        await callback.answer()
        return
    
    # Устанавливаем состояние и сохраняем цену
    await state.set_state(ImageGeneration.waiting_for_prompt)
    await state.update_data(cost=cost)
    
    await callback.message.edit_text(
        "🖼️ <b>Генерация изображений</b>\n\n"
        f"💳 Стоимость: {cost}₽\n\n"
        "🎨 <b>Доступные стили:</b>\n"
        "• Реалистичные фотографии\n"
        "• Цифровое искусство\n"
        "• Картины маслом\n"
        "• Аниме и манга\n"
        "• Киберпанк\n"
        "• Фэнтези\n\n"
        "📝 <b>Как писать промпты:</b>\n"
        "1. Укажите главный объект\n"
        "2. Добавьте детали (цвет, освещение)\n"
        "3. Укажите стиль\n"
        "4. Добавьте фон и атмосферу\n\n"
        "<b>Примеры:</b>\n"
        "• 'Реалистичная фотография заката над горами, золотые облака, эпическое освещение, профессиональная фотография'\n"
        "• 'Кот в скафандре в космосе, цифровое искусство, детализированное, 4K, звёздное небо на заднем плане'\n"
        "• 'Футуристический город будущего ночью, неоновые огни, дождь, киберпанк стиль, Blade Runner'\n\n"
        "<i>Отправьте ваш запрос ниже...</i>",
        parse_mode="HTML",
        reply_markup=get_back_button()
    )
    await callback.answer()

@router.callback_query(F.data == "text_generation")
async def handle_text_generation(callback: CallbackQuery, state: FSMContext):
    """Обработчик кнопки генерации текста - сразу запрашивает текст"""
    # Устанавливаем состояние и фиксированную стоимость
    from config import PRICE_CONFIG
    cost = PRICE_CONFIG.get('text_generation', 10)  # Новая цена для генерации текста
    
    await state.set_state(TextGeneration.waiting_for_prompt)
    await state.update_data(cost=cost)
    
    await callback.message.edit_text(
        "📝 <b>Генерация текста</b>\n\n"
        "Введите ваш запрос для генерации текста.\n\n"
        f"💳 Стоимость: {cost}₽\n\n"
        "Примеры запросов:\n"
        "• 'Напиши пост о пользе спорта'\n"
        "• 'Составь план обучения Python'\n"
        "• 'Придумай рекламный слоган для кофейни'\n\n"
        "<i>Отправьте ваш текст ниже...</i>",
        parse_mode="HTML",
        reply_markup=get_back_button()
    )
    await callback.answer()


@router.callback_query(F.data == "image_generation")
async def handle_image_generation(callback: CallbackQuery):
    """Обработчик кнопки генерации изображений"""
    await callback.message.edit_text(
        "🖼️ <b>Генерация изображений</b>\n\n"
        "В данный момент генерация изображений временно недоступна.\n"
        "Мы работаем над интеграцией новой модели.\n\n"
        "Скоро все будет готово!",
        parse_mode="HTML",
        reply_markup=get_back_button()
    )


@router.callback_query(F.data == "audio_transcription")
async def handle_audio_transcription(callback: CallbackQuery):
    """Обработчик кнопки транскрибации аудио"""
    await callback.message.edit_text(
        "🎤 <b>Транскрибация аудио</b>\n\n"
        "В данный момент транскрибация аудио временно недоступна.\n"
        "Мы работаем над интеграцией новой модели.\n\n"
        "Скоро все будет готово!",
        parse_mode="HTML",
        reply_markup=get_back_button()
    )


@router.callback_query(F.data.in_(["image_sd", "image_hd", "image_4k"]))
async def handle_image_options(callback: CallbackQuery):
    """Обработчик выбора качества изображения"""
    await callback.answer("⏳ Функция в разработке", show_alert=True)


@router.callback_query(F.data.in_(["audio_short", "audio_long"]))
async def handle_audio_options(callback: CallbackQuery):
    """Обработчик выбора типа аудио"""
    await callback.answer("⏳ Функция в разработке", show_alert=True)