"""Energy indicators calculation service.

Implements LCOE (Levelized Cost of Energy), capacity factor, and
renewable share metrics using Ecuador-specific financial parameters.

Financial methodology:
    Discount rate = Risk-Free Rate + Country Risk Premium (EMBI+)

References:
    - US Treasury 10Y yield: Federal Reserve H.15 release (2024 average)
    - EMBI+ Ecuador spread: JP Morgan EMBI+ Index, December 2024
    - LCOE formula: NREL (2021). Annual Technology Baseline.
      https://atb.nrel.gov/electricity/2021/lcoe
"""

import logging
from typing import Final

from app.models.energy import GenerationType

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Financial constants — Ecuador EMBI+ methodology
# ---------------------------------------------------------------------------

# 4.2% — US Treasury 10-year yield, 2024 annual average
# Source: Federal Reserve H.15 Statistical Release, December 2024
RISK_FREE_RATE: Final[float] = 0.042

# 8.5% — Ecuador EMBI+ sovereign spread, JP Morgan, December 2024
# Source: JP Morgan Emerging Market Bond Index Plus (EMBI+), Dec 2024
ECUADOR_EMBI_SPREAD: Final[float] = 0.085

# 12.7% — Composite discount rate = RISK_FREE_RATE + ECUADOR_EMBI_SPREAD
# Represents minimum required return for energy projects in Ecuador.
DISCOUNT_RATE: Final[float] = RISK_FREE_RATE + ECUADOR_EMBI_SPREAD  # 0.127

# ---------------------------------------------------------------------------
# Generation type classification for renewable share
# ---------------------------------------------------------------------------

RENEWABLE_TYPES: Final[frozenset[GenerationType]] = frozenset({
    GenerationType.HYDRAULIC,
    GenerationType.SOLAR,
    GenerationType.WIND,
    GenerationType.BIOMASS,
})


def calculate_lcoe(
    investment_costs: list[float],
    operation_costs: list[float],
    energy_generated: list[float],
    discount_rate: float = DISCOUNT_RATE,
) -> float:
    """Calculate the Levelized Cost of Energy (LCOE) in USD/MWh.

    Formula::

        LCOE = Σ_{t=0}^{T} (I_t + M_t) / (1+r)^t
               ─────────────────────────────────────
               Σ_{t=0}^{T} E_t / (1+r)^t

    where:
        I_t = capital investment in year t (USD)
        M_t = operation & maintenance costs in year t (USD)
        E_t = energy generated in year t (MWh)
        r   = discount rate (decimal)
        T   = project lifetime (years, inferred from list length)

    Args:
        investment_costs: Annual capital investment per year (USD).
            Typically front-loaded: large value at t=0, zeros thereafter.
        operation_costs: Annual O&M costs per year (USD).
        energy_generated: Annual energy output per year (MWh).
        discount_rate: Annual discount rate as decimal.
            Defaults to ``DISCOUNT_RATE`` (12.7% for Ecuador).

    Returns:
        LCOE in USD/MWh.

    Raises:
        ValueError: If any input list is empty or lists have different lengths.
        ValueError: If the discounted energy sum is zero or negative.
        ValueError: If discount_rate ≤ -1 (would cause division by zero).

    Examples:
        >>> calculate_lcoe([1_000_000], [50_000], [5_000], 0.127)
        210.0  # Approximate — (1_050_000 / 1) / (5_000 / 1)
    """
    if not investment_costs or not operation_costs or not energy_generated:
        raise ValueError("Input lists must not be empty.")

    n = len(investment_costs)
    if len(operation_costs) != n or len(energy_generated) != n:
        raise ValueError(
            f"All input lists must have the same length. Got: "
            f"investment={len(investment_costs)}, "
            f"operation={len(operation_costs)}, "
            f"energy={len(energy_generated)}."
        )

    if discount_rate <= -1:
        raise ValueError(
            f"discount_rate must be > -1, got {discount_rate}."
        )

    discounted_costs = 0.0
    discounted_energy = 0.0

    for t, (inv, ops, energy) in enumerate(
        zip(investment_costs, operation_costs, energy_generated)
    ):
        if energy < 0:
            raise ValueError(
                f"energy_generated[{t}] = {energy} is negative. "
                "Energy output cannot be negative."
            )
        discount_factor = (1 + discount_rate) ** t
        discounted_costs += (inv + ops) / discount_factor
        discounted_energy += energy / discount_factor

    if discounted_energy <= 0:
        raise ValueError(
            "Discounted energy sum is zero or negative — "
            "cannot compute LCOE. Check energy_generated values."
        )

    return discounted_costs / discounted_energy


