from aiogram import Router, F
from aiogram.types import CallbackQuery
from datetime import datetime, timedelta
import random
import asyncio
import time
import logging
from config import AD_REWARD_AMOUNT, AD_WATCH_TIME
from database import User
from sqlalchemy.ext.asyncio import AsyncSession
from keyboards import (
    get_payment_menu, 
    get_back_button, 
    get_back_to_balance_button, 
    get_ad_confirmation_keyboard, 
    get_waiting_keyboard,
    get_main_inline_menu
)


router = Router()
logger = logging.getLogger(__name__)

@router.callback_query(F.data.startswith("payment_"))
async def handle_payment(callback: CallbackQuery, user: User):
    """Обработка выбора суммы для пополнения"""
    payment_type = callback.data
    
    if payment_type == "payment_100":
        amount = 100
    elif payment_type == "payment_300":
        amount = 300
    elif payment_type == "payment_500":
        amount = 500
    elif payment_type == "payment_1000":
        amount = 1000
    elif payment_type == "payment_5000":
        amount = 5000
    elif payment_type == "payment_free":
        # Обработка бесплатной попытки
        await handle_free_payment(callback, user)
        return
    else:
        await callback.answer("❌ Неизвестная сумма платежа", show_alert=True)
        return
    
    # Для платных платежей показываем инструкцию
    await callback.message.edit_text(
        f"💳 <b>Пополнение баланса на {amount}₽</b>\n\n"
        "Для пополнения баланса:\n\n"
        "1. Напишите нашему менеджеру\n"
        "    <code>@CitiZeN2406</code>\n\n"
        "2. Укажите сумму пополнения и следуйте указаниям менеджера\n\n"
        "3. Средства будут зачислены в течение 15 минут\n\n"
        "<i>Или выберите другой способ пополнения:</i>",
        parse_mode="HTML",
        reply_markup=get_payment_menu()
    )
    await callback.answer()


async def handle_free_payment(callback: CallbackQuery, user: User, session: AsyncSession):
    """Обработка бесплатной попытки"""
    from datetime import date
    
    # Проверяем, не использовал ли пользователь уже бесплатную попытку сегодня
    today = date.today()
    
    if user.last_free_payment and user.last_free_payment.date() == today:
        await callback.answer(
            "❌ Вы уже использовали бесплатную попытку сегодня. Попробуйте завтра!",
            show_alert=True
        )
        return
    
    # Начисляем 10 рублей за бесплатную попытку
    reward = 10
    user.balance += reward
    user.last_free_payment = datetime.now()
    
    # Сохраняем платеж в базе
    from database import Payment
    payment = Payment(
        user_id=user.id,
        amount=reward,
        status='completed',
        payment_method='free_trial'
    )
    session.add(payment)
    await session.commit()
    
    await callback.answer(f"✅ Вам начислено {reward}₽ на баланс!", show_alert=True)
    
    # Обновляем сообщение с балансом
    await callback.message.edit_text(
        f"💰 <b>Ваш баланс:</b> {user.balance}₽\n\n"
        "Выберите способ пополнения:",
        parse_mode="HTML",
        reply_markup=get_payment_menu()
    )

@router.callback_query(F.data == "balance")
async def show_balance(callback: CallbackQuery, user: User):
    """Показывает баланс пользователя"""
    try:
        logger.info(f"Пользователь {user.telegram_id} запросил баланс: {user.balance}₽")
        
        balance_text = (
            f"💰 <b>Ваш баланс:</b> {user.balance}₽\n\n"
            "Выберите способ пополнения:"
        )
        
        await callback.message.edit_text(
            balance_text,
            parse_mode="HTML",
            reply_markup=get_payment_menu()
        )
        await callback.answer()
        
        logger.info(f"Баланс успешно показан пользователю {user.telegram_id}")
    except Exception as e:
        logger.error(f"Ошибка при показе баланса: {e}", exc_info=True)
        await callback.answer("❌ Ошибка при загрузке баланса. Попробуйте позже.", show_alert=True)

@router.callback_query(F.data == "waiting")
async def handle_waiting_button(callback: CallbackQuery):
    """Обработка нажатия на кнопку ожидания"""
    await callback.answer(
        "⏳ Пожалуйста, дождитесь окончания просмотра рекламы.",
        show_alert=True
    )


