"""add my_module item table

Creates ``oe_my_module_item`` — Items owned by a project, used by the
``my_module`` example community module.

Idempotent ``CREATE TABLE IF NOT EXISTS`` style mirrors the recent
collab/lock and BIM migrations so re-runs against a dev SQLite DB
(where ``Base.metadata.create_all`` may already have created the
table) are safe.

Revision ID: v2c0_my_module_items
Revises: v2b0_preset_sync_columns
Create Date: 2026-05-02

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "v2c0_my_module_items"
down_revision: str | None = "v2b0_preset_sync_columns"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


# ---------------------------------------------------------------------------
# Helpers (mirrored from a1b2c3d4e5f6 / collab_lock migration)
# ---------------------------------------------------------------------------


def _create_if_not_exists(table_name: str, *columns: sa.Column, **kw) -> None:  # noqa: ANN003
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if table_name not in insp.get_table_names():
        op.create_table(table_name, *columns, **kw)


def _pk() -> sa.Column:
    return sa.Column("id", sa.String(36), primary_key=True)


def _timestamps() -> list[sa.Column]:
    return [
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    ]


def _meta() -> sa.Column:
    return sa.Column("metadata", sa.JSON, nullable=False, server_default="{}")


# ---------------------------------------------------------------------------
# Migration
# ---------------------------------------------------------------------------


def upgrade() -> None:
    _create_if_not_exists(
        "oe_my_module_item",
        _pk(),
        sa.Column(
            "project_id",
            sa.String(36),
            sa.ForeignKey("oe_projects_project.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        _meta(),
        *_timestamps(),
    )

    bind = op.get_bind()
    insp = sa.inspect(bind)
    existing = {ix["name"] for ix in insp.get_indexes("oe_my_module_item")}
    if "ix_my_module_item_project_id" not in existing:
        op.create_index(
            "ix_my_module_item_project_id", "oe_my_module_item", ["project_id"]
        )


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if "oe_my_module_item" in insp.get_table_names():
        try:
            op.drop_index("ix_my_module_item_project_id", table_name="oe_my_module_item")
        except Exception:
            pass
        op.drop_table("oe_my_module_item")
