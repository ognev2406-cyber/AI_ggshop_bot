from aiogram import Router

# Создаем главный роутер
router = Router()

# Импортируем все роутеры
from .start import router as start_router
from .products import router as products_router
from .admin import router as admin_router
from .audio import router as audio_router
from .balance import router as balance_router
from .orders import router as orders_router

# Включаем все роутеры
router.include_router(start_router)
router.include_router(products_router)
router.include_router(admin_router)
router.include_router(audio_router)
router.include_router(balance_router)
router.include_router(orders_router)

__all__ = ['router']