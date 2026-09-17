# Batch 6 — Projects module audit

**Date:** 2026-06-16
**Branch:** `batch-6/audit-projects-module`
**Scope:** `backend/app/modules/projects/` — every file, read in full, compared against the
module conventions in `.claude/CLAUDE.md` and cross-referenced with consumers elsewhere in
the backend.
**Method:** read all 8 files in the module; greppped for permission consumers, router mount
points, validation-rule registration, and test files; tallied endpoint count against
implied responsibilities; no behavioural changes made — pure read-and-report.

This is the first of five Phase-1 module audits (projects → boq → costs → validation →
takeoff). The pattern established here sets the template for the rest.

---

## TL;DR (read this if nothing else)

The Projects module is **shipping and structurally functional**, but has six concrete
problems that warrant follow-up tickets and three architectural smells the team should
discuss before they get worse.

The highest-leverage finding: **the per-module permission registry has no consumers
anywhere in the codebase.** `permissions.py` registers `projects.create / read / update /
delete` with role gates, but nothing in the request path ever calls
`permission_registry.role_has_permission(...)`. Authorization is currently enforced by an
inline `_verify_project_owner` helper in `router.py:45-65` that hardcodes "owner OR
role==admin" and ignores the registry entirely. Every other module's permission
registrations are presumably in the same state — Batch 6/boq will confirm.

The second-highest: **`router.py` is 1712 lines, of which ~960 (lines 251-1208) are a
god-dashboard endpoint that cross-queries 18 other modules via inline `try/except
ImportError`.** It works but it bypasses every architectural boundary the rest of the
module respects, and it makes the manifest's `depends=["oe_users"]` a lie.

---

## Present vs. spec (module conventions)

CLAUDE.md "Module conventions" section enumerates the canonical layout. Reality:

| File / dir         | Spec     | Present? | Notes                                               |
| ------------------ | -------- | -------- | --------------------------------------------------- |
| `manifest.py`      | required | ✅       | But version still `0.1.0` and description stale     |
| `__init__.py`      | implicit | ✅       | Just calls `register_project_permissions` on boot   |
| `models.py`        | required | ✅       | 4 models, 341 lines, well-commented                 |
| `schemas.py`       | required | ✅       | 778 lines — large but cohesive                      |
| `repository.py`    | required | ✅       | Only covers `Project`, not `WBS` or `Milestone`     |
| `service.py`       | required | ✅       | 555 lines, covers Project + match-settings helpers  |
| `router.py`        | required | ✅       | 1712 lines, 21 endpoints — see findings #2, #3, #4  |
| `hooks.py`         | required | ❌       | No file. No filters or actions registered.          |
| `events.py`        | required | ❌       | Events are published as ad-hoc string literals in service.py |
| `validators.py`    | required | ❌       | No file. Module contributes zero validation rules. |
| `permissions.py`   | required | ✅       | Present but unused — see finding #1                 |
| `migrations/`      | required | ❌       | Migrations live in global `backend/alembic/versions/` instead |
| `tests/`           | required | ❌ (off-spec) | Tests exist at `backend/tests/{unit,integration}/test_project*.py` — 959 lines across 4 files. Not module-colocated as spec requires. |

Two layout deviations (`tests/` and `migrations/` being non-colocated) are platform-wide
patterns — they're not unique to this module. Worth flagging as platform-level decisions
to revisit, not module-level bugs.

---

## Findings

### #1 — Registered permissions are never enforced (HIGH)

**Files:** `permissions.py:6-16`, `router.py:45-65`, `app/core/permissions.py` (entire
registry).

`register_project_permissions()` registers four permission strings:

```python
{
    "projects.create": Role.EDITOR,
    "projects.read":   Role.VIEWER,
    "projects.update": Role.EDITOR,
    "projects.delete": Role.MANAGER,
}
```

Grep across the entire backend for any caller of
`permission_registry.role_has_permission` / `.check` / `.has` / `.verify` / `.enforce`
returns **zero hits**. The registry is populated at startup and then ignored.

What actually gates write access:

```python
# router.py:45-65 — the only authorization check on every route
async def _verify_project_owner(service, project_id, user_id, payload=None):
    project = await service.get_project(project_id)
    if payload and payload.get("role") == "admin":
        return project
    if str(project.owner_id) != user_id:
        raise HTTPException(403, "You do not have access to this project")
    return project
```

This means:

- `Role.MANAGER` requirement on `projects.delete` is decorative — a regular `EDITOR` who
  owns the project can delete it.
- `Role.VIEWER` requirement on `projects.read` is bypassed — list/get only check
  ownership, not role.
- The "estimator", "quantity_surveyor", "qs", "owner" aliases in
  `app/core/permissions.py:51-60` are defined but cannot affect behaviour because the
  registry is never consulted.