async def update_ad_timer(message, total_seconds: int, ad_id: str, user_id: int):
    """Обновляет таймер в сообщении с рекламой"""
    try:
        from aiogram import Bot
        from config import BOT_TOKEN
        bot = Bot(token=BOT_TOKEN)
        
        for seconds_left in range(total_seconds, 0, -1):
            await asyncio.sleep(1)
            
            # Обновляем сообщение каждые 10 секунд или в последние 5 секунд
            if seconds_left % 10 == 0 or seconds_left <= 5:
                minutes = seconds_left // 60
                seconds = seconds_left % 60
                
                # Получаем текущий текст сообщения
                current_text = message.text
                
                # Обновляем только часть с таймером
                lines = current_text.split('\n')
                for i, line in enumerate(lines):
                    if "⏰ <b>Время просмотра:</b>" in line:
                        if seconds_left > 0:
                            lines[i] = f"⏰ <b>Осталось времени:</b> {minutes}:{seconds:02d}"
                        else:
                            lines[i] = f"⏰ <b>Время просмотра завершено!</b>"
                        break
                
                updated_text = '\n'.join(lines)
                
                try:
                    if seconds_left > 0:
                        # Обновляем сообщение с кнопкой ожидания
                        from keyboards import get_waiting_keyboard
                        await message.edit_text(
                            updated_text,
                            parse_mode="HTML",
                            disable_web_page_preview=True,
                            reply_markup=get_waiting_keyboard(seconds_left, ad_id)
                        )
                    else:
                        # Время истекло, показываем кнопку подтверждения
                        from keyboards import get_ad_confirmation_keyboard
                        # Заменяем последнюю строку
                        lines = updated_text.split('\n')
                        if "Пожалуйста, уделите внимание" in lines[-1]:
                            lines[-1] = "✅ <b>Время просмотра завершено! Теперь вы можете подтвердить просмотр.</b>"
                        
                        final_text = '\n'.join(lines)
                        
                        await message.edit_text(
                            final_text,
                            parse_mode="HTML",
                            disable_web_page_preview=True,
                            reply_markup=get_ad_confirmation_keyboard(ad_id)
                        )
                except Exception as e:
                    logger.error(f"Ошибка при обновлении таймера: {e}")
                    # Если не удалось обновить, прекращаем таймер
                    break
        
        await bot.session.close()
        
    except Exception as e:
        logger.error(f"Ошибка в таймере рекламы: {e}")


@router.callback_query(F.data.startswith("confirm_ad_"))
async def confirm_ad_watch(callback: CallbackQuery, session: AsyncSession, user: User):
    """Подтверждение просмотра рекламы"""
    try:
        ad_id = callback.data.replace("confirm_ad_", "")
        
        # Проверяем, прошло ли достаточно времени
        from aiogram.fsm.context import FSMContext
        from aiogram.fsm.storage.base import StorageKey
        from main import dp
        from datetime import datetime
        
        state = FSMContext(
            storage=dp.storage,
            key=StorageKey(
                chat_id=callback.message.chat.id,
                user_id=callback.from_user.id,
                bot_id=callback.bot.id
            )
        )
        
        data = await state.get_data()
        stored_ad_id = data.get("ad_id")
        ad_start_time_str = data.get("ad_start_time")
        
        # Проверяем совпадение ad_id и время просмотра
        if stored_ad_id != ad_id:
            await callback.answer("❌ Неверная реклама. Начните просмотр заново.", show_alert=True)
            return
        
        if ad_start_time_str:
            ad_start_time = datetime.fromisoformat(ad_start_time_str)
            time_watched = (datetime.now() - ad_start_time).total_seconds()
            
            if time_watched < AD_WATCH_TIME:
                remaining = AD_WATCH_TIME - int(time_watched)
                await callback.answer(
                    f"⏳ Пожалуйста, просмотрите рекламу еще {remaining} секунд.",
                    show_alert=True
                )
                return
        
        # Начисляем награду
        user.balance += AD_REWARD_AMOUNT
        user.last_ad_watch = datetime.now()
        
        await session.commit()
        
        # Показываем успешное сообщение
        success_message = (
            f"✅ <b>Отлично!</b>\n\n"
            f"💎 На ваш баланс начислено: <b>+{AD_REWARD_AMOUNT}₽</b>\n"
            f"💰 Текущий баланс: <b>{user.balance}₽</b>\n\n"
            "🎉 <i>Вы можете смотреть рекламу неограниченное количество раз!</i>\n"
            "Просто вернитесь в меню баланса и выберите 'Бесплатные деньги за рекламу' снова."
        )
        
        # Редактируем сообщение с рекламой
        try:
            await callback.message.edit_text(
                success_message,
                parse_mode="HTML",
                reply_markup=get_back_to_balance_button()
            )
        except:
            # Если не удалось редактировать, отправляем новое сообщение
            await callback.message.answer(
                success_message,
                parse_mode="HTML",
                reply_markup=get_back_to_balance_button()
            )
        
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Ошибка при подтверждении рекламы: {e}", exc_info=True)
        await callback.answer("❌ Ошибка при подтверждении. Попробуйте позже.", show_alert=True)


