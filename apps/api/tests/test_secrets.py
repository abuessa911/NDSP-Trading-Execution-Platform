from pathlib import Path

import pytest

from nex_api.secrets import EnvironmentSecretProvider, MountedFileSecretProvider


def test_environment_secret_provider_returns_value_without_logging(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("NEX_TEST_SECRET", "private-value")
    provider = EnvironmentSecretProvider()

    assert provider.get("NEX_TEST_SECRET") == "private-value"
    assert provider.get("NEX_MISSING_SECRET") is None


def test_mounted_secret_provider_reads_only_files_within_root(tmp_path: Path) -> None:
    (tmp_path / "OIDC_CLIENT_SECRET").write_text("value\n", encoding="utf-8")
    provider = MountedFileSecretProvider(str(tmp_path))

    assert provider.get("OIDC_CLIENT_SECRET") == "value"
    assert provider.get("MISSING") is None
    with pytest.raises(ValueError):
        provider.get("../outside")


def test_secret_name_rejects_path_separators(tmp_path: Path) -> None:
    provider = MountedFileSecretProvider(str(tmp_path))

    with pytest.raises(ValueError):
        provider.get("..%2fsecret")