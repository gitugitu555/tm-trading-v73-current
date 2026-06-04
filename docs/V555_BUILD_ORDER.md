# V555 Build Order

See `docs/V555_3_PHASE_PLAN.md` for the practical 3-phase execution plan.

## Phase 0

- repository structure
- config hash
- logging/test skeleton
- dependency-free unit tests

## Phase 1

- Binance trade loader
- L2 collector
- replay file format
- data quality firewall

## Phase 2

- pure feature engines
- synthetic tests
- streaming versus batch parity
- footprint F1-F5 research track, see `docs/V555_FOOTPRINT_F1_F5_SPEC.md`

## Phase 3

- Nautilus strategy skeleton
- feature snapshots only
- no trading

## Phase 5

- AlphaPermission
- deterministic KQ fallback
- reason-coded no-trade decisions

## Rule Zero

If a signal cannot be replayed deterministically, explained with reason codes,
and validated out of sample after fees and slippage, it is an observation, not an alpha.

## V7.2 Nautilus-Prime Patch Note

Before implementing the Nautilus-backed V7.2 path, apply the decisions in
`docs/V720_NAUTILUS_PRIME_PATCHES.md`: correct Nautilus indicator registration,
fix the regime classifier kwarg, and use `CVDMomentumConfirmation` for Chunk B.