@router.callback_query(F.data == "cancel_ad")
async def cancel_ad_watch(callback: CallbackQuery):
    """Отмена просмотра рекламы"""
    await callback.message.edit_text(
        "❌ Просмотр рекламы отменен.",
        reply_markup=get_back_to_balance_button()
    )
    await callback.answer()


@router.callback_query(F.data == "ad_stats")
async def show_ad_stats(callback: CallbackQuery, user: User):
    """Статистика по просмотрам рекламы"""
    from datetime import datetime
    
    stats_message = "📊 <b>Статистика просмотра рекламы</b>\n\n"
    
    if hasattr(user, 'last_ad_watch') and user.last_ad_watch:
        last_watch = user.last_ad_watch.strftime("%d.%m.%Y в %H:%M")
        stats_message += f"⏰ <b>Последний просмотр:</b> {last_watch}\n"
    else:
        stats_message += "⏰ <b>Последний просмотр:</b> Еще не смотрели\n"
    
    if hasattr(user, 'ads_watched_today'):
        stats_message += f"👁️ <b>Просмотрено сегодня:</b> {user.ads_watched_today}\n"
    
    stats_message += (
        f"💰 <b>Награда за просмотр:</b> {AD_REWARD_AMOUNT}₽\n"
        f"⏱️ <b>Время просмотра:</b> {AD_WATCH_TIME} секунд\n\n"
        "🎯 <b>Особенности:</b>\n"
        "✅ Без ограничений по количеству\n"
        "✅ Разная реклама каждый раз\n"
        f"✅ Необходимо просматривать {AD_WATCH_TIME} секунд\n\n"
        "<i>Смотрите рекламу, получайте деньги, пользуйтесь ботом бесплатно!</i>"
    )
    
    await callback.message.answer(
        stats_message,
        parse_mode="HTML",
        reply_markup=get_back_button()
    )
    await callback.answer()


@router.callback_query(F.data == "back_to_balance")
async def back_to_balance(callback: CallbackQuery):
    """Возврат в меню баланса"""
    from keyboards import get_payment_menu
    
    await callback.message.edit_text(
        "💰 <b>Пополнение баланса</b>\n\n"
        "Выберите способ пополнения:",
        parse_mode="HTML",
        reply_markup=get_payment_menu()
    )
    await callback.answer()
