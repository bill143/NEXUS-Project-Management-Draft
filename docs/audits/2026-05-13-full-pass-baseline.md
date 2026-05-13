# NEXUS — Full-Pass Baseline (2026-05-13)

**Goal**: ground-truth measurement before a guided fix pass. No code changes made. All numbers reproducible from this environment.

**Scope**: backend + frontend + desktop + deploy. Marketing site skipped per agreement.

**Branch**: `claude/add-npx-skills-command-HDMg3` (no commits made in this batch — read-only baseline).

---

## TL;DR

| Stack | Health | Notes |
|-------|--------|-------|
| Backend lint (ruff) | 166 errors (137 auto-fixable) | Almost all import-order / unused-import in tests |
| Backend types (mypy `strict=true`) | 1830 errors / 276 files | Mostly missing annotations + unparameterized `dict`; ~10 real null-deref bugs mixed in |
| Backend pytest collection | 3454 tests collected, 2 collection errors | Missing deps: `langgraph`, `jsonschema` |
| Backend unit tests | 2719 pass / 1 fail / 2 skip (99.96%) | One bug: `test_default_role_is_editor` (test/code drift) |
| Backend integration tests | NOT EVALUATED | No Docker daemon in this sandbox |
| Alembic topology | 1 head — clean | (Prior filesystem scan reported 4 heads — false positive; merge migrations resolve them) |
| Alembic schema drift (sqlite) | 38 drift events | 21 added indexes, 6 removed indexes, 8 added FKs, 3 column drifts |
| App boot | PASS (50 routes registered) | Notable: 50 routes at create_app vs 96 frontend routes — gap |
| Frontend install (pnpm) | PASS | Build-script warnings (core-js, esbuild, msw); not blocking |
| Frontend eslint | **BROKEN under pnpm** | `eslint.config.js` imports `@eslint/js` but it's not declared in `package.json` |
| Frontend tsc -b | PASS | Clean — no TS errors |
| Frontend vite build | PASS (3m 1s) | 8 chunks > 500 KB, biggest: `VisualBimPage` 4.87 MB, `i18n-data` 4.74 MB |
| Frontend vitest | 1511 pass / 69 fail / 24 skip (94.2%) | 18 of 111 files fail; mix of label drift + 6 snapshot failures + 1 obsolete |
| Frontend e2e (Playwright) | NOT EVALUATED | Browser deps + time |
| Desktop (Tauri) | NOT EVALUATED | `cargo check` deferred to Batch 18 |
| Deploy YAML | 2/3 valid | `docker-compose.quickstart.yml` line 34 has unquoted `${VAR:?…}` with a `:` in the error message — strict YAML rejects, Docker Compose may be lenient |
| Docker daemon | UNAVAILABLE | Sandbox limitation, not a code issue |

---

## 1. Environment & toolchain

