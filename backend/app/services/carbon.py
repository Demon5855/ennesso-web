"""Carbon emissions calculation service.

All emission factors are lifecycle values from IPCC (2014) Working Group III,
Annex II, Table A.III.2 — median values in kg CO₂eq/MWh.

Reference:
    IPCC (2014). Climate Change 2014: Mitigation of Climate Change.
    Contribution of Working Group III to the Fifth Assessment Report.
    Cambridge University Press. Annex II, p. 1335.
    https://www.ipcc.ch/report/ar5/wg3/
"""

import logging
from typing import Final

from app.models.energy import GenerationType

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Emission factors (kg CO₂eq / MWh) — IPCC AR5 WG3 (2014), Table A.III.2
# Lifecycle median values.
# ---------------------------------------------------------------------------

EMISSION_FACTORS: Final[dict[GenerationType, float]] = {
    # 490 kg CO₂eq/MWh — combined cycle gas turbine (CCGT), IPCC AR5 median
    GenerationType.THERMAL: 490.0,
    # 4 kg CO₂eq/MWh — reservoir hydropower, IPCC AR5 median
    GenerationType.HYDRAULIC: 4.0,
    # 48 kg CO₂eq/MWh — utility-scale solar PV, IPCC AR5 median
    GenerationType.SOLAR: 48.0,
    # 11 kg CO₂eq/MWh — onshore wind, IPCC AR5 median
    GenerationType.WIND: 11.0,
    # 230 kg CO₂eq/MWh — biomass (dedicated combustion), IPCC AR5 median
    GenerationType.BIOMASS: 230.0,
    # 490 kg CO₂eq/MWh — fallback to thermal for unclassified sources
    GenerationType.OTHER: 490.0,
}

# Baseline for avoided emissions: 100% thermal generation
# Used to compute how much CO₂ was avoided by using cleaner sources.
_THERMAL_FACTOR: Final[float] = EMISSION_FACTORS[GenerationType.THERMAL]


def calculate_emissions(generation_by_type: dict[str, float]) -> float:
    """Calculate total lifecycle CO₂ emissions for a generation mix.

    Formula::

        CO₂_total = Σ (MWh_i × EF_i)

    where EF_i is the IPCC lifecycle emission factor for source i
    (kg CO₂eq/MWh).

    Args:
        generation_by_type: Dict mapping generation type string or
            ``GenerationType`` to energy in MWh. Unknown types fall back
            to the thermal emission factor with a warning.

    Returns:
        Total emissions in kg CO₂eq. Returns 0.0 for an empty dict.

    Examples:
        >>> calculate_emissions({"hydraulic": 1000.0, "thermal": 500.0})
        249000.0  # (1000×4) + (500×490)
    """
    if not generation_by_type:
        return 0.0

    total_co2 = 0.0

    for source, mwh in generation_by_type.items():
        if mwh < 0:
            logger.warning("Negative MWh for source '%s' — skipping.", source)
            continue

        try:
            gen_type = GenerationType(source) if isinstance(source, str) else source
            factor = EMISSION_FACTORS.get(gen_type, _THERMAL_FACTOR)
        except ValueError:
            logger.warning(
                "Unknown generation type '%s' — using thermal factor as fallback.",
                source,
            )
            factor = _THERMAL_FACTOR

        total_co2 += mwh * factor

    return total_co2


def calculate_avoided_emissions(generation_by_type: dict[str, float]) -> float:
    """Calculate CO₂ emissions avoided versus a 100% thermal baseline.

    Formula::

        CO₂_avoided = (MWh_total × EF_thermal) − CO₂_actual

    where EF_thermal = 490 kg CO₂eq/MWh (IPCC AR5, CCGT median).

    Args:
        generation_by_type: Dict mapping generation type to MWh.

    Returns:
        Avoided emissions in kg CO₂eq. Returns 0.0 for an empty dict.
        A negative value means the mix is dirtier than 100% thermal
        (possible if biomass or OTHER dominates).

    Examples:
        >>> calculate_avoided_emissions({"thermal": 1000.0})
        0.0  # No savings vs baseline
        >>> calculate_avoided_emissions({"hydraulic": 1000.0})
        486000.0  # (1000×490) − (1000×4)
    """
    if not generation_by_type:
        return 0.0

    total_mwh = sum(v for v in generation_by_type.values() if v >= 0)
    baseline_co2 = total_mwh * _THERMAL_FACTOR
    actual_co2 = calculate_emissions(generation_by_type)

    return baseline_co2 - actual_co2


def calculate_carbon_intensity(total_mwh: float, total_co2_kg: float) -> float:
    """Calculate the carbon intensity of a generation mix.

    Formula::

        CI = CO₂_total (kg) / MWh_total

    Args:
        total_mwh: Total energy generated in MWh.
        total_co2_kg: Total lifecycle CO₂ emissions in kg CO₂eq.

    Returns:
        Carbon intensity in kg CO₂eq/MWh.

    Raises:
        ValueError: If ``total_mwh`` is zero or negative.

    Examples:
        >>> calculate_carbon_intensity(1000.0, 4000.0)
        4.0  # Pure hydraulic mix
    """
    if total_mwh <= 0:
        raise ValueError(
            f"total_mwh must be positive, got {total_mwh}. "
            "Cannot compute carbon intensity for zero or negative generation."
        )

    return total_co2_kg / total_mwh