def calculate_capacity_factor(
    actual_generation_mwh: float,
    installed_capacity_mw: float,
    hours_in_period: float,
) -> float:
    """Calculate the capacity factor for a generation unit or portfolio.

    Formula::

        CF = E_actual / (P_installed × T)

    where:
        E_actual     = actual energy generated (MWh)
        P_installed  = installed / nameplate capacity (MW)
        T            = number of hours in the period (h)

    The result is a dimensionless ratio in [0, 1].
    Values above 1.0 are physically impossible and raise ValueError.

    Args:
        actual_generation_mwh: Actual energy produced in MWh.
        installed_capacity_mw: Nameplate installed capacity in MW.
        hours_in_period: Number of hours in the measurement period.

    Returns:
        Capacity factor as a decimal in [0.0, 1.0].

    Raises:
        ValueError: If ``installed_capacity_mw`` ≤ 0.
        ValueError: If ``hours_in_period`` ≤ 0.
        ValueError: If ``actual_generation_mwh`` < 0.
        ValueError: If result exceeds 1.05 (5% tolerance for rounding).

    Examples:
        >>> calculate_capacity_factor(8_760, 1.0, 8_760)
        1.0  # 1 MW running at full capacity for a full year
        >>> calculate_capacity_factor(4_380, 1.0, 8_760)
        0.5  # Running at half capacity
    """
    if installed_capacity_mw <= 0:
        raise ValueError(
            f"installed_capacity_mw must be positive, got {installed_capacity_mw}."
        )
    if hours_in_period <= 0:
        raise ValueError(
            f"hours_in_period must be positive, got {hours_in_period}."
        )
    if actual_generation_mwh < 0:
        raise ValueError(
            f"actual_generation_mwh cannot be negative, got {actual_generation_mwh}."
        )

    theoretical_max = installed_capacity_mw * hours_in_period
    cf = actual_generation_mwh / theoretical_max

    if cf > 1.05:
        raise ValueError(
            f"Capacity factor {cf:.4f} exceeds 1.05 — "
            f"actual={actual_generation_mwh} MWh, max={theoretical_max} MWh. "
            "Verify input values."
        )

    return min(cf, 1.0)


def calculate_renewable_share(generation_by_type: dict[str, float]) -> float:
    """Calculate the renewable energy share of a generation mix.

    Renewable types: hydraulic, solar, wind, biomass.
    Non-renewable: thermal, other.

    Formula::

        RS = MWh_renewable / MWh_total

    Args:
        generation_by_type: Dict mapping generation type string to MWh.

    Returns:
        Renewable share as a decimal in [0.0, 1.0].
        Returns 0.0 for an empty dict.

    Raises:
        ValueError: If total generation is zero (all values are 0).

    Examples:
        >>> calculate_renewable_share({"hydraulic": 800.0, "thermal": 200.0})
        0.8
        >>> calculate_renewable_share({"thermal": 1000.0})
        0.0
    """
    if not generation_by_type:
        return 0.0

    renewable_mwh = 0.0
    total_mwh = 0.0

    for source, mwh in generation_by_type.items():
        if mwh < 0:
            logger.warning(
                "Negative MWh for source '%s' in renewable share — skipping.",
                source,
            )
            continue

        total_mwh += mwh

        try:
            gen_type = GenerationType(source) if isinstance(source, str) else source
            if gen_type in RENEWABLE_TYPES:
                renewable_mwh += mwh
        except ValueError:
            logger.debug("Unknown type '%s' treated as non-renewable.", source)

    if total_mwh == 0:
        raise ValueError(
            "Total generation is zero — cannot compute renewable share."
        )

    return renewable_mwh / total_mwh
