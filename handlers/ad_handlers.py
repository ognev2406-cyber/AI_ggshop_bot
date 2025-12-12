# handlers/ad_handlers.py
import asyncio
import logging
from datetime import datetime, timedelta
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from config import AD_REWARD_AMOUNT, AD_WATCH_TIME, MAX_ADS_PER_DAY, AD_COOLDOWN_MINUTES, ADMIN_IDS
from keyboards import get_main_inline_menu
import pytz

logger = logging.getLogger(__name__)
router = Router()


class AdStates(StatesGroup):
    watching_ad = State()


def get_ad_keyboard(ad_id: str = None):
    """Главная клавиатура рекламы"""
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(
            text="✅ Подтвердить просмотр", 
            callback_data=f"confirm_ad_{ad_id}" if ad_id else "confirm_ad"
        ),
    )
    builder.row(
        InlineKeyboardButton(text="📱 Открыть рекламу", url="https://t.me/@CitiZeN2406"),
        InlineKeyboardButton(text="🎥 Видео-реклама", url="https://youtube.com/shorts/example")
    )
    builder.row(
        InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_ad"),
    )
    
    return builder.as_markup()


def get_waiting_keyboard(seconds_left: int, ad_id: str = None):
    """Клавиатура ожидания с большими кнопками"""
    builder = InlineKeyboardBuilder()
    
    minutes = seconds_left // 60
    seconds = seconds_left % 60
    
    builder.row(
        InlineKeyboardButton(
            text=f"⏳ {minutes:02d}:{seconds:02d} | Смотрите рекламу...", 
            callback_data="waiting"
        ),
    )
    builder.row(
        InlineKeyboardButton(text="📱 Перейти к рекламе", url="https://t.me/your_channel"),
    )
    builder.row(
        InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_ad"),
    )
    
    return builder.as_markup()


@router.callback_query(F.data == "watch_ad")
async def start_watching_ad(callback: CallbackQuery, state: FSMContext, user, session):
    """Начало просмотра рекламы - 15 раз в день по 50₽"""
    now = datetime.now(pytz.UTC)
    
    # Проверяем количество просмотров сегодня
    from database import Payment
    from sqlalchemy import select, func, cast, Date
    
    # Получаем количество просмотров за сегодня
    result = await session.execute(
        select(func.count(Payment.id)).where(
            Payment.user_id == user.id,
            Payment.payment_method == "ad_reward",
            func.date(Payment.created_at) == func.date(now)
        )
    )
    today_views = result.scalar() or 0
    
    logger.info(f"📊 Пользователь {user.telegram_id} просмотров сегодня: {today_views}/{MAX_ADS_PER_DAY}")
    
    # Проверяем лимит
    if today_views >= MAX_ADS_PER_DAY:
        await callback.answer(
            f"❌ Достигнут лимит!\n"
            f"Вы просмотрели {today_views} реклам сегодня.\n"
            f"Максимум: {MAX_ADS_PER_DAY} раз в день.\n"
            f"Попробуйте завтра!",
            show_alert=True
        )
        return
    
    # Проверяем минимальный интервал между просмотрами (если нужно)
    if AD_COOLDOWN_MINUTES > 0 and user.last_ad_watch:
        time_since_last = now - user.last_ad_watch
        if time_since_last < timedelta(minutes=AD_COOLDOWN_MINUTES):
            minutes_left = AD_COOLDOWN_MINUTES - time_since_last.seconds // 60
            await callback.answer(
                f"⏳ Подождите {minutes_left} минут перед следующим просмотром",
                show_alert=True
            )
            return
    
    # Начинаем просмотр
    await state.set_state(AdStates.watching_ad)
    
    # Генерируем уникальный ID
    import uuid
    ad_id = str(uuid.uuid4())[:8]
    
    await state.update_data(
        start_time=now,
        ad_id=ad_id,
        user_id=user.id,
        reward_amount=AD_REWARD_AMOUNT
    )
    
    # Рассчитываем общий возможный заработок за день
    total_possible = (MAX_ADS_PER_DAY - today_views) * AD_REWARD_AMOUNT
    
    # Показываем рекламу
    await callback.message.edit_text(
        f"🎬 <b>ПРОСМОТР РЕКЛАМЫ • {today_views + 1}/{MAX_ADS_PER_DAY}</b>\n\n"
        
        f"💰 <b>ЗАРАБОТОК ЗА ПРОСМОТР:</b> {AD_REWARD_AMOUNT}₽\n"
        f"💎 <b>ОСТАЛОСЬ СЕГОДНЯ:</b> {MAX_ADS_PER_DAY - today_views} просмотров\n"
        f"🏆 <b>МОЖНО ЗАРАБОТАТЬ:</b> {total_possible}₽\n\n"
        
        f"📋 <b>ИНСТРУКЦИЯ:</b>\n"
        f"1. Нажмите кнопку '📱 Перейти к рекламе'\n"
        f"2. Просмотрите рекламу ({AD_WATCH_TIME} сек)\n"
        f"3. Вернитесь в бот\n"
        f"4. Нажмите '✅ Подтвердить просмотр'\n\n"
        
        f"⏳ <b>ТАЙМЕР:</b> {AD_WATCH_TIME} секунд\n"
        f"📊 <b>ВАШ БАЛАНС:</b> {user.balance:.2f}₽",
        parse_mode="HTML",
        disable_web_page_preview=True,
        reply_markup=get_waiting_keyboard(AD_WATCH_TIME, ad_id)
    )
    
    # Запускаем таймер
    asyncio.create_task(ad_timer(callback.message, state, ad_id, AD_WATCH_TIME))
    await callback.answer(f"🎬 Начало просмотра #{today_views + 1}")

