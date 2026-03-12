"""Validation service — data quality business rules engine.

Each rule is a method that accepts an ``EnergyRecordCreate`` and returns a
``ValidationResult``. The public ``validate`` method runs all rules and
returns a ``ValidationSummary`` with the aggregate outcome.

Usage::

    from app.services.validation import ValidationService
    from app.models.energy import EnergyRecordCreate

    record = EnergyRecordCreate(...)
    summary = ValidationService.validate(record)

    if summary.overall_flag != QualityFlag.OK:
        print(summary.combined_notes)
"""

from datetime import date

from app.models.energy import EnergyRecordCreate, GenerationType, QualityFlag
from app.models.quality import ValidationResult, ValidationSummary

# ---------------------------------------------------------------------------
# Installed capacity constants (MW) — Ecuador 2024 approximate figures.
# Used as upper bounds for plausibility checks.
# Source: ARCERNNR Boletín Estadístico 2023.
# ---------------------------------------------------------------------------
INSTALLED_CAPACITY_MW: dict[GenerationType, float] = {
    GenerationType.HYDRAULIC: 5_200.0,
    GenerationType.THERMAL: 3_800.0,
    GenerationType.SOLAR: 250.0,
    GenerationType.WIND: 50.0,
    GenerationType.BIOMASS: 120.0,
    GenerationType.OTHER: 500.0,
}

# Maximum daily MWh = installed MW × 24 h × safety margin
_HOURS_PER_DAY = 24.0
_CAPACITY_MARGIN = 1.05  # 5% tolerance for rounding / measurement error

# Reasonable lower warning threshold (suspiciously low non-zero generation)
_MIN_NONZERO_MWH: dict[GenerationType, float] = {
    GenerationType.HYDRAULIC: 1.0,
    GenerationType.THERMAL: 1.0,
    GenerationType.SOLAR: 0.1,
    GenerationType.WIND: 0.1,
    GenerationType.BIOMASS: 0.1,
    GenerationType.OTHER: 0.01,
}

_MIN_VALID_YEAR = 2000


