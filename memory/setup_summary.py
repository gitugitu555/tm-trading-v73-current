"""Setup summary export for OpenClaw/vector memory."""

from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any

from core.types import FeatureSnapshot


@dataclass(frozen=True)
class SetupMemoryObject:
    timestamp: str
    instrument: str
    setup_type: str
    regime: str
    features: dict[str, float | str | None]
    summary: str
    outcome: str = "pending"

    def to_json_ready(self) -> dict[str, Any]:
        return asdict(self)


def build_setup_memory_object(
    *,
    snapshot: FeatureSnapshot,
    setup_type: str,
    outcome: str = "pending",
) -> SetupMemoryObject:
    summary = (
        f"{setup_type} on {snapshot.instrument}: cvd velocity "
        f"{snapshot.delta_velocity:.4f}, acceleration {snapshot.delta_acceleration:.4f}, "
        f"book imbalance {snapshot.book_imbalance:.4f}, whale pressure "
        f"{snapshot.whale_pressure:.2f}."
    )
    return SetupMemoryObject(
        timestamp=snapshot.ts_event.isoformat(),
        instrument=snapshot.instrument,
        setup_type=setup_type,
        regime=snapshot.regime,
        features={
            "cvd": snapshot.cvd,
            "cvd_velocity": snapshot.delta_velocity,
            "delta_acceleration": snapshot.delta_acceleration,
            "vpin": snapshot.vpin,
            "microprice": snapshot.microprice,
            "book_imbalance": snapshot.book_imbalance,
            "whale_pressure": snapshot.whale_pressure,
            "alpha_reason_codes": ",".join(snapshot.reason_codes),
        },
        summary=summary,
        outcome=outcome,
    )
