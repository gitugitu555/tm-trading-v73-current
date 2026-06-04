"""Run the V555 deterministic replay demo."""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from data.replay.validator import ReplayValidator
from strategy.alpha_permission import AlphaPermissionEngine


def main() -> None:
    validator = ReplayValidator(tick_size=0.1)
    snapshots, report = validator.replay_csv(
        trades_csv=ROOT / "examples" / "sample_trades.csv",
        books_csv=ROOT / "examples" / "sample_books.csv",
    )
    permission = AlphaPermissionEngine().compute(snapshots[-1])

    print("TM Trading Codex V555 replay demo")
    print(f"snapshots={report.snapshot_count}")
    print(f"checksum={report.checksum}")
    print(f"parity_passed={report.parity_passed}")
    print(f"final_cvd={snapshots[-1].cvd:.4f}")
    print(f"final_delta_velocity={snapshots[-1].delta_velocity:.4f}")
    print(f"final_book_imbalance={snapshots[-1].book_imbalance:.4f}")
    print(f"final_whale_pressure={snapshots[-1].whale_pressure:.2f}")
    print(f"alpha_direction={permission.direction}")
    print(f"alpha_strength={permission.strength:.2f}")
    print(f"alpha_confidence={permission.confidence:.2f}")
    print(f"alpha_reason_codes={','.join(permission.reason_codes)}")


if __name__ == "__main__":
    main()
