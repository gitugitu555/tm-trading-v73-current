"""Promotion summary helpers for V8.4 research artifacts."""

from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from pathlib import Path

from .trade_path_db import TradePathDatabase


@dataclass(frozen=True)
class GateHighlight:
    name: str
    mae_threshold: float | None
    mfe_threshold: float | None
    trades_evaluated: int
    would_exit_early: int
    early_exits_that_were_winners: int
    early_exits_that_were_losers: int
    counterfactual_win_rate: float
    counterfactual_pnl_delta: float
    winner_loser_ratio: float


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _baseline_metrics(report: dict) -> dict:
    return {
        "trades": int(report.get("trade_scorecard", {}).get("trades", report.get("trades", 0))),
        "win_rate": float(report.get("trade_scorecard", {}).get("win_rate", report.get("win_rate", 0.0))),
        "total_pnl": float(report.get("trade_scorecard", {}).get("total_pnl", report.get("total_pnl", 0.0))),
        "sharpe": float(report.get("sharpe", 0.0)),
        "dsr_passed": bool(report.get("dsr_passed", False)),
        "ending_equity": float(report.get("ending_equity", 0.0)),
        "lookahead_safe": bool(report.get("lookahead_safe", False)),
        "entry_lag_bars": int(report.get("entry_lag_bars", 0)),
    }


def _best_gate(shadow_gates: dict[str, dict], prefix: str) -> GateHighlight | None:
    items = []
    for name, data in shadow_gates.items():
        if not name.startswith(prefix):
            continue
        items.append(
            GateHighlight(
                name=name,
                mae_threshold=data.get("mae_threshold"),
                mfe_threshold=data.get("mfe_threshold"),
                trades_evaluated=int(data.get("trades_evaluated", 0)),
                would_exit_early=int(data.get("would_exit_early", 0)),
                early_exits_that_were_winners=int(data.get("early_exits_that_were_winners", 0)),
                early_exits_that_were_losers=int(data.get("early_exits_that_were_losers", 0)),
                counterfactual_win_rate=float(data.get("counterfactual_win_rate", 0.0)),
                counterfactual_pnl_delta=float(data.get("counterfactual_pnl_delta", 0.0)),
                winner_loser_ratio=float(data.get("winner_loser_ratio", 0.0)),
            )
        )
    if not items:
        return None
    items.sort(key=lambda g: (g.winner_loser_ratio, g.counterfactual_pnl_delta), reverse=True)
    return items[0]


def build_promotion_summary(
    *,
    baseline_report: dict,
    trade_path_db_path: Path,
    mae_mfe_report: dict,
    candidate_report: dict | None = None,
) -> dict:
    trade_db = TradePathDatabase.load_jsonl(trade_path_db_path)
    trade_summary = asdict(trade_db.summary())
    baseline = _baseline_metrics(baseline_report.get("report", baseline_report))
    candidate = _baseline_metrics(candidate_report.get("report", candidate_report)) if candidate_report else None

    shadow_gates = mae_mfe_report.get("shadow_gates", {})
    best_mae_gate = _best_gate(shadow_gates, "mae_")
    best_mfe_gate = _best_gate(shadow_gates, "mfe_")

    verdict_reasons: list[str] = []
    eligible = True

    if baseline["trades"] <= 0:
        eligible = False
        verdict_reasons.append("NO_BASELINE_TRADES")
    if not baseline["dsr_passed"]:
        verdict_reasons.append("BASELINE_DSR_NOT_PASSED")

    if best_mae_gate is None:
        eligible = False
        verdict_reasons.append("NO_MAE_GATE")
    else:
        if best_mae_gate.winner_loser_ratio < 1.5:
            eligible = False
            verdict_reasons.append("MAE_GATE_RATIO_TOO_LOW")
        if best_mae_gate.counterfactual_pnl_delta <= 0:
            eligible = False
            verdict_reasons.append("MAE_GATE_PNL_NOT_POSITIVE")

    if candidate is not None:
        candidate_delta = {
            "trades": candidate["trades"] - baseline["trades"],
            "win_rate": round(candidate["win_rate"] - baseline["win_rate"], 6),
            "total_pnl": round(candidate["total_pnl"] - baseline["total_pnl"], 2),
            "sharpe": round(candidate["sharpe"] - baseline["sharpe"], 4),
            "ending_equity": round(candidate["ending_equity"] - baseline["ending_equity"], 2),
        }
    else:
        candidate_delta = None

    if best_mfe_gate is not None and best_mfe_gate.counterfactual_pnl_delta <= 0:
        verdict_reasons.append("MFE_GATE_PNL_NOT_POSITIVE")

    verdict = {
        "eligible": eligible,
        "reasons": verdict_reasons,
        "baseline": baseline,
        "trade_path_db": trade_summary,
        "best_mae_gate": asdict(best_mae_gate) if best_mae_gate is not None else None,
        "best_mfe_gate": asdict(best_mfe_gate) if best_mfe_gate is not None else None,
        "candidate_delta": candidate_delta,
        "promotion_label": _promotion_label(eligible, verdict_reasons, best_mae_gate),
    }
    return verdict


def _promotion_label(eligible: bool, reasons: list[str], best_mae_gate: GateHighlight | None) -> str:
    if eligible and best_mae_gate is not None:
        return "PROMOTE_MAE_GATE"
    if "NO_BASELINE_TRADES" in reasons:
        return "INSUFFICIENT_DATA"
    if "MAE_GATE_RATIO_TOO_LOW" in reasons:
        return "NEEDS_SHARPER_GATE"
    if "MAE_GATE_PNL_NOT_POSITIVE" in reasons:
        return "NON_POSITIVE_GATE"
    return "REVIEW_ONLY"
