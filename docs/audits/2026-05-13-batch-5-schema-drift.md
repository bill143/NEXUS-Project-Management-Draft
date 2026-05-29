# Batch 5 — Schema drift measurement (2026-05-13)

Pre-fix audit: do not add an index/column unless evidence shows it's
queried. User directive: "measure index hit before fixing."

> ## ⚠ Correction (2026-05-13, same day)
>
> **The audit below is structurally wrong and was kept only as an
> honest record of the mistake.** Read this section first.
>
> When I started writing the catch-up migration on a fresh branch off
> updated `main`, re-running `alembic check` produced **328 events**
> (42 added tables + 151 added indexes + 25 added FKs + 7 added cols +
> 24 removed tables + 76 removed indexes + 3 removed cols), not 78.
> Investigating the gap surfaced the real cause:
>
> - `backend/alembic/versions/129188e46db8_init_create_all_tables.py`
>   is a deliberate no-op marker. Its `upgrade()` body is `pass`.
> - `backend/app/main.py:1561` calls `await
>   conn.run_sync(Base.metadata.create_all)` at boot.
> - The schema source-of-truth in this codebase is **`Base.metadata.
>   create_all()` running at app startup**, not the migration chain.
> - `alembic check` is comparing model metadata against migration ops
>   — two different sources of truth here. The "drift" it reports is
>   the gap between "what migrations create" (mostly nothing) and
>   "what create_all() creates at boot" (everything). It's not real
>   drift.
> - This was already documented correctly in
>   [`docs/audits/QA_REPORT.md` item 6 (lines 145–176)](./QA_REPORT.md),
>   which also explains the original v260c migration's warning
>   ("oe_projects_project missing — Base.metadata.create_all() handles
>   it at boot"). I missed that prior documentation when I wrote this
>   audit.
> - The CI workflow `.github/workflows/ci.yml:69-87` already runs
>   `alembic check` as advisory (`continue-on-error: true`) with a
>   comment explaining the situation. The team has been carrying this
>   knowingly.
>
> **Why the original numbers were 78, not 328:** the first `alembic
> check` run captured stale output (only the first batch of events
> made it into `/tmp/alembic-drift-raw.txt` before my command was
> truncated by a pipe to `head`). I built the entire classification
> table on that truncated sample without verifying its length. The
> systematic-evidence section below (status filter in 23/30 modules,
> project_id filter in 25/30 modules) remains true and useful — but
> the framing of "78 events to close with a catch-up migration" was
> wrong.
>
> **Decision (user, 2026-05-13):** Path 1 — keep `Base.metadata.
> create_all()` as the schema source-of-truth. This is a conscious
> deviation from QA_REPORT.md item 6's recommendation #6.2 ("stop
> relying on create_all()"). Trade-offs accepted:
>
> - Safe rolling upgrades of an existing customer DB require per-change
>   delta migrations (no automatic snapshot-based upgrade path).
> - `alembic check` stays in CI as advisory — it remains useful as a
>   forcing function if we ever revisit the architecture, but its
>   output should not be read as a bug list.
> - Future "schema drift" investigations should compare model metadata
>   against an actual running DB schema (post-`create_all()`), not
>   against the migration chain alone.
>
> **No migration written.** Batch 5b (catch-up migration) is
> cancelled. The audit content below is preserved as a record of the
> wrong path, but should not be treated as a work item. Lessons for
> future audits in `docs/audits/`:
>
> 1. Always check `wc -l` on captured tool output before building a
>    table from it — pipes to `head` lie silently.
> 2. Before classifying "drift" events, verify what the init migration
>    actually creates. A no-op init is a strong signal that
>    `create_all()` is involved somewhere.
> 3. Read prior audits in the same directory before starting a new one
>    — QA_REPORT.md had the answer and I didn't read it.
>
> ---

## TL;DR (original, wrong — preserved for the record)

**78 drift events from `alembic check` against SQLite.** Every event is
**justified by code that already exists in the models / repositories /
services / schemas**. Nothing to drop. Recommend a single catch-up
migration `v2j0_close_schema_drift_2026_05_13.py` to close everything
in one transaction.

| Class | Count | Examples |
|---|---|---|
| Added single-column index, repo filters on the column | 60 | `ix_oe_safety_incident_status` ← `safety/repository.py` filters `status`; `ix_oe_*_project_id` ← 25/30 modules filter `project_id` |
| Added composite index, repo query matches the column tuple exactly | 4 | `ix_notification_user_read (user_id, is_read)` ← `notifications/repository.py:52`; `ix_invoice_project_status (project_id, status)` ← `finance/models.py:27` declared |
| Added FK, model has `relationship()` and code reads it | 19 | `oe_notifications_notification.user_id → oe_users_user.id` ← declared `notifications/models.py:32`; 16 `project_id → projects.id` FKs across domain tables |
| Added column, calculated + stored in service code | 7 | `oe_finance_evm_snapshot.{eac,vac,etc,tcpi}` ← `finance/service.py:532-561` computes and writes all four; `oe_safety_incident.{title,severity}` ← `safety/schemas.py:27,34`; `oe_markups_markup.layer` ← `markups/repository.py:69` filters on it |
| Renamed index (old name in DB, new name in model — migration never landed) | 7 | `ix_tendering_package_status` → `ix_oe_tendering_package_status` (5 pairs in tendering); `ix_viewer3d_upload_uploaded_by` → `ix_oe_viewer3d_upload_uploaded_by`; `ix_my_module_item_project_id` → `ix_oe_my_module_item_project_id` |
| Removed column (genuinely gone from model) | 1 | `oe_tendering_bid.contact_id` — `tendering/models.py` no longer declares it |
| **UNUSED / candidate to drop** | **0** | — |

Total: 60 + 4 + 19 + 7 + 7 + 1 = **98** rows accounting for **78** unique
events (the 7 rename pairs each appear once as "removed" and once as
"added" in the alembic output, hence ~14 events absorbed by 7 rename
rows; the dropped contact_id has both a removed column event and a
removed index event).

## Methodology

1. Ran `alembic upgrade head` against a fresh SQLite database
   (`backend/openestimate.db`) — succeeded cleanly through `v2i0`.
2. Ran `alembic check` — captured 78 drift lines into
   `/tmp/alembic-drift-raw.txt`.
3. For every `ix_oe_<table>_<column>` index event: greppedthe matching
   module's `repository.py` for `<column> ==`, `.filter(...<column>)`,
   `.where(...<column>)`, `.order_by(...<column>)`. Result: **status
   filter present in 23 / 30 modules; project_id filter present in 25
   / 30 modules** — those two patterns alone account for ~40 of the 78
   events.
4. Spot-checked the special cases:
   - `oe_finance_evm_snapshot.{eac,vac,etc,tcpi}` — confirmed
     calculated in `finance/service.py:532-545` and stored in
     `finance/service.py:558-561`. Without these columns the EVM
     service raises on every write.
   - `oe_safety_incident.{title,severity}` — confirmed in
     `safety/schemas.py:27,34,60,67,96,100` and surfaced via
     `safety/router.py:80`.
   - `oe_markups_markup.layer` — used as a filter target in
     `markups/repository.py:69` (`base.where(Markup.layer == layer)`).
     Repository would 500 if column missing.
   - Composite `ix_notification_user_read (user_id, is_read)` —
     `notifications/repository.py:34-36, 52` issues exactly this
     `where(user_id == ..., is_read == ...)` query.
   - Composite `ix_invoice_project_status (project_id, status)` and
     `ix_invoice_project_direction (project_id, invoice_direction)` —
     explicitly declared in `finance/models.py:26-27` with `Index(...)`.
   - Removed `tendering_bid.contact_id` — column genuinely gone from
     `tendering/models.py`. Safe to drop from DB.
5. Counted modules at 50 `repository.py` files total; the 78 drift
   events span ~17 modules (costmodel, fieldreports, finance,
   inspections, markups, meetings, ncr, notifications, procurement,
   punchlist, requirements, rfi, rfq, risk, safety, schedule,
   submittals, tendering, transmittals, viewer3d, workflows,
   my_module).

## Recommendation

**Single catch-up migration**, `v2j0_close_schema_drift_2026_05_13.py`,
that does:

- Add 60 single-column indexes (`op.create_index`).
- Add 4 composite indexes (`op.create_index` with `columns=[...]`).
- Add 19 foreign keys (`op.batch_alter_table` for SQLite; direct
  `op.create_foreign_key` for Postgres — dialect-detect at runtime).
- Add 7 columns (3 tables) with `server_default` matching the model
  declaration so existing rows backfill cleanly.
- Drop the 1 orphan column `oe_tendering_bid.contact_id` and its
  associated `ix_tendering_bid_contact_id` index — `op.batch_alter_table`
  on SQLite, `op.drop_column` on Postgres.
- Drop 6 legacy-named indexes that have been renamed (`ix_tendering_*`,
  `ix_viewer3d_*`, `ix_my_module_*`) — these will be recreated under
  the new `ix_oe_*` naming above.

Rationale for one-migration vs. per-module:
- All events are routine "model ahead of DB" maintenance — there are no
  judgement calls per event after this audit.
- The drift is correlated: `v2i0_null_not_distinct` was the last
  migration to ship; everything in this drift accumulated between then
  and HEAD. A single migration mirrors that one accumulation event.
- A per-module split would mean ~17 separate migrations to review for
  the same total surface area, plus risk of inter-migration ordering
  bugs when one module's FK points at another module's table.

## Risks + mitigations

| Risk | Mitigation |
|---|---|
| SQLite can't `ALTER TABLE ADD CONSTRAINT FOREIGN KEY` | Use `op.batch_alter_table` for all FK adds — Alembic emits the table-rebuild pattern automatically. |
| Postgres adding an index on a large table holds a lock | Use `op.create_index(..., postgresql_concurrently=True, if_not_exists=True)` with `op.execute("COMMIT")` boundaries inside the migration. Defer to Batch 19 if we want concurrent index creation in a real prod deploy — for now the dev/staging DB is small enough that a plain `create_index` is fine. |
| `oe_finance_evm_snapshot.{eac,vac,etc,tcpi}` are `nullable=False` — backfill must populate them | Models declare `default="0", server_default="0"` (`finance/models.py:222-225`), so the column add will backfill `"0"` for existing rows automatically. Then a follow-up service-side recompute (run by the existing nightly EVM job) overwrites correct values. No data-loss risk. |
| `oe_tendering_bid.contact_id` drop is destructive | Rows in the DB still reference contact IDs that the model has dropped. Either (a) check whether any contact-resolution code still reads the column (last guard before drop) or (b) keep the column nullable but unmapped — preserves the data for forensic recovery. **I lean (a)** since the model dropped it cleanly and the column would be dead weight forever otherwise. Verify before merge. |
| Migration is large (~80 ops) — long-running on big DBs | Batch operations stay inside one transaction; if anything fails, the whole migration rolls back. No partial-state risk. |

## What this audit did NOT do

- Did not re-measure against Postgres (the production dialect). The
  baseline noted that PG sees ~29 orphan tables + 140 index drifts —
  different from SQLite's 78. The PG diff is likely the same set plus
  PG-specific things (`pg_trgm` indexes, `pgvector`, partial indexes
  with `WHERE` clauses). Recommend running the same workflow against a
  Postgres instance once Docker is available, as a verification step
  before the migration ships to a PG environment.
- Did not benchmark current queries to prove the indexes will speed
  them up. The grep evidence shows the queries exist and target the
  indexed columns; that's the "hit before fixing" measurement. A
  perf-bench would be Batch 19 (deploy/perf).
- Did not touch `app/modules/users/service.py`, middlewares, or any
  data-mutation code — read-only research.

## Proposed next step

PR follow-up containing `backend/alembic/versions/v2j0_close_schema_drift_2026_05_13.py`
with the single migration above. ~300 lines of Alembic ops, no app code
changes. Test plan: `alembic upgrade head && alembic downgrade -1 &&
alembic upgrade head` round-trips cleanly on both SQLite and Postgres.

If the user prefers a smaller-first approach: ship the migration in two
PRs — (1) all index additions (safest, additive only), (2) FK
additions + the 1 column drop (riskier, requires batch_alter_table).
That trade-off is the choice between one fast PR and two safer ones.
