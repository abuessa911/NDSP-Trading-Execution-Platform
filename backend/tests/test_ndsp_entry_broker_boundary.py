"""Offline HTTP contract with source handlers, real execution function and fake exchange.

Load the specific handler definitions in isolation so database startup, credentials,
network transports and alert integrations cannot be initialized by module imports.
Run with python backend/tests/test_ndsp_entry_broker_boundary.py.
"""
import ast
import json
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock

from fastapi import APIRouter, Depends, FastAPI, Header, HTTPException
from fastapi.testclient import TestClient
from pydantic import BaseModel, ConfigDict

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))
from app.services.ndsp_decision_interpreter import interpret_ndsp_payload


def source_definitions(relative_path, names):
    path = BACKEND / "app" / relative_path
    tree = ast.parse(path.read_text(encoding="utf-8"))
    tree.body = [node for node in tree.body if getattr(node, "name", None) in names]
    if {node.name for node in tree.body} != names:
        raise RuntimeError(f"Missing contract dependency in {relative_path}")
    exec(compile(tree, str(path), "exec"), globals())


router = APIRouter()
Session = Any
User = MagicMock()
settings = SimpleNamespace(BINANCE_MODE="dryrun", NDSP_WEBHOOK_SECRET="local-fixture")
broker = MagicMock()
BinanceClient = MagicMock(return_value=broker)
broker.market_order_by_notional.return_value = {"status": "simulated", "amount": 1, "price": 100}
pre_trade_risk_check = MagicMock()
validate_trade = MagicMock(return_value=(True, "fixture"))
normalize_symbol = normalize_market_type = str
database = MagicMock()


def TradeLog(**values):
    return SimpleNamespace(id=1, **values)


def get_current_user():
    return SimpleNamespace(id=1, is_active=True, settings=None, email="test@example.invalid")


def get_db():
    database.query.return_value.filter.return_value.first.return_value = get_current_user()
    return database


source_definitions("schemas/schemas.py", {"NdspSignalRequest"})
source_definitions("services/execution.py", {"execute_signal", "calculate_protective_prices"})
source_definitions("api/advanced_routes.py", {
    "NdspWebhookSignalRequest", "ndsp_signal", "ndsp_webhook_signal",
    "_payload_dict", "_payload_reason", "_payload_symbol", "_interpret_entry",
})
app = FastAPI()
app.include_router(router)


class BrokerBoundaryTest(unittest.TestCase):
    def test_unsigned_ready_decision_never_leaves_simulation(self):
        from unittest.mock import patch

        with TestClient(app) as http:
            for mode in ("testnet", "live", "unknown"):
                for path in ("/ndsp/signal", "/webhooks/ndsp-signal"):
                    with self.subTest(mode=mode, path=path), patch.object(settings, "BINANCE_MODE", mode):
                        broker.reset_mock()
                        database.reset_mock()
                        pre_trade_risk_check.reset_mock()
                        document = {"direction": "bullish", "confidence": 90,
                                    "single_truth_state": "READY", "allowed": True}
                        response = http.post(path, json={"symbol": "BTC/USDT", "decision": document,
                            "user_email": get_current_user().email},
                            headers={"X-NDSP-SECRET": "local-fixture"})
                        self.assertEqual(response.status_code, 200)
                        self.assertEqual(response.json()["action"], "NO_TRADE")
                        broker.market_order_by_notional.assert_not_called()
                        pre_trade_risk_check.assert_not_called()
                        database.add.assert_not_called()

    def test_entry_contract(self):
        baseline = {"direction": "bullish", "confidence": 90}
        cases = [
            ("monitor", {"single_truth_state": "MONITORING_ONLY", "allowed": False}, False),
            ("blocked", {"single_truth_state": "BLOCKED_BY_DEVILS_ADVOCATE", "allowed": False}, False),
            ("missing", {}, False),
            ("unknown", {"single_truth_state": "UNKNOWN", "allowed": True}, False),
            ("contradiction", {"single_truth_state": "READY", "allowed": False}, False),
            ("text permission", {"single_truth_state": "READY", "allowed": "true"}, False),
            ("control", {"single_truth_state": "READY", "allowed": True}, True),
        ]
        with TestClient(app) as http:
            for path in ("/ndsp/signal", "/webhooks/ndsp-signal"):
                for name, fields, permitted in cases:
                    with self.subTest(path=path, case=name):
                        broker.reset_mock()
                        database.reset_mock()
                        pre_trade_risk_check.reset_mock()
                        payload = {"symbol": "BTC/USDT", "decision": {**baseline, **fields}}
                        if path.startswith("/webhooks"):
                            payload["user_email"] = get_current_user().email
                        response = http.post(path, json=payload, headers={"X-NDSP-SECRET": "local-fixture"})
                        self.assertEqual(response.status_code, 200)
                        self.assertEqual(response.json()["action"], "BUY" if permitted else "NO_TRADE")
                        self.assertEqual(pre_trade_risk_check.call_count, int(permitted))
                        self.assertEqual(broker.market_order_by_notional.call_count, int(permitted))
                        self.assertEqual(database.add.call_count, int(permitted))


if __name__ == "__main__":
    unittest.main()
