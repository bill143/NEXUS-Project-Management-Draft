/**
 * Visual badge for the 8-state RFQ invitation lifecycle.
 *
 * Mirrors `StageBadge` but with a colour palette tuned to the invitation
 * funnel: blues for "in flight" states, greens for engaged, red for awarded
 * (which is the goal), and grays for declined / ignored / not_awarded.
 */

import clsx from 'clsx';

import type { InvitationState } from '../api/types';

const STATE_LABEL: Record<InvitationState, string> = {
  INVITED: 'Invited',
  VIEWED: 'Viewed',
  ACCEPTED: 'Accepted',
  SUBMITTED: 'Submitted',
  DECLINED: 'Declined',
  IGNORED: 'Ignored',
  AWARDED: 'Awarded',
  NOT_AWARDED: 'Not Awarded',
};

const STATE_CLASS: Record<InvitationState, string> = {
  INVITED: 'bg-blue-50 text-blue-800 ring-1 ring-blue-300',
  VIEWED: 'bg-sky-50 text-sky-800 ring-1 ring-sky-300',
  ACCEPTED: 'bg-emerald-50 text-emerald-800 ring-1 ring-emerald-300',
  SUBMITTED: 'bg-emerald-100 text-emerald-900 ring-1 ring-emerald-400',
  DECLINED: 'bg-gray-100 text-gray-700 ring-1 ring-gray-300 line-through',
  IGNORED: 'bg-gray-100 text-gray-500 ring-1 ring-gray-300 italic',
  AWARDED: 'bg-[#B8232C] text-white ring-1 ring-[#8a1920]',
  NOT_AWARDED: 'bg-gray-200 text-gray-600 ring-1 ring-gray-300',
};

export interface InvitationStatusBadgeProps {
  status: InvitationState;
  className?: string;
}

export function InvitationStatusBadge({
  status,
  className,
}: InvitationStatusBadgeProps) {
  return (
    <span
      className={clsx(
        'inline-flex items-center rounded px-2 py-0.5 font-mono text-[11px] font-medium tracking-tight',
        STATE_CLASS[status],
        className,
      )}
      data-state={status}
    >
      {STATE_LABEL[status]}
    </span>
  );
}
