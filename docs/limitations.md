# Known limitations

This is an honest list of what this build does not do or does not do fully. It is the
companion to [production-readiness.md](production-readiness.md).

## Not implemented at all

1. **OIDC single sign-on.** Configuration flags and a capability report exist, but no
   authorization-code flow, token exchange or JWKS validation is wired. Password + TOTP
   is the implemented auth path. See [adapters.md](adapters.md).
2. **Live SMS, SMTP, LLM, translation and speech providers.** Each is an adapter with a
   documented contract and a safe development fallback; none is connected to a real
   vendor account in this repository.
3. **Semantic / vector retrieval.** Search is PostgreSQL full-text plus synonym expansion
   and a substring fallback. No embedding store is used; a semantic path would need an
   evaluation demonstrating a benefit before adoption.
4. **Automatic application submission.** HVA prepares and exports drafts only. It never
   submits, impersonates the citizen, or claims to have filed anything.
5. **Document upload vault.** No object storage or identity-document vault exists; the
   checklist tells the citizen which documents to attach themselves.
6. **Public deployment / infrastructure as code.** Docker Compose and a runbook are
   provided; no cloud deployment is performed or claimed.
7. **Backups and restore automation.** Documented as a required step in the runbook, but
   no backup job or restore test exists in this repository.

## Implemented but limited

1. **Rate limiter is single-process and in-memory.** Correct for one API instance; a
   shared store (e.g. Redis) is required before scaling horizontally.
2. **CSP still allows `unsafe-inline` and `unsafe-eval` for scripts** because Next.js
   injects inline bootstrap scripts. A nonce-based policy is the follow-up.
3. **Curated scheme catalogue only.** The seeded dataset covers a small number of
   national schemes. Coverage is not exhaustive and is not presented as such.
4. **Hindi and Tamil translations cover only part of the catalogue** and are marked
   `draft` (unreviewed). Additional languages (Telugu, Kannada, Malayalam, Bengali,
   Marathi) are not enabled because their quality has not been evaluated.
5. **Language detection is script-based** and treats Latin-script input as English, even
   when it is romanized Hindi or Tamil. Code-mixed input is not reliably detected.
6. **Official source links may be unverifiable from the build environment.** Two seeded
   links (PM-JAY, PM-KISAN) could not be fetched here and are flagged unverified, not
   broken. See [evaluation/links.md](evaluation/links.md).
7. **Postal data is a seeded sample**, not the full India Post dataset. It is clearly
   labelled as a sample with provenance and refresh time.
8. **Eligibility is preliminary, never an official determination.** Rules are transcribed
   from source documents and validated by a reviewer; a `cannot_evaluate` outcome is
   returned when a rule or its source is unusable.
9. **Assistant answers are grounded in the reviewed catalogue only.** It declines to
   answer outside it rather than inventing sources, amounts or deadlines.
10. **Accessibility is reviewed manually** (semantic HTML, labels, keyboard, focus,
    contrast) but has not been audited with a screen reader or an automated axe scan.
11. **No anomaly/bot detection or WAF.** Rate limits are the only abuse control.
12. **CERT-In log retention and incident reporting are not automated.** Retention must be
    wired to a managed log store before launch.

## Data and legal caveats

1. **No compliance or certification is claimed.** Privacy features do not equal legal
   compliance; the DPDP Act's phased commencement, security requirements and provider
   contracts must be reviewed by counsel.
2. **No government partnership, endorsement or identity certification.** HVA is an
   independent assistance platform. No fake trust badges or government logos are used.
3. **Phone verification proves access to a number, not legal identity.**
4. **Sensitive attributes are never inferred.** Missing income, caste, disability or
   citizenship is surfaced as "insufficient information", not guessed.

## Development-environment notes

- The portable PostgreSQL cluster used for local testing lives under `.devdb/`
  (gitignored) and is not part of the application.
- Docker was not available on the build machine, so `docker-compose.yml` and the
  Dockerfiles are provided but unexercised.
