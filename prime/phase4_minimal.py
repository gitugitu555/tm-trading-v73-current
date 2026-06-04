"""V7.2 Chunk B minimal regime proxy."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RegimeState:
    timestamp_ns: int
    hard_label: str
    hard_confidence: float
    cusum_alert: bool
    cusum_variables: list[str]
    transition_warning: str
    trend_enabled: bool
    mean_reversion_enabled: bool
    breakout_enabled: bool
    all_halted: bool
    regime_confidence_scalar: float
    volatility_percentile: float
    bars_in_regime: int


class HardRegimeClassifier:
    """Chunk B proxy using price change and CVD only."""

    def __init__(
        self,
        *,
        trend_threshold_pct: float = 0.0025,
        ranging_threshold_pct: float = 0.001,
        stress_price_change_pct: float = 0.0045,
        stress_cvd_threshold: float = 500.0,
        use_stress_regime: bool = True,
    ) -> None:
        self._trend_threshold_pct = trend_threshold_pct
        self._ranging_threshold_pct = ranging_threshold_pct
        self._stress_price_change_pct = stress_price_change_pct
        self._stress_cvd_threshold = stress_cvd_threshold
        self._use_stress_regime = use_stress_regime

    def classify(
        self,
        *,
        timestamp_ns: int,
        price_change_5m_pct: float,
        cvd_session: float,
        bars_in_regime: int = 0,
    ) -> RegimeState:
        label, confidence = chunk_b_regime_proxy(
            price_change_5m_pct,
            cvd_session,
            trend_threshold_pct=self._trend_threshold_pct,
            ranging_threshold_pct=self._ranging_threshold_pct,
            stress_price_change_pct=self._stress_price_change_pct,
            stress_cvd_threshold=self._stress_cvd_threshold,
            use_stress_regime=self._use_stress_regime,
        )
        gates = self.get_strategy_gates(label)
        return RegimeState(
            timestamp_ns=timestamp_ns,
            hard_label=label,
            hard_confidence=confidence,
            cusum_alert=False,
            cusum_variables=[],
            transition_warning="NONE",
            trend_enabled=gates["trend_enabled"],
            mean_reversion_enabled=gates["mean_reversion_enabled"],
            breakout_enabled=gates["breakout_enabled"],
            all_halted=gates["all_halted"],
            regime_confidence_scalar=self.confidence_scalar(label, confidence),
            volatility_percentile=50.0,
            bars_in_regime=bars_in_regime,
        )

    @staticmethod
    def get_strategy_gates(label: str) -> dict[str, bool]:
        gates = {
            "trend_enabled": False,
            "mean_reversion_enabled": False,
            "breakout_enabled": False,
            "all_halted": False,
        }
        if label in {"TREND_BULL", "TREND_BEAR"}:
            gates["trend_enabled"] = True
            gates["breakout_enabled"] = True
        elif label in {"RANGING", "UNKNOWN"}:
            gates["mean_reversion_enabled"] = True
        else:
            gates["all_halted"] = True
        return gates

    @staticmethod
    def confidence_scalar(label: str, confidence: float) -> float:
        if label == "STRESS":
            return 0.0
        return round(confidence, 3)

    @staticmethod
    def gate_for_signal_mode(regime: RegimeState, signal_mode: str) -> bool:
        if regime.all_halted:
            return False
        if signal_mode == "divergence":
            return regime.mean_reversion_enabled
        if signal_mode == "momentum":
            return regime.trend_enabled
        return False


def chunk_b_regime_proxy(
    price_change_5m_pct: float,
    cvd_session: float,
    *,
    trend_threshold_pct: float = 0.0025,
    ranging_threshold_pct: float = 0.001,
    stress_price_change_pct: float = 0.0045,
    stress_cvd_threshold: float = 500.0,
    use_stress_regime: bool = True,
) -> tuple[str, float]:
    if (
        use_stress_regime
        and abs(price_change_5m_pct) >= stress_price_change_pct
        and abs(cvd_session) >= stress_cvd_threshold
    ):
        confidence = min(
            0.99,
            0.70
            + abs(price_change_5m_pct) / max(stress_price_change_pct, 1e-12) * 0.10
            + abs(cvd_session) / max(stress_cvd_threshold, 1e-12) * 0.05,
        )
        return "STRESS", round(confidence, 3)
    if abs(price_change_5m_pct) > trend_threshold_pct and cvd_session * price_change_5m_pct > 0:
        label = "TREND_BULL" if price_change_5m_pct > 0 else "TREND_BEAR"
        confidence = min(0.90, 0.60 + abs(price_change_5m_pct) * 100)
        return label, round(confidence, 3)
    if abs(price_change_5m_pct) < ranging_threshold_pct:
        return "RANGING", 0.70
    return "UNKNOWN", 0.30
