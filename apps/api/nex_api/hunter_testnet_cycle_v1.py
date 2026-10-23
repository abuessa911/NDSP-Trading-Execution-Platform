"""Hunter USD-M Futures Testnet execution lifecycle.

No mainnet URL, no mainnet credentials and no production route.
Testnet order writes require explicit approval.

A reserved order ID is never silently reused after an error.
"""

import base64
import re
import sqlite3
import time
from decimal import Decimal, InvalidOperation
from pathlib import Path
from urllib.parse import urlencode, quote

import httpx

from nex_api.hunter_execution_safety_v1 import (
    SafetyHalt,
    verify_risk,
)
from nex_api.hunter_live_risk_bridge_v1 import (
    build_verified_snapshot,
)


ORIGIN = "https://demo-fapi.binance.com"

SIGNED_PATHS = {
    ("POST", "/fapi/v1/order"),
    ("GET", "/fapi/v1/order"),
    ("DELETE", "/fapi/v1/order"),
}

PUBLIC_PATHS = {
    "/fapi/v1/exchangeInfo",
    "/fapi/v1/premiumIndex",
}

FINAL_STATES = {
    "FILLED",
    "CANCELED",
    "EXPIRED",
    "EXPIRED_IN_MATCH",
}

ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{1,36}$")
SYMBOL_PATTERN = re.compile(r"^[A-Z0-9]{3,24}$")


def dec(value):
    try:
        x = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        raise SafetyHalt("INVALID_DECIMAL") from None

    if not x.is_finite():
        raise SafetyHalt("INVALID_DECIMAL")
    return x


def validate_symbol(info, symbol):
    if not SYMBOL_PATTERN.fullmatch(symbol):
        raise SafetyHalt("INVALID_SYMBOL")

    matches = [
        row for row in info.get("symbols", [])
        if row.get("symbol") == symbol
    ]

    if len(matches) != 1:
        raise SafetyHalt("SYMBOL_NOT_FOUND")

    row = matches[0]

    if row.get("status") != "TRADING":
        raise SafetyHalt("SYMBOL_NOT_TRADING")

    if row.get("contractType") != "PERPETUAL":
        raise SafetyHalt("NOT_PERPETUAL")

    if row.get("quoteAsset") != "USDT":
        raise SafetyHalt("NOT_USDT_QUOTED")

    filters = {
        f["filterType"]: f
        for f in row.get("filters", [])
        if isinstance(f, dict) and "filterType" in f
    }

    return filters


def validate_limit_order(
    filters,
    *,
    quantity,
    price,
    max_notional,
    mark_price,
):
    qty = dec(quantity)
    px = dec(price)
    cap = dec(max_notional)
    mark = dec(mark_price)

    if min(qty, px, cap, mark) <= 0:
        raise SafetyHalt("NONPOSITIVE_ORDER_VALUE")

    lot = filters.get("LOT_SIZE")
    price_filter = filters.get("PRICE_FILTER")

    if not lot or not price_filter:
        raise SafetyHalt("EXCHANGE_FILTERS_MISSING")

    step = dec(lot["stepSize"])
    tick = dec(price_filter["tickSize"])

    if step <= 0 or tick <= 0:
        raise SafetyHalt("INVALID_EXCHANGE_FILTER")

    if qty % step != 0:
        raise SafetyHalt("QUANTITY_STEP_INVALID")

    if px % tick != 0:
        raise SafetyHalt("PRICE_TICK_INVALID")

    if qty < dec(lot["minQty"]):
        raise SafetyHalt("QUANTITY_BELOW_MIN")

    max_qty = dec(lot["maxQty"])
    if max_qty > 0 and qty > max_qty:
        raise SafetyHalt("QUANTITY_ABOVE_MAX")

    min_price = dec(price_filter["minPrice"])
    max_price = dec(price_filter["maxPrice"])

    if min_price > 0 and px < min_price:
        raise SafetyHalt("PRICE_BELOW_MIN")

    if max_price > 0 and px > max_price:
        raise SafetyHalt("PRICE_ABOVE_MAX")

    notional = qty * px

    if notional > cap:
        raise SafetyHalt("NOTIONAL_CAP_EXCEEDED")

    notional_filter = (
        filters.get("MIN_NOTIONAL")
        or filters.get("NOTIONAL")
        or {}
    )

    min_notional = dec(
        notional_filter.get(
            "notional",
            notional_filter.get("minNotional", "0"),
        )
    )

    if notional < min_notional:
        raise SafetyHalt("NOTIONAL_BELOW_EXCHANGE_MIN")

    # Additional conservative check for the test lifecycle.
    # This is not a substitute for Binance PERCENT_PRICE filters.
    deviation = abs(px - mark) / mark

    if deviation > Decimal("0.05"):
        raise SafetyHalt("PRICE_DEVIATION_TOO_LARGE")

    return str(notional)


