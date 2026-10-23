"""Authenticated Binance Ed25519 read-only account connection."""

import asyncio
import json
import os
from pathlib import Path
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, ConfigDict, Field, SecretStr

from nex_api.binance_ed25519_readonly import (
    BinanceEd25519ReadOnly,
    BinanceReadError,
)
from nex_api.dependencies import (
    Principal, failure, get_current_principal, get_operator,
)
from nex_api.models import User
from nex_api.routes.trading_control import (
    LIVE_CONNECT_TTL_SECONDS,
    live_cipher,
    live_connection_key,
    redis_store,
    verify_mutation,
)

router = APIRouter(
    prefix="/api/v1/trading/ed25519",
    tags=["hunter ed25519 readonly"],
    include_in_schema=False,
)


def credential_path() -> Path:
    directory = os.environ.get("CREDENTIALS_DIRECTORY")
    if not directory:
        raise RuntimeError("SERVICE_CREDENTIAL_UNAVAILABLE")
    path = Path(directory) / "binance-ed25519.pem"
    if not path.is_file():
        raise RuntimeError("SERVICE_CREDENTIAL_UNAVAILABLE")
    return path


class ConnectRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    api_key: SecretStr = Field(min_length=10, max_length=256)


class ConnectResult(BaseModel):
    authenticated: bool
    connector_read_only: Literal[True] = True
    spot_connected: bool
    futures_connected: bool
    ip_restricted: bool
    key_has_trading_permissions: bool
    encrypted_server_storage: bool
    execution_enabled: Literal[False] = False


@router.post("/connect", response_model=ConnectResult)
async def connect(
    request: Request,
    credentials: ConnectRequest,
    user: Annotated[User, Depends(get_operator)],
    principal: Annotated[Principal, Depends(get_current_principal)],
):
    verify_mutation(request, principal)

    # Fail closed if encrypted credential storage is unavailable.
    encryptor = live_cipher(request)
    store = redis_store(request)

    api_key = credentials.api_key.get_secret_value()

    try:
        path = credential_path()

        def probe():
            client = BinanceEd25519ReadOnly(api_key, path)
            permissions = client.read("permissions")
            client.read("spot")
            client.read("futures")
            return permissions

        permissions = await asyncio.to_thread(probe)

    except (BinanceReadError, OSError, RuntimeError, ValueError):
        raise failure(
            "ED25519_CONNECT_FAILED",
            "Binance Ed25519 read-only verification failed.",
            422,
        ) from None

    if (
        permissions.get("enableReading") is not True
        or permissions.get("enableWithdrawals") is not False
        or permissions.get("enableFutures") is not True
        or permissions.get("enableSpotAndMarginTrading") is not True
    ):
        raise failure(
            "ED25519_PERMISSION_CHECK_FAILED",
            "Required read permissions or withdrawal safety check failed.",
            422,
        )

    encrypted = encryptor.encrypt(
        json.dumps({
            "key": api_key,
            "scheme": "ed25519",
        }).encode("utf-8")
    )

    try:
        await store.set(
            live_connection_key(user),
            encrypted,
            ex=LIVE_CONNECT_TTL_SECONDS,
        )
    except Exception:
        raise failure(
            "MONITOR_STORE_UNAVAILABLE",
            "Credential store unavailable.",
            503,
        ) from None

    return ConnectResult(
        authenticated=True,
        spot_connected=True,
        futures_connected=True,
        ip_restricted=permissions.get("ipRestrict") is True,
        key_has_trading_permissions=True,
        encrypted_server_storage=True,
    )


