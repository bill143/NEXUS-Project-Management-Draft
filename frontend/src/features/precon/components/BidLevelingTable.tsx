/**
 * Side-by-side bid leveling matrix.
 *
 * Each column is a snapshot from `oe_nexus_precon_bid_level`.  Rows show the
 * raw bid, applied adjustments (one row per adjustment), the running
 * adjusted total, and a "Mark winner" button.  The lowest adjusted total is
 * visually highlighted but the user picks the winner manually — leveling is
 * advisory, not automatic.
 */

import { Award, Check, Plus } from 'lucide-react';
import clsx from 'clsx';

import type { BidLevelResponse } from '../api/types';

export interface BidLevelingTableProps {
  levels: BidLevelResponse[];
  isLoading?: boolean;
  onMarkWinner?: (levelId: string) => void;
  onAddAdjustment?: (levelId: string) => void;
  bidderNameFor?: (contactId: string | null) => string;
}

export function BidLevelingTable({
  levels,
  isLoading,
  onMarkWinner,
  onAddAdjustment,
  bidderNameFor,
}: BidLevelingTableProps) {
  if (isLoading) {
    return (
      <div className="rounded-lg border border-gray-200 bg-white p-8 text-center text-sm text-gray-500">
        Loading leveling snapshots…
      </div>
    );
  }
  if (levels.length === 0) {
    return (
      <div className="rounded-lg border border-dashed border-gray-300 bg-gray-50 p-8 text-center">
        <p className="font-display text-sm font-bold uppercase tracking-wide text-gray-700">
          No bids leveled yet
        </p>
        <p className="mt-1 text-xs text-gray-500">
          Once estimating fires the leveling engine, snapshots appear here.
        </p>
      </div>
    );
  }

  // Lowest adjusted total visually flagged for the estimator's eye.
  const lowestId = lowestAdjustedId(levels);

  return (
    <div className="overflow-x-auto rounded-lg border border-gray-200 bg-white">
      <table className="w-full border-collapse text-sm">
        <thead className="bg-gray-50">
          <tr>
            <th className="sticky left-0 z-10 bg-gray-50 px-4 py-3 text-left font-display text-xs font-bold uppercase tracking-wider text-gray-600">
              Bidder
            </th>
            <th className="px-4 py-3 text-right font-display text-xs font-bold uppercase tracking-wider text-gray-600">
              Raw
            </th>
            <th className="px-4 py-3 text-left font-display text-xs font-bold uppercase tracking-wider text-gray-600">
              Adjustments
            </th>
            <th className="px-4 py-3 text-right font-display text-xs font-bold uppercase tracking-wider text-gray-600">
              Adjusted
            </th>
            <th className="px-4 py-3 text-center font-display text-xs font-bold uppercase tracking-wider text-gray-600">
              Status
            </th>
          </tr>
        </thead>
        <tbody>
          {levels.map((level) => {
            const isLowest = level.id === lowestId;
            const bidderName =
              (bidderNameFor && bidderNameFor(level.bidder_contact_id)) ||
              (level.bidder_contact_id ?? 'Unknown bidder');
            return (
              <tr
                key={level.id}
                className={clsx(
                  'border-t border-gray-100',
                  level.is_winner && 'bg-[#B8232C]/5',
                )}
              >
                <td className="sticky left-0 z-10 bg-white px-4 py-3 font-medium text-[#0D0D0D]">
                  {bidderName}
                </td>
                <td className="px-4 py-3 text-right font-mono text-sm text-gray-700">
                  ${formatAmount(level.raw_amount)}
                </td>
                <td className="px-4 py-3">
                  {level.adjustments.length === 0 ? (
                    <span className="text-xs text-gray-400">—</span>
                  ) : (
                    <ul className="space-y-1">
                      {level.adjustments.map((adj, i) => (
                        <li
                          key={i}
                          className="flex items-center justify-between gap-2 text-xs"
                        >
                          <span className="text-gray-600">
                            {adj.label || adj.reason}
                          </span>
                          <span className="font-mono text-gray-700">
                            {Number(adj.amount) >= 0 ? '+' : ''}${formatAmount(adj.amount)}
                          </span>
                        </li>
                      ))}
                    </ul>
                  )}
                  {onAddAdjustment && (
                    <button
                      type="button"
                      onClick={() => onAddAdjustment(level.id)}
                      className="mt-2 inline-flex items-center gap-1 text-[11px] text-gray-500 hover:text-[#B8232C]"
                    >
                      <Plus className="h-3 w-3" aria-hidden /> Add adjustment
                    </button>
                  )}
                </td>
                <td
                  className={clsx(
                    'px-4 py-3 text-right font-mono text-sm font-bold',
                    isLowest && !level.is_winner && 'text-emerald-700',
                    level.is_winner && 'text-[#B8232C]',
                  )}
                >
                  ${formatAmount(level.adjusted_amount)}
                </td>
                <td className="px-4 py-3 text-center">
                  {level.is_winner ? (
                    <span className="inline-flex items-center gap-1 rounded bg-[#B8232C] px-2 py-1 text-xs font-bold text-white">
                      <Award className="h-3.5 w-3.5" aria-hidden /> Winner
                    </span>
                  ) : onMarkWinner ? (
                    <button
                      type="button"
                      onClick={() => onMarkWinner(level.id)}
                      className="inline-flex items-center gap-1 rounded border border-gray-300 px-2 py-1 text-xs font-medium text-gray-700 hover:border-[#B8232C] hover:text-[#B8232C]"
                    >
                      <Check className="h-3.5 w-3.5" aria-hidden /> Mark
                    </button>
                  ) : (
                    <span className="text-xs text-gray-400">—</span>
                  )}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

// ── Helpers ────────────────────────────────────────────────────────────────

function formatAmount(value: string): string {
  const n = Number(value);
  if (!Number.isFinite(n)) return value;
  return Math.abs(n).toLocaleString(undefined, {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

function lowestAdjustedId(levels: BidLevelResponse[]): string | null {
  if (levels.length === 0) return null;
  let best: BidLevelResponse | null = null;
  for (const l of levels) {
    if (!best || Number(l.adjusted_amount) < Number(best.adjusted_amount)) {
      best = l;
    }
  }
  return best?.id ?? null;
}
