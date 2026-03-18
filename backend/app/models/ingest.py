"""Pydantic models for ETL ingestion reporting."""

from datetime import datetime
from pydantic import BaseModel, Field


class PipelineResult(BaseModel):
    """Result from a single pipeline run.

    Attributes:
        pipeline: Machine-readable pipeline name.
        records_inserted: Number of rows written to the DB.
        records_skipped: Rows skipped (duplicates / quality errors).
        warnings: Non-fatal issues encountered.
        errors: Fatal errors that stopped the pipeline.
        duration_seconds: Wall-clock time for this pipeline.
    """

    pipeline: str
    records_inserted: int = 0
    records_skipped: int = 0
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    duration_seconds: float = 0.0

    @property
    def success(self) -> bool:
        """Return True if no errors were recorded."""
        return len(self.errors) == 0


class IngestSummary(BaseModel):
    """Aggregated result from a full ingestion cycle.

    Attributes:
        started_at: UTC timestamp when the cycle began.
        finished_at: UTC timestamp when the cycle ended.
        pipelines: Individual result per pipeline.
    """

    started_at: datetime = Field(default_factory=datetime.utcnow)
    finished_at: datetime | None = None
    pipelines: list[PipelineResult] = Field(default_factory=list)

    @property
    def total_inserted(self) -> int:
        """Total records inserted across all pipelines."""
        return sum(p.records_inserted for p in self.pipelines)

    @property
    def total_errors(self) -> int:
        """Total error count across all pipelines."""
        return sum(len(p.errors) for p in self.pipelines)

    @property
    def total_warnings(self) -> int:
        """Total warning count across all pipelines."""
        return sum(len(p.warnings) for p in self.pipelines)

    @property
    def duration_seconds(self) -> float:
        """Total wall-clock duration of the ingestion cycle."""
        if self.finished_at is None:
            return 0.0
        return (self.finished_at - self.started_at).total_seconds()
