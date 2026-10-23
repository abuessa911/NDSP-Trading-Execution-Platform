"""Optional paper/testnet failures must not hide the owner power switch."""
from types import SimpleNamespace
from uuid import uuid4
import json

from fastapi import HTTPException

import pytest

from nex_api.routes import bot_power
from nex_api.paper_broker import PaperRejected


class Store:
    def __init__(self):
        self.records = {}

    async def scan_iter(self, match, count=16):
        for key in list(self.records):
            if key.startswith(match.rstrip('*')):
                yield key

    async def get(self, key):
        return self.records.get(key)

    async def exists(self, key):
        return int(key in self.records)

    async def set(self, key, value, ex=None):
        self.records[key] = value
        return True

    async def delete(self, *keys):
        for key in keys:
            self.records.pop(key, None)
        return len(keys)


class FailingPaper:
    def metadata(self, scope):
        raise PaperRejected('PAPER_LEDGER_UNAVAILABLE')


class BusyDemo:
    def session(self, scope):
        raise OSError('TESTNET_OPERATION_IN_PROGRESS')


@pytest.mark.asyncio
async def test_owner_switch_status_stays_readable_when_optional_services_unavailable(monkeypatch):
    async def monitor_state(request, user):
        return SimpleNamespace(state='STOPPED')
    monkeypatch.setattr(bot_power, 'state', monitor_state)
    user = SimpleNamespace(tenant_id=uuid4(), id=uuid4())
    store = Store()
    app = SimpleNamespace(state=SimpleNamespace(
        redis=store, paper_broker=FailingPaper(), testnet_execution=BusyDemo()))
    request = SimpleNamespace(app=app)
    response = await bot_power.current(request, user)
    assert response['status'] == 'DEGRADED'
    assert not response['powered']
    assert set(response['issues']) == {'PAPER_STATUS_UNAVAILABLE', 'TESTNET_STATUS_UNAVAILABLE'}
    assert response['live_orders_enabled'] is False
    store.records[bot_power.power_key(user)] = 'on'
    response = await bot_power.current(request, user)
    assert response['status'] == 'RUNNING'
    assert response['waiting_for_strategy'] is True
    assert len(response['issues']) == 2


@pytest.mark.asyncio
async def test_no_optional_services_returns_genuine_off_state(monkeypatch):
    async def monitor_state(request, user):
        return SimpleNamespace(state='STOPPED')
    monkeypatch.setattr(bot_power, 'state', monitor_state)
    user = SimpleNamespace(tenant_id=uuid4(), id=uuid4())
    request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(
        redis=Store(), paper_broker=None, testnet_execution=None)))
    response = await bot_power.current(request, user)
    assert response['status'] == 'STOPPED' and not response['issues']
    assert response['private_ndsp_strategies_connected'] is False


@pytest.mark.asyncio
async def test_strategy_selection_is_saved_while_bot_off_and_remains_visible(monkeypatch):
    async def monitor_state(request, user):
        return SimpleNamespace(state='STOPPED')
    monkeypatch.setattr(bot_power, 'state', monitor_state)
    monkeypatch.setattr(bot_power, 'verify_mutation', lambda request, principal: None)
    user = SimpleNamespace(tenant_id=uuid4(), id=uuid4())
    store = Store()
    request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(
        redis=store, paper_broker=None, testnet_execution=None)))
    chosen = next(iter(bot_power.BY_ID))
    response = await bot_power.select_strategy(chosen, request, user, SimpleNamespace())
    assert response['selected_strategy_id'] == chosen
    assert response['powered'] is False
    assert response['status'] == 'STOPPED'
    assert response['live_orders_enabled'] is False
    assert store.records[bot_power.selected_key(user)] == chosen