**Action:** either wire the registry into a FastAPI dependency that runs alongside
`_verify_project_owner`, or delete the registry and the per-module `permissions.py`
files and document "ownership-only" as the project's actual auth model. Pretending we
have RBAC when we don't is worse than honestly admitting we don't.

### #2 — `router.py` is a god-router (HIGH)

**File:** `router.py:1-1712`, especially `project_dashboard` (251-975) and
`dashboard_cards` (981-1208).

The router has 21 route handlers. Five of them are the documented Project CRUD
(create/list/get/update/delete + restore). The other 16 cover: WBS CRUD, milestone CRUD,
match-settings CRUD+reset, the dashboard, the dashboard-cards endpoint, and the
cross-project analytics endpoint.

The `project_dashboard` endpoint alone is 725 lines (line 251 to 975). It imports from
and queries — with inline `try/except` — these modules:

```
boq, costmodel, schedule, projects, punchlist, inspections, ncr,
risk, documents, transmittals, rfi, submittals, tasks, meetings,
procurement, changeorders, fieldreports, markups, requirements,
takeoff
```

That's **20 cross-module imports** wrapped in `try/except Exception: logger.debug(...)`
for "graceful degradation". Two problems:

1. **The module's manifest lies.** `manifest.py:12` declares `depends=["oe_users"]`. The
   real dependency graph contains every Phase-1 through Phase-4 module. If any one of
   those modules has a breaking schema change, the dashboard endpoint either returns a
   partial response with no visible warning to the caller, or — depending on which
   `try/except` boundary fires — degrades silently. The user sees zeros where they
   should see errors.
2. **The dashboard belongs in its own module.** Per the spec's "Modules = plugins"
   principle, a unified dashboard that aggregates 20 modules' data should live in
   `app/modules/dashboard/` (or `app/modules/reporting/dashboard.py`). Putting it under
   `/api/v1/projects/{id}/dashboard` makes Projects the unwilling owner of every other
   module's KPI definitions.

**Bonus smell:** `budget_section["committed"] = str(round(actual_total * 0.8, 2))` on
line 357 — a hardcoded 0.8 fudge factor with no comment. Reads like a placeholder that
shipped.

**Action:** factor `project_dashboard` and `dashboard_cards` out into
`app/modules/dashboard/` (new module) with a manifest that honestly declares its
20-module dependency chain. Keep a thin `GET /api/v1/projects/{id}/dashboard` shim that
proxies to the new module for URL compatibility, deprecate it, remove in v3.

### #3 — WBS and Milestone CRUD bypass the repository/service layers (MEDIUM)

**Files:** `router.py:1330-1641` (WBS + Milestone handlers), `repository.py:1-122` (only
covers Project).

The router handlers for `POST/GET/PATCH/DELETE /{project_id}/wbs/...` and the matching
milestone routes contain inline SQLAlchemy: direct `session.execute(select(...))`,
`session.add(node)`, `session.execute(delete(...).where(...))`, etc. They do call
`_verify_project_owner` first, then drop straight to ORM.

The Project routes go through `ProjectService → ProjectRepository`. The WBS and
Milestone routes don't, because `ProjectRepository` only has methods for `Project`.

Consequence: business logic that should be testable in isolation (parent-id validation,
status-transition rules, cycle prevention) is glued into HTTP handlers. The
`_MILESTONE_TRANSITIONS` table is defined in `schemas.py:476-481` but enforced in
`router.py:1581-1596` — schema-level data with router-level enforcement.

**Action:** extract `WBSRepository`, `MilestoneRepository`, `MatchSettingsRepository`
(or fold them into `ProjectRepository`). Move the WBS parent-validation, milestone
status-transition logic, and cycle-prevention checks into service methods. The router
should be ~30 lines per resource, not 80-130.

### #4 — `delete_project` cascade is incomplete and brittle (MEDIUM)

**File:** `service.py:276-375`.

The soft-delete path explicitly hard-deletes child records from eight modules:
`Task, RFI, Meeting, PunchItem, Inspection, NCR, FieldReport, Risk`. Each is wrapped in
`try: import; except ImportError: pass`.

Project rows have `project_id` FKs declared (across alembic migrations grepped above)
in at least: `documents, transmittals, submittals, schedule, procurement, changeorders,
markups, requirements, takeoff, safety, costmodel, sustainability` — none of which are
in the cascade list. Those rows will silently outlive their parent project after the
project is archived, accessible by ID to anyone who still holds the URL.

**Root cause:** the architectural choice to soft-delete (set `status='archived'`) means
DB-level `ondelete=CASCADE` never fires. The explicit Python cascade is the only thing
that keeps child records in sync with parent visibility. Adding new modules with
`project_id` FKs requires editing this list — easy to forget.

