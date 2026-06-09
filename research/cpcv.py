"""Combinatorial Purged Cross-Validation (CPCV) helpers — V8.4.

Provides purging and embargoing utilities to prevent lookahead bias and label leakage
in backtesting and walk-forward evaluations.
References:
  Lopez de Prado (2018) "Advances in Financial Machine Learning", Ch. 7.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence


@dataclass(frozen=True)
class TrainTestSplit:
    train_indices: list[int]
    test_indices: list[int]


def purge_and_embargo_splits(
    event_times: Sequence[int],       # entry timestamps (e.g. nanoseconds or indices)
    exit_times: Sequence[int],        # exit timestamps corresponding to entries
    test_start: int,                  # test start timestamp
    test_end: int,                    # test end timestamp
    embargo_duration: int = 0,        # embargo duration in the same units as event_times
) -> list[int]:
    """Purge and embargo training indices relative to a test window.

    Purging: Removes any training sample whose label evaluation period overlaps with the test set.
    Embargoing: Removes training samples immediately after the test set to handle serial correlation.
    """
    if len(event_times) == 0:
        return []

    embargo_limit = test_end + embargo_duration
    safe_train_indices = []

    for idx, (entry, exit_val) in enumerate(zip(event_times, exit_times)):
        # If the sample is inside the test set, it cannot be in the training set
        if test_start <= entry <= test_end:
            continue

        # Purging check:
        # Case 1: Training entry starts before the test set, but its exit overlaps into the test set
        if entry < test_start and exit_val >= test_start:
            continue

        # Embargoing check:
        # Case 2: Training entry falls within the embargo window right after the test set
        if test_end < entry <= embargo_limit:
            continue

        safe_train_indices.append(idx)

    return safe_train_indices
