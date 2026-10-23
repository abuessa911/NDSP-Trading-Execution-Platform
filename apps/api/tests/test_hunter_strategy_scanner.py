"""Authenticated, tenant-scoped scanning. No exchange order endpoints."""
import json
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import FastAPI, HTTPException
from starlette.requests import Request

from nex_api.dependencies import Principal
from nex_api.routes import strategy_scanner as scan

class FakeRedis:
    def __init__(self):
        self.data = {}
    async def get(self, key):
        return self.data.get(key)
    async def ttl(self, key):
        return 900 if key in self.data else -2
    async def set(self, key, value, ex=None, nx=False, **kwargs):
        if nx and key in self.data: return False
        self.data[key] = value
        return True
    async def delete(self, key):
        return int(self.data.pop(key, None) is not None)
    async def scan_iter(self, match, count):
        for key in list(self.data):
            if key.startswith(scan.ACTIVE_PREFIX) and not key.endswith(":worker-lock"):
                yield key

def context(enabled=True, csrf="proof", origin="https://bot.ndsp.app"):
    app = FastAPI()
    app.state.redis = FakeRedis()
    app.state.settings = SimpleNamespace(
        oidc_redirect_uri="https://bot.ndsp.app/api/v1/auth/callback",
        hunter_market_monitor_enabled=enabled,
    )
    request = Request({
        "type":"http", "method":"POST", "path":"/api/v1/trading/strategies",
        "headers":[(b"origin",origin.encode()),(b"x-nex-csrf",csrf.encode())],
        "app":app,
    })
    user=SimpleNamespace(tenant_id=uuid4(), id=uuid4())
    principal=Principal("issuer","subject",{"csrf":"proof"})
    return request,user,principal

def fake_result(nonce):
    return json.dumps({
        "nonce":nonce, "signal":"NEUTRAL", "close":"100.15",
        "closed_ms":1_700_000_000_000,
        "checked_ms":int(__import__("time").time()*1000)
    })

@pytest.mark.asyncio
async def test_start_stops_server_state_and_never_authorizes_orders(monkeypatch):
    req,user,principal=context()
    async def sample(strategy_id,symbol,interval,nonce):
        assert (strategy_id,symbol,interval)==("trend-ladder","BTCUSDT","1h")
        return fake_result(nonce)
    monkeypatch.setattr(scan,"_scan_once",sample)
    start=await scan.start_strategy(
        "trend-ladder",scan.StrategyStart(symbol="BTCUSDT",interval="1h"),
        req,user,principal
    )
    assert start.status=="SCANNING" and start.signal=="NEUTRAL"
    assert start.execution_enabled is False and start.ndsp_verified is False
    response=await scan.get_strategies(req,user)
    assert response.order_submission_available is False
    assert len(response.strategies)==5
    assert sum(s.status=="SCANNING" for s in response.strategies)==1
    another=SimpleNamespace(tenant_id=uuid4(),id=uuid4())
    other=await scan.get_strategies(req,another)
    assert all(s.status=="STOPPED" for s in other.strategies)
    stopped=await scan.stop_strategy("trend-ladder",req,user,principal)
    assert stopped.status=="STOPPED"
    assert stopped.signal is None

@pytest.mark.asyncio
async def test_csrf_blocks_mutations_before_market_or_redis(monkeypatch):
    req,user,principal=context(csrf="wrong")
    async def must_not_scan(*args,**kwargs):
        raise AssertionError("market must not be contacted")
    monkeypatch.setattr(scan,"_scan_once",must_not_scan)
    with pytest.raises(HTTPException) as err:
        await scan.start_strategy("trend-ladder",
            scan.StrategyStart(symbol="BTCUSDT",interval="1h"),req,user,principal)
    assert err.value.detail["reason_code"]=="CSRF_NOT_VALID"

@pytest.mark.asyncio
async def test_disabled_worker_blocks_start_and_no_execution(monkeypatch):
    req,user,principal=context(enabled=False)
    with pytest.raises(HTTPException) as err:
        await scan.start_strategy("trend-ladder",
            scan.StrategyStart(symbol="BTCUSDT",interval="1h"),req,user,principal)
    assert err.value.status_code==503
    assert await req.app.state.redis.get(scan.active_key(user,"trend-ladder")) is None

@pytest.mark.asyncio
async def test_market_failure_never_enables(monkeypatch):
    from nex_api.binance_closed_candles import MarketDataUnavailable
    req,user,principal=context()
    async def fail(*args):
        raise MarketDataUnavailable("EXCHANGE_RATE_LIMITED")
    monkeypatch.setattr(scan,"_scan_once",fail)
    with pytest.raises(HTTPException) as err:
        await scan.start_strategy("trend-ladder",
            scan.StrategyStart(symbol="BTCUSDT",interval="1h"),req,user,principal)
    assert err.value.detail["reason_code"]=="STRATEGY_MARKET_UNAVAILABLE"
    assert await req.app.state.redis.get(scan.active_key(user,"trend-ladder")) is None

@pytest.mark.asyncio
async def test_late_worker_result_after_stop_does_not_restart():
    req,user,principal=context()
    key=scan.active_key(user,"trend-ladder")
    await req.app.state.redis.set(key,json.dumps({"nonce":"abc","symbol":"BTCUSDT","interval":"1h"}),ex=900)
    await scan.stop_strategy("trend-ladder",req,user,principal)
    await req.app.state.redis.set(scan.result_key(key), fake_result("abc"),ex=900)
    after=await scan.status(req.app.state.redis,user,scan.BY_ID["trend-ladder"])
    assert after.status=="STOPPED" and after.signal is None

@pytest.mark.asyncio
async def test_worker_updates_only_readonly_result_and_does_not_resurrect_stop(monkeypatch):
    import asyncio
    req,user,principal=context()
    key=scan.active_key(user,"breakout-scout")
    await req.app.state.redis.set(key,json.dumps({
        "nonce":"generation-1","symbol":"SOLUSDT","interval":"4h"
    }),ex=900)
    calls=[]
    async def stub_scan(strategy_id,symbol,interval,nonce):
        calls.append((strategy_id,symbol,interval,nonce))
        return fake_result(nonce)
    async def finish_once(_):
        raise asyncio.CancelledError()
    monkeypatch.setattr(scan,"_scan_once",stub_scan)
    monkeypatch.setattr(scan.asyncio,"sleep",finish_once)
    with pytest.raises(asyncio.CancelledError):
        await scan.strategy_scan_worker(req.app.state.redis)
    assert calls==[("breakout-scout","SOLUSDT","4h","generation-1")]
    record=json.loads(await req.app.state.redis.get(scan.result_key(key)))
    assert record["nonce"]=="generation-1"
    assert (await scan.status(req.app.state.redis,user,scan.BY_ID["breakout-scout"])).status=="SCANNING"
    await req.app.state.redis.delete(key)
    assert (await scan.status(req.app.state.redis,user,scan.BY_ID["breakout-scout"])).status=="STOPPED"
