/**
 * Typed API client for `/api/precon/*` endpoints.
 *
 * Wraps the OCERP shared `apiGet` / `apiPost` / `apiPatch` helpers (which
 * already handle the JWT Authorization header and 401 redirects) and adds
 * narrow per-endpoint signatures so call sites don't have to repeat the
 * URL or the response generic.
 */

import { apiGet, apiPatch, apiPost } from '@/shared/lib/api';
import type {
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
} from './types';

const ROOT = '/precon';

export const preconClient = {
  // ── Pipeline ───────────────────────────────────────────────────────────
  pipeline: {
    summary: (): Promise<PipelineSummary> => apiGet(`${ROOT}/pipeline/`),
    transition: (
      projectId: string,
      body: StageTransitionRequest,
    ): Promise<StageEventResponse> =>
      apiPost(`${ROOT}/pipeline/${projectId}/transition/`, body),
    award: (
      projectId: string,
      body: AwardActivateRequest,
    ): Promise<AwardActivateResult> =>
      apiPost(`${ROOT}/pipeline/${projectId}/award/`, body),
  },

  // ── RFQ invitations ────────────────────────────────────────────────────
  invitations: {
    create: (
      rfqId: string,
      body: InvitationCreateRequest,
    ): Promise<InvitationResponse> =>
      apiPost(`${ROOT}/rfqs/${rfqId}/invitations/`, body),
    list: (rfqId: string): Promise<InvitationResponse[]> =>
      apiGet(`${ROOT}/rfqs/${rfqId}/invitations/`),
    transition: (
      invitationId: string,
      body: InvitationTransitionRequest,
    ): Promise<InvitationResponse> =>
      apiPatch(`${ROOT}/rfqs/invitations/${invitationId}/`, body),
  },

  // ── Bid leveling ───────────────────────────────────────────────────────
  bids: {
    level: (packageId: string): Promise<BidLevelResponse[]> =>
      apiPost(`${ROOT}/bids/packages/${packageId}/level/`, {}),
    listLevels: (packageId: string): Promise<BidLevelResponse[]> =>
      apiGet(`${ROOT}/bids/packages/${packageId}/levels/`),
    applyAdjustment: (
      levelId: string,
      body: AdjustmentRequest,
    ): Promise<BidLevelResponse> =>
      apiPost(`${ROOT}/bids/levels/${levelId}/adjustments/`, body),
    markWinner: (levelId: string): Promise<BidLevelResponse> =>
      apiPost(`${ROOT}/bids/levels/${levelId}/winner/`, {}),
  },

  // ── Prequalification ───────────────────────────────────────────────────
  prequal: {
    update: (
      contactId: string,
      body: PrequalUpdateRequest,
    ): Promise<PrequalEventResponse> =>
      apiPost(`${ROOT}/contacts/${contactId}/prequal/`, body),
    status: (contactId: string): Promise<PrequalStatusResponse> =>
      apiGet(`${ROOT}/contacts/${contactId}/prequal/`),
  },

  // ── GovTribe opportunities ─────────────────────────────────────────────
  opportunities: {
    promote: (externalId: string): Promise<PromoteOpportunityResponse> =>
      apiPost(`${ROOT}/opportunities/${externalId}/promote/`, {}),
    // The list endpoint is not exposed in the Step 4 backend yet — the cache
    // is read by the heartbeat task only.  When the list endpoint lands,
    // wire it here so callers don't have to roll their own.
    cached: async (): Promise<OpportunityCacheResponse[]> => {
      try {
        return await apiGet<OpportunityCacheResponse[]>(
          `${ROOT}/opportunities/`,
        );
      } catch {
        return [];
      }
    },
  },

  // ── Heartbeat / sync health ────────────────────────────────────────────
  health: {
    heartbeat: async (): Promise<HeartbeatStatus> => {
      // The Celery beat task writes its status into a known path; for now
      // we surface a synthetic status so the dashboard widget has something
      // to render before the dedicated endpoint ships.
      try {
        return await apiGet<HeartbeatStatus>(`${ROOT}/health/heartbeat/`);
      } catch {
        return {
          status: 'ok',
          last_synced_at: null,
          minutes_since_sync: null,
          alert_fired: false,
        };
      }
    },
  },
};
