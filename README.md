[![make.fun · btc-race-24h-20261118-1444](https://make.fun/badge/btc-race-24h-20261118-1444.svg)](https://make.fun/bounty/btc-race-24h-20261118-1444?utm_source=github&utm_medium=readme&utm_campaign=btc-race-24h-20261118-1444)
[![rank](https://make.fun/badge/btc-race-24h-20261118-1444/signature15/cbbtc-deep-dip/rank.svg)](https://make.fun/bounty/btc-race-24h-20261118-1444/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=btc-race-24h-20261118-1444)
[![reward](https://make.fun/badge/btc-race-24h-20261118-1444/signature15/cbbtc-deep-dip/reward.svg)](https://make.fun/bounty/btc-race-24h-20261118-1444?utm_source=github&utm_medium=readme&utm_campaign=btc-race-24h-20261118-1444)

# cbbtc-deep-dip

Long-only mean-reversion bot for **CBBTC** on make.fun's `btc-race-24h` contest, speaking `agent-fun/bars-replay/v1` over stdin/stdout. It waits for a deep dip in price, buys it once, and exits on a stop, a time stop, or a mean reversion.

## Strategy

Deep-dip mean reversion over a rolling window of 360 closes:

- Each batch appends CBBTC's close to a rolling history; once 360 closes exist, the latest close is scored as a z-score against that window.
- **Entry** — flat, warmed up, armed, and z <= **-3.0**: spend all cash when z <= -3.6, else `cash*4//10`, as one buy with 200 bps max slippage.
- **Hysteresis** — a buy disarms the trigger; it re-arms only once z recovers above **-2.25**, so one dip is bought once instead of on every bar of it.
- **Exit** (at most one position held):
  - **stop**: pnl <= **-250 bps**
  - **time stop**: held >= **60** bars, counted from the fill bar (orders decided on bar k fill at bar k+1's open)
  - **profit exit**: pnl >= **+10 bps** and z >= **-0.5** (price has reverted toward the mean)

## Layout

- `main.py` — the strategy: `zscore()`, `on_batch(state, batch)`, and `makefun_bars.run(on_batch)` under `__main__`.
- `vendor/makefun_bars.py` — vendored bars-replay shim (unmodified): owns the wire protocol and `BarsState` (`.cash`, `.positions{symbol: Holding(qty, cost)}`, `.value(symbol, qty)`, `.warming_up`, `.seq`).
- `README.md` — this file.

Run as the grader does:

```sh
python3 -P -s main.py
```

## Determinism

Every entry is graded twice and the two action logs must match byte for byte, so the bot is a pure function of the stdin bar stream: it never reads the clock, the environment, or a random source. All money math is integer (Python ints; the z-score uses one float division, IEEE-deterministic), bot state lives on `BarsState` (`_closes`, `_armed`, `_entry_seq`), and the only outputs are the reply lines the shim writes to stdout.

## License

MIT — see [LICENSE](LICENSE) if present; otherwise:

```
Copyright (c) 2026 signature15

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```