@router.callback_query(F.data.startswith("payment_"))
async def handle_payment_selection(callback: CallbackQuery, user: User):
    """Обработка выбора суммы для пополнения"""
    payment_data = callback.data
    logger.info(f"Пользователь {user.telegram_id} выбрал платеж: {payment_data}")
    
    # Определяем сумму платежа
    if payment_data == "payment_100":
        amount = 100
    elif payment_data == "payment_300":
        amount = 300
    elif payment_data == "payment_500":
        amount = 500
    elif payment_data == "payment_1000":
        amount = 1000
    elif payment_data == "payment_5000":
        amount = 5000
    elif payment_data == "payment_free":
        # Бесплатная попытка - начисляем 10 рублей
        amount = 10
    else:
        await callback.answer("❌ Неизвестная сумма платежа", show_alert=True)
        return
    
    if payment_data == "payment_free":
        # Обработка бесплатной попытки
        from datetime import datetime
        
        # Проверяем, не использовал ли пользователь уже бесплатную попытку
        if hasattr(user, 'last_free_payment') and user.last_free_payment:
            # Проверяем, была ли бесплатная попытка сегодня
            from datetime import date
            if user.last_free_payment.date() == date.today():
                await callback.answer(
                    "❌ Вы уже использовали бесплатную попытку сегодня. Попробуйте завтра!",
                    show_alert=True
                )
                return
        
        # Начисляем средства
        from database import Payment
        from sqlalchemy.ext.asyncio import AsyncSession
        
        payment = Payment(
            user_id=user.id,
            amount=amount,
            status='completed',
            method='free_trial'
        )
        
        # Обновляем баланс пользователя
        user.balance += amount
        if hasattr(user, 'last_free_payment'):
            user.last_free_payment = datetime.now()
        
        try:
            session = AsyncSession()  # Получаем сессию
            session.add(payment)
            await session.commit()
            
            await callback.answer(
                f"✅ Вам начислено {amount}₽ на баланс!",
                show_alert=True
            )
            
            # Обновляем сообщение с балансом
            from keyboards import get_payment_menu
            await callback.message.edit_text(
                f"💰 <b>Ваш баланс:</b> {user.balance}₽\n\n"
                "Выберите способ пополнения:",
                parse_mode="HTML",
                reply_markup=get_payment_menu()
            )
            
        except Exception as e:
            logger.error(f"Ошибка при начислении бесплатных средств: {e}")
            await callback.answer("❌ Ошибка при начислении средств", show_alert=True)
    else:
        # Для платных платежей - показываем инструкцию
        await callback.message.edit_text(
            f"💳 <b>Пополнение баланса на {amount}₽</b>\n\n"
            "Для пополнения баланса:\n\n"
            "1. Переведите сумму на карту:\n"
            "   <code>2200 7001 2345 6789</code>\n\n"
            "2. После перевода отправьте скриншот чека @manager_username\n\n"
            "3. Средства будут зачислены в течение 15 минут\n\n"
            "<i>Или выберите другой способ пополнения:</i>",
            parse_mode="HTML",
            reply_markup=get_payment_menu()
        )
    
    await callback.answer()


@router.callback_query(F.data == "help")
async def show_help(callback: CallbackQuery):
    """Показывает справку"""
    await callback.message.edit_text(
        "🆘 <b>Помощь</b>\n\n"
        "📝 <b>Генерация текста:</b>\n"
        "• Нажмите 'Генерация текста'\n"
        "• Введите ваш запрос\n"
        "• Получите результат за несколько секунд\n\n"
        "💰 <b>Пополнение баланса:</b>\n"
        "• Выберите сумму в меню баланса\n"
        "• Переведите средства на карту\n"
        "• Отправьте скриншот менеджеру\n\n"
        "🎬 <b>Просмотр рекламы:</b>\n"
        "• Нажмите 'Бесплатные деньги за рекламу'\n"
        "• Просмотрите рекламу 40 секунд\n"
        "• Подтвердите просмотр\n"
        "• Получите +5₽ на баланс\n\n"
        "👨‍💼 <b>Связь с менеджером:</b> @manager_username\n"
        "📧 <b>Техподдержка:</b> support@example.com",
        parse_mode="HTML",
        reply_markup=get_back_button()
    )
    await callback.answer()


@router.callback_query(F.data == "back_to_main")
async def back_to_main_menu(callback: CallbackQuery):
    """Возврат в главное меню"""
    from keyboards import get_main_inline_menu
    from database import User
    from sqlalchemy.ext.asyncio import AsyncSession
    from sqlalchemy import select
    
    # Определяем, является ли пользователь админом
    try:
        # Получаем пользователя из базы данных
        stmt = select(User).where(User.telegram_id == callback.from_user.id)
        result = await AsyncSession().execute(stmt)
        user = result.scalar_one_or_none()
        
        is_admin = user.is_admin if user and hasattr(user, 'is_admin') else False
    except Exception as e:
        logger.error(f"Ошибка при проверке прав админа: {e}")
        is_admin = False
    
    await callback.message.edit_text(
        "🤖 <b>Добро пожаловать в AIggshop!</b>\n\n"
        "Я помогу вам создать уникальный контент с помощью искусственного интеллекта.\n\n"
        "Выберите действие:",
        parse_mode="HTML",
        reply_markup=get_main_inline_menu(is_admin)
    )
    await callback.answer()
@router.callback_query(F.data == "back_to_main")
async def back_to_main_menu(callback: CallbackQuery, user: User):
    """Возврат в главное меню"""
    # Определяем, является ли пользователь админом
    is_admin = user.is_admin if user else False
    
    await callback.message.edit_text(
        "🤖 <b>Добро пожаловать в AIggshop!</b>\n\n"
        "Я помогу вам создать уникальный контент с помощью искусственного интеллекта.\n\n"
        "Выберите действие:",
        parse_mode="HTML",
        reply_markup=get_main_inline_menu(is_admin)
    )
    await callback.answer()