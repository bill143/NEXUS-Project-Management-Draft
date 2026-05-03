/**
 * Precon Dashboard — win rate, pipeline value, agency breakdown, sync health.
 *
 * Aggregates pipeline counts from the backend summary endpoint and surfaces
 * the heartbeat widget at the top so a stale GovTribe sync is visible
 * before any other metric.
 */

import { useMemo } from 'react';
import { Navigate } from 'react-router-dom';
import { Activity, Award, BarChart3, ChevronRight, Trophy } from 'lucide-react';
import clsx from 'clsx';

import { useAuthStore } from '@/stores/useAuthStore';

import { GovTribeSyncHealth } from './components/GovTribeSyncHealth';
import { isPreconRole, type PipelineStage } from './api/types';
import { usePipelineSummary } from './hooks/usePipeline';

const ACTIVE_STAGES: PipelineStage[] = ['identified', 'triaged', 'qualified', 'bidding', 'submitted'];

export function PreconDashboardPage() {
  const role = useAuthStore((s) => s.userRole);
  const { data: summary, isLoading } = usePipelineSummary();

  if (!isPreconRole(role)) {
    return <Navigate to="/" replace />;
  }

  const counts = summary?.counts;
  const totals = useMemo(() => {
    if (!counts) return { active: 0, awarded: 0, lost: 0, no_bid: 0, total: 0 };
    const active = ACTIVE_STAGES.reduce((sum, s) => sum + (counts[s] ?? 0), 0);
    const awarded = counts.awarded ?? 0;
    const lost = counts.lost ?? 0;
    const noBid = counts.no_bid ?? 0;
    return { active, awarded, lost, no_bid: noBid, total: active + awarded + lost + noBid };
  }, [counts]);

  // Win rate = awarded / (awarded + lost).  Excludes no_bid because those
  // are deliberate skip decisions, not losses.
  const winRate =
    totals.awarded + totals.lost > 0
      ? Math.round((totals.awarded / (totals.awarded + totals.lost)) * 100)
      : null;

  return (
    <div className="flex flex-col gap-5">
      {/* ── Header ───────────────────────────────────────────────────── */}
      <header>
        <h1 className="font-display text-3xl font-bold uppercase tracking-tight text-[#0D0D0D]">
          Precon Dashboard
        </h1>
        <p className="text-sm text-gray-600">
          Pipeline health, win rate, and federal-opportunity sync status.
        </p>
      </header>

      {/* ── Sync health (top — most actionable) ────────────────────── */}
      <GovTribeSyncHealth />

      {/* ── KPIs ────────────────────────────────────────────────────── */}
      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <KpiTile
          label="Active Pursuits"
          value={isLoading ? '—' : String(totals.active)}
          Icon={Activity}
          tone="active"
        />
        <KpiTile
          label="Awarded"
          value={isLoading ? '—' : String(totals.awarded)}
          Icon={Trophy}
          tone="award"
        />
        <KpiTile
          label="Win Rate"
          value={winRate === null ? '—' : `${winRate}%`}
          Icon={Award}
          tone="active"
        />
        <KpiTile
          label="Total Tracked"
          value={isLoading ? '—' : String(totals.total)}
          Icon={BarChart3}
          tone="neutral"
        />
      </div>

      {/* ── Stage breakdown ─────────────────────────────────────────── */}
      <section className="rounded-lg border border-gray-200 bg-white">
        <header className="flex items-center justify-between border-b border-gray-200 bg-gray-50 px-4 py-2.5">
          <h2 className="font-display text-sm font-bold uppercase tracking-widest text-gray-700">
            Pipeline by Stage
          </h2>
        </header>
        {isLoading || !counts ? (
          <div className="px-4 py-8 text-center text-sm text-gray-500">Loading…</div>
        ) : (
          <ul className="divide-y divide-gray-100">
            {(Object.keys(counts) as PipelineStage[]).map((stage) => (
              <li key={stage} className="flex items-center justify-between px-4 py-2.5">
                <span className="font-display text-xs font-bold uppercase tracking-wide text-gray-700">
                  {labelize(stage)}
                </span>
                <div className="flex items-center gap-2">
                  <StageBar count={counts[stage] ?? 0} max={totals.total || 1} />
                  <span className="w-10 text-right font-mono text-sm text-gray-700 tabular-nums">
                    {counts[stage] ?? 0}
                  </span>
                </div>
              </li>
            ))}
          </ul>
        )}
      </section>

      {/* ── Quick links ─────────────────────────────────────────────── */}
      <section className="grid gap-3 md:grid-cols-2">
        <QuickLink
          href="/precon/pipeline"
          title="Pipeline"
          description="Drag opportunities through the 8-stage pipeline."
        />
        <QuickLink
          href="/precon/bids"
          title="Bid Management"
          description="Bid packages, leveling, and Award & Activate."
        />
      </section>
    </div>
  );
}

// ── KPI tile ──────────────────────────────────────────────────────────────

function KpiTile({
  label,
  value,
  Icon,
  tone,
}: {
  label: string;
  value: string;
  Icon: React.ComponentType<{ className?: string }>;
  tone: 'active' | 'award' | 'neutral';
}) {
  const toneCls = {
    active: 'bg-[#B8232C]/5 ring-[#B8232C]/30 text-[#8a1920]',
    award: 'bg-[#0D0D0D] ring-black text-white',
    neutral: 'bg-gray-50 ring-gray-200 text-gray-700',
  }[tone];
  return (
    <div className={clsx('rounded-lg ring-1 px-4 py-3', toneCls)}>
      <div className="flex items-center justify-between">
        <span className="font-display text-[11px] font-bold uppercase tracking-widest opacity-80">
          {label}
        </span>
        <Icon className="h-4 w-4 opacity-70" aria-hidden />
      </div>
      <div className="mt-2 font-display text-3xl font-bold tabular-nums">{value}</div>
    </div>
  );
}

// ── Stage bar ─────────────────────────────────────────────────────────────

function StageBar({ count, max }: { count: number; max: number }) {
  const pct = Math.min(100, Math.round((count / max) * 100));
  return (
    <div className="h-2 w-32 overflow-hidden rounded bg-gray-100">
      <div
        className="h-full bg-[#B8232C] transition-all"
        style={{ width: `${pct}%` }}
        aria-hidden
      />
    </div>
  );
}

// ── Quick link ────────────────────────────────────────────────────────────

function QuickLink({
  href,
  title,
  description,
}: {
  href: string;
  title: string;
  description: string;
}) {
  return (
    <a
      href={href}
      className="group flex items-center justify-between rounded-lg border border-gray-200 bg-white px-4 py-3 transition hover:border-[#B8232C]/40 hover:shadow-sm"
    >
      <div>
        <div className="font-display text-sm font-bold uppercase tracking-wide text-[#0D0D0D]">
          {title}
        </div>
        <div className="text-xs text-gray-600">{description}</div>
      </div>
      <ChevronRight className="h-4 w-4 text-gray-400 transition group-hover:translate-x-0.5 group-hover:text-[#B8232C]" aria-hidden />
    </a>
  );
}

// ── Helpers ────────────────────────────────────────────────────────────────

function labelize(stage: PipelineStage): string {
  switch (stage) {
    case 'no_bid':
      return 'No Bid';
    default:
      return stage.charAt(0).toUpperCase() + stage.slice(1);
  }
}
