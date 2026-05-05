/**
 * Compact pill displaying a contact's prequalification state with expiry
 * awareness.  When the underlying event has expired the pill flips to
 * `expired` and exposes the days-since-expiry so the BD manager knows how
 * stale the record is.
 */

import clsx from 'clsx';
import { AlertTriangle, CheckCircle2, Clock, Hourglass, ShieldAlert } from 'lucide-react';

import type { PrequalState, PrequalStatusResponse } from '../api/types';

const STATE_META: Record<PrequalState, { label: string; cls: string; Icon: React.ComponentType<{ className?: string }> }> = {
  pending: { label: 'Pending', cls: 'bg-gray-100 text-gray-700 ring-gray-300', Icon: Hourglass },
  in_review: { label: 'In Review', cls: 'bg-amber-50 text-amber-800 ring-amber-300', Icon: Clock },
  approved: { label: 'Approved', cls: 'bg-emerald-50 text-emerald-800 ring-emerald-300', Icon: CheckCircle2 },
  rejected: { label: 'Rejected', cls: 'bg-red-50 text-[#8a1920] ring-[#B8232C]/40', Icon: ShieldAlert },
  expired: { label: 'Expired', cls: 'bg-orange-50 text-orange-900 ring-orange-300', Icon: AlertTriangle },
};

export interface PrequalificationStatusProps {
  status: PrequalStatusResponse;
  className?: string;
}

export function PrequalificationStatus({ status, className }: PrequalificationStatusProps) {
  const current = status.current_status ?? 'pending';
  const meta = STATE_META[current];
  const { Icon } = meta;
  return (
    <div className={clsx('flex items-center gap-2', className)}>
      <span
        className={clsx(
          'inline-flex items-center gap-1 rounded px-2 py-1 text-xs font-display font-bold uppercase tracking-wide ring-1',
          meta.cls,
        )}
        data-prequal={current}
      >
        <Icon className="h-3.5 w-3.5" aria-hidden />
        {meta.label}
      </span>
      {status.is_expired && status.days_since_expiry !== null && (
        <span className="font-mono text-[11px] text-gray-500">
          {status.days_since_expiry}d ago
        </span>
      )}
    </div>
  );
}
