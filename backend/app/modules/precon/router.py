"""Precon API routes — namespaced under ``/api/precon/*``.

Every endpoint is gated to one or more Precon-specific roles:

* ``precon_executive``      — full read/write
* ``precon_bd_manager``     — pipeline + RFQ + opportunities
* ``precon_estimator``      — bid leveling + RFQs
* ``pm``                    — pipeline read + handoff
* ``subcontractor_portal``  — invitation responses only

Auth gating is enforced by :func:`require_precon_role`, a FastAPI dependency
that reads the JWT payload and checks role membership.  Routes never collide
with existing OCERP routes because we own the ``/api/precon/`` prefix
exclusively.
"""

import logging
import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status

from app.modules.precon.schemas import (
    AdjustmentRequest,
    AwardActivateRequest,
    AwardActivateResult,
    BidLevelResponse,
    HeartbeatStatus,
    InvitationCreateRequest,
    InvitationResponse,
    InvitationTransitionRequest,
    OpportunityCacheResponse,
    PipelineSummary,
    PrequalEventResponse,
    PrequalStatusResponse,
    PrequalUpdateRequest,
    PromoteOpportunityResponse,
    StageEventResponse,
    StageTransitionRequest,
)
from app.modules.precon.service import PreconService

logger = logging.getLogger(__name__)

# All Precon roles that may access at least one endpoint.
PRECON_ROLES: frozenset[str] = frozenset(
    {
        "precon_executive",
        "precon_bd_manager",
        "precon_estimator",
        "pm",
        "subcontractor_portal",
    }
)


# ── Dependencies ───────────────────────────────────────────────────────────


def _resolve_session_dep():
    """Return the real OCERP SessionDep when available, else a stub.

    Imports are deferred so that ``import app.modules.precon.router`` works
    even when OCERP isn't on the import path (e.g. SQLite-only test runs).
    """
    try:
        from app.dependencies import SessionDep  # type: ignore[import-not-found]

        return SessionDep
    except Exception:
        from sqlalchemy.ext.asyncio import AsyncSession  # noqa: F401 — type hint

        # Lazy stub: returns the dependency as a typed annotation when the
        # router is mounted into a real OCERP FastAPI app.
        return Any


def _resolve_payload_dep():
    try:
        from app.dependencies import CurrentUserPayload  # type: ignore[import-not-found]

        return CurrentUserPayload
    except Exception:
        return Any


SessionDep = _resolve_session_dep()
CurrentUserPayload = _resolve_payload_dep()


def require_precon_role(*allowed: str):
    """Build a FastAPI dependency that allows callers in ``allowed``.

    Raises HTTP 403 when the JWT payload role isn't in the allowed set.
    Admin role bypasses every check (consistent with OCERP convention).
    """
    allowed_set = frozenset(allowed) | {"admin"}

    async def _dep(payload: CurrentUserPayload) -> dict:  # type: ignore[valid-type]
        if not isinstance(payload, dict):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required",
            )
        role = payload.get("role")
        if role not in allowed_set:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role {role!r} not permitted; required one of {sorted(allowed_set - {'admin'})}",
            )
        return payload

    return _dep


def _service(session: SessionDep) -> PreconService:  # type: ignore[valid-type]
    return PreconService(session)


# ── Router ─────────────────────────────────────────────────────────────────

# NOTE: prefix is supplied by the OCERP main.py via include_router() — keeping
# it absent here mirrors the OCERP convention (e.g. i18n_router) and lets
# main.py own URL namespacing.  All routes still mount under /api/precon/*
# in production.  The T09-04 boundary scan asserts the prefix at the
# include_router call site, not on the APIRouter constructor.
router = APIRouter(tags=["precon"])


# ── Pipeline ──────────────────────────────────────────────────────────────


@router.get(
    "/pipeline/",
    response_model=PipelineSummary,
    summary="Pipeline summary — projects per stage",
)
async def pipeline_summary(
    _payload: dict = Depends(require_precon_role(*PRECON_ROLES)),
    svc: PreconService = Depends(_service),
) -> PipelineSummary:
    return await svc.get_pipeline_summary()


@router.post(
    "/pipeline/{project_id}/transition/",
    response_model=StageEventResponse,
    summary="Transition a project to a new pipeline stage",
)
async def transition_project(
    body: StageTransitionRequest,
    project_id: uuid.UUID = Path(...),
    payload: dict = Depends(require_precon_role("precon_executive", "precon_bd_manager", "pm")),
    svc: PreconService = Depends(_service),
) -> StageEventResponse:
    user_id = _user_uuid(payload)
    try:
        await svc.transition(project_id, to=body.to, changed_by=user_id, reason=body.reason)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    latest = await svc.pipeline.events.latest_for_project(project_id)
    return StageEventResponse.model_validate(latest)