Available: `python3.12` and `3.13`, `node 22.22.2`, `pnpm 10.33.0`, `cargo 1.94.1`, `uv 0.8.17`, `docker 29.3.1` (binary only, daemon won't start — no systemd).

Installed for the baseline:
- Backend: `uv venv --python 3.12 backend/.venv` + `uv pip install -e ".[server,dev]"` (after workaround, see §2)
- Frontend: `pnpm install` (27 s)

Not installed: Rust crates for Tauri, Playwright browsers, optional `[vector]`/`[semantic]`/`[cv]` extras.

---

## 2. Install-time bugs

### 2.1 — Backend editable install fails on fresh clone (chicken-and-egg)

`backend/pyproject.toml` declares:

```toml
[tool.hatch.build.targets.wheel.force-include]
"../frontend/dist" = "app/_frontend_dist"
```

…but `frontend/dist` doesn't exist until `npm run build` is run inside `frontend/`. Running `make setup` (which does `pip install -e .[server]` for the backend first) fails with:

```
FileNotFoundError: Forced include not found: …/frontend/dist
```

**Fix candidates** (decide in Batch 3):
- Skip force-include in editable installs (hatch supports `[tool.hatch.build.targets.wheel]` per-target conditionals).
- `Makefile`: reorder `setup` to build the frontend before backend install.
- Document the order in `README.md`.

Workaround used for this baseline: `mkdir -p frontend/dist && touch frontend/dist/.placeholder`, then install. Frontend was subsequently built and overwrote the placeholder.

### 2.2 — Backend has undeclared transitive runtime deps

Two `ModuleNotFoundError`s during `pytest --collect-only`:

| Missing | Importer | Why it matters |
|---------|----------|----------------|
| `langgraph` | `app/pipelines/text_to_cost_estimate/graph.py` | `app/pipelines/__init__.py` *eagerly* re-imports this — so **any `from app.pipelines import …` blows up on a fresh install** |
| `jsonschema` | `tests/unit/eac/test_schema_jsonschema.py` | Test-only; needs to be in `[dev]` extras |

**Fix** (Batch 9 / EAC): add `langgraph` to `[project.dependencies]` (or make the import lazy in `app/pipelines/__init__.py`), and add `jsonschema` to `[project.optional-dependencies].dev`.

### 2.3 — Frontend `eslint.config.js` is incompatible with pnpm

```js
// frontend/eslint.config.js line 15
import js from '@eslint/js';
```

`@eslint/js` is a peer/transitive of `eslint`. npm hoists it; pnpm doesn't. `pnpm exec eslint .` therefore fails with `ERR_MODULE_NOT_FOUND` — but pnpm's wrapper exit-coded 0, so this silently hides the failure.

**Fix** (Batch 12): add `"@eslint/js": "^9.x"` to `frontend/package.json` devDependencies.

---

## 3. Backend findings

### 3.1 — `ruff check`: 166 errors, 137 auto-fixable

Sample categories (from a 100-line tail — partial):
- `I001` import-block unsorted/unformatted
- `F401` unused imports
- `PT018` compound assertion
- A handful of test-file violations: `tests/unit/test_schedule.py`, `test_schedule_xxe.py`, `test_submittals.py`, `test_sarif_exporter.py`

`ruff format --check` not measured separately (line length is 120 per `pyproject.toml`; ruff format runs same engine).

**Fix path**: `ruff check --fix app/ tests/` clears 137 automatically. Hand-fix the remaining 29 (mostly PT018 assertion splits).

### 3.2 — `mypy app/` (strict=true): 1830 errors in 276 of 813 source files

Most are mechanical:
- `type-arg` — bare `dict`, `list`, `tuple` without parameters
- `no-untyped-def` — missing function/parameter annotations
- `unused-ignore` — `# type: ignore` directives that no longer match

Real bugs to investigate (not all "missing annotation"):
- `app/main.py:605` — `User | None` accessed for `.id` without null check, plus a `where(...)` bool/Any incompatibility
- `app/core/match_service/extractors/bim.py:89,96,99,102,133` — Optional `dict | None` indexed without check; `_auto_classifier_hint` called with `None`-tainted arg
- `app/core/match_service/extractors/photo.py:60` — `float(Any | None)` 
- `app/core/match_service/extractors/pdf.py:60,75,80` — same pattern as photo.py
- `app/main.py:1183` — `Set[object]` where `Set[str]` expected

Recommend: in Batch 3, audit the ~30-ish real-bug findings; treat the rest as Batch-X "type-tightening" work after fixes land.

### 3.3 — `pytest --collect-only`: 3454 tests, 2 collection errors

Collection errors block 2 test files (see §2.2). All other 3454 tests collected cleanly.

### 3.4 — `pytest tests/unit/`: 2719 pass / 1 fail / 2 skip in 36 s

The single failure:

```
FAILED tests/unit/test_users.py::TestUserCreateSchema::test_default_role_is_editor
AssertionError: assert 'viewer' == 'editor'
```

Test expects default role `'editor'`, code returns `'viewer'`. Almost certainly drift from commit `4bd83bb chore(users): document bootstrap-admin policy; add canonical 'editor' to AdminUserCreate role Literal`.

**Fix path**: either update the test to assert `'viewer'` (if viewer is intentional default) or change the default in `UserCreate` schema. Decide in Batch 4 (auth/users).

### 3.5 — Integration / perf / eval tests: NOT RUN

`tests/integration/` (76 files), `tests/perf/` (2 files), `tests/eval/` (1 file): all need live Postgres/Redis/MinIO. Skipped because no Docker daemon. Will need a separate baseline pass in a Docker-capable environment.

### 3.6 — Pytest marker problem

`pyproject.toml` declares three markers (`unit`, `integration`, `slow`), but the repo uses **directory-based test organisation** (`tests/unit/`, `tests/integration/`) rather than decorators. Only one `@pytest.mark.slow` exists in the whole repo and zero `@pytest.mark.unit` / `@pytest.mark.integration`.

This means **`make test-unit` (which runs `pytest -m unit`) selects 0 tests** — the Makefile target is broken. Same for `make test-integration`.

**Fix path** (Batch 3): either auto-mark by path in `tests/conftest.py` via `pytest_collection_modifyitems`, or change the Makefile to use path-based selection (`pytest tests/unit/` / `pytest tests/integration/`).

### 3.7 — Alembic state

- **Migrations**: 45 version files, **1 head** (`v2i0_null_not_distinct`). The `v2h0_merge_heads` migration explicitly merges what was previously branched.
- **Schema drift** (after `alembic upgrade head` against SQLite, then `alembic check`): 38 drift events.

| Drift kind | Count |
|---|---|
| Added index (in models, not in migrations) | 21 |
| Removed index (in migrations, not in models) | 6 |
| Added FK (in models, not in migrations) | 8 |
| Added column | 2 |
| Removed column | 1 |
| **Total** | **38** |

The prior 2026-05-09 QA report flagged "29 orphan tables, 140 index drifts, 3 column drifts" — likely measured against Postgres with the `pgduckdb` image, which has different index semantics. Numbers differ from this baseline but the *kind* of problem (model/migration drift) matches.

Two patterns stand out:
- **Double-named indexes**: many indexes appear in both `ix_xxx` and `ix_oe_xxx` form (e.g., `ix_oe_tendering_package_status` and `ix_tendering_package_status`). Suggests inconsistent naming convention across models and explicit `Index()` declarations.
- **Status columns without backing indexes**: many `status` columns (rfi, rfq, safety_incident, transmittal, submittal, punchlist, etc.) want indexes that the migrations don't provide.

Defer to Batch 5 (Alembic migrations).

### 3.8 — App boots, but route count is suspicious

`app.main.create_app()` succeeds and registers **50 routes** at startup. Frontend declares **96 routes** in `App.tsx`. The 46-route gap is likely a mix of:
- Conditionally-mounted routers (the `try:` blocks in `main.py:1576-1615` for OpenCDE / Variations / EVM / Schedules v2 — wrapped in feature flags)
- Routes auto-mounted by the module-loader at lifespan-startup (after `create_app()` returns)

Defer to Batch 3 (foundation / module loader) — confirm whether every frontend route has a backend partner.

### 3.9 — 32 backend modules have `router.py` but aren't directly imported in `main.py`

Inventory:

```
admin, architecture_map, asia_pac_pack, backup, compliance, compliance_ai,
cost_match, dach_pack, dashboards, ddc_pdf_excel, ddc_profiling, ddc_qto,
ddc_revit_export, eac, hello_world, india_pack, jobs, latam_pack, match,
middle_east_pack, ml_price_prediction, my_module, project_intelligence,
russia_pack, search, sustainability, uk_pack, uploads, us_pack, viewer3d,
visualbim
```

`main.py` has 88 `from app.modules.*` imports but only 14 `app.include_router` calls — suggests most are mounted dynamically. Could include dead code; needs case-by-case verification in module batches.

### 3.10 — Module convention: 1 module without `manifest.py`

`backend/app/modules/precon` lacks the `manifest.py` that CLAUDE.md prescribes. Every other module has one. Either precon is special-case (it lives behind `/api/precon` prefix per the test) or the convention drifted.

---

## 4. Frontend findings

### 4.1 — TypeScript: PASS

`tsc -b` (the strict project-references build) completes cleanly — no `TS####` errors anywhere. `noUnusedLocals: true` is honored.

### 4.2 — `vite build`: PASS (3m 1s)

`dist/` produces 199 chunks, total transferred size in line with previous QA report. **Bundle warnings (chunks >500 KB)**:

| Chunk | Raw | gzip |
|---|---:|---:|
| `VisualBimPage` | 4.87 MB | 1.48 MB |
| `i18n-data` | 4.74 MB | 1.23 MB |
| main `index` | 2.42 MB | 602 KB |
| `maplibre-gl` | 1.06 MB | 285 KB |
| `o3dv.module` | 1.05 MB | 281 KB |
| `vendor-exceljs` | 940 KB | 271 KB |
| `vendor-ag-grid` | 896 KB | 234 KB |
| `vendor-charts` | 630 KB | 189 KB |

`VisualBimPage` and `i18n-data` are the two genuine outliers. The vendor chunks are unavoidable without finer code-splitting. Track in Batch 14 (CAD/BIM) and Batch 12 (app shell — i18n).

### 4.3 — `vitest run`: 69 failed / 1511 passed / 24 skipped (1604 total)

18 of 111 test files fail. Sample failure (`ConflictResolutionPanel.test.tsx:296`):

```
expect(screen.getByText('Your version')).toBeInTheDocument();
```

…but rendered output has "Manual merge..." instead. Looks like label drift from a recent component refactor.

Other categories likely present (not yet itemised):
- 6 snapshot failures (`src/tests/visual-regression.test.tsx`)
- 1 obsolete snapshot
- Label/i18n drift on multiple component tests

Full breakdown deferred to per-batch frontend audits (12-17).

### 4.4 — Routes vs nav drift (carry-over from 2026-05-09 QA)

The prior QA report flagged 96 routes vs only ~3 visible nav targets in `Sidebar.tsx`. The most recent commit `c641ead feat(layout): consolidate scattered nav items into top-nav Settings gear menu` suggests nav has since been refactored. Re-verify in Batch 12 (frontend app shell).

### 4.5 — `i18n-fallbacks.ts` is 5.45 MB

`frontend/src/app/i18n-fallbacks.ts` is 5,450,594 bytes — an auto-generated translation blob. It's already in `eslint.config.js`'s ignore list (line 107: `'src/app/i18n.ts'` — note: this is the wrong filename; the actual huge file is `i18n-fallbacks.ts`). 

**Minor ESLint config bug**: ignore pattern points at `src/app/i18n.ts` (1.4 KB) but the multi-megabyte file is `src/app/i18n-fallbacks.ts`. If `i18n.ts` is regenerated as big, it'll lint; the file actually causing lint pain isn't ignored.

---

## 5. Desktop findings

Not measured (Batch 18). Light static read:
- `desktop/src-tauri/Cargo.toml` package name is `openestimate-desktop` and description `"OpenEstimate Desktop — Construction Cost Estimation"` — **branding drift** vs. NEXUS rebrand
- Tauri v2, `tauri-plugin-{shell,updater,process}` plugins
- Sidecar architecture: `build-sidecar.sh` + `pyinstaller.spec` packages the Python backend as a sidecar binary

---

## 6. Deploy findings

### 6.1 — `docker-compose.quickstart.yml` line 34: strict-YAML invalid

```yaml
POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:?POSTGRES_PASSWORD must be set — generate with: openssl rand -base64 24}
```

The unquoted value contains `: ` inside the `:?error_msg` part. Strict YAML parsers (PyYAML) reject this. Docker Compose's parser may be lenient enough to accept it, but it's fragile and tooling-hostile.

**Fix** (Batch 19): wrap the value in quotes:

```yaml
POSTGRES_PASSWORD: "${POSTGRES_PASSWORD:?POSTGRES_PASSWORD must be set — generate with: openssl rand -base64 24}"
```

Other compose files (`docker-compose.yml`, `docker-compose.prod.yml`) parse cleanly.

### 6.2 — Dockerfiles: structural sanity OK

4 Dockerfiles (`./Dockerfile`, `deploy/docker/Dockerfile.{backend,frontend,unified}`). Line counts modest (28-109 lines), no obvious red flags (`:latest`, `curl … | sh`, `sudo`, etc.). Real audit deferred to Batch 19.

### 6.3 — `.env.example` files: no real secrets

| File | Status |
|---|---|
| `.env.example` | Placeholder values (`minioadmin`, `change-me-in-production`) — fine |
| `backend/.env.example` | Same |
| `deploy/docker/.env.example` | Same (`CHANGE_ME_TO_A_RANDOM_64_CHAR_STRING`) |

Search for hardcoded secrets in source: only **demo credentials** explicitly labelled `DEMO_HASH_NOT_FOR_PRODUCTION_USE_ONLY` (`backend/app/core/demo_projects.py:1993`, `backend/app/scripts/seed_demo_estimates.py:641`) and the well-known demo login (`demo@openestimator.io / DemoPass1234!`) in `backend/app/cli.py`. No actual leaks.

---

## 7. Code-rot signals (low priority, informational)

### 7.1 — Marker counts

| Marker | Backend `app/` + Frontend `src/` + `desktop/src-tauri/src/` |
|--------|------:|
| TODO | 7 |
| FIXME | 0 |
| HACK | 0 |
| XXX | 4 |
| BUG: | 0 |
| NOTE | 21 |
| WORKAROUND | 0 |
| DEPRECATED | 0 |

Extremely low — this codebase is well-curated by marker count.

### 7.2 — Largest files (possible rot or just legitimately large)

Backend (top 5):
1. `backend/app/core/demo_projects.py` — 322 KB
2. `backend/app/modules/boq/router.py` — 227 KB
3. `backend/app/modules/boq/service.py` — 194 KB
4. `backend/app/core/i18n.py` — 142 KB
5. `backend/app/modules/bim_hub/router.py` — 137 KB

Frontend (top 5):
1. `frontend/src/app/i18n-fallbacks.ts` — 5.45 MB (generated)
2. `frontend/src/modules/pdf-takeoff/TakeoffViewerModule.tsx` — 203 KB
3. `frontend/src/features/dwg-takeoff/DwgTakeoffPage.tsx` — 202 KB
4. `frontend/src/features/boq/grid/cellRenderers.tsx` — 198 KB
5. `frontend/src/features/cad-explorer/CadDataExplorerPage.tsx` — 181 KB

`demo_projects.py` and `i18n-fallbacks.ts` are generated/seed and probably fine. The 200KB+ TSX page components are worth at least an eyes-on pass during their respective batches.

### 7.3 — Pytest skip/xfail markers

5 `@pytest.mark.skip`/`xfail` decorators in the test suite. Plus the 2 skipped tests recorded by the unit run.

---

## 8. What this baseline did NOT measure

| Item | Why | Where addressed |
|---|---|---|
| `cargo check` on Tauri | Heavy crate fetch deferred | Batch 18 |
| Backend integration tests (76 files) | No Docker daemon for Postgres/Redis/MinIO | Run in Docker-capable env before Batches 3-11 land |
| Backend perf + eval tests | Same | Defer |
| Playwright e2e (51 specs) | Browser deps + slow | Batches 12-17 (manual sample, full run after) |
| `terraform validate` | Terraform not installed | Batch 19 |
| Bundle deep analysis (`rollup-plugin-visualizer`) | Not run | Batch 14 (BIM) + Batch 12 (i18n) |
| Pre-commit hook health | Not run | Batch 19 or 3 |
| GitHub Actions workflow status | `.github/workflows/` not inspected | Batch 19 |
| Live RBAC matrix probe (per 2026-05-09 QA) | Needs running app | Batch 4 |

---

## 9. Recommendation: re-ordered batch priorities

Based on baseline data, the proposed batch order from the todos still holds, but priorities within batches shift:

1. **Batch 2 (CLAUDE.md rewrite)** — straightforward, no dependencies. Do first.
2. **Batch 3 (backend foundation)** — covers the eager-pipelines import bug (§2.2), the broken `make test-unit` marker problem (§3.6), the routes-vs-nav gap (§3.8), the 32-unmounted-routers question (§3.9), and the install-order force-include bug (§2.1).
3. **Batch 5 (Alembic)** — schema drift (§3.7) is real and growing.
4. **Batch 4 (security)** — the `test_default_role_is_editor` failure (§3.4) lives here, plus the real null-deref bugs in `match_service/extractors/*.py` (§3.2).
5. **Batches 6-11 (backend modules)** — most issues here are type-tightening + module-specific cleanup.
6. **Batch 12 (frontend app shell)** — fixes ESLint (§2.3), `i18n-fallbacks.ts` ignore pattern (§4.5), nav drift (§4.4).
7. **Batches 13-17 (frontend features)** — 69 vitest failures distributed here.
8. **Batch 18 (desktop)** — branding rename, then `cargo check`.
9. **Batch 19 (deploy)** — quickstart YAML fix (§6.1), Dockerfile audit, CI sanity.
10. **Batch 20 (root docs)** — strictly last; cleanup only.

---

## 10. Reproducibility

Commands run (in order), all from repo root unless noted:

```bash
# Toolchain check
python3.12 --version; node --version; pnpm --version; cargo --version

# Backend install (note: requires frontend/dist to exist)
mkdir -p frontend/dist && touch frontend/dist/.placeholder
cd backend && uv venv --python 3.12 .venv \
  && VIRTUAL_ENV=$PWD/.venv uv pip install -e ".[server,dev]"

# Frontend install
cd frontend && pnpm install

# Lint
cd backend && .venv/bin/ruff check app/ tests/        # 166 errors
cd frontend && pnpm exec eslint .                      # broken: missing @eslint/js

# Types
cd backend && .venv/bin/python -m mypy app/            # 1830 errors
cd frontend && pnpm exec tsc -b                        # PASS

# Tests
cd backend && .venv/bin/python -m pytest --collect-only -q     # 3454 / 2 collection errors
cd backend && .venv/bin/python -m pytest tests/unit/ -q \
  --ignore=tests/unit/eac/test_schema_jsonschema.py             # 2719 / 1 / 2
cd frontend && pnpm exec vitest run                              # 1511 / 69 / 24

# Build
cd frontend && npm run build                            # 3m 1s, PASS

# App boot
cd backend && .venv/bin/python -c "from app.main import create_app; create_app()"  # 50 routes

# Alembic
cd backend && .venv/bin/alembic heads                  # 1 head
DATABASE_URL=sqlite+aiosqlite:////tmp/oe_baseline.db \
DATABASE_SYNC_URL=sqlite:////tmp/oe_baseline.db \
  .venv/bin/alembic upgrade head
DATABASE_URL=... DATABASE_SYNC_URL=... .venv/bin/alembic check   # 38 drift events
```

---

*Baseline complete. No code changes were made in this batch.*
