/**
 * Award & Activate confirmation modal.
 *
 * T06-10 acceptance: the modal MUST list all 11 sub-actions before any
 * action fires.  T06-11 acceptance: clicking Cancel changes nothing.
 *
 * The list of sub-actions is sourced from `AWARD_SUB_ACTIONS` in the types
 * module so it stays in lock-step with the backend's
 * `pipeline_service.award_and_activate` ordering.
 */

import { AlertTriangle, Loader2, X } from 'lucide-react';
import { useEffect, useId, useRef, useState } from 'react';

import { AWARD_SUB_ACTIONS } from '../api/types';

export interface AwardActivateModalProps {
  open: boolean;
  /** Display name of the winning bidder for the modal header. */
  winningBidder?: string | null;
  /** Display name of the project. */
  projectName?: string | null;
  /** Total amount of the winning bid (formatted string, currency-included). */
  winningAmount?: string | null;
  isSubmitting?: boolean;
  errorMessage?: string | null;
  onCancel: () => void;
  onConfirm: (reason: string) => void;
}

export function AwardActivateModal({
  open,
  winningBidder,
  projectName,
  winningAmount,
  isSubmitting = false,
  errorMessage,
  onCancel,
  onConfirm,
}: AwardActivateModalProps) {
  const headingId = useId();
  const reasonRef = useRef<HTMLTextAreaElement | null>(null);
  const [reason, setReason] = useState('');

  // Auto-focus the reason field for accessibility & keyboard flow.
  useEffect(() => {
    if (open) {
      // Defer to next tick so the focus lands after the modal mounts.
      const timer = window.setTimeout(() => reasonRef.current?.focus(), 0);
      return () => window.clearTimeout(timer);
    }
    return undefined;
  }, [open]);

  // Reset the reason field whenever the modal closes.
  useEffect(() => {
    if (!open) setReason('');
  }, [open]);

  // Esc closes the modal — never bypass the explicit Cancel path.
  useEffect(() => {
    if (!open) return undefined;
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && !isSubmitting) onCancel();
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [open, isSubmitting, onCancel]);

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 px-4 py-8"
      role="dialog"
      aria-modal="true"
      aria-labelledby={headingId}
    >
      <div className="relative flex max-h-full w-full max-w-2xl flex-col overflow-hidden rounded-lg bg-white shadow-2xl">
        {/* ── Header ─────────────────────────────────────────────────── */}
        <div className="flex items-start justify-between gap-4 border-b border-gray-200 bg-[#0D0D0D] px-6 py-4 text-white">
          <div>
            <h2 id={headingId} className="font-display text-xl font-bold uppercase tracking-tight">
              Award &amp; Activate
            </h2>
            {projectName && (
              <p className="mt-0.5 text-sm text-gray-300">
                {projectName}
              </p>
            )}
          </div>
          <button
            type="button"
            onClick={onCancel}
            disabled={isSubmitting}
            aria-label="Cancel"
            className="rounded p-1 text-gray-400 hover:bg-white/10 hover:text-white disabled:opacity-50"
          >
            <X className="h-5 w-5" aria-hidden />
          </button>
        </div>

        {/* ── Body ──────────────────────────────────────────────────── */}
        <div className="flex-1 space-y-5 overflow-y-auto px-6 py-5">
          {/* Winner summary */}
          {(winningBidder || winningAmount) && (
            <div className="rounded-lg border border-[#B8232C]/40 bg-[#B8232C]/5 px-4 py-3">
              <div className="font-display text-xs font-bold uppercase tracking-widest text-[#8a1920]">
                Winning Bid
              </div>
              <div className="mt-1 flex items-baseline justify-between gap-4">
                <span className="text-base font-semibold text-[#0D0D0D]">
                  {winningBidder ?? 'Unnamed bidder'}
                </span>
                {winningAmount && (
                  <span className="font-mono text-lg font-bold text-[#B8232C]">
                    {winningAmount}
                  </span>
                )}
              </div>
            </div>
          )}

          {/* Sub-action list — REQUIRED by T06-10 */}
          <section>
            <h3 className="mb-2 font-display text-sm font-bold uppercase tracking-widest text-gray-700">
              The following 11 actions will execute in a single transaction:
            </h3>
            <ol className="space-y-1.5">
              {AWARD_SUB_ACTIONS.map((action, idx) => (
                <li
                  key={action.key}
                  className="flex items-start gap-3 rounded border border-gray-100 bg-gray-50 px-3 py-2"
                >
                  <span className="font-mono text-xs font-bold text-[#B8232C] tabular-nums">
                    {String(idx + 1).padStart(2, '0')}
                  </span>
                  <span className="text-sm text-gray-800">{action.label}</span>
                </li>
              ))}
            </ol>
            <p className="mt-3 flex items-start gap-2 rounded bg-amber-50 px-3 py-2 text-xs text-amber-900 ring-1 ring-amber-200">
              <AlertTriangle className="mt-0.5 h-4 w-4 flex-shrink-0" aria-hidden />
              <span>
                If any single action fails the entire transaction rolls back —
                the project remains in <span className="font-mono">bidding</span>,
                and no PO, document, or notification is written.
              </span>
            </p>
          </section>

          {/* Optional reason */}
          <div>
            <label htmlFor={`${headingId}-reason`} className="block font-display text-xs font-bold uppercase tracking-widest text-gray-700">
              Reason / Notes (optional)
            </label>
            <textarea
              id={`${headingId}-reason`}
              ref={reasonRef}
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              rows={2}
              maxLength={2000}
              disabled={isSubmitting}
              className="mt-1 w-full rounded border border-gray-300 px-3 py-2 text-sm focus:border-[#B8232C] focus:outline-none focus:ring-1 focus:ring-[#B8232C]"
              placeholder="e.g. Lowest qualified bid; references checked"
            />
          </div>

          {errorMessage && (
            <div className="rounded border border-[#B8232C] bg-[#B8232C]/10 px-3 py-2 text-sm text-[#8a1920]">
              {errorMessage}
            </div>
          )}
        </div>

        {/* ── Footer ─────────────────────────────────────────────────── */}
        <div className="flex justify-end gap-2 border-t border-gray-200 bg-gray-50 px-6 py-4">
          <button
            type="button"
            onClick={onCancel}
            disabled={isSubmitting}
            className="rounded border border-gray-300 bg-white px-4 py-2 text-sm font-display font-bold uppercase tracking-wide text-gray-700 hover:bg-gray-100 disabled:opacity-50"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={() => onConfirm(reason)}
            disabled={isSubmitting}
            className="inline-flex items-center gap-2 rounded bg-[#B8232C] px-4 py-2 font-display text-sm font-bold uppercase tracking-wide text-white shadow-sm hover:bg-[#8a1920] disabled:opacity-50"
          >
            {isSubmitting && <Loader2 className="h-4 w-4 animate-spin" aria-hidden />}
            {isSubmitting ? 'Awarding…' : 'Award & Activate'}
          </button>
        </div>
      </div>
    </div>
  );
}
