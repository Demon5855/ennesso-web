# ADR-002 — FastAPI for Backend

**Status:** Accepted  
**Date:** 2025-01  
**Author:** Diego (Perennia Systems)

---

## Context

The backend must:

1. Ingest structured tabular data from CENACE (CKAN API, XHR endpoints) and ARCERNNR
2. Run scheduled ingestion jobs (hourly)
3. Serve a REST API consumed by the Next.js frontend
4. Generate data exports (Excel, PDF)
5. Eventually integrate Claude/Anthropic AI for report summarisation

The data-processing workload is **Python-native**: `pandas` for transforms,
`openpyxl` for Excel, `pdfplumber` for PDF parsing, `reportlab` for generation.

## Decision

Use **FastAPI** with `uvicorn` as the ASGI server, deployed on **Railway**.

## Alternatives Considered

| Option | Reason Rejected |
|--------|-----------------|
| Next.js API Routes only | No APScheduler; weak pandas/openpyxl support; single-process limits |
| Django + DRF | Too opinionated, heavier ORM overhead; async story less ergonomic |
| Node.js (Express / Hono) | Loses the Python data-science ecosystem advantage |

## Consequences

- **Positive:** Pydantic v2 models serve as both API schema and internal validation.
- **Positive:** Native `async/await` with `httpx` for CENACE API calls.
- **Positive:** APScheduler integrates directly in the same process.
- **Positive:** `anthropic` Python SDK is first-class.
- **Negative:** Two runtimes (Node + Python) to maintain.
- **Mitigation:** Shared type definitions documented in `docs/` and mirrored in
  `frontend/types/energy.ts`; OpenAPI schema can be used to generate TS types in future.
