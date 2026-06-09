"""MAE/MFE Exit Laboratory — V8.3.

Transforms Maximum Adverse/Favorable Excursion data from a summary report
into a queryable historical trade-path database. Provides:

  - TradePath: per-trade MAE/MFE record with regime/session/signal context.
  - MAEMFEExitLab: in-memory store with percentile-based exit research.
  - Shadow gate: passive counterfactual exit testing (does NOT alter trades).

References:
  Sweeney (1996) "Technical Analysis in the Foreign Exchange Market".
  Lopez de Prado (2018) "Advances in Financial Machine Learning", Ch. 3.
"""

from __future__ import annotations

import json
import math
import statistics
from collections import defaultdict
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class TradePath:
    """Complete trade path record for MAE/MFE research."""
    trade_id: str
    signal_id: str
    symbol: str
    side: int                          # +1 long, -1 short
    entry_ts_ns: int
    exit_ts_ns: int
    entry_price: float
    exit_price: float
    mae: float                         # Maximum Adverse Excursion (as fraction)
    mfe: float                         # Maximum Favorable Excursion (as fraction)
    mae_r: float                       # MAE in R-multiples (mae / risk)
    mfe_r: float                       # MFE in R-multiples (mfe / risk)
    pnl: float                         # Net PnL in currency units
    pnl_r: float                       # PnL in R-multiples
    win: bool                          # True if pnl > 0
    exit_reason: str                   # TARGET, STOP, BAR_EXIT, TIME, etc.
    signal_family: str                 # volume_bar_cvd, swing, momentum, etc.
    regime: str                        # RANGING, TREND_BULL, etc.
    session_hour_utc: int              # 0-23
    volatility_bucket: str             # LOW, MED, HIGH
    bars_held: int
    max_hold_bars: int
    target_pct: float
    stop_pct: float
    # Optional diagnostics (None if engine not active)
    toxicity_state: Optional[str] = None
    mlofi_zscore: Optional[float] = None
    book_agreement: Optional[float] = None


@dataclass
class PercentileExitResult:
    """Result of a passive percentile-based exit counterfactual."""
    name: str
    mae_threshold: Optional[float]     # Exit if MAE exceeds this fraction
    mfe_threshold: Optional[float]     # Take profit if MFE exceeds this fraction
    trades_evaluated: int
    would_exit_early: int
    early_exits_that_were_winners: int
    early_exits_that_were_losers: int
    counterfactual_win_rate: float
    counterfactual_pnl_delta: float    # Estimated PnL change vs baseline
    winner_loser_ratio: float          # blocked_losers / blocked_winners


@dataclass
class MAEMFEReport:
    """Aggregated MAE/MFE report for a group of trade paths."""
    group_key: str
    n_trades: int
    n_wins: int
    win_rate: float
    mae_mean: float
    mae_median: float
    mae_p75: float
    mae_p85: float
    mae_p90: float
    mae_p95: float
    mfe_mean: float
    mfe_median: float
    mfe_p50: float
    mfe_p70: float
    mfe_p80: float
    mfe_p90: float
    avg_bars_held: float
    winner_mae_p90: float              # MAE at 90th pct for winning trades
    loser_mae_p90: float               # MAE at 90th pct for losing trades
    winner_mfe_p50: float              # MFE at 50th pct for winning trades
    loser_mfe_p50: float               # MFE at 50th pct for losing trades


