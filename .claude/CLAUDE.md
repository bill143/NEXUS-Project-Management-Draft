# CLAUDE.md — NEXUS

## Project identity

**NEXUS** is the open-source modular platform for construction cost estimation and project management — the federal-pivot fork of OpenEstimate that consolidates DDC tooling (CO₂ embodied carbon, ML price prediction, federal-compliance helpers). Branding was changed from `OpenConstructionERP` (and the older `OpenEstimate` lineage) in commit `bc0222e` (2026-04). Some artefacts still carry the old name — see "Known branding drift" below.

- License: **AGPL-3.0-or-later** (community) + Commercial (enterprise).
- Maintainer / founder: Artem (10+ years construction estimating, author of CWICR / cad2db / DDC).
- Current package versions: backend `2.8.8` (`backend/pyproject.toml`), frontend `2.8.8` (`frontend/package.json`). **The in-app changelog (`frontend/src/features/about/Changelog.tsx`) is stuck at `2.5.0` — that's a known drift caught by `scripts/check_version_sync.py`.**

---

## Reality check (2026-05-13)

This file used to describe a Phase-0 greenfield project. The repo is far past that. As of this rewrite:

- **91 backend modules** under `backend/app/modules/` (not the ~10 the old doc listed)
- **58 frontend feature directories** under `frontend/src/features/` + **41 frontend module directories** under `frontend/src/modules/`
- **45 Alembic migrations**, currently converging to a single head (`v2i0_null_not_distinct`) via the explicit `v2h0_merge_heads` merge
- A working Tauri desktop app under `desktop/` (sidecar architecture; package name still says `openestimate-desktop` — branding drift)
- A working Vite/React frontend that builds cleanly (`vite build` ≈ 3 min) and a FastAPI backend that boots cleanly against SQLite
- 51 Playwright e2e specs, 243 backend test files (3454 collectible tests), 111 frontend test files (1604 vitest tests)

So the development phase is not "Foundation — 2 weeks." It's "established product with active feature work and known tech debt." See `docs/audits/2026-05-13-full-pass-baseline.md` for the most recent measured state.

The architectural principles below are still the project's North Star. Where the code currently disagrees with a principle, the disagreement is called out inline.

---

## Principles (PR-blocking when violated)

