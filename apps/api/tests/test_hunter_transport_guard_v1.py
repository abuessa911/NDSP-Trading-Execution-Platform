from unittest.mock import patch
import httpx
import pytest
from nex_api.hunter_live_executor import Exchange, Halt

def exchange(mode, calls):
    def handler(req):
        calls.append((req.method, req.url.path))
        return httpx.Response(200,json={"ok":True})
    return Exchange(mode,"fake-key","fake-secret",transport=httpx.MockTransport(handler))

@pytest.mark.parametrize("method,path", [
    ("POST","/fapi/v1/order"),
    ("DELETE","/fapi/v1/algoOrder"),
])
def test_mainnet_direct_transport_block(method,path):
    calls=[]
    ex=exchange("mainnet",calls)
    try:
        with pytest.raises(Halt,match="MAINNET_ORDER_WRITES_NOT_RELEASED"):
            ex._call(method,path,{},signed=True)
        assert not calls
    finally:
        ex.close()

@pytest.mark.parametrize("method,path,signed", [
    ("POST","/fapi/v1/leverage",True),
    ("DELETE","/fapi/v1/order",True),
    ("PUT","/fapi/v1/order",True),
    ("POST","/fapi/v1/order",False),
])
def test_testnet_direct_transport_allowlist(method,path,signed):
    calls=[]
    ex=exchange("testnet",calls)
    try:
        with pytest.raises(Halt,match="EXCHANGE_WRITE_ROUTE_FORBIDDEN"):
            ex._call(method,path,{},signed=signed)
        assert not calls
    finally:
        ex.close()

def test_mock_testnet_post_allowed():
    calls=[]
    ex=exchange("testnet",calls)
    try:
        with patch("nex_api.hunter_live_executor.Path.exists",return_value=False):
            assert ex._call("POST","/fapi/v1/order",{"symbol":"BTCUSDT"},signed=True)=={"ok":True}
        assert calls==[("POST","/fapi/v1/order")]
    finally:
        ex.close()

def test_emergency_blocks_direct_testnet_post():
    calls=[]
    ex=exchange("testnet",calls)
    try:
        with patch("nex_api.hunter_live_executor.Path.exists",return_value=True):
            with pytest.raises(Halt,match="EMERGENCY_STOP_ACTIVE"):
                ex._call("POST","/fapi/v1/order",{},signed=True)
        assert not calls
    finally:
        ex.close()
