/**
 * React Query hooks for RFQ invitations (8-state lifecycle).
 *
 * The backend rejects illegal transitions with 409; we let the error bubble
 * so the calling page can show a toast like
 * `Backward stage transitions are not permitted` (T11-08 / T03-11).
 */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { preconClient } from '../api/preconClient';
import type { InvitationResponse, InvitationState } from '../api/types';

function listKey(rfqId: string) {
  return ['precon', 'invitations', rfqId] as const;
}

export function useInvitations(rfqId: string | null | undefined) {
  return useQuery<InvitationResponse[]>({
    queryKey: listKey(rfqId ?? '__none__'),
    queryFn: () => preconClient.invitations.list(rfqId as string),
    enabled: Boolean(rfqId),
    staleTime: 15_000,
  });
}

export function useCreateInvitation(rfqId: string | null | undefined) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (contact_id: string) =>
      preconClient.invitations.create(rfqId as string, { contact_id }),
    onSuccess: () => {
      if (rfqId) void qc.invalidateQueries({ queryKey: listKey(rfqId) });
    },
  });
}

export function useTransitionInvitation(rfqId: string | null | undefined) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      invitationId,
      to,
    }: {
      invitationId: string;
      to: InvitationState;
    }) => preconClient.invitations.transition(invitationId, { to }),
    onSuccess: () => {
      if (rfqId) void qc.invalidateQueries({ queryKey: listKey(rfqId) });
    },
  });
}
