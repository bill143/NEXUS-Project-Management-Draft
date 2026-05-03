/**
 * Visual badge for the 8-state opportunity pipeline.
 *
 * Each stage gets a distinct colour token so estimators can scan a Kanban
 * column or a list at a glance.  Terminal stages (`awarded` / `lost` /
 * `no_bid`) wear muted shades to de-emphasize closed-out work; in-flight
 * stages use the O'Neill red gradient for active pursuits.
 */

import clsx from 'clsx';

import type { PipelineStage } from '../api/types';

const STAGE_LABEL: Record<PipelineStage, string> = {
  identified: 'Identified',
  triaged: 'Triaged',
  qualified: 'Qualified',
  bidding: 'Bidding',
  submitted: 'Submitted',
  awarded: 'Awarded',
  lost: 'Lost',
  no_bid: 'No Bid',
};

const STAGE_CLASS: Record<PipelineStage, string> = {
  // In-flight — warming red as the opportunity moves toward award.
  identified: 'bg-gray-100 text-gray-800 ring-1 ring-gray-300',
  triaged: 'bg-amber-50 text-amber-900 ring-1 ring-amber-300',
  qualified: 'bg-orange-50 text-orange-900 ring-1 ring-orange-300',
  bidding: 'bg-red-50 text-[#8a1920] ring-1 ring-[#B8232C]/40',
  submitted: 'bg-red-100 text-[#8a1920] ring-1 ring-[#B8232C]/60',
  // Terminal — flat tones.
  awarded: 'bg-[#0D0D0D] text-white',
  lost: 'bg-gray-600 text-white',
  no_bid: 'bg-gray-200 text-gray-700 line-through',
};

export interface StageBadgeProps {
  stage: PipelineStage;
  className?: string;
  size?: 'sm' | 'md';
}

export function StageBadge({ stage, className, size = 'md' }: StageBadgeProps) {
  return (
    <span
      className={clsx(
        'inline-flex items-center rounded font-display font-bold uppercase tracking-wide',
        size === 'sm' ? 'px-1.5 py-0.5 text-xs' : 'px-2.5 py-1 text-xs',
        STAGE_CLASS[stage],
        className,
      )}
      data-stage={stage}
    >
      {STAGE_LABEL[stage]}
    </span>
  );
}
