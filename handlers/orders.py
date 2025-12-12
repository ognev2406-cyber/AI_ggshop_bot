from aiogram import Router, F
from aiogram.types import CallbackQuery
from sqlalchemy import select
from database import Order
from keyboards import get_back_button

router = Router()


@router.callback_query(F.data == "orders")
async def show_orders(callback: CallbackQuery, user, session):
    """Показать заказы пользователя"""
    result = await session.execute(
        select(Order)
        .where(Order.user_id == user.id)
        .order_by(Order.created_at.desc())
        .limit(10)
    )
    orders = result.scalars().all()
    
    if not orders:
        await callback.message.edit_text(
            "📦 <b>Мои заказы</b>\n\n"
            "У вас еще нет заказов.\n"
            "Создайте первый заказ в разделе генерации текста!",
            parse_mode="HTML",
            reply_markup=get_back_button()
        )
        return
    
    text = "📦 <b>Мои последние заказы:</b>\n\n"
    
    for order in orders:
        text += (
            f"🆔 <b>Заказ #{order.id}</b>\n"
            f"📝 <b>Тип:</b> {order.product_type} - {order.product_subtype}\n"
            f"💰 <b>Стоимость:</b> {order.cost}₽\n"
            f"📅 <b>Дата:</b> {order.created_at.strftime('%d.%m.%Y %H:%M')}\n"
        )
        
        if order.prompt:
            prompt_preview = order.prompt[:50] + "..." if len(order.prompt) > 50 else order.prompt
            text += f"📋 <b>Запрос:</b> {prompt_preview}\n"
        
        text += "\n"
    
    await callback.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=get_back_button()
    )