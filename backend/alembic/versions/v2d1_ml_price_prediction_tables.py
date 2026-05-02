"""add ml_price_prediction tables

Creates two tables behind the ML Price-Prediction module:

* ``oe_ml_price_prediction_model``      — registered trained models
* ``oe_ml_price_prediction_prediction`` — cached prediction results

Revision ID: v2d1_ml_price_prediction_tables
Revises: v2d0_sustainability_tables
Create Date: 2026-05-02

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "v2d1_ml_price_prediction_tables"
down_revision: str | None = "v2d0_sustainability_tables"
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
        "oe_ml_price_prediction_model",
        _pk(),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("version", sa.String(32), nullable=False, server_default="1.0.0"),
        sa.Column(
            "algorithm",
            sa.String(64),
            nullable=False,
            server_default="LinearRegression",
        ),
        sa.Column(
            "feature_columns",
            sa.JSON(),
            nullable=False,
            server_default="[]",
        ),
        sa.Column(
            "target_column",
            sa.String(64),
            nullable=False,
            server_default="price",
        ),
        sa.Column("artifact_path", sa.String(512), nullable=False, server_default=""),
        sa.Column("metrics", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("sample_size", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("notes", sa.Text(), nullable=False, server_default=""),
        *_timestamps(),
    )
    _create_if_not_exists(
        "oe_ml_price_prediction_prediction",
        _pk(),
        sa.Column(
            "model_id",
            sa.String(36),
            sa.ForeignKey("oe_ml_price_prediction_model.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "project_id",
            sa.String(36),
            sa.ForeignKey("oe_projects_project.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("features", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("predicted_price", sa.Numeric(16, 4), nullable=False),
        sa.Column("confidence", sa.Numeric(6, 4), nullable=True),
        *_timestamps(),
    )

    bind = op.get_bind()
    insp = sa.inspect(bind)
    for tbl, idx_col in [
        ("oe_ml_price_prediction_model", "name"),
        ("oe_ml_price_prediction_prediction", "model_id"),
        ("oe_ml_price_prediction_prediction", "project_id"),
    ]:
        idx_name = f"ix_{tbl}_{idx_col}"
        existing = {ix["name"] for ix in insp.get_indexes(tbl)}
        if idx_name not in existing:
            op.create_index(idx_name, tbl, [idx_col])


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    for tbl in (
        "oe_ml_price_prediction_prediction",
        "oe_ml_price_prediction_model",
    ):
        if tbl in insp.get_table_names():
            op.drop_table(tbl)
