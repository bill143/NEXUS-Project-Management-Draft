"""Precon data-access layer.

Pure data access — no business logic, no transaction management.  All queries
for the five ``oe_nexus_precon_*`` tables live here so the service layer never
constructs SQL inline.

Append-only discipline
----------------------
Three tables are append-only audit trails:

* ``oe_nexus_precon_stage_event``
* ``oe_nexus_precon_bid_level``
* ``oe_nexus_precon_prequalification_event``

For these tables the repository deliberately exposes no ``update`` or
``delete`` methods.  ``BidLevelRepository.set_winner_flag`` is the single
narrow exception — it's required by the leveling service to flip the
"current winner" pointer, but it never deletes a snapshot or rewrites the
audit fields (raw_amount, adjustments, leveled_by, leveled_at).
"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import and_, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.precon.models import (
    BidLevel,
    OpportunityCache,
    PrequalificationEvent,
    RFQInvitation,
    StageEvent,
)

# ── Stage events (append-only) ────────────────────────────────────────────


class StageEventRepository:
    """Read + insert access for the opportunity-stage audit log."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add(
        self,
        *,
        project_id: uuid.UUID | None,
        from_stage: str | None,
        to_stage: str,
        changed_by: uuid.UUID | None,
        reason: str | None = None,
    ) -> StageEvent:
        """Insert a new stage-transition event row."""
        event = StageEvent(
            project_id=project_id,
            from_stage=from_stage,
            to_stage=to_stage,
            changed_by=changed_by,
            reason=reason,
        )
        self.session.add(event)
        await self.session.flush()
        return event

    async def list_for_project(self, project_id: uuid.UUID) -> list[StageEvent]:
        """Return all stage events for a project, oldest first."""
        stmt = (
            select(StageEvent)
            .where(StageEvent.project_id == project_id)
            .order_by(StageEvent.timestamp.asc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def latest_for_project(self, project_id: uuid.UUID) -> StageEvent | None:
        stmt = (
            select(StageEvent)
            .where(StageEvent.project_id == project_id)
            .order_by(StageEvent.timestamp.desc())
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()


# ── Bid leveling (append-only with narrow winner-flag flip) ───────────────


class BidLevelRepository:
    """Read + insert access for bid-leveling snapshots.

    The winner flag flip in :meth:`set_winner_flag` is the sole mutation; it
    only touches the boolean and never rewrites the snapshot's audit fields.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, level_id: uuid.UUID) -> BidLevel | None:
        return await self.session.get(BidLevel, level_id)

    async def add(
        self,
        *,
        package_id: uuid.UUID,
        bidder_contact_id: uuid.UUID | None,
        raw_amount,
        adjustments: list,
        adjusted_amount,
        notes: str | None,
        leveled_by: uuid.UUID | None,
    ) -> BidLevel:
        """Insert a fresh leveling snapshot row."""
        level = BidLevel(
            package_id=package_id,
            bidder_contact_id=bidder_contact_id,
            raw_amount=raw_amount,
            adjustments=list(adjustments or []),
            adjusted_amount=adjusted_amount,
            notes=notes,
            is_winner=False,
            leveled_by=leveled_by,
        )
        self.session.add(level)
        await self.session.flush()
        return level

    async def list_for_package(self, package_id: uuid.UUID) -> list[BidLevel]:
        stmt = (
            select(BidLevel)
            .where(BidLevel.package_id == package_id)
            .order_by(BidLevel.leveled_at.asc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def set_winner_flag(self, *, package_id: uuid.UUID, level_id: uuid.UUID) -> None:
        """Flip the winner flag so only ``level_id`` is winner for this package.

        This is intentionally the only mutation exposed by this repository:
        it sets every other row to ``is_winner=False`` and the chosen row
        to ``is_winner=True``.  All other audit fields stay untouched.
        """
        clear = (
            update(BidLevel)
            .where(BidLevel.package_id == package_id, BidLevel.id != level_id)
            .values(is_winner=False)
        )
        await self.session.execute(clear)
        set_ = (
            update(BidLevel)
            .where(BidLevel.id == level_id)
            .values(is_winner=True)
        )
        await self.session.execute(set_)
        await self.session.flush()


# ── Opportunity cache (read + write idempotent) ───────────────────────────


class OpportunityCacheRepository:
    """Cache of GovTribe federal opportunities.

    Idempotent on ``govtribe_external_id``: callers that try to insert a
    duplicate get the existing row back instead.  The mutation methods only
    rewrite cache-side bookkeeping (payload snapshot, last_synced_at,
    promoted_to_project_id); the source-of-truth fields (external_id,
    solicitation_number) are immutable once set.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, cache_id: uuid.UUID) -> OpportunityCache | None:
        return await self.session.get(OpportunityCache, cache_id)

    async def get_by_external_id(self, external_id: str) -> OpportunityCache | None:
        stmt = select(OpportunityCache).where(OpportunityCache.govtribe_external_id == external_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def upsert(
        self,
        *,
        external_id: str,
        solicitation_number: str | None,
        payload: dict,
    ) -> OpportunityCache:
        """Insert if missing, otherwise refresh the payload + sync timestamp."""
        existing = await self.get_by_external_id(external_id)
        if existing is not None:
            existing.payload = dict(payload or {})
            existing.last_synced_at = datetime.now(UTC)
            if solicitation_number and not existing.solicitation_number:
                existing.solicitation_number = solicitation_number
            await self.session.flush()
            return existing
        row = OpportunityCache(
            govtribe_external_id=external_id,
            solicitation_number=solicitation_number,
            payload=dict(payload or {}),
            last_synced_at=datetime.now(UTC),
        )
        self.session.add(row)
        await self.session.flush()
        return row

    async def mark_promoted(
        self,
        *,
        cache_id: uuid.UUID,
        project_id: uuid.UUID,
    ) -> None:
        stmt = (
            update(OpportunityCache)
            .where(OpportunityCache.id == cache_id)
            .values(promoted_to_project_id=project_id)
        )
        await self.session.execute(stmt)
        await self.session.flush()

    async def latest_sync(self) -> datetime | None:
        """Return the most recent ``last_synced_at`` across the cache."""
        stmt = select(func.max(OpportunityCache.last_synced_at))
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()


# ── Prequalification events (append-only) ─────────────────────────────────


class PrequalificationRepository:
    """Read + insert access for the prequalification audit log."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add(
        self,
        *,
        contact_id: uuid.UUID,
        from_status: str | None,
        to_status: str,
        changed_by: uuid.UUID | None,
        reason: str | None = None,
        expires_at: datetime | None = None,
    ) -> PrequalificationEvent:
        event = PrequalificationEvent(
            contact_id=contact_id,
            from_status=from_status,
            to_status=to_status,
            changed_by=changed_by,
            reason=reason,
            expires_at=expires_at,
        )
        self.session.add(event)
        await self.session.flush()
        return event

    async def list_for_contact(self, contact_id: uuid.UUID) -> list[PrequalificationEvent]:
        stmt = (
            select(PrequalificationEvent)
            .where(PrequalificationEvent.contact_id == contact_id)
            .order_by(PrequalificationEvent.timestamp.asc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def latest_for_contact(
        self,
        contact_id: uuid.UUID,
    ) -> PrequalificationEvent | None:
        stmt = (
            select(PrequalificationEvent)
            .where(PrequalificationEvent.contact_id == contact_id)
            .order_by(PrequalificationEvent.timestamp.desc())
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()


# ── RFQ invitations (read + insert + state transition) ───────────────────


class RFQInvitationRepository:
    """Read, insert, and state-transition access for RFQ invitations.

    State transitions are mutations (not append-only) because the row is the
    source of truth for the invitation lifecycle — the audit trail is the
    surrounding metadata column, not separate event rows.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, invitation_id: uuid.UUID) -> RFQInvitation | None:
        return await self.session.get(RFQInvitation, invitation_id)

    async def get_by_pair(self, rfq_id: uuid.UUID, contact_id: uuid.UUID) -> RFQInvitation | None:
        stmt = select(RFQInvitation).where(
            and_(RFQInvitation.rfq_id == rfq_id, RFQInvitation.contact_id == contact_id),
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_for_rfq(self, rfq_id: uuid.UUID) -> list[RFQInvitation]:
        stmt = (
            select(RFQInvitation)
            .where(RFQInvitation.rfq_id == rfq_id)
            .order_by(RFQInvitation.invited_at.asc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def add(
        self,
        *,
        rfq_id: uuid.UUID,
        contact_id: uuid.UUID,
        metadata: dict | None = None,
    ) -> RFQInvitation:
        invitation = RFQInvitation(
            rfq_id=rfq_id,
            contact_id=contact_id,
            status="INVITED",
            metadata_=dict(metadata or {}),
        )
        self.session.add(invitation)
        await self.session.flush()
        return invitation

    async def update_status(
        self,
        *,
        invitation_id: uuid.UUID,
        new_status: str,
        last_viewed_at: datetime | None = None,
        responded_at: datetime | None = None,
    ) -> None:
        values: dict[str, object] = {"status": new_status}
        if last_viewed_at is not None:
            values["last_viewed_at"] = last_viewed_at
        if responded_at is not None:
            values["responded_at"] = responded_at
        stmt = update(RFQInvitation).where(RFQInvitation.id == invitation_id).values(**values)
        await self.session.execute(stmt)
        await self.session.flush()