**Options:**

- A. Hard-delete projects (let DB cascade do its job). Loses audit trail of historical
  projects.
- B. Add a generic "archive cascade" registry that any module can opt into. When a
  project archives, iterate the registry. New modules register; nobody edits
  `service.py`.
- C. Filter every child-module query by `project.status != 'archived'`. Spreads the
  responsibility everywhere instead of localising it.

Recommendation: **B**. Builds on the existing event bus — `projects.project.deleted`
already fires (`service.py:358-365`), modules can subscribe and clean up their own rows.
Remove the inline cascade list entirely.

### #5 — Duplicate `@field_validator` on `ProjectUpdate.name` (LOW)

**File:** `schemas.py:274-282` and `schemas.py:342-352`.

Both decorated `@field_validator("name", mode="after")`, both rejecting HTML tags, both
returning `v.strip()`. The second is a copy-paste of the first under a different
function name (`_reject_html_in_name` vs `reject_html_tags`). Pydantic v2 will run both,
which produces no incorrect behaviour but does the work twice.

**Action:** delete `reject_html_tags` at lines 342-352. Trivial fix.

### #6 — Restore endpoint inconsistent trailing-slash handling (LOW)

**File:** `router.py:177-188` vs `router.py:219-225`.

`DELETE /{project_id}/` and `DELETE /{project_id}` both exist (the latter hidden from
OpenAPI). `POST /{project_id}/restore/` exists but `POST /{project_id}/restore` does
not. Clients that strip trailing slashes hit 404 on restore but succeed on delete.

**Action:** add the trailing-slash-less variant on restore, mirroring the delete
pattern, OR commit to one form across the whole router and remove the duplicates. Five
minutes of work either way.

### #7 — `parent_project_id` allows cycles (LOW-MEDIUM)

**File:** `models.py:66-71`, no corresponding validation anywhere.

`Project.parent_project_id` is a self-referential FK with `ondelete=SET NULL`. Nothing
prevents `A.parent = B; B.parent = A` or longer cycles. The `selectin` eager loader on
the `children`/`parent_project` relationships will recurse and either hang or
stack-overflow when something tries to walk the tree.

No test exercises this. Setting up the cycle through the PATCH endpoint is
straightforward.

**Action:** add a service-level cycle check in `update_project` (and `create_project`
if `parent_project_id` is set on create). Walk up the proposed ancestor chain; reject
if the project itself appears.

### #8 — Events are stringly-typed; no `events.py` (LOW)

**File:** `service.py:130-138, 254-261, 358-365, 395-402`.

Four event names are published as raw string literals:
`projects.project.created`, `projects.project.updated`, `projects.project.deleted`,
`projects.project.restored`. There's no central definition. A consumer subscribing has
to grep the publisher to find the name and inspect the call site to learn the payload
shape.

CLAUDE.md says each module should have `events.py` defining its events. The validation
framework (`backend/app/core/events.py`) supports both publish and subscribe; what's
missing is a per-module type definition for the contract.

**Action:** add `app/modules/projects/events.py` with constants and Pydantic schemas
for each event's payload. Service uses the constants instead of literals. Optional but
makes the bus self-documenting.

### #9 — Manifest is stale (LOW)

**File:** `manifest.py:5-14`.

- `version="0.1.0"` — but the model has shipped through at least Phase 12 expansion
  fields, RFC 37 multi-currency (v2.6.0), and match-settings (v2.8.0). Migration
  filenames (`v260c`, `v281`, `v282`) imply versions 2.6 and 2.8 of *something*; the
  module manifest doesn't reflect any of it.
- `description` mentions "regional settings, classification standards, and validation
  configuration" — never mentions WBS, milestones, match-settings, dashboard, or
  analytics, which together account for 1500+ of the 1712 router lines.

**Action:** bump version to align with whatever versioning scheme the migrations use
(`v2.8.x`?), rewrite description to describe what's actually shipped. Cheap and
prevents future engineers from misreading the module's scope.

### #10 — Date fields stored as strings (LOW)

**File:** `models.py:76-79, 228-229`.

`planned_start_date`, `planned_end_date`, `actual_start_date`, `actual_end_date` (on
Project), and `planned_date`/`actual_date` (on Milestone) are all `String(20)` columns.
The Pydantic layer (`_validate_date_string`) accepts ISO, European, and US formats and
returns them unchanged.

Consequences:

- DB can't enforce `planned_start_date <= planned_end_date` via a CHECK constraint
  because string ordering ≠ date ordering across formats.
- Postgres `BETWEEN` queries on these fields return wrong results when formats are
  mixed.
- The dashboard endpoint compares them lexically against `date.today().isoformat()`
  (e.g. `router.py:451, 633, 691`) which silently fails for any project that stored
  dates in DD.MM.YYYY or MM/DD/YYYY format.

