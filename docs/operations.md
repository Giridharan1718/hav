# Operations runbook

Day-two operations for the HVA API, web app, worker and database. Several procedures
here are **documented but not exercised** in this repository; that is stated explicitly
so nothing is claimed without evidence.

## Processes

| Process | Command | Notes |
| --- | --- | --- |
| API | `uvicorn app.main:app --host 0.0.0.0 --port 8000 --proxy-headers` | Stateless; scale horizontally only after adding a shared rate-limit store |
| Worker | `python -m app.jobs.worker --loop --interval 10` | Ingestion queue + account-deletion purge |
| Web | `npm start` (after `npm run build`) | `/api/v1` rewritten to the API via `HVA_API_ORIGIN` |
| Migrations | `alembic upgrade head` | Run as a one-shot task before releasing |

## Routine tasks

### Apply a migration

```bash
alembic current        # confirm the revision
alembic upgrade head
alembic history        # record what changed
```

Run migrations before releasing the code that depends on them. Prefer forward-fix
migrations; use `alembic downgrade` only for a breaking change with a tested downgrade
path.

### Re-seed development data (development only)

```bash
python -m seed.seed --skip-link-check     # or omit the flag to fetch official pages
```

Prints the demo account passwords once. Reviewer/admin accounts must enrol TOTP at
`/settings/security` before using `/admin`.

### Check official source links

```bash
python -m seed.check_links --markdown ../docs/evaluation/links.md
```

Run on a machine with outbound internet. Unreachable links stay flagged as unverified,
never as working.

### Run the evaluation report

```bash
python -m evaluation.run_eval
```

Writes `docs/evaluation/results.md` with measured retrieval and source-attribution
numbers.

## Monitoring and alerting

Structured JSON logs go to stdout (`log_event`). There is no built-in dashboarding or
alerting; wire the logs to a managed store and alert on:

- `server_error` events (5xx) and any `unhandled error` traceback.
- Repeated `origin_rejected`, `csrf_failed` or `rate_limited` spikes (abuse).
- `sms_provider_failure`, `smtp_failure`, `translation provider failure`,
  `transcription provider failure` (provider outages).
- `degraded` health status (database unreachable).
- Ingestion runs ending in `failed`.

`audit_events` records privileged and security-relevant actions with no personal data;
review `GET /admin/audit` after any security incident.

## Backups and restoration

**No backup automation exists in this repository.** Before production:

1. Enable encrypted automated backups on the managed PostgreSQL instance.
2. Define and document a retention period aligned with the deletion policy (deletion
   cannot reach immutable backups until they expire; this must be stated in the privacy
   notice).
3. Perform and record a restore test into a scratch database:

```bash
createdb hva_restore_test
psql hva_restore_test < backup.dump
alembic current          # confirm the revision matches
```

Deletion requests that complete while a backup predates them will be present in that
backup until it expires; document this propagation honestly.

## Log retention (CERT-In)

Applicable CERT-In directions require retention of security logs and timely incident
reporting. This build writes `audit_events` to the database and structured logs to
stdout; **retention is not automated here.** Wire logs to a managed store with the
required retention period and document the incident-reporting procedure and contacts
before launch.

## Incident response

1. **Detect** — alert or report triggers; capture the time and the request ids.
2. **Contain** — revoke affected sessions (`DELETE /auth/sessions`), rotate
   `HVA_SECRET_KEY` / `HVA_ENCRYPTION_KEY` / provider tokens, block an abusive IP at the
   proxy, or take the environment offline.
3. **Eradicate & recover** — patch, run migrations, restore from backup if data was
   corrupted.
4. **Notify** — report per CERT-In timelines and any contractual obligations; record the
   timeline.
5. **Review** — update the threat model and controls.

### Credential rotation

| Credential | Rotation |
| --- | --- |
| `HVA_SECRET_KEY` | Update in the secrets manager and restart; invalidates derived dev keys (production requires an explicit key) |
| `HVA_ENCRYPTION_KEY` | **Re-encrypt sensitive fields before switching** — TOTP secrets and DOB are Fernet-encrypted; a key change without re-encryption makes them unreadable |
| SMS / SMTP / LLM tokens | Update the `HVA_*_TOKEN` variables and restart |
| Database credentials | Rotate in the managed instance; update `HVA_DATABASE_URL` |
| User password | Self-service `POST /auth/password/change` (revokes other sessions) |

## Scaling

- The API is stateless apart from the in-memory rate limiter; add a shared counter store
  (e.g. Redis) before running more than one instance.
- The worker can run as a singleton; run multiple only with a job-locking strategy.
- PostgreSQL is the primary scaling concern; add read replicas only if search load
  requires it.