@pytest.mark.asyncio
async def test_power_on_uses_explicit_selection_and_does_not_create_order(monkeypatch):
    async def monitor_state(request, user):
        return SimpleNamespace(state='STOPPED')
    monkeypatch.setattr(bot_power, 'state', monitor_state)
    monkeypatch.setattr(bot_power, 'verify_mutation', lambda request, principal: None)
    calls = []
    async def begin(strategy_id, request, user, principal):
        calls.append(strategy_id)
        request.app.state.redis.records[bot_power.active_key(user, strategy_id)] = 'on'
    monkeypatch.setattr(bot_power, '_begin_selected_strategy', begin)
    user = SimpleNamespace(tenant_id=uuid4(), id=uuid4())
    store = Store()
    chosen = next(iter(bot_power.BY_ID))
    store.records[bot_power.selected_key(user)] = chosen
    request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(
        redis=store, paper_broker=None, testnet_execution=None,
        settings=SimpleNamespace(hunter_market_monitor_enabled=True))))
    response = await bot_power.start_bot(request, user, SimpleNamespace())
    assert calls == [chosen]
    assert response['powered'] is True
    assert response['waiting_for_strategy'] is False
    assert response['selected_strategy_id'] == chosen
    assert response['live_orders_enabled'] is False


@pytest.mark.asyncio
async def test_trading_preferences_are_saved_with_daily_policy_atomically(monkeypatch):
    from nex_api.routes import trading_profile, risk_equity

    async def snapshot(request, user):
        return SimpleNamespace(symbol='BTCUSDT', interval='15m', leverage=3), '', ''
    monkeypatch.setattr(trading_profile, 'workspace_snapshot', snapshot)
    monkeypatch.setattr(bot_power, 'verify_mutation', lambda request, principal: None)

    class PreferencesStore(Store):
        async def eval(self, script, count, policy, baseline, preferences, daily, day, payload):
            assert script == bot_power.SAVE_TRADING_PREFERENCES
            assert count == 3
            assert policy == risk_equity.policy_key(user)
            assert preferences == bot_power.preferences_key(user)
            self.records[policy] = json.dumps({'daily_loss_pct': daily, 'utc_day': day})
            self.records[preferences] = payload
            return 1

    user = SimpleNamespace(tenant_id=uuid4(), id=uuid4())
    store = PreferencesStore()
    request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(redis=store)))
    body = bot_power.TradingPreferenceUpdate(
        venue='BINANCE_USDM_FUTURES', capital_limit_usdt='250.50',
        trade_risk_pct='0.5', daily_loss_pct='2',
    )
    result = await bot_power.save_trading_preferences(body, request, user, SimpleNamespace())
    assert result['configured'] is True
    assert result['capital_limit_usdt'] == '250.50'
    assert result['trade_risk_pct'] == '0.5'
    assert result['daily_loss_pct'] == '2'
    assert result['leverage'] == 3
    assert result['execution_ready'] is False
    assert result['live_orders_enabled'] is False
    assert json.loads(store.records[bot_power.preferences_key(user)])['capital_limit_usdt'] == '250.50'


@pytest.mark.asyncio
async def test_risk_increase_and_trade_risk_greater_than_daily_are_rejected(monkeypatch):
    monkeypatch.setattr(bot_power, 'verify_mutation', lambda request, principal: None)

    class LockedStore(Store):
        async def eval(self, *args):
            return 0

    user = SimpleNamespace(tenant_id=uuid4(), id=uuid4())
    store = LockedStore()
    request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(redis=store)))
    base = dict(venue='BINANCE_USDM_FUTURES', capital_limit_usdt='100',
                trade_risk_pct='1', daily_loss_pct='2')
    with pytest.raises(HTTPException) as limited:
        await bot_power.save_trading_preferences(
            bot_power.TradingPreferenceUpdate(**base), request, user, SimpleNamespace())
    assert limited.value.status_code == 409
    assert store.records == {}
    with pytest.raises(HTTPException) as invalid:
        await bot_power.save_trading_preferences(
            bot_power.TradingPreferenceUpdate(**(base | {'trade_risk_pct': '3'})),
            request, user, SimpleNamespace())
    assert invalid.value.status_code == 422
