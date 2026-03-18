"""Tests for the energy indicators calculation service."""

import pytest

from app.services.indicators import (
    DISCOUNT_RATE,
    ECUADOR_EMBI_SPREAD,
    RISK_FREE_RATE,
    calculate_capacity_factor,
    calculate_lcoe,
    calculate_renewable_share,
)


# ---------------------------------------------------------------------------
# Constants sanity
# ---------------------------------------------------------------------------


class TestConstants:
    def test_discount_rate_equals_sum(self):
        assert DISCOUNT_RATE == pytest.approx(RISK_FREE_RATE + ECUADOR_EMBI_SPREAD)

    def test_discount_rate_is_127_percent(self):
        assert DISCOUNT_RATE == pytest.approx(0.127)


# ---------------------------------------------------------------------------
# calculate_lcoe
# ---------------------------------------------------------------------------


class TestCalculateLcoe:
    def test_single_period_known_value(self):
        # t=0: investment=1_000_000, O&M=50_000, energy=5_000 MWh
        # LCOE = (1_000_000 + 50_000) / 1 / (5_000 / 1) = 210 USD/MWh
        result = calculate_lcoe(
            investment_costs=[1_000_000.0],
            operation_costs=[50_000.0],
            energy_generated=[5_000.0],
            discount_rate=0.0,  # No discounting for simple test
        )
        assert result == pytest.approx(210.0)

    def test_zero_discount_rate(self):
        # With r=0, LCOE = total cost / total energy
        result = calculate_lcoe(
            investment_costs=[100.0, 0.0],
            operation_costs=[10.0, 10.0],
            energy_generated=[100.0, 100.0],
            discount_rate=0.0,
        )
        # (100+10+0+10) / (100+100) = 120/200 = 0.6
        assert result == pytest.approx(0.6)

    def test_positive_discount_rate_increases_lcoe(self):
        # Discounting reduces future energy more than upfront costs
        lcoe_no_discount = calculate_lcoe(
            [1_000_000.0, 0.0], [50_000.0, 50_000.0],
            [5_000.0, 5_000.0], discount_rate=0.0
        )
        lcoe_discounted = calculate_lcoe(
            [1_000_000.0, 0.0], [50_000.0, 50_000.0],
            [5_000.0, 5_000.0], discount_rate=0.127
        )
        assert lcoe_discounted > lcoe_no_discount

    def test_empty_lists_raise(self):
        with pytest.raises(ValueError):
            calculate_lcoe([], [], [])

    def test_mismatched_lengths_raise(self):
        with pytest.raises(ValueError):
            calculate_lcoe([100.0, 100.0], [10.0], [50.0, 50.0])

    def test_negative_energy_raises(self):
        with pytest.raises(ValueError):
            calculate_lcoe([100.0], [10.0], [-50.0])

    def test_zero_energy_raises(self):
        with pytest.raises(ValueError):
            calculate_lcoe([100.0], [10.0], [0.0])

    def test_ecuador_discount_rate_used_by_default(self):
        # Just verify the default runs without error
        result = calculate_lcoe(
            [1_000_000.0], [50_000.0], [5_000.0]
        )
        assert result > 0


# ---------------------------------------------------------------------------
# calculate_capacity_factor
# ---------------------------------------------------------------------------


class TestCalculateCapacityFactor:
    def test_full_capacity_returns_one(self):
        # 1 MW × 8760 h = 8760 MWh theoretical max
        result = calculate_capacity_factor(8_760.0, 1.0, 8_760.0)
        assert result == pytest.approx(1.0)

    def test_zero_generation_returns_zero(self):
        result = calculate_capacity_factor(0.0, 100.0, 8_760.0)
        assert result == pytest.approx(0.0)

    def test_half_capacity(self):
        result = calculate_capacity_factor(4_380.0, 1.0, 8_760.0)
        assert result == pytest.approx(0.5)

    def test_typical_hydro_value(self):
        # Ecuador hydro CF ~55-65%
        result = calculate_capacity_factor(4_818.0, 1.0, 8_760.0)
        assert 0.5 < result < 0.7

    def test_zero_capacity_raises(self):
        with pytest.raises(ValueError):
            calculate_capacity_factor(1000.0, 0.0, 8_760.0)

    def test_negative_capacity_raises(self):
        with pytest.raises(ValueError):
            calculate_capacity_factor(1000.0, -100.0, 8_760.0)

    def test_zero_hours_raises(self):
        with pytest.raises(ValueError):
            calculate_capacity_factor(1000.0, 100.0, 0.0)

    def test_negative_generation_raises(self):
        with pytest.raises(ValueError):
            calculate_capacity_factor(-100.0, 100.0, 8_760.0)

    def test_exceeding_max_raises(self):
        # 200% capacity factor — physically impossible
        with pytest.raises(ValueError):
            calculate_capacity_factor(20_000.0, 1.0, 8_760.0)


# ---------------------------------------------------------------------------
# calculate_renewable_share
# ---------------------------------------------------------------------------


class TestCalculateRenewableShare:
    def test_all_renewable_returns_one(self):
        result = calculate_renewable_share({
            "hydraulic": 500.0, "solar": 200.0, "wind": 300.0
        })
        assert result == pytest.approx(1.0)

    def test_all_thermal_returns_zero(self):
        result = calculate_renewable_share({"thermal": 1000.0})
        assert result == pytest.approx(0.0)

    def test_mixed_known_ratio(self):
        # 800 hydraulic / 1000 total = 0.8
        result = calculate_renewable_share({
            "hydraulic": 800.0, "thermal": 200.0
        })
        assert result == pytest.approx(0.8)

    def test_empty_dict_returns_zero(self):
        result = calculate_renewable_share({})
        assert result == 0.0

    def test_all_zero_values_raises(self):
        with pytest.raises(ValueError):
            calculate_renewable_share({"hydraulic": 0.0, "thermal": 0.0})

    def test_biomass_counts_as_renewable(self):
        result = calculate_renewable_share({"biomass": 500.0, "thermal": 500.0})
        assert result == pytest.approx(0.5)

    def test_unknown_type_treated_as_non_renewable(self):
        result = calculate_renewable_share({
            "hydraulic": 500.0,
            "future_fusion": 500.0,
        })
        assert result == pytest.approx(0.5)