class ValidationService:
    """Stateless collection of validation rules for energy records.

    All rule methods are classmethods so the service can be used without
    instantiation.
    """

    @classmethod
    def validate(cls, record: EnergyRecordCreate) -> ValidationSummary:
        """Run all validation rules against a record and return a summary.

        Args:
            record: The energy record to validate.

        Returns:
            ``ValidationSummary`` with results from every rule.
        """
        rules = [
            cls.required_fields,
            cls.no_negative_values,
            cls.value_range,
            cls.hydraulic_capacity,
            cls.date_in_range,
        ]
        results = [rule(record) for rule in rules]
        return ValidationSummary(results=results)

    # ------------------------------------------------------------------
    # Rules
    # ------------------------------------------------------------------

    @classmethod
    def required_fields(cls, record: EnergyRecordCreate) -> ValidationResult:
        """Ensure mandatory fields are present and non-empty.

        Args:
            record: Energy record to check.

        Returns:
            ``ValidationResult`` with flag ERROR if any required field is
            missing or empty.
        """
        missing: list[str] = []

        if not record.source:
            missing.append("source")
        if not record.record_date:
            missing.append("record_date")
        if not record.generation_type:
            missing.append("generation_type")
        if not record.country_code or len(record.country_code.strip()) != 2:
            missing.append("country_code")

        if missing:
            return ValidationResult(
                flag=QualityFlag.ERROR,
                rule_name="required_fields",
                notes=f"Missing or invalid required fields: {', '.join(missing)}.",
            )

        return ValidationResult(flag=QualityFlag.OK, rule_name="required_fields")

    @classmethod
    def no_negative_values(cls, record: EnergyRecordCreate) -> ValidationResult:
        """Ensure value_mwh is not negative.

        Args:
            record: Energy record to check.

        Returns:
            ``ValidationResult`` with flag ERROR for negative values,
            WARNING for exactly zero (possible missing data).
        """
        if record.value_mwh is None:
            return ValidationResult(
                flag=QualityFlag.WARNING,
                rule_name="no_negative_values",
                notes="value_mwh is null — may indicate missing data.",
            )

        if record.value_mwh < 0:
            return ValidationResult(
                flag=QualityFlag.ERROR,
                rule_name="no_negative_values",
                notes=f"Negative value_mwh={record.value_mwh} is physically impossible.",
            )

        if record.value_mwh == 0.0:
            return ValidationResult(
                flag=QualityFlag.WARNING,
                rule_name="no_negative_values",
                notes="value_mwh=0 — verify the generation unit was offline.",
            )

        return ValidationResult(flag=QualityFlag.OK, rule_name="no_negative_values")

    @classmethod
    def value_range(cls, record: EnergyRecordCreate) -> ValidationResult:
        """Check value_mwh against reasonable bounds per generation type.

        Args:
            record: Energy record to check.

        Returns:
            ``ValidationResult`` with WARNING for suspiciously low non-zero
            values and ERROR for values exceeding theoretical daily capacity.
        """
        if record.value_mwh is None:
            return ValidationResult(flag=QualityFlag.OK, rule_name="value_range")

        capacity = INSTALLED_CAPACITY_MW.get(record.generation_type, 500.0)
        max_daily_mwh = capacity * _HOURS_PER_DAY * _CAPACITY_MARGIN
        min_nonzero = _MIN_NONZERO_MWH.get(record.generation_type, 0.01)

        if record.value_mwh > max_daily_mwh:
            return ValidationResult(
                flag=QualityFlag.ERROR,
                rule_name="value_range",
                notes=(
                    f"value_mwh={record.value_mwh:.2f} exceeds theoretical maximum "
                    f"{max_daily_mwh:.2f} MWh/day for {record.generation_type}."
                ),
            )

        if 0 < record.value_mwh < min_nonzero:
            return ValidationResult(
                flag=QualityFlag.WARNING,
                rule_name="value_range",
                notes=(
                    f"value_mwh={record.value_mwh:.4f} is below the plausibility "
                    f"threshold {min_nonzero} MWh for {record.generation_type}."
                ),
            )

        return ValidationResult(flag=QualityFlag.OK, rule_name="value_range")

    @classmethod
    def hydraulic_capacity(cls, record: EnergyRecordCreate) -> ValidationResult:
        """Check hydraulic generation against Ecuador's installed capacity.

        This rule only applies to hydraulic records and acts as a tighter
        cross-check beyond the generic ``value_range`` rule.

        Args:
            record: Energy record to check.

        Returns:
            ``ValidationResult`` with WARNING if generation exceeds 90% of
            daily capacity (possible sensor error), ERROR if it exceeds 100%.
        """
        if record.generation_type != GenerationType.HYDRAULIC:
            return ValidationResult(
                flag=QualityFlag.OK, rule_name="hydraulic_capacity"
            )

        if record.value_mwh is None:
            return ValidationResult(
                flag=QualityFlag.OK, rule_name="hydraulic_capacity"
            )

        capacity = INSTALLED_CAPACITY_MW[GenerationType.HYDRAULIC]
        max_mwh = capacity * _HOURS_PER_DAY
        warning_threshold = max_mwh * 0.90

        if record.value_mwh > max_mwh:
            return ValidationResult(
                flag=QualityFlag.ERROR,
                rule_name="hydraulic_capacity",
                notes=(
                    f"Hydraulic generation {record.value_mwh:.2f} MWh exceeds "
                    f"installed capacity ceiling {max_mwh:.2f} MWh/day."
                ),
            )

        if record.value_mwh > warning_threshold:
            return ValidationResult(
                flag=QualityFlag.WARNING,
                rule_name="hydraulic_capacity",
                notes=(
                    f"Hydraulic generation {record.value_mwh:.2f} MWh is above "
                    f"90% of daily capacity ({warning_threshold:.2f} MWh). "
                    "Verify sensor data."
                ),
            )

        return ValidationResult(flag=QualityFlag.OK, rule_name="hydraulic_capacity")

    @classmethod
    def date_in_range(cls, record: EnergyRecordCreate) -> ValidationResult:
        """Ensure record_date is not in the future and not before 2000.

        Args:
            record: Energy record to check.

        Returns:
            ``ValidationResult`` with ERROR for future dates or dates before
            the minimum valid year, WARNING for dates more than 7 days old
            that could indicate a delayed ingestion.
        """
        today = date.today()

        if record.record_date > today:
            return ValidationResult(
                flag=QualityFlag.ERROR,
                rule_name="date_in_range",
                notes=(
                    f"record_date={record.record_date} is in the future "
                    f"(today={today})."
                ),
            )

        if record.record_date.year < _MIN_VALID_YEAR:
            return ValidationResult(
                flag=QualityFlag.ERROR,
                rule_name="date_in_range",
                notes=(
                    f"record_date={record.record_date} is before the minimum "
                    f"valid year {_MIN_VALID_YEAR}."
                ),
            )

        days_old = (today - record.record_date).days
        if days_old > 7:
            return ValidationResult(
                flag=QualityFlag.WARNING,
                rule_name="date_in_range",
                notes=(
                    f"record_date={record.record_date} is {days_old} days old. "
                    "Verify this is not a late-arriving duplicate."
                ),
            )

        return ValidationResult(flag=QualityFlag.OK, rule_name="date_in_range")
