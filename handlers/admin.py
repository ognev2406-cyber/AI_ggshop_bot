from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from database import User, Order, Payment, get_pending_payments, get_completed_payments
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from keyboards import get_admin_menu, get_admin_payments_menu, get_back_button
import logging
import asyncio
from datetime import datetime, timedelta

router = Router()
logger = logging.getLogger(__name__)


class AddBalanceStates(StatesGroup):
    waiting_for_user_id = State()
    waiting_for_amount = State()


class AdminBroadcastStates(StatesGroup):
    waiting_for_broadcast_message = State()


@router.callback_query(F.data == "admin_panel")
async def admin_panel(callback: CallbackQuery, user: User, session: AsyncSession):
    """Показывает админ-панель"""
    if not user.is_admin:
        await callback.answer("❌ У вас нет прав администратора", show_alert=True)
        return
    
    try:
        # Статистика пользователей
        users_count_result = await session.execute(
            select(func.count(User.id))
        )
        users_count = users_count_result.scalar()
        
        # Статистика заказов
        orders_count_result = await session.execute(
            select(func.count(Order.id))
        )
        orders_count = orders_count_result.scalar()
        
        # Статистика платежей
        payments_sum_result = await session.execute(
            select(func.sum(Payment.amount)).where(Payment.status == "completed")
        )
        payments_sum = payments_sum_result.scalar() or 0
        
        # Пользователи за последние 7 дней
        week_ago = datetime.now() - timedelta(days=7)
        new_users_result = await session.execute(
            select(func.count(User.id)).where(User.created_at >= week_ago)
        )
        new_users = new_users_result.scalar()
        
        stats_text = (
            "⚙️ <b>Админ-панель</b>\n\n"
            "📊 <b>Статистика:</b>\n"
            f"👥 Пользователей: {users_count}\n"
            f"📦 Заказов: {orders_count}\n"
            f"💰 Общая сумма платежей: {payments_sum:.2f}₽\n"
            f"📈 Новых за неделю: {new_users}\n\n"
            "Выберите раздел:"
        )
        
        await callback.message.edit_text(
            stats_text,
            parse_mode="HTML",
            reply_markup=get_admin_menu()
        )
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Ошибка в админ-панели: {e}", exc_info=True)
        await callback.answer("❌ Ошибка при загрузке админ-панели", show_alert=True)


@router.callback_query(F.data == "admin_stats")
async def admin_stats(callback: CallbackQuery, session: AsyncSession):
    """Подробная статистика"""
    try:
        # Общая статистика
        users_count_result = await session.execute(select(func.count(User.id)))
        users_count = users_count_result.scalar()
        
        orders_count_result = await session.execute(select(func.count(Order.id)))
        orders_count = orders_count_result.scalar()
        
        payments_sum_result = await session.execute(
            select(func.sum(Payment.amount)).where(Payment.status == "completed")
        )
        payments_sum = payments_sum_result.scalar() or 0
        
        # Сегодняшняя статистика
        today = datetime.now().date()
        today_start = datetime.combine(today, datetime.min.time())
        today_end = datetime.combine(today, datetime.max.time())
        
        today_users_result = await session.execute(
            select(func.count(User.id)).where(User.created_at.between(today_start, today_end))
        )
        today_users = today_users_result.scalar()
        
        today_orders_result = await session.execute(
            select(func.count(Order.id)).where(Order.created_at.between(today_start, today_end))
        )
        today_orders = today_orders_result.scalar()
        
        today_payments_result = await session.execute(
            select(func.sum(Payment.amount)).where(
                Payment.status == "completed",
                Payment.completed_at.between(today_start, today_end)
            )
        )
        today_payments = today_payments_result.scalar() or 0
        
        stats_text = (
            "📊 <b>Детальная статистика</b>\n\n"
            "📅 <b>За все время:</b>\n"
            f"👥 Пользователей: {users_count}\n"
            f"📦 Заказов: {orders_count}\n"
            f"💰 Сумма платежей: {payments_sum:.2f}₽\n\n"
            "📅 <b>Сегодня:</b>\n"
            f"👥 Новых пользователей: {today_users}\n"
            f"📦 Новых заказов: {today_orders}\n"
            f"💰 Сумма платежей: {today_payments:.2f}₽"
        )
        
        await callback.message.edit_text(
            stats_text,
            parse_mode="HTML",
            reply_markup=get_back_button()
        )
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Ошибка при получении статистики: {e}", exc_info=True)
        await callback.answer("❌ Ошибка при загрузке статистики", show_alert=True)


