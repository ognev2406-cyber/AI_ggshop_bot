from common_imports import *
from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
import sqlalchemy

from database import User, Payment
from keyboards import get_balance_menu, get_topup_amounts_menu
from config import BOT_TOKEN, ADMIN_ID, DATABASE_URL, PRICE_CONFIG
from payments import create_yookassa_payment  # или другая платежка

router = Router()

@router.callback_query(F.data == "balance")
async def show_balance(callback: types.CallbackQuery, session: AsyncSession):
    result = await session.execute(
        sqlalchemy.select(User).where(User.telegram_id == callback.from_user.id)
    )
    user = result.scalar_one_or_none()
    
    if user:
        await callback.message.edit_text(
            f"💰 <b>Ваш баланс:</b> {user.balance}₽\n\n"
            f"Выберите действие:",
            reply_markup=get_balance_menu()
        )
    await callback.answer()

@router.callback_query(F.data == "topup_balance")
async def topup_balance(callback: types.CallbackQuery):
    await callback.message.edit_text(
        "💳 <b>Пополнение баланса</b>\n\n"
        "Выберите сумму для пополнения:",
        reply_markup=get_topup_amounts_menu()
    )
    await callback.answer()

@router.callback_query(F.data.startswith("topup:"))
async def process_topup(callback: types.CallbackQuery, session: AsyncSession):
    amount = float(callback.data.split(":")[1])
    
    # Создаем платеж
    payment_data = await create_yookassa_payment(
        amount=amount,
        description=f"Пополнение баланса на {amount}₽",
        user_id=callback.from_user.id
    )
    
    if payment_data:
        # Сохраняем платеж в БД
        payment = Payment(
            user_id=callback.from_user.id,
            amount=amount,
            status="pending",
            provider="yookassa",
            provider_payment_id=payment_data["payment_id"]
        )
        session.add(payment)
        await session.commit()
        
        # Показываем ссылку для оплаты
        await callback.message.edit_text(
            f"💳 <b>Оплата {amount}₽</b>\n\n"
            f"Для оплаты перейдите по ссылке:\n"
            f"{payment_data['payment_url']}\n\n"
            f"После оплаты баланс пополнится автоматически в течение 1-5 минут.\n"
            f"ID платежа: {payment_data['payment_id']}"
        )
    else:
        await callback.message.answer("❌ Ошибка создания платежа")
    
    await callback.answer()