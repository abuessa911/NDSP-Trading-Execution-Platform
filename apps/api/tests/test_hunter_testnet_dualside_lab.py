import pytest
from nex_api.hunter_testnet_dualside_lab import DualSideLab, LabPlan, LabHalt


@pytest.mark.parametrize("direction,entry_side,exit_side", [
    ("LONG", "BUY", "SELL"), ("SHORT", "SELL", "BUY")
])
def test_full_protected_closed_cycle(direction, entry_side, exit_side):
    plan = LabPlan("BTCUSDT", direction, "0.001", "60000", "lab_entry", "lab_stop", "lab_exit")
    lab = DualSideLab(plan)
    lab.entry_filled(signed_exchange_proof=True, filled_quantity="0.001", side=entry_side)
    assert not lab.passed
    lab.stop_protected(signed_exchange_proof=True, stop_side=exit_side,
                       stop_price="60000", reduce_only=True, status="NEW")
    lab.exit_filled(signed_exchange_proof=True, exit_side=exit_side, filled_quantity="0.001")
    assert not lab.passed
    lab.close_verified(signed_exchange_proof=True, position_quantity="0", open_stops=0)
    assert lab.passed


@pytest.mark.parametrize("direction", ["LONG", "SHORT"])
def test_unprotected_entry_halts(direction):
    plan = LabPlan("BTCUSDT", direction, "0.001", "60000", "lab_e", "lab_s", "lab_x")
    lab = DualSideLab(plan)
    lab.entry_filled(signed_exchange_proof=True, filled_quantity="0.001",
                     side="BUY" if direction == "LONG" else "SELL")
    with pytest.raises(LabHalt):
        lab.stop_protected(signed_exchange_proof=False, stop_side="SELL", stop_price="60000",
                           reduce_only=True, status="NEW")
    assert lab.state == "HALTED_RECONCILE_REQUIRED"


def test_incomplete_exit_not_success():
    lab = DualSideLab(LabPlan("BTCUSDT", "LONG", "0.001", "60000",
                              "lab_a", "lab_b", "lab_c"))
    with pytest.raises(LabHalt):
        lab.close_verified(signed_exchange_proof=True, position_quantity="0", open_stops=0)
    assert not lab.passed


def test_invalid_identity_rejected():
    with pytest.raises(LabHalt):
        LabPlan("BTCUSDT", "SHORT", "0.001", "60000", "duplicate", "duplicate", "duplicate")