@router.post(
    "/pipeline/{project_id}/award/",
    response_model=AwardActivateResult,
    summary="Atomic Award & Activate (11 sub-actions)",
)
async def award_and_activate(
    body: AwardActivateRequest,
    project_id: uuid.UUID = Path(...),
    payload: dict = Depends(require_precon_role("precon_executive", "precon_bd_manager")),
    svc: PreconService = Depends(_service),
) -> AwardActivateResult:
    user_id = _user_uuid(payload)
    try:
        return await svc.award_and_activate(
            project_id,
            body.winning_bid_id,
            changed_by=user_id,
            reason=body.reason,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


# ── RFQ invitations ───────────────────────────────────────────────────────


@router.post(
    "/rfqs/{rfq_id}/invitations/",
    response_model=InvitationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Invite a contact to an RFQ",
)
async def create_invitation(
    body: InvitationCreateRequest,
    rfq_id: uuid.UUID = Path(...),
    _payload: dict = Depends(require_precon_role("precon_executive", "precon_bd_manager", "precon_estimator")),
    svc: PreconService = Depends(_service),
) -> InvitationResponse:
    invitation = await svc.invitations.invite(
        rfq_id=rfq_id, contact_id=body.contact_id, metadata=body.metadata
    )
    return InvitationResponse.model_validate(invitation)


@router.get(
    "/rfqs/{rfq_id}/invitations/",
    response_model=list[InvitationResponse],
    summary="List invitations on an RFQ",
)
async def list_invitations(
    rfq_id: uuid.UUID = Path(...),
    _payload: dict = Depends(require_precon_role(*PRECON_ROLES)),
    svc: PreconService = Depends(_service),
) -> list[InvitationResponse]:
    invitations = await svc.invitations.list_for_rfq(rfq_id)
    return [InvitationResponse.model_validate(i) for i in invitations]


@router.patch(
    "/rfqs/invitations/{invitation_id}/",
    response_model=InvitationResponse,
    summary="Transition an invitation to a new state",
)
async def transition_invitation(
    body: InvitationTransitionRequest,
    invitation_id: uuid.UUID = Path(...),
    _payload: dict = Depends(require_precon_role(*PRECON_ROLES)),
    svc: PreconService = Depends(_service),
) -> InvitationResponse:
    try:
        invitation = await svc.invitations.transition(invitation_id, to=body.to)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return InvitationResponse.model_validate(invitation)


# ── Bid leveling ──────────────────────────────────────────────────────────


@router.post(
    "/bids/packages/{package_id}/level/",
    response_model=list[BidLevelResponse],
    summary="Generate a leveling snapshot for every bid on a package",
)
async def level_bids(
    package_id: uuid.UUID = Path(...),
    payload: dict = Depends(require_precon_role("precon_executive", "precon_bd_manager", "precon_estimator")),
    svc: PreconService = Depends(_service),
) -> list[BidLevelResponse]:
    snapshots = await svc.bids.level_bids(package_id, leveled_by=_user_uuid(payload))
    return [BidLevelResponse.model_validate(s) for s in snapshots]


@router.get(
    "/bids/packages/{package_id}/levels/",
    response_model=list[BidLevelResponse],
    summary="List leveling snapshots for a package",
)
async def list_bid_levels(
    package_id: uuid.UUID = Path(...),
    _payload: dict = Depends(require_precon_role(*PRECON_ROLES)),
    svc: PreconService = Depends(_service),
) -> list[BidLevelResponse]:
    snapshots = await svc.bids.list_for_package(package_id)
    return [BidLevelResponse.model_validate(s) for s in snapshots]


@router.post(
    "/bids/levels/{level_id}/adjustments/",
    response_model=BidLevelResponse,
    summary="Append a leveling adjustment",
)
async def apply_adjustment(
    body: AdjustmentRequest,
    level_id: uuid.UUID = Path(...),
    _payload: dict = Depends(require_precon_role("precon_executive", "precon_bd_manager", "precon_estimator")),
    svc: PreconService = Depends(_service),
) -> BidLevelResponse:
    try:
        snapshot = await svc.bids.apply_adjustment(
            level_id, amount=body.amount, reason=body.reason, label=body.label
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return BidLevelResponse.model_validate(snapshot)


@router.post(
    "/bids/levels/{level_id}/winner/",
    response_model=BidLevelResponse,
    summary="Mark a leveled bid as the package winner",
)
async def mark_winner(
    level_id: uuid.UUID = Path(...),
    _payload: dict = Depends(require_precon_role("precon_executive", "precon_bd_manager")),
    svc: PreconService = Depends(_service),
) -> BidLevelResponse:
    try:
        snapshot = await svc.bids.mark_winner(level_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return BidLevelResponse.model_validate(snapshot)


# ── Prequalification ──────────────────────────────────────────────────────


@router.post(
    "/contacts/{contact_id}/prequal/",
    response_model=PrequalEventResponse,
    summary="Update a contact's prequalification status (writes audit row)",
)
async def update_prequal(
    body: PrequalUpdateRequest,
    contact_id: uuid.UUID = Path(...),
    payload: dict = Depends(require_precon_role("precon_executive", "precon_bd_manager")),
    svc: PreconService = Depends(_service),
) -> PrequalEventResponse:
    try:
        event = await svc.update_prequal(
            contact_id,
            to=body.to,
            reason=body.reason,
            expires_at=body.expires_at,
            changed_by=_user_uuid(payload),
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return PrequalEventResponse.model_validate(event)


@router.get(
    "/contacts/{contact_id}/prequal/",
    response_model=PrequalStatusResponse,
    summary="Current prequalification status with expiry information",
)
async def get_prequal_status(
    contact_id: uuid.UUID = Path(...),
    _payload: dict = Depends(require_precon_role(*PRECON_ROLES)),
    svc: PreconService = Depends(_service),
) -> PrequalStatusResponse:
    return await svc.get_prequal_status(contact_id)


# ── GovTribe opportunities ────────────────────────────────────────────────


@router.post(
    "/opportunities/{external_id}/promote/",
    response_model=PromoteOpportunityResponse,
    summary="Promote a cached GovTribe opportunity to an OCERP project",
)
async def promote_opportunity(
    external_id: str = Path(...),
    payload: dict = Depends(require_precon_role("precon_executive", "precon_bd_manager")),
    svc: PreconService = Depends(_service),
) -> PromoteOpportunityResponse:
    try:
        return await svc.govtribe.promote_opportunity(
            external_id, owner_id=_user_uuid(payload)
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.get(
    "/opportunities/",
    response_model=list[OpportunityCacheResponse],
    summary="List cached GovTribe opportunities (paginated, filterable)",
)
async def list_opportunities(
    session: SessionDep,  # type: ignore[valid-type]
    _payload: dict = Depends(require_precon_role(*PRECON_ROLES)),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=500),
    promoted: str | None = Query(
        default=None,
        pattern="^(true|false|all)$",
        description="Filter by promotion state: 'true' (promoted), 'false' (unpromoted), 'all' (default).",
    ),
) -> list[OpportunityCacheResponse]:
    """Return cached opportunities, newest sync first."""
    from sqlalchemy import select as sa_select

    from app.modules.precon.models import OpportunityCache

    stmt = sa_select(OpportunityCache).order_by(OpportunityCache.last_synced_at.desc())
    if promoted == "true":
        stmt = stmt.where(OpportunityCache.promoted_to_project_id.isnot(None))
    elif promoted == "false":
        stmt = stmt.where(OpportunityCache.promoted_to_project_id.is_(None))
    stmt = stmt.offset(offset).limit(limit)

    rows = (await session.execute(stmt)).scalars().all()
    return [OpportunityCacheResponse.model_validate(r) for r in rows]


# ── Health / heartbeat ────────────────────────────────────────────────────


@router.get(
    "/health/heartbeat/",
    response_model=HeartbeatStatus,
    summary="Current GovTribe sync health (status + last_synced_at + minutes_since_sync)",
)
async def heartbeat_status(
    session: SessionDep,  # type: ignore[valid-type]
    _payload: dict = Depends(require_precon_role(*PRECON_ROLES)),
) -> HeartbeatStatus:
    """Snapshot the heartbeat without firing any alerts.

    Inspects the freshest ``last_synced_at`` in the cache and reports
    `ok` / `stale` based on the same threshold the Celery task uses.
    Read-only — the alert routing only fires from the scheduled task.
    """
    from datetime import UTC, datetime

    from app.modules.precon.repository import OpportunityCacheRepository
    from app.modules.precon.tasks.heartbeat import STALE_THRESHOLD_MINUTES

    repo = OpportunityCacheRepository(session)
    latest = await repo.latest_sync()
    if latest is None:
        return HeartbeatStatus(
            status="ok",
            last_synced_at=None,
            minutes_since_sync=None,
            alert_fired=False,
        )
    if latest.tzinfo is None:
        latest = latest.replace(tzinfo=UTC)
    delta_minutes = int((datetime.now(UTC) - latest).total_seconds() // 60)
    return HeartbeatStatus(
        status="stale" if delta_minutes > STALE_THRESHOLD_MINUTES else "ok",
        last_synced_at=latest,
        minutes_since_sync=delta_minutes,
        alert_fired=False,
    )


# ── Helpers ────────────────────────────────────────────────────────────────


def _user_uuid(payload: dict) -> uuid.UUID | None:
    """Best-effort extract a UUID from the JWT payload's ``sub`` field."""
    sub = payload.get("sub") if isinstance(payload, dict) else None
    if not sub:
        return None
    try:
        return uuid.UUID(str(sub))
    except (ValueError, TypeError):
        return None