# handlers/ad_handlers.py - ДОБАВЬТЕ этот метод в класс AIService или создайте отдельно

async def check_and_award_daily_bonus(user, session, today_views):
    """Проверка и начисление ежедневного бонуса"""
    from database import Payment
    from sqlalchemy import select, func
    from datetime import datetime
    import pytz
    from config import DAILY_BONUS_AMOUNT, DAILY_BONUS_THRESHOLD
    
    now = datetime.now(pytz.UTC)
    
    # Проверяем, достиг ли пользователь порога для бонуса
    if today_views >= DAILY_BONUS_THRESHOLD:
        # Проверяем, не получал ли уже бонус сегодня
        result = await session.execute(
            select(func.count(Payment.id)).where(
                Payment.user_id == user.id,
                Payment.payment_method == "daily_bonus",
                func.date(Payment.created_at) == func.date(now)
            )
        )
        already_got_bonus = result.scalar() or 0
        
        if already_got_bonus == 0:
            # Начисляем бонус
            old_balance = user.balance
            user.balance += DAILY_BONUS_AMOUNT
            
            # Сохраняем платеж
            bonus_payment = Payment(
                user_id=user.id,
                amount=DAILY_BONUS_AMOUNT,
                currency="RUB",
                status="completed",
                payment_method="daily_bonus",
                comment=f"Ежедневный бонус за {today_views} просмотров рекламы"
            )
            session.add(bonus_payment)
            await session.commit()
            
            logger.info(f"🎁 Пользователь {user.telegram_id} получил ежедневный бонус {DAILY_BONUS_AMOUNT}₽")
            
            return {
                "awarded": True,
                "amount": DAILY_BONUS_AMOUNT,
                "old_balance": old_balance,
                "new_balance": user.balance,
                "views": today_views
            }
    
    return {"awarded": False}

async def ad_timer(message, state, ad_id, wait_time):
    """Таймер обратного отсчета"""
    try:
        for i in range(wait_time, 0, -1):
            await asyncio.sleep(1)
            
            # Проверяем, не отменил ли пользователь
            current_state = await state.get_state()
            if not current_state:
                return
                
            # Обновляем каждую секунду или каждые 5 секунд
            if i % 5 == 0 or i == wait_time or i <= 10:
                try:
                    await message.edit_reply_markup(
                        reply_markup=get_waiting_keyboard(i, ad_id)
                    )
                except:
                    pass
        
        # Время вышло - меняем на кнопку подтверждения
        current_state = await state.get_state()
        if current_state:
            try:
                await message.edit_reply_markup(
                    reply_markup=get_ad_keyboard(ad_id)
                )
            except:
                pass
                
    except Exception as e:
        logger.error(f"Ошибка в таймере: {e}")


