"""Pydantic models for data quality validation.

``ValidationResult`` is the return type of every rule in the validation
service and is embedded in pipeline output before DB insertion.
"""

from pydantic import BaseModel, Field

from app.models.energy import QualityFlag


class ValidationResult(BaseModel):
    """Result of a single validation rule evaluation.

    Attributes:
        flag: Severity level of the result.
        rule_name: Machine-readable name of the rule that was evaluated,
            e.g. ``"no_negative_values"``.
        notes: Human-readable explanation, populated when flag is not ``ok``.
        passed: Convenience bool — True when flag is QualityFlag.OK.
    """

    flag: QualityFlag = QualityFlag.OK
    rule_name: str = Field(min_length=1)
    notes: str | None = None

    @property
    def passed(self) -> bool:
        """Return True if the validation rule passed without issues."""
        return self.flag == QualityFlag.OK


class ValidationSummary(BaseModel):
    """Aggregated result of all rules applied to a single record.

    Attributes:
        overall_flag: Worst flag across all results
            (error > warning > ok).
        results: Individual result per rule.
        combined_notes: Newline-joined notes from all non-ok results.
    """

    results: list[ValidationResult] = Field(default_factory=list)

    @property
    def overall_flag(self) -> QualityFlag:
        """Return the most severe flag across all results."""
        flags = {r.flag for r in self.results}
        if QualityFlag.ERROR in flags:
            return QualityFlag.ERROR
        if QualityFlag.WARNING in flags:
            return QualityFlag.WARNING
        return QualityFlag.OK

    @property
    def combined_notes(self) -> str | None:
        """Return newline-joined notes from all non-ok results, or None."""
        notes = [r.notes for r in self.results if r.notes and not r.passed]
        return "\n".join(notes) if notes else None
