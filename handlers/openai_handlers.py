import asyncio
from aiogram import Router
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from states import TextGeneration
import logging
from services.ai_service import ai_service

router = Router()
logger = logging.getLogger(__name__)

@router.message(TextGeneration.waiting_for_prompt)
async def process_text_prompt(message: Message, state: FSMContext, user, session):
    """Обработка запроса на генерацию текста - ИСПРАВЛЕННАЯ ВЕРСИЯ"""
    current_state = await state.get_state()
    if current_state != TextGeneration.waiting_for_prompt:
        logger.warning(f"Некорректное состояние: {current_state} для генерации текста")
        await message.answer("❌ Пожалуйста, начните генерацию заново через меню.")
        await state.clear()
        return
    
    data = await state.get_data()
    cost = data.get("cost", 15)
    prompt = message.text.strip()
    
    # Проверки длины с очисткой состояния
    if len(prompt) > 2000:
        await message.answer("❌ Слишком длинный запрос. Максимум 2000 символов.")
        await state.clear()
        return
    
    if len(prompt) < 3:
        await message.answer("❌ Слишком короткий запрос. Минимум 3 символа.")
        await state.clear()
        return
    
    # Статус-сообщение
    status_msg = await message.answer("⏳ <b>Генерирую текст...</b>", parse_mode="HTML")
    
    try:
        logger.info(f"Начало генерации для пользователя {user.telegram_id}")
        logger.info(f"Запрос: {prompt}")
        
        # УВЕЛИЧИВАЕМ таймаут и уменьшаем токены
        system_prompt = "Ты полезный ассистент. Отвечай кратко и по делу. Твой ответ должен быть полностью на русском языке."
        
        try:
            # УВЕЛИЧИВАЕМ таймаут до 240 секунд, УМЕНЬШАЕМ токены до 512
            generated_text = await asyncio.wait_for(
                ai_service.generate_text(
                    prompt, 
                    system_prompt=system_prompt, 
                    max_tokens=512  # УМЕНЬШЕНО с 2048
                ),
                timeout=240.0  # УВЕЛИЧЕНО с 120.0
            )
        except asyncio.TimeoutError:
            logger.error("Таймаут генерации (240 секунд)")
            try:
                await status_msg.edit_text(
                    "❌ <b>Превышено время ожидания!</b>\n\n"
                    "Генерация заняла слишком много времени.\n"
                    "Попробуйте:\n"
                    "• Упростить запрос\n"
                    "• Разделить на части\n"
                    "• Использовать другую функцию",
                    parse_mode="HTML"
                )
            except:
                await message.answer("❌ Превышено время генерации. Попробуйте другой запрос.")
            
            # ГАРАНТИРОВАННАЯ очистка состояния
            await state.clear()
            
            # ДОПОЛНИТЕЛЬНО: проверяем доступность Ollama
            asyncio.create_task(check_and_notify_ollama_status())
            return
        
        # Проверяем результат
        if not generated_text or generated_text.startswith("❌"):
            logger.warning(f"Ошибка генерации: {generated_text}")
            await status_msg.edit_text(
                f"❌ <b>Ошибка генерации:</b>\n{generated_text}",
                parse_mode="HTML"
            )
            await state.clear()
            return
        
        # Списание средств
        user.balance -= cost
        
        # Сохраняем заказ
        from database import Order
        order = Order(
            user_id=user.id,
            product_type="text",
            product_subtype="text_generation",
            prompt=prompt[:1000],
            result=generated_text[:2000],  # Уменьшено с 4000
            cost=cost
        )
        session.add(order)
        await session.commit()
        
        logger.info(f"Заказ сохранен, ID: {order.id}, баланс: {user.balance}")
        
        # Формируем результат
        result_text = (
            f"✅ <b>Текст готов!</b>\n\n"
            f"{generated_text}\n\n"
            f"💳 Списано: {cost}₽ | 💰 Остаток: {user.balance:.2f}₽"
        )
        
        # Удаляем статус
        try:
            await status_msg.delete()
        except:
            pass
        
        await message.answer(result_text, parse_mode="HTML")
        
        # Очищаем состояние
        await state.clear()
        logger.info(f"Генерация завершена для пользователя {user.telegram_id}")
        
    except Exception as e:
        logger.error(f"Критическая ошибка в обработчике: {e}", exc_info=True)
        
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
        
        # ГАРАНТИРОВАННАЯ очистка состояния
        await state.clear()

