# ADR-003 — `country_code` on All Energy Records

**Status:** Accepted  
**Date:** 2025-01  
**Author:** Diego (Perennia Systems)

---

## Context

Ennesso launches with Ecuador (`EC`) as the only country. However, the platform
may expand to other Latin American markets (Colombia, Peru, Bolivia) or serve
international clients who want comparative data.

If `country_code` is not present from day one, migrating the schema later requires
a costly backfill and API version bump.

## Decision

Every energy record table in Supabase will include a **non-nullable `country_code`
column** (ISO 3166-1 alpha-2, `CHAR(2)`).

All Pydantic models expose `country_code` with a default of `"EC"` for convenience
but require explicit values in writes.

API endpoints accept `country_code` as a query parameter (default `"EC"`).

## Rejected Approaches

| Approach | Reason Rejected |
|----------|-----------------|
| Single-tenant (no column) | Blocks multi-country expansion without schema migration |
| Separate tables per country | Explosion of table count; complicates queries |
| Row-level schemas | Premature and complex for current scale |

## Consequences

- **Positive:** Zero-cost expansion to new countries — just insert rows with a different code.
- **Positive:** Row-level security policies in Supabase can filter by `country_code` for future multi-tenant billing.
- **Neutral:** All EC-only queries must include `WHERE country_code = 'EC'`; this is mitigated by default parameter values.
- **Negative:** Slight schema verbosity for a single-country MVP.
