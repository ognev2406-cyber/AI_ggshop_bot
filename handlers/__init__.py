from aiogram import Router

from .start import router as start_router
from .products import router as products_router
from .admin import router as admin_router
from .admin_payments import router as admin_payments_router
from .ad_handlers import router as ad_router
from .balance import router as balance_router
from .orders import router as orders_router
from .audio_handlers import router as audio_router
from .openai_handlers import router as openai_handlers_router
from .image_handlers import router as image_handlers_router  # Новый импорт
from .debug import router as debug_router

router = Router()

router.include_router(start_router)
router.include_router(products_router)
router.include_router(admin_router)
router.include_router(admin_payments_router)
router.include_router(ad_router)
router.include_router(balance_router)
router.include_router(orders_router)
router.include_router(audio_router)
router.include_router(openai_handlers_router)
router.include_router(image_handlers_router)  # Добавляем новый роутер
router.include_router(debug_router)
