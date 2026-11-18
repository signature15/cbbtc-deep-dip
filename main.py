"""cbBTC/USDC 1-minute bars bot: deep-dip mean reversion (make.fun bars-replay/v1).

Deterministic long-only strategy, single asset, one position:
- Keep a rolling window of closes; compute the z-score of the latest close.
- Enter only on deep dislocations (z <= Z_ENTRY) with size scaled by conviction.
- Exit on reversion (z back toward mean and PnL over fees), on stop-loss, or
  on a time stop. Fees are 4 bps + 2 bps slippage + impact: a round trip costs
  ~10 bps, so trades are rare and only on strong signals.
- No clock, no environment, no randomness: identical input, identical orders.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "vendor"))
import makefun_bars  # noqa: E402

WINDOW = 360        # rolling window for the z-score
Z_ENTRY = 3.0       # enter when the price is this far below the mean
Z_EXIT = -0.5       # reversion level at which profit exits unlock
STOP_BPS = 250      # stop-loss from entry
MAX_HOLD = 60       # time stop (bars)
PROFIT_BPS = 10     # minimum profit to take
SIZE_FULL_Z = 3.6   # conviction level for a full-position buy
SIZE_PCT = 4        # base buy size, tenths of cash


def zscore(w, close):
    mean = sum(w) / len(w)
    var = sum((v - mean) ** 2 for v in w) / len(w)
    std = var ** 0.5
    return ((close - mean) / std) if std > 0 else 0.0


def on_batch(state, batch):
    sym = "CBBTC"
    bars = [b for b in batch["bars"] if b["symbol"] == sym]
    if not bars:
        return []
    close = int(bars[0]["c"])

    hist = getattr(state, "_closes", None)
    if hist is None:
        hist = state._closes = []
    hist.append(close)

    orders = []
    pos = state.positions.get(sym)

    if pos is None:
        if state.warming_up or len(hist) < WINDOW:
            return []
        z = zscore(hist[-WINDOW:], close)
        armed = getattr(state, "_armed", True)
        if not armed and z > Z_ENTRY + 0.75:
            state._armed = True
            armed = True
        if armed and z <= Z_ENTRY:
            spend = state.cash if z <= -SIZE_FULL_Z else state.cash * SIZE_PCT // 10
            if spend > 2_000_000:
                orders.append({
                    "side": "buy", "symbol": sym,
                    "notional_quote_units": spend,
                    "max_slippage_bps": 200,
                })
                state._entry_seq = batch["seq"] + 1
                state._armed = False
        return orders

    entry_seq = getattr(state, "_entry_seq", batch["seq"])
    held = batch["seq"] - entry_seq
    qty = pos.qty
    cost = pos.cost
    val = state.value(sym, qty)
    pnl_bps = (val - cost) * 10000 // max(1, cost)

    exit_now = pnl_bps <= -STOP_BPS or held >= MAX_HOLD
    if not exit_now and pnl_bps >= PROFIT_BPS:
        exit_now = zscore(hist[-WINDOW:], close) >= Z_EXIT
    if exit_now:
        orders.append({
            "side": "sell", "symbol": sym,
            "qty": qty,
            "max_slippage_bps": 200,
        })
    return orders


if __name__ == "__main__":
    makefun_bars.run(on_batch)
