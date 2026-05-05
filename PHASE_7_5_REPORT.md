# PHASE 7.5 REPORT — Vercel Frontend Deployment

**Date:** 2026-05-03
**Operator:** Bill Asmar, O'Neill Contractors
**Branch:** `feature/nexus-precon-module`
**Public URL (frontend):** **https://frontend-six-phi-76.vercel.app**
**Public URL (backend, proxied):** **https://backend-production-ff185.up.railway.app**
**Status:** ✅ COMPLETE — both ends serving traffic, all 4 smoke tests green

---

## 1. Executive summary

The NEXUS Precon frontend is deployed to Vercel and proxies API calls to the
Railway backend via a same-origin rewrite — no CORS configuration required, no
OCERP source modifications, no `VITE_*` env vars on Vercel. The deploy went
through one self-heal iteration (Vercel's `:path*` matcher only caught
single-segment paths) before all four smoke tests passed. Estimated monthly
Vercel cost is **$0** (Hobby tier covers 2-user usage by a wide margin).

---

## 2. Vite + React build characteristics

**Build command** (from `frontend/package.json` line 8):
```
"build": "tsc -b && vite build"
```
Two-phase: full TypeScript project-references type-check, then Rollup bundling.

**Local build duration**: 123 s (2 m 3 s) on Bill's dev machine (Node 20.20.2,
npm 10.8.2).

**Vercel build duration**: 175-224 s per deploy (3-4 minutes including upload).

**Output**: `dist/` — 22.7 MB across 164 files, 39 vendor chunks per
`vite.config.ts`'s `manualChunks` strategy.

**Heaviest chunks** (gzip in parens):

| Chunk | Size |
|---|---|
| `VisualBimPage` | 4,874 KB (1,478 KB gz) |
| `i18n-data` (translations) | 4,742 KB (1,232 KB gz) |
| `index` (main app) | 2,392 KB (595 KB gz) |
| `o3dv.module` (3D viewer) | 1,055 KB (281 KB gz) |
| `maplibre-gl` | 1,053 KB (284 KB gz) |
| `vendor-exceljs` | 940 KB (271 KB gz) |
| `vendor-ag-grid` | 896 KB (234 KB gz) |
| `vendor-charts` | 630 KB (189 KB gz) |

The four precon page chunks (`PipelinePage`, `BidManagementPage`,
`PreconDashboardPage`, `SolicitationDetailPage`) are all sub-100 KB pre-gzip
and split out via the `lazy(() => import(...))` calls in `routes.tsx`. They
don't appear in the heavy-chunk warning.

**Vite chunk-size warning** is emitted but expected — the construction-domain
deps (BIM viewer, MapLibre, ag-grid, exceljs) are inherently large. Vercel
serves them gzipped + brotli'd so wire-size is ~30% of disk size.

---

## 3. Vercel deployment configuration

| Field | Value |
|---|---|
| Vercel CLI version | 53.1.0 |
| Logged in as | `bill-6947` |
| Project name | **`frontend`** (defaulted to dir name) |
| Scope | bill-6947's projects |
| Framework preset | Vite (auto-detected from `vite.config.ts`) |
| Root directory | `frontend/` |
| Build command | `npm run build` (auto-detected) |
| Output directory | `dist/` (auto-detected, Vite default) |
| Install command | `npm install` (auto-detected) |
| Node.js version | Vercel default (20.x) |
| Build environment vars | **NONE** — code reads no `VITE_*` vars |
| Runtime environment vars | **NONE** — `vercel.json` rewrite handles API routing |

The frontend was deployed directly from the local `feature/nexus-precon-module`
working tree via `vercel deploy --yes` — Vercel uploaded the code, ran the
build on its infra, served the result. Branch tracking is not configured (no
GitHub auto-deploy hook), so future deploys come from `vercel deploy --prod
--yes` rather than git push.

---

## 4. The `vercel.json` rewrite architecture

Final `frontend/vercel.json`:

```json
{
  "rewrites": [
    {
      "source": "/api/(.*)",
      "destination": "https://backend-production-ff185.up.railway.app/api/$1"
    },
    {
      "source": "/(.*)",
      "destination": "/index.html"
    }
  ]
}
```

