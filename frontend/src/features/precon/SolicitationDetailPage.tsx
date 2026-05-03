/**
 * Solicitation Detail — single-opportunity drill-down.
 *
 * Composes opportunity info, documents, contacts, bid packages, and the
 * stage-action rail (transition / award) into a single page.  Everything
 * non-precon-specific (documents, contacts) is fetched via OCERP endpoints;
 * the precon-specific stage actions go through the precon hooks.
 */

import { useState } from 'react';
import { Navigate, useNavigate, useParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { ArrowLeft, Calendar, FileText, Users } from 'lucide-react';

import { useAuthStore } from '@/stores/useAuthStore';
import { useToastStore } from '@/stores/useToastStore';
import { apiGet } from '@/shared/lib/api';

import { InvitationStatusBadge } from './components/InvitationStatusBadge';
import { StageBadge } from './components/StageBadge';
import { useTransitionPipeline } from './hooks/usePipeline';
import {
  PIPELINE_STAGES,
  isPreconRole,
  type PipelineStage,
} from './api/types';

interface ProjectDetail {
  id: string;
  name: string;
  description?: string;
  phase?: PipelineStage | null;
  client_name?: string | null;
  contract_value?: string | null;
  planned_end_date?: string | null;
  metadata?: Record<string, unknown> | null;
}

interface DocumentSummary {
  id: string;
  name: string;
  category?: string | null;
  cde_state?: string | null;
}

interface ContactSummary {
  id: string;
  name: string;
  role?: string | null;
}

export function SolicitationDetailPage() {
  const { projectId = '' } = useParams<{ projectId: string }>();
  const navigate = useNavigate();
  const role = useAuthStore((s) => s.userRole);
  const addToast = useToastStore((s) => s.addToast);
  const transition = useTransitionPipeline();
  const [pendingStage, setPendingStage] = useState<PipelineStage | null>(null);

  if (!isPreconRole(role)) {
    return <Navigate to="/" replace />;
  }

  const { data: project, isLoading } = useQuery<ProjectDetail | null>({
    queryKey: ['precon', 'project', projectId],
    queryFn: () => apiGet<ProjectDetail>(`/v1/projects/${projectId}`),
    enabled: Boolean(projectId),
  });

  const { data: documents } = useQuery<DocumentSummary[]>({
    queryKey: ['precon', 'project', projectId, 'documents'],
    queryFn: async () => {
      try {
        return await apiGet<DocumentSummary[]>(`/v1/documents/?project_id=${projectId}`);
      } catch {
        return [];
      }
    },
    enabled: Boolean(projectId),
  });

  const { data: contacts } = useQuery<ContactSummary[]>({
    queryKey: ['precon', 'project', projectId, 'contacts'],
    queryFn: async () => {
      try {
        return await apiGet<ContactSummary[]>(`/v1/contacts/?project_id=${projectId}`);
      } catch {
        return [];
      }
    },
    enabled: Boolean(projectId),
  });

  if (isLoading) {
    return (
      <div className="rounded-lg border border-gray-200 bg-white p-12 text-center text-sm text-gray-500">
        Loading opportunity…
      </div>
    );
  }
  if (!project) {
    return (
      <div className="rounded-lg border border-gray-200 bg-white p-12 text-center text-sm text-gray-500">
        Opportunity not found.
      </div>
    );
  }

  const currentStage = project.phase ?? 'identified';

  const handleTransition = async (toStage: PipelineStage) => {
    setPendingStage(toStage);
    try {
      await transition.mutateAsync({ projectId, to: toStage });
      addToast({ type: 'success', title: 'Stage updated', message: `Moved to ${toStage}` });
    } catch (err) {
      const message =
        err instanceof Error
          ? err.message.includes('not permitted')
            ? `Backward stage transitions are not permitted (${currentStage} → ${toStage})`
            : err.message
          : 'Stage transition rejected';
      addToast({ type: 'error', title: 'Transition blocked', message });
    } finally {
      setPendingStage(null);
    }
  };

  return (
    <div className="flex flex-col gap-5">
      {/* ── Header / breadcrumb ────────────────────────────────────── */}
      <button
        type="button"
        onClick={() => navigate('/precon/pipeline')}
        className="inline-flex w-fit items-center gap-1 text-xs font-display font-bold uppercase tracking-widest text-gray-500 hover:text-[#B8232C]"
      >
        <ArrowLeft className="h-3.5 w-3.5" aria-hidden /> Back to Pipeline
      </button>

      <header className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="font-display text-3xl font-bold uppercase tracking-tight text-[#0D0D0D]">
            {project.name}
          </h1>
          <div className="mt-1 flex items-center gap-2">
            <StageBadge stage={currentStage} />
            {project.client_name && (
              <span className="font-mono text-xs text-gray-600">
                · {project.client_name}
              </span>
            )}
          </div>
        </div>
      </header>

      {/* ── Stage action rail ──────────────────────────────────────── */}
      <section className="rounded-lg border border-gray-200 bg-white p-4">
        <h2 className="font-display text-xs font-bold uppercase tracking-widest text-gray-700">
          Stage Actions
        </h2>
        <div className="mt-2 flex flex-wrap gap-2">
          {PIPELINE_STAGES.map((stage) => (
            <button
              key={stage}
              type="button"
              disabled={
                stage === currentStage ||
                pendingStage !== null ||
                transition.isPending
              }
              onClick={() => handleTransition(stage)}
              className="rounded border border-gray-300 bg-white px-3 py-1 text-xs font-display font-bold uppercase tracking-wide text-gray-700 hover:border-[#B8232C] hover:text-[#B8232C] disabled:cursor-not-allowed disabled:opacity-40"
            >
              → {stage.replace('_', ' ')}
            </button>
          ))}
        </div>
        <p className="mt-2 text-[11px] text-gray-500">
          The backend rejects backward / skip / resurrection transitions; the
          UI surfaces the rejection as a toast.
        </p>
      </section>

      {/* ── Opportunity facts ───────────────────────────────────────── */}
      <section className="grid gap-3 md:grid-cols-3">
        <FactCard
          Icon={Calendar}
          label="Bid Due"
          value={
            project.planned_end_date
              ? new Date(project.planned_end_date).toLocaleDateString()
              : '—'
          }
        />
        <FactCard
          Icon={FileText}
          label="Documents"
          value={String(documents?.length ?? 0)}
        />
        <FactCard
          Icon={Users}
          label="Contacts"
          value={String(contacts?.length ?? 0)}
        />
      </section>

      {project.description && (
        <section className="rounded-lg border border-gray-200 bg-white p-4">
          <h2 className="font-display text-xs font-bold uppercase tracking-widest text-gray-700">
            Description
          </h2>
          <p className="mt-1 whitespace-pre-line text-sm text-gray-700">
            {project.description}
          </p>
        </section>
      )}

      {/* ── Documents ──────────────────────────────────────────────── */}
      <section className="rounded-lg border border-gray-200 bg-white">
        <header className="border-b border-gray-200 bg-gray-50 px-4 py-2 font-display text-xs font-bold uppercase tracking-widest text-gray-700">
          Documents
        </header>
        {!documents || documents.length === 0 ? (
          <div className="px-4 py-6 text-center text-sm text-gray-500">
            No documents linked yet.
          </div>
        ) : (
          <ul className="divide-y divide-gray-100">
            {documents.slice(0, 10).map((d) => (
              <li
                key={d.id}
                className="flex items-center justify-between px-4 py-2.5 text-sm"
              >
                <span className="text-[#0D0D0D]">{d.name}</span>
                <span className="font-mono text-[11px] text-gray-500">
                  {d.category ?? '—'} · {d.cde_state ?? 'wip'}
                </span>
              </li>
            ))}
          </ul>
        )}
      </section>

      {/* ── Sample invitation status badges (placeholder until RFQ wired) ── */}
      <section className="rounded-lg border border-gray-200 bg-white p-4">
        <h2 className="font-display text-xs font-bold uppercase tracking-widest text-gray-700">
          Invitation Status Legend
        </h2>
        <div className="mt-2 flex flex-wrap gap-2">
          {(['INVITED', 'VIEWED', 'ACCEPTED', 'SUBMITTED', 'AWARDED', 'NOT_AWARDED', 'DECLINED', 'IGNORED'] as const).map(
            (s) => (
              <InvitationStatusBadge key={s} status={s} />
            ),
          )}
        </div>
      </section>
    </div>
  );
}

// ── Fact card ─────────────────────────────────────────────────────────────

function FactCard({
  Icon,
  label,
  value,
}: {
  Icon: React.ComponentType<{ className?: string }>;
  label: string;
  value: string;
}) {
  return (
    <div className="rounded-lg border border-gray-200 bg-white px-4 py-3">
      <div className="flex items-center justify-between">
        <span className="font-display text-[11px] font-bold uppercase tracking-widest text-gray-600">
          {label}
        </span>
        <Icon className="h-4 w-4 text-gray-400" aria-hidden />
      </div>
      <div className="mt-1 font-display text-xl font-bold text-[#0D0D0D]">{value}</div>
    </div>
  );
}