class TestnetLedger:
    """Durable reservation and recovery state."""

    def __init__(self, path):
        self.path = Path(path)

        if self.path.is_symlink():
            raise SafetyHalt("LEDGER_SYMLINK_FORBIDDEN")

        self.path.parent.mkdir(
            parents=True, exist_ok=True
        )

        with sqlite3.connect(self.path) as db:
            db.execute("""
                CREATE TABLE IF NOT EXISTS testnet_orders (
                    client_id TEXT PRIMARY KEY,
                    symbol TEXT NOT NULL,
                    state TEXT NOT NULL,
                    created_at INTEGER NOT NULL
                )
            """)

    def reserve(self, client_id, symbol):
        if not ID_PATTERN.fullmatch(client_id):
            raise SafetyHalt("INVALID_CLIENT_ID")

        try:
            with sqlite3.connect(
                self.path, timeout=10
            ) as db:
                db.execute(
                    """
                    INSERT INTO testnet_orders
                    (client_id, symbol, state, created_at)
                    VALUES (?, ?, 'RESERVED', ?)
                    """,
                    (client_id, symbol, int(time.time())),
                )
        except sqlite3.IntegrityError:
            raise SafetyHalt(
                "DUPLICATE_ORDER_BLOCKED"
            ) from None
        except sqlite3.Error:
            raise SafetyHalt(
                "LEDGER_UNAVAILABLE"
            ) from None

    def update(self, client_id, state):
        if state not in (
            "RESERVED",
            "SUBMISSION_UNKNOWN",
            "SUBMITTED",
            "FILLED",
            "CANCELED",
            "EXPIRED",
            "EXPIRED_IN_MATCH",
            "RECONCILE_REQUIRED",
        ):
            raise SafetyHalt("INVALID_LEDGER_STATE")

        try:
            with sqlite3.connect(
                self.path, timeout=10
            ) as db:
                cursor = db.execute(
                    """
                    UPDATE testnet_orders
                    SET state=?
                    WHERE client_id=?
                    """,
                    (state, client_id),
                )
                if cursor.rowcount != 1:
                    raise SafetyHalt(
                        "ORDER_RESERVATION_MISSING"
                    )
        except sqlite3.Error:
            raise SafetyHalt(
                "LEDGER_UNAVAILABLE"
            ) from None

    def state(self, client_id):
        with sqlite3.connect(self.path) as db:
            row = db.execute(
                """
                SELECT state FROM testnet_orders
                WHERE client_id=?
                """,
                (client_id,),
            ).fetchone()
        return row[0] if row else None


class TestnetClient:
    def __init__(
        self,
        api_key,
        private_key,
        *,
        transport=None,
        approved=False,
    ):
        if approved is not True:
            raise SafetyHalt(
                "TESTNET_ORDER_APPROVAL_REQUIRED"
            )

        from cryptography.hazmat.primitives.asymmetric.ed25519 import (
            Ed25519PrivateKey,
        )

        if not api_key or not isinstance(
            private_key, Ed25519PrivateKey
        ):
            raise SafetyHalt("TESTNET_CREDENTIALS_REQUIRED")

        self.key = api_key
        self.signer = private_key
        self.transport = transport

    def _request(
        self,
        method,
        path,
        params=None,
        signed=False,
    ):
        params = dict(params or {})

        if signed:
            if (method, path) not in SIGNED_PATHS:
                raise SafetyHalt("SIGNED_ROUTE_FORBIDDEN")

            params["timestamp"] = int(
                time.time() * 1000
            )
            params["recvWindow"] = 5000

            query = urlencode(params)

            signature = base64.b64encode(
                self.signer.sign(
                    query.encode("ascii")
                )
            ).decode("ascii")

            payload = (
                query + "&signature=" +
                quote(signature, safe="")
            )

        else:
            if method != "GET" or path not in PUBLIC_PATHS:
                raise SafetyHalt("PUBLIC_ROUTE_FORBIDDEN")

            payload = None

        try:
            with httpx.Client(
                transport=self.transport,
                timeout=8,
                trust_env=False,
                follow_redirects=False,
            ) as client:
                response = client.request(
                    method,
                    ORIGIN + path,
                    params=(
                        payload
                        if signed and method == "GET"
                        else params if not signed else None
                    ),
                    content=(
                        payload if signed and method != "GET"
                        else None
                    ),
                    headers={
                        "X-MBX-APIKEY": self.key,
                    },
                )
        except httpx.HTTPError:
            raise SafetyHalt(
                "EXCHANGE_RESPONSE_UNKNOWN"
            ) from None

        if response.status_code != 200:
            raise SafetyHalt(
                f"EXCHANGE_HTTP_{response.status_code}"
            )

        try:
            return response.json()
        except ValueError:
            raise SafetyHalt(
                "EXCHANGE_INVALID_RESPONSE"
            ) from None

    def exchange_info(self):
        return self._request(
            "GET", "/fapi/v1/exchangeInfo"
        )

    def mark_price(self, symbol):
        return self._request(
            "GET",
            "/fapi/v1/premiumIndex",
            {"symbol": symbol},
        )

    def place(self, order):
        return self._request(
            "POST",
            "/fapi/v1/order",
            order,
            signed=True,
        )

    def query(self, symbol, client_id):
        return self._request(
            "GET",
            "/fapi/v1/order",
            {
                "symbol": symbol,
                "origClientOrderId": client_id,
            },
            signed=True,
        )

    def cancel(self, symbol, client_id):
        return self._request(
            "DELETE",
            "/fapi/v1/order",
            {
                "symbol": symbol,
                "origClientOrderId": client_id,
            },
            signed=True,
        )