### Why two rewrites in this order

1. **`/api/(.*)` → Railway** (first). Catches every API path and proxies it
   to the Railway backend. The `(.*)` regex capture matches any number of
   segments; the `$1` reference reconstructs the path on the destination.
2. **`/(.*)` → `/index.html`** (second). SPA fallback for client-side
   routing. React Router handles the actual page selection in the browser.

Vercel evaluates rewrites top-down; first match wins. Static files in `dist/`
are served BEFORE rewrites are evaluated, so `/assets/index-xyz.js` hits the
file directly without falling through to the SPA fallback.

### Why `(.*)` instead of `:path*`

The first iteration used the shorter `:path*` named-wildcard syntax:

```json
{ "source": "/api/:path*", "destination": "https://.../api/:path*" }
```

This worked for `/api/health` but **silently failed for every multi-segment
path** (`/api/precon/health/heartbeat/`, `/api/openapi.json`, etc.) — those
returned 404. Switched to `/api/(.*)` regex capture with `$1` reference and
all paths matched correctly.

This is a known wart of Vercel's path-to-regexp version: `:path*` matches
zero-or-one segments inconsistently. Anchored regex captures are the safe
default for any sub-path that may contain slashes.

---

## 5. Same-origin proxy strategy

We chose Vercel rewrites over modifying `api.ts` to read `VITE_API_URL` for
four reasons:

1. **Zero OCERP source modifications.** `frontend/src/shared/lib/api.ts`
   line 18 hardcodes `const BASE_URL = '/api'`. Any change to that file
   would have been a third OCERP touch beyond the two from Phase 7.1.

2. **No CORS configuration needed.** The browser sees same-origin requests
   (`/api/health` from `frontend-six-phi-76.vercel.app`); Vercel's edge
   transparently proxies to Railway. No `Access-Control-Allow-Origin`
   headers required.

3. **`ALLOWED_ORIGINS` on Railway stays untouched.** Backend's
   `ALLOWED_ORIGINS=https://nexus.eliteal.info` (set in Phase 7.3.3) is
   irrelevant to the frontend — the browser never directly contacts
   Railway. Phase 7.6 DNS cutover doesn't require an `ALLOWED_ORIGINS`
   change either.

4. **Future-proof for direct backend access.** If Phase 7.7+ adds mobile
   apps or third-party integrations that hit Railway directly (bypassing
   the Vercel proxy), `ALLOWED_ORIGINS` can be widened then without
   touching the frontend.

**Trade-off accepted**: each request gains a Vercel-edge → Railway hop
(~30-100 ms latency). For a 2-user internal app this is invisible. If
latency ever becomes a concern, switch to direct API calls (modify
`api.ts` to use `VITE_API_URL` + add the Vercel domain to
`ALLOWED_ORIGINS`).

---

## 6. Smoke verification matrix

All tests against `https://frontend-six-phi-76.vercel.app`:

