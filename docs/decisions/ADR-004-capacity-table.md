# ADR-004 — Separate `installed_capacity` Table

**Status:** Accepted  
**Date:** 2026-03  
**Author:** Diego (Perennia Systems)

---

## Context

CENACE publishes two distinct datasets:

- **Generation (MWh):** time-series of actual energy produced per plant per day
- **Dispatched capacity (MW):** snapshot of installed/available power capacity

Both were initially candidates for the `energy_records` table. A `record_type`
column (`'generation'` | `'capacity'`) was considered to distinguish them.

The key difference is temporal behavior:
- Generation data arrives daily and grows indefinitely (high-volume time-series)
- Installed capacity changes rarely — typically once or twice per year when new
  plants come online or are decommissioned (low-volume reference data)

## Decision

Store installed capacity in a **separate `installed_capacity` table** with an
`effective_date` column to track historical changes over time.

`energy_records` remains exclusively for generation time-series (MWh).

## Alternatives Considered

| Option | Reason Rejected |
|--------|-----------------|
| `record_type` column in `energy_records` | Mixes reference data with time-series; `value_mwh` column name becomes misleading for MW values; complicates dashboard aggregations |
| Single `value` column + `unit` column | More flexible but loses type safety and makes queries verbose |
| No capacity table at all | The validation service needs capacity constants — without a table they live hardcoded in Python, making updates require a redeploy |

## Consequences

- **Positive:** `energy_records` stays semantically clean — always MWh, always
  generation actuals.
- **Positive:** Capacity updates (new plants) are a simple INSERT with a new
  `effective_date` — no backfill needed.
- **Positive:** The validation service (`hydraulic_capacity` rule) can query
  the DB for the latest capacity instead of relying on hardcoded constants.
- **Positive:** Ready for multi-country expansion — capacity is scoped by
  `country_code` like all other tables.
- **Negative:** One additional JOIN when the dashboard needs to show capacity
  utilisation rate alongside generation.
- **Mitigation:** A DB view can pre-join both tables for the dashboard if the
  JOIN becomes a performance concern.