# PHASE 7.5 RECOVERY — Vercel Project Re-creation

**Date:** 2026-05-05
**Operator:** Bill Asmar, O'Neill Contractors
**Branch:** `feature/nexus-precon-module`
**Trigger:** Vercel project `frontend` (originally deployed in Phase 7.5)
deleted by accident from the Vercel dashboard. Backend on Railway untouched.
**Status:** ✅ COMPLETE — new project deployed, 4/4 smoke tests green

---

## 1. Outcome

| Field | Old (Phase 7.5) | New (Phase 7.5 recovery) |
|---|---|---|
| Vercel project name | `frontend` (cosmetic, dir-name default) | **`nexus-precon-frontend`** (canonical) |
| Stable public URL | `https://frontend-six-phi-76.vercel.app` (dead) | **`https://nexus-precon-frontend.vercel.app`** |
| Project ID | (deleted) | `prj_NHQ2y87GsV3t0tevR69vEWjVVndW` |
| Org / scope | bill-6947's projects | bill-6947's projects (unchanged) |
| Latest deployment ID | `dpl_CwMCABiyFVaRZpQ9fVZ8FQFtSF1W` (gone) | `dpl_4MWgeeXCrCqivQ6NGiEWZbC65LKV` |
| Hashed deployment URL (auth-gated) | `frontend-dvtyl14gf-bill-6947s-projects.vercel.app` | `nexus-precon-frontend-pf1r2wggt-bill-6947s-projects.vercel.app` |
| Build duration | 175 s | 174 s (iteration 2; iteration 1 also built in 175 s but failed at deploy-outputs step) |
| `vercel.json` rewrite config | `(.*)` regex + SPA fallback | unchanged — no source edits |
| Backend (Railway) | `https://backend-production-ff185.up.railway.app` | unchanged |

**Net effect:** the Phase 7.5 architecture is intact. Only the Vercel project
slot was rebuilt, and the new slot uses the canonical project name flagged in
`PHASE_7_5_REPORT.md` §8.1 as a known cosmetic issue. The bug is now self-fixed.

---

## 2. Recovery procedure (executed)

1. **Local cleanup** — removed `frontend/.vercel/` so a fresh project link
   could be established.
2. **Build reuse** — `frontend/dist/` from the original Phase 7.5 build was
   ~4 hours old and content-equivalent (same source tree, no commits in
   between). No `npm run build` re-run; Vercel builds remotely anyway.
3. **`vercel.json` verified** — already had the correct `(.*)` regex
   rewrite + SPA fallback baked in by commit `c00733ac`. No edits needed.
4. **Deploy with explicit project name** —
   `vercel deploy --prod --yes --name nexus-precon-frontend`. The
   `--name` flag is deprecated but Vercel still honors it: the project was
   created and the local directory linked.
5. **Self-heal — iteration 2** — first deploy failed at the final
   "Deploying outputs..." step with `deploy_failed: Deployment not found`
   (transient Vercel platform error; build itself completed in 1m 42s and
   was cached). Project link in `.vercel/project.json` survived. Retried
   with bare `vercel deploy --prod --yes`; build was restored from cache
   (also 1m 42s) and deploy completed.
6. **Smoke tests** — same 4-test matrix as Phase 7.5 §6, against the new
   alias `https://nexus-precon-frontend.vercel.app`:

| # | URL | Got | Expected | Result |
|---|---|---|---|---|
| 1 | `/api/health` | HTTP 200 — `{"status":"healthy","version":"2.6.40","env":"production","modules_loaded":78,...}` | 200 + healthy JSON | ✅ |
| 2 | `/` | HTTP 200 — `<!DOCTYPE html>...` | 200 + index.html | ✅ |
| 3 | `/precon/dashboard` | HTTP 200 — same `<!DOCTYPE html>...` | 200 + SPA fallback | ✅ |
| 4 | `/api/precon/health/heartbeat/` | HTTP 401 + empty body | 401 (auth-gated, proxied intact) | ✅ |

**Self-heal iterations used:** 1 of 3.

---

## 3. Items still flagged for Bill

1. **Cosmetic-mismatch flag from `PHASE_7_5_REPORT.md` §8.1 is now resolved.**
   The new project name is `nexus-precon-frontend`, no longer the generic
   `frontend`.
2. **`frontend/.gitignore` was committed separately** as `7aa30ddf
   chore(frontend): ignore .vercel directory` between the original
   Phase 7.5 report and this recovery — 9 bytes, contents `.vercel`.
   The file is Vercel-CLI-auto-generated and now locks in
   `.vercel/project.json` exclusion for future operators. The
   §8.3 flag in `PHASE_7_5_REPORT.md` is therefore also resolved.
3. **The `frontend-six-phi-76.vercel.app` alias in `PHASE_7_5_REPORT.md`
   §10 is now historical / dead.** The report itself is left as-is (a
   point-in-time artefact); this recovery doc supersedes the URL fields.
4. **No GitHub auto-deploy hook configured** — same as before. Future
   redeploys still require `cd frontend && vercel deploy --prod --yes`.
5. **`--name` flag deprecation** — Vercel CLI 53.1 still honors it but
   prints a deprecation warning. Future project creation should use
   `vercel link --project <name> --yes` followed by `vercel deploy
   --prod --yes` to avoid the warning.

---

## 4. Constraints respected during recovery

- ❌ No `pip install` or `pip upgrade`
- ❌ No `pyproject.toml` edits
- ❌ No upstream OCERP pull
- ❌ No Docker rebuild
- ❌ No Railway redeploy or backend changes
- ❌ No source-file edits (Python, TypeScript, JSON config)
- ❌ Phase 7.6 not started
- ✅ Only Vercel CLI deploy + git commit/push + this report

---

## 5. Production state at end of Phase 7.5 recovery

### Frontend (Vercel — recreated)

| Field | Value |
|---|---|
| Public URL | `https://nexus-precon-frontend.vercel.app` |
| Latest deployment ID | `dpl_4MWgeeXCrCqivQ6NGiEWZbC65LKV` |
| Latest hashed URL (auth-gated) | `https://nexus-precon-frontend-pf1r2wggt-bill-6947s-projects.vercel.app` |
| Project ID | `prj_NHQ2y87GsV3t0tevR69vEWjVVndW` |
| Org ID | `team_4of4vqMhG6YkaHeJc1eapGRh` |
| Build duration (last deploy) | 174 s |
| `vercel.json` source | `frontend/vercel.json` (unchanged from `c00733ac`) |

### Backend (Railway — unchanged)

| Field | Value |
|---|---|
| Public URL | `https://backend-production-ff185.up.railway.app` |
| Reachable via Vercel rewrite at | `https://nexus-precon-frontend.vercel.app/api/*` |

### Git state

| | |
|---|---|
| Branch | `feature/nexus-precon-module` |
| Latest commit (this) | `docs(precon): Phase 7.5 recovery report` |
| Files changed in this commit | `PHASE_7_5_RECOVERY.md` (new) |
| Previous commits | `7aa30ddf` (frontend/.gitignore), `d7a441f0` (Phase 7.5 report), `c00733ac` (infra housekeeping), `0cd228aa`, `fd5b0c34` |
| Pushed to origin | (about to be) ✅ |

---

**Phase 7.5 recovery is COMPLETE.** Standing by for Phase 7.6 (DNS cutover for
`nexus.eliteal.info` and `api.nexus.eliteal.info`) — not started.