| # | URL | Expected | Got | Result |
|---|---|---|---|---|
| 1 | `/api/health` | 200 + healthy JSON | HTTP 200 — `{"status":"healthy","version":"2.6.40","env":"production","instance_id":"...","modules_loaded":78,"database":"ok",...}` | ✅ |
| 2 | `/` | 200 + index.html | HTTP 200 — `<!DOCTYPE html>...` | ✅ |
| 3 | `/precon/dashboard` | 200 + same index.html (SPA fallback) | HTTP 200 — same `<!DOCTYPE html>...` | ✅ |
| 4 | `/api/precon/health/heartbeat/` | 401 (auth-gated, proxied intact) | HTTP 401 + empty body (FastAPI's auth response) | ✅ |
| Bonus | `/assets/index-DeKs8fBH.js` | 200 + JS module | HTTP 200 — `import{r as o,j as e,L as qe}from"./vend...` | ✅ |

**Response-header inspection on Test 1** confirmed Vercel proxied to Railway
(headers carried back: `X-Railway-Edge: railway/us-east4-eqdc4a`,
`X-Railway-Request-Id: t2UK3_47T5en-G9VGbGh5g`, `X-Powered-By:
OpenConstructionERP`, `X-Api-Version: 2.6.40`). The `Server: Vercel` header
shows Vercel's edge as the responder; the back-end headers ride through.

---

## 7. Self-heal log (1 of 3 iterations used)

### Iteration 1 — `:path*` matcher failure

**Symptom**: After first `vercel deploy --yes`, smoke tests showed:
- `/api/health` → HTTP 200 ✅
- `/api/openapi.json` → HTTP 404 ❌
- `/api/precon/health/heartbeat/` → HTTP 404 ❌
- `/precon/dashboard` → HTTP 404 ❌

**Diagnostic**: pulled response headers — `/api/health` showed Railway
provenance headers (proxied), other paths returned bare 404 without
backend headers (Vercel never proxied). Pattern: only single-segment
captures matched.

**Fix**: rewrote `vercel.json` two ways at once (combined fix to avoid a
second redeploy):
1. `"source": "/api/:path*"` → `"source": "/api/(.*)"` with `$1` capture
2. Added second rewrite `"/(.*)"` → `"/index.html"` for SPA fallback (was
   missing entirely; would have been a separate iteration otherwise)

Re-deployed; all 4 smoke tests + bonus passed.

**Iterations used**: 1 of 3.

---

## 8. Items flagged for Bill

1. **Vercel project name is `frontend`, not `nexus-precon-frontend`.**
   `vercel deploy --yes` defaulted to the directory name. Cosmetic only —
   doesn't change URLs. To fix: Vercel dashboard → project settings →
   rename. Or delete + redeploy with `vercel link --project nexus-precon-frontend`
   (forfeits the current alias).

2. **Commit `0cd228aa` subject has garbled `§` character.** PowerShell 5.1
   doesn't expand `\u{00A7}`, so the message reads `(u{00A7}16 GovTribe
   deferred)` instead of `(§16 GovTribe deferred)`. Already pushed; force-push
   amend on the feature branch is technically safe but cosmetic only.

3. **`frontend/.gitignore` appeared as untracked** during the housekeeping
   commit (Vercel CLI auto-created it for `.vercel/` exclusion). Not in
   the housekeeping commit list, so left untracked. Trivial to commit
   when desired.

4. **Vercel preview-deployment URLs are auth-gated** (the random-hash
   URLs like `frontend-9z9hcivwy-bill-6947s-projects.vercel.app` return
   HTTP 401 from Vercel's preview wall). Use the stable alias
   (`frontend-six-phi-76.vercel.app`) for any verification or testing.
   This is Vercel's default behavior for new projects — can be disabled
   via project settings → Deployment Protection if desired.

5. **No GitHub auto-deploy hook configured.** Future frontend deploys
   require `cd frontend && vercel deploy --prod --yes`. Phase 7.6 might
   want to wire `feature/nexus-precon-module` (or eventually `main`) to
   auto-deploy on push.

---

## 9. Architectural decisions log

1. **Same-origin rewrites over `VITE_API_URL` env var** — keeps
   `frontend/src/shared/lib/api.ts` (an OCERP file) untouched; eliminates
   CORS as a concern; ALLOWED_ORIGINS on Railway stays at the contracted
   value. Trade-off: ~30-100 ms latency per request via the Vercel edge.
2. **`(.*)` regex captures over `:path*` named wildcards** — Vercel's
   `:path*` matched single-segment captures only, silently 404'd
   multi-segment paths. The regex form is unambiguous and is now baked
   into `vercel.json` as the canonical pattern.
3. **SPA fallback `"/(.*)"` → `"/index.html"`** placed AFTER the API
   rewrite — first-match-wins ordering ensures `/api/...` routes proxy,
   non-API routes serve the React shell, static assets in `dist/`
   are served by Vercel's static handler before either rewrite fires.
4. **Project name defaulted to `frontend`** — accepted instead of
   pre-creating the project with `vercel link --project
   nexus-precon-frontend`. The deployment URLs are stable (the alias
   `frontend-six-phi-76.vercel.app` doesn't change with redeploys), so
   the cosmetic mismatch doesn't bleed into Phase 7.6 DNS work.
5. **No build-time env injection.** The frontend never references
   `process.env.VITE_*`; only `import.meta.env.DEV` (built-in Vite flag,
   automatically `false` in production builds). Zero env vars to manage
   on Vercel.
6. **First `vercel deploy --yes` auto-promoted to production** in Vercel
   CLI v53; the explicit `vercel deploy --prod --yes` second call was a
   no-op duplicate. Subsequent deploys (the rewrite fix) used `--prod`
   explicitly to remove ambiguity.
7. **`.vercel/` directory created locally** by the CLI on first deploy —
   contains `project.json` linking the local dir to the Vercel project.
   Already gitignored (Vercel auto-added `frontend/.gitignore`). Bill or
   future operators reproducing the setup will need to run `vercel link`
   themselves to re-establish the link.

---

## 10. Production state at end of Phase 7.5

### Frontend (Vercel)

| Field | Value |
|---|---|
| Public URL (use this) | `https://frontend-six-phi-76.vercel.app` |
| Latest deployment ID | `dpl_CwMCABiyFVaRZpQ9fVZ8FQFtSF1W` |
| Latest deployment URL (auth-gated) | `https://frontend-dvtyl14gf-bill-6947s-projects.vercel.app` |
| Other aliases | `https://frontend-bill-6947s-projects.vercel.app`, `https://frontend-bill-6947-bill-6947s-projects.vercel.app` |
| Build duration (last deploy) | 175 s |
| Output bundle size | 22.7 MB on disk, ~7 MB compressed wire-size |