def reconcile(client, ledger, symbol, client_id):
    """Recovery only. Never resubmit an unknown order."""

    if ledger.state(client_id) is None:
        raise SafetyHalt("UNKNOWN_LOCAL_ORDER")

    try:
        response = client.query(symbol, client_id)
    except SafetyHalt:
        ledger.update(
            client_id, "RECONCILE_REQUIRED"
        )
        raise

    status = response.get("status")

    if status in FINAL_STATES:
        ledger.update(client_id, status)
    else:
        ledger.update(client_id, "SUBMITTED")

    return response


async def guarded_testnet_cycle(
    *,
    request,
    user,
    client,
    ledger,
    symbol,
    side,
    quantity,
    price,
    client_id,
    max_notional,
):
    """Account-scoped risk check before Testnet submission.

    This is a staging adapter, not a production order gate.
    """

    snapshot = await build_verified_snapshot(
        request, user
    )

    verify_risk(snapshot)

    if side not in ("BUY", "SELL"):
        raise SafetyHalt("INVALID_SIDE")

    if not ID_PATTERN.fullmatch(client_id):
        raise SafetyHalt("INVALID_CLIENT_ID")

    info = client.exchange_info()
    filters = validate_symbol(info, symbol)

    mark_data = client.mark_price(symbol)

    if mark_data.get("symbol") != symbol:
        raise SafetyHalt("MARK_PRICE_SYMBOL_MISMATCH")

    validate_limit_order(
        filters,
        quantity=quantity,
        price=price,
        max_notional=max_notional,
        mark_price=mark_data["markPrice"],
    )

    # Reserve before POST; never retry after ambiguity.
    ledger.reserve(client_id, symbol)

    order = {
        "symbol": symbol,
        "side": side,
        "type": "LIMIT",
        "timeInForce": "GTX",
        "quantity": str(dec(quantity)),
        "price": str(dec(price)),
        "newClientOrderId": client_id,
    }

    try:
        response = client.place(order)
    except SafetyHalt:
        ledger.update(
            client_id, "SUBMISSION_UNKNOWN"
        )
        raise

    ledger.update(client_id, "SUBMITTED")

    # Query and cancel the Testnet order, even though
    # a post-only order should not match immediately.
    try:
        state = reconcile(
            client, ledger, symbol, client_id
        )

        if state.get("status") not in FINAL_STATES:
            client.cancel(symbol, client_id)
            state = reconcile(
                client, ledger, symbol, client_id
            )

        if state.get("status") not in FINAL_STATES:
            ledger.update(
                client_id, "RECONCILE_REQUIRED"
            )
            raise SafetyHalt(
                "ORDER_NOT_FINAL_REVIEW_REQUIRED"
            )

    except SafetyHalt:
        if ledger.state(client_id) not in FINAL_STATES:
            ledger.update(
                client_id, "RECONCILE_REQUIRED"
            )
        raise

    return {
        "market": "TESTNET_ONLY",
        "client_id": client_id,
        "final_status": state.get("status"),
        "mainnet_execution_enabled": False,
    }
