"""add sustainability / CO₂ tables

Creates the three tables behind the sustainability module:

* ``oe_sustainability_epd``           — emission-factor catalog
* ``oe_sustainability_element_group`` — per-project element groups
* ``oe_sustainability_report``        — calculated carbon-footprint snapshots

Idempotent ``CREATE TABLE IF NOT EXISTS`` style mirrors v2c0 so re-runs
against a dev SQLite DB are safe.

Revision ID: v2d0_sustainability_tables
Revises: v2c0_my_module_items
Create Date: 2026-05-02

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "v2d0_sustainability_tables"
down_revision: str | None = "v2c0_my_module_items"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


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


def upgrade() -> None:
    _create_if_not_exists(
        "oe_sustainability_epd",
        _pk(),
        sa.Column("code", sa.String(64), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("material_category", sa.String(64), nullable=False),
        sa.Column("buy_clean_category", sa.String(64), nullable=True),
        sa.Column("unit", sa.String(16), nullable=False, server_default="m3"),
        sa.Column("factor_kgco2e", sa.Numeric(12, 4), nullable=False),
        sa.Column("region", sa.String(8), nullable=False, server_default="US"),
        sa.Column("source", sa.String(255), nullable=False, server_default=""),
        sa.Column("notes", sa.Text(), nullable=False, server_default=""),
        *_timestamps(),
    )
    _create_if_not_exists(
        "oe_sustainability_element_group",
        _pk(),
        sa.Column(
            "project_id",
            sa.String(36),
            sa.ForeignKey("oe_projects_project.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("material_category", sa.String(64), nullable=False),
        sa.Column("epd_code", sa.String(64), nullable=True),
        sa.Column("quantity", sa.Numeric(16, 4), nullable=False),
        sa.Column("unit", sa.String(16), nullable=False, server_default="m3"),
        sa.Column("metadata", sa.JSON(), nullable=False, server_default="{}"),
        *_timestamps(),
    )
    _create_if_not_exists(
        "oe_sustainability_report",
        _pk(),
        sa.Column(
            "project_id",
            sa.String(36),
            sa.ForeignKey("oe_projects_project.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "title",
            sa.String(255),
            nullable=False,
            server_default="Embodied Carbon Report",
        ),
        sa.Column(
            "total_kgco2e", sa.Numeric(16, 4), nullable=False, server_default="0"
        ),
        sa.Column("by_category", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column(
            "by_buy_clean_category", sa.JSON(), nullable=False, server_default="{}"
        ),
        sa.Column(
            "methodology",
            sa.String(64),
            nullable=False,
            server_default="GSA-P100-2023",
        ),
        sa.Column("notes", sa.Text(), nullable=False, server_default=""),
        *_timestamps(),
    )

    bind = op.get_bind()
    insp = sa.inspect(bind)
    for tbl, idx_col in [
        ("oe_sustainability_epd", "code"),
        ("oe_sustainability_epd", "material_category"),
        ("oe_sustainability_epd", "buy_clean_category"),
        ("oe_sustainability_element_group", "project_id"),
        ("oe_sustainability_element_group", "epd_code"),
        ("oe_sustainability_report", "project_id"),
    ]:
        idx_name = f"ix_{tbl}_{idx_col}"
        existing = {ix["name"] for ix in insp.get_indexes(tbl)}
        if idx_name not in existing:
            op.create_index(idx_name, tbl, [idx_col])


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    for tbl in (
        "oe_sustainability_report",
        "oe_sustainability_element_group",
        "oe_sustainability_epd",
    ):
        if tbl in insp.get_table_names():
            op.drop_table(tbl)