@router.callback_query(F.data == "admin_users")
async def admin_users(callback: CallbackQuery, session: AsyncSession):
    """Список пользователей"""
    try:
        # Получаем последних 20 пользователей
        result = await session.execute(
            select(User).order_by(desc(User.created_at)).limit(20)
        )
        users = result.scalars().all()
        
        if not users:
            await callback.message.edit_text(
                "👥 <b>Пользователи</b>\n\n"
                "Пользователей пока нет.",
                parse_mode="HTML",
                reply_markup=get_back_button()
            )
            await callback.answer()
            return
        
        users_text = "👥 <b>Последние пользователи</b>\n\n"
        
        for user in users:
            user_info = (
                f"👤 <b>ID:</b> {user.telegram_id}\n"
                f"📛 <b>Имя:</b> {user.first_name or 'Не указано'} {user.last_name or ''}\n"
                f"📱 <b>Username:</b> @{user.username or 'Не указан'}\n"
                f"💰 <b>Баланс:</b> {user.balance:.2f}₽\n"
                f"📅 <b>Регистрация:</b> {user.created_at.strftime('%d.%m.%Y %H:%M')}\n"
            )
            if user.is_admin:
                user_info += "👑 <b>Администратор</b>\n"
            users_text += user_info + "──────────────\n"
        
        await callback.message.edit_text(
            users_text,
            parse_mode="HTML",
            reply_markup=get_back_button()
        )
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Ошибка при получении списка пользователей: {e}", exc_info=True)
        await callback.answer("❌ Ошибка при загрузке списка пользователей", show_alert=True)


@router.callback_query(F.data == "admin_payments")
async def admin_payments_menu(callback: CallbackQuery):
    """Меню управления платежами"""
    await callback.message.edit_text(
        "💰 <b>Управление платежами</b>\n\n"
        "Выберите раздел:",
        parse_mode="HTML",
        reply_markup=get_admin_payments_menu()
    )
    await callback.answer()


@router.callback_query(F.data == "admin_pending_payments")
async def admin_pending_payments(callback: CallbackQuery, session: AsyncSession):
    """Ожидающие платежи"""
    try:
        payments = await get_pending_payments(session)
        
        if not payments:
            await callback.message.edit_text(
                "⏳ <b>Ожидающие платежи</b>\n\n"
                "Ожидающих платежей нет.",
                parse_mode="HTML",
                reply_markup=get_back_button()
            )
            await callback.answer()
            return
        
        payments_text = "⏳ <b>Ожидающие платежи</b>\n\n"
        
        for payment in payments:
            # Получаем информацию о пользователе
            user_result = await session.execute(
                select(User).where(User.id == payment.user_id)
            )
            user = user_result.scalar_one_or_none()
            
            user_info = f"@{user.username}" if user and user.username else f"ID: {payment.user_id}"
            
            payments_text += (
                f"💰 <b>Платеж ID:</b> {payment.id}\n"
                f"👤 <b>Пользователь:</b> {user_info}\n"
                f"💳 <b>Сумма:</b> {payment.amount}₽\n"
                f"📝 <b>Комментарий:</b> {payment.comment or 'Нет'}\n"
                f"📅 <b>Создан:</b> {payment.created_at.strftime('%d.%m.%Y %H:%M')}\n"
                "──────────────\n"
            )
        
        await callback.message.edit_text(
            payments_text,
            parse_mode="HTML",
            reply_markup=get_back_button()
        )
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Ошибка при получении ожидающих платежей: {e}", exc_info=True)
        await callback.answer("❌ Ошибка при загрузке платежей", show_alert=True)


@router.callback_query(F.data == "admin_completed_payments")
async def admin_completed_payments(callback: CallbackQuery, session: AsyncSession):
    """Завершенные платежи"""
    try:
        payments = await get_completed_payments(session)
        
        if not payments:
            await callback.message.edit_text(
                "✅ <b>Завершенные платежи</b>\n\n"
                "Завершенных платежей пока нет.",
                parse_mode="HTML",
                reply_markup=get_back_button()
            )
            await callback.answer()
            return
        
        payments_text = "✅ <b>Последние завершенные платежи</b>\n\n"
        
        for payment in payments[:10]:  # Показываем только последние 10
            # Получаем информацию о пользователе
            user_result = await session.execute(
                select(User).where(User.id == payment.user_id)
            )
            user = user_result.scalar_one_or_none()
            
            user_info = f"@{user.username}" if user and user.username else f"ID: {payment.user_id}"
            
            payments_text += (
                f"💰 <b>Платеж ID:</b> {payment.id}\n"
                f"👤 <b>Пользователь:</b> {user_info}\n"
                f"💳 <b>Сумма:</b> {payment.amount}₽\n"
                f"📅 <b>Завершен:</b> {payment.completed_at.strftime('%d.%m.%Y %H:%M') if payment.completed_at else 'Не указано'}\n"
                "──────────────\n"
            )
        
        await callback.message.edit_text(
            payments_text,
            parse_mode="HTML",
            reply_markup=get_back_button()
        )
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Ошибка при получении завершенных платежей: {e}", exc_info=True)
        await callback.answer("❌ Ошибка при загрузке платежей", show_alert=True)


