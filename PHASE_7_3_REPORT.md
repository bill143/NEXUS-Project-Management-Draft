# PHASE 7.3 REPORT — Railway Backend Deployment

**Date:** 2026-05-03
**Operator:** Bill Asmar, O'Neill Contractors
**Branch:** `feature/nexus-precon-module`
**Public URL:** **https://backend-production-ff185.up.railway.app**
**Status:** ✅ COMPLETE — backend live, all 15 verification checkpoints green

---

## 1. Executive summary

The NEXUS Precon backend is deployed to Railway, running against a managed Postgres
+ Redis stack, and serving authenticated requests at the public URL above.  The
deploy went through three deliberate self-heal iterations (Railway upload size,
`LOG_LEVEL` casing, OCERP migration-chain bug) plus two env-name discoveries
(`APP_ENV` vs `ENV`, `JWT_SECRET` vs `JWT_SECRET_KEY`) — all documented below.
Zero OCERP source files modified beyond the two from Phase 7.1.  Estimated
monthly Railway cost is ≈ **$15–20** at current usage.

---

## 2. Dockerfile design decisions

`Dockerfile` (104 lines, repo root):

* **Multi-stage build** — `builder` stage installs build tools + pip wheels into a
  venv at `/opt/venv`; `runtime` stage carries only the venv + source + `curl`.
  Keeps the runtime image surface small.
* **`python:3.12-slim-bookworm`** — matches Bill's local 3.12 and OCERP's
  `requires-python = ">=3.12"`.
* **Non-root `app` user** (UID 1000) — `USER app` before `EXPOSE`; `chown -R app:app /app`
  bakes ownership at build time.
* **Healthcheck**: `curl -fsS http://localhost:${PORT}/api/health` with
  `--start-period=40s` so the 78-module OCERP startup gets room before the
  container is marked unhealthy.
* **Build context entrypoint**: `Dockerfile` lives at repo root; build context
  is repo root; `WORKDIR /app` for both alembic and uvicorn so relative paths
  (`alembic.ini` → `script_location = alembic`) resolve correctly.
* **`uvicorn ... --proxy-headers --forwarded-allow-ips='*'`** — required so
  Railway's `X-Forwarded-Proto` / `X-Forwarded-For` headers propagate; without
  these, FastAPI sees Railway's internal IP everywhere and HTTPS detection breaks.

---

## 3. Hatchling `/frontend/dist` placeholder workaround

`pyproject.toml` lines 175-181 declare:

```toml
[tool.hatch.build.targets.wheel.force-include]
"../frontend/dist" = "app/_frontend_dist"
```

This is for the `openestimate serve` CLI mode that bundles the React build into
the Python wheel.  Backend-only Railway deploy never serves the bundled assets
(Vercel does), but hatchling treats `force-include` as a hard requirement —
missing path → `FileNotFoundError` → `pip install` aborts.

Resolution: builder stage creates an empty `/frontend/dist/.placeholder` file
before `pip install`.  Hatchling walks the dir, finds nothing, includes nothing
in the wheel.

