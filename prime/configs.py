"""Clean, professional dataclasses for strategy configuration.

Central place for all tunable params. Used by engines, permission, backtesters,
runners, and the new tiered cache materializer.

Import from here everywhere (deprecate scattered kwargs over time).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal


@dataclass(frozen=True)
class RegimeConfig:
    trend_threshold_pct: float = 0.0025
    ranging_threshold_pct: float = 0.001
    stress_price_change_pct: float = 0.0045
    stress_cvd_threshold: float = 500.0
    use_stress_regime: bool = True


@dataclass(frozen=True)
class AuctionConfig:
    discovery_price_change_pct: float = 0.0015
    trending_price_change_pct: float = 0.003
    exhaustion_price_change_pct: float = 0.0045
    acceptance_cvd_threshold: float = 80.0
    failed_auction_cvd_threshold: float = 120.0
    hysteresis_bars: int = 2


@dataclass(frozen=True)
class PermissionConfig:
    kq_approve: float = 0.55
    kq_reduced: float = 0.35
    base_position_size: float = 0.01
    use_auction_state_gate: bool = True
    use_regime_gate_for_fade: bool = True  # for volume_bar_cvd divergence
    use_vwap_gate: bool = False  # off for volbar per V73 program
    # vpin / l2 etc. added as we wire them


@dataclass(frozen=True)
class FootprintConfluenceConfig:
    """Weights and rules for footprint + absorption etc. as conviction (0-1)."""
    bias_match_base: float = 0.7
    neutral_base: float = 0.4
    stacked_bonus: float = 0.15
    absorption_bonus: float = 0.20
    delta_cluster_bonus: float = 0.10
    min_score: float = 0.5
    require_stacked: bool = False


@dataclass(frozen=True)
class VolumeBarCVDConfig:
    """Core signal + conversion params for the protected edge."""
    volume_bar_threshold: float = 300.0
    divergence_lookback_bars: int = 40
    htf_flat_quantile: float = 0.25
    exit_after_volume_bars: int = 5
    use_delta_rev_2_entry: bool = False  # D5 opt-in; D4 default
    use_footprint_confluence: bool = True
    use_regime_gate_volume_bar: bool = True
    use_auction_state_gate: bool = True
    invert_signal_side: bool = False


@dataclass(frozen=True)
class ChunkBBacktestConfig:
    """Top-level config for Chunk B (research + potential live). Composes the above."""
    starting_equity: float = 100_000.0
    signal_mode: Literal["momentum", "divergence"] = "divergence"
    divergence_type: Literal["opposite_delta", "swing", "volume_bar_cvd"] = "volume_bar_cvd"

    # Sub-configs (can override individually)
    regime: RegimeConfig = field(default_factory=RegimeConfig)
    auction: AuctionConfig = field(default_factory=AuctionConfig)
    permission: PermissionConfig = field(default_factory=PermissionConfig)
    vol_cvd: VolumeBarCVDConfig = field(default_factory=VolumeBarCVDConfig)
    footprint_confluence: FootprintConfluenceConfig = field(default_factory=FootprintConfluenceConfig)

    # Common
    stop_pct: float = 0.0045
    target_pct: float = 0.0025
    use_tpsl: bool = True
    footprint_tick_size: float = 0.5
    footprint_warm_period: int = 100
    # ... (add vwap, swing etc. as we unify)

    # For cached path
    threshold_btc: float = 300.0
    divergence_lookback_bars: int = 40
    htf_flat_quantile: float = 0.25
    exit_after_volume_bars: int | None = None
    use_footprint_confluence: bool = True
    footprint_require_stacked: bool = False
    use_delta_rev_2_entry: bool = False
    use_regime_gate_volume_bar: bool = False

    # Legacy compat fields (will be removed)
    divergence_threshold: float = 100.0
    price_change_threshold: float = 0.001
    # etc.
