# ADR-001 — Monorepo Structure

**Status:** Accepted  
**Date:** 2025-01  
**Author:** Diego (Perennia Systems)

---

## Context

Ennesso consists of two tightly coupled applications:

- A **Next.js** frontend deployed to Vercel
- A **FastAPI** backend deployed to Railway

Both share domain vocabulary (energy sources, country codes, unit definitions)
and will evolve together. We need a repository layout that minimises drift between
frontend types and backend schemas while keeping CI/CD simple for a solo founder.

## Decision

Use a **single Git repository (monorepo)** with a flat top-level split:

```
ennesso/
├── frontend/
├── backend/
└── docs/
```

Each sub-project retains its own dependency manifest (`package.json`,
`requirements.txt`) and independent deployment configuration.

## Alternatives Considered

| Option | Reason Rejected |
|--------|-----------------|
| Separate repos | Higher coordination overhead; no shared type source |
| Turborepo / Nx | Overkill for a two-app solo project; adds tooling complexity |
| Full polyrepo with git submodules | Submodule UX is poor; increases friction for rapid iteration |

## Consequences

- **Positive:** Single PR review surface; shared docs; easier refactors across layers.
- **Positive:** Vercel and Railway both support sub-directory deployments natively.
- **Negative:** Slightly larger clone size for contributors who only touch one app.
- **Mitigation:** Vercel `Root Directory` set to `frontend/`; Railway `Root Directory` set to `backend/`.