**Action:** migrate to `Date` columns. Schema validator stays the same on input,
serializes to ISO on output. One alembic migration with a USING clause that parses
whichever format is present.

---

## Tests

| File                                                                       | Lines | What it covers                                                            |
| -------------------------------------------------------------------------- | ----- | ------------------------------------------------------------------------- |
| `backend/tests/unit/test_project_schemas.py`                               | 136   | `ProjectCreate` field validators (HTML stripping, currency, dates, etc.) |
| `backend/tests/unit/test_project_region_cache.py`                          | 237   | Region cache invalidation hook (cross-module — match service)            |
| `backend/tests/integration/test_projects_list_isolation.py`                | 190   | Multi-user list isolation (user A doesn't see user B's projects)          |
| `backend/tests/unit/v1_9/test_project_intelligence_endpoints.py`           | 396   | v1.9 "intelligence" endpoints (no clear mapping to module code — needs investigation) |

959 lines total. **What's missing:**

- No test for the dashboard endpoint (the largest function in the module).
- No test for WBS CRUD.
- No test for milestone CRUD or status-transition enforcement.
- No test for match-settings CRUD.
- No test for the soft-delete cascade behaviour (finding #4).
- No test for cycle prevention on `parent_project_id` (finding #7) — the missing
  validation would currently let the test create a cycle.
- No test that the registered permissions are enforced (finding #1) — because they
  aren't.
- No test for `restore_project` happy path or failure modes.

The v1.9 intelligence test file (396 lines) is larger than the schema test file plus
the isolation test file combined. Worth a follow-up to confirm what those endpoints
actually are, because grepping the router (`router.py`) doesn't reveal anything labeled
"intelligence".

---

## Punch list

Ordered by leverage (impact × confidence × cheapness):

1. **Decide and document the actual auth model.** Either wire the permission registry
   into route dependencies (preserving the registry as designed), or delete it and
   replace with explicit "ownership-only" comments. Don't ship the lie.
2. **Move the dashboard endpoints out of Projects.** New `app/modules/dashboard/`
   module, manifest with honest dependencies, thin shim left under `/projects/{id}/`
   for URL compat.
3. **Replace the inline `delete_project` cascade with event-bus subscribers.** Each
   module owns its own cleanup. Remove the brittle list from `service.py`.
4. **Add `WBSRepository` / `MilestoneRepository`** (or extend `ProjectRepository`).
   Move WBS/Milestone business logic out of router handlers.
5. **Add cycle detection on `parent_project_id`.** Service-level check in create +
   update.
6. **Migrate date columns to `Date` type.** Single alembic migration.
7. **Delete the duplicate `name` validator** in `ProjectUpdate` (schemas.py:342-352).
8. **Add `events.py` + restore endpoint trailing-slash fix + manifest version/description
   refresh.** Three trivial cleanups, one commit.
9. **Add tests** for: dashboard, WBS CRUD, milestone CRUD + transitions, match-settings
   CRUD, cascade behaviour, cycle prevention, restore happy/error paths.
10. **Investigate what `test_project_intelligence_endpoints.py` covers** and either map
    the endpoints back into the router or delete the orphan tests.

Items 1-5 are architectural and want a real ticket discussion. Items 6-8 are mechanical
and could be done in a single follow-up PR. Item 9 should grow alongside whatever fixes
get made — don't add tests for code that's about to be rewritten.

---

## Not in scope for this audit

- No code changes. This is a read-only audit.
- No comparison against frontend usage. A finding like "the frontend uses field X but
  the model deprecated it" would need a separate cross-cutting Batch.
- No load/perf characterisation of the dashboard endpoint. The dashboard's 20-module
  query fan-out is a probable hotspot but quantifying that is its own piece of work.
- No deep dive into the v1.9 intelligence endpoints. Flagged for follow-up.
- No security review of `_verify_project_owner` beyond noting it's the *only* auth
  check — the actual code looks correct as far as ownership goes.

---

## Method notes (for future audits in this series)

What worked:

- **Reading every file in full before writing anything.** No file in this module is
  shorter than 122 lines except `permissions.py` (17) and `__init__.py` (13). Excerpt
  tools would have missed the dashboard's full scope.
- **Greping for *consumers* of the things the module exports.** The permission
  registry finding (#1) only showed up because I searched for callers of
  `permission_registry.*`, not just usages within the projects module.
- **Counting endpoints and matching them to the manifest description.** The mismatch
  jumped out immediately.

What to try next batch:

- Check the test count per source line before reading the module — gives a quick
  signal about coverage debt.
- Pull the migration files referenced by `oe_<module>_*` table names and check whether
  the model and migrations have drifted (Batch 5 territory, but cheaper to do per-module
  than as a global pass).
