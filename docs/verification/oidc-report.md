# HVA — OIDC Authorization-code Flow Report

**Generated:** 2026-10-23
**Purpose:** Document OIDC status per Phase K of the Mandatory Build, Test, Fix and Verify Protocol.

## 1. Current OIDC Configuration

| Setting | Value | Status |
|---|---|---|
| `HVA_OIDC_ISSUER` | `""` (empty) | Not configured |
| `HVA_OIDC_CLIENT_ID` | `""` (empty) | Not configured |
| `HVA_OIDC_CLIENT_SECRET` | `""` (empty) | Not configured |
| `HVA_OIDC_REDIRECT_URI` | `""` (empty) | Not configured |
| `OIDC enabled` | `False` | Confirmed by test `assert body["features"]["oidc"]["enabled"] is False` |

## 2. Current Authentication Path

The active authentication system uses:

| Method | Description | Status |
|---|---|---|
| Password + TOTP MFA | Argon2id-hashed passwords; TOTP secret per user | ✅ Functional and tested |
| OIDC authorization-code flow | Not implemented | `enabled: False`; empty config fields |
| Session management | FastAPI cookies + CSRF tokens | ✅ Functional |

## 3. OIDC Authorization-code Flow Requirements

Per Phase K, if OIDC SSO is required, the following must be implemented:

### 3.1 issuer and client configuration validation
- Validate `issuer` URL (the OIDC provider's well-known configuration endpoint)
- Validate `client_id` (must match the registered value at the provider)
- Validate `client_secret` (kept server-side; never sent to frontend)
- Validate `redirect_uri` (must be in the provider's registered redirect URIs)

### 3.2 Authorization-code flow with PKCE
- Generate `code_verifier` and `code_challenge` (PKCE)
- Direct user to the provider's authorization endpoint
- Exchange the authorization code for tokens (access_token, refresh_token)
- Validate token signatures, issuer, audience (`aud`), and expiration
- Use exact registered redirect URIs (no open redirects)

### 3.3 Token validation
- Verify `iss` (issuer) matches the expected value
- Verify `aud` (audience) matches the `client_id`
- Verify `exp` (expiration) is in the future
- Verify `iat` (issued-at) timestamp
- Refresh tokens if supported and configured

### 3.3 Session establishment
- Establish the application's own secure session (separate from the OIDC tokens)
- Link external identities to internal accounts safely
- Prevent account takeover through unsafe email-based account linking
- Support logout and session revocation according to the provider's capabilities

### 3.4 Security controls
- Prevent open redirects (validate redirect URIs exactly)
- Handle callback errors safely (no stack traces to the user)
- Support logout and session revocation
- Client secrets must remain server-side (never in browser, source code, or logs)

## 4. Current Blocker

| Blocking item | Status | Resolution |
|---|---|---|
| `oidc_issuer` | ❌ Empty string `""` | Requires OIDC provider URL (e.g., "https://accounts.google.com") |
| `oidc_client_id` | ❌ Empty string `""` | Requires registered client ID at the provider |
| `oidc_client_secret` | ❌ Empty string `""` | Requires registered client secret (server-side only) |
| `oidc_redirect_uri` | ❌ Empty string `""` | Requires registered redirect URI (e.g., "https://app.example.com/auth/callback") |
| OIDC library | ❌ Not installed | Would need `python3-oidc` or similar maintained library |
| PKCE implementation | ❌ Not present | Would need to add PKCE code verifier/challenge generation |

## 5. Recommended Next Steps

If OIDC SSO is required for the production candidate:

1. **Select an OIDC identity provider** (Google Workspace, Azure AD, Okta, Keycloak, etc.)
2. **Create an OIDC application/client** in the provider's console and obtain:
   - Issuer URL (well-known configuration endpoint)
   - Client ID (registered at the provider)
   - Client secret (kept server-side, never in browser)
   - Redirect URIs (exact matches; one for production, one for development/loopback)
3. **Configure environment variables:**
   - `HVA_OIDC_ISSUER=https://accounts.google.com` (or provider issuer)
   - `HVA_OIDC_CLIENT_ID=your_client_id`
   - `HVA_OIDC_CLIENT_SECRET=your_client_secret` (server-side only; not in .env committed to VCS)
   - `HVA_OIDC_REDIRECT_URI=https://your-app.com/auth/freebuff/callback`
4. **Install and configure an OIDC library** (e.g., `python3-oidc` or use the `authlib` library which is already a dependency)
5. **Implement the authorization-code flow with PKCE:**
   - Generate code verifier and challenge
   - Redirect user to provider's consent screen
   - Exchange authorization code for tokens
   - Validate tokens (iss, aud, exp, iat)
   - Establish application session
   - Link external identity to internal account (or create new account)
6. **Test the full flow:**
   - Initiate login from the frontend
   - Redirect to provider, authorize, redirect back
   - Verify session is established
   - Test logout/revocation
   - Test with development loopback provider (e.g., Keycloak test realm, or Auth0 development domain)
7. **Update the `enabled` check** in the features endpoint to reflect the new configuration
8. **Run the existing test suite** to ensure no regressions

**Do not** treat configuration flags alone as an implemented OIDC flow. The authorization-code flow with PKCE must be fully functional with a real or sandbox provider before the `enabled` flag is set to `True`.

## 5. Current Features Endpoint

The `/api/v1/health` endpoint (or equivalent features endpoint) reports:

```json
{
  "features": {
    "oidc": {
      "enabled": false
    }
  }
}
```

This is correct per the current configuration. Once the OIDC flow is implemented and tested, this should be updated to `enabled: true`.

## 6. Verification (For When OIDC Is Implemented)

When the OIDC flow is implemented with a sandbox provider, verify:

```bash
# Check the features endpoint
cd /c/Users/girid/Downloads/HVA/backend && .venv/bin/python -c "
from app.main import app
from fastapi.testclient import TestClient
client = TestClient(app)
response = client.get('/api/v1/health')
print(response.json())
# Expected with OIDC implemented: features.oidc.enabled should reflect the configuration
"
```

---
*Report generated per Phase K of the Mandatory Build, Test, Fix and Verify Protocol. OIDC is not implemented; password + TOTP MFA is the active authentication path. OIDC requires issuer, client_id, client_secret, and redirect_uri configuration plus a full authorization-code flow with PKCE.*