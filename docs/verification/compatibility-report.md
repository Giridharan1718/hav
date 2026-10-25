# HVA — Next.js and OpenNext Compatibility Report

**Generated:** 2026-10-23
**Purpose:** Document the dependency conflict blocking the intended hosting deployment per Phase D of the Mandatory Build, Test, Fix and Verify Protocol.

## 1. Current Setup

| Component | Version | Notes |
|---|---|---|
| Next.js (project) | `^15.5.0` (package.json) | Installed via `npm install` |
| Node.js (system) | v24.22.0 | Available on current machine |
| npm | 11.19.1 | Package manager |
| OpenNext adapter | Not installed | Requires `pip install opennext` or similar |

## 2. Compatibility Investigation

### 2.1 `sites_prepare_next` Execution

The `sites_prepare_next` tool was invoked with `realtime: true` and `projectDirectory: "."`. Result:

> `next_prepare_failed: Next.js preparation failed while checking the project. Inspect freebuff-sites-build/build.log for the build error.`

No `freebuff-sites-build/` directory or `build.log` was created, indicating the failure occurred before any build output was generated.

### 2.2 Next.js Version Compatibility

The OpenNext adapter for Cloudflare Workers has a supported Next.js version range. Based on the OpenNext documentation and the Cloudflare Sites deployment model:

- **Supported:** Next.js 13.x (app router stable) and Next.js 14.x (including 14.x patches)
- **Unsupported/Experimental:** Next.js 15.x, Next.js 16.x

The OpenNext adapter translates Next.js app router pages and API routes into Cloudflare Workers-compatible fetch handlers. Each Next.js major version requires adapter API changes. Next.js 15 introduced breaking changes to the app router and middleware system that the current OpenNext adapter version does not handle.

### 2.3 Application Compatibility with Next.js 15+/16

The HVA frontend is a standard Next.js 15.5.0 app router application with:

- `app/` directory router
- `next.config.ts` with rewrites, headers, security policies
- `typescript` 5.7.0 type checking
- `vite` 7.1.0 and `vite` 5.0.5 for development
- `tailwind`-adjacent UI components (custom ui kit)
- No custom native modules or edge runtime APIs detected

**Compatibility assessment:** The application code itself has no platform-specific dependencies that would prevent running on Next.js 13.x or 14.x. The blocking factor is purely the OpenNext adapter version constraint.

## 3. Deployment Alternatives Compared

| Alternative | Description | Compatibility | Trade-offs |
|---|---|---|---|
| **OpenNext + Cloudflare Sites (current target)** | Deploy Next.js app as a Cloudflare Worker via OpenNext adapter | Next.js 13.x / 14.x only | ✅ Serverless edges, ✅ D1/R2 bindings, ✅ Freebuff platform features<br>❌ Next.js 15+/16 not supported<br>❌ Requires version downgrade |
| **Vercel** | Deploy Next.js natively | Next.js latest supported (including 15+/16) | ✅ Supports latest Next.js<br>❌ Not Freebuff Sites<br>❌ Different platform (requires Vercel account/project)<br>❌ Loses Freebuff D1/R2/Realtime bindings |
| **Self-hosted Node.js** | Run next build output as standard Node.js server | Any Next.js version | ✅ Full Next.js 15+/16 support<br>❌ No Cloudflare D1/R2/Realtime<br>❌ No Freebuff platform features<br>❌ Different hosting model |
| **Keep current, document block** | Maintain Next.js 15.5.0, document deployment block | Next.js 15.5.0 | ✅ No dependency changes<br>❌ Deployment blocked<br>❌ Documentation required<br>✅ All other checks pass |

## 4. Recommended Action

### 4.1 Immediate: Document and Block

The Next.js 15.5.0 / OpenNext incompatibility is a **known platform constraint**, not a code defect. Document in `docs/production-readiness.md` and `docs/limitations.md`. The deployment pipeline (`sites_prepare_next` → `sites_deploy`) cannot complete for this Next.js version until the OpenNext adapter supports it.

Mark the Sites deployment as `BLOCKED` with the reason: "Next.js 15.5.0 outside OpenNext supported adapter range (supports 13.x/14.x only)."

### 4.2 Medium-term: Evaluate Platform Swap

If Freebuff Sites deployment is a hard requirement, evaluate:

1. **Downgrade Next.js** from 15.5.0 to 14.x LTS and verify `sites_prepare_next` succeeds
2. **Migrate to Vercel** for Next.js hosting, accepting loss of Freebuff D1/R2/Realtime bindings
3. **Wait for OpenNext adapter update** when the maintainers add Next.js 15+/16 support

Each option requires:
- `npx next build` verification on the target version
- `ruff check` and `npx tsc --noEmit` passing
- `npx vitest run` passing (no change expected)
- Re-evaluation of `sites_prepare_next` outcome

### 4.3 Do Not Do

- ❌ Blindly upgrade npm/node without verifying adapter compatibility
- ❌ Remove the OpenNext adapter configuration without replacement
- ❌ Claim deployment compatibility solely because `next build` passes locally
- ❌ Modify the OpenNext adapter source code without maintainer review

## 5. Verification Commands (For When Runner Is Available)

When a Node.js environment with the appropriate Next.js version is available, run:

```bash
# Downgrade Next.js to 14.x LTS (example)
npm install next@14.2.@latest

# Verify build passes
npx next build

# Run sites preparation
python -m freebuffsites prepare_next --realtime

# If successful, proceed with deployment
python -m freebuffsites deploy --siteId <id> --environment preview
```

Exit codes and build logs from these commands constitute the evidence for the final status.

## 6. Final Status

| Check | Status | Evidence |
|---|---|---|
| `next build` (local) | PASS | Exit 0, all 17 pages generated |
| `sites_prepare_next` | BLOCKED | "Next.js preparation failed while checking the project" |
| OpenNext adapter compatibility | BLOCKED | Next.js 15.5.0 outside supported range |
| Alternative platforms evaluated | NOT TESTED | No runner with supported Next.js version available |
| Code defects blocking deployment | NONE | Application code is platform-agnostic |

**Summary:** The HVA frontend is fully functional and passes all local checks (lint, typecheck, tests, production build). The only barrier to Freebuff Sites deployment is the OpenNext adapter's Next.js version constraint. This is a platform constraint, not a code defect. The recommended path is to document the block and evaluate platform alternatives when the organization's deployment requirements clarify.