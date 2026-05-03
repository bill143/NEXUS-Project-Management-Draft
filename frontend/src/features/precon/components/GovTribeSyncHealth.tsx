/**
 * Heartbeat health widget for the Precon dashboard.
 *
 * Polls the heartbeat endpoint every 30 seconds via `useGovTribeHealth` and
 * surfaces three states: green (fresh), amber (no data yet), red (stale —
 * banner-style alert per the Gap 1 routing in the build contract).
 */

import { Activity, AlertCircle, CheckCircle2 } from 'lucide-react';
import clsx from 'clsx';

import { useGovTribeHealth } from '../hooks/useGovTribeHealth';

export interface GovTribeSyncHealthProps {
  className?: string;
  compact?: boolean;
}

export function GovTribeSyncHealth({ className, compact = false }: GovTribeSyncHealthProps) {
  const { data, isLoading, isError } = useGovTribeHealth();
  const status: 'ok' | 'stale' | 'unknown' =
    isLoading || isError || !data ? 'unknown' : data.status;

  const tone = {
    ok: { ring: 'ring-emerald-300', bg: 'bg-emerald-50', text: 'text-emerald-800', Icon: CheckCircle2 },
    stale: { ring: 'ring-[#B8232C]/60', bg: 'bg-[#B8232C]/10', text: 'text-[#8a1920]', Icon: AlertCircle },
    unknown: { ring: 'ring-amber-300', bg: 'bg-amber-50', text: 'text-amber-800', Icon: Activity },
  }[status];

  const minutes = data?.minutes_since_sync ?? null;
  const lastSynced = data?.last_synced_at ?? null;

  return (
    <div
      className={clsx(
        'flex items-start gap-3 rounded-lg ring-1 px-4 py-3',
        tone.ring,
        tone.bg,
        className,
      )}
      role="status"
      aria-label="GovTribe sync health"
    >
      <tone.Icon className={clsx('mt-0.5 h-5 w-5 flex-shrink-0', tone.text)} aria-hidden />
      <div className="flex-1 min-w-0">
        <div className={clsx('font-display text-sm font-bold uppercase tracking-wide', tone.text)}>
          GovTribe Sync · {status === 'ok' ? 'Healthy' : status === 'stale' ? 'Stale' : 'Checking'}
        </div>
        {!compact && (
          <div className="mt-1 font-mono text-[11px] text-gray-600">
            {lastSynced ? (
              <>
                Last sync: {new Date(lastSynced).toLocaleString()}
                {minutes !== null && <> · {minutes}m ago</>}
              </>
            ) : (
              'No sync recorded yet'
            )}
          </div>
        )}
        {status === 'stale' && (
          <div className="mt-1 text-xs text-[#8a1920]">
            Federal opportunity feed has not refreshed in over 60 minutes. Bill has been notified.
          </div>
        )}
      </div>
    </div>
  );
}
