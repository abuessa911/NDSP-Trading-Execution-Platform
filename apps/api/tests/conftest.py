import pytest


@pytest.fixture(autouse=True)
def isolate_configuration_from_workspace(monkeypatch):
    """Tests never consume workspace/external connection or provider settings."""
    for name in (
        "DATABASE_URL", "MIGRATION_DATABASE_URL", "REDIS_URL",
        "OIDC_ISSUER", "OIDC_AUDIENCE", "OIDC_JWKS_URL", "OIDC_ALLOWED_ALGORITHM",
        "SECRET_PROVIDER", "SECRETS_DIRECTORY",
        "OIDC_BROWSER_LOGIN_ENABLED", "OIDC_CLIENT_ID", "OIDC_CLIENT_SECRET",
        "OIDC_REDIRECT_URI", "OIDC_POST_LOGOUT_REDIRECT_URI",
        "NEX_SESSION_ENCRYPTION_KEY", "NEX_SESSION_SECONDS",
    ):
        monkeypatch.delenv(name, raising=False)