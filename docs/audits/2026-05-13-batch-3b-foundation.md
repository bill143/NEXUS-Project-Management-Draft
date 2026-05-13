# Batch 3b — Backend foundation followup (2026-05-13)

Investigation results for the open items from `2026-05-13-full-pass-baseline.md` §3.6 / §3.8 / §3.9 / §3.2. This batch's fixes ship on `fix/backend-foundation-rest`; the findings below were discovered along the way and are recorded so we don't re-investigate next session.

## §3.6 — `make test-unit` / `make test-integration` select 0 tests — **fixed**

Tests are organised by directory (`tests/unit/`, `tests/integration/`), not by `@pytest.mark.unit` / `@pytest.mark.integration` decorators. The only `@pytest.mark` actually used in the suite is one `@pytest.mark.slow`. So `pytest -m unit` was selecting **0 tests** and reporting success.

Fix landed in this branch: changed both Makefile targets to select by path. The `markers = [...]` block in `pyproject.toml` is left in place (harmless, useful for future).

## §3.8 — Routes vs nav: framing was wrong — **resolved (no action needed)**

The baseline reported "50 backend routes at boot vs 96 frontend routes" and called the gap suspicious. After investigation the comparison is **apples-to-oranges**:

- `App.tsx` `<Route path="…">` declarations are **client-side SPA routes** for React Router. They render React pages.
- `app.include_router(...)` calls register **HTTP API routes** under `/api/…`. They serve JSON.

A frontend SPA route doesn't need a 1:1 backend route — most pages make multiple API calls, some pages make none (`/about`, `/login` initially, etc.).

The relevant numbers measured this batch:

| Layer | Count |
|---|---:|
| Frontend SPA routes (`<Route>` in `App.tsx`) | 96 |
| Backend API routes after `create_app()` only (no lifespan) | 50 |
| Backend API routes after full lifespan (`module_loader.load_all`) | **963** |

So the boot-time-50 number from the baseline was *before* the module loader had run. After lifespan startup the backend exposes ~10x as many routes as the frontend has SPA routes. Not a gap — the opposite.

## §3.9 — 32 modules with `router.py` not imported in `main.py` — **resolved (no action needed)**

The baseline flagged 32 backend modules whose `router.py` was never `from app.modules.X import …`'d in `main.py`, raising the question of whether they were dead. They are not — they're loaded dynamically by `app.core.module_loader.module_loader.load_all(app)` (called from `main.py:1581` inside the lifespan).

Reproducible measurement (run from `backend/`):

```bash
SEED_DEMO=false python -c "
import asyncio
from app.main import create_app
from app.core.module_loader import module_loader

async def main():
    app = create_app()
    await module_loader.load_all(app)
    print(f'Modules loaded: {len(module_loader.list_modules())}')
    print(f'Total routes: {len(app.routes)}')

asyncio.run(main())
"
```

Result: **79 modules loaded, 963 routes**.

The on-disk inventory of `backend/app/modules/` directories that contain `__init__.py` is **80 dirs**. So exactly **one** dir is on disk but not loaded:

- `precon` — no `manifest.py`; hand-wired via `main.py:916` (`app.include_router(precon_router, prefix="/api/precon", tags=["precon"])`). Intentional special case for the federal-pivot module. Confirmed earlier in the baseline §3.10.

**No dead modules in the backend.** The earlier "91 modules" count in the baseline overcounted by including non-module entries (or was an inventory artefact); the real number is 80 module dirs + 79 manifest-driven loads + 1 hand-wired (precon) = 80 active.

## §3.2 — Real null-deref bugs vs mypy noise — **triaged + fixed where real**

The baseline flagged ~10 sites as "real null-deref bugs" out of 1830 mypy errors. After investigating each:

| Site | Verdict | Fixed |
|---|---|---|
| `app/main.py:605` — `demo.id` while `demo: User \| None` | **Real fragility** — if account creation raises before `demo = user`, the demo-project install crashes the lifespan | Yes (early-return + warning) |
| `app/main.py:1183` — `set[object]` vs `set[str]` | Type cleanliness | Yes (`str()` coerce) |
| `app/core/match_service/extractors/bim.py:78,95,118` — `raw.get(...) if isinstance(raw.get(...), dict) else {}` | Read-twice pattern; mypy can't narrow across two calls; runtime fine | Yes (extracted to local var, makes mypy happy AND removes the theoretical race window) |
| `app/core/match_service/extractors/photo.py:60` — `float(value)` on `Any \| None` | mypy false-positive — `value in (None, "", 0): continue` filter + `try/except (TypeError, ValueError)` already in place | No fix needed |
| `app/core/match_service/extractors/pdf.py:60,75,80` — same `float(...)` pattern | Same — `try/except` already in place | No fix needed |

So the audit's "~10 real null-deref bugs" count was high; the real number is **one fragility (main.py:605) and a handful of mypy-strict noise**. The remaining ~1820 mypy errors are missing annotations / bare `dict` / `list` types — tracked for a future type-tightening pass, not runtime issues.

## What's NOT addressed in this batch

- The remaining 1820 mypy errors (missing annotations etc.) — too noisy to take on as a single PR; will be addressed module-by-module in Batches 6-11.
- The pre-existing `tests/unit/test_users.py::test_default_role_is_editor` failure — belongs to Batch 4 (security cross-cuts).
- The `app/main.py:691, 858, 983, 1108, 1119` missing annotations — same pattern as the broader mypy noise; defer.
