import logging

from nex_api.audit import sanitize_metadata
from nex_api.logging import LibraryRedaction, redact_event
from nex_api.config import Settings
from nex_api.secrets import MountedFileSecretProvider, resolve_configuration


def test_metadata_drops_sensitive_payloads():
    assert sanitize_metadata({
        "authorization": "Bearer secret", "password": "secret", "ip": "192.0.2.1",
        "user_agent": "sensitive", "returned": 3, "role": "Bearer secret",
        "status_code": {"token": "secret"}, "operation": "secret",
    }) == {"returned": 3}


def test_library_logs_and_exceptions_are_redacted():
    record = logging.LogRecord("sqlalchemy.engine", logging.ERROR, "", 1,
                               "postgres://user:secret@db", (), None)
    record.exc_text = "secret"
    LibraryRedaction().filter(record)
    assert "secret" not in record.getMessage()
    assert record.exc_text is None
    result = redact_event(None, "", {"event": "Bearer secret", "password": "secret",
                                     "exc_info": "secret"})
    assert "secret" not in str(result)


def test_file_provider_is_used_for_configuration(tmp_path):
    (tmp_path / "DATABASE_URL").write_text("postgresql://synthetic-test-value")
    settings = resolve_configuration(
        Settings(_env_file=None, secret_provider="file",
                 secrets_directory=str(tmp_path), redis_url="redis://must-not-fallback"),
        MountedFileSecretProvider(str(tmp_path)),
    )
    assert settings.database_url == "postgresql://synthetic-test-value"
    assert settings.redis_url is None


def test_explicit_database_target_wins_over_ambient_configuration(monkeypatch):
    from nex_api.secrets import EnvironmentSecretProvider
    monkeypatch.setenv("DATABASE_URL", "postgresql://must-not-use-ambient")
    settings = Settings(_env_file=None, database_url="postgresql://isolated")
    resolved = resolve_configuration(settings, EnvironmentSecretProvider())
    assert resolved.database_url == "postgresql://isolated"