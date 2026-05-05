/**
 * React Query hooks for the opportunity pipeline.
 *
 * Surfaces three concerns: (1) the per-stage counts powering the dashboard,
 * (2) per-project transition mutations with optimistic invalidation, and
 * (3) the atomic Award & Activate mutation.  All errors propagate to the
 * caller so the UI can show a toast — the hooks themselves are intentionally
 * dumb.
 */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { preconClient } from '../api/preconClient';
import type {
  AwardActivateRequest,
  AwardActivateResult,
  PipelineStage,
  PipelineSummary,
} from '../api/types';

const PIPELINE_KEY = ['precon', 'pipeline'] as const;

export function usePipelineSummary() {
  return useQuery<PipelineSummary>({
    queryKey: PIPELINE_KEY,
    queryFn: preconClient.pipeline.summary,
    // Pipeline counts change every time someone moves a card; 30s keeps
    // the dashboard fresh without hammering the API.
    staleTime: 30_000,
    refetchInterval: 60_000,
  });
}

export function useTransitionPipeline() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      projectId,
      to,
      reason,
    }: {
      projectId: string;
      to: PipelineStage;
      reason?: string;
    }) =>
      preconClient.pipeline.transition(projectId, { to, reason: reason ?? null }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: PIPELINE_KEY });
    },
  });
}

export function useAwardAndActivate() {
  const qc = useQueryClient();
  return useMutation<
    AwardActivateResult,
    Error,
    { projectId: string } & AwardActivateRequest
  >({
    mutationFn: ({ projectId, ...body }) =>
      preconClient.pipeline.award(projectId, body),
    onSuccess: () => {
      // Award flips multiple downstream queries; invalidate them all.
      void qc.invalidateQueries({ queryKey: PIPELINE_KEY });
      void qc.invalidateQueries({ queryKey: ['precon', 'bids'] });
      void qc.invalidateQueries({ queryKey: ['precon', 'invitations'] });
    },
  });
}