async def check_and_notify_ollama_status():
    """Проверка статуса Ollama после таймаута"""
    await asyncio.sleep(5)  # Ждем 5 секунд
    is_accessible = await ai_service.check_api_access()
    if not is_accessible:
        logger.error("❌ Ollama недоступен после таймаута!")

@router.message(TextGeneration.waiting_for_prompt)
async def process_text_prompt(message: Message, state: FSMContext, user, session):
    """Обработка запроса на генерацию текста"""
    # Проверяем, что состояние корректное
    current_state = await state.get_state()
    if current_state != TextGeneration.waiting_for_prompt:
        logger.warning(f"Некорректное состояние: {current_state} для генерации текста")
        await message.answer("❌ Пожалуйста, начните генерацию заново через меню.")
        await state.clear()
        return
    
    data = await state.get_data()
    cost = data.get("cost", 15)  # Берем цену из состояния
    
    prompt = message.text
    
    if len(prompt) > 2000:
        await message.answer("❌ Слишком длинный запрос. Максимум 2000 символов.")
        return
    
    if len(prompt) < 3:
        await message.answer("❌ Слишком короткий запрос. Минимум 3 символа.")
        return
    
    # Показываем статус
    status_msg = await message.answer("⏳ <b>Генерирую текст...</b>", parse_mode="HTML")
    
    try:
        logger.info(f"Начало генерации для пользователя {user.telegram_id}")
        logger.info(f"Запрос: {prompt}")
        
        # Генерируем текст с увеличенным лимитом токенов
        system_prompt = "Ты полезный ассистент. Отвечай подробно и развернуто. Твой ответ должен быть полностью на русском языке, даже если запрос на другом языке."
        
        try:
            import asyncio
            generated_text = await asyncio.wait_for(
                ai_service.generate_text(prompt, system_prompt=system_prompt, max_tokens=1024),  # Увеличенный лимит
                timeout=300.0  # Увеличили таймаут для длинных текстов
            )
        except asyncio.TimeoutError:
            logger.error("Таймаут генерации (120 секунд)")
            await status_msg.edit_text(
                "❌ <b>Превышено время ожидания генерации!</b>\n\n"
                "Генерация заняла слишком много времени.\n"
                "Попробуйте упростить запрос или разделить его на части.",
                parse_mode="HTML"
            )
            await state.clear()
            return
        
        logger.info(f"Текст сгенерирован, длина: {len(generated_text)} символов")
        
        # Проверяем результат
        if not generated_text or generated_text.startswith("❌"):
            logger.warning(f"Ошибка генерации: {generated_text}")
            await status_msg.edit_text(
                f"❌ <b>Ошибка генерации:</b>\n{generated_text}",
                parse_mode="HTML"
            )
            await state.clear()
            return
        
        # Списание средств
        user.balance -= cost
        
        # Сохраняем заказ
        from database import Order
        order = Order(
            user_id=user.id,
            product_type="text",
            product_subtype="text_generation",  # Фиксированный тип
            prompt=prompt[:1000],
            result=generated_text[:4000],  # Увеличенный лимит сохранения
            cost=cost
        )
        session.add(order)
        await session.commit()
        
        logger.info(f"Заказ сохранен, ID: {order.id}, баланс: {user.balance}")
        
        # Формируем результат
        result_text = (
            f"✅ <b>Текст готов!</b>\n\n"
            f"{generated_text}\n\n"
            f"💳 Списано: {cost}₽ | 💰 Остаток: {user.balance:.2f}₽"
        )
        
        # Удаляем статус и отправляем результат
        try:
            await status_msg.delete()
        except:
            pass
        
        await message.answer(result_text, parse_mode="HTML")
        
        # Очищаем состояние
        await state.clear()
        logger.info(f"Генерация завершена для пользователя {user.telegram_id}")
        
    except Exception as e:
        logger.error(f"Критическая ошибка в обработчике: {e}", exc_info=True)
        
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