# Human Vernacular Assist (HVA)

A privacy-first, multilingual web application that helps people in India discover
government schemes, read documented eligibility criteria, check those criteria
deterministically, prepare application drafts and follow official links in English,
Hindi or Tamil.

**HVA is an independent assistance platform.** It is not a government website, it does
not certify identity, it does not file applications and it does not guarantee benefits.
Every scheme screen cites the official source and shows its verification status.

## What is in this repository

| Area | Stack | Location |
| --- | --- | --- |
| API | Python 3.12, FastAPI, SQLAlchemy 2, Alembic, PostgreSQL 16 | [`backend/`](backend) |
| Web app | Next.js 15 (App Router), TypeScript, React 19 | [`frontend/`](frontend) |
| Local stack | Docker Compose (PostgreSQL, API, worker, web) | [`docker-compose.yml`](docker-compose.yml) |
| Documentation | Architecture, data model, API, security, privacy, adapters, operations | [`docs/`](docs) |
| Evaluation | Reproducible multilingual retrieval/link evaluation | [`backend/evaluation/`](backend/evaluation) |

Implemented citizen journey:

register → privacy notice + purpose-specific consent → profile and PIN-code
post-office confirmation → search and filter the reviewed catalogue → read scheme
evidence and source status → answer eligibility questions → deterministic preliminary
result → grounded multilingual assistant answer (text; voice transcription is adapter
gated) → private application draft with per-field provenance → draft export → personal
data export / account deletion request → content reviewer verification.

## Quick start (Docker)

Requires Docker Compose. This configuration was written but **not exercised on the
build machine**, which had no Docker engine (see [docs/testing.md](docs/testing.md)).

```bash
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env.local
# Fill HVA_SECRET_KEY and HVA_ENCRYPTION_KEY in backend/.env (commands are in the file).
docker compose up --build
```

Web: <http://localhost:3000> · API docs: <http://localhost:8000/api/docs>

## Quick start (without Docker)

PostgreSQL must be reachable at the URL in `backend/.env` (the example uses
`127.0.0.1:55432`).

```bash
# API
cd backend
python -m venv .venv
.venv/Scripts/pip install -e ".[dev]"      # macOS/Linux: .venv/bin/pip
cp .env.example .env                        # fill both keys
alembic upgrade head
python -m seed.seed                         # prints the demo account passwords once
uvicorn app.main:app --reload --port 8000

# Web (second terminal)
cd frontend
npm ci
npm run dev                                 # http://localhost:3000
```

Seeded accounts: `citizen@hva.test`, `reviewer@hva.test`, `admin@hva.test`. Passwords
are random and printed only by the seed command. Reviewer and administrator accounts
must enrol TOTP at `/settings/security` before using `/admin`.

Scheme source links are checked during seeding. If the machine cannot reach the
official portals, re-run `python -m seed.check_links --markdown ../docs/evaluation/links.md`
on a networked machine; unreachable links stay flagged as unverified.

## Verification commands

```bash
# API: lint, tests (needs PostgreSQL), evaluation report
cd backend
.venv/Scripts/python -m ruff check .
.venv/Scripts/python -m pytest
.venv/Scripts/python -m evaluation.run_eval

# Web: typecheck, unit tests, production build
cd frontend
npx tsc --noEmit
npm test
npm run build
```

Current measured results are reported in [docs/testing.md](docs/testing.md) and
[docs/evaluation/results.md](docs/evaluation/results.md). They are not repeated here so
the README cannot drift from the measured numbers.

## Documentation

- [Implementation plan](docs/plan.md)
- [Architecture and data flow](docs/architecture.md)
- [Data model](docs/data-model.md)
- [API contracts](docs/api.md)
- [Security, threat model and checklist](docs/security.md)
- [Privacy and consent workflows](docs/privacy.md)
- [Provider adapters](docs/adapters.md)
- [Deployment guide](docs/deployment.md)
- [Operations runbook](docs/operations.md)
- [Testing and evaluation](docs/testing.md)
- [Known limitations](docs/limitations.md)
- [Production-readiness checklist](docs/production-readiness.md)

## Status

MVP vertical slice, suitable for a restricted demonstration after the release checks in
[docs/production-readiness.md](docs/production-readiness.md) are completed. No public
deployment, government partnership, legal compliance certification or provider
agreement is claimed by this repository.
