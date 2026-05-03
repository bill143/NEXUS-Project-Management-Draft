"""Top-level Precon service — thin orchestration over the specialized services.

Most callers (router, tasks) work with the specialized services directly:

* :class:`PipelineService` — opportunity stage machine + Award & Activate
* :class:`RFQInvitationService` — 8-state invitation lifecycle
* :class:`BidLevelingService` — leveling snapshots and adjustments
* :class:`PrequalificationService` — append-only prequal audit log
* :class:`GovTribeAdapter` — federal-opportunity promotion

This file exists so the module presents a single ``PreconService`` entrypoint
that routes high-level workflow calls (e.g. "transition this project") to the
right specialized service without leaking the internal partition.
"""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.precon.schemas import (
    AwardActivateResult,
    PipelineSummary,
    PrequalStatusResponse,
)
from app.modules.precon.services.bid_leveling import BidLevelingService
from app.modules.precon.services.govtribe_adapter import GovTribeAdapter
from app.modules.precon.services.pipeline_service import PipelineService
from app.modules.precon.services.prequalification_service import PrequalificationService
from app.modules.precon.services.rfq_invitation_service import RFQInvitationService


class PreconService:
    """Single facade over the specialized Precon services."""

    def __init__(self, session: AsyncSession, *, mcp_client: Any | None = None) -> None:
        self.session = session
        self.pipeline = PipelineService(session)
        self.invitations = RFQInvitationService(session)
        self.bids = BidLevelingService(session)
        self.prequal = PrequalificationService(session)
        self.govtribe = GovTribeAdapter(session, mcp_client=mcp_client)

    # ── Pipeline ──────────────────────────────────────────────────────────

    async def transition(
        self,
        project_id: uuid.UUID,
        *,
        to: str,
        changed_by: uuid.UUID | None = None,
        reason: str | None = None,
    ) -> object:
        return await self.pipeline.transition(
            project_id, to=to, changed_by=changed_by, reason=reason
        )

    async def get_pipeline_summary(self) -> PipelineSummary:
        return await self.pipeline.get_pipeline_summary()

    async def award_and_activate(
        self,
        project_id: uuid.UUID,
        winning_bid_id: uuid.UUID,
        *,
        changed_by: uuid.UUID | None = None,
        reason: str | None = None,
    ) -> AwardActivateResult:
        return await self.pipeline.award_and_activate(
            project_id,
            winning_bid_id,
            changed_by=changed_by,
            reason=reason,
        )

    # ── Prequalification ──────────────────────────────────────────────────

    async def update_prequal(
        self,
        contact_id: uuid.UUID,
        *,
        to: str,
        reason: str | None = None,
        expires_at: datetime | None = None,
        changed_by: uuid.UUID | None = None,
    ) -> object:
        return await self.prequal.update_prequal(
            contact_id,
            to=to,
            reason=reason,
            expires_at=expires_at,
            changed_by=changed_by,
        )

    async def get_prequal_status(self, contact_id: uuid.UUID) -> PrequalStatusResponse:
        return await self.prequal.get_prequal_status(contact_id)
