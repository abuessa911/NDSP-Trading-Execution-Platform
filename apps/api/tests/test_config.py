import pytest
from pydantic import ValidationError

from nex_api.config import Settings


def test_safe_trading_configuration_is_the_only_accepted_configuration() -> None:
    settings = Settings(_env_file=None)

    assert settings.trading_safety == {
        "trading_mode": "paper",
        "live_trading_enabled": False,
        "global_kill_switch": True,
        "binance_allow_withdraw": False,
    }


@pytest.mark.parametrize(
    "override",
    [
        {"trading_mode": "live"},
        {"live_trading_enabled": True},
        {"global_kill_switch": False},
        {"binance_allow_withdraw": True},
    ],
)
def test_unsafe_configuration_fails_closed(override: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        Settings(_env_file=None, **override)