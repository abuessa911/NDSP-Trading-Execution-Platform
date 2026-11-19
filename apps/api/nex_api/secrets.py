import os
from pathlib import Path
from typing import Protocol

from nex_api.config import Settings


class SecretProvider(Protocol):
    def get(self, name: str) -> str | None: ...


def _validate_name(name: str) -> None:
    if not name or len(name) > 128 or any(
        character not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-"
        for character in name
    ):
        raise ValueError("Secret names may contain only letters, digits, '_' and '-'.")


class EnvironmentSecretProvider:
    def get(self, name: str) -> str | None:
        _validate_name(name)
        value = os.environ.get(name)
        return value if value else None


class MountedFileSecretProvider:
    def __init__(self, directory: str) -> None:
        self.directory = Path(directory).resolve(strict=True)
        if not self.directory.is_dir():
            raise ValueError("The configured secrets path is not a directory.")

    def get(self, name: str) -> str | None:
        _validate_name(name)
        candidate = (self.directory / name).resolve(strict=False)
        try:
            candidate.relative_to(self.directory)
        except ValueError as error:
            raise ValueError("Secret path escapes the configured secrets directory.") from error
        if not candidate.exists():
            return None
        if not candidate.is_file():
            raise ValueError("Mounted secrets must be regular files.")
        if candidate.stat().st_size > 65536:
            raise ValueError("Mounted secret exceeds the 64 KiB limit.")
        value = candidate.read_text(encoding="utf-8").rstrip("\r\n")
        return value if value else None


def build_secret_provider(settings: Settings) -> SecretProvider:
    if settings.secret_provider == "file":
        return MountedFileSecretProvider(settings.secrets_directory)
    return EnvironmentSecretProvider()


def resolve_configuration(settings: Settings, provider: SecretProvider) -> Settings:
    """Operational secret delivery, including mounted database/Redis URLs.

    Env Settings already reads environment configuration. File mode never falls
    back to env connection URLs: missing mounted secrets fail closed.
    """
    values = {}
    for name in ("database_url", "migration_database_url", "redis_url",
                 "oidc_client_secret", "oidc_admin_mfa_client_secret", "nex_session_encryption_key"):
        value = provider.get(name.upper())
        # Explicit Settings (including operator/test constructors) must win over
        # ambient environment. Never redirect an isolated test to another DB.
        values[name] = value if settings.secret_provider == "file" else (
            getattr(settings, name) if name in settings.model_fields_set else value
        )
    configured = Settings.model_validate(settings.model_dump() | values)
    if configured.oidc_browser_login_enabled and not configured.nex_session_encryption_key:
        raise ValueError("Browser session encryption key missing from configured secret provider.")
    return configured