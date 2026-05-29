from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    invite_code: str | None = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class BinanceKeyRequest(BaseModel):
    api_key: str
    api_secret: str


class BotSettingsRequest(BaseModel):
    enabled: bool = False
    allowed_symbols: str = "BTC/USDT,ETH/USDT"
    max_order_usdt: float = 25.0
    max_daily_loss_usdt: float = 20.0
    max_trades_per_day: int = 3
    stop_loss_pct: float = 0.0
    take_profit_pct: float = 0.0
    prevent_duplicate_positions: bool = True
    telegram_enabled: bool = True
    email_enabled: bool = True


class TestSignalRequest(BaseModel):
    symbol: str = "BTC/USDT"
    side: str = "BUY"
    notional_usdt: float = 10.0
    reason: str = "manual test signal"


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str = Field(min_length=8)


class NdspSignalRequest(BaseModel):
    symbol: str
    side: str
    notional_usdt: float
    reason: str = "NDSP signal"
    ndsp_layer: str | None = None


class LiveSafetyConfirmRequest(BaseModel):
    confirm_text: str