# Account balances: authenticated, per-user, strictly GET-only.
# This endpoint never authorizes order execution.
@router.get("/balances")
async def ed25519_balances(
    request: Request,
    user: Annotated[User, Depends(get_operator)],
):
    from decimal import Decimal, InvalidOperation
    from cryptography.fernet import InvalidToken
    import httpx

    store = redis_store(request)
    encrypted = await store.get(live_connection_key(user))
    if not encrypted:
        raise failure(
            "BINANCE_NOT_CONNECTED",
            "No account connection saved.",
            404,
        )

    try:
        saved = json.loads(live_cipher(request).decrypt(encrypted))
        if saved.get("scheme") != "ed25519":
            raise ValueError("NOT_ED25519")
        api_key = saved["key"]
        if not isinstance(api_key, str) or not api_key:
            raise ValueError("INVALID_KEY")
    except (InvalidToken, ValueError, TypeError, KeyError):
        raise failure(
            "BINANCE_CREDENTIAL_UNAVAILABLE",
            "Ed25519 credential unavailable.",
            503,
        ) from None

    def numeric(value):
        number = Decimal(str(value))
        if not number.is_finite() or number < 0:
            raise ValueError("INVALID_AMOUNT")
        return number

    def fetch():
        connector = BinanceEd25519ReadOnly(api_key, credential_path())
        spot = connector.read("spot")
        futures = connector.read("futures")

        # Public market prices; API credentials are never sent here.
        with httpx.Client(
            timeout=10,
            trust_env=False,
            follow_redirects=False,
        ) as client:
            response = client.get(
                "https://api.binance.com/api/v3/ticker/price"
            )
            response.raise_for_status()
            raw_prices = response.json()

        if not isinstance(raw_prices, list) or len(raw_prices) > 100000:
            raise ValueError("INVALID_PRICES")

        prices = {}
        for item in raw_prices:
            if not isinstance(item, dict):
                continue
            symbol = item.get("symbol")
            try:
                value = numeric(item.get("price"))
            except (ValueError, InvalidOperation, TypeError):
                continue
            if isinstance(symbol, str) and value > 0:
                prices[symbol] = value

        if not isinstance(spot.get("balances"), list):
            raise ValueError("INVALID_SPOT")
        futures_value = numeric(futures["totalMarginBalance"])

        def asset_price(asset):
            if asset == "USDT":
                return Decimal("1")
            direct = prices.get(asset + "USDT")
            if direct:
                return direct
            inverse = prices.get("USDT" + asset)
            if inverse:
                return Decimal("1") / inverse

            for bridge in ("BTC", "ETH", "BNB"):
                bridge_usdt = prices.get(bridge + "USDT")
                if not bridge_usdt:
                    continue
                direct_bridge = prices.get(asset + bridge)
                if direct_bridge:
                    return direct_bridge * bridge_usdt
                inverse_bridge = prices.get(bridge + asset)
                if inverse_bridge:
                    return bridge_usdt / inverse_bridge

            return None

        spot_value = Decimal("0")
        unpriced = set()

        for entry in spot["balances"]:
            if not isinstance(entry, dict):
                raise ValueError("INVALID_BALANCE")

            asset = entry.get("asset")
            if not isinstance(asset, str) or not asset.isalnum():
                raise ValueError("INVALID_ASSET")

            quantity = numeric(entry["free"]) + numeric(entry["locked"])
            if quantity == 0:
                continue

            rate = asset_price(asset)
            if rate is None:
                unpriced.add(asset)
            else:
                spot_value += quantity * rate

        complete = not unpriced

        def format_usdt(value):
            return format(value.quantize(Decimal("0.01")), "f")

        return {
            "spot_usdt": format_usdt(spot_value) if complete else None,
            "futures_usdt": format_usdt(futures_value),
            "total_usdt": format_usdt(spot_value + futures_value)
                if complete else None,
            "valuation_complete": complete,
            "unpriced_assets_count": len(unpriced),
            "execution_enabled": False,
            "valuation_basis": "PUBLIC_LAST_PRICE_INDICATIVE",
        }

    try:
        result = await asyncio.to_thread(fetch)
    except Exception:
        # Never expose Binance account data, keys or exchange responses.
        raise failure(
            "BALANCES_UNAVAILABLE",
            "Could not value Binance balances safely.",
            503,
        ) from None

    return result