class MAEMFEExitLab:
    """In-memory MAE/MFE trade-path database with percentile exit research.

    Usage
    -----
    lab = MAEMFEExitLab()
    lab.add(trade_path)                # Add completed trades
    report = lab.report_by_regime()    # Grouped analysis
    shadow = lab.shadow_mae_gate(0.85) # Test 85th percentile MAE stop
    lab.export_jsonl(path)             # Persist to disk
    """

    def __init__(self) -> None:
        self._paths: list[TradePath] = []

    # ------------------------------------------------------------------
    # Data ingestion
    # ------------------------------------------------------------------

    def add(self, path: TradePath) -> None:
        """Append a completed trade path."""
        self._paths.append(path)

    def add_from_paper_trade(
        self,
        *,
        trade_id: str,
        signal_id: str,
        symbol: str,
        side: int,
        entry_ts_ns: int,
        exit_ts_ns: int,
        entry_price: float,
        exit_price: float,
        max_adverse: float,
        max_favorable: float,
        pnl: float,
        exit_reason: str,
        signal_family: str,
        regime: str,
        bars_held: int,
        max_hold_bars: int,
        target_pct: float,
        stop_pct: float,
        toxicity_state: Optional[str] = None,
        mlofi_zscore: Optional[float] = None,
        book_agreement: Optional[float] = None,
    ) -> TradePath:
        """Construct and store a TradePath from backtest PaperTrade fields."""
        risk = stop_pct if stop_pct > 0 else 0.01
        mae_r = max_adverse / risk
        mfe_r = max_favorable / risk
        pnl_r = (pnl / (entry_price * risk)) if (entry_price > 0 and risk > 0) else 0.0
        win = pnl > 0
        session_hour = _utc_hour(exit_ts_ns)
        vol_bucket = _volatility_bucket(max_adverse, max_favorable)

        path = TradePath(
            trade_id=trade_id,
            signal_id=signal_id,
            symbol=symbol,
            side=side,
            entry_ts_ns=entry_ts_ns,
            exit_ts_ns=exit_ts_ns,
            entry_price=entry_price,
            exit_price=exit_price,
            mae=max_adverse,
            mfe=max_favorable,
            mae_r=mae_r,
            mfe_r=mfe_r,
            pnl=pnl,
            pnl_r=pnl_r,
            win=win,
            exit_reason=exit_reason,
            signal_family=signal_family,
            regime=regime,
            session_hour_utc=session_hour,
            volatility_bucket=vol_bucket,
            bars_held=bars_held,
            max_hold_bars=max_hold_bars,
            target_pct=target_pct,
            stop_pct=stop_pct,
            toxicity_state=toxicity_state,
            mlofi_zscore=mlofi_zscore,
            book_agreement=book_agreement,
        )
        self._paths.append(path)
        return path

    # ------------------------------------------------------------------
    # Reporting
    # ------------------------------------------------------------------

    def report_by_regime(self) -> dict[str, MAEMFEReport]:
        """MAE/MFE statistics split by regime label."""
        return self._grouped_report(lambda p: p.regime)

    def report_by_signal_family(self) -> dict[str, MAEMFEReport]:
        """MAE/MFE statistics split by signal family."""
        return self._grouped_report(lambda p: p.signal_family)

    def report_by_session_hour(self) -> dict[str, MAEMFEReport]:
        """MAE/MFE statistics split by UTC session hour."""
        return self._grouped_report(lambda p: f"H{p.session_hour_utc:02d}")

    def report_by_toxicity(self) -> dict[str, MAEMFEReport]:
        """MAE/MFE statistics split by toxicity state."""
        return self._grouped_report(lambda p: p.toxicity_state or "UNKNOWN")

    def report_by_exit_reason(self) -> dict[str, MAEMFEReport]:
        """MAE/MFE statistics split by exit reason."""
        return self._grouped_report(lambda p: p.exit_reason)

    def full_report(self) -> dict:
        """Complete MAE/MFE report across all dimensions."""
        if not self._paths:
            return {"error": "no_trades"}
        all_report = self._build_report("ALL", self._paths)
        return {
            "all": asdict(all_report),
            "by_regime": {k: asdict(v) for k, v in self.report_by_regime().items()},
            "by_signal_family": {k: asdict(v) for k, v in self.report_by_signal_family().items()},
            "by_session_hour": {k: asdict(v) for k, v in self.report_by_session_hour().items()},
            "by_toxicity": {k: asdict(v) for k, v in self.report_by_toxicity().items()},
            "by_exit_reason": {k: asdict(v) for k, v in self.report_by_exit_reason().items()},
            "shadow_gates": self.shadow_all_gates(),
        }

    # ------------------------------------------------------------------
    # Shadow gate research (PASSIVE — does NOT alter any live trade)
    # ------------------------------------------------------------------

    def shadow_mae_gate(self, mae_percentile: float) -> PercentileExitResult:
        """Evaluate: what if we exited when MAE exceeded the Nth percentile?

        Parameters
        ----------
        mae_percentile : float
            Percentile (0-1) of MAE distribution used as exit threshold.
            e.g. 0.85 = exit if current MAE exceeds 85th percentile of all MAEs.
        """
        if not self._paths:
            return self._empty_gate(f"mae_p{int(mae_percentile*100)}")
        all_maes = sorted(p.mae for p in self._paths)
        threshold = _percentile(all_maes, mae_percentile)
        name = f"mae_p{int(mae_percentile*100)}_gate"
        return self._evaluate_mae_gate(name, threshold)

    def shadow_mfe_gate(self, mfe_percentile: float) -> PercentileExitResult:
        """Evaluate: what if we took profit when MFE exceeded the Nth percentile?"""
        if not self._paths:
            return self._empty_gate(f"mfe_p{int(mfe_percentile*100)}")
        all_mfes = sorted(p.mfe for p in self._paths)
        threshold = _percentile(all_mfes, mfe_percentile)
        name = f"mfe_p{int(mfe_percentile*100)}_gate"
        return self._evaluate_mfe_gate(name, threshold)

    def shadow_all_gates(self) -> dict[str, dict]:
        """Run all standard shadow gate evaluations and return a summary."""
        results = {}
        for pct in [0.70, 0.75, 0.80, 0.85, 0.90, 0.95]:
            r = self.shadow_mae_gate(pct)
            results[r.name] = asdict(r)
        for pct in [0.50, 0.60, 0.70, 0.80, 0.90]:
            r = self.shadow_mfe_gate(pct)
            results[r.name] = asdict(r)
        return results

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def export_jsonl(self, path: Path) -> None:
        """Write all trade paths to a JSONL file."""
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as fh:
            for p in self._paths:
                fh.write(json.dumps(asdict(p), sort_keys=True))
                fh.write("\n")

    def export_report_json(self, path: Path) -> None:
        """Write the full report to a JSON file."""
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as fh:
            json.dump(self.full_report(), fh, indent=2, sort_keys=True)

    @classmethod
    def load_jsonl(cls, path: Path) -> "MAEMFEExitLab":
        """Load trade paths from a previously exported JSONL file."""
        lab = cls()
        with path.open(encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                data = json.loads(line)
                lab.add(TradePath(**data))
        return lab

    def __len__(self) -> int:
        return len(self._paths)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _grouped_report(self, key_fn) -> dict[str, MAEMFEReport]:
        groups: dict[str, list[TradePath]] = defaultdict(list)
        for p in self._paths:
            groups[key_fn(p)].append(p)
        return {k: self._build_report(k, v) for k, v in sorted(groups.items())}

    @staticmethod
    def _build_report(group_key: str, paths: list[TradePath]) -> MAEMFEReport:
        if not paths:
            return MAEMFEReport(
                group_key=group_key, n_trades=0, n_wins=0, win_rate=0.0,
                mae_mean=0.0, mae_median=0.0, mae_p75=0.0, mae_p85=0.0,
                mae_p90=0.0, mae_p95=0.0, mfe_mean=0.0, mfe_median=0.0,
                mfe_p50=0.0, mfe_p70=0.0, mfe_p80=0.0, mfe_p90=0.0,
                avg_bars_held=0.0, winner_mae_p90=0.0, loser_mae_p90=0.0,
                winner_mfe_p50=0.0, loser_mfe_p50=0.0,
            )
        n = len(paths)
        wins = [p for p in paths if p.win]
        losses = [p for p in paths if not p.win]
        maes = sorted(p.mae for p in paths)
        mfes = sorted(p.mfe for p in paths)
        return MAEMFEReport(
            group_key=group_key,
            n_trades=n,
            n_wins=len(wins),
            win_rate=round(len(wins) / n, 4),
            mae_mean=round(statistics.mean(maes), 6),
            mae_median=round(statistics.median(maes), 6),
            mae_p75=round(_percentile(maes, 0.75), 6),
            mae_p85=round(_percentile(maes, 0.85), 6),
            mae_p90=round(_percentile(maes, 0.90), 6),
            mae_p95=round(_percentile(maes, 0.95), 6),
            mfe_mean=round(statistics.mean(mfes), 6),
            mfe_median=round(statistics.median(mfes), 6),
            mfe_p50=round(_percentile(mfes, 0.50), 6),
            mfe_p70=round(_percentile(mfes, 0.70), 6),
            mfe_p80=round(_percentile(mfes, 0.80), 6),
            mfe_p90=round(_percentile(mfes, 0.90), 6),
            avg_bars_held=round(statistics.mean(p.bars_held for p in paths), 2),
            winner_mae_p90=round(_percentile(sorted(p.mae for p in wins), 0.90), 6) if wins else 0.0,
            loser_mae_p90=round(_percentile(sorted(p.mae for p in losses), 0.90), 6) if losses else 0.0,
            winner_mfe_p50=round(_percentile(sorted(p.mfe for p in wins), 0.50), 6) if wins else 0.0,
            loser_mfe_p50=round(_percentile(sorted(p.mfe for p in losses), 0.50), 6) if losses else 0.0,
        )

    def _evaluate_mae_gate(self, name: str, threshold: float) -> PercentileExitResult:
        evaluated = early = win_early = loss_early = 0
        pnl_delta = 0.0
        for p in self._paths:
            evaluated += 1
            if p.mae > threshold:
                early += 1
                if p.win:
                    win_early += 1
                else:
                    loss_early += 1
                    pnl_delta += abs(p.pnl) * 0.5  # rough estimate: save half the loss
                    pnl_delta -= p.pnl * 0.1  # cost of exiting winners early
        kept = evaluated - early
        kept_wins = sum(1 for p in self._paths if p.win and p.mae <= threshold)
        kept_total = sum(1 for p in self._paths if p.mae <= threshold)
        cfwr = kept_wins / kept_total if kept_total else 0.0
        wl_ratio = loss_early / max(win_early, 1)
        return PercentileExitResult(
            name=name,
            mae_threshold=round(threshold, 6),
            mfe_threshold=None,
            trades_evaluated=evaluated,
            would_exit_early=early,
            early_exits_that_were_winners=win_early,
            early_exits_that_were_losers=loss_early,
            counterfactual_win_rate=round(cfwr, 4),
            counterfactual_pnl_delta=round(pnl_delta, 2),
            winner_loser_ratio=round(wl_ratio, 3),
        )

    def _evaluate_mfe_gate(self, name: str, threshold: float) -> PercentileExitResult:
        evaluated = early = win_early = loss_early = 0
        pnl_delta = 0.0
        for p in self._paths:
            evaluated += 1
            if p.mfe > threshold:
                early += 1
                if p.win:
                    win_early += 1
                    pnl_delta += p.pnl * 0.2  # capture some of the winner early
                else:
                    loss_early += 1  # taking profit on what becomes a loser = good
                    pnl_delta += abs(p.pnl) * 0.3
        kept = evaluated - early
        kept_wins = sum(1 for p in self._paths if p.win and p.mfe <= threshold)
        kept_total = sum(1 for p in self._paths if p.mfe <= threshold)
        cfwr = kept_wins / kept_total if kept_total else 0.0
        wl_ratio = loss_early / max(win_early, 1)
        return PercentileExitResult(
            name=name,
            mae_threshold=None,
            mfe_threshold=round(threshold, 6),
            trades_evaluated=evaluated,
            would_exit_early=early,
            early_exits_that_were_winners=win_early,
            early_exits_that_were_losers=loss_early,
            counterfactual_win_rate=round(cfwr, 4),
            counterfactual_pnl_delta=round(pnl_delta, 2),
            winner_loser_ratio=round(wl_ratio, 3),
        )

    @staticmethod
    def _empty_gate(name: str) -> PercentileExitResult:
        return PercentileExitResult(
            name=name, mae_threshold=None, mfe_threshold=None,
            trades_evaluated=0, would_exit_early=0,
            early_exits_that_were_winners=0, early_exits_that_were_losers=0,
            counterfactual_win_rate=0.0, counterfactual_pnl_delta=0.0,
            winner_loser_ratio=0.0,
        )


# ------------------------------------------------------------------
# Internal helpers
# ------------------------------------------------------------------

def _percentile(sorted_values: list[float], p: float) -> float:
    if not sorted_values:
        return 0.0
    n = len(sorted_values)
    idx = min(n - 1, int(n * p))
    return sorted_values[idx]


def _utc_hour(ts_ns: int) -> int:
    return (ts_ns // 1_000_000_000 // 3600) % 24


def _volatility_bucket(mae: float, mfe: float) -> str:
    excursion = max(mae, mfe)
    if excursion < 0.002:
        return "LOW"
    if excursion < 0.008:
        return "MED"
    return "HIGH"
