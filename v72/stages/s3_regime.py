"""S3 — hard regime classifier."""

from __future__ import annotations

from collections import deque

from prime.phase4_minimal import HardRegimeClassifier
from v72.contracts import V72PipelineState


class RegimeStage:
    stage_id = "s3"

    def __init__(self, *, lookback_ns: int = 300_000_000_000) -> None:
        self._classifier = HardRegimeClassifier()
        self._lookback_ns = lookback_ns
        self._prices: deque[tuple[int, float]] = deque()
        self._bars_in_regime = 0
        self._last_label: str | None = None

    def process(
        self,
        state: V72PipelineState,
        *,
        book=None,
    ) -> V72PipelineState:
        if state.halted or state.tick is None or state.microstructure is None:
            return state

        ts = int(state.tick.ts_event)
        price = float(state.tick.price)
        self._prices.append((ts, price))
        cutoff = ts - self._lookback_ns
        while self._prices and self._prices[0][0] <= cutoff:
            self._prices.popleft()

        price_change = 0.0
        if self._prices:
            first = self._prices[0][1]
            if first != 0:
                price_change = (price - first) / first

        regime = self._classifier.classify(
            timestamp_ns=ts,
            price_change_5m_pct=price_change,
            cvd_session=state.microstructure.cvd_session,
            bars_in_regime=self._bars_in_regime,
        )
        if self._last_label == regime.hard_label:
            self._bars_in_regime += 1
        else:
            self._bars_in_regime = 0
            self._last_label = regime.hard_label

        state.regime = regime
        state.stage_trace.append(self.stage_id)
        return state