@router.callback_query(F.data.startswith("confirm_ad_"))
async def confirm_ad_watch(callback: CallbackQuery, state: FSMContext, user, session):
    """Подтверждение просмотра рекламы - ИСПРАВЛЕННАЯ ВЕРСИЯ"""
    try:
        # 1. ПОЛУЧИТЕ ДАННЫЕ ИЗ СОСТОЯНИЯ (ВАЖНО!)
        data = await state.get_data()
        if not data:
            await callback.answer("❌ Сессия истекла. Начните просмотр заново.", show_alert=True)
            return
        
        ad_id = callback.data.replace("confirm_ad_", "")
        
        # 2. Проверяем ID рекламы
        stored_ad_id = data.get("ad_id")
        if stored_ad_id != ad_id:
            await callback.answer("❌ Недействительное подтверждение", show_alert=True)
            return
        
        # 3. Проверяем время просмотра
        start_time = data.get("start_time")
        if not start_time:
            await callback.answer("❌ Ошибка таймера", show_alert=True)
            await state.clear()
            return
        
        elapsed = (datetime.now(pytz.UTC) - start_time).seconds
        if elapsed < AD_WATCH_TIME:
            remaining = AD_WATCH_TIME - elapsed
            await callback.answer(
                f"❌ Просмотрите рекламу еще {remaining} секунд",
                show_alert=True
            )
            return
        
        # 4. Получаем количество просмотров сегодня
        from database import Payment
        from sqlalchemy import select, func
        
        result = await session.execute(
            select(func.count(Payment.id)).where(
                Payment.user_id == user.id,
                Payment.payment_method == "ad_reward",
                func.date(Payment.created_at) == func.date(datetime.now(pytz.UTC))
            )
        )
        today_views = result.scalar() or 0
        
        # 5. Проверяем лимит
        if today_views >= MAX_ADS_PER_DAY:
            await callback.answer(
                f"❌ Достигнут дневной лимит {MAX_ADS_PER_DAY} просмотров",
                show_alert=True
            )
            await state.clear()
            return
        
        # 6. Начисляем награду
        reward = data.get("reward_amount", AD_REWARD_AMOUNT)  # Теперь data определена
        old_balance = user.balance
        user.balance += reward
        user.last_ad_watch = datetime.now(pytz.UTC)
        
        # 7. Сохраняем платеж
        payment = Payment(
            user_id=user.id,
            amount=reward,
            currency="RUB",
            status="completed",
            payment_method="ad_reward",
            comment=f"Просмотр рекламы #{today_views + 1} за день"
        )
        session.add(payment)
        await session.commit()
        
        # 8. Обновляем счетчик
        today_views += 1
        
        # 9. Формируем сообщение
        remaining_views = MAX_ADS_PER_DAY - today_views
        remaining_earnings = remaining_views * AD_REWARD_AMOUNT
        
        success_text = (
            f"✅ <b>РЕКЛАМА ПРОСМОТРЕНА!</b>\n\n"
            f"🎯 <b>ПРОСМОТР #{today_views}/{MAX_ADS_PER_DAY}</b>\n"
            f"💰 <b>+{reward}₽</b> начислено на баланс\n\n"
            f"📊 <b>БАЛАНС:</b> {old_balance:.2f}₽ → {user.balance:.2f}₽\n"
            f"📈 <b>ОСТАЛОСЬ:</b> {remaining_views} просмотров\n"
            f"💵 <b>МОЖНО ЗАРАБОТАТЬ:</b> {remaining_earnings}₽\n\n"
        )
        
        if today_views == MAX_ADS_PER_DAY:
            success_text += "🏆 <b>ВЫ ВЫПОЛНИЛИ ДНЕВНОЙ ПЛАН!</b>\nЗаходите завтра!"
        elif remaining_views <= 3:
            success_text += f"⚡ <b>Осталось {remaining_views} просмотра!</b>"
        
        await callback.message.edit_text(
            success_text,
            parse_mode="HTML",
            reply_markup=get_main_inline_menu(user.telegram_id in ADMIN_IDS)
        )
        
        await state.clear()
        await callback.answer(f"✅ +{reward}₽ на баланс!", show_alert=False)
        
    except Exception as e:
        logger.error(f"❌ Ошибка в confirm_ad_watch: {e}", exc_info=True)
        await callback.answer(f"❌ Ошибка: {str(e)[:100]}", show_alert=True)

