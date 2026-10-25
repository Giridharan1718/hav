# Docker Compose verification (2026-10-23)

The Docker daemon became available on the verification machine after the earlier
baseline. The shipped `docker-compose.yml` and both Dockerfiles were built and run
without modifying them.

To avoid colliding with the local PostgreSQL/API/web processes, a temporary override
file outside the repository mapped only the host ports:

- db `127.0.0.1:65432 -> 5432`
- api `127.0.0.1:8100 -> 8000`
- web `127.0.0.1:3100 -> 3000`

No application code, Dockerfile, image, environment file or service definition was
changed. Command:

```powershell
docker compose -p hva-probe -f docker-compose.yml -f <temp>/docker-compose.override.yml up --build -d
```

Result:

- `hva-probe-db-1` healthy, `hva-probe-migrate-1` exited 0, `hva-probe-api-1`
  healthy, `hva-probe-worker-1` running, `hva-probe-web-1` running.
- Migration log ended at Alembic revision `0003_widen_application_mode`; seed log
  reported `{'seeded': 8, 'skipped': 0}`.
- API health at `http://127.0.0.1:8100/api/v1/health` returned `status: ok`,
  `database: ok`, with SMS `mock`, email `outbox`, assistant `disabled` (grounded
  template fallback), translation `catalog`, transcription `disabled`, OIDC `false`,
  postal `local`, MFA `true`.
- The 17-check live HTTP probe (same probe used against the local API) passed
  `17/17` against the containerised API and container database:
  `compose-probe.txt`, `compose-probe-results.json`.
- The containerised web app loaded the home page and `/schemes`; searching
  `scholarship` returned exactly one result, `Post-Matric Scholarship for Scheduled
  Caste Students`, served through the Next.js rewrite to the API container.
- Container logs showed normal request/worker lines and no unhandled errors. The
  worker logged `processed 0 jobs: []`.
- `docker compose ... down -v --remove-orphans` removed containers, network and
  volume; no `hva` containers or volumes remain.

Note: the development seed prints demo account passwords to the migrate container
log. That is expected for this local-development stack but must never be used for a
production deployment.
