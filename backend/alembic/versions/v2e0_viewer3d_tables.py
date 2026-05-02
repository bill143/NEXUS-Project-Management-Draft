"""add viewer3d upload table

Creates ``oe_viewer3d_upload`` for the 3D viewer module's upload metadata.

Revision ID: v2e0_viewer3d_tables
Revises: v2d1_ml_price_prediction_tables
Create Date: 2026-05-02

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "v2e0_viewer3d_tables"
down_revision: str | None = "v2d1_ml_price_prediction_tables"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _create_if_not_exists(table_name: str, *columns: sa.Column, **kw) -> None:  # noqa: ANN003
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if table_name not in insp.get_table_names():
        op.create_table(table_name, *columns, **kw)


def upgrade() -> None:
    _create_if_not_exists(
        "oe_viewer3d_upload",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("original_name", sa.String(512), nullable=False),
        sa.Column(
            "mime",
            sa.String(128),
            nullable=False,
            server_default="application/octet-stream",
        ),
        sa.Column("extension", sa.String(16), nullable=False, server_default=""),
        sa.Column("size_bytes", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("stored_path", sa.String(1024), nullable=False),
        sa.Column(
            "uploaded_by",
            sa.String(36),
            sa.ForeignKey("oe_users_user.id", ondelete="SET NULL"),
            nullable=True,
        ),
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
    )

    bind = op.get_bind()
    insp = sa.inspect(bind)
    existing = {ix["name"] for ix in insp.get_indexes("oe_viewer3d_upload")}
    if "ix_viewer3d_upload_uploaded_by" not in existing:
        op.create_index(
            "ix_viewer3d_upload_uploaded_by",
            "oe_viewer3d_upload",
            ["uploaded_by"],
        )


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if "oe_viewer3d_upload" in insp.get_table_names():
        try:
            op.drop_index("ix_viewer3d_upload_uploaded_by", table_name="oe_viewer3d_upload")
        except Exception:
            pass
        op.drop_table("oe_viewer3d_upload")
