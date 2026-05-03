/**
 * Polls the heartbeat endpoint every 30 seconds so the dashboard widget can
 * surface a stale-sync banner promptly.  When the endpoint isn't shipped yet
 * (early Phase E builds) the client returns a synthesized OK status — see
 * `preconClient.health.heartbeat`.
 */

import { useQuery } from '@tanstack/react-query';

import { preconClient } from '../api/preconClient';
import type { HeartbeatStatus } from '../api/types';

export function useGovTribeHealth() {
  return useQuery<HeartbeatStatus>({
    queryKey: ['precon', 'health', 'heartbeat'],
    queryFn: preconClient.health.heartbeat,
    staleTime: 15_000,
    refetchInterval: 30_000,
  });
}
