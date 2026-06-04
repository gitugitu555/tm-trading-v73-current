# Session 5: Volume-Bar Confluence Prompt

Use this prompt when resuming the Chunk B port into the backtester.

```text
You are working in /home/tokio/tm-trading-v555.

Context:
- The repo already has a working VolumeBarSampler in prime/volume_bars.py.
- The repo already has a volume-bar cache in prime/volume_bar_cache.py.
- Do NOT create a duplicate sampler API.
- Do NOT use is_buyer_maker; use the existing TradeTick.aggressor_side / aggressor helpers from prime/nautilus_compat.py and prime/phase1.py.
- The 6-year diagnostic result we are porting is:
  - 300 BTC volume bars
  - 40-bar divergence lookback
  - D1 divergence + D4 HTF filter
  - archive-level htf_flat_abs precompute matching the diagnostic exactly
- Keep raw Binance ZIPs untouched.
- No pandas anywhere in engine or backtester code.
- Use apply_patch only for edits.

Goal:
Port the proven volume-bar divergence architecture into the Chunk B backtester without breaking the existing momentum path.

What already exists and must be reused:
1. prime/volume_bars.py
   - VolumeBar
   - VolumeBarSampler.update(tick) -> VolumeBar | None
   - VolumeBar fields:
     start_ts_ns, end_ts_ns, open, high, low, close, volume, buy_volume, sell_volume, delta, cumulative_delta, ticks
2. prime/volume_bar_cache.py
   - load_cached_bars(...)
   - write_cached_bars(...)
3. prime/nautilus_compat.py
   - TradeTick has price, size, aggressor_side, ts_event
4. prime/phase1.py
   - BaseEngine._signed_volume(tick)
   - aggressor_name(...)
   - CVDEngine, SwingDivergenceEngine, SessionExtremeTracker already exist

Architectural target:
- tick -> indicators -> volume bars -> D1 -> D4 -> signal -> permission -> entry
- The new volume-bar signal path must be opt-in and must not change momentum mode behavior.

Implementation plan:

STEP 1
Add a lightweight confluence engine for volume bars.
Use a new class in prime/phase1.py or a new prime module if cleaner, but it must operate on the existing VolumeBar objects.

Name:
- CVDConfluenceEngine or VolumeBarCVDConfluenceEngine

Responsibilities:
- operate on deque[VolumeBar]
- detect D1 divergence
- apply D4 HTF filter
- use archive-level htf_flat_abs exactly like scripts/volume_bar_cvd_diagnostic.py

Definitions:
D1_divergence:
- bearish if current bar makes a lookback high and current cumulative_delta is below prior cumulative_delta high
- bullish if current bar makes a lookback low and current cumulative_delta is above prior cumulative_delta low

D4_htf:
- compute one-hour CVD changes from the bar series
- compute htf_flat_abs as the quantile of abs(one_hour_cvd_change)
- bearish is allowed only if HTF is not strongly bullish
- bullish is allowed only if HTF is not strongly bearish

Important:
- Match the diagnostic logic exactly.
- htf_flat_abs is not a rolling live metric in this session.
- It should be computed from the full archive bar history, just like scripts/volume_bar_cvd_diagnostic.py.

STEP 2
Wire the existing VolumeBarSampler into ChunkBBacktester.

Add opt-in config fields to ChunkBBacktestConfig:
- use_volume_bar_signal: bool = False
- volume_bar_threshold: float = 300.0
- cvd_lookback_bars: int = 40
- htf_flat_quantile: float = 0.25

Do not change the default momentum path.

In ChunkBBacktester.__init__:
- instantiate self._vol_sampler = VolumeBarSampler(self.config.volume_bar_threshold)
- instantiate the confluence engine
- add state for a deque of closed bars
- add state to hold the precomputed htf_flat_abs
- keep the existing engines and permission logic unchanged

STEP 3
Use a two-pass research flow for the volume-bar signal path.

Pass 1:
- stream the archive ticks
- feed each tick into the existing indicators
- feed each tick into self._vol_sampler.update(tick)
- collect closed VolumeBar objects
- if cache is enabled, use prime/volume_bar_cache.py to skip rebuilding bars when possible

After enough bars exist:
- compute htf_flat_abs from the full closed-bar history
- use the exact diagnostic logic:
  - build one_hour_cvd_changes from bar timestamps and cumulative_delta
  - take abs(change)
  - compute the q-quantile via sorted list indexing, matching the diagnostic
- do not use pandas
- do not claim exact O(1) rolling quantiles

Pass 2:
- replay the closed volume bars through the confluence engine
- generate D1 + D4 signals
- route the final signal into the existing permission engine
- open trades only after permission approves

If you prefer a single-pass implementation, it must still produce the same archive-level htf_flat_abs behavior as the diagnostic. A two-pass archive-level pass is acceptable and simpler.

STEP 4
Integrate the signal selection cleanly in ChunkBBacktester.run().

Required order:
1. update raw tick-based indicators
2. update volume bar sampler
3. collect / cache closed volume bars
4. when volume-bar signal mode is active and the bar history is ready, detect D1 + D4
5. call permission.evaluate(...)
6. open trade only if approved

Do not mix permission logic into signal detection.

Signal payload should include:
- id
- side
- strength
- price
- stage label if useful

STEP 5
Add tests.

Add tests that verify:
- VolumeBarSampler emits a bar at threshold
- VolumeBarSampler tracks high/low correctly
- VolumeBarSampler accumulates delta and cumulative_delta correctly
- htf_flat_abs precompute matches the diagnostic-style quantile behavior on a small synthetic bar set
- CVDConfluenceEngine detects bearish D1
- CVDConfluenceEngine detects bullish D1
- CVDConfluenceEngine blocks signals when HTF disagrees
- momentum mode remains unchanged

Do not add brittle tests that depend on exact live market outcomes.

STEP 6
Add one smoke run.

Update scripts/chunk_b_sweep.py so it can run the new opt-in volume-bar signal path.

Add CLI flags:
- --use-volume-bar-signal / --no-use-volume-bar-signal
- --volume-bar-threshold
- --cvd-lookback-bars
- --htf-flat-quantile

Run one smoke test only:
- archive: BTCUSDT-aggTrades-2022-09.zip
- max rows: 500000
- signal mode: divergence
- use volume bar signal: true
- volume bar threshold: 300
- lookback bars: 40
- htf flat quantile: 0.25

Report:
- signals_seen
- trades
- win_rate
- sharpe
- permission_counts

Success criteria:
- The new volume-bar path fires at least one signal on smoke test, or if not, explain precisely whether the blocker is calibration, D1 logic, or permission gating.
- Existing tests still pass.
- Momentum mode still behaves as before.
- The code path uses the existing VolumeBarSampler and volume_bar_cache modules, not a duplicate implementation.

Output:
- Make code changes via apply_patch only.
- Show the files changed.
- Show test results.
- Show the smoke run result.
- Be explicit if any assumption had to be made.
```
