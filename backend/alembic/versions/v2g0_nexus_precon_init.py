"""NEXUS Precon Module — initial schema

Implements the locked architectural decisions from:
    C:\\dev\\NEXUS_Relay\\precon_preflight\\00_BUILD_CONTRACT_LOCKED.md

Locked decisions implemented by this migration:
    SC-02  — oe_nexus_precon_prequalification_event
             Append-only prequalification audit trail linked to oe_contacts_contact.
    SC-03  — oe_tendering_bid.contact_id (nullable FK)
             Backward-compatible column linking bid submissions to a Contact record.
    SC-04  — oe_nexus_precon_rfq_invitation
             Junction table replacing the JSON issued_to_contacts field in oe_rfq_rfq;
             tracks 8-state invitation lifecycle per contact per RFQ.
    F4-01  — oe_nexus_precon_bid_level
             Bid leveling snapshots with JSONB adjustments for apples-to-apples
             comparison; append-only audit records.
    F4-02  — oe_nexus_precon_stage_event
             Append-only audit trail of all 8-state opportunity stage transitions
             enforced by pipeline_service.py.
             oe_nexus_precon_opportunity_cache
             Local cache of GovTribe federal opportunities; prevents duplicate
             project creation via promoted_to_project_id idempotency guard.
    A1     — oe_contacts_contact.is_bidder, oe_contacts_contact.is_subcontractor
             Concern #4 acceptance: single contact record carries role lifecycle.
             Both flags coexist; service layer auto-flips on award.

New tables (5):
    oe_nexus_precon_stage_event
    oe_nexus_precon_bid_level
    oe_nexus_precon_opportunity_cache
    oe_nexus_precon_prequalification_event
    oe_nexus_precon_rfq_invitation

Modified tables (2):
    oe_tendering_bid    — adds nullable contact_id FK column (SC-03)
    oe_contacts_contact — adds is_bidder, is_subcontractor flags (Amendment A1)

Status field conventions (String, service-layer enforced):
    rfq_invitation.status:
        INVITED | VIEWED | ACCEPTED | SUBMITTED | DECLINED | IGNORED | AWARDED | NOT_AWARDED
    prequalification_event.to_status / from_status:
        pending | in_review | approved | rejected | expired
    stage_event.from_stage / to_stage:
        identified | triaged | qualified | bidding | submitted | awarded | lost | no_bid

PROTECTED ZONES — this migration does NOT touch:
    - Any existing table beyond the 2 approved modifications above
    - Any existing migration file
    - Any existing model file

Revision ID: v2g0_nexus_precon_init
Revises: v2f0_pipeline_runs_extension
Create Date: 2026-05-03

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# ---------------------------------------------------------------------------
# Alembic revision chain
# ---------------------------------------------------------------------------
revision: str = "v2g0_nexus_precon_init"
down_revision: str | None = "v2f0_pipeline_runs_extension"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


# ---------------------------------------------------------------------------
# Helpers — idempotency guards matching OCERP convention (v2e0 / v2f0)
# ---------------------------------------------------------------------------

def _table_exists(table: str) -> bool:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    return table in insp.get_table_names()


def _has_column(table: str, column: str) -> bool:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if not _table_exists(table):
        return False
    return any(c["name"] == column for c in insp.get_columns(table))


def _has_index(table: str, index_name: str) -> bool:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if not _table_exists(table):
        return False
    return any(ix["name"] == index_name for ix in insp.get_indexes(table))


def _create_if_not_exists(table_name: str, *columns, **kw) -> None:
    if not _table_exists(table_name):
        op.create_table(table_name, *columns, **kw)


def _create_index_if_not_exists(index_name: str, table_name: str, columns: list, **kw) -> None:
    if not _has_index(table_name, index_name):
        op.create_index(index_name, table_name, columns, **kw)


def _drop_index_if_exists(index_name: str, table_name: str) -> None:
    if _has_index(table_name, index_name):
        try:
            op.drop_index(index_name, table_name=table_name)
        except Exception:  # noqa: BLE001 — best-effort on legacy SQLite
            pass


def _drop_table_if_exists(table_name: str) -> None:
    if _table_exists(table_name):
        op.drop_table(table_name)


# ---------------------------------------------------------------------------
# Table names — constants to avoid typos in downgrade()
# ---------------------------------------------------------------------------
T_STAGE_EVENT    = "oe_nexus_precon_stage_event"
T_BID_LEVEL      = "oe_nexus_precon_bid_level"
T_OPP_CACHE      = "oe_nexus_precon_opportunity_cache"
T_PREQUAL_EVENT  = "oe_nexus_precon_prequalification_event"
T_RFQ_INVITATION = "oe_nexus_precon_rfq_invitation"
T_TENDERING_BID  = "oe_tendering_bid"
T_CONTACTS       = "oe_contacts_contact"


# ---------------------------------------------------------------------------
# upgrade()
# ---------------------------------------------------------------------------

def upgrade() -> None:

    # ── 1. oe_nexus_precon_stage_event ──────────────────────────────────────
    # Append-only audit log of every opportunity stage transition.
    # project_id FK → oe_projects_project.id (SET NULL on project delete so
    # audit history is preserved even if the project is archived).
    _create_if_not_exists(
        T_STAGE_EVENT,
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "project_id",
            sa.String(36),
            sa.ForeignKey("oe_projects_project.id", ondelete="SET NULL"),
            nullable=True,   # nullable so rows survive project deletion
        ),
        sa.Column("from_stage", sa.String(50), nullable=True),   # NULL on first transition (initial state)
        sa.Column("to_stage", sa.String(50), nullable=False),
        sa.Column(
            "changed_by",
            sa.String(36),
            sa.ForeignKey("oe_users_user.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column(
            "timestamp",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
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
    _create_index_if_not_exists(
        "ix_precon_stage_event_project_id",
        T_STAGE_EVENT,
        ["project_id"],
    )
    _create_index_if_not_exists(
        "ix_precon_stage_event_changed_by",
        T_STAGE_EVENT,
        ["changed_by"],
    )
    # Composite index for audit queries: all events for a project, ordered by time
    _create_index_if_not_exists(
        "ix_precon_stage_event_project_timestamp",
        T_STAGE_EVENT,
        ["project_id", "timestamp"],
    )

    # ── 2. oe_nexus_precon_bid_level ─────────────────────────────────────────
    # Bid leveling snapshots — append-only; service layer blocks DELETE/UPDATE.
    # package_id FK → oe_tendering_package.id
    # bidder_contact_id FK → oe_contacts_contact.id
    # leveled_by FK → oe_users_user.id
    _create_if_not_exists(
        T_BID_LEVEL,
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "package_id",
            sa.String(36),
            sa.ForeignKey("oe_tendering_package.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "bidder_contact_id",
            sa.String(36),
            sa.ForeignKey("oe_contacts_contact.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("raw_amount", sa.Numeric(20, 4), nullable=False, server_default="0"),
        # adjustments: JSONB on PG; JSON on SQLite — list of
        # {"label": str, "amount": decimal, "reason": str, "applied_at": iso_str}
        sa.Column("adjustments", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("adjusted_amount", sa.Numeric(20, 4), nullable=False, server_default="0"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("is_winner", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column(
            "leveled_by",
            sa.String(36),
            sa.ForeignKey("oe_users_user.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "leveled_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
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
    _create_index_if_not_exists(
        "ix_precon_bid_level_package_id",
        T_BID_LEVEL,
        ["package_id"],
    )
    _create_index_if_not_exists(
        "ix_precon_bid_level_bidder_contact_id",
        T_BID_LEVEL,
        ["bidder_contact_id"],
    )
    _create_index_if_not_exists(
        "ix_precon_bid_level_leveled_by",
        T_BID_LEVEL,
        ["leveled_by"],
    )
    _create_index_if_not_exists(
        "ix_precon_bid_level_is_winner",
        T_BID_LEVEL,
        ["package_id", "is_winner"],
    )

    # ── 3. oe_nexus_precon_opportunity_cache ─────────────────────────────────
    # Local cache of GovTribe federal opportunities.
    # promoted_to_project_id: nullable FK — NULL until promoted; idempotency guard.
    _create_if_not_exists(
        T_OPP_CACHE,
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("govtribe_external_id", sa.String(255), nullable=False),
        sa.Column("solicitation_number", sa.String(255), nullable=True),
        # payload: full GovTribe opportunity JSON blob
        sa.Column("payload", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column(
            "last_synced_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "promoted_to_project_id",
            sa.String(36),
            sa.ForeignKey("oe_projects_project.id", ondelete="SET NULL"),
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
    # Lookup indexes — adapter fetches by external_id to enforce idempotency
    _create_index_if_not_exists(
        "ix_precon_opp_cache_govtribe_external_id",
        T_OPP_CACHE,
        ["govtribe_external_id"],
        unique=True,
    )
    _create_index_if_not_exists(
        "ix_precon_opp_cache_solicitation_number",
        T_OPP_CACHE,
        ["solicitation_number"],
    )
    _create_index_if_not_exists(
        "ix_precon_opp_cache_promoted_to_project_id",
        T_OPP_CACHE,
        ["promoted_to_project_id"],
    )
    _create_index_if_not_exists(
        "ix_precon_opp_cache_last_synced_at",
        T_OPP_CACHE,
        ["last_synced_at"],
    )

    # ── 4. oe_nexus_precon_prequalification_event ────────────────────────────
    # Append-only federal-compliant prequalification audit trail.
    # contact_id FK → oe_contacts_contact.id
    # changed_by FK → oe_users_user.id
    # from_status / to_status: String(50), values enforced at service layer:
    #   pending | in_review | approved | rejected | expired
    _create_if_not_exists(
        T_PREQUAL_EVENT,
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "contact_id",
            sa.String(36),
            sa.ForeignKey("oe_contacts_contact.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("from_status", sa.String(50), nullable=True),  # NULL on first event
        sa.Column("to_status", sa.String(50), nullable=False),
        sa.Column(
            "changed_by",
            sa.String(36),
            sa.ForeignKey("oe_users_user.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "timestamp",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
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
    _create_index_if_not_exists(
        "ix_precon_prequal_event_contact_id",
        T_PREQUAL_EVENT,
        ["contact_id"],
    )
    _create_index_if_not_exists(
        "ix_precon_prequal_event_changed_by",
        T_PREQUAL_EVENT,
        ["changed_by"],
    )
    _create_index_if_not_exists(
        "ix_precon_prequal_event_contact_timestamp",
        T_PREQUAL_EVENT,
        ["contact_id", "timestamp"],
    )

    # ── 5. oe_nexus_precon_rfq_invitation ────────────────────────────────────
    # Junction table: one row per (rfq, contact) pair.
    # Tracks 8-state invitation lifecycle — service layer enforces transitions.
    # Status values: INVITED | VIEWED | ACCEPTED | SUBMITTED |
    #                DECLINED | IGNORED | AWARDED | NOT_AWARDED
    # rfq_id FK → oe_rfq_rfq.id
    # contact_id FK → oe_contacts_contact.id
    _create_if_not_exists(
        T_RFQ_INVITATION,
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "rfq_id",
            sa.String(36),
            sa.ForeignKey("oe_rfq_rfq.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "contact_id",
            sa.String(36),
            sa.ForeignKey("oe_contacts_contact.id", ondelete="CASCADE"),
            nullable=False,
        ),
        # Status: String(50), service-layer enforced enum
        sa.Column(
            "status",
            sa.String(50),
            nullable=False,
            server_default="INVITED",
        ),
        sa.Column(
            "invited_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("last_viewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("responded_at", sa.DateTime(timezone=True), nullable=True),
        # metadata_: flexible blob for extension (portal tokens, webhook receipts, etc.)
        sa.Column("metadata_", sa.JSON(), nullable=False, server_default="{}"),
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
        # Unique constraint: one invitation record per (rfq, contact) pair
        sa.UniqueConstraint("rfq_id", "contact_id", name="uq_precon_rfq_invitation_rfq_contact"),
    )
    _create_index_if_not_exists(
        "ix_precon_rfq_invitation_rfq_id",
        T_RFQ_INVITATION,
        ["rfq_id"],
    )
    _create_index_if_not_exists(
        "ix_precon_rfq_invitation_contact_id",
        T_RFQ_INVITATION,
        ["contact_id"],
    )
    # Composite index for invitation queries: all invites for an RFQ filtered by status
    _create_index_if_not_exists(
        "ix_precon_rfq_invitation_rfq_status",
        T_RFQ_INVITATION,
        ["rfq_id", "status"],
    )

    # ── 6. oe_tendering_bid — add nullable contact_id FK (SC-03) ────────────
    # Backward-compatible: all existing rows keep contact_id = NULL.
    # Service layer populates on new bids; existing bids reconciled manually.
    if not _has_column(T_TENDERING_BID, "contact_id"):
        op.add_column(
            T_TENDERING_BID,
            sa.Column(
                "contact_id",
                sa.String(36),
                sa.ForeignKey("oe_contacts_contact.id", ondelete="SET NULL"),
                nullable=True,
            ),
        )
    _create_index_if_not_exists(
        "ix_tendering_bid_contact_id",
        T_TENDERING_BID,
        ["contact_id"],
    )

    # ── 7. oe_contacts_contact — add role flag columns (Amendment A1) ────────
    # Honors Concern #4 acceptance test:
    # Single contact record carries the role lifecycle.
    # is_bidder and is_subcontractor coexist — flags are additive, not exclusive.
    # All existing rows default to false (additive, backward-compatible per Domino Rule).
    if not _has_column(T_CONTACTS, "is_bidder"):
        op.add_column(
            T_CONTACTS,
            sa.Column(
                "is_bidder",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("false"),
            ),
        )

    if not _has_column(T_CONTACTS, "is_subcontractor"):
        op.add_column(
            T_CONTACTS,
            sa.Column(
                "is_subcontractor",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("false"),
            ),
        )

    # Indexes for query performance — Precon dashboards filter by these flags
    _create_index_if_not_exists(
        "ix_contacts_contact_is_bidder",
        T_CONTACTS,
        ["is_bidder"],
    )
    _create_index_if_not_exists(
        "ix_contacts_contact_is_subcontractor",
        T_CONTACTS,
        ["is_subcontractor"],
    )


# ---------------------------------------------------------------------------
# downgrade() — fully reversible; drops in strict reverse creation order
# ---------------------------------------------------------------------------

def downgrade() -> None:

    # ── 7 reversed: remove role flag columns from oe_contacts_contact (Amendment A1) ──
    _drop_index_if_exists("ix_contacts_contact_is_subcontractor", T_CONTACTS)
    _drop_index_if_exists("ix_contacts_contact_is_bidder", T_CONTACTS)

    if _has_column(T_CONTACTS, "is_subcontractor"):
        try:
            op.drop_column(T_CONTACTS, "is_subcontractor")
        except Exception:  # noqa: BLE001 — legacy SQLite < 3.35 best-effort
            pass

    if _has_column(T_CONTACTS, "is_bidder"):
        try:
            op.drop_column(T_CONTACTS, "is_bidder")
        except Exception:  # noqa: BLE001 — legacy SQLite < 3.35 best-effort
            pass

    # ── 6 reversed: remove contact_id from oe_tendering_bid ─────────────────
    _drop_index_if_exists("ix_tendering_bid_contact_id", T_TENDERING_BID)
    if _has_column(T_TENDERING_BID, "contact_id"):
        try:
            op.drop_column(T_TENDERING_BID, "contact_id")
        except Exception:  # noqa: BLE001 — legacy SQLite < 3.35 best-effort
            pass

    # ── 5 reversed: oe_nexus_precon_rfq_invitation ───────────────────────────
    _drop_index_if_exists("ix_precon_rfq_invitation_rfq_status", T_RFQ_INVITATION)
    _drop_index_if_exists("ix_precon_rfq_invitation_contact_id", T_RFQ_INVITATION)
    _drop_index_if_exists("ix_precon_rfq_invitation_rfq_id", T_RFQ_INVITATION)
    _drop_table_if_exists(T_RFQ_INVITATION)

    # ── 4 reversed: oe_nexus_precon_prequalification_event ───────────────────
    _drop_index_if_exists("ix_precon_prequal_event_contact_timestamp", T_PREQUAL_EVENT)
    _drop_index_if_exists("ix_precon_prequal_event_changed_by", T_PREQUAL_EVENT)
    _drop_index_if_exists("ix_precon_prequal_event_contact_id", T_PREQUAL_EVENT)
    _drop_table_if_exists(T_PREQUAL_EVENT)

    # ── 3 reversed: oe_nexus_precon_opportunity_cache ────────────────────────
    _drop_index_if_exists("ix_precon_opp_cache_last_synced_at", T_OPP_CACHE)
    _drop_index_if_exists("ix_precon_opp_cache_promoted_to_project_id", T_OPP_CACHE)
    _drop_index_if_exists("ix_precon_opp_cache_solicitation_number", T_OPP_CACHE)
    _drop_index_if_exists("ix_precon_opp_cache_govtribe_external_id", T_OPP_CACHE)
    _drop_table_if_exists(T_OPP_CACHE)

    # ── 2 reversed: oe_nexus_precon_bid_level ────────────────────────────────
    _drop_index_if_exists("ix_precon_bid_level_is_winner", T_BID_LEVEL)
    _drop_index_if_exists("ix_precon_bid_level_leveled_by", T_BID_LEVEL)
    _drop_index_if_exists("ix_precon_bid_level_bidder_contact_id", T_BID_LEVEL)
    _drop_index_if_exists("ix_precon_bid_level_package_id", T_BID_LEVEL)
    _drop_table_if_exists(T_BID_LEVEL)

    # ── 1 reversed: oe_nexus_precon_stage_event ──────────────────────────────
    _drop_index_if_exists("ix_precon_stage_event_project_timestamp", T_STAGE_EVENT)
    _drop_index_if_exists("ix_precon_stage_event_changed_by", T_STAGE_EVENT)
    _drop_index_if_exists("ix_precon_stage_event_project_id", T_STAGE_EVENT)
    _drop_table_if_exists(T_STAGE_EVENT)