Decision rationale (per Bill's review of three options): keep the placeholder
because (a) auditable surface area stays smallest, (b) doesn't fork OCERP
upstream, (c) ~50 MB image bloat avoided vs pre-building the React bundle.
Federal compliance auditors prefer documented in-line workarounds over silent
upstream forks.

---

## 4. Railway project structure

| Field | Value |
|---|---|
| Project name | `nexus-precon-prod` |
| Project ID | `ddf1506f-2b2c-44f2-9414-5db3ef55091b` |
| Project URL | https://railway.com/project/ddf1506f-2b2c-44f2-9414-5db3ef55091b |
| Workspace | Bill Asmar's Projects |
| Environment | `production` (ID `bbe526ec-f238-480e-a453-bba2d4d9ecaf`) |
| Region | `us-east4-eqdc4a` (Google Cloud — Virginia US East) |

**Three services:**

| Service | ID | Image | Volume |
|---|---|---|---|
| Postgres | `ba7bda52-087c-4579-ae4e-882a569e5091` | `ghcr.io/railwayapp-templates/postgres-ssl:18` | `postgres-volume`, 5 GB, `/var/lib/postgresql/data` |
| Redis | `5a4efa59-4cb9-4aed-a63b-77fdab1a3616` | `redis:8.2.1` | `redis-volume`, 5 GB, `/data` |
| backend | `093acae7-d0fe-41b2-9789-87fb8cd6e841` | (custom Dockerfile from feature/nexus-precon-module branch) | — |

---

## 5. Environment variables (12 set on backend service)

Two more added since the original 11 in §7.3.3:

| Name | Value | Status |
|---|---|---|
| `DATABASE_URL` | `postgresql+asyncpg://${{Postgres.PGUSER}}:${{Postgres.PGPASSWORD}}@${{Postgres.RAILWAY_PRIVATE_DOMAIN}}:${{Postgres.PGPORT}}/${{Postgres.PGDATABASE}}` | ✅ |
| `DATABASE_SYNC_URL` | `${{Postgres.DATABASE_URL}}` | ✅ |
| `REDIS_URL` | `${{Redis.REDIS_URL}}` | ✅ |
| `SECRET_KEY` | (64-char hex hidden) | ✅ unused by OCERP — kept per brief |
| `JWT_SECRET_KEY` | (64-char hex hidden) | ✅ unused by OCERP — kept per brief |
| **`JWT_SECRET`** ← added | (64-char hex hidden) | ✅ this is the var OCERP actually reads |
| `ENV` | `production` | ✅ unused by OCERP — kept per brief |
| **`APP_ENV`** ← added | `production` | ✅ this is the var OCERP actually reads |
| `LOG_LEVEL` | `INFO` (was `info`) | ✅ |
| `PORT` | `8000` | ✅ |
| `GOVTRIBE_MCP_ENABLED` | `false` (Phase 7.4 will flip) | ✅ |
| `GOVTRIBE_ALERT_EMAIL` | `bill@oneillcontractors.com` | ✅ |
| `ALLOWED_ORIGINS` | `https://nexus.eliteal.info` | ✅ |

**Two env-name discoveries** documented in §14 (architectural decisions).

---

## 6. Three-iteration self-heal log

### Deploy attempt 1 — Cloudflare 413

```
node.exe : Failed to upload code. File too large (360054311 bytes)
HTTP 413 Payload Too Large
```

Root cause: Railway CLI v4.44.0 didn't honor `.gitignore` for sub-path patterns
(`backend/openestimate.db` was gitignored on lines 36 + 166 but still
uploaded).  The 360 MB upload exceeded Cloudflare's 100 MB ingress cap.

Fix: created `.railwayignore`.  First attempt was a `*` whitelist — gitignore
semantics meant re-included parent directories did NOT re-include their
contents, so `backend/alembic/env.py` was missing in the build (build
succeeded, container crashed at runtime with `Can't find Python file alembic/env.py`).

Second attempt: blacklist-only `.railwayignore` (just the heavy local dirs +
files explicitly).  Worked.  Upload dropped to a few MB.

### Deploy attempt 2 — `LOG_LEVEL=info` rejected

```
pydantic_core._pydantic_core.ValidationError: 1 validation error for Settings
log_level
  Input should be 'DEBUG', 'INFO', 'WARNING' or 'ERROR'
  [type=literal_error, input_value='info', input_type=str]
```

Root cause: brief specified `LOG_LEVEL=info` (lowercase); OCERP's
`Settings.log_level` is `Literal["DEBUG", "INFO", "WARNING", "ERROR"]`
(uppercase only).

Fix: `railway variables --set 'LOG_LEVEL=INFO'`.  Auto-redeploy.

### Deploy attempt 3 — OCERP migration chain bug

```
sqlalchemy.exc.ProgrammingError: (psycopg2.errors.UndefinedTable)
relation "oe_documents_document" does not exist
```

Root cause: pre-existing OCERP migration chain incompleteness — see §7.

Fix: rewrote `docker-entrypoint.sh` to bootstrap with `Base.metadata.create_all`
before alembic — see §8.

---

## 7. OCERP migration chain bug analysis

OCERP has **39 alembic migrations** but **no migration creates `oe_documents_document`**.
Migration `ffe3f561e2c1_add_documents_bim_link_table.py` (down_revision `f22fa2934807`)
declares an FK to that table:

```python
sa.ForeignKey("oe_documents_document.id", ondelete="CASCADE"),
```

Bill's local SQLite dev DB has the table because OCERP's startup hook
(`main.py:1428-1497`) calls `Base.metadata.create_all` for both SQLite AND
PostgreSQL — that's where `oe_documents_document` gets created.  The hook
runs BEFORE alembic on every fresh boot.

Our Phase 7.3.4 entrypoint inverted the order: `alembic upgrade head` BEFORE
`uvicorn` (so OCERP's startup hook never gets a chance to run).  The chain
crashes immediately on a fresh PG volume.

**This is an OCERP-side bug, not introduced by Phase 7.3** — it's been latent
because the docker-compose dev workflow uses SQLite (which doesn't enforce FKs
by default, masking the order issue).  Filed as a flagged item for upstream in
§12.

---

## 8. Entrypoint fix architecture (4-step bootstrap)

`docker-entrypoint.sh` (195 lines, all in-line documented):

```
Step 1/4: model registration + create_all
  → Inline Python heredoc imports the same 47 OCERP model modules main.py:1431-1481
    imports verbatim, plus app.modules.precon.models.  Defensive try/except
    per import — a missing module logs WARN but doesn't abort.
  → Builds sync engine from DATABASE_SYNC_URL.
  → Base.metadata.create_all(engine) — idempotent.  Creates only tables not
    already present.  This is what materialises oe_documents_document and
    closes the OCERP migration-chain gap.

Step 2/4: alembic state detection + stamp/upgrade
  → Inspects pg_tables for alembic_version.  Writes "yes" or "no" to
    /tmp/alembic_state.txt for the shell to read.
  → If "no" (first deploy): alembic stamp head — locks v2g0 as the current
    revision without replaying.  create_all already made the schema; replay
    would conflict.
  → If "yes" (subsequent deploy): alembic upgrade head — no-op or applies
    new revisions (Step 8+).

Step 3/4: bootstrap complete

Step 4/4: exec uvicorn
  → uvicorn app.main:create_app --factory --host 0.0.0.0 --port ${PORT:-8000}
    --proxy-headers --forwarded-allow-ips='*'
```

Bootstrap log on first deploy:

```
[entrypoint] Step 1/4: registering models + create_all (mirrors main.py:1428-1497)
[bootstrap] imported 48 model modules (0 skipped)
[bootstrap] running Base.metadata.create_all (idempotent)...
[bootstrap] create_all complete — 118 tables registered
[bootstrap] alembic_version table present: False
[entrypoint] Step 2/4: first deploy — stamping alembic to head (no migration replay)
INFO  [alembic.runtime.migration] Running stamp_revision -> v2g0_nexus_precon_init
[entrypoint] Step 3/4: bootstrap + alembic complete
[entrypoint] Step 4/4: starting uvicorn on 0.0.0.0:8000
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000
```

---

## 9. Verification matrix

| # | Check | Result |
|---|---|---|
| 1 | Dockerfile builds locally | ✅ 112 s cold, 1.17 GB image |
| 2 | Docker container runs healthy locally with Postgres | ✅ HTTP 200 on `/api/health` |
| 3 | Railway upload | ✅ ≪ 100 MB after `.railwayignore` |
| 4 | Railway build | ✅ 41-134 s per iteration |
| 5 | Railway deploy status | ✅ SUCCESS · instance RUNNING |
| 6 | Bootstrap log: model imports | ✅ 48/48 imported, 0 skipped |
| 7 | Bootstrap log: `create_all` | ✅ 118 tables registered |
| 8 | Bootstrap log: first-deploy detection | ✅ `alembic_version table present: False` |
| 9 | Bootstrap log: `alembic stamp head` | ✅ `Running stamp_revision -> v2g0_nexus_precon_init` |
| 10 | Uvicorn startup | ✅ `Started server process [1]` · `Application startup complete` |
| 11 | Public `GET /api/health` | ✅ HTTP 200 · `{"status":"healthy","env":"production","modules_loaded":78,"database":"ok",...}` |
| 12 | Public `GET /api/precon/health/heartbeat/` | ✅ HTTP 401 (auth gate live, route registered) |
| 13 | `alembic_version` on prod Postgres | ✅ `['v2g0_nexus_precon_init']` |
| 14 | 5 `oe_nexus_precon_*` tables on prod Postgres | ✅ all 5 present |
| 15 | `"env":"production"` in `/api/health` | ✅ after `APP_ENV=production` set |

---

## 10. `IF NOT EXISTS` convention for future precon migrations

The bootstrap fix in §8 calls `Base.metadata.create_all` BEFORE `alembic upgrade head`.
This pattern is safe for v2g0 (which already uses `_create_if_not_exists` /
`_has_column` / `_create_index_if_not_exists` helpers), but **future precon
migrations must follow the same convention** or they will conflict with
`create_all` on first-deploy bootstrap.

**Mandatory pattern for every precon migration (Step 8+):**

```python
def _table_exists(table: str) -> bool:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    return table in insp.get_table_names()

def _has_column(table: str, column: str) -> bool: ...

def _create_if_not_exists(table_name: str, *columns, **kw) -> None:
    if not _table_exists(table_name):
        op.create_table(table_name, *columns, **kw)

def _create_index_if_not_exists(index_name: str, table_name: str, columns: list, **kw) -> None: ...
def _drop_index_if_exists(index_name: str, table_name: str) -> None: ...
def _drop_table_if_exists(table_name: str) -> None: ...
```

These helpers already exist in `v2g0_nexus_precon_init.py` lines 75-117.  Either
copy them verbatim into each new migration or promote them to a shared
`backend/app/modules/precon/_alembic_helpers.py` module.

**Why this matters:** without IF NOT EXISTS guards, a fresh PG volume would
have `create_all` make a table, then alembic try to `CREATE TABLE` the same
table → `relation "..." already exists`.  v2g0's helpers are the precedent.

---

## 11. Public URL and how to test

**Backend URL:** `https://backend-production-ff185.up.railway.app`

```bash
# Health check (expect 200)
curl https://backend-production-ff185.up.railway.app/api/health

# Precon route (expect 401 — auth-gated)
curl https://backend-production-ff185.up.railway.app/api/precon/health/heartbeat/

# Precon listing (expect 401)
curl https://backend-production-ff185.up.railway.app/api/precon/opportunities/

# Backend OpenAPI spec (expect 200, JSON schema)
curl https://backend-production-ff185.up.railway.app/openapi.json
```

---

## 12. Items flagged for Bill

1. **OCERP migration-chain bug** (§7) — `oe_documents_document` and
   `oe_documents_bim_link` have FK relationship but no migration creates
   `oe_documents_document`.  Latent because dev uses SQLite.  Not fixed here
   (out of scope); our entrypoint works around it via `create_all`.  Worth
   filing upstream for OCERP.
2. **OCERP demo-seed bug** — `oe_changeorders_order.variation_type` is
   `varchar(20)` but a seed value exceeds that length.  OCERP's seed code
   wraps in try/except and logs "Failed to seed demo account (non-fatal)" —
   non-blocking.  Same backlog as above.
3. **Two env-var name mismatches in the original Phase 7.3 brief**:
   - Brief said `ENV=production`; OCERP reads `APP_ENV`.  Both set; `ENV` is
     dead weight (kept per "minimum-change" posture).
   - Brief said `JWT_SECRET_KEY`; OCERP reads `JWT_SECRET`.  Both set;
     `JWT_SECRET_KEY` is dead weight.  Same posture.
   - `SECRET_KEY` (also from brief) — no `secret_key` field in OCERP config
     at all.  Pure dead weight.  Probably future-reserved for Step 7.7
     auth setup; harmless.
4. **`ALLOWED_ORIGINS=https://nexus.eliteal.info`** is set ahead of the
   actual DNS (Phase 7.6).  Once Vercel preview URLs come online (Phase 7.5),
   we'll need to add them temporarily so the preview frontend can hit the API.
5. **`POSTGRES_DB=railway`** (Railway template default), not
   `openestimate` (local dev).  No functional impact; flagging if Bill
   inspects production DB by name.
6. **LanceDB not installed in production image** — `[vector]` extra omitted
   from the install.  OCERP gracefully degrades: "Failed to connect LanceDB:
   No module named 'lancedb' — Semantic search is disabled."  If Bill wants
   semantic search live in production, add `lancedb` + `fastembed` to a
   second pip install in the Dockerfile builder.  Image grows ~150 MB.
7. **Pre-existing Railway projects on same workspace** (`surprising-abundance`,
   `artistic-dedication`, both running `echo-litellm-proxy`) — separate billing
   line items, not in scope for Phase 7 audit.

---

## 13. Cost estimate

Railway pricing (as of 2026-05-03):

| Service | Resource baseline | Hourly | Monthly est. |
|---|---|---|---|
| Postgres 18 + 5 GB volume | 0.5 vCPU, 512 MB RAM | $0.000463 / GB-hr RAM + $0.000231 / vCPU-hr | ≈ $5–7 |
| Redis 8.2.1 + 5 GB volume | 0.25 vCPU, 256 MB RAM | same per-resource pricing | ≈ $2–3 |
| Backend (custom image) | ~315 MB RAM at idle, low CPU | usage-based | ≈ $5–8 |
| Egress | first 100 GB/mo free, then $0.10/GB | low traffic at this stage | ≈ $0 |
| **Total estimate** | | | **≈ $12–18 / month** |

Headroom: Bill's Railway plan limits not yet surfaced.  Quickstart team plan
typically caps at $20 included usage, then pay-as-you-go.

Cost will rise in Phase 7.4 (GovTribe MCP service) and Phase 7.5 (frontend on
Vercel — separate, free tier likely sufficient for two users).

---

## 14. Architectural decisions log

1. **Hatchling `/frontend/dist` empty placeholder** vs pre-build vs upstream
   pyproject change.  Kept placeholder; documented in Dockerfile.  See §3.
2. **`.railwayignore` blacklist over whitelist.**  Whitelist gitignore semantics
   meant re-included parent dirs didn't re-include their contents.  Blacklist
   is clearer and more robust to filesystem layout changes.
3. **Single batched `railway variables --set`** for all 11 (later 12) env vars.
   Avoids 11 redeploys.
4. **`DATABASE_URL` constructed via individual `${{Postgres.PGUSER}}` etc.
   references**, not `${{Postgres.DATABASE_URL}}` directly — required to
   prepend the `+asyncpg` driver scheme that OCERP's `create_async_engine`
   needs.  Still 100% reference-driven; no static credentials.
5. **`DATABASE_SYNC_URL` added** to the brief's 10-var list (now 12 total) —
   alembic's `env.py` uses `settings.database_sync_url` for both online and
   offline migrations.  Without this var, `alembic upgrade head` would crash
   on container startup.
6. **`docker-entrypoint.sh` does `create_all` BEFORE alembic** to materialise
   tables OCERP has no migration for (the chain bug in §7).  Mirrors OCERP's
   own startup-hook pattern at `main.py:1428-1497`, just shifted earlier so
   alembic + uvicorn both see a fully-bootstrapped schema.  See §8.
7. **`alembic stamp head` on first deploy** instead of `upgrade head`.
   `create_all` already made the schema; replaying every migration would
   conflict.  Subsequent deploys use `upgrade head` (idempotent + applies
   any new revisions).
8. **Defensive model imports in entrypoint** — every import wrapped in
   try/except logging WARN on failure.  If OCERP renames a module in
   future, the bootstrap warns but continues.
9. **`/tmp/alembic_state.txt` shell↔Python bridge** — flag file for the
   shell to read instead of `$()` command substitution from heredoc Python
   (which is fragile in `sh`).
10. **Two env-var name discoveries** (`APP_ENV` for env, `JWT_SECRET` for
    JWT secret).  Found by inspecting OCERP `config.py` field declarations
    and matching `pydantic-settings`'s default mapping (`field: type` →
    `FIELD` env var).  Original brief used different names which OCERP
    silently ignored, defaulting to `development` mode and a known-insecure
    JWT secret.  Both fixed without removing the brief's original variables
    (kept as dead weight per minimum-change posture).
11. **Kept `ENV`, `JWT_SECRET_KEY`, `SECRET_KEY` despite OCERP not reading
    them.**  Brief listed them; possibly used elsewhere (Phase 7.7 auth
    setup, monitoring tools).  Removing now risks breaking some future
    consumer.

---

## 15. Phase 7.3 checklist

| Sub-phase | Status |
|---|---|
| 7.3.1 — Production Dockerfile + entrypoint built and verified | ✅ |
| 7.3.2 — Railway project + Postgres + Redis + backend service provisioned | ✅ |
| 7.3.3 — 11 env vars set via Railway references + cryptographic secrets | ✅ |
| 7.3.4 — `railway up` deploy from `feature/nexus-precon-module` branch | ✅ (after entrypoint refactor) |
| 7.3.5 — Migration verified on prod Postgres (5 tables + alembic stamp) | ✅ |
| 7.3.6 — Public backend responds (`/api/health` 200, `/api/precon/...` 401) | ✅ |
| 7.3.7 — `PHASE_7_3_REPORT.md` (this file) | ✅ |
| Env-var name mismatch fix (`APP_ENV`, `JWT_SECRET`) | ✅ |
| `IF NOT EXISTS` convention documented | ✅ §10 |
| Cost estimate | ✅ §13 |
| Items flagged for Bill | ✅ §12 |

**Phase 7.3 is COMPLETE.**  Standing by for review before authorising Phase 7.4
(GovTribe MCP service + flip `GOVTRIBE_MCP_ENABLED=true`).

---

## 16. GovTribe Integration Deferred (Phase 7.4 closeout — Path D)

After Phase 7.3 backend went live, a focused 7.4.0 reconnaissance pass on the
GovTribe MCP integration surfaced enough mismatches between our Step 6.1 code
and the real upstream that Bill chose **Path D — defer live integration to
Step 8** rather than try to wire it live tonight.  Soft-launch ships with
`GOVTRIBE_MCP_ENABLED=false` and federal-opportunity intake disabled.

### 16.1 Recon findings (verbatim)

1. **Custom HTTP transport, not standard MCP-over-HTTP/JSON-RPC.**
   `govtribe_mcp_client.py` line 245-253 hand-rolls an HTTP shim that POSTs
   to `{GOVTRIBE_MCP_URL}/tools/{tool_name}` with a `{"params": {...}}` body
   and no auth headers.  The real `https://govtribe.com/mcp` SaaS connector
   speaks Anthropic's MCP-over-HTTP / Streamable HTTP / SSE protocol with
   JSON-RPC 2.0 framing — `POST /messages` (or `GET /sse`) with bodies
   shaped `{"jsonrpc": "2.0", "method": "tools/call", "params": {...}}`.
   Our requests would be rejected as 404/400 even with auth.

2. **Code reads `GOVTRIBE_MCP_URL` and `GOVTRIBE_MCP_COMMAND`, NOT
   `GOVTRIBE_API_KEY`.**
   The exhaustive set of env vars our precon code reads:

   | Env var | Read by | Purpose |
   |---|---|---|
   | `GOVTRIBE_MCP_ENABLED` | `mcp_client.py:55` | enable / disable gate |
   | `GOVTRIBE_MCP_COMMAND` | `mcp_client.py:220` | stdio MCP subprocess command |
   | `GOVTRIBE_MCP_URL` | `mcp_client.py:237` | HTTP shim base URL |
   | `GOVTRIBE_SYNC_PAGE_SIZE` | `tasks/govtribe_sync.py:34` | sync batch size |
   | `GOVTRIBE_ALERT_EMAIL` | `tasks/heartbeat.py` | stale-sync alert recipient |

   Bill set `GOVTRIBE_API_KEY` on Railway expecting it to be picked up
   automatically — it isn't.  No code path in the precon module (or
   anywhere else in OCERP, per grep) consumes it.

