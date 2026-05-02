"""extend oe_job_run with pipeline tracking columns

Sweep B (DDC AI/LLM workflow port) — adds four nullable columns so a
pipeline run's metadata is queryable without a separate table:

    pipeline_name      Manifest name (alias of ``kind`` for pipeline rows;
                       NULL for non-pipeline jobs).
    llm_tier_used      Last LLMTier the dispatcher hit on this run
                       (``hard`` / ``classify`` / ``fallback``).
    total_tokens       Sum of provider-reported tokens across all
                       LLM calls in the run.
    total_cost_usd     Heuristic blended cost estimate per
                       :data:`app.core.pipelines.runtime._COST_PER_1K_TOKENS_USD`.
                       NUMERIC(12, 4) — five digits left of the decimal
                       is enough for any individual run we can imagine
                       in the next decade.

All columns are nullable so existing JobRun rows (and non-pipeline jobs)
continue to round-trip without backfill. Idempotent: each ``add_column``
call is gated on a column-presence check so re-running on a partially
migrated database is a no-op, matching the convention from v260.

Revision ID: v2f0_pipeline_runs_extension
Revises: v2e0_viewer3d_tables
Create Date: 2026-05-02

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "v2f0_pipeline_runs_extension"
down_revision: str | None = "v2e0_viewer3d_tables"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


TABLE_NAME = "oe_job_run"
PIPELINE_NAME_INDEX = "ix_oe_job_run_pipeline_name"


def _has_column(table: str, column: str) -> bool:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if table not in insp.get_table_names():
        return False
    return any(c["name"] == column for c in insp.get_columns(table))


def _has_index(table: str, index_name: str) -> bool:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if table not in insp.get_table_names():
        return False
    return any(ix["name"] == index_name for ix in insp.get_indexes(table))


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if TABLE_NAME not in insp.get_table_names():
        # JobRun table missing — earlier migration must run first; bail
        # quietly so the operator sees the upstream error not ours.
        return

    if not _has_column(TABLE_NAME, "pipeline_name"):
        op.add_column(
            TABLE_NAME,
            sa.Column("pipeline_name", sa.String(length=120), nullable=True),
        )
    if not _has_column(TABLE_NAME, "llm_tier_used"):
        op.add_column(
            TABLE_NAME,
            sa.Column("llm_tier_used", sa.String(length=20), nullable=True),
        )
    if not _has_column(TABLE_NAME, "total_tokens"):
        op.add_column(
            TABLE_NAME,
            sa.Column("total_tokens", sa.Integer, nullable=True),
        )
    if not _has_column(TABLE_NAME, "total_cost_usd"):
        op.add_column(
            TABLE_NAME,
            sa.Column("total_cost_usd", sa.Numeric(12, 4), nullable=True),
        )

    # Pipeline-name index — dashboards filter by pipeline far more often
    # than by raw kind once pipelines are in production.
    if not _has_index(TABLE_NAME, PIPELINE_NAME_INDEX):
        op.create_index(PIPELINE_NAME_INDEX, TABLE_NAME, ["pipeline_name"])


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if TABLE_NAME not in insp.get_table_names():
        return

    if _has_index(TABLE_NAME, PIPELINE_NAME_INDEX):
        op.drop_index(PIPELINE_NAME_INDEX, table_name=TABLE_NAME)

    # SQLite cannot DROP COLUMN before 3.35; the test DB is recent enough
    # that ``op.drop_column`` works in batch mode. Wrap in try/except so a
    # legacy SQLite still allows downgrade to land (column simply lingers).
    for col in ("total_cost_usd", "total_tokens", "llm_tier_used", "pipeline_name"):
        if _has_column(TABLE_NAME, col):
            try:
                op.drop_column(TABLE_NAME, col)
            except Exception:  # noqa: BLE001 — best-effort downgrade on legacy SQLite
                pass