@router.callback_query(F.data == "claim_bonus")
async def claim_daily_bonus(callback: CallbackQuery, user, session):
    """Ручное получение ежедневного бонуса"""
    from database import Payment
    from sqlalchemy import select, func
    from datetime import datetime
    import pytz
    
    now = datetime.now(pytz.UTC)
    
    # Проверяем просмотры за сегодня
    result = await session.execute(
        select(func.count(Payment.id)).where(
            Payment.user_id == user.id,
            Payment.payment_method == "ad_reward",
            func.date(Payment.created_at) == func.date(now)
        )
    )
    today_views = result.scalar() or 0
    
    # Проверяем, получал ли уже бонус
    result_bonus = await session.execute(
        select(func.count(Payment.id)).where(
            Payment.user_id == user.id,
            Payment.payment_method == "daily_bonus",
            func.date(Payment.created_at) == func.date(now)
        )
    )
    already_got_bonus = result_bonus.scalar() or 0
    
    if already_got_bonus > 0:
        await callback.answer("🎁 Вы уже получили ежедневный бонус сегодня!", show_alert=True)
        return
    
    if today_views >= DAILY_BONUS_THRESHOLD:
        # Начисляем бонус
        old_balance = user.balance
        user.balance += DAILY_BONUS_AMOUNT
        
        bonus_payment = Payment(
            user_id=user.id,
            amount=DAILY_BONUS_AMOUNT,
            currency="RUB",
            status="completed",
            payment_method="daily_bonus",
            comment=f"Ежедневный бонус за {today_views} просмотров рекламы"
        )
        session.add(bonus_payment)
        await session.commit()
        
        await callback.message.edit_text(
            f"🎁 <b>ЕЖЕДНЕВНЫЙ БОНУС ПОЛУЧЕН!</b>\n\n"
            f"🏆 За {today_views} просмотров рекламы\n"
            f"💰 +{DAILY_BONUS_AMOUNT}₽ на баланс\n\n"
            f"📊 Баланс: {old_balance:.2f}₽ → {user.balance:.2f}₽\n\n"
            f"Спасибо за активность! 🎯",
            parse_mode="HTML",
            reply_markup=get_main_inline_menu(user.telegram_id in ADMIN_IDS)
        )
        await callback.answer(f"✅ +{DAILY_BONUS_AMOUNT}₽ бонус!", show_alert=False)
    else:
        await callback.answer(
            f"❌ Нужно {DAILY_BONUS_THRESHOLD} просмотров для бонуса. У вас: {today_views}",
            show_alert=True
        )
@router.callback_query(F.data == "cancel_ad")
async def cancel_ad_watch(callback: CallbackQuery, state: FSMContext):
    """Отмена просмотра рекламы"""
    await state.clear()
    
    is_admin = callback.from_user.id in ADMIN_IDS if ADMIN_IDS else False
    
    await callback.message.edit_text(
        "❌ Просмотр рекламы отменен",
        reply_markup=get_main_inline_menu(is_admin)
    )
    await callback.answer("❌ Просмотр отменен")


