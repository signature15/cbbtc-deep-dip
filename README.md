# cbbtc-deep-dip

A cbBTC/USDC mean-reversion bot for make.fun's `agent-fun/bars-replay/v1`
protocol (competition btc-race-24h-20261118-1444).

## Strategy

Deep-dip mean reversion, long-only, one position:

- rolling 360-bar z-score of the close; enter only at z <= -3.0
- size scaled by conviction (full size at z <= -3.6)
- exit on reversion (z >= -0.5 with PnL >= 10 bps), stop-loss at 250 bps,
  or a 60-bar time stop
- re-entry hysteresis: after an exit the entry stays disarmed until
  z recovers above -2.25, preventing churn in a falling market

Fees are 4 bps + 2 bps slippage + impact (~10 bps round trip), so trades are
rare and only on strong dislocations.

## Layout

- `main.py` — the bot (Python 3.13, standard library only)
- `vendor/makefun_bars.py` — vendored copy of the kit's shim

## Determinism

No clock, no environment reads, no randomness: two runs over the same bars
produce byte-identical order logs.

## Backtest (published dev window, 1440 one-minute bars)

- net PnL: +$0.73 (passes the dev gate)
- max drawdown: 0.11%
- fills: 2

## License

MIT
