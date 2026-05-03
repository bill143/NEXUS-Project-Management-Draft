"""Precon ORM models.

Five tables, all prefixed ``oe_nexus_precon_*``:

    oe_nexus_precon_stage_event           — append-only opportunity-stage audit log
    oe_nexus_precon_bid_level             — append-only bid leveling snapshots
    oe_nexus_precon_opportunity_cache     — local cache of GovTribe federal opps
    oe_nexus_precon_prequalification_event — append-only prequal audit log
    oe_nexus_precon_rfq_invitation        — RFQ ↔ contact junction with 8-state lifecycle

Schema mirrors the v2g0_nexus_precon_init Alembic migration exactly.  Append-only
discipline (DELETE/UPDATE blocked) is enforced at the service layer, not in the
schema, to keep the ORM portable across PostgreSQL and SQLite.
"""

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import GUID, Base


class StageEvent(Base):
    """Append-only audit row for an opportunity stage transition.

    One row per call to ``pipeline_service.transition()``.  ``from_stage`` is
    nullable so the very first event for a project (initial state) can be
    recorded without inventing a synthetic predecessor.
    """

    __tablename__ = "oe_nexus_precon_stage_event"

    project_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(),
        ForeignKey("oe_projects_project.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    from_stage: Mapped[str | None] = mapped_column(String(50), nullable=True)
    to_stage: Mapped[str] = mapped_column(String(50), nullable=False)
    changed_by: Mapped[uuid.UUID | None] = mapped_column(
        GUID(),
        ForeignKey("oe_users_user.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<StageEvent {self.from_stage!r}->{self.to_stage!r} project={self.project_id}>"


class BidLevel(Base):
    """A normalized leveling snapshot for one bid against one tender package.

    Append-only.  Adjustments are stored as a JSON list of
    ``{"label", "amount", "reason", "applied_at"}`` entries; ``adjusted_amount``
    is the running total after every entry has been applied.
    """

    __tablename__ = "oe_nexus_precon_bid_level"

    package_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("oe_tendering_package.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    bidder_contact_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(),
        ForeignKey("oe_contacts_contact.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    raw_amount: Mapped[Decimal] = mapped_column(
        Numeric(20, 4),
        nullable=False,
        server_default="0",
        default=Decimal("0"),
    )
    adjustments: Mapped[list] = mapped_column(  # type: ignore[assignment]
        JSON,
        nullable=False,
        default=list,
        server_default="[]",
    )
    adjusted_amount: Mapped[Decimal] = mapped_column(
        Numeric(20, 4),
        nullable=False,
        server_default="0",
        default=Decimal("0"),
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_winner: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
    )
    leveled_by: Mapped[uuid.UUID | None] = mapped_column(
        GUID(),
        ForeignKey("oe_users_user.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    leveled_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<BidLevel package={self.package_id} adjusted={self.adjusted_amount} winner={self.is_winner}>"


class OpportunityCache(Base):
    """Local cache of a single GovTribe federal opportunity.

    ``promoted_to_project_id`` is the idempotency guard — non-null means the
    adapter has already created an OCERP project for this opportunity, so a
    re-promotion just returns the existing id.
    """

    __tablename__ = "oe_nexus_precon_opportunity_cache"

    govtribe_external_id: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    solicitation_number: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    payload: Mapped[dict] = mapped_column(  # type: ignore[assignment]
        JSON,
        nullable=False,
        default=dict,
        server_default="{}",
    )
    last_synced_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )
    promoted_to_project_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(),
        ForeignKey("oe_projects_project.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    def __repr__(self) -> str:
        return f"<OpportunityCache external={self.govtribe_external_id} promoted={self.promoted_to_project_id}>"


class PrequalificationEvent(Base):
    """Append-only audit row for a prequalification status change.

    ``from_status`` is nullable so the first event for a contact (e.g. moving
    from "no record" → ``pending``) can be recorded.
    """

    __tablename__ = "oe_nexus_precon_prequalification_event"

    contact_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("oe_contacts_contact.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    from_status: Mapped[str | None] = mapped_column(String(50), nullable=True)
    to_status: Mapped[str] = mapped_column(String(50), nullable=False)
    changed_by: Mapped[uuid.UUID | None] = mapped_column(
        GUID(),
        ForeignKey("oe_users_user.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<PrequalificationEvent contact={self.contact_id} {self.from_status!r}->{self.to_status!r}>"


class RFQInvitation(Base):
    """One row per (rfq, contact) pair tracking the 8-state invitation lifecycle.

    The status column is a plain ``String(50)``; the value set
    (INVITED|VIEWED|ACCEPTED|SUBMITTED|DECLINED|IGNORED|AWARDED|NOT_AWARDED)
    and the legal transitions between values are enforced by
    ``services/rfq_invitation_service.py`` so the schema stays portable.
    """

    __tablename__ = "oe_nexus_precon_rfq_invitation"
    __table_args__ = (
        UniqueConstraint("rfq_id", "contact_id", name="uq_precon_rfq_invitation_rfq_contact"),
    )

    rfq_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("oe_rfq_rfq.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    contact_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("oe_contacts_contact.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="INVITED",
        server_default="INVITED",
    )
    invited_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    last_viewed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    responded_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    metadata_: Mapped[dict] = mapped_column(  # type: ignore[assignment]
        "metadata_",
        JSON,
        nullable=False,
        default=dict,
        server_default="{}",
    )

    def __repr__(self) -> str:
        return f"<RFQInvitation rfq={self.rfq_id} contact={self.contact_id} status={self.status}>"
