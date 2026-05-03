/**
 * Bid Management — bid packages table, leveling matrix, and Award & Activate.
 *
 * The page is split into three regions: a list of tender packages on the
 * left rail, the leveling matrix for the selected package, and the
 * Award & Activate flow that fires the 11-action atomic transaction.
 */

import { useEffect, useMemo, useState } from 'react';
import { Navigate, useSearchParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { Award, Layers, RefreshCw } from 'lucide-react';
import clsx from 'clsx';

import { useAuthStore } from '@/stores/useAuthStore';
import { useToastStore } from '@/stores/useToastStore';
import { apiGet } from '@/shared/lib/api';

import { AwardActivateModal } from './components/AwardActivateModal';
import { BidLevelingTable } from './components/BidLevelingTable';
import {
  useApplyAdjustment,
  useBidLevels,
  useGenerateLeveling,
  useMarkWinner,
} from './hooks/useBidLeveling';
import { useAwardAndActivate } from './hooks/usePipeline';
import { isPreconRole } from './api/types';

interface PackageSummary {
  id: string;
  name: string;
  status: string;
  project_id: string;
  project_name?: string | null;
  bid_count?: number;
}

export function BidManagementPage() {
  const role = useAuthStore((s) => s.userRole);
  const addToast = useToastStore((s) => s.addToast);
  const [searchParams, setSearchParams] = useSearchParams();
  const selectedPackageId = searchParams.get('package');

  if (!isPreconRole(role)) {
    return <Navigate to="/" replace />;
  }

  const { data: packages, isLoading: packagesLoading } = useQuery<PackageSummary[]>({
    queryKey: ['precon', 'tender-packages'],
    queryFn: async () => {
      try {
        return await apiGet<PackageSummary[]>('/v1/tendering/packages/?limit=500');
      } catch {
        return [];
      }
    },
  });

  // Auto-select the first package when none picked.
  useEffect(() => {
    if (!selectedPackageId && packages && packages.length > 0) {
      const first = packages[0];
      if (first) {
        setSearchParams({ package: first.id }, { replace: true });
      }
    }
  }, [selectedPackageId, packages, setSearchParams]);

  return (
    <div className="flex flex-col gap-4">
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="font-display text-3xl font-bold uppercase tracking-tight text-[#0D0D0D]">
            Bid Management
          </h1>
          <p className="text-sm text-gray-600">
            Tender packages, leveling, and Award &amp; Activate.
          </p>
        </div>
      </header>

      <div className="grid gap-4 lg:grid-cols-[280px_1fr]">
        <PackageList
          packages={packages ?? []}
          isLoading={packagesLoading}
          selectedId={selectedPackageId}
          onSelect={(id) => setSearchParams({ package: id })}
        />
        {selectedPackageId ? (
          <PackageDetail
            packageId={selectedPackageId}
            packageMeta={packages?.find((p) => p.id === selectedPackageId) ?? null}
            addToast={addToast}
          />
        ) : (
          <div className="rounded-lg border border-dashed border-gray-300 bg-gray-50 p-12 text-center text-sm text-gray-500">
            Select a package on the left to view its leveling matrix.
          </div>
        )}
      </div>
    </div>
  );
}

// ── Package list ──────────────────────────────────────────────────────────

function PackageList({
  packages,
  isLoading,
  selectedId,
  onSelect,
}: {
  packages: PackageSummary[];
  isLoading: boolean;
  selectedId: string | null;
  onSelect: (id: string) => void;
}) {
  return (
    <aside className="overflow-hidden rounded-lg border border-gray-200 bg-white">
      <div className="border-b border-gray-200 bg-gray-50 px-3 py-2 font-display text-xs font-bold uppercase tracking-widest text-gray-700">
        Tender Packages
      </div>
      {isLoading ? (
        <div className="px-3 py-6 text-center text-sm text-gray-500">Loading…</div>
      ) : packages.length === 0 ? (
        <div className="px-3 py-6 text-center text-sm text-gray-500">
          No packages yet.
        </div>
      ) : (
        <ul className="divide-y divide-gray-100">
          {packages.map((p) => (
            <li key={p.id}>
              <button
                type="button"
                onClick={() => onSelect(p.id)}
                className={clsx(
                  'flex w-full flex-col items-start gap-0.5 px-3 py-2.5 text-left transition',
                  selectedId === p.id
                    ? 'bg-[#B8232C]/10 text-[#0D0D0D]'
                    : 'hover:bg-gray-50',
                )}
              >
                <span className="line-clamp-1 font-medium">{p.name}</span>
                <span className="font-mono text-[11px] text-gray-500">
                  {p.project_name ?? p.project_id.slice(0, 8)} · {p.status}
                </span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </aside>
  );
}

// ── Package detail (leveling + award) ─────────────────────────────────────

type AddToastFn = (
  toast: { type: 'success' | 'error' | 'warning' | 'info'; title: string; message?: string },
  options?: { duration?: number },
) => string;

function PackageDetail({
  packageId,
  packageMeta,
  addToast,
}: {
  packageId: string;
  packageMeta: PackageSummary | null;
  addToast: AddToastFn;
}) {
  const { data: levels, isLoading } = useBidLevels(packageId);
  const generate = useGenerateLeveling(packageId);
  const adjust = useApplyAdjustment(packageId);
  const markWinner = useMarkWinner(packageId);
  const award = useAwardAndActivate();

  const winningLevel = useMemo(
    () => levels?.find((l) => l.is_winner) ?? null,
    [levels],
  );

  const [awardModalOpen, setAwardModalOpen] = useState(false);
  const [awardError, setAwardError] = useState<string | null>(null);

  const handleAddAdjustment = (levelId: string) => {
    const reason = window.prompt('Adjustment reason (e.g. "scope gap")');
    if (!reason) return;
    const amount = window.prompt('Adjustment amount (signed; e.g. 500 or -250)');
    if (!amount) return;
    adjust.mutate(
      { levelId, amount, reason },
      {
        onError: (err) =>
          addToast({ type: 'error', title: 'Adjustment failed', message: (err as Error).message }),
        onSuccess: () =>
          addToast({ type: 'success', title: 'Adjustment applied' }),
      },
    );
  };

  const handleMarkWinner = (levelId: string) => {
    markWinner.mutate(levelId, {
      onError: (err) =>
        addToast({ type: 'error', title: 'Failed to mark winner', message: (err as Error).message }),
      onSuccess: () =>
        addToast({ type: 'success', title: 'Winner marked' }),
    });
  };

  const openAwardModal = () => {
    setAwardError(null);
    setAwardModalOpen(true);
  };

  const handleConfirmAward = (reason: string) => {
    if (!winningLevel || !packageMeta) return;
    setAwardError(null);
    award.mutate(
      {
        projectId: packageMeta.project_id,
        winning_bid_id: winningLevel.id,
        reason: reason || null,
      },
      {
        onError: (err) => {
          setAwardError((err as Error).message ?? 'Award failed');
        },
        onSuccess: (result) => {
          setAwardModalOpen(false);
          addToast({
            type: 'success',
            title: 'Award & Activate complete',
            message: `${result.sub_actions_completed.length} sub-actions executed`,
          });
        },
      },
    );
  };

  return (
    <section className="flex flex-col gap-3">
      <div className="flex flex-wrap items-end justify-between gap-2">
        <div>
          <h2 className="font-display text-xl font-bold uppercase tracking-tight text-[#0D0D0D]">
            {packageMeta?.name ?? 'Package'}
          </h2>
          <p className="font-mono text-xs text-gray-500">
            {packageMeta ? `${packageMeta.project_name ?? packageMeta.project_id} · ${packageMeta.status}` : '—'}
          </p>
        </div>
        <div className="flex gap-2">
          <button
            type="button"
            onClick={() =>
              generate.mutate(undefined, {
                onError: (err) =>
                  addToast({ type: 'error', title: 'Leveling failed', message: (err as Error).message }),
              })
            }
            disabled={generate.isPending}
            className="inline-flex items-center gap-1.5 rounded border border-gray-300 bg-white px-3 py-1.5 text-xs font-display font-bold uppercase tracking-wide text-gray-700 hover:border-[#B8232C] hover:text-[#B8232C] disabled:opacity-50"
          >
            <RefreshCw className={clsx('h-3.5 w-3.5', generate.isPending && 'animate-spin')} aria-hidden />
            {generate.isPending ? 'Leveling…' : 'Generate Leveling'}
          </button>
          <button
            type="button"
            disabled={!winningLevel}
            onClick={openAwardModal}
            className="inline-flex items-center gap-1.5 rounded bg-[#B8232C] px-3 py-1.5 text-xs font-display font-bold uppercase tracking-wide text-white hover:bg-[#8a1920] disabled:cursor-not-allowed disabled:opacity-50"
          >
            <Award className="h-3.5 w-3.5" aria-hidden />
            Award &amp; Activate
          </button>
        </div>
      </div>

      <BidLevelingTable
        levels={levels ?? []}
        isLoading={isLoading}
        onAddAdjustment={handleAddAdjustment}
        onMarkWinner={handleMarkWinner}
      />

      {!winningLevel && (levels?.length ?? 0) > 0 && (
        <div className="rounded border border-amber-300 bg-amber-50 px-3 py-2 text-xs text-amber-900">
          <Layers className="mr-1 inline h-3.5 w-3.5 align-text-bottom" aria-hidden />
          Mark a winner before opening the Award &amp; Activate flow.
        </div>
      )}

      <AwardActivateModal
        open={awardModalOpen}
        winningBidder={winningLevel?.bidder_contact_id ?? 'Selected bidder'}
        winningAmount={winningLevel ? `$${winningLevel.adjusted_amount}` : null}
        projectName={packageMeta?.project_name ?? null}
        isSubmitting={award.isPending}
        errorMessage={awardError}
        onCancel={() => setAwardModalOpen(false)}
        onConfirm={handleConfirmAward}
      />
    </section>
  );
}
