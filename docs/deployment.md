# Deployment guide

This repository ships a Docker-based local/development stack (`docker-compose.yml`) and
the configuration needed to run a restricted demonstration. **No public deployment has
been performed and none is claimed.** Production requires the steps and approvals in
[production-readiness.md](production-readiness.md).

## Environments

Development, staging and production are separated by environment variables, never by
code changes. The application reads `HVA_*` variables (see `backend/.env.example`).

| Variable | Development | Production |
| --- | --- | --- |
| `HVA_ENV` | `development` | `production` |
| `HVA_SECRET_KEY` | dev default accepted | **must** be an explicit 32+ char secret; the app refuses to boot otherwise |
| `HVA_ENCRYPTION_KEY` | derived from the secret if unset | **must** be an explicit Fernet key from a secrets manager |
| `HVA_DATABASE_URL` | local PostgreSQL | managed PostgreSQL, least-privilege role, not publicly reachable |
| `HVA_CORS_ORIGINS` | `http://localhost:3000` | exact deployed origins only |
| `HVA_SMS_PROVIDER` | `mock` (refused in production) | `http` with a real gateway |
| `HVA_EMAIL_PROVIDER` | `outbox` | `smtp` |
| `HVA_LLM_PROVIDER` | `disabled` | `openai_compatible` only if a key is funded |
| `HVA_COOKIE_SECURE` | unset (auto) | `true` (enforced; production refuses `false`) |

## Local stack (Docker Compose)

```bash
cp backend/.env.example backend/.env      # fill HVA_SECRET_KEY and HVA_ENCRYPTION_KEY
cp frontend/.env.example frontend/.env.local
docker compose up --build
```

Services: `db` (PostgreSQL 16 on `127.0.0.1:55432`), `migrate` (runs
`alembic upgrade head` then seeds), `api` (FastAPI on `:8000`), `worker`
(`python -m app.jobs.worker`), `web` (Next.js on `:3000`).

## Production topology (recommended)

```
Internet ──TLS──> Reverse proxy (Caddy/Nginx/ALB)
                      ├── /            ──> Next.js (web, :3000)
                      └── /api/v1      ──> FastAPI (api, :8000)
                                              ├── managed PostgreSQL
                                              └── worker (separate process/host)
```

1. **Terminate TLS** at the proxy; forward `X-Forwarded-*` (the API runs with
   `--proxy-headers`). Confirm `HSTS` and `Secure` cookies end to end.
2. **Run migrations** as a one-shot task before releasing new code:
   `alembic upgrade head`. Migrations are version-controlled under
   `backend/alembic/versions/`.
3. **Run the worker** as a separate process (`python -m app.jobs.worker --loop`) so
   ingestion and deletion purges do not run inside the API process.
4. **Serve the built frontend** (`npm run build` then `npm start`) with
   `HVA_API_ORIGIN` pointing at the API. The `/api/v1` rewrite is configured in
   `next.config.ts`.
5. **Use a secrets manager** for `HVA_SECRET_KEY` and `HVA_ENCRYPTION_KEY`; never bake
   them into images or commit them.
6. **Restrict the database role** to least privilege; the application needs DML and
   migration DDL, not superuser.
7. **Confirm CORS** contains only the deployed origins.

## Build artifacts

| Component | Build | Output |
| --- | --- | --- |
| Backend | `docker build backend/` or `pip install .` | `uvicorn app.main:app` |
| Frontend | `docker build frontend/` or `npm run build` | `.next/`, served by `next start` |
| Migrations | `alembic upgrade head` | applied to the target database |
| Seed (dev only) | `python -m seed.seed` | synthetic accounts + curated catalogue |

## Health and readiness

- `GET /api/v1/health` — liveness, database check, honest capability summary.
- `GET /api/v1/health/catalogue` — published scheme count and postal dataset provenance.

Use these as proxy health checks. A `degraded` status means the database is unreachable.

## Rollback

1. Point the proxy at the previous web/api images.
2. Run `alembic downgrade <target>` only if the release included a breaking migration;
   prefer forward-fix migrations.
3. Revoke any sessions issued during the incident if credentials were exposed.

## What is deliberately not deployed

Automated application submission, a document upload vault, semantic retrieval, and any
government portal integration. These are out of scope for the MVP and are listed in
[limitations.md](limitations.md).
