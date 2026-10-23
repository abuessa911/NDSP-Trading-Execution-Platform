from pathlib import Path
from unittest.mock import patch

import pytest

from nex_api.hunter_live_executor import (
    Exchange,
    Halt,
    execute_once,
)


def test_emergency_stop_blocks_post():
    with patch.object(Path, "exists", return_value=True):
        exchange = object.__new__(Exchange)
        exchange.mode = "testnet"

        with pytest.raises(Halt, match="EMERGENCY_STOP_ACTIVE"):
            exchange.signed_post(
                "/fapi/v1/order",
                symbol="DOGEUSDT",
            )


def test_emergency_stop_blocks_delete():
    with patch.object(Path, "exists", return_value=True):
        exchange = object.__new__(Exchange)
        exchange.mode = "testnet"

        with pytest.raises(Halt, match="EMERGENCY_STOP_ACTIVE"):
            exchange.signed_delete(
                "/fapi/v1/algoOrder",
                algoId=123,
            )


def test_mainnet_write_is_blocked(tmp_path):
    class FakeExchange:
        mode = "mainnet"

    with patch.object(Path, "exists", return_value=False):
        with pytest.raises(
            Halt,
            match="MAINNET_ORDER_WRITES_NOT_RELEASED",
        ):
            execute_once(
                {"symbol": "DOGEUSDT"},
                tmp_path / "state.json",
                FakeExchange(),
                allow_write=True,
            )


def test_stop_blocks_before_account_read(tmp_path):
    class FakeExchange:
        mode = "testnet"

    with patch.object(Path, "exists", return_value=True):
        with pytest.raises(Halt, match="EMERGENCY_STOP_ACTIVE"):
            execute_once(
                {"symbol": "DOGEUSDT"},
                tmp_path / "state.json",
                FakeExchange(),
                allow_write=True,
            )
