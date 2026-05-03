"""Pydantic v2 request/response schemas for the Precon module.

Schemas are organised by concept: stage events, bid levels, opportunity cache,
prequalification events, and RFQ invitations.  Plus a small set of action
payloads (``transition``, ``award_and_activate``, ``apply_adjustment``) for the
router layer.
"""

from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

# ── State / value sets enforced by the service layer ───────────────────────

PIPELINE_STAGES: tuple[str, ...] = (
    "identified",
    "triaged",
    "qualified",
    "bidding",
    "submitted",
    "awarded",
    "lost",
    "no_bid",
)

INVITATION_STATES: tuple[str, ...] = (
    "INVITED",
    "VIEWED",
    "ACCEPTED",
    "SUBMITTED",
    "DECLINED",
    "IGNORED",
    "AWARDED",
    "NOT_AWARDED",
)

PREQUAL_STATES: tuple[str, ...] = (
    "pending",
    "in_review",
    "approved",
    "rejected",
    "expired",
)


# ── Stage events ──────────────────────────────────────────────────────────


class StageTransitionRequest(BaseModel):
    """Payload for ``POST /api/precon/pipeline/{project_id}/transition``."""

    to: str = Field(..., description="Target stage; must be one of PIPELINE_STAGES")
    reason: str | None = Field(default=None, max_length=2000)


class StageEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    project_id: UUID | None
    from_stage: str | None
    to_stage: str
    changed_by: UUID | None
    reason: str | None
    timestamp: datetime
    created_at: datetime
    updated_at: datetime


class PipelineSummary(BaseModel):
    """Counts of projects in each pipeline stage."""

    counts: dict[str, int] = Field(
        default_factory=lambda: {s: 0 for s in PIPELINE_STAGES},
        description="Dict keyed by stage name; values are project counts.",
    )


# ── Bid leveling ──────────────────────────────────────────────────────────


class BidLevelResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    package_id: UUID
    bidder_contact_id: UUID | None
    raw_amount: Decimal
    adjustments: list[dict[str, Any]]
    adjusted_amount: Decimal
    notes: str | None
    is_winner: bool
    leveled_by: UUID | None
    leveled_at: datetime
    created_at: datetime
    updated_at: datetime


class AdjustmentRequest(BaseModel):
    """Payload for ``POST /api/precon/bids/levels/{level_id}/adjustments``."""

    amount: Decimal = Field(..., description="Signed adjustment amount in package currency")
    reason: str = Field(..., min_length=1, max_length=2000)
    label: str | None = Field(default=None, max_length=255)


# ── Opportunity cache ─────────────────────────────────────────────────────


class OpportunityCacheResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    govtribe_external_id: str
    solicitation_number: str | None
    payload: dict[str, Any]
    last_synced_at: datetime
    promoted_to_project_id: UUID | None
    created_at: datetime
    updated_at: datetime


class PromoteOpportunityResponse(BaseModel):
    """Returned by ``POST /api/precon/opportunities/{opp_id}/promote``."""

    project_id: UUID
    cache_id: UUID
    already_promoted: bool = False


# ── Prequalification ──────────────────────────────────────────────────────


class PrequalUpdateRequest(BaseModel):
    """Payload for ``POST /api/precon/contacts/{contact_id}/prequal``."""

    to: str = Field(..., description="Target prequal status; must be one of PREQUAL_STATES")
    reason: str | None = Field(default=None, max_length=2000)
    expires_at: datetime | None = Field(default=None)


class PrequalEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    contact_id: UUID
    from_status: str | None
    to_status: str
    changed_by: UUID | None
    reason: str | None
    expires_at: datetime | None
    timestamp: datetime
    created_at: datetime
    updated_at: datetime


class PrequalStatusResponse(BaseModel):
    """Returned by ``GET /api/precon/contacts/{contact_id}/prequal``."""

    contact_id: UUID
    current_status: str | None
    expires_at: datetime | None = None
    is_expired: bool = False
    days_since_expiry: int | None = None


# ── RFQ invitations ───────────────────────────────────────────────────────


class InvitationCreateRequest(BaseModel):
    """Payload for ``POST /api/precon/rfqs/{rfq_id}/invitations``."""

    contact_id: UUID
    metadata: dict[str, Any] = Field(default_factory=dict)


class InvitationTransitionRequest(BaseModel):
    """Payload for ``PATCH /api/precon/rfqs/invitations/{invitation_id}``."""

    to: str = Field(..., description="Target invitation state; must be one of INVITATION_STATES")


class InvitationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: UUID
    rfq_id: UUID
    contact_id: UUID
    status: str
    invited_at: datetime
    last_viewed_at: datetime | None
    responded_at: datetime | None
    metadata: dict[str, Any] = Field(default_factory=dict, validation_alias="metadata_")
    created_at: datetime
    updated_at: datetime


# ── Award & activate ──────────────────────────────────────────────────────


class AwardActivateRequest(BaseModel):
    """Payload for ``POST /api/precon/pipeline/{project_id}/award``."""

    winning_bid_id: UUID
    reason: str | None = Field(default=None, max_length=2000)


class AwardActivateResult(BaseModel):
    """Summary returned after a successful award + activate."""

    project_id: UUID
    winning_bid_id: UUID
    winning_contact_id: UUID | None = None
    purchase_order_id: UUID | None = None
    subcontract_document_id: UUID | None = None
    sub_actions_completed: list[str] = Field(default_factory=list)


# ── Heartbeat ─────────────────────────────────────────────────────────────


class HeartbeatStatus(BaseModel):
    """Health snapshot returned by the heartbeat task."""

    status: str = Field(..., description="'ok' | 'stale'")
    last_synced_at: datetime | None = None
    minutes_since_sync: int | None = None
    alert_fired: bool = False
