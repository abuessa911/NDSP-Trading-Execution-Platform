"""Isolated execution-safety prototype. No exchange order submission."""

import base64
import json
import sqlite3
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path
from urllib.parse import urlencode

from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
)

class SafetyHalt(RuntimeError):
    pass


def number(value):
    try:
        result = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        raise SafetyHalt("INVALID_NUMBER") from None

    if not result.is_finite():
        raise SafetyHalt("INVALID_NUMBER")
    return result


@dataclass(frozen=True)
class RiskSnapshot:
    opening_equity: str
    current_equity: str
    daily_limit_pct: str
    account_verified: bool
    utc_day: str


def verify_risk(snapshot):
    if not snapshot.account_verified:
        raise SafetyHalt("ACCOUNT_NOT_VERIFIED")

    opening = number(snapshot.opening_equity)
    current = number(snapshot.current_equity)
    limit = number(snapshot.daily_limit_pct)

    if opening <= 0 or current <= 0:
        raise SafetyHalt("INVALID_EQUITY")

    if not 0 < limit <= 100:
        raise SafetyHalt("INVALID_RISK_PERCENT")

    if not snapshot.utc_day:
        raise SafetyHalt("UTC_DAY_REQUIRED")

    loss = max(Decimal("0"), opening - current)
    budget = opening * limit / Decimal("100")

    if loss >= budget:
        raise SafetyHalt("DAILY_LOSS_LIMIT_REACHED")

    return {
        "loss": str(loss),
        "budget": str(budget),
        "remaining": str(budget - loss),
    }


class DurableOrderLedger:
    """Fail-closed idempotency ledger.

    Reserved order IDs remain reserved after crashes.
    No automatic retry of ambiguous submissions.
    """

    def __init__(self, path):
        path = Path(path)
        if path.exists() and path.is_symlink():
            raise SafetyHalt("LEDGER_SYMLINK_FORBIDDEN")

        path.parent.mkdir(parents=True, exist_ok=True)
        self.path = path

        with sqlite3.connect(self.path) as db:
            db.execute("""
                CREATE TABLE IF NOT EXISTS orders (
                    order_id TEXT PRIMARY KEY,
                    utc_day TEXT NOT NULL,
                    status TEXT NOT NULL
                )
            """)

    def reserve(self, order_id, utc_day):
        if not isinstance(order_id, str) or not (
            1 <= len(order_id) <= 64
        ):
            raise SafetyHalt("INVALID_ORDER_ID")

        if not utc_day:
            raise SafetyHalt("UTC_DAY_REQUIRED")

        try:
            with sqlite3.connect(
                self.path, timeout=5, isolation_level="IMMEDIATE"
            ) as db:
                db.execute(
                    """
                    INSERT INTO orders
                    (order_id, utc_day, status)
                    VALUES (?, ?, 'RESERVED')
                    """,
                    (order_id, utc_day),
                )
        except sqlite3.IntegrityError:
            raise SafetyHalt("DUPLICATE_ORDER_BLOCKED") from None
        except sqlite3.Error:
            raise SafetyHalt("LEDGER_UNAVAILABLE") from None


def ed25519_signature(key, parameters):
    """Offline Ed25519 signature; returns no executable HTTP request."""
    if not isinstance(key, Ed25519PrivateKey):
        raise SafetyHalt("INVALID_SIGNER")

    query = urlencode(parameters)
    signature = base64.b64encode(
        key.sign(query.encode("ascii"))
    ).decode("ascii")

    return query, signature


def simulate_order(
    *,
    mode,
    order_id,
    snapshot,
    ledger,
    quantity,
    price,
    max_notional,
):
    # This prototype cannot authorize exchange writes in any mode.
    if mode not in ("dry-run", "testnet-simulation"):
        raise SafetyHalt("REAL_ORDER_EXECUTION_DISABLED")

    risk = verify_risk(snapshot)

    qty = number(quantity)
    market_price = number(price)
    max_value = number(max_notional)

    if qty <= 0 or market_price <= 0 or max_value <= 0:
        raise SafetyHalt("INVALID_ORDER_VALUES")

    notional = qty * market_price

    if notional > max_value:
        raise SafetyHalt("ORDER_NOTIONAL_LIMIT_REACHED")

    ledger.reserve(order_id, snapshot.utc_day)

    return {
        "order_id": order_id,
        "status": "SIMULATED_ONLY",
        "notional": str(notional),
        "risk_remaining": risk["remaining"],
        "real_order_sent": False,
        "execution_enabled": False,
    }