@router.callback_query(F.data == "admin_add_balance")
async def admin_add_balance_start(callback: CallbackQuery, state: FSMContext):
    """Начало пополнения баланса пользователя"""
    await state.set_state(AddBalanceStates.waiting_for_user_id)
    await callback.message.edit_text(
        "👤 <b>Пополнение баланса пользователя</b>\n\n"
        "Введите Telegram ID пользователя:",
        parse_mode="HTML",
        reply_markup=get_back_button()
    )
    await callback.answer()


@router.message(AddBalanceStates.waiting_for_user_id)
async def admin_add_balance_get_user_id(message: Message, state: FSMContext, session: AsyncSession):
    """Получение ID пользователя"""
    try:
        telegram_id = int(message.text.strip())
    except ValueError:
        await message.answer("❌ Неверный формат. Введите числовой Telegram ID.")
        return
    
    # Ищем пользователя
    result = await session.execute(
        select(User).where(User.telegram_id == telegram_id)
    )
    user = result.scalar_one_or_none()
    
    if not user:
        await message.answer(f"❌ Пользователь с ID {telegram_id} не найден.")
        await state.clear()
        return
    
    await state.update_data(telegram_id=telegram_id, user_id=user.id)
    await state.set_state(AddBalanceStates.waiting_for_amount)
    
    await message.answer(
        f"👤 <b>Пользователь найден:</b>\n"
        f"ID: {user.telegram_id}\n"
        f"Имя: {user.first_name or 'Не указано'} {user.last_name or ''}\n"
        f"Username: @{user.username or 'Не указан'}\n"
        f"💰 Текущий баланс: {user.balance}₽\n\n"
        "Введите сумму для пополнения (в рублях):",
        parse_mode="HTML"
    )


@router.message(AddBalanceStates.waiting_for_amount)
async def admin_add_balance_get_amount(message: Message, state: FSMContext, session: AsyncSession):
    """Получение суммы и пополнение баланса"""
    try:
        amount = float(message.text.strip().replace(',', '.'))
        if amount <= 0:
            await message.answer("❌ Сумма должна быть положительной.")
            return
    except ValueError:
        await message.answer("❌ Неверный формат. Введите число (например: 100 или 50.5).")
        return
    
    data = await state.get_data()
    telegram_id = data['telegram_id']
    user_id = data['user_id']
    
    # Находим пользователя
    result = await session.execute(
        select(User).where(User.id == user_id)
    )
    user = result.scalar_one_or_none()
    
    if not user:
        await message.answer("❌ Пользователь не найден.")
        await state.clear()
        return
    
    # Пополняем баланс
    old_balance = user.balance
    user.balance += amount
    
    # Создаем запись о платеже
    payment = Payment(
        user_id=user.id,
        amount=amount,
        status='completed',
        payment_method='admin_add',
        completed_at=datetime.now()
    )
    session.add(payment)
    await session.commit()
    
    await message.answer(
        f"✅ <b>Баланс успешно пополнен!</b>\n\n"
        f"👤 Пользователь: {user.first_name or 'ID: ' + str(user.telegram_id)}\n"
        f"📊 Было: {old_balance}₽\n"
        f"➕ Начислено: {amount}₽\n"
        f"💰 Стало: {user.balance}₽\n"
        f"📝 ID транзакции: {payment.id}",
        parse_mode="HTML"
    )
    
    await state.clear()


@router.callback_query(F.data == "admin_broadcast")
async def admin_broadcast_start(callback: CallbackQuery, state: FSMContext):
    """Начало рассылки сообщений"""
    if not callback.from_user:
        await callback.answer("❌ Ошибка: пользователь не найден", show_alert=True)
        return
    
    await state.set_state(AdminBroadcastStates.waiting_for_broadcast_message)
    await callback.message.edit_text(
        "📢 <b>Рассылка сообщений</b>\n\n"
        "Введите сообщение для рассылки всем пользователям:",
        parse_mode="HTML",
        reply_markup=get_back_button()
    )
    await callback.answer()


