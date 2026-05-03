#!/usr/bin/env sh
# NEXUS Precon backend — Docker entrypoint.
#
# Bootstrap order on a fresh database:
#   1. Import every OCERP + precon model so SQLAlchemy registers them
#      with Base.metadata.  (Mirrors app/main.py:1431-1481 verbatim,
#      plus app.modules.precon.models for our additions.)
#   2. Base.metadata.create_all(engine) — idempotent, creates only
#      tables that don't yet exist.  This catches tables OCERP has no
#      explicit Alembic migration for (notably oe_documents_document,
#      which is FK-referenced by ffe3f561e2c1_add_documents_bim_link_table.py
#      but never created by any migration).  Without this step the
#      migration chain crashes on a fresh PG volume.
#   3. Detect first deploy via the alembic_version table:
#        absent  → alembic stamp head  (lock revision without replay)
#        present → alembic upgrade head (no-op or apply new revisions)
#   4. exec uvicorn.
#
# This pattern matches what OCERP's own startup hook does at
# main.py:1428-1497, just shifted to BEFORE uvicorn so the migration
# step and uvicorn both see a fully-bootstrapped schema.
#
# CONVENTION going forward (documented in PHASE_7_3_REPORT.md):
#   ANY new precon migration MUST use IF NOT EXISTS guards (mirror the
#   _create_if_not_exists / _has_column / _create_index_if_not_exists
#   helpers in v2g0_nexus_precon_init.py).  This keeps the
#   create_all + alembic upgrade flow conflict-free in perpetuity.
set -e

echo "[entrypoint] Step 1/4: registering models + create_all (mirrors main.py:1428-1497)"

python - <<'PYEOF'
import importlib
import os
import sys

# Mirrors app/main.py:1431-1481 verbatim, plus app.modules.precon.models.
# Each import triggers SQLAlchemy table registration on Base.metadata.
MODEL_MODULES = [
    "app.core.audit",
    "app.modules.ai.models",
    "app.modules.assemblies.models",
    "app.modules.bim_hub.models",
    "app.modules.bim_requirements.models",
    "app.modules.boq.models",
    "app.modules.catalog.models",
    "app.modules.cde.models",
    "app.modules.changeorders.models",
    "app.modules.collaboration.models",
    "app.modules.collaboration_locks.models",
    "app.modules.contacts.models",
    "app.modules.correspondence.models",
    "app.modules.costmodel.models",
    "app.modules.costs.models",
    "app.modules.documents.models",
    "app.modules.dwg_takeoff.models",
    "app.modules.enterprise_workflows.models",
    "app.modules.erp_chat.models",
    "app.modules.fieldreports.models",
    "app.modules.finance.models",
    "app.modules.full_evm.models",
    "app.modules.i18n_foundation.models",
    "app.modules.inspections.models",
    "app.modules.integrations.models",
    "app.modules.markups.models",
    "app.modules.meetings.models",
    "app.modules.ncr.models",
    "app.modules.notifications.models",
    "app.modules.procurement.models",
    "app.modules.projects.models",
    "app.modules.punchlist.models",
    "app.modules.reporting.models",
    "app.modules.requirements.models",
    "app.modules.rfi.models",
    "app.modules.rfq_bidding.models",
    "app.modules.risk.models",
    "app.modules.safety.models",
    "app.modules.schedule.models",
    "app.modules.submittals.models",
    "app.modules.takeoff.models",
    "app.modules.tasks.models",
    "app.modules.teams.models",
    "app.modules.tendering.models",
    "app.modules.transmittals.models",
    "app.modules.users.models",
    "app.modules.validation.models",
    # NEXUS Precon — our module (Phase 7.1 integration)
    "app.modules.precon.models",
]

skipped = []
for mod_name in MODEL_MODULES:
    try:
        importlib.import_module(mod_name)
    except Exception as exc:
        skipped.append(mod_name)
        print(f"[bootstrap] WARN: {mod_name} import failed: {exc!s}", file=sys.stderr)

print(
    f"[bootstrap] imported {len(MODEL_MODULES) - len(skipped)} model modules"
    f" ({len(skipped)} skipped)"
)

sync_url = os.environ.get("DATABASE_SYNC_URL")
if not sync_url:
    print("[bootstrap] ERROR: DATABASE_SYNC_URL is not set", file=sys.stderr)
    sys.exit(1)

from sqlalchemy import create_engine, inspect

from app.database import Base

engine = create_engine(sync_url, future=True)

print("[bootstrap] running Base.metadata.create_all (idempotent)...")
Base.metadata.create_all(engine)
print(f"[bootstrap] create_all complete — {len(Base.metadata.tables)} tables registered")

# Detect first deploy via alembic_version table presence.  Alembic creates
# this table itself on first stamp/upgrade — its absence after create_all
# means we have never run alembic against this DB.
inspector = inspect(engine)
has_alembic_table = "alembic_version" in inspector.get_table_names()
print(f"[bootstrap] alembic_version table present: {has_alembic_table}")

with open("/tmp/alembic_state.txt", "w") as f:
    f.write("yes" if has_alembic_table else "no")

engine.dispose()
PYEOF

ALEMBIC_STATE=$(cat /tmp/alembic_state.txt 2>/dev/null || echo "no")

if [ "$ALEMBIC_STATE" = "no" ]; then
  echo "[entrypoint] Step 2/4: first deploy — stamping alembic to head (no migration replay)"
  alembic stamp head
else
  echo "[entrypoint] Step 2/4: alembic_version present — running upgrade head (idempotent)"
  alembic upgrade head
fi

PORT_TO_USE="${PORT:-8000}"
echo "[entrypoint] Step 3/4: bootstrap + alembic complete"
echo "[entrypoint] Step 4/4: starting uvicorn on 0.0.0.0:${PORT_TO_USE}"
exec uvicorn app.main:create_app \
    --factory \
    --host 0.0.0.0 \
    --port "${PORT_TO_USE}" \
    --proxy-headers \
    --forwarded-allow-ips='*'
