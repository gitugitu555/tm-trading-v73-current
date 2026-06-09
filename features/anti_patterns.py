"""Shadow anti-pattern detection for research gating."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class AntiPatternSnapshot:
    labels: tuple[str, ...]
    should_block: bool
    severity: float
    confidence: float
    reason_codes: tuple[str, ...] = field(default_factory=tuple)


class AntiPatternEngine:
    """Deterministic shadow classifier for common failure modes."""

    def evaluate(
        self,
        *,
        setup_side: int,
        profile_context: str,
        toxicity_state: str,
        mlofi_zscore: float | None,
        spread_bps: float | None,
        session_tier: str,
        breakout_strength: float,
        atr_used_pct: float,
        value_area_context: str,
    ) -> AntiPatternSnapshot:
        labels: list[str] = []
        reasons: list[str] = []

        if session_tier == "SKIP" or atr_used_pct >= 75.0:
            labels.append("EXHAUSTION_CONTINUATION")
            reasons.append("ATR_USED_TOO_HIGH")
        if profile_context == "IN_VALUE" and breakout_strength < 0.35:
            labels.append("PROFILE_MID_VALUE_CHASE")
            reasons.append("INSIDE_VALUE_WITH_WEAK_MOMENTUM")
        if spread_bps is not None and toxicity_state in {"HIGH_TOXICITY", "RISING_TOXICITY"} and spread_bps > 6.0:
            labels.append("LOW_LIQUIDITY_BREAKOUT")
            reasons.append("TOXIC_FLOW_WITH_WIDE_SPREAD")
        if mlofi_zscore is not None and abs(mlofi_zscore) < 0.4 and breakout_strength > 0.55:
            labels.append("RANGE_BREAKOUT_FAKE")
            reasons.append("WEAK_BOOK_CONFIRMATION")
        if value_area_context == "ABOVE_VALUE" and setup_side < 0 and breakout_strength < 0.45:
            labels.append("BULL_TRAP")
            reasons.append("SHORT_IN_UPPER_EXTREME")
        if value_area_context == "BELOW_VALUE" and setup_side > 0 and breakout_strength < 0.45:
            labels.append("BEAR_TRAP")
            reasons.append("LONG_IN_LOWER_EXTREME")

        severity = min(1.0, 0.2 * len(labels) + (0.2 if toxicity_state == "HIGH_TOXICITY" else 0.0))
        confidence = min(1.0, 0.4 + 0.12 * len(labels) + min(abs(mlofi_zscore or 0.0) / 4.0, 0.2))
        return AntiPatternSnapshot(
            labels=tuple(labels),
            should_block=bool(labels),
            severity=round(severity, 4),
            confidence=round(confidence, 4),
            reason_codes=tuple(reasons),
        )
