from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "NDSP Binance Trading Bot"
    ENV: str = "dev"

    DATABASE_URL: str

    SECRET_KEY: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440
    FERNET_KEY: str

    INVITE_CODE: str | None = None

    BINANCE_MODE: str = "dryrun"

    NDSP_WEBHOOK_SECRET: str | None = None

    TELEGRAM_BOT_TOKEN: str | None = None
    TELEGRAM_CHAT_ID: str | None = None

    SMTP_HOST: str | None = None
    SMTP_PORT: int = 587
    SMTP_USER: str | None = None
    SMTP_PASSWORD: str | None = None
    EMAIL_FROM: str | None = None

    class Config:
        env_file = ".env"


settings = Settings()