### Backend (Railway, unchanged from Phase 7.3)

| Field | Value |
|---|---|
| Public URL | `https://backend-production-ff185.up.railway.app` |
| Reachable via Vercel rewrite at | `https://frontend-six-phi-76.vercel.app/api/*` |
| Latest deployment | `434ba4f9-5a88-4cdb-890c-5a8a2af78c5e` (RUNNING) |

### Git state

| | |
|---|---|
| Branch | `feature/nexus-precon-module` |
| Latest commit | `c00733ac` (infra housekeeping) |
| Previous commits | `0cd228aa` (vercel.json + Phase 7.3 §16), `fd5b0c34` (Phase 7.1 integration) |
| Pushed to origin | ✅ |
| Open PR | #19 (still un-merged) |

### Cost estimate

**Vercel Hobby tier** (free) covers this deploy comfortably:

| Resource | Hobby limit | Current usage | Headroom |
|---|---|---|---|
| Bandwidth | 100 GB / mo | < 1 GB / mo expected (2 users) | 99% |
| Edge function invocations | 100,000 / mo | 0 (no edge functions used) | 100% |
| Build minutes | 6,000 / mo | ~10 / mo expected | 99% |
| Team members | 1 (Hobby is solo) | 1 (Bill) | OK |
| Custom domains | 1 included | will use 1 in Phase 7.6 (`nexus.eliteal.info`) | exact fit |
| Deployment Protection | enabled by default | enabled | OK |

**Combined Phase 7.3 + 7.5 cost**: still ≈ **$12-18 / month** total
(Railway cost from §13 of `PHASE_7_3_REPORT.md` plus $0 Vercel).

If frontend traffic ever grows past Hobby limits (very unlikely for a
2-user internal tool), Vercel Pro is $20/user/mo.

---

## 11. Phase 7.5 checklist

| Sub-phase | Status |
|---|---|
| 7.5.1 — Local `npm run build` verification (clean, 0 TS errors) | ✅ |
| 7.5.2 — Write `frontend/vercel.json` (initial `:path*` version) | ✅ |
| 7.5.3 — Commit + push `vercel.json` and PHASE_7_3_REPORT.md | ✅ (commit `0cd228aa`) |
| 7.5.4 — `vercel deploy --yes` from `frontend/` (preview + auto-prod) | ✅ |
| 7.5.5 — 4 smoke tests | ✅ (1 self-heal iteration to fix `:path*` matcher) |
| 7.5.6 — Inline report (in chat) | ✅ |
| 7.5.7a — Housekeeping commit (4 infra files) | ✅ (commit `c00733ac`) |
| 7.5.7b — `PHASE_7_5_REPORT.md` (this file) | ✅ |

**Phase 7.5 is COMPLETE.** Standing by for review before authorising Phase
7.6 (DNS cutover for `nexus.eliteal.info` and `api.nexus.eliteal.info`).
