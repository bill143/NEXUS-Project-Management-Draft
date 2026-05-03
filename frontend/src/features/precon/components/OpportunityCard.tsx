/**
 * Reusable opportunity card for the Kanban board and the list view.
 *
 * Stays presentational on purpose — the Kanban / list owns drag handlers,
 * navigation, and selection.  The card just renders.
 */

import { Building2, Calendar, ExternalLink, MapPin } from 'lucide-react';
import clsx from 'clsx';

import type { PipelineStage } from '../api/types';
import { StageBadge } from './StageBadge';

export interface OpportunityCardData {
  id: string;
  name: string;
  agency?: string | null;
  location?: string | null;
  bid_due_date?: string | null;
  contract_value?: string | null;
  stage: PipelineStage;
  solicitation_number?: string | null;
}

export interface OpportunityCardProps {
  opportunity: OpportunityCardData;
  onClick?: (id: string) => void;
  draggable?: boolean;
  className?: string;
}

export function OpportunityCard({
  opportunity,
  onClick,
  draggable = false,
  className,
}: OpportunityCardProps) {
  const { id, name, agency, location, bid_due_date, contract_value, stage, solicitation_number } =
    opportunity;

  return (
    <div
      className={clsx(
        'group flex flex-col gap-2 rounded-lg border border-gray-200 bg-white p-3 shadow-sm transition',
        'hover:border-[#B8232C]/40 hover:shadow-md',
        draggable && 'cursor-grab active:cursor-grabbing',
        className,
      )}
      onClick={onClick ? () => onClick(id) : undefined}
      data-opportunity-id={id}
      role={onClick ? 'button' : undefined}
      tabIndex={onClick ? 0 : undefined}
      onKeyDown={
        onClick
          ? (e) => {
              if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                onClick(id);
              }
            }
          : undefined
      }
    >
      <div className="flex items-start justify-between gap-2">
        <h3 className="line-clamp-2 font-display text-sm font-bold uppercase leading-tight tracking-tight text-[#0D0D0D]">
          {name}
        </h3>
        <StageBadge stage={stage} size="sm" />
      </div>

      {solicitation_number && (
        <div className="font-mono text-[11px] text-gray-500" title="Federal solicitation number">
          {solicitation_number}
        </div>
      )}

      <div className="flex flex-wrap gap-x-3 gap-y-1 text-xs text-gray-600">
        {agency && (
          <span className="inline-flex items-center gap-1">
            <Building2 className="h-3 w-3" aria-hidden />
            {agency}
          </span>
        )}
        {location && (
          <span className="inline-flex items-center gap-1">
            <MapPin className="h-3 w-3" aria-hidden />
            {location}
          </span>
        )}
        {bid_due_date && (
          <span className="inline-flex items-center gap-1">
            <Calendar className="h-3 w-3" aria-hidden />
            Due {new Date(bid_due_date).toLocaleDateString()}
          </span>
        )}
      </div>

      {contract_value && (
        <div className="mt-1 flex items-center justify-between">
          <span className="font-mono text-sm font-bold text-[#B8232C]">
            ${contract_value}
          </span>
          <ExternalLink className="h-3.5 w-3.5 text-gray-400 opacity-0 transition group-hover:opacity-100" aria-hidden />
        </div>
      )}
    </div>
  );
}
