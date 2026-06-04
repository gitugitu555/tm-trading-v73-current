"""Experiment and result manifests for reproducible research runs."""

from __future__ import annotations

import hashlib
import json
import subprocess
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class ExperimentManifest:
    experiment_id: str
    git_commit: str
    strategy_name: str
    config_hash: str
    command: str
    output_path: str
    dataset_archive: str | None = None
    fee_bps_per_side: float = 5.0
    slippage_bps_per_side: float = 1.0
    created_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ResultManifest:
    experiment_id: str
    git_commit: str
    output_path: str
    status: str
    signal_win_rate: float | None = None
    trade_win_rate: float | None = None
    trades: int = 0
    created_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def git_commit(cwd: Path | None = None) -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=cwd,
            text=True,
        ).strip()
    except Exception:
        return "unknown"


def config_hash(config: dict[str, Any]) -> str:
    payload = json.dumps(config, sort_keys=True, default=str)
    return hashlib.sha256(payload.encode()).hexdigest()[:16]


def build_experiment_manifest(
    *,
    experiment_id: str,
    strategy_name: str,
    config: dict[str, Any],
    command: str,
    output_path: Path | str,
    repo_root: Path | None = None,
    dataset_archive: str | None = None,
) -> ExperimentManifest:
    return ExperimentManifest(
        experiment_id=experiment_id,
        git_commit=git_commit(repo_root),
        strategy_name=strategy_name,
        config_hash=config_hash(config),
        command=command,
        output_path=str(output_path),
        dataset_archive=dataset_archive,
        fee_bps_per_side=float(config.get("fee_bps_per_side", 5.0)),
        slippage_bps_per_side=float(config.get("slippage_bps_per_side", 1.0)),
        created_at=datetime.now(timezone.utc).isoformat(),
    )


def append_manifest_jsonl(path: Path, record: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, sort_keys=True))
        handle.write("\n")


def wrap_result_payload(
    payload: dict[str, Any],
    *,
    experiment_id: str,
    command: str,
    output_path: Path | str,
    repo_root: Path | None = None,
) -> dict[str, Any]:
    report = payload.get("report", {})
    manifest = build_experiment_manifest(
        experiment_id=experiment_id,
        strategy_name=payload.get("strategy", report.get("config", {}).get("divergence_type", "chunk_b")),
        config=report.get("config", {}),
        command=command,
        output_path=output_path,
        repo_root=repo_root,
        dataset_archive=payload.get("archive"),
    )
    signal_card = report.get("signal_scorecard") or {}
    result = ResultManifest(
        experiment_id=experiment_id,
        git_commit=manifest.git_commit,
        output_path=str(output_path),
        status="complete",
        signal_win_rate=signal_card.get("hit_rate"),
        trade_win_rate=report.get("win_rate"),
        trades=int(report.get("trades", 0)),
        created_at=datetime.now(timezone.utc).isoformat(),
    )
    return {
        **payload,
        "experiment_manifest": manifest.to_dict(),
        "result_manifest": result.to_dict(),
    }