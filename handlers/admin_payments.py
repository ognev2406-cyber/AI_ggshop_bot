from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy.ext.asyncio import AsyncSession

from database import (
    get_pending_payments,
    get_completed_payments,
    get_payment_by_id,
    update_payment_status
)
from keyboards import (
    get_admin_payments_menu,
    get_payment_management_menu,
    get_back_to_payments_button
)
from states import PaymentComment

router = Router()


@router.callback_query(F.data == "admin_pending_payments")
async def show_pending_payments(callback: CallbackQuery, session: AsyncSession):
    """Показать список ожидающих платежей"""
    payments = await get_pending_payments(session)
    
    if not payments:
        await callback.message.edit_text(
            "⏳ <b>Ожидающие платежи</b>\n\nНет ожидающих платежей.",
            parse_mode="HTML",
            reply_markup=get_back_to_payments_button()
        )
        return
    
    text = "⏳ <b>Ожидающие платежи:</b>\n\n"
    
    for payment in payments[:10]:  # Ограничим 10 платежами
        text += (
            f"💰 <b>Платеж #{payment.id}</b>\n"
            f"👤 Пользователь ID: {payment.user_id}\n"
            f"💳 Сумма: {payment.amount}₽\n"
            f"📅 Создан: {payment.created_at.strftime('%d.%m.%Y %H:%M')}\n"
        )
        
        if payment.comment:
            text += f"💬 Комментарий: {payment.comment}\n"
        
        text += "\n"
    
    if len(payments) > 10:
        text += f"\n<i>И еще {len(payments) - 10} платежей...</i>"
    
    await callback.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=get_admin_payments_menu()
    )


@router.callback_query(F.data.startswith("confirm_payment_"))
async def confirm_payment(callback: CallbackQuery, session: AsyncSession):
    """Подтвердить платеж"""
    payment_id = int(callback.data.replace("confirm_payment_", ""))
    
    success = await update_payment_status(
        session,
        payment_id,
        "completed",
        "Подтверждено менеджером"
    )
    
    if success:
        # Получаем информацию о платеже
        payment = await get_payment_by_id(session, payment_id)
        
        if payment:
            # Отправляем уведомление пользователю
            try:
                await callback.bot.send_message(
                    payment.user_id,
                    f"✅ Ваш платеж #{payment_id} подтвержден!\n\n"
                    f"💰 Сумма: {payment.amount}₽ зачислена на баланс."
                )
            except Exception as e:
                print(f"Не удалось отправить уведомление: {e}")
        
        await callback.answer(f"✅ Платеж #{payment_id} подтвержден!", show_alert=True)
        await show_pending_payments(callback, session)
    else:
        await callback.answer("❌ Ошибка при подтверждении платежа", show_alert=True)


@router.callback_query(F.data.startswith("reject_payment_"))
async def reject_payment(callback: CallbackQuery, state: FSMContext):
    """Отклонить платеж"""
    payment_id = int(callback.data.replace("reject_payment_", ""))
    
    await state.set_state(PaymentComment.waiting_for_comment)
    await state.update_data(payment_id=payment_id, action="reject")
    
    await callback.message.edit_text(
        f"💬 <b>Введите причину отказа для платежа #{payment_id}:</b>",
        parse_mode="HTML",
        reply_markup=get_back_to_payments_button()
    )


@router.message(PaymentComment.waiting_for_comment)
async def process_payment_comment(message: Message, state: FSMContext, session: AsyncSession):
    """Обработка комментария к платежу"""
    data = await state.get_data()
    payment_id = data.get("payment_id")
    action = data.get("action")
    comment = message.text
    
    if action == "reject":
        success = await update_payment_status(
            session,
            payment_id,
            "rejected",
            f"Отклонено: {comment}"
        )
        
        if success:
            await message.answer(
                f"✅ Платеж #{payment_id} отклонен с комментарием.",
                reply_markup=get_back_to_payments_button()
            )
        else:
            await message.answer("❌ Ошибка при отклонении платежа")
    elif action == "comment":
        payment = await get_payment_by_id(session, payment_id)
        if payment:
            payment.comment = comment
            await session.commit()
            await message.answer(
                f"✅ Комментарий добавлен к платежу #{payment_id}",
                reply_markup=get_back_to_payments_button()
            )
    
    await state.clear()


@router.callback_query(F.data == "admin_completed_payments")
async def show_completed_payments(callback: CallbackQuery, session: AsyncSession):
    """Показать завершенные платежи"""
    payments = await get_completed_payments(session, limit=20)
    
    if not payments:
        await callback.message.edit_text(
            "✅ <b>Завершенные платежи</b>\n\nНет завершенных платежей.",
            parse_mode="HTML",
            reply_markup=get_back_to_payments_button()
        )
        return
    
    text = "✅ <b>Завершенные платежи:</b>\n\n"
    
    total_amount = 0
    for payment in payments:
        completed_time = payment.completed_at.strftime('%d.%m.%Y %H:%M') if payment.completed_at else "N/A"
        text += (
            f"💰 <b>Платеж #{payment.id}</b>\n"
            f"👤 Пользователь ID: {payment.user_id}\n"
            f"💳 Сумма: {payment.amount}₽\n"
            f"📅 Завершен: {completed_time}\n"
        )
        
        if payment.comment:
            text += f"💬 Комментарий: {payment.comment}\n"
        
        text += "\n"
        total_amount += payment.amount
    
    text += f"\n📊 <b>Итого:</b> {len(payments)} платежей на сумму {total_amount}₽"
    
    await callback.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=get_back_to_payments_button()
    )