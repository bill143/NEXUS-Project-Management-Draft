"""v2h0 — merge nexus-precon head with match-settings head.

Origin/main accumulated two parallel migration heads after the Precon
module was merged in PR #19:

* ``v282_match_cost_database_id`` — terminus of the cost-database / match
  settings chain (``v280_translation_cache`` → ``v281_match_project_settings``
  → ``v282_match_cost_database_id``).
* ``v2g0_nexus_precon_init`` — the Precon module's initial schema
  (continues from ``v2f0_pipeline_runs_extension``).

A fresh container starting via ``docker-entrypoint.sh`` runs
``alembic upgrade head`` and aborts with::

    ERROR: Multiple head revisions are present for given argument
    'head'; please specify a specific target revision,
    '<branchname>@head' to narrow to a specific head, or 'heads'
    for all heads

This empty merge migration unifies the two heads into a single tip so
``alembic upgrade head`` succeeds again on a fresh database.  No schema
changes — the two branches' tables are independent and don't conflict.
"""
from __future__ import annotations

from typing import Sequence, Union

# revision identifiers, used by Alembic.
revision: str = "v2h0_merge_heads"
down_revision: Union[str, Sequence[str], None] = (
    "v282_match_cost_database_id",
    "v2g0_nexus_precon_init",
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """No-op — the two parent branches don't conflict."""


def downgrade() -> None:
    """No-op — splitting back into two heads is a manual operation."""