@router.callback_query(F.data == "ad_stats")
async def show_ad_stats(callback: CallbackQuery, user, session):
    """Показать статистику по рекламе с информацией о бонусах"""
    from database import Payment
    from sqlalchemy import select, func
    from datetime import datetime
    import pytz
    from config import DAILY_BONUS_AMOUNT, DAILY_BONUS_THRESHOLD
    
    now = datetime.now(pytz.UTC)
    
    # Статистика за сегодня
    result = await session.execute(
        select(func.count(Payment.id), func.sum(Payment.amount)).where(
            Payment.user_id == user.id,
            Payment.payment_method == "ad_reward",
            func.date(Payment.created_at) == func.date(now)
        )
    )
    today_stats = result.first()
    
    today_views = today_stats[0] or 0
    today_earnings = today_stats[1] or 0
    
    # Бонусы за сегодня
    result_bonus = await session.execute(
        select(func.count(Payment.id), func.sum(Payment.amount)).where(
            Payment.user_id == user.id,
            Payment.payment_method == "daily_bonus",
            func.date(Payment.created_at) == func.date(now)
        )
    )
    today_bonus_stats = result_bonus.first()
    
    today_bonus_count = today_bonus_stats[0] or 0
    today_bonus_amount = today_bonus_stats[1] or 0
    
    # Статистика за все время
    result_all = await session.execute(
        select(func.count(Payment.id), func.sum(Payment.amount)).where(
            Payment.user_id == user.id,
            Payment.payment_method == "ad_reward"
        )
    )
    all_stats = result_all.first()
    
    total_views = all_stats[0] or 0
    total_earnings = all_stats[1] or 0
    
    # Бонусы за все время
    result_all_bonus = await session.execute(
        select(func.count(Payment.id), func.sum(Payment.amount)).where(
            Payment.user_id == user.id,
            Payment.payment_method == "daily_bonus"
        )
    )
    all_bonus_stats = result_all_bonus.first()
    
    total_bonus_count = all_bonus_stats[0] or 0
    total_bonus_amount = all_bonus_stats[1] or 0
    
    # Расчеты
    remaining_views = MAX_ADS_PER_DAY - today_views
    views_to_bonus = max(0, DAILY_BONUS_THRESHOLD - today_views)
    possible_bonus = DAILY_BONUS_AMOUNT if today_views < DAILY_BONUS_THRESHOLD else 0
    
    # Формируем текст статистики
    stats_text = (
        f"📊 <b>СТАТИСТИКА РЕКЛАМЫ</b>\n\n"
        
        f"🎯 <b>СЕГОДНЯ:</b>\n"
        f"• Просмотров: {today_views}/{MAX_ADS_PER_DAY}\n"
        f"• Заработано: {today_earnings:.2f}₽\n"
    )
    
    # Информация о бонусе
    if today_bonus_count > 0:
        stats_text += f"• 🎁 Бонус получен: {today_bonus_amount:.2f}₽\n"
    else:
        if today_views >= DAILY_BONUS_THRESHOLD:
            stats_text += f"• 🎁 Бонус доступен: {DAILY_BONUS_AMOUNT}₽\n"
        else:
            stats_text += f"• 🎁 До бонуса: {views_to_bonus} просмотров\n"
    
    stats_text += (
        f"• Осталось просмотров: {remaining_views}\n"
        f"• Можно заработать: {remaining_views * AD_REWARD_AMOUNT}₽\n\n"
        
        f"🏆 <b>ЕЖЕДНЕВНЫЙ БОНУС:</b>\n"
        f"• За {DAILY_BONUS_THRESHOLD} просмотров: {DAILY_BONUS_AMOUNT}₽\n"
        f"• Ваш прогресс: {today_views}/{DAILY_BONUS_THRESHOLD}\n"
    )
    
    if today_views >= DAILY_BONUS_THRESHOLD:
        if today_bonus_count > 0:
            stats_text += f"• ✅ Бонус получен сегодня!\n"
        else:
            stats_text += f"• ⚡ Бонус ожидает получения!\n"
    else:
        stats_text += f"• 📈 Осталось до бонуса: {views_to_bonus} просмотров\n"
    
    stats_text += (
        f"\n💰 <b>ВСЕГО ЗАРАБОТАНО:</b>\n"
        f"• Просмотров: {total_views}\n"
        f"• С рекламы: {total_earnings:.2f}₽\n"
        f"• С бонусов: {total_bonus_amount:.2f}₽\n"
        f"• <b>ИТОГО: {total_earnings + total_bonus_amount:.2f}₽</b>\n\n"
        
        f"📈 <b>РАСЧЕТ НА ДЕНЬ:</b>\n"
        f"• 15 просмотров × 50₽ = 750₽\n"
        f"• Ежедневный бонус = 200₽\n"
        f"• <b>Максимум в день: 950₽</b>"
    )
    
    await callback.message.edit_text(
        stats_text,
        parse_mode="HTML",
        reply_markup=get_main_inline_menu(user.telegram_id in ADMIN_IDS)
    )
    await callback.answer()