/**
 * React Query hooks for the bid-leveling engine.
 *
 * Snapshots are append-only on the backend; the only mutation that modifies
 * an existing row is `markWinner`, which flips the boolean.  Adjustments
 * append a JSON entry and recompute `adjusted_amount`.
 */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { preconClient } from '../api/preconClient';
import type { AdjustmentRequest, BidLevelResponse } from '../api/types';

function levelsKey(packageId: string) {
  return ['precon', 'bids', packageId] as const;
}

export function useBidLevels(packageId: string | null | undefined) {
  return useQuery<BidLevelResponse[]>({
    queryKey: levelsKey(packageId ?? '__none__'),
    queryFn: () => preconClient.bids.listLevels(packageId as string),
    enabled: Boolean(packageId),
    staleTime: 15_000,
  });
}

export function useGenerateLeveling(packageId: string | null | undefined) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => preconClient.bids.level(packageId as string),
    onSuccess: () => {
      if (packageId) void qc.invalidateQueries({ queryKey: levelsKey(packageId) });
    },
  });
}

export function useApplyAdjustment(packageId: string | null | undefined) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      levelId,
      ...body
    }: { levelId: string } & AdjustmentRequest) =>
      preconClient.bids.applyAdjustment(levelId, body),
    onSuccess: () => {
      if (packageId) void qc.invalidateQueries({ queryKey: levelsKey(packageId) });
    },
  });
}

export function useMarkWinner(packageId: string | null | undefined) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (levelId: string) => preconClient.bids.markWinner(levelId),
    onSuccess: () => {
      if (packageId) void qc.invalidateQueries({ queryKey: levelsKey(packageId) });
    },
  });
}
