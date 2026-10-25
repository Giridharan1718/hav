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

Requires Docker Desktop / Compose engine.

```bash
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env.local
# Fill HVA_SECRET_KEY and HVA_ENCRYPTION_KEY in backend/.env (commands are in the file).
docker compose up -d --build
```

### Services & Port Mappings

| Service | Container | Host Port | Target URL / Health Check |
|---|---|---|---|
| **Web** | `hva-web-1` | `3000` | <http://localhost:3000> |
| **API** | `hva-api-1` | `8000` | <http://localhost:8000/api/docs> · Health: `/api/v1/health` |
| **Database** | `hva-db-1` | `55433` | PostgreSQL 16 (mapped to 55433 to avoid collision with local port 55432) |
| **Migrations** | `hva-migrate-1` | — | Runs Alembic `upgrade head` and catalogue seed, then exits 0 |
| **Worker** | `hva-worker-1` | — | Background task processing (dispatches batch jobs) |

Inspect running containers and logs:
```bash
docker compose ps
docker compose logs -f api
```

Stop containers while keeping database volume data:
```bash
docker compose down
```

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

## Algorithmic Complexity & Performance

The platform is designed with deterministic bounds and scalable index structures:

| Flow | Time Complexity | Space Complexity | Underlying Mechanism |
|---|---|---|---|
| **Scheme Search** | $\mathcal{O}(k \log S)$ | $\mathcal{O}(P)$ | PostgreSQL GIN index (`search_vector`) + paginated limit ($P \le 50$) |
| **Eligibility Check** | $\mathcal{O}(R \log R)$ | $\mathcal{O}(R)$ | Deterministic in-memory operator evaluation over $R$ rules ($R \le 15$) |
| **PIN Code Lookup** | $\mathcal{O}(\log P_{off} + M)$ | $\mathcal{O}(M)$ | B-Tree index on `pincode` over 155k post offices ($M$ = matching branches) |
| **Assistant Guardrails** | $\mathcal{O}(E \cdot T)$ | $\mathcal{O}(E \cdot T)$ | Context bounded to $E \le 3$ schemes, 1,000 char prompt, citation validation |
| **Rate Limiter** | $\mathcal{O}(1)$ amortized | $\mathcal{O}(K)$ | In-memory sliding-window deque with hard memory cap ($K \le 50,000$ keys) |
| **Data Export / Delete** | $\mathcal{O}(D + S + C)$ | $\mathcal{O}(D)$ | Indexed user foreign-key queries with eager `selectinload` (no N+1 queries) |

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

Current measured results and requirement verification statuses are recorded in the authoritative [docs/verification-report.md](docs/verification-report.md) (110 pytest tests pass, Ruff clean, 17/17 Next.js pages build, 12/12 Vitest pass), as well as [docs/testing.md](docs/testing.md) and [docs/evaluation/results.md](docs/evaluation/results.md).

## Documentation

- [Authoritative verification report](docs/verification-report.md)
- [Historical verification records & evidence](docs/verification/README.md)
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
- [Evaluation results](docs/evaluation/results.md)
- [Scheme link audit](docs/evaluation/links.md)
- [Known limitations](docs/limitations.md)
- [Production-readiness checklist](docs/production-readiness.md)

## Status

MVP vertical slice, suitable for a restricted demonstration after the release checks in
[docs/production-readiness.md](docs/production-readiness.md) are completed.

- **Dockerized Stack**: Verified live with healthy containers (`hva-api-1`, `hva-db-1`, `hva-web-1`, `hva-migrate-1`, `hva-worker-1`).
- **Automated Verification**: 110/110 pytest tests pass on host (real PostgreSQL), Ruff lint clean, TypeScript clean, Vitest 12/12 pass, production Next.js build passes.
- **Multilingual Evaluation**: Recall@5 = 1.00 (EN/HI/TA), 100% source attribution, 5/5 negative controls passed.
- **Authoritative Report**: Detailed verification logs and known environment constraints (Next.js 15 / OpenNext adapter support, password+TOTP auth path, Hindi/Tamil catalogue draft reviews) are fully documented in [docs/verification-report.md](docs/verification-report.md).
- **Disclaimer**: No public deployment, government partnership, legal compliance certification or provider agreement is claimed by this repository.
