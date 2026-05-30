from sqlalchemy import String, Integer, Float, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
from app.db.session import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    api_key = relationship("BinanceApiKey", back_populates="user", uselist=False)
    settings = relationship("BotSettings", back_populates="user", uselist=False)
    trades = relationship("TradeLog", back_populates="user")


class BinanceApiKey(Base):
    __tablename__ = "binance_api_keys"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True)
    api_key_encrypted: Mapped[str] = mapped_column(Text)
    api_secret_encrypted: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="api_key")


class BotSettings(Base):
    __tablename__ = "bot_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True)

    enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    allowed_symbols: Mapped[str] = mapped_column(String(500), default="BTC/USDT,ETH/USDT")
    market_type: Mapped[str] = mapped_column(String(20), default="spot")
    max_order_usdt: Mapped[float] = mapped_column(Float, default=25.0)
    max_daily_loss_usdt: Mapped[float] = mapped_column(Float, default=20.0)
    max_trades_per_day: Mapped[int] = mapped_column(Integer, default=3)
    stop_loss_pct: Mapped[float] = mapped_column(Float, default=0.0)
    take_profit_pct: Mapped[float] = mapped_column(Float, default=0.0)
    prevent_duplicate_positions: Mapped[bool] = mapped_column(Boolean, default=True)
    live_safety_confirmed: Mapped[bool] = mapped_column(Boolean, default=False)

    telegram_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    email_enabled: Mapped[bool] = mapped_column(Boolean, default=True)

    user = relationship("User", back_populates="settings")


class TradeLog(Base):
    __tablename__ = "trade_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))

    symbol: Mapped[str] = mapped_column(String(50))
    side: Mapped[str] = mapped_column(String(10))
    amount: Mapped[float] = mapped_column(Float)
    price: Mapped[float] = mapped_column(Float, default=0)
    notional_usdt: Mapped[float] = mapped_column(Float, default=0)
    pnl_usdt: Mapped[float] = mapped_column(Float, default=0.0)
    stop_loss_price: Mapped[float] = mapped_column(Float, default=0.0)
    take_profit_price: Mapped[float] = mapped_column(Float, default=0.0)
    protective_orders_status: Mapped[str] = mapped_column(String(50), default="preview")

    status: Mapped[str] = mapped_column(String(50))
    mode: Mapped[str] = mapped_column(String(20))
    reason: Mapped[str] = mapped_column(Text, default="")
    exchange_response: Mapped[str] = mapped_column(Text, default="")

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="trades")
