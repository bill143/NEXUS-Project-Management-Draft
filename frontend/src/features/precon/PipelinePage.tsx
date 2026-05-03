/**
 * Pipeline page — Kanban + list view of opportunities by 8 stages.
 *
 * Auth-gated to Precon roles (T11-09).  Backward-stage drags are blocked by
 * the backend (T11-08); the catch handler surfaces the rejection as a toast
 * and the card visually snaps back because the data hasn't moved.
 */

import { useMemo, useState } from 'react';
import { Navigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { LayoutGrid, List } from 'lucide-react';
import clsx from 'clsx';

import { useAuthStore } from '@/stores/useAuthStore';
import { useToastStore } from '@/stores/useToastStore';
import { apiGet } from '@/shared/lib/api';

import { OpportunityCard, type OpportunityCardData } from './components/OpportunityCard';
import { PipelineKanban } from './components/PipelineKanban';
import { StageBadge } from './components/StageBadge';
import { isPreconRole, type PipelineStage, PIPELINE_STAGES } from './api/types';
import { useTransitionPipeline } from './hooks/usePipeline';

/**
 * Shape we expect from `GET /api/projects/?phase=precon`.  Mirrored as a
 * narrow local interface — the OCERP `Project` type is much wider but we
 * only need these fields here.
 */
interface PipelineProject {
  id: string;
  name: string;
  phase: PipelineStage | null;
  client_name?: string | null;
  address?: { city?: string; state?: string } | null;
  planned_end_date?: string | null;
  contract_value?: string | null;
  metadata?: Record<string, unknown> | null;
}

type ViewMode = 'kanban' | 'list';

export function PipelinePage() {
  const role = useAuthStore((s) => s.userRole);
  const addToast = useToastStore((s) => s.addToast);
  const transition = useTransitionPipeline();
  const [view, setView] = useState<ViewMode>('kanban');

  if (!isPreconRole(role)) {
    return <Navigate to="/" replace />;
  }

  // Pull projects with a phase set — those are the precon pipeline.
  const { data: projects, isLoading } = useQuery<PipelineProject[]>({
    queryKey: ['precon', 'pipeline-projects'],
    queryFn: async () => {
      const all = await apiGet<PipelineProject[]>('/v1/projects/?limit=500');
      return all.filter((p) => p.phase && PIPELINE_STAGES.includes(p.phase));
    },
    staleTime: 30_000,
  });

  const opportunities = useMemo<OpportunityCardData[]>(() => {
    if (!projects) return [];
    return projects.map((p) => ({
      id: p.id,
      name: p.name,
      stage: (p.phase ?? 'identified') as PipelineStage,
      agency: typeof p.metadata?.agency === 'string' ? p.metadata.agency : p.client_name ?? null,
      location: p.address ? joinLocation(p.address) : null,
      bid_due_date: p.planned_end_date ?? null,
      contract_value: p.contract_value ?? null,
      solicitation_number:
        typeof p.metadata?.solicitation_number === 'string'
          ? p.metadata.solicitation_number
          : null,
    }));
  }, [projects]);

  const handleTransition = async (
    opportunityId: string,
    fromStage: PipelineStage,
    toStage: PipelineStage,
  ): Promise<boolean> => {
    try {
      await transition.mutateAsync({ projectId: opportunityId, to: toStage });
      addToast({
        type: 'success',
        title: 'Stage updated',
        message: `Moved opportunity from ${fromStage} → ${toStage}`,
      });
      return true;
    } catch (err) {
      const message =
        err instanceof Error ? err.message : 'Stage transition rejected';
      // T11-08 acceptance: surface the rejection as a toast.
      addToast({
        type: 'error',
        title: 'Transition blocked',
        message:
          message.includes('Forbidden') || message.includes('not permitted')
            ? `Backward stage transitions are not permitted (${fromStage} → ${toStage})`
            : message,
      });
      return false;
    }
  };

  return (
    <div className="flex flex-col gap-4">
      {/* ── Header ───────────────────────────────────────────────────── */}
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="font-display text-3xl font-bold uppercase tracking-tight text-[#0D0D0D]">
            Precon Pipeline
          </h1>
          <p className="text-sm text-gray-600">
            Opportunities by stage. Drag a card between columns to advance the
            pipeline.
          </p>
        </div>
        <div className="inline-flex rounded-lg border border-gray-300 bg-white p-1">
          <button
            type="button"
            className={clsx(
              'inline-flex items-center gap-1.5 rounded px-3 py-1.5 text-xs font-display font-bold uppercase tracking-wide transition',
              view === 'kanban'
                ? 'bg-[#B8232C] text-white shadow-sm'
                : 'text-gray-600 hover:text-[#B8232C]',
            )}
            onClick={() => setView('kanban')}
          >
            <LayoutGrid className="h-3.5 w-3.5" aria-hidden /> Kanban
          </button>
          <button
            type="button"
            className={clsx(
              'inline-flex items-center gap-1.5 rounded px-3 py-1.5 text-xs font-display font-bold uppercase tracking-wide transition',
              view === 'list'
                ? 'bg-[#B8232C] text-white shadow-sm'
                : 'text-gray-600 hover:text-[#B8232C]',
            )}
            onClick={() => setView('list')}
          >
            <List className="h-3.5 w-3.5" aria-hidden /> List
          </button>
        </div>
      </header>

      {/* ── Body ─────────────────────────────────────────────────────── */}
      {isLoading ? (
        <div className="rounded-lg border border-gray-200 bg-white p-12 text-center text-sm text-gray-500">
          Loading pipeline…
        </div>
      ) : view === 'kanban' ? (
        <PipelineKanban
          opportunities={opportunities}
          onTransition={handleTransition}
        />
      ) : (
        <ListView opportunities={opportunities} />
      )}
    </div>
  );
}

// ── List view ──────────────────────────────────────────────────────────────

function ListView({ opportunities }: { opportunities: OpportunityCardData[] }) {
  if (opportunities.length === 0) {
    return (
      <div className="rounded-lg border border-dashed border-gray-300 bg-gray-50 p-12 text-center text-sm text-gray-500">
        No opportunities in the pipeline yet.
      </div>
    );
  }
  return (
    <div className="overflow-hidden rounded-lg border border-gray-200 bg-white">
      <table className="w-full text-sm">
        <thead className="bg-gray-50">
          <tr>
            <th className="px-4 py-3 text-left font-display text-xs font-bold uppercase tracking-wider text-gray-600">
              Opportunity
            </th>
            <th className="px-4 py-3 text-left font-display text-xs font-bold uppercase tracking-wider text-gray-600">
              Stage
            </th>
            <th className="px-4 py-3 text-left font-display text-xs font-bold uppercase tracking-wider text-gray-600">
              Agency
            </th>
            <th className="px-4 py-3 text-right font-display text-xs font-bold uppercase tracking-wider text-gray-600">
              Value
            </th>
            <th className="px-4 py-3 text-right font-display text-xs font-bold uppercase tracking-wider text-gray-600">
              Bid Due
            </th>
          </tr>
        </thead>
        <tbody>
          {opportunities.map((opp) => (
            <tr key={opp.id} className="border-t border-gray-100 hover:bg-gray-50">
              <td className="px-4 py-3 font-medium text-[#0D0D0D]">{opp.name}</td>
              <td className="px-4 py-3"><StageBadge stage={opp.stage} size="sm" /></td>
              <td className="px-4 py-3 text-gray-600">{opp.agency ?? '—'}</td>
              <td className="px-4 py-3 text-right font-mono text-gray-700">
                {opp.contract_value ? `$${opp.contract_value}` : '—'}
              </td>
              <td className="px-4 py-3 text-right font-mono text-gray-700">
                {opp.bid_due_date ? new Date(opp.bid_due_date).toLocaleDateString() : '—'}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ── Helpers ────────────────────────────────────────────────────────────────

function joinLocation(addr: { city?: string; state?: string }): string {
  const parts: string[] = [];
  if (addr.city) parts.push(addr.city);
  if (addr.state) parts.push(addr.state);
  return parts.join(', ');
}

// Re-export OpportunityCard so consumers can use it without separate imports.
export { OpportunityCard };
