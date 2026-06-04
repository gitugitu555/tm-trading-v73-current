"""Minimal synthetic auction-state engine for V7.5/V7.4-style orchestration."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AuctionStateSnapshot:
    timestamp_ns: int
    state: str
    confidence: float
    transition: str | None
    transition_reason: str
    bars_in_state: int
    value_acceptance: bool
    evidence_score: float


class AuctionStateEngine:
    """Deterministic auction-state classifier with anti-flicker hysteresis."""

    def __init__(
        self,
        *,
        discovery_price_change_pct: float = 0.0015,
        trending_price_change_pct: float = 0.003,
        exhaustion_price_change_pct: float = 0.0045,
        acceptance_cvd_threshold: float = 80.0,
        failed_auction_cvd_threshold: float = 120.0,
        hysteresis_bars: int = 2,
    ) -> None:
        self._discovery_price_change_pct = discovery_price_change_pct
        self._trending_price_change_pct = trending_price_change_pct
        self._exhaustion_price_change_pct = exhaustion_price_change_pct
        self._acceptance_cvd_threshold = acceptance_cvd_threshold
        self._failed_auction_cvd_threshold = failed_auction_cvd_threshold
        self._hysteresis_bars = hysteresis_bars
        self._state = "BALANCED"
        self._bars_in_state = 0
        self._pending_transition: str | None = None
        self._pending_count = 0

    @property
    def state(self) -> str:
        return self._state

    @property
    def bars_in_state(self) -> int:
        return self._bars_in_state

    def update(
        self,
        *,
        timestamp_ns: int,
        price_change_5m_pct: float,
        cvd_session: float,
        value_acceptance: bool,
    ) -> AuctionStateSnapshot:
        candidate, reason = self._classify(price_change_5m_pct, cvd_session, value_acceptance)
        transition: str | None = None

        if candidate == self._state:
            self._pending_transition = None
            self._pending_count = 0
            self._bars_in_state += 1
        else:
            if candidate == self._pending_transition:
                self._pending_count += 1
            else:
                self._pending_transition = candidate
                self._pending_count = 1

            if self._pending_count >= self._hysteresis_bars:
                transition = f"{self._state}->{candidate}"
                self._state = candidate
                self._bars_in_state = 0
                self._pending_transition = None
                self._pending_count = 0
            else:
                self._bars_in_state += 1

        confidence = self._confidence(price_change_5m_pct, cvd_session, value_acceptance, self._state)
        evidence_score = self._evidence_score(price_change_5m_pct, cvd_session, value_acceptance)
        return AuctionStateSnapshot(
            timestamp_ns=timestamp_ns,
            state=self._state,
            confidence=round(confidence, 3),
            transition=transition,
            transition_reason=reason,
            bars_in_state=self._bars_in_state,
            value_acceptance=value_acceptance,
            evidence_score=round(evidence_score, 3),
        )

    def _classify(self, price_change_5m_pct: float, cvd_session: float, value_acceptance: bool) -> tuple[str, str]:
        abs_price = abs(price_change_5m_pct)
        abs_cvd = abs(cvd_session)

        if abs_price >= self._exhaustion_price_change_pct and abs_cvd >= self._failed_auction_cvd_threshold and not value_acceptance:
            return "FAILED_AUCTION", "EXTREME_FLOW_REJECTED_VALUE"
        if abs_price >= self._exhaustion_price_change_pct:
            return "EXHAUSTION", "EXTREME_PRICE_MOVE"
        if abs_price >= self._trending_price_change_pct and value_acceptance:
            return "TRENDING", "STRONG_MOVE_WITH_ACCEPTANCE"
        if abs_price >= self._discovery_price_change_pct or abs_cvd >= self._acceptance_cvd_threshold:
            return "DISCOVERY", "VALUE_MIGRATION_OR_INITIATION"
        return "BALANCED", "NO_STRONG_IMBALANCE"

    @staticmethod
    def _confidence(
        price_change_5m_pct: float,
        cvd_session: float,
        value_acceptance: bool,
        state: str,
    ) -> float:
        base = 0.50 + min(abs(price_change_5m_pct) * 80.0, 0.25) + min(abs(cvd_session) / 800.0, 0.20)
        if value_acceptance:
            base += 0.05
        if state == "BALANCED":
            base = min(base, 0.65)
        elif state == "FAILED_AUCTION":
            base = max(base, 0.80)
        return min(base, 0.99)

    @staticmethod
    def _evidence_score(price_change_5m_pct: float, cvd_session: float, value_acceptance: bool) -> float:
        score = abs(price_change_5m_pct) * 1000.0 + abs(cvd_session) / 10.0
        if value_acceptance:
            score += 15.0
        return score