3. **Zero auth headers in current implementation.**
   The HTTP shim sends no `Authorization`, `X-API-Key`, or `Bearer`
   header.  Even if the var name matched, the request would land at
   `govtribe.com/mcp` unauthenticated and be rejected.

4. **Decision: Path D — defer to Step 8.**
   Soft-launch ships now with `GOVTRIBE_MCP_ENABLED=false`.  No live
   federal-opportunity intake; the precon dashboard shows an empty
   pipeline with the "GovTribe Sync · Stale" indicator until Step 8.
   Frontend, backend, auth, and 5 precon tables all live.

5. **Step 8 plan: rewrite to call SAM.gov public API.**
   Roughly 90 minutes of focused work.  SAM.gov publishes federal
   contract opportunities at `https://api.sam.gov/opportunities/v2/search`
   with no API key required for read access (rate-limited).  Replacing
   GovTribe MCP entirely with SAM.gov:
   * removes the auth complexity (no key, no MCP handshake)
   * removes the third-party SaaS dependency (governmental-authority
     source instead)
   * keeps our Amendment A2 schema mostly compatible (SAM.gov fields map
     cleanly to `solicitation_number`, `name`, `due_date`, `naics_code`,
     `place_of_performance`, etc.)
   The rewrite would replace `govtribe_mcp_client.py` with `sam_gov_client.py`
   and re-target `govtribe_sync.py` (renamed `opportunity_sync.py`) at the
   new client.  Adapter layer (`govtribe_adapter.py`) and Amendment A2
   schema stay unchanged.

