"""V7.2 Chunk B three-multiplier AlphaPermission engine."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from prime.contracts import DataQualitySnapshot, hash_dict
from prime.auction_state import AuctionStateSnapshot
from prime.phase4_minimal import RegimeState


@dataclass(frozen=True)
class MultiplierRecord:
    source: str
    code: str
    multiplier: float
    value_before: float
    value_after: float


@dataclass(frozen=True)
class AlphaPermission:
    permission_id: str
    signal_id: str
    timestamp_ns: int
    trade_side: int
    verdict: str
    kq: float
    chain: list[MultiplierRecord]
    bottleneck_code: Optional[str]
    bottleneck_mult: float
    permitted_size: float
    size_scalar: float
    blocking_codes: list[str]
    input_hash: str
    output_hash: str


class AlphaPermissionEngineChunkB:
    """Chunk B: Feed quality -> Regime -> CVD confirmation only."""

    def __init__(
        self,
        kq_approve: float = 0.55,
        kq_reduced: float = 0.35,
        base_position_size: float = 0.01,
        vwap_structure_pct: float = 0.003,
        use_auction_state_gate: bool = False,
    ) -> None:
        self._kq_approve = kq_approve
        self._kq_reduced = kq_reduced
        self._base_size = base_position_size
        self._vwap_structure_pct = vwap_structure_pct
        self._use_auction_state_gate = use_auction_state_gate
        self._verdict_history: list[str] = []
        self._multiplier_verdicts: dict[str, list[str]] = {}

    def evaluate(
        self,
        *,
        signal_id: str,
        timestamp_ns: int,
        trade_side: int,
        raw_strength: float,
        quality_snapshot: DataQualitySnapshot,
        regime: RegimeState,
        cvd_divergence: bool,
        cvd_5m: float,
        signal_mode: str = "momentum",
        vwap_deviation: float | None = None,
        auction_state: AuctionStateSnapshot | None = None,
    ) -> AlphaPermission:
        chain: list[MultiplierRecord] = []
        blocking: list[str] = []
        kq = raw_strength
        input_hash = hash_dict({"sid": signal_id, "ts": timestamp_ns, "str": raw_strength})
        cvd_confirms = (trade_side == +1 and cvd_5m > 0) or (trade_side == -1 and cvd_5m < 0)

        if quality_snapshot.state == "HALT":
            return self._hard_deny(signal_id, timestamp_ns, trade_side, kq, chain, ["FEED_HALT"], input_hash)
        kq, rec = self._apply(kq, quality_snapshot.confidence_scalar, "PHASE0", "FEED_QUALITY")
        chain.append(rec)

        if regime.all_halted:
            return self._hard_deny(signal_id, timestamp_ns, trade_side, kq, chain, ["REGIME_HALT"], input_hash)
        if signal_mode == "momentum":
            kq, rec = self._apply(kq, regime.regime_confidence_scalar, "PHASE4", "REGIME_CONFIDENCE")
            chain.append(rec)
        elif regime.hard_label == "UNKNOWN":
            kq, rec = self._apply(kq, 0.5, "PHASE4", "REGIME_UNKNOWN_SOFT")
            chain.append(rec)

        if cvd_divergence:
            if cvd_confirms:
                kq, rec = self._apply(kq, 1.15, "PHASE1", "CVD_CONFIRMING")
            else:
                kq, rec = self._apply(kq, 0.70, "PHASE1", "CVD_OPPOSING")
            chain.append(rec)

        if auction_state is not None:
            if self._use_auction_state_gate:
                if auction_state.state in {"BALANCED", "DISCOVERY"}:
                    multiplier = 1.05 if auction_state.value_acceptance else 1.00
                elif auction_state.state == "TRENDING":
                    multiplier = 1.10 if cvd_confirms else 0.85
                elif auction_state.state == "EXHAUSTION":
                    multiplier = 0.80
                elif auction_state.state == "FAILED_AUCTION":
                    multiplier = 1.12 if cvd_confirms else 0.75
                else:
                    multiplier = 0.90
                kq, rec = self._apply(kq, multiplier, "PHASE4", f"AUCTION_{auction_state.state}")
                chain.append(rec)
            else:
                kq, rec = self._apply(kq, 1.0, "PHASE4", f"AUCTION_{auction_state.state}_OPTIN_OFF")
                chain.append(rec)

        if vwap_deviation is not None:
            vwap_dev = abs(vwap_deviation)
            if vwap_dev < 0.001:
                multiplier = 1.10
            elif vwap_dev < 0.003:
                multiplier = 1.05
            elif vwap_dev < 0.005:
                multiplier = 0.80
            else:
                multiplier = 0.60
            kq, rec = self._apply(kq, multiplier, "PHASE1", "VWAP_SCORE")
            chain.append(rec)

        kq = max(0.0, min(1.0, kq))
        if kq >= self._kq_approve:
            verdict = "APPROVE"
            size_scalar = 1.0
        elif kq >= self._kq_reduced:
            verdict = "REDUCED"
            size_scalar = 0.5
        else:
            verdict = "HARD_DENY"
            size_scalar = 0.0

        bottleneck = min(chain, key=lambda item: item.multiplier) if chain else None
        permission = AlphaPermission(
            permission_id=f"{signal_id}_perm",
            signal_id=signal_id,
            timestamp_ns=timestamp_ns,
            trade_side=trade_side,
            verdict=verdict,
            kq=round(kq, 6),
            chain=chain,
            bottleneck_code=bottleneck.code if bottleneck else None,
            bottleneck_mult=round(bottleneck.multiplier, 6) if bottleneck else 1.0,
            permitted_size=round(self._base_size * size_scalar, 8),
            size_scalar=size_scalar,
            blocking_codes=sorted(blocking),
            input_hash=input_hash,
            output_hash=hash_dict({"verdict": verdict, "kq": kq}),
        )
        self._record(permission)
        return permission

    def _apply(
        self,
        kq: float,
        multiplier: float,
        source: str,
        code: str,
    ) -> tuple[float, MultiplierRecord]:
        before = kq
        after = kq * multiplier
        return after, MultiplierRecord(source, code, multiplier, round(before, 6), round(after, 6))

    def _hard_deny(
        self,
        signal_id: str,
        timestamp_ns: int,
        trade_side: int,
        kq: float,
        chain: list[MultiplierRecord],
        blocking: list[str],
        input_hash: str,
    ) -> AlphaPermission:
        permission = AlphaPermission(
            permission_id=f"{signal_id}_deny",
            signal_id=signal_id,
            timestamp_ns=timestamp_ns,
            trade_side=trade_side,
            verdict="HARD_DENY",
            kq=0.0,
            chain=chain,
            bottleneck_code=blocking[0] if blocking else None,
            bottleneck_mult=0.0,
            permitted_size=0.0,
            size_scalar=0.0,
            blocking_codes=sorted(blocking),
            input_hash=input_hash,
            output_hash=hash_dict({"verdict": "HARD_DENY"}),
        )
        self._record(permission)
        return permission

    def _record(self, permission: AlphaPermission) -> None:
        self._verdict_history.append(permission.verdict)
        for record in permission.chain:
            self._multiplier_verdicts.setdefault(record.code, []).append(permission.verdict)

    def run_ablation(self, pnl_with: dict[str, float], pnl_without: dict[str, float]) -> dict:
        results: dict = {}
        total = len(self._verdict_history)
        if total == 0:
            return results
        for code in sorted(self._multiplier_verdicts.keys()):
            verdicts = self._multiplier_verdicts[code]
            pnl_w = pnl_with.get(code, 0.0)
            pnl_wo = pnl_without.get(code, 0.0)
            pnl_change = abs(pnl_w - pnl_wo) / max(abs(pnl_w), 1e-9) * 100
            flip_pct = len(verdicts) / total * 100
            results[code] = {
                "verdict_flip_pct": round(flip_pct, 2),
                "pnl_change_pct": round(pnl_change, 2),
                "verdict": "KEEP" if (flip_pct >= 3.0 or pnl_change >= 5.0) else "DELETE",
            }
        return results