@router.message(AdminBroadcastStates.waiting_for_broadcast_message)
async def admin_broadcast_send(message: Message, state: FSMContext, session: AsyncSession):
    """Отправка рассылки"""
    broadcast_text = message.text
    
    if not broadcast_text or len(broadcast_text.strip()) == 0:
        await message.answer("❌ Сообщение не может быть пустым.")
        return
    
    # Получаем всех пользователей
    result = await session.execute(select(User))
    users = result.scalars().all()
    
    if not users:
        await message.answer("❌ Нет пользователей для рассылки.")
        await state.clear()
        return
    
    sent_count = 0
    failed_count = 0
    
    # Сначала отправляем сообщение о начале рассылки
    status_message = await message.answer(
        f"📤 <b>Начинаю рассылку...</b>\n"
        f"👥 Всего пользователей: {len(users)}\n"
        f"⏳ Это займет примерно {len(users) * 0.05:.1f} секунд",
        parse_mode="HTML"
    )
    
    for user in users:
        try:
            await message.bot.send_message(
                chat_id=user.telegram_id,
                text=f"📢 <b>Сообщение от администратора:</b>\n\n{broadcast_text}",
                parse_mode="HTML"
            )
            sent_count += 1
            
            # Обновляем статус каждые 10 сообщений
            if sent_count % 10 == 0:
                try:
                    await status_message.edit_text(
                        f"📤 <b>Рассылка в процессе...</b>\n"
                        f"✅ Отправлено: {sent_count}\n"
                        f"❌ Не отправлено: {failed_count}\n"
                        f"👥 Всего пользователей: {len(users)}",
                        parse_mode="HTML"
                    )
                except:
                    pass
                    
        except Exception as e:
            logger.error(f"Не удалось отправить сообщение пользователю {user.telegram_id}: {e}")
            failed_count += 1
        
        # Небольшая задержка, чтобы не превысить лимиты Telegram
        await asyncio.sleep(0.05)
    
    # Отправляем финальный отчет
    await status_message.edit_text(
        f"✅ <b>Рассылка завершена!</b>\n\n"
        f"📤 Успешно отправлено: {sent_count}\n"
        f"❌ Не удалось отправить: {failed_count}\n"
        f"👥 Всего пользователей: {len(users)}\n\n"
        f"📊 Эффективность: {(sent_count/len(users)*100):.1f}%",
        parse_mode="HTML"
    )
    
    await state.clear()


@router.callback_query(F.data == "admin_settings")
async def admin_settings(callback: CallbackQuery):
    """Настройки админ-панели"""
    await callback.message.edit_text(
        "⚙️ <b>Настройки админ-панели</b>\n\n"
        "Функции настроек пока в разработке.\n\n"
        "Доступные настройки:\n"
        "• Управление администраторами\n"
        "• Настройка тарифов\n"
        "• Логирование действий\n"
        "• Резервное копирование",
        parse_mode="HTML",
        reply_markup=get_back_button()
    )
    await callback.answer()


@router.callback_query(F.data == "admin_payments_stats")
async def admin_payments_stats(callback: CallbackQuery, session: AsyncSession):
    """Статистика платежей"""
    try:
        # Общая сумма платежей
        total_payments_result = await session.execute(
            select(func.sum(Payment.amount)).where(Payment.status == "completed")
        )
        total_payments = total_payments_result.scalar() or 0
        
        # Количество платежей
        payments_count_result = await session.execute(
            select(func.count(Payment.id)).where(Payment.status == "completed")
        )
        payments_count = payments_count_result.scalar()
        
        # Средний платеж
        avg_payment = total_payments / payments_count if payments_count > 0 else 0
        
        # Платежи по дням за последние 7 дней
        week_ago = datetime.now() - timedelta(days=7)
        daily_stats_result = await session.execute(
            select(
                func.date(Payment.completed_at).label('date'),
                func.count(Payment.id).label('count'),
                func.sum(Payment.amount).label('total')
            )
            .where(
                Payment.status == "completed",
                Payment.completed_at >= week_ago
            )
            .group_by(func.date(Payment.completed_at))
            .order_by(func.date(Payment.completed_at).desc())
        )
        daily_stats = daily_stats_result.all()
        
        stats_text = "💰 <b>Статистика платежей</b>\n\n"
        stats_text += f"📊 <b>Общая статистика:</b>\n"
        stats_text += f"• Всего платежей: {payments_count}\n"
        stats_text += f"• Общая сумма: {total_payments:.2f}₽\n"
        stats_text += f"• Средний платеж: {avg_payment:.2f}₽\n\n"
        
        stats_text += f"📅 <b>За последние 7 дней:</b>\n"
        if daily_stats:
            for stat in daily_stats:
                stats_text += f"• {stat.date}: {stat.count} платежей на {stat.total or 0:.2f}₽\n"
        else:
            stats_text += "Платежей за последние 7 дней нет.\n"
        
        await callback.message.edit_text(
            stats_text,
            parse_mode="HTML",
            reply_markup=get_back_button()
        )
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Ошибка при получении статистики платежей: {e}", exc_info=True)
        await callback.answer("❌ Ошибка при загрузке статистики платежей", show_alert=True)