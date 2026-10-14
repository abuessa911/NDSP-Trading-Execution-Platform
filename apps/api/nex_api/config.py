from functools import lru_cache
from typing import Self
from urllib.parse import urlsplit

from pydantic import SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
        hide_input_in_errors=True,
    )

    environment: str = "development"
    trading_mode: str = "paper"
    live_trading_enabled: bool = False
    global_kill_switch: bool = True
    binance_allow_withdraw: bool = False
    m2a_public_market_enabled: bool = False  # isolated admin-only test gate

    database_url: str | None = None
    migration_database_url: str | None = None
    redis_url: str | None = None

    oidc_issuer: str | None = None
    oidc_audience: str | None = None
    oidc_jwks_url: str | None = None
    oidc_allowed_algorithm: str = "RS256"
    oidc_jwks_cache_seconds: int = 300
    oidc_browser_login_enabled: bool = False
    oidc_client_id: str | None = None
    oidc_client_secret: SecretStr | None = None
    oidc_admin_mfa_policy: str | None = None
    oidc_admin_mfa_client_id: str | None = None
    oidc_admin_mfa_client_secret: SecretStr | None = None
    oidc_admin_mfa_max_age: int = 600
    oidc_redirect_uri: str | None = None
    oidc_post_logout_redirect_uri: str | None = None
    nex_session_encryption_key: SecretStr | None = None
    nex_session_seconds: int = 1800

    secret_provider: str = "env"
    secrets_directory: str = "/run/secrets"

    @model_validator(mode="after")
    def enforce_safety_invariants(self) -> Self:
        if self.environment not in {"development", "test", "production"}:
            raise ValueError("ENVIRONMENT must be development, test, or production.")
        if self.trading_mode != "paper":
            raise ValueError("TRADING_MODE must remain paper in M1.")
        if self.live_trading_enabled:
            raise ValueError("LIVE_TRADING_ENABLED must remain false in M1.")
        if not self.global_kill_switch:
            raise ValueError("GLOBAL_KILL_SWITCH must remain true in M1.")
        if self.binance_allow_withdraw:
            raise ValueError("BINANCE_ALLOW_WITHDRAW must remain false in M1.")
        if self.m2a_public_market_enabled and self.environment != "test":
            raise ValueError("M2A market API is test-only, never production/dev.")
        if self.secret_provider not in {"env", "file"}:
            raise ValueError("SECRET_PROVIDER must be either env or file.")
        if self.oidc_allowed_algorithm not in {"RS256", "ES256"}:
            raise ValueError("OIDC_ALLOWED_ALGORITHM must be RS256 or ES256.")
        if self.oidc_jwks_cache_seconds < 30 or self.oidc_jwks_cache_seconds > 3600:
            raise ValueError("OIDC_JWKS_CACHE_SECONDS must be between 30 and 3600.")
        if not 60 <= self.nex_session_seconds <= 3600:
            raise ValueError("NEX session lifetime must be between 60 and 3600 seconds.")
        if not 60 <= self.oidc_admin_mfa_max_age <= 900:
            raise ValueError("Administrator MFA lifetime must be between 60 and 900 seconds.")
        if self.oidc_admin_mfa_policy is not None:
            # Only this explicitly approved disposable policy has been verified.
            # Production or another issuer needs independent authority/evidence.
            if (self.environment != "test" or not self.oidc_browser_login_enabled
                    or self.oidc_admin_mfa_policy != "keycloak-password-totp-v1"
                    or self.oidc_issuer != "https://localhost:18443/oidc/realms/nex-m1-test"
                    or self.oidc_admin_mfa_client_id != "nex-m1-admin"
                    or (self.secret_provider == "env" and not self.oidc_admin_mfa_client_secret)):
                raise ValueError("Administrator MFA requires the approved isolated provider policy.")
        if self.oidc_browser_login_enabled:
            if (not all((self.oidc_configured, self.oidc_client_id, self.oidc_redirect_uri,
                         self.oidc_post_logout_redirect_uri))
                    or (self.secret_provider == "env" and not self.nex_session_encryption_key)):
                raise ValueError("Browser OIDC requires explicit client, redirects and session key.")
            from cryptography.fernet import Fernet
            if self.nex_session_encryption_key:
                Fernet(self.nex_session_encryption_key.get_secret_value().encode())
            callback = urlsplit(self.oidc_redirect_uri or "")
            logout = urlsplit(self.oidc_post_logout_redirect_uri or "")
            if (urlsplit(self.oidc_issuer or "").scheme != "https"
                    or callback.scheme != "https" or logout.scheme != "https"
                    or callback.netloc != logout.netloc
                    or callback.path != "/api/v1/auth/callback"
                    or callback.query or callback.fragment or logout.query or logout.fragment
                    or callback.username or logout.username):
                raise ValueError("Browser OIDC requires exact same-origin HTTPS redirect URIs.")
        for url in (self.oidc_issuer, self.oidc_jwks_url):
            if not url:
                continue
            parsed = urlsplit(url)
            if not parsed.hostname:
                raise ValueError("OIDC issuer and JWKS values must be absolute URLs.")
            if parsed.username or parsed.query or parsed.fragment:
                raise ValueError("OIDC URLs cannot contain credentials, queries or fragments.")
            local_http = parsed.scheme == "http" and parsed.hostname in {
                "localhost",
                "127.0.0.1",
                "::1",
            }
            if parsed.scheme != "https" and not (
                self.environment != "production" and local_http
            ):
                raise ValueError("OIDC URLs must use HTTPS outside local development.")
        return self

    @property
    def oidc_configured(self) -> bool:
        return bool(self.oidc_issuer and self.oidc_audience and self.oidc_jwks_url)

    @property
    def trading_safety(self) -> dict[str, bool | str]:
        return {
            "trading_mode": self.trading_mode,
            "live_trading_enabled": self.live_trading_enabled,
            "global_kill_switch": self.global_kill_switch,
            "binance_allow_withdraw": self.binance_allow_withdraw,
        }


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()