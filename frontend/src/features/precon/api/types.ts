/**
 * TypeScript mirrors of the backend Pydantic schemas in
 * `backend/app/modules/precon/schemas.py`.
 *
 * Hand-written (not generated) so the precon module remains self-contained
 * and doesn't depend on the OpenAPI generator wired up to the live OCERP
 * dev server.  When the API contract changes, regenerate by re-reading
 * `schemas.py` and patching here — both files are the single source of
 * truth, and CI catches drift via the static-scan tests in Suite 9.
 */

// ── State / value sets enforced by the service layer ─────────────────────

export const PIPELINE_STAGES = [
  'identified',
  'triaged',
  'qualified',
  'bidding',
  'submitted',
  'awarded',
  'lost',
  'no_bid',
] as const;
export type PipelineStage = (typeof PIPELINE_STAGES)[number];

export const INVITATION_STATES = [
  'INVITED',
  'VIEWED',
  'ACCEPTED',
  'SUBMITTED',
  'DECLINED',
  'IGNORED',
  'AWARDED',
  'NOT_AWARDED',
] as const;
export type InvitationState = (typeof INVITATION_STATES)[number];

export const PREQUAL_STATES = [
  'pending',
  'in_review',
  'approved',
  'rejected',
  'expired',
] as const;
export type PrequalState = (typeof PREQUAL_STATES)[number];

// ── Stage events ─────────────────────────────────────────────────────────

export interface StageTransitionRequest {
  to: PipelineStage;
  reason?: string | null;
}

export interface StageEventResponse {
  id: string;
  project_id: string | null;
  from_stage: PipelineStage | null;
  to_stage: PipelineStage;
  changed_by: string | null;
  reason: string | null;
  timestamp: string;
  created_at: string;
  updated_at: string;
}

export interface PipelineSummary {
  counts: Record<PipelineStage, number>;
}

// ── Bid leveling ─────────────────────────────────────────────────────────

export interface BidLevelAdjustment {
  label?: string | null;
  amount: string; // Decimal serialized as string
  reason: string;
  applied_at: string;
}

export interface BidLevelResponse {
  id: string;
  package_id: string;
  bidder_contact_id: string | null;
  raw_amount: string; // Decimal as string
  adjustments: BidLevelAdjustment[];
  adjusted_amount: string;
  notes: string | null;
  is_winner: boolean;
  leveled_by: string | null;
  leveled_at: string;
  created_at: string;
  updated_at: string;
}

export interface AdjustmentRequest {
  amount: string; // Decimal as string for precision
  reason: string;
  label?: string | null;
}

// ── Opportunity cache ────────────────────────────────────────────────────

export interface OpportunityCacheResponse {
  id: string;
  govtribe_external_id: string;
  solicitation_number: string | null;
  payload: Record<string, unknown>;
  last_synced_at: string;
  promoted_to_project_id: string | null;
  created_at: string;
  updated_at: string;
}

export interface PromoteOpportunityResponse {
  project_id: string;
  cache_id: string;
  already_promoted: boolean;
}

// ── Prequalification ─────────────────────────────────────────────────────

export interface PrequalUpdateRequest {
  to: PrequalState;
  reason?: string | null;
  expires_at?: string | null; // ISO 8601 datetime
}

export interface PrequalEventResponse {
  id: string;
  contact_id: string;
  from_status: PrequalState | null;
  to_status: PrequalState;
  changed_by: string | null;
  reason: string | null;
  expires_at: string | null;
  timestamp: string;
  created_at: string;
  updated_at: string;
}

export interface PrequalStatusResponse {
  contact_id: string;
  current_status: PrequalState | null;
  expires_at: string | null;
  is_expired: boolean;
  days_since_expiry: number | null;
}

// ── RFQ invitations ──────────────────────────────────────────────────────

export interface InvitationCreateRequest {
  contact_id: string;
  metadata?: Record<string, unknown>;
}

export interface InvitationTransitionRequest {
  to: InvitationState;
}

export interface InvitationResponse {
  id: string;
  rfq_id: string;
  contact_id: string;
  status: InvitationState;
  invited_at: string;
  last_viewed_at: string | null;
  responded_at: string | null;
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

// ── Award & activate ─────────────────────────────────────────────────────

export interface AwardActivateRequest {
  winning_bid_id: string;
  reason?: string | null;
}

export interface AwardActivateResult {
  project_id: string;
  winning_bid_id: string;
  winning_contact_id: string | null;
  purchase_order_id: string | null;
  subcontract_document_id: string | null;
  sub_actions_completed: string[];
}

/**
 * The 11 sub-actions, in the order they fire in the backend transaction.
 * Used by the confirmation modal so users see exactly what's about to happen
 * before they click "Award & Activate" — see T06-10 acceptance.
 */
export const AWARD_SUB_ACTIONS: ReadonlyArray<{ key: string; label: string }> = [
  { key: 'mark_winning_bid', label: 'Mark winning bid as AWARDED' },
  { key: 'mark_losing_bids', label: 'Mark all losing bids as NOT_AWARDED' },
  { key: 'update_project_phase', label: 'Move project from Bidding → Awarded' },
  { key: 'flip_contact_subcontractor', label: 'Flip awarded contact to subcontractor (preserves bidder flag)' },
  { key: 'promote_budgets', label: 'Promote precon estimate budgets → active budget' },
  { key: 'create_purchase_order', label: 'Create purchase order for the awarded sub' },
  { key: 'create_subcontract_draft', label: 'Generate subcontract draft document' },
  { key: 'notify_winner', label: 'Notify winning subcontractor' },
  { key: 'notify_losers', label: 'Notify losing subcontractors' },
  { key: 'write_stage_event', label: 'Write opportunity stage_event audit row' },
  { key: 'operations_handoff', label: 'Trigger Operations handoff event (notifies assigned PM)' },
];

// ── Heartbeat ────────────────────────────────────────────────────────────

export interface HeartbeatStatus {
  status: 'ok' | 'stale';
  last_synced_at: string | null;
  minutes_since_sync: number | null;
  alert_fired: boolean;
}

// ── Auth roles ───────────────────────────────────────────────────────────

export const PRECON_ROLES = [
  'precon_executive',
  'precon_bd_manager',
  'precon_estimator',
  'pm',
  'subcontractor_portal',
] as const;
export type PreconRole = (typeof PRECON_ROLES)[number];

export function isPreconRole(role: string | null | undefined): boolean {
  if (!role) return false;
  if (role === 'admin') return true;
  return (PRECON_ROLES as readonly string[]).includes(role);
}
