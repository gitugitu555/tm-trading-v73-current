"""Stage protocol for composable V7.2 pipeline."""

from __future__ import annotations

from typing import Protocol

from core.types import BookSnapshot
from v72.contracts import V72PipelineState


class PipelineStage(Protocol):
    stage_id: str

    def process(
        self,
        state: V72PipelineState,
        *,
        book: BookSnapshot | None = None,
    ) -> V72PipelineState: ...