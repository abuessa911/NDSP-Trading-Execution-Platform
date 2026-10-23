"""Isolated 1m dual-side TESTNET lifecycle verifier.

No network client, scheduler, credentials, production route or order submission.
The adapter accepts signed exchange observations from an external test harness.
Uncertain protection or flattening always fails closed.
"""
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation


class LabHalt(RuntimeError):
    pass


@dataclass(frozen=True)
class LabPlan:
    symbol: str
    direction: str
    quantity: str
    stop_price: str
    entry_id: str
    stop_id: str
    exit_id: str
    timeframe: str = "1m"

    def __post_init__(self):
        if self.symbol not in {"BTCUSDT", "ETHUSDT"} or self.direction not in {"LONG", "SHORT"} or self.timeframe != "1m":
            raise LabHalt("INVALID_TESTNET_PLAN")
        for value in (self.quantity, self.stop_price):
            try:
                number = Decimal(value)
            except (InvalidOperation, TypeError):
                raise LabHalt("INVALID_NUMBER") from None
            if not number.is_finite() or number <= 0:
                raise LabHalt("INVALID_NUMBER")
        ids = (self.entry_id, self.stop_id, self.exit_id)
        if len(set(ids)) != 3 or any(not isinstance(x, str) or not x.startswith("lab_") or len(x) > 36 for x in ids):
            raise LabHalt("UNSAFE_ORDER_ID")


class DualSideLab:
    """Evidence gate: state transitions only, caller never submits orders here."""
    def __init__(self, plan: LabPlan):
        self.plan = plan
        self.state = "PLANNED"
        self.history = []

    def _advance(self, required, new_state, evidence):
        if self.state != required or evidence is not True:
            self.state = "HALTED_RECONCILE_REQUIRED"
            raise LabHalt("MISSING_OR_CONFLICTING_EXCHANGE_PROOF")
        self.state = new_state
        self.history.append(new_state)

    def entry_filled(self, *, signed_exchange_proof, filled_quantity, side):
        expected = "BUY" if self.plan.direction == "LONG" else "SELL"
        self._advance("PLANNED", "ENTRY_FILLED", signed_exchange_proof is True
                      and side == expected and filled_quantity == self.plan.quantity)

    def stop_protected(self, *, signed_exchange_proof, stop_side, stop_price, reduce_only, status):
        expected = "SELL" if self.plan.direction == "LONG" else "BUY"
        self._advance("ENTRY_FILLED", "PROTECTED", signed_exchange_proof is True
                      and stop_side == expected and stop_price == self.plan.stop_price
                      and reduce_only is True and status in {"NEW", "TRIGGER_PENDING"})

    def exit_filled(self, *, signed_exchange_proof, exit_side, filled_quantity):
        expected = "SELL" if self.plan.direction == "LONG" else "BUY"
        self._advance("PROTECTED", "EXIT_FILLED", signed_exchange_proof is True
                      and exit_side == expected and filled_quantity == self.plan.quantity)

    def close_verified(self, *, signed_exchange_proof, position_quantity, open_stops):
        self._advance("EXIT_FILLED", "CLOSED_VERIFIED",
                      signed_exchange_proof is True and position_quantity == "0" and open_stops == 0)

    @property
    def passed(self):
        return self.state == "CLOSED_VERIFIED"
