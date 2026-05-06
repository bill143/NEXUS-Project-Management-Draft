"""v2i0 — make uq_costs_code_region treat NULL regions as equal.

Postgres' default behavior is NULL != NULL inside unique constraints, so
the existing ``uq_costs_code_region`` silently allows duplicate
``(code, NULL)`` rows. The /import/file/ endpoint inserts every row
with ``region = NULL``, so historical failed imports could stack
duplicates and break ``CostItemRepository.get_by_code``'s existence
check (``MultipleResultsFound``).

Postgres 15+ supports ``UNIQUE NULLS NOT DISTINCT`` to opt into the
"NULL == NULL" behavior. This migration drops the old constraint and
recreates it with that semantics. SQLite (dev) is skipped — its UNIQUE
behavior with NULL is the same as Postgres' default, but the prod fix
is what matters and SQLite doesn't support the syntax.
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op


revision: str = "v2i0_cost_region_null_not_distinct"
down_revision: Union[str, Sequence[str], None] = "v2h0_merge_heads"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return
    op.execute("ALTER TABLE oe_costs_item DROP CONSTRAINT IF EXISTS uq_costs_code_region;")
    op.execute(
        "ALTER TABLE oe_costs_item "
        "ADD CONSTRAINT uq_costs_code_region "
        "UNIQUE NULLS NOT DISTINCT (code, region);"
    )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return
    op.execute("ALTER TABLE oe_costs_item DROP CONSTRAINT IF EXISTS uq_costs_code_region;")
    op.execute(
        "ALTER TABLE oe_costs_item "
        "ADD CONSTRAINT uq_costs_code_region "
        "UNIQUE (code, region);"
    )