1. **LIGHTWEIGHT & SIMPLE** — minimal dependencies, fast start (`make quickstart` or `pip install nexus`). Core boots against SQLite with no external services. *Reality note*: the frontend bundle is heavyweight (8 chunks > 500 KB; `VisualBimPage` at 4.87 MB, `i18n-data` at 4.74 MB) — those are tracked for code-splitting work. The "VPS with 2GB RAM" target is realistic for SQLite-only mode; the full Postgres/Redis/MinIO/Qdrant compose stack wants more.
2. **i18n EVERYWHERE** — 20 languages baked into the core. All UI strings, validation messages, cost-database labels go through i18n. New language = JSON file. Zero hardcoded strings. *Reality note*: the auto-generated `frontend/src/app/i18n-fallbacks.ts` is 5.45 MB; the ESLint ignore in `eslint.config.js` points at the wrong filename (`src/app/i18n.ts`). Fix tracked.
3. **CAD-agnostic through conversion** — we do **NOT** use IfcOpenShell or native IFC parsing. All CAD formats (DWG, DGN, RVT, IFC) flow through the DDC cad2data pipeline into our canonical format. **BCF is allowed** as an I/O format (issues / validation reports / viewpoints) because it's XML over data with no IfcOpenShell runtime dependency. Decision last reviewed 2026-04-26.
4. **Data validation as a first-class citizen** — every import passes a validation pipeline with configurable rule sets (DIN, NRM, MasterFormat, custom). Validation is **NOT** optional — it's part of the core workflow.
5. **Modules = plugins** — download, drop into a directory, restart, it works. Each module has a `manifest.py`. Marketplace for discovery and install. *Reality note*: 90 of 91 backend modules ship `manifest.py`; only `precon` is missing one and is special-cased.
6. **Open data standards** — GAEB XML 3.3, DIN 276, NRM, MasterFormat are natively supported. Proprietary formats go through modules.
7. **AI-augmented, human-confirmed** — AI proposes, the human confirms. Confidence scores. No auto-actions without review.
8. **SQLite-first** — SQLite is the default backend storage (it's in `backend/pyproject.toml` base deps as `aiosqlite`). PostgreSQL + Redis + MinIO + Celery are **optional** server extras (`pip install nexus[server]`). The Makefile's `make infra` brings them up via `docker compose` for production-shape dev work.

---

## Stack (as actually installed)

| Layer | Tech | Notes |
|-------|------|-------|
| Backend API | **Python 3.12+ / FastAPI** | `backend/pyproject.toml` requires `python>=3.12`. Pydantic v2, async SQLAlchemy. |
| Database (default) | **SQLite via aiosqlite** | Base dep. App boots with no external service. |
| Database (server) | **PostgreSQL 16+** (`pgduckdb/pgduckdb:16-main`) | Optional, via `[server]` extras: asyncpg + psycopg2-binary. Docker image bundles DuckDB FDW for OLAP. |
| Background jobs | **Celery + Redis** | Optional, via `[server]` extras. In-process job runner is the dev default. |
| Object storage | **MinIO** (S3-compatible) | Optional, via `[s3]` extras (aioboto3). Local filesystem otherwise. |
| Vector search | **Qdrant** (server) / **LanceDB** (embedded) | Optional, via `[semantic]` / `[vector]` extras. |
| CV / OCR | **PaddleOCR + Ultralytics YOLO** | Optional, via `[cv]` extras. PDF takeoff + symbol detection. |
| LLM access | **direct HTTP via `httpx`** | **No vendor SDKs in deps** — `app/modules/ai/ai_client.py` talks to provider REST APIs directly to avoid 800 MB of dead wheels. Keys live in the DB + `~/.openestimate/config.json`. |
| Email | **Resend HTTP API** + SMTP fallback | `resend>=2.0` is a base dep because Railway and most PaaS hosts block outbound SMTP. Backend selection in `app/core/email/`. |
| CAD conversion | **DDC cad2data** pipeline | `backend/data/ddc_templates/` + `services/cad-converter/`. **Not IfcOpenShell.** |
| Frontend | **React 18 / TypeScript 5.9 / Vite 6** | AG Grid Community (BOQ), Three.js + online-3d-viewer (BIM), pdf.js (takeoff), Yjs + y-webrtc + y-websocket (collab). MapLibre + Leaflet for geo. |
| Frontend state | **Zustand** (global) + **React Query** (server state) | 24 Zustand stores in `frontend/src/stores/`. |
| Frontend styling | **Tailwind 3** + CSS variables | PostCSS + Autoprefixer. |
| Desktop | **Tauri 2** + PyInstaller sidecar | `desktop/src-tauri/` (Rust shell) + `desktop/pyinstaller.spec` (Python sidecar). |

---

## Code conventions

### Python (backend)

- Formatter / linter: **ruff** (line-length **120**, not the 100 the old doc claimed)
- `[tool.ruff.lint] select`: `E, F, W, I, N, UP, B, A, C4, PT, RET, SIM` — **no `ANN` / `COM` / `ARG`** (FastAPI DI patterns conflict with strict arg checking)
- Long list of `ignore` entries — see `backend/pyproject.toml`. Don't add new ignores without justification in the same commit.
- Type hints: present in most public APIs; **mypy is configured `strict = true` but currently reports 1830 errors across 276 of 813 files**. Treat mypy as an aspirational guardrail today, not a merge gate. Some of those 1830 are real null-deref bugs; they get fixed in the relevant module's batch.
- Docstrings: prevalent on modules and public functions; no enforced style yet.
- Tests: **pytest**. 243 files, ~3454 tests. Tests are organised by **directory** (`tests/unit/`, `tests/integration/`, `tests/perf/`, `tests/eval/`), not by `@pytest.mark.unit` decorators — only 1 `@pytest.mark.slow` exists in the whole repo. The Makefile targets `make test-unit` / `make test-integration` currently use `pytest -m …` and therefore select 0 tests — known bug, fix tracked.
- Async: `async def` on all FastAPI handlers. Sync allowed in domain logic when there's no I/O.
- Imports: absolute, grouped stdlib → third-party → local, isort-managed via ruff `I`.

### TypeScript (frontend)

- `tsconfig`: strict mode on. `noUnusedLocals: true` is honoured (build catches violations).
- Formatter: **Prettier** (printWidth=100, singleQuote=true, via `npm run format`)
- Linter: **ESLint 9 flat config** in `frontend/eslint.config.js`. *Reality note*: the config imports `@eslint/js` but doesn't declare it in `package.json`; works under `npm` (hoists transitives) but fails under `pnpm`. Fix tracked.
- State: **Zustand** for global state, **React Query** for server state.
- Styling: **Tailwind** + CSS variables for theming.
- Components: functional only, named exports, co-located tests (`Component.tsx` + `Component.test.tsx`).
- API client: auto-generated from OpenAPI via `npm run api:generate` (`src/shared/lib/api-types.ts`).

### Universal

- Commits: **Conventional Commits** (`feat:`, `fix:`, `refactor:`, `docs:`, `test:`, `chore:`).
- Branch naming (current repo practice): `feat/short-description`, `fix/short-description`, `docs/short-description`, `audit/YYYY-MM-DD-description`. (The old "OE-123" Jira-prefix convention from the previous CLAUDE.md is not used in current commit history.)
- PR: prefer **squash merge**, linked issue or audit reference, at least 1 review.
- All code, comments, and docs are written in **English**. README has multiple-language sections; user-facing docs may add DE / RU.

---

## Monorepo layout (actual)

```
NEXUS-Project-Management-Draft/
├── .claude/CLAUDE.md          # ← you are here
├── LICENSE                    # AGPL-3.0
├── README.md
├── CHANGELOG.md               # 273 KB — large history; release-please managed
├── Makefile
├── docker-compose.yml         # Dev stack: postgres + redis + minio + qdrant + worker
├── docker-compose.prod.yml
├── docker-compose.quickstart.yml   # Single-command launch
├── Dockerfile, docker-entrypoint.sh
├── pyproject.toml             # Root-level for tooling only (real package is backend/)
│
├── backend/                   # FastAPI application
│   ├── pyproject.toml         # The Python package "nexus" v2.8.8
│   ├── alembic.ini
│   ├── alembic/versions/      # 45 migration files, head v2i0_null_not_distinct
│   ├── app/
│   │   ├── main.py            # 87 KB FastAPI app factory + lifespan
│   │   ├── config.py          # pydantic-settings
│   │   ├── database.py        # async engine + session factory
│   │   ├── dependencies.py    # DI
│   │   ├── cli.py             # CLI entrypoint (`nexus` / `openestimate` commands)
│   │   ├── schemas.py
│   │   ├── middleware/
│   │   ├── core/              # Framework: events, hooks, module loader, validation
│   │   │   ├── module_loader.py
│   │   │   ├── events.py / hooks.py
│   │   │   ├── permissions.py
│   │   │   ├── validation/    # Rule engine + colocated rule registry
│   │   │   ├── email/         # Resend + SMTP backends
│   │   │   ├── match_service/ # CWICR / RSMeans semantic match
│   │   │   ├── workflow_engine.py
│   │   │   ├── i18n.py        # 142 KB
│   │   │   ├── storage.py
│   │   │   └── …
│   │   ├── pipelines/         # text_to_cost_estimate (LangGraph); see "Known bugs"
│   │   ├── modules/           # 91 business modules (see inventory below)
│   │   └── scripts/           # seed_catalog, demo data, etc.
│   ├── data/ddc_templates/    # DDC cad2data templates
│   ├── locales/               # i18n source files
│   └── tests/{unit,integration,perf,eval,fixtures}/
│
├── frontend/                  # React SPA
│   ├── package.json           # nexus-frontend v2.8.8
│   ├── vite.config.ts
│   ├── eslint.config.js
│   ├── tailwind.config.js
│   ├── playwright.config.ts
│   ├── public/
│   ├── src/
│   │   ├── app/               # Shell, layout, i18n, App.tsx (96 routes)
│   │   ├── features/          # 58 feature dirs (mirror backend modules)
│   │   ├── modules/           # 41 plugin-style modules (regional BOQ-exchange, viewers, etc.)
│   │   ├── shared/{ui,hooks,lib,types}/
│   │   ├── stores/            # 24 Zustand stores
│   │   └── tests/             # cross-cutting test setup
│   ├── e2e/                   # 51 Playwright specs
│   └── login-variants/        # Auth-screen design alternates
│
├── desktop/                   # Tauri 2 desktop app
│   ├── src-tauri/             # Rust shell (Cargo.toml — package still "openestimate-desktop")
│   ├── pyinstaller.spec
│   └── build-sidecar.sh
│
├── modules/                   # Module-development scaffolding
│   └── oe-module-template/
│
├── deploy/
│   ├── docker/                # Dockerfile.{backend,frontend,unified}
│   ├── railway/railway.toml
│   ├── render/render.yaml
│   └── terraform/digitalocean/
│
├── data/                      # Seed data, dashboards, BIM samples
├── docs/                      # ADRs, RFCs, audits, install guides
├── scripts/                   # Cross-cutting scripts (check_version_sync.py, etc.)
├── tools/                     # watermark and other utilities
├── signatures/                # CLA signatures DB
└── website-marketing/         # 17 marketing-site design variants — out of scope for app fixes
```

The old CLAUDE.md described a `packages/` shared-libraries directory and a `services/` separate top level. Neither exists in this tree — `services/` is implied inside `backend/app/` (e.g. `core/match_service/`) and `packages/` content lives under `backend/app/core/` and `frontend/src/shared/`.

### Backend module inventory (91 modules)

Grouped roughly by domain (this mapping drives the per-batch fix order in `docs/audits/2026-05-13-full-pass-baseline.md`):

- **Phase-1 estimation core**: `projects`, `costs`, `boq`, `takeoff`, `validation`, `assemblies`, `dashboards`, `catalog` (the last lives in `data/catalog/`, not as a backend module)
- **CAD/BIM**: `cad`, `bim_hub`, `bim_requirements`, `dwg_takeoff`, `viewer3d`, `visualbim`, `ddc_pdf_excel`, `ddc_profiling`, `ddc_qto`, `ddc_revit_export`, `opencde_api`
- **Construction workflow**: `rfi`, `submittals`, `transmittals`, `changeorders`, `ncr`, `punchlist`, `inspections`, `safety`, `meetings`, `fieldreports`, `correspondence`, `markups`, `rfq_bidding`, `tendering`, `procurement`, `contacts`
- **Planning / control**: `schedule`, `eac`, `full_evm`, `risk`, `project_intelligence`, `sustainability`, `ml_price_prediction`
- **Cross-cutting**: `search`, `jobs`, `notifications`, `integrations`, `reporting`, `finance`, `compliance`, `compliance_ai`, `enterprise_workflows`, `erp_chat`, `ai`, `cost_match`, `match`, `costmodel`, `backup`, `uploads`, `documents`, `cde`, `tasks`, `teams`, `requirements`, `precon`
- **Regional packs**: `us_pack`, `uk_pack`, `dach_pack`, `asia_pac_pack`, `latam_pack`, `india_pack`, `middle_east_pack`, `russia_pack`
- **Stragglers / templates**: `hello_world`, `my_module`, `i18n_foundation`, `admin`, `architecture_map`, `collaboration`, `collaboration_locks`, `users`

32 of these modules have a `router.py` that isn't directly imported in `backend/app/main.py` — most are mounted dynamically via `app/core/module_loader.py`; a small number may be dead. Confirm per-module before deleting anything.

---

## Module conventions

A module is a Python package under `backend/app/modules/<name>/` with these files. Not every file is mandatory, but if a module needs the responsibility, that's where it goes:

```
backend/app/modules/<name>/
├── manifest.py          # ModuleManifest declaration (recommended, missing on precon)
├── models.py            # SQLAlchemy ORM models (auto-registered)
├── schemas.py           # Pydantic request/response schemas
├── router.py            # FastAPI router — mounted by module_loader at /api/v1/<name>/
├── service.py           # Business logic (stateless)
├── repository.py        # Data access layer (often inlined into service.py in practice)
├── hooks.py / events.py # Event-bus + hook subscriptions
├── validators.py        # Module-specific validation rules
├── permissions.py       # RBAC permission definitions
├── tests/               # Module-local tests (in addition to top-level tests/)
└── migrations/          # Module-scoped Alembic migrations (rare; most live at backend/alembic/versions/)
```

Example manifest:

```python
# backend/app/modules/boq/manifest.py
from app.core.module_loader import ModuleManifest

manifest = ModuleManifest(
    name="oe_boq",
    version="1.0.0",
    display_name="Bill of Quantities",
    description="Core BOQ editor with hierarchical structure and assembly support",
    author="NEXUS Core Team",
    category="core",
    depends=["oe_projects", "oe_costs"],
    auto_install=True,
)
```

---

## Validation pipeline (CRITICAL)

Validation is a first-class workflow step. Every import / data change runs through configurable rules:

```python
class ValidationRule(ABC):
    rule_id: str
    name: str
    standard: str          # "DIN276", "NRM", "MasterFormat", "GAEB", "custom"
    severity: Severity     # ERROR (blocks), WARNING (flags), INFO (suggests)
    category: str          # "structure", "completeness", "consistency", "compliance"

    @abstractmethod
    async def validate(self, context: ValidationContext) -> ValidationResult: ...
```

```
Import → Parse → VALIDATE → Enrich → Store
              ↓
   ValidationReport (passed / warnings / errors / score 0.0-1.0)
```

Built-in rule sets (toggleable per project/tenant):

| Rule set | Scope | Examples |
|----------|-------|----------|
| `din276` | DACH cost structure | KG hierarchy, allowed codes, level completeness |
| `gaeb` | DACH tender format | GAEB XML schema, LV structure, Einheitspreise |
| `nrm` | UK measurement | NRM 1/2 element compliance, measurement rules, BCIS |
| `masterformat` | US classification | Division structure, code format, descriptions |
| `boq_quality` | Universal | Missing quantities, zero prices, duplicates, unrealistic rates |
| `bim_compliance` | CAD/BIM data | Required properties present, geometry valid, classification mapped |
| `project_completeness` | Universal | All trades covered, benchmark deviations, missing scope |
| `custom` | User-defined | Python scripts or rule-builder UI |

All rule classes are colocated in `backend/app/core/validation/rules/__init__.py`. Third-party rules register via the rule registry. UI shows results as 🟢 / 🟡 / 🔴 traffic-light dashboard.

---

## CAD conversion pipeline (DDC cad2data — NOT IfcOpenShell)

```
Any CAD input
    ↓
DDC cad2data converter (DWG / DGN / RVT / IFC) → canonical JSON
PDF                    → PyMuPDF vector + raster extraction → canonical
Photos                 → CV pipeline (YOLO + OCR)            → canonical
    ↓
VALIDATION (structure, completeness, required properties)
    ↓
Enrichment (classification, cost matching via Qdrant)
    ↓
Storage (PostgreSQL / SQLite + blobs in MinIO / filesystem)
```

Canonical format (one JSON shape for every CAD source):

```json
{
  "format_version": "1.0",
  "source": {"type": "rvt", "filename": "project.rvt", "converter": "ddc-cad2data/0.3.0"},
  "metadata": {"project_name": "...", "units": "metric", "coordinate_system": "..."},
  "elements": [
    {
      "id": "elem_001",
      "category": "wall",
      "classification": {"din276": "330", "masterformat": "04 20 00"},
      "geometry": {"type": "extrusion", "length_m": 12.5, "height_m": 3.0, "thickness_m": 0.24, "area_m2": 37.5, "volume_m3": 9.0},
      "properties": {"material": "concrete_c30_37", "fire_rating": "F90"},
      "quantities": {"area": 37.5, "volume": 9.0, "length": 12.5},
      "relations": {"level": "level_01", "zone": "zone_a", "parent": null}
    }
  ],
  "levels": [...], "zones": [...], "spatial_structure": {...}
}
```

---

## End-to-end workflow

```
1. IMPORT
   ├── Upload PDF / Photo / CAD (drag-and-drop or API)
   ├── Auto-detect format (magic bytes + extension)
   └── Route to the appropriate converter

2. CONVERT
   ├── CAD → canonical JSON (DDC cad2data)
   ├── PDF → vector + OCR (PyMuPDF + PaddleOCR)
   ├── Photo → CV pipeline (YOLO + OCR)
   └── Output: structured elements with quantities

3. ✅ VALIDATE (mandatory)
   ├── Structural / classification / completeness / consistency / custom checks
   ├── Generate ValidationReport with traffic-light dashboard
   └── User reviews and resolves issues before proceeding

4. ENRICH
   ├── AI classification (auto-assign cost codes)
   ├── Cost matching (vector search in CWICR / RSMeans via Qdrant)
   ├── Assembly suggestion (similar historical assemblies)
   └── Confidence scores on every AI suggestion

5. ESTIMATE
   ├── BOQ editor (block-based, AG Grid, assemblies)
   ├── Rate application (manual + AI-suggested)
   ├── What-if scenarios (material substitution, regional adjustment)
   ├── Real-time cost rollup
   └── Collaborative editing (Yjs multiplayer)

6. ✅ VALIDATE ESTIMATE (second pass)
   ├── BOQ-quality rules (zero prices, missing quantities, duplicates)
   ├── Benchmark comparison vs historical
   ├── Anomaly detection
   ├── Coverage % vs original scope
   └── Client-specific rules

7. TENDER
   ├── Generate tender documents (GAEB X83, PDF, Excel)
   ├── Distribute to subcontractors
   ├── Collect & compare bids
   └── Award recommendation

8. REPORT & EXPORT
   ├── Executive summary (PDF)
   ├── Detailed BOQ (GAEB XML, Excel, CSV)
   ├── Cost breakdown by KG / NRM / Division
   ├── Validation report (compliance certificate)
   ├── API export (JSON, Parquet)
   └── Integration push (SAP, Procore, MS Project via n8n)
```

---

## Roadmap (current state, not a fresh plan)

The original CLAUDE.md described five sequential phases starting from a Phase 0 "Foundation — 2 weeks." That plan is historical. As of 2026-05-13 the project is past Phase 4-equivalent feature work (see `PHASE_7_*.md` at the repo root). Active development tracks:

| Track | Status | Notes |
|-------|--------|-------|
| Foundation (auth, RBAC, modules, validation framework, i18n) | Shipped | RBAC enforced (see 2026-05-09 QA audit); 91 modules autoloaded |
| Core estimation (projects, costs, BOQ, takeoff, validation) | Shipped | BOQ editor in production use; CWICR catalogue seeded |
| CAD integration | Shipped | DDC cad2data bridge live; 3D viewer (Three.js + online-3d-viewer) live |
| AI takeoff (PDF) | Shipped (PaddleOCR + YOLO behind `[cv]` extra) | DWG-takeoff page is one of the largest TS files (202 KB) |
| Collaboration / Enterprise (Yjs, multi-tenant, SSO, audit) | Partial | Yjs deps installed; tendering module exists; multi-tenant work in progress |
| Marketplace / ecosystem | Backlog | Module SDK exists; marketplace registry not yet shipped |
| Federal pivot | Active | Precon module, EAC engine, federal compliance helpers — recent commits in `bill143/` fork |
| Email (Railway compatibility) | Shipped | Resend HTTP backend added in `067fb7f` to bypass blocked SMTP |
| Branding rename | Mostly shipped | `bc0222e` renamed OpenConstructionERP → NEXUS; remaining drift listed below |

What needs attention (from the baseline audit and the 2026-05-09 QA report):

- Schema drift (38 events from `alembic check` on SQLite; the QA report saw more on Postgres)
- `frontend/eslint.config.js` missing `@eslint/js` devDep (breaks under pnpm)
- `app/pipelines/__init__.py` eagerly imports `text_to_cost_estimate.graph`, which needs an undeclared `langgraph` dep
- `tests/unit/eac/test_schema_jsonschema.py` needs `jsonschema` in `[dev]` extras
- `make test-unit` / `make test-integration` Makefile targets select 0 tests (no `pytest.mark.unit` decorators in code)
- 1 unit-test failure (`test_default_role_is_editor`) and 69 vitest failures
- `docker-compose.quickstart.yml:34` has an unquoted `${VAR:?error: msg}` containing a colon (strict YAML invalid)
- 8 bundle chunks > 500 KB; `VisualBimPage` and `i18n-data` are the two outliers
- `Changelog.tsx` stuck at 2.5.0 while everything else is 2.8.8

---

## Instructions for Claude Code

### Code generation

1. **Match scope to the request** — this is a working app, not a greenfield project. Don't write Phase-0 scaffolding when fixing a Phase-7+ bug. Match the change to what the user asked for.
2. **One module at a time when refactoring** — complete a module's chain (`models → schemas → service → router → tests`) before moving to the next. For bug fixes, touch only the affected file plus what's necessary to keep tests green.
3. **Tests first for core** — `validation/`, `module_loader.py`, `events.py`, `hooks.py` get TDD treatment. Business modules can land tests alongside or after.
4. **Read each module's CLAUDE.md** before working on it — some modules have their own context file. Honour module-local conventions.
5. **Canonical format is the source of truth** — all CAD conversions land in the canonical shape; BOQ / validation read canonical.
6. **Don't break validation** — when adding a feature that creates data, add corresponding validation rules. Validation isn't optional.
7. **Don't reintroduce IfcOpenShell** — under any circumstances. BCF is allowed; IfcOpenShell is not. Decision last reviewed 2026-04-26.
8. **Don't auto-apply AI suggestions** — confidence score + human review, always.

### Problem solving

1. Propose a solution → wait for confirmation → implement (for non-trivial work).
2. When the problem is ambiguous, propose 2-3 options with trade-offs.
3. Don't delete code without explaining why and getting confirmation — some apparently dead modules are loaded dynamically.
4. Don't add dependencies without justification (check: is there a stdlib or already-installed alternative?).

### Answer style

- Code, comments, docs: **English**.
- Conversation: English.
- Keep technical terms in English (don't translate "validation", "canonical format", "hook").
- Be concrete: not "add validation," but "add `DIN276CostGroupHierarchy` to `backend/app/core/validation/rules/__init__.py`."

### Development commands (matches the real `Makefile`)

```bash
# First-time setup
make setup            # pip install backend[server] + npm install frontend
                      # NOTE: requires frontend/dist to exist — see Known bug §"force-include"

# Day-to-day dev (two terminals)
make infra            # docker compose up -d postgres redis minio
make dev-backend      # uvicorn app.main:create_app --factory --reload --port 8000
make dev-frontend     # vite dev server on port 5173

# Or: single-command launch
make quickstart       # docker compose -f docker-compose.quickstart.yml up --build → http://localhost:8080

# Testing
make test             # backend pytest + frontend vitest
make test-backend     # pytest -x -v
make test-backend-cov # pytest --cov=app --cov-report=term --cov-report=html
make test-frontend    # npm run test
# NOTE: `make test-unit` / `make test-integration` use pytest -m, currently select 0 tests
# Use `pytest tests/unit/` / `pytest tests/integration/` directly.

# Quality
make lint             # ruff check + npm run lint
make format           # ruff format + prettier
make typecheck        # mypy app/ + tsc --noEmit
                      # NOTE: mypy strict mode currently reports ~1830 errors — aspirational

# Database
make migrate          # alembic upgrade head
make seed             # python -m app.scripts.seed_catalog
make migrate-new MSG="..."   # alembic revision --autogenerate

# Module scaffolding
make module-new NAME=oe_tendering    # create skeleton

# Build
make build            # docker build all three deploy images
make build-wheel      # build frontend first, then python wheel (correct install order)
```

---

## Key data models (canonical)

### Project

```
Project → many BOQ → many Section → many Position
Project → many Document (PDFs, CAD files)
Project → many ValidationReport
Project → one ProjectConfig (enabled standards, rule sets, regional settings)
```

### BOQ Position

```
Position:
  - id: UUID
  - boq_id: FK
  - parent_id: FK (nullable — hierarchy)
  - ordinal: str ("01.02.003")
  - description: text
  - unit: enum (m, m2, m3, kg, pcs, lsum, ...)
  - quantity: Decimal
  - unit_rate: Decimal (Numeric, money-safe; see migration v258_money_numeric)
  - total: Decimal (computed: quantity × unit_rate)
  - classification: JSONB {din276: "330", nrm: "2.6.1", masterformat: "03 30 00"}
  - source: enum (manual, cad_import, ai_takeoff, gaeb_import)
  - confidence: float (0.0-1.0, only for AI-sourced rows)
  - assembly_id: FK (nullable — assembly template link)
  - cad_element_ids: list[str] (links into the canonical-format elements array)
  - validation_status: enum (pending, passed, warnings, errors)
  - metadata: JSONB (module-extensible)
```

### Assembly (recipe / Stahlbetonwand-style composite)

```
Assembly:
  - id: UUID
  - name: str
  - category: str
  - components: list[AssemblyComponent]
    - cost_item_id: FK to CostDatabase
    - factor: Decimal
    - unit: str
  - total_rate: Decimal (computed)
  - regional_factors: JSONB
```

### Validation report

```
ValidationReport:
  - id: UUID
  - project_id: FK
  - target_type: enum (boq, document, cad_import, tender)
  - target_id: UUID
  - rule_set: str
  - status: enum (passed, warnings, errors)
  - score: float (0.0-1.0)
  - results: list[ValidationResult]
    - rule_id: str
    - status: enum (pass, warning, error)
    - message: str
    - element_ref: str (links to a specific BOQ position / CAD element / page)
    - details: JSONB
  - created_at: datetime
  - created_by: FK
```

---

## Environment variables (`.env.example`)

```env
# Database — defaults to SQLite, no external service needed
DATABASE_URL=sqlite+aiosqlite:///./openestimate.db
DATABASE_SYNC_URL=sqlite:///./openestimate.db
# For production:
# DATABASE_URL=postgresql+asyncpg://oe:oe@localhost:5432/openestimate
# DATABASE_SYNC_URL=postgresql://oe:oe@localhost:5432/openestimate

# Redis (optional — in-memory fallback for dev)
REDIS_URL=redis://localhost:6379/0

# Celery (only if running background workers)
OE_CELERY_BROKER_URL=redis://localhost:6379/1
OE_CELERY_RESULT_BACKEND=redis://localhost:6379/1

# MinIO / S3 (optional — local FS fallback)
S3_ENDPOINT=http://localhost:9000
S3_ACCESS_KEY=minioadmin
S3_SECRET_KEY=minioadmin
S3_BUCKET=openestimate

# Auth
JWT_SECRET=change-me-in-production
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=60

# AI (optional — features degrade gracefully)
QDRANT_URL=http://localhost:6333
OPENAI_API_KEY=
ANTHROPIC_API_KEY=

# Email (Resend HTTP API — Railway-compatible)
RESEND_API_KEY=
EMAIL_BACKEND=resend   # or "smtp" / "console"

# CAD converter sidecar
CAD_CONVERTER_URL=http://localhost:8001

# CV pipeline sidecar
CV_PIPELINE_URL=http://localhost:8002

# App
APP_ENV=development
APP_DEBUG=true
LOG_LEVEL=INFO
ALLOWED_ORIGINS=http://localhost:5173
```

---

## Hard constraints

1. **NO IfcOpenShell** — all BIM/CAD goes through DDC cad2data.
2. **BCF is allowed** as an I/O format (issues / viewpoints / validation reports). Hand-rolled XML or an AGPL-compatible library, no IfcOpenShell-dependent stack. Decision last reviewed 2026-04-26.
3. **No native IFC parser** — IFC is just one more CAD format that flows through the canonical converter.
4. **No monolithic architecture** — every feature is a module with a manifest. Don't merge separate modules into shared mega-files.
5. **Validation is mandatory** — no module ships without validation rules; no workflow skips the validation step.
6. **No auto-applied AI results** — every AI suggestion needs a confidence score and a human confirm.
7. **No vendor lock-in** — all data is exportable; all formats are open.
8. **No `git push --force`** to `main` or any shared branch.

---

## Known branding drift

These artefacts still carry the old names. Each will be cleaned up in its corresponding batch:

- `desktop/src-tauri/Cargo.toml` — package name `openestimate-desktop`, description "OpenEstimate Desktop" (Batch 18)
- `backend/openestimate.db` and `s3 bucket = openestimate` in `.env.example` (intentional — the on-disk filename is back-compat)
- `frontend/cli.py` demo login: `demo@openestimator.io / DemoPass1234!` (low priority, demo creds)
- `pyproject.toml [project.scripts]` exposes both `openestimate` and `nexus` CLIs (intentional — back-compat)
- `data/init.sql` and seed scripts reference `openestimate` as the Postgres database name (intentional — back-compat)

If you find more drift, surface it in the relevant batch and either fix it inline or list it for follow-up.
