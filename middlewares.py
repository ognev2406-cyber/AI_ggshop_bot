from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery, Update
from typing import Callable, Dict, Any, Awaitable, Union
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_or_create_user, AsyncSessionLocal


class DatabaseMiddleware(BaseMiddleware):
    """Middleware для работы с базой данных"""
    
    async def __call__(
        self,
        handler: Callable[[Update, Dict[str, Any]], Awaitable[Any]],
        event: Update,
        data: Dict[str, Any]
    ) -> Any:
        # Определяем тип события и получаем пользователя
        user_data = None
        
        if hasattr(event, 'message') and event.message:
            # Для CallbackQuery
            user_data = event.message.from_user if event.message.from_user else None
        elif hasattr(event, 'from_user'):
            # Для Message и других событий с from_user
            user_data = event.from_user
        elif hasattr(event, 'callback_query') and event.callback_query:
            # Для Update с callback_query
            user_data = event.callback_query.from_user
        
        if not user_data:
            # Если не смогли определить пользователя, пропускаем
            return await handler(event, data)
        
        async with AsyncSessionLocal() as session:
            # Получаем или создаем пользователя в БД
            user = await get_or_create_user(
                session=session,
                telegram_id=user_data.id,
                username=user_data.username,
                first_name=user_data.first_name,
                last_name=user_data.last_name
            )
            
            # Проверяем, является ли пользователь администратором
            from config import ADMIN_IDS
            if user.telegram_id in ADMIN_IDS and not user.is_admin:
                user.is_admin = True
                await session.commit()
            
            # Добавляем сессию и пользователя в data
            data["session"] = session
            data["user"] = user
            
            # Вызываем обработчик
            result = await handler(event, data)
            
            # Коммитим изменения
            await session.commit()
            
            return result


def register_middlewares(dp):
    """Регистрация всех middleware"""
    dp.update.middleware(DatabaseMiddleware())
