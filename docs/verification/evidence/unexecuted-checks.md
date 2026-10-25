# Checks that could not be executed (2026-10-23)

## Secret scan

`gitleaks` is not installed on the verification machine:

```text
Get-Command gitleaks -> not found
GITLEAKS_NOT_INSTALLED
```

The GitHub Actions workflow contains a `gitleaks` job, but the workflow has not been
executed on a runner. No secret-scan result is claimed. This gate is **BLOCKED**.

## GitHub Actions

`.github/workflows/ci.yml` exists. It was reviewed but not executed because no
GitHub Actions runner is available in this environment. Local equivalents of its
backend/frontend jobs were executed and passed; that is not the same as CI passing.
This gate is **NOT TESTED**.

## External providers and audits

No real SMS, SMTP, LLM, translation-HTTP, transcription or OIDC provider credentials
were available. No external penetration test, load/soak test, automated accessibility
audit, backup/restore drill, TLS/HSTS deployment test or monitoring integration was
performed. These remain BLOCKED or NOT TESTED in the final report.
