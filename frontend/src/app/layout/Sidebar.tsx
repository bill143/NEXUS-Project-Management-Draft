import { useState } from 'react';
import { NavLink, useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import clsx from 'clsx';
import {
  FolderOpen,
  Table2,
  CalendarDays,
  ClipboardList,
  HelpCircle,
  HardHat,
  History,
  X,
  ChevronRight,
  Sparkles,
  Users,
  type LucideIcon,
} from 'lucide-react';
import { useProjectContextStore } from '@/stores/useProjectContextStore';
import { useRecentStore } from '@/stores/useRecentStore';
import { useSidebarBadges } from '@/shared/hooks/useSidebarBadges';

/**
 * Project context sidebar.
 *
 * After the module navigation moved into the top-nav `ModulesNavButton`,
 * the sidebar's only job is to show the user *what they are working on*
 * — the active project, its open-item counts, and the entities they've
 * touched recently. The sidebar deliberately renders nothing else; the
 * brand and the navigation taxonomy now belong to the header.
 *
 * Layout dimensions (w-sidebar / h-header) are unchanged so AppLayout's
 * desktop pl-sidebar offset still lines up.
 */
export function Sidebar({ onClose }: { onClose?: () => void }) {
  const { t } = useTranslation();
  const activeProjectId = useProjectContextStore((s) => s.activeProjectId);
  const activeProjectName = useProjectContextStore((s) => s.activeProjectName);
  const activeBOQId = useProjectContextStore((s) => s.activeBOQId);
  const badges = useSidebarBadges();

  return (
    <aside
      data-tour="sidebar"
      className={clsx(
        'flex h-full w-sidebar flex-col',
        'border-r border-border-light bg-surface-primary',
      )}
    >
      {/* Header strip — mirrors header height so the sidebar and top-nav
          baselines align. The mobile close button lives here. */}
      <div className="flex h-header items-center justify-between px-5 border-b border-border-light">
        <span className="text-2xs font-semibold uppercase tracking-wider text-content-tertiary">
          {t('sidebar.context_title', { defaultValue: 'Project context' })}
        </span>
        {onClose && (
          <button
            onClick={onClose}
            className="lg:hidden flex h-7 w-7 min-h-[44px] min-w-[44px] items-center justify-center rounded-lg text-content-tertiary hover:bg-surface-secondary hover:text-content-primary transition-colors"
            aria-label={t('common.close', { defaultValue: 'Close' })}
          >
            <X size={16} />
          </button>
        )}
      </div>

      <div className="flex-1 overflow-y-auto px-3 py-4 space-y-5">
        {activeProjectId ? (
          <ActiveProjectCard
            projectId={activeProjectId}
            projectName={activeProjectName}
            boqId={activeBOQId}
            badges={badges}
            onNavigate={onClose}
          />
        ) : (
          <EmptyProjectCard onNavigate={onClose} />
        )}

        <RecentSection onNavigate={onClose} />
      </div>
    </aside>
  );
}

/* ── Active project card ────────────────────────────────────────────── */

function ActiveProjectCard({
  projectId,
  projectName,
  boqId,
  badges,
  onNavigate,
}: {
  projectId: string;
  projectName: string;
  boqId: string | null;
  badges: { tasks: number; rfi: number; safety: number };
  onNavigate?: () => void;
}) {
  const { t } = useTranslation();
  const initials = (projectName || 'P').slice(0, 2).toUpperCase();
  const hasAnyBadge = badges.tasks > 0 || badges.rfi > 0 || badges.safety > 0;

  return (
    <section className="space-y-3">
      <div
        className={clsx(
          'rounded-xl border border-oe-blue/20 bg-gradient-to-br from-oe-blue/5 to-transparent',
          'p-3.5',
        )}
      >
        <div className="flex items-center gap-2.5 mb-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-oe-blue text-white text-sm font-semibold shrink-0">
            {initials}
          </div>
          <div className="min-w-0 flex-1">
            <p className="text-[10px] font-medium uppercase tracking-wider text-content-tertiary">
              {t('common.active_project', { defaultValue: 'Active project' })}
            </p>
            <p className="text-sm font-semibold text-content-primary truncate">
              {projectName || t('schedule.untitled_project', { defaultValue: 'Untitled project' })}
            </p>
          </div>
        </div>

        <NavLink
          to={`/projects/${projectId}`}
          onClick={onNavigate}
          className="flex items-center justify-between rounded-lg bg-surface-primary/60 px-2.5 py-2 text-xs font-medium text-oe-blue hover:bg-surface-primary transition-colors"
        >
          <span className="flex items-center gap-2">
            <FolderOpen size={13} strokeWidth={1.75} />
            {t('projects.open_details', { defaultValue: 'Open project' })}
          </span>
          <ChevronRight size={13} strokeWidth={2} />
        </NavLink>

        {boqId && (
          <NavLink
            to={`/boq/${boqId}`}
            onClick={onNavigate}
            className="mt-1.5 flex items-center justify-between rounded-lg bg-surface-primary/60 px-2.5 py-2 text-xs font-medium text-content-secondary hover:bg-surface-primary hover:text-content-primary transition-colors"
          >
            <span className="flex items-center gap-2">
              <Table2 size={13} strokeWidth={1.75} />
              {t('boq.open_active', { defaultValue: 'Open active BOQ' })}
            </span>
            <ChevronRight size={13} strokeWidth={2} />
          </NavLink>
        )}
      </div>

      {/* Open-items grid — only render if any badge is non-zero so the
          sidebar doesn't display three "0"s on a fresh project. */}
      {hasAnyBadge && (
        <div className="grid grid-cols-3 gap-1.5">
          <MetricTile icon={ClipboardList} label={t('tasks.title', { defaultValue: 'Tasks' })} value={badges.tasks} to="/tasks" onNavigate={onNavigate} />
          <MetricTile icon={HelpCircle} label={t('rfi.title', { defaultValue: 'RFIs' })} value={badges.rfi} to="/rfi" onNavigate={onNavigate} />
          <MetricTile icon={HardHat} label={t('safety.title', { defaultValue: 'Safety' })} value={badges.safety} to="/safety" onNavigate={onNavigate} />
        </div>
      )}

      <QuickLinks projectId={projectId} onNavigate={onNavigate} />
    </section>
  );
}

function MetricTile({
  icon: Icon,
  label,
  value,
  to,
  onNavigate,
}: {
  icon: LucideIcon;
  label: string;
  value: number;
  to: string;
  onNavigate?: () => void;
}) {
  return (
    <NavLink
      to={to}
      onClick={onNavigate}
      title={`${value} ${label}`}
      className="flex flex-col items-start rounded-lg border border-border-light bg-surface-primary px-2 py-2 hover:border-oe-blue/30 hover:bg-oe-blue/[0.03] transition-colors"
    >
      <Icon size={13} strokeWidth={1.75} className="text-content-tertiary mb-1" />
      <span className="text-base font-semibold tabular-nums text-content-primary leading-none">
        {value > 99 ? '99+' : value}
      </span>
      <span className="mt-1 text-[10px] uppercase tracking-wide text-content-tertiary truncate w-full">
        {label}
      </span>
    </NavLink>
  );
}

function QuickLinks({ projectId, onNavigate }: { projectId: string; onNavigate?: () => void }) {
  const { t } = useTranslation();
  const links: Array<{ labelKey: string; defaultLabel: string; to: string; icon: LucideIcon }> = [
    { labelKey: 'schedule.title', defaultLabel: 'Schedule', to: '/schedule', icon: CalendarDays },
    { labelKey: 'contacts.title', defaultLabel: 'Contacts', to: '/contacts', icon: Users },
    { labelKey: 'nav.ai_advisor', defaultLabel: 'AI advisor', to: '/advisor', icon: Sparkles },
  ];

  return (
    <div>
      <p className="px-2 mb-1.5 text-2xs font-semibold uppercase tracking-wider text-content-tertiary">
        {t('sidebar.shortcuts', { defaultValue: 'Shortcuts' })}
      </p>
      <ul className="space-y-0.5">
        {links.map((l) => {
          const Icon = l.icon;
          return (
            <li key={l.to}>
              <NavLink
                to={l.to}
                onClick={onNavigate}
                className={({ isActive }) =>
                  clsx(
                    'flex items-center gap-2 rounded-md px-2 py-1.5 text-[13px] font-medium transition-colors',
                    isActive
                      ? 'bg-oe-blue-subtle text-oe-blue'
                      : 'text-content-secondary hover:bg-surface-secondary hover:text-content-primary',
                  )
                }
              >
                <Icon size={15} strokeWidth={1.75} className="shrink-0" />
                <span className="truncate">{t(l.labelKey, { defaultValue: l.defaultLabel })}</span>
              </NavLink>
            </li>
          );
        })}
      </ul>
      {/* Hidden marker so e2e and unit tests can assert the sidebar
          is project-scoped without depending on translated strings. */}
      <span data-testid={`sidebar-project-${projectId}`} className="sr-only">
        {projectId}
      </span>
    </div>
  );
}

/* ── Empty state ────────────────────────────────────────────────────── */

function EmptyProjectCard({ onNavigate }: { onNavigate?: () => void }) {
  const { t } = useTranslation();
  const navigate = useNavigate();
  return (
    <section className="space-y-3">
      <div className="rounded-xl border border-dashed border-border bg-surface-secondary/40 p-4 text-center">
        <div className="mx-auto flex h-10 w-10 items-center justify-center rounded-lg bg-surface-tertiary text-content-tertiary mb-2.5">
          <FolderOpen size={18} strokeWidth={1.75} />
        </div>
        <p className="text-sm font-semibold text-content-primary mb-1">
          {t('sidebar.no_project_title', { defaultValue: 'No active project' })}
        </p>
        <p className="text-xs text-content-tertiary mb-3 leading-snug">
          {t('sidebar.no_project_hint', {
            defaultValue: 'Pick a project to see open RFIs, tasks, and shortcuts here.',
          })}
        </p>
        <button
          type="button"
          onClick={() => {
            onNavigate?.();
            navigate('/projects');
          }}
          className="inline-flex items-center gap-1.5 rounded-lg bg-oe-blue px-3 py-1.5 text-xs font-semibold text-white hover:opacity-90 transition-opacity"
        >
          <FolderOpen size={13} strokeWidth={2} />
          {t('projects.browse_all', { defaultValue: 'Browse projects' })}
        </button>
      </div>
    </section>
  );
}

/* ── Recent items ───────────────────────────────────────────────────── */

const RECENT_TYPE_ICONS: Record<string, LucideIcon> = {
  project: FolderOpen,
  boq: Table2,
  schedule: CalendarDays,
  task: ClipboardList,
  rfi: HelpCircle,
  contact: Users,
};

function RecentSection({ onNavigate }: { onNavigate?: () => void }) {
  const { t } = useTranslation();
  const items = useRecentStore((s) => s.items);
  const clearRecent = useRecentStore((s) => s.clearRecent);

  if (items.length === 0) return null;

  return (
    <section>
      <div className="flex items-center justify-between px-2 mb-1.5">
        <p className="text-2xs font-semibold uppercase tracking-wider text-content-tertiary">
          {t('nav.recent', { defaultValue: 'Recent' })}
        </p>
        <button
          onClick={clearRecent}
          className="text-[10px] text-content-tertiary hover:text-content-secondary transition-colors"
          title={t('common.clear', { defaultValue: 'Clear' })}
        >
          {t('common.clear', { defaultValue: 'Clear' })}
        </button>
      </div>
      <ul className="space-y-0.5">
        {items.map((item) => {
          const Icon = RECENT_TYPE_ICONS[item.type] ?? FolderOpen;
          return (
            <li key={item.id}>
              <NavLink
                to={item.url}
                onClick={onNavigate}
                title={item.title}
                className="flex items-center gap-2 rounded-md px-2 py-1.5 text-[12px] font-medium text-content-secondary hover:bg-surface-secondary hover:text-content-primary transition-colors"
              >
                <Icon size={13} strokeWidth={1.75} className="shrink-0 text-content-tertiary" />
                <span className="truncate flex-1">{item.title}</span>
              </NavLink>
            </li>
          );
        })}
      </ul>
    </section>
  );
}

/* ── Floating buttons (kept — still referenced from AppLayout) ──────── */

/**
 * Floating Recent button — rendered by AppLayout in the bottom-right
 * corner as a small shortcut to recent items even on full-bleed pages
 * where the sidebar is hidden. The list inside the sidebar above is the
 * primary surface; this is the always-on-screen secondary one.
 */
export function FloatingRecentButton() {
  const { t } = useTranslation();
  const recentItems = useRecentStore((s) => s.items);
  const [open, setOpen] = useState(false);

  if (recentItems.length === 0) return null;
  const displayed = recentItems.slice(0, 5);

  return (
    <div className="fixed bottom-24 end-4 z-40">
      {open && (
        <div className="absolute bottom-12 end-0 w-72 rounded-xl border border-border-light bg-surface-primary shadow-xl overflow-hidden animate-in fade-in slide-in-from-bottom-2 duration-150">
          <div className="flex items-center justify-between px-4 py-2.5 border-b border-border-light">
            <span className="text-xs font-semibold text-content-primary">{t('nav.recent', { defaultValue: 'Recent' })}</span>
            <button onClick={() => setOpen(false)} className="p-0.5 rounded text-content-tertiary hover:text-content-primary">
              <X size={14} />
            </button>
          </div>
          <ul className="py-1.5 max-h-60 overflow-y-auto">
            {displayed.map((item) => {
              const Icon = RECENT_TYPE_ICONS[item.type] ?? FolderOpen;
              return (
                <li key={item.id}>
                  <NavLink
                    to={item.url}
                    onClick={() => setOpen(false)}
                    title={item.title}
                    className="flex items-center gap-2.5 px-4 py-2 text-[13px] font-medium text-content-secondary hover:bg-surface-secondary hover:text-content-primary transition-all"
                  >
                    <Icon size={14} strokeWidth={1.75} className="shrink-0 text-content-tertiary" />
                    <span className="truncate flex-1">{item.title}</span>
                    <span className="text-[10px] text-content-quaternary shrink-0 tabular-nums">
                      {new Date(item.visitedAt).toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit' })}
                    </span>
                  </NavLink>
                </li>
              );
            })}
          </ul>
        </div>
      )}

      <button
        onClick={() => setOpen((p) => !p)}
        className={clsx(
          'w-10 h-10 rounded-full flex items-center justify-center shadow-lg border transition-all duration-200 hover:scale-105 active:scale-95',
          open
            ? 'bg-oe-blue text-white border-oe-blue shadow-oe-blue/20'
            : 'bg-surface-primary text-content-secondary border-border-light hover:border-oe-blue/30 hover:text-oe-blue',
        )}
        title={t('nav.recent', { defaultValue: 'Recent' })}
      >
        <History size={18} strokeWidth={2} />
      </button>
    </div>
  );
}
