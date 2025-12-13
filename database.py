# database.py - исправленный класс User (обратите внимание на отступы!)
from datetime import datetime, timezone
from sqlalchemy import DateTime
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base, Mapped, mapped_column, relationship
from sqlalchemy import Integer, String, Boolean, DateTime, Text, Float, select, func, ForeignKey
from datetime import datetime
import pytz
from typing import Optional, List
import logging

from config import DATABASE_URL

logger = logging.getLogger(__name__)

# Создаем базовый класс для моделей
Base = declarative_base()

# Создаем движок и сессию
engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class User(Base):
    __tablename__ = 'users'
    __table_args__ = {'extend_existing': True}
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    telegram_id: Mapped[int] = mapped_column(Integer, unique=True, nullable=False)
    username: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    first_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    last_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    balance: Mapped[float] = mapped_column(Float, default=0.0)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    last_active = Column(DateTime(timezone=True), nullable=True)
    last_ad_watch = Column(DateTime(timezone=True), nullable=True)
    last_free_payment = Column(DateTime(timezone=True), nullable=True)
    free_trials_used = Column(Integer, default=0, nullable=False)
    
    # Отношения
    payments: Mapped[List["Payment"]] = relationship("Payment", back_populates="user")
    orders: Mapped[List["Order"]] = relationship("Order", back_populates="user")


class Order(Base):
    __tablename__ = "orders"
    __table_args__ = {'extend_existing': True} 
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"))
    product_type: Mapped[str] = mapped_column(String(50), nullable=False)
    product_subtype: Mapped[str] = mapped_column(String(50), nullable=False)
    prompt: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    result: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    cost: Mapped[float] = mapped_column(Float, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="completed")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(pytz.UTC))
    
    # Отношения
    user: Mapped["User"] = relationship("User", back_populates="orders")


class Payment(Base):
    __tablename__ = "payments"
    __table_args__ = {'extend_existing': True}
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"))
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    currency: Mapped[str] = mapped_column(String(10), default="RUB")
    provider_payment_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    payment_method: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    comment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(pytz.UTC))
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # Отношения
    user: Mapped["User"] = relationship("User", back_populates="payments")


async def init_db():
    """Инициализация базы данных"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("База данных инициализирована")


async def init_db():
    """Инициализация базы данных"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("База данных инициализирована")


async def get_or_create_user(
    session: AsyncSession,
    telegram_id: int,
    username: Optional[str] = None,
    first_name: Optional[str] = None,
    last_name: Optional[str] = None
) -> User:
    """Получить или создать пользователя"""
    result = await session.execute(
        select(User).where(User.telegram_id == telegram_id)
    )
    user = result.scalar_one_or_none()
    
    if user is None:
        user = User(
            telegram_id=telegram_id,
            username=username,
            first_name=first_name,
            last_name=last_name,
            balance=0.0,
            free_trials_used=0,
            is_admin=False
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        logger.info(f"Создан новый пользователь: {telegram_id}")
    else:
        user.last_active = datetime.now(pytz.UTC)
        await session.commit()
    
    return user


async def get_pending_payments(session: AsyncSession, limit: int = 50):
    """Получить список ожидающих платежей"""
    result = await session.execute(
        select(Payment)
        .where(Payment.status == "pending")
        .order_by(Payment.created_at.desc())
        .limit(limit)
    )
    return result.scalars().all()


async def get_completed_payments(session: AsyncSession, limit: int = 50):
    """Получить список завершенных платежей"""
    result = await session.execute(
        select(Payment)
        .where(Payment.status == "completed")
        .order_by(Payment.completed_at.desc())
        .limit(limit)
    )
    return result.scalars().all()


async def get_payment_by_id(session: AsyncSession, payment_id: int):
    """Получить платеж по ID"""
    result = await session.execute(
        select(Payment).where(Payment.id == payment_id)
    )
    return result.scalar_one_or_none()


async def update_payment_status(
    session: AsyncSession, 
    payment_id: int, 
    status: str,
    comment: str = None
) -> bool:
    """Обновить статус платежа"""
    result = await session.execute(
        select(Payment).where(Payment.id == payment_id)
    )
    payment = result.scalar_one_or_none()
    
    if payment:
        payment.status = status
        if comment:
            payment.comment = comment
        
        if status == "completed":
            # Находим пользователя и пополняем баланс
            user_result = await session.execute(
                select(User).where(User.id == payment.user_id)
            )
            user = user_result.scalar_one_or_none()
            if user:
                user.balance += payment.amount
                payment.completed_at = datetime.now(pytz.UTC)
        
        await session.commit()
        logger.info(f"Статус платежа {payment_id} обновлен на '{status}'")
        return True
    
    return False


async def get_pending_payments_for_user(session: AsyncSession, user_id: int):
    """Получить ожидающие платежи пользователя"""
    result = await session.execute(
        select(Payment)
        .where(Payment.user_id == user_id, Payment.status == "pending")
        .order_by(Payment.created_at.desc())
    )
    return result.scalars().all()
