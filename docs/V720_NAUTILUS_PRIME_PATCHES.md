# V7.2 Nautilus-Prime Patches

These patches apply before implementing the V7.2 Nautilus-backed Chunk A/B path.
The current V555 scaffold remains the deterministic no-trade feature sandbox.

## Required Fixes

1. Use the correct Nautilus tick-indicator registration API.

```python
self.register_indicator_for_trade_ticks(self.instrument_id, self._cvd)
self.register_indicator_for_trade_ticks(self.instrument_id, self._delta)
self.register_indicator_for_trade_ticks(self.instrument_id, self._footprint)
self.register_indicator_for_trade_ticks(self.instrument_id, self._vp)
```

Bar indicators still use:

```python
self.register_indicator_for_bars(bar_type, self._atr_ind)
self.register_indicator_for_bars(bar_type, self._adx_ind)
```

2. Match the regime classifier parameter name.

```python
self._regime_cls.classify(
    vol_percentile=50.0,
    adx=adx,
    price_change_5m_pct=price_change_5m,
    cvd_session=self._cvd.cvd_session,
    bars_in_regime=0,
)
```

3. Chunk B strategy is momentum confirmation, not divergence reversal.

The strategy name is `CVDMomentumConfirmation`.

Entry logic:

- `TREND_BULL` and `cvd_session > threshold` -> long.
- `TREND_BEAR` and `cvd_session < -threshold` -> short.
- Other regimes do not trade.
- Footprint must align with the chosen side.
- CVD divergence is not the primary entry signal in Chunk B.

Divergence is reserved as an AlphaPermission modifier or a later ranging-regime
mean-reversion strategy after Chunk B proves edge.

## Codex Prompt Delta

Add these constraints to V7.2 implementation prompts:

- Tick indicators: `register_indicator_for_trade_ticks()`.
- Bar indicators: `register_indicator_for_bars()`.
- Chunk B strategy: `CVDMomentumConfirmation`.
- Do not gate Chunk B entries on `cvd_divergence`.
- Use `bars_in_regime`, not `bars_in_current_regime`.

## Data Priority

Before Chunk A IC work:

1. Complete the Binance BTCUSDT aggTrades download.
2. Verify all `.CHECKSUM` files.
3. Convert raw zips into a sorted, immutable research format.
4. Run sample-first IC: 1 week, then 1 month, then full six-year span.
