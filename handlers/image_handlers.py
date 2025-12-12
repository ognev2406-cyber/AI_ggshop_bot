from aiogram import Router
from aiogram.types import Message, BufferedInputFile
from aiogram.fsm.context import FSMContext
from states import ImageGeneration
import logging
from config import STABLE_DIFFUSION_ENABLED
from database import User, Order
from sqlalchemy.ext.asyncio import AsyncSession
from services.ai_service import ai_service

router = Router()
logger = logging.getLogger(__name__)


@router.message(ImageGeneration.waiting_for_prompt)
async def process_image_prompt(message: Message, state: FSMContext, user: User, session: AsyncSession):
    """Обработка запроса на генерацию изображения"""
    # Проверяем, что состояние корректное
    current_state = await state.get_state()
    if current_state != ImageGeneration.waiting_for_prompt:
        logger.warning(f"Некорректное состояние: {current_state} для генерации изображения")
        await message.answer("❌ Пожалуйста, начните генерацию заново через меню.")
        await state.clear()
        return
    
    # Получаем данные из состояния
    data = await state.get_data()
    cost = data.get("cost", 20)
    
    prompt = message.text
    
    # Проверяем длину промпта
    if len(prompt) > 1000:
        await message.answer("❌ Слишком длинный запрос. Максимум 1000 символов.")
        return
    
    if len(prompt) < 3:
        await message.answer("❌ Слишком короткий запрос. Минимум 3 символа.")
        return
    
    # Проверяем баланс
    if user.balance < cost:
        await message.answer(f"❌ Недостаточно средств. Нужно {cost}₽, у вас {user.balance}₽")
        return
    
    # Показываем статус
    status_msg = await message.answer("⏳ <b>Генерирую изображение...</b>\n\n"
                                     "Это может занять 30-60 секунд.", 
                                     parse_mode="HTML")
    
    try:
        if not STABLE_DIFFUSION_ENABLED:
            await status_msg.edit_text(
                "❌ <b>Генерация изображений временно отключена</b>\n\n"
                "Мы работаем над интеграцией новой модели.\n"
                "Скоро все будет готово!",
                parse_mode="HTML"
            )
            await state.clear()
            return
        
        # Импортируем сервис только когда нужен
        from services.ai_service import ai_service
        
        # Генерируем изображение
        logger.info(f"Начало генерации изображения для пользователя {user.telegram_id}")
        logger.info(f"🖼️ Запрос: {prompt}")
        
        # Добавляем базовые улучшения к промпту
        enhanced_prompt = f"{prompt}, high quality, detailed, masterpiece"
        
        result_text, image_bytes = await ai_service.generate_image(enhanced_prompt)
        
        if not image_bytes:
            await status_msg.edit_text(f"❌ {result_text}")
            await state.clear()
            return
        
        logger.info(f"✅ Изображение сгенерировано, размер: {len(image_bytes)} байт")
        
        # Списание средств
        user.balance -= cost
        
        # Сохраняем заказ
        order = Order(
            user_id=user.id,
            product_type="image",
            product_subtype="generated",
            prompt=prompt[:500],
            result="Изображение успешно сгенерировано",
            cost=cost
        )
        session.add(order)
        await session.commit()
        
        logger.info(f"✅ Заказ сохранен, ID: {order.id}, баланс: {user.balance}")
        
        # Отправляем изображение
        photo = BufferedInputFile(image_bytes, filename="generated_image.png")
        
        await message.answer_photo(
            photo,
            caption=f"✅ <b>Изображение готово!</b>\n\n"
                   f"📝 <b>Запрос:</b> {prompt}\n\n"
                   f"💳 Списано: {cost}₽ | 💰 Остаток: {user.balance:.2f}₽",
            parse_mode="HTML"
        )
        
        # Удаляем статус
        try:
            await status_msg.delete()
        except:
            pass
        
        # Очищаем состояние
        await state.clear()
        logger.info(f"✅ Генерация изображения завершена для пользователя {user.telegram_id}")
        
    except Exception as e:
        logger.error(f"❌ Критическая ошибка в обработчике изображений: {e}", exc_info=True)
        
        try:
            await status_msg.edit_text(
                f"❌ <b>Внутренняя ошибка:</b>\n{str(e)[:200]}",
                parse_mode="HTML"
            )
        except:
            await message.answer(
                f"❌ <b>Внутренняя ошибка:</b>\n{str(e)[:200]}",
                parse_mode="HTML"
            )
        
        await state.clear()