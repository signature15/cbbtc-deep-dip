"""cbBTC deep-dip mean-reversion bot for make.fun btc-race-24h (agent-fun/bars-replay/v1).

Long-only, single asset (CBBTC), at most one position. Each batch appends CBBTC's
close to a rolling history; once WINDOW closes exist, the latest close is scored
as a z-score against that window. A dip to z <= -3.0 buys (all cash when
z <= -3.6, else cash*4//10), and the trigger then disarms until z recovers past
the hysteresis band (-2.25), so one dip is bought once, not on every bar of it.
The position exits on a -250 bps stop, a 60-bar time stop (counted from the fill
bar, since orders decided on bar k fill at bar k+1's open), or +10 bps of profit
once price has reverted to z >= -0.5.

Determinism: every entry runs twice and the two action logs must match byte for
byte, so the bot is a pure function of the stdin bar stream — no clock, no
environment, no random. All money math is integer (Python ints; the z-score
uses one float division, IEEE-deterministic), so both runs agree exactly.
"""

import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "vendor"))

import makefun_bars

SYMBOL = "CBBTC"
WINDOW = 360
Z_ENTRY = -3.0
Z_DEEP = -3.6
Z_HYSTERESIS = -2.25
Z_PROFIT = -0.5
STOP_BPS = -250
PROFIT_BPS = 10
TIME_STOP_BARS = 60
MIN_SPEND = 2_000_000
SLIPPAGE_BPS = 200


def zscore(window, close):
    """(close - mean) / std over window (population variance); 0.0 when std == 0."""
    mean = sum(window) // len(window)
    var = sum((c - mean) ** 2 for c in window) // len(window)
    std = math.isqrt(var)
    if std == 0:
        return 0.0
    return (close - mean) / std


def on_batch(state, batch):
    """Decide this batch's orders: None, one buy, or one sell."""
    hist = getattr(state, "_closes", None)
    if hist is None:
        hist = state._closes = []
    for bar in batch["bars"]:
        if bar["symbol"] == SYMBOL:
            hist.append(int(bar["c"]))

    if len(hist) < WINDOW:
        return None

    window = hist[-WINDOW:]
    z = zscore(window, window[-1])

    # Hysteresis: once disarmed, re-arm only after the dip has recovered.
    if not getattr(state, "_armed", True) and z > Z_HYSTERESIS:
        state._armed = True

    pos = state.positions.get(SYMBOL)
    if pos is not None:
        pnl_bps = (state.value(SYMBOL, pos.qty) - pos.cost) * 10000 // max(1, pos.cost)
        held = batch["seq"] - getattr(state, "_entry_seq", batch["seq"])
        if pnl_bps <= STOP_BPS or held >= TIME_STOP_BARS or (pnl_bps >= PROFIT_BPS and z >= Z_PROFIT):
            return [{"side": "sell", "symbol": SYMBOL, "qty": pos.qty, "max_slippage_bps": SLIPPAGE_BPS}]
        return None

    if state.warming_up or not getattr(state, "_armed", True) or z > Z_ENTRY:
        return None

    spend = state.cash if z <= Z_DEEP else state.cash * 4 // 10
    orders = []
    if spend > MIN_SPEND:
        orders.append({"side": "buy", "symbol": SYMBOL, "notional_quote_units": spend, "max_slippage_bps": SLIPPAGE_BPS})
    state._entry_seq = batch["seq"] + 1
    state._armed = False
    return orders


if __name__ == "__main__":
    makefun_bars.run(on_batch)
