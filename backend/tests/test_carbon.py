"""Tests for the carbon emissions calculation service."""

import pytest

from app.services.carbon import (
    EMISSION_FACTORS,
    calculate_avoided_emissions,
    calculate_carbon_intensity,
    calculate_emissions,
)
from app.models.energy import GenerationType


# ---------------------------------------------------------------------------
# calculate_emissions
# ---------------------------------------------------------------------------


class TestCalculateEmissions:
    def test_empty_dict_returns_zero(self):
        assert calculate_emissions({}) == 0.0

    def test_single_thermal_source(self):
        # 1000 MWh × 490 kg/MWh = 490_000 kg CO₂
        result = calculate_emissions({"thermal": 1000.0})
        assert result == pytest.approx(490_000.0)

    def test_single_hydraulic_source(self):
        # 1000 MWh × 4 kg/MWh = 4_000 kg CO₂
        result = calculate_emissions({"hydraulic": 1000.0})
        assert result == pytest.approx(4_000.0)

    def test_mixed_generation_known_values(self):
        # hydraulic: 1000 × 4 = 4_000
        # thermal:    500 × 490 = 245_000
        # total = 249_000
        result = calculate_emissions({"hydraulic": 1000.0, "thermal": 500.0})
        assert result == pytest.approx(249_000.0)

    def test_all_renewable_mix(self):
        result = calculate_emissions({
            "hydraulic": 500.0,
            "solar": 200.0,
            "wind": 300.0,
        })
        expected = (500 * 4) + (200 * 48) + (300 * 11)
        assert result == pytest.approx(expected)

    def test_zero_mwh_source_contributes_nothing(self):
        result = calculate_emissions({"thermal": 0.0, "hydraulic": 1000.0})
        assert result == pytest.approx(4_000.0)

    def test_negative_mwh_skipped(self):
        # Negative values should be silently skipped
        result = calculate_emissions({"thermal": -100.0, "hydraulic": 1000.0})
        assert result == pytest.approx(4_000.0)

    def test_unknown_source_falls_back_to_thermal(self):
        result = calculate_emissions({"unknown_future_source": 100.0})
        assert result == pytest.approx(100.0 * 490.0)

    def test_generation_type_enum_keys_accepted(self):
        result = calculate_emissions({GenerationType.SOLAR: 100.0})
        assert result == pytest.approx(100.0 * 48.0)

    def test_biomass_factor_applied(self):
        result = calculate_emissions({"biomass": 100.0})
        assert result == pytest.approx(100.0 * 230.0)


# ---------------------------------------------------------------------------
# calculate_avoided_emissions
# ---------------------------------------------------------------------------


class TestCalculateAvoidedEmissions:
    def test_empty_dict_returns_zero(self):
        assert calculate_avoided_emissions({}) == 0.0

    def test_all_thermal_avoided_is_zero(self):
        # If baseline IS thermal, nothing is avoided
        result = calculate_avoided_emissions({"thermal": 1000.0})
        assert result == pytest.approx(0.0)

    def test_all_hydraulic_avoids_maximum(self):
        # baseline: 1000 × 490 = 490_000
        # actual:   1000 × 4   = 4_000
        # avoided:  486_000
        result = calculate_avoided_emissions({"hydraulic": 1000.0})
        assert result == pytest.approx(486_000.0)

    def test_all_solar_avoided(self):
        result = calculate_avoided_emissions({"solar": 500.0})
        expected = 500 * (490 - 48)
        assert result == pytest.approx(expected)

    def test_mixed_renewable_and_thermal(self):
        mix = {"hydraulic": 800.0, "thermal": 200.0}
        total = 1000.0
        baseline = total * 490
        actual = calculate_emissions(mix)
        assert calculate_avoided_emissions(mix) == pytest.approx(baseline - actual)


# ---------------------------------------------------------------------------
# calculate_carbon_intensity
# ---------------------------------------------------------------------------


class TestCalculateCarbonIntensity:
    def test_pure_hydraulic_intensity(self):
        # 4_000 kg / 1000 MWh = 4.0 kg/MWh
        result = calculate_carbon_intensity(1000.0, 4_000.0)
        assert result == pytest.approx(4.0)

    def test_pure_thermal_intensity(self):
        result = calculate_carbon_intensity(1000.0, 490_000.0)
        assert result == pytest.approx(490.0)

    def test_zero_mwh_raises(self):
        with pytest.raises(ValueError):
            calculate_carbon_intensity(0.0, 1000.0)

    def test_negative_mwh_raises(self):
        with pytest.raises(ValueError):
            calculate_carbon_intensity(-100.0, 1000.0)

    def test_mixed_intensity_value(self):
        co2 = calculate_emissions({"hydraulic": 800.0, "thermal": 200.0})
        intensity = calculate_carbon_intensity(1000.0, co2)
        expected = co2 / 1000.0
        assert intensity == pytest.approx(expected)
