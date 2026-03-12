"""Tests for the ValidationService business rules engine.

Each rule is tested with valid input, boundary cases, and invalid input
to achieve full branch coverage.
"""

from datetime import date, timedelta

import pytest

from app.models.energy import DataSource, EnergyRecordCreate, GenerationType, QualityFlag
from app.services.validation import (
    INSTALLED_CAPACITY_MW,
    ValidationService,
    _HOURS_PER_DAY,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_record(**kwargs) -> EnergyRecordCreate:
    """Return a valid EnergyRecordCreate with sensible defaults.

    Any field can be overridden via keyword arguments.
    """
    defaults = dict(
        source=DataSource.CENACE_CKAN,
        country_code="EC",
        record_date=date.today() - timedelta(days=1),
        generation_type=GenerationType.HYDRAULIC,
        value_mwh=1_000.0,
    )
    defaults.update(kwargs)
    return EnergyRecordCreate(**defaults)


# ---------------------------------------------------------------------------
# required_fields
# ---------------------------------------------------------------------------

class TestRequiredFields:
    def test_valid_record_passes(self):
        result = ValidationService.required_fields(make_record())
        assert result.flag == QualityFlag.OK
        assert result.passed

    def test_invalid_country_code_single_char_errors(self):
        record = EnergyRecordCreate.model_construct(
            source=DataSource.CENACE_CKAN,
            country_code="E",
            record_date=date.today() - timedelta(days=1),
            generation_type=GenerationType.HYDRAULIC,
            value_mwh=1_000.0,
        )
        result = ValidationService.required_fields(record)
        assert result.flag == QualityFlag.ERROR
        assert "country_code" in result.notes  # type: ignore[operator]

    def test_invalid_country_code_three_chars_errors(self):
        record = EnergyRecordCreate.model_construct(
            source=DataSource.CENACE_CKAN,
            country_code="ECU",
            record_date=date.today() - timedelta(days=1),
            generation_type=GenerationType.HYDRAULIC,
            value_mwh=1_000.0,
        )
        result = ValidationService.required_fields(record)
        assert result.flag == QualityFlag.ERROR

    def test_whitespace_country_code_errors(self):
        result = ValidationService.required_fields(make_record(country_code="  "))
        assert result.flag == QualityFlag.ERROR


# ---------------------------------------------------------------------------
# no_negative_values
# ---------------------------------------------------------------------------

class TestNoNegativeValues:
    def test_positive_value_passes(self):
        result = ValidationService.no_negative_values(make_record(value_mwh=500.0))
        assert result.flag == QualityFlag.OK

    def test_negative_value_errors(self):
        record = EnergyRecordCreate.model_construct(
            source=DataSource.CENACE_CKAN,
            country_code="EC",
            record_date=date.today() - timedelta(days=1),
            generation_type=GenerationType.HYDRAULIC,
            value_mwh=-1.0,
        )
        result = ValidationService.no_negative_values(record)
        assert result.flag == QualityFlag.ERROR
        assert result.notes is not None

    def test_zero_value_warns(self):
        result = ValidationService.no_negative_values(make_record(value_mwh=0.0))
        assert result.flag == QualityFlag.WARNING

    def test_none_value_warns(self):
        result = ValidationService.no_negative_values(make_record(value_mwh=None))
        assert result.flag == QualityFlag.WARNING

    def test_large_positive_passes(self):
        result = ValidationService.no_negative_values(make_record(value_mwh=50_000.0))
        assert result.flag == QualityFlag.OK


# ---------------------------------------------------------------------------
# value_range
# ---------------------------------------------------------------------------

class TestValueRange:
    def test_normal_hydraulic_passes(self):
        result = ValidationService.value_range(make_record(
            generation_type=GenerationType.HYDRAULIC, value_mwh=10_000.0
        ))
        assert result.flag == QualityFlag.OK

    def test_exceeds_daily_capacity_errors(self):
        capacity = INSTALLED_CAPACITY_MW[GenerationType.HYDRAULIC]
        excessive = capacity * _HOURS_PER_DAY * 2  # double theoretical max
        result = ValidationService.value_range(make_record(
            generation_type=GenerationType.HYDRAULIC, value_mwh=excessive
        ))
        assert result.flag == QualityFlag.ERROR

    def test_below_plausibility_threshold_warns(self):
        result = ValidationService.value_range(make_record(
            generation_type=GenerationType.SOLAR, value_mwh=0.001
        ))
        assert result.flag == QualityFlag.WARNING

    def test_none_value_passes_range_check(self):
        result = ValidationService.value_range(make_record(value_mwh=None))
        assert result.flag == QualityFlag.OK

    def test_thermal_at_boundary_passes(self):
        capacity = INSTALLED_CAPACITY_MW[GenerationType.THERMAL]
        boundary = capacity * _HOURS_PER_DAY * 1.04  # just under 1.05 margin
        result = ValidationService.value_range(make_record(
            generation_type=GenerationType.THERMAL, value_mwh=boundary
        ))
        assert result.flag == QualityFlag.OK

    def test_wind_normal_value_passes(self):
        result = ValidationService.value_range(make_record(
            generation_type=GenerationType.WIND, value_mwh=200.0
        ))
        assert result.flag == QualityFlag.OK


# ---------------------------------------------------------------------------
# hydraulic_capacity
# ---------------------------------------------------------------------------

class TestHydraulicCapacity:
    def test_non_hydraulic_skipped(self):
        result = ValidationService.hydraulic_capacity(make_record(
            generation_type=GenerationType.THERMAL, value_mwh=999_999.0
        ))
        assert result.flag == QualityFlag.OK

    def test_normal_hydraulic_passes(self):
        result = ValidationService.hydraulic_capacity(make_record(
            generation_type=GenerationType.HYDRAULIC, value_mwh=50_000.0
        ))
        assert result.flag == QualityFlag.OK

    def test_above_90_percent_warns(self):
        capacity = INSTALLED_CAPACITY_MW[GenerationType.HYDRAULIC]
        high_value = capacity * _HOURS_PER_DAY * 0.92
        result = ValidationService.hydraulic_capacity(make_record(
            generation_type=GenerationType.HYDRAULIC, value_mwh=high_value
        ))
        assert result.flag == QualityFlag.WARNING

    def test_above_100_percent_errors(self):
        capacity = INSTALLED_CAPACITY_MW[GenerationType.HYDRAULIC]
        over_capacity = capacity * _HOURS_PER_DAY * 1.1
        result = ValidationService.hydraulic_capacity(make_record(
            generation_type=GenerationType.HYDRAULIC, value_mwh=over_capacity
        ))
        assert result.flag == QualityFlag.ERROR

    def test_none_value_passes(self):
        result = ValidationService.hydraulic_capacity(make_record(
            generation_type=GenerationType.HYDRAULIC, value_mwh=None
        ))
        assert result.flag == QualityFlag.OK


# ---------------------------------------------------------------------------
# date_in_range
# ---------------------------------------------------------------------------

class TestDateInRange:
    def test_yesterday_passes(self):
        result = ValidationService.date_in_range(make_record(
            record_date=date.today() - timedelta(days=1)
        ))
        assert result.flag == QualityFlag.OK

    def test_future_date_errors(self):
        result = ValidationService.date_in_range(make_record(
            record_date=date.today() + timedelta(days=1)
        ))
        assert result.flag == QualityFlag.ERROR

    def test_today_passes(self):
        result = ValidationService.date_in_range(make_record(
            record_date=date.today()
        ))
        assert result.flag == QualityFlag.OK

    def test_before_2000_errors(self):
        result = ValidationService.date_in_range(make_record(
            record_date=date(1999, 12, 31)
        ))
        assert result.flag == QualityFlag.ERROR

    def test_exactly_2000_passes(self):
        result = ValidationService.date_in_range(make_record(
            record_date=date(2000, 1, 1)
        ))
        assert result.flag in (QualityFlag.OK, QualityFlag.WARNING)

    def test_8_days_old_warns(self):
        result = ValidationService.date_in_range(make_record(
            record_date=date.today() - timedelta(days=8)
        ))
        assert result.flag == QualityFlag.WARNING


# ---------------------------------------------------------------------------
# ValidationSummary / validate() integration
# ---------------------------------------------------------------------------

class TestValidationSummary:
    def test_clean_record_overall_ok(self):
        summary = ValidationService.validate(make_record())
        assert summary.overall_flag == QualityFlag.OK
        assert summary.combined_notes is None
        assert all(r.passed for r in summary.results)

    def test_error_dominates_warning(self):
        """A record with both a warning and an error should report ERROR overall."""
        record = EnergyRecordCreate.model_construct(
            source=DataSource.CENACE_CKAN,
            country_code="EC",
            record_date=date.today() - timedelta(days=8),
            generation_type=GenerationType.HYDRAULIC,
            value_mwh=-5.0,
        )
        summary = ValidationService.validate(record)
        assert summary.overall_flag == QualityFlag.ERROR

    def test_combined_notes_join_all_issues(self):
        record = EnergyRecordCreate.model_construct(
            source=DataSource.CENACE_CKAN,
            country_code="EC",
            record_date=date.today() + timedelta(days=1),
            generation_type=GenerationType.HYDRAULIC,
            value_mwh=-1.0,
        )
        summary = ValidationService.validate(record)
        assert summary.combined_notes is not None
        assert "\n" in summary.combined_notes or len(summary.combined_notes) > 0