6. **Variable preservation: `GOVTRIBE_API_KEY` stays on Railway.**
   Kept as a placeholder reference for now.  Will be removed at the start
   of Step 8 when SAM.gov replaces GovTribe entirely.  Same minimum-change
   posture used for the other dead-weight vars (`ENV`, `JWT_SECRET_KEY`,
   `SECRET_KEY`).

7. **Sync task behaviour when disabled (verified live in production).**
   `govtribe_sync.py` lines 68-72:
   ```python
   client = mcp_client if mcp_client is not None else get_default_mcp_client()
   if isinstance(client, DisabledGovTribeMCPClient) or not is_govtribe_enabled():
       message = "GovTribe MCP integration disabled (GOVTRIBE_MCP_ENABLED=false)"
       logger.info(message)
       return _result(status="disabled", fetched=0, cached=0, errors=0, message=message)
   ```
   Returns `{"status":"disabled","fetched":0,"cached":0,"errors":0,...}`
   cleanly.  No exception, no retry storm.  Heartbeat task in turn sees
   `last_synced_at = NULL` (nothing has ever synced) and the freshness
   check returns `status="ok"` rather than `"stale"` — so no alert spam.

### 16.2 Production state at end of Phase 7.4

| Var | Value | Effect |
|---|---|---|
| `GOVTRIBE_MCP_ENABLED` | `false` | Sync task short-circuits to `disabled` |
| `GOVTRIBE_API_KEY` | (1069-char preserved) | Dead var; held for Step 8 cleanup |
| `GOVTRIBE_ALERT_EMAIL` | `bill@oneillcontractors.com` | Used only when stale-sync alerts fire (won't, while disabled) |

Backend is healthy, `GET /api/health` returns 200, `GET /api/precon/health/heartbeat/`
returns 401.  Federal opportunity intake is the only deferred capability;
everything else (pipeline, RFQ, bid leveling, prequal, Award & Activate)
operates as designed.
