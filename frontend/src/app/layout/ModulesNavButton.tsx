import { useState, useRef, useEffect, useCallback, useMemo } from 'react';
import { NavLink, useLocation } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import clsx from 'clsx';
import { ChevronDown, Grid3x3, Plus } from 'lucide-react';
import { navGroups, type NavItem } from './navGroups';
import { useModuleStore } from '@/stores/useModuleStore';
import { useViewModeStore } from '@/stores/useViewModeStore';
import { useSidebarBadges } from '@/shared/hooks/useSidebarBadges';
import { getModuleNavItems } from '@/modules/_registry';

/**
 * Modules mega-menu — the centerpiece of the top-nav refactor.
 *
 * Button sits in the Header next to the brand. When opened it expands a
 * single wide panel that lays out all 9 nav groups in a 3-column grid.
 * Preserves every behaviour the old sidebar had:
 *   - per-group filtering by `useModuleStore.isModuleEnabled`
 *   - advanced-mode hiding via `useViewModeStore`
 *   - dynamic module injection via `getModuleNavItems(groupId)`
 *   - numeric badges (tasks/rfi/safety) from `useSidebarBadges`
 *   - the BETA / NEW tag styling and the "Add module" CTA
 *
 * Click outside or Escape to close. Closing on navigation is implicit
 * because <NavLink onClick={close}> fires before route change.
 */
export function ModulesNavButton() {
  const { t } = useTranslation();
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const location = useLocation();
  const { isModuleEnabled } = useModuleStore();
  const isAdvanced = useViewModeStore((s) => s.isAdvanced);
  const badgeCounts = useSidebarBadges();

  const badgeMap: Record<string, number> = {
    '/tasks': badgeCounts.tasks,
    '/rfi': badgeCounts.rfi,
    '/safety': badgeCounts.safety,
  };

  const close = useCallback(() => setOpen(false), []);

  // Close on click outside.
  useEffect(() => {
    if (!open) return;
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) close();
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, [open, close]);

  // Close on Escape.
  useEffect(() => {
    if (!open) return;
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') close();
    };
    document.addEventListener('keydown', handler);
    return () => document.removeEventListener('keydown', handler);
  }, [open, close]);

  // Active state — button glows when the current route matches any module
  // item, so the user always sees where they are without scanning the
  // panel.
  const renderedGroups = useMemo(() => {
    return navGroups
      .filter((g) => !g.hideInSimple || isAdvanced)
      .map((group) => {
        const dynamicItems: NavItem[] = getModuleNavItems(group.id)
          .filter((mi) => {
            const moduleId = mi.labelKey.split('.')[1] ?? mi.to.slice(1);
            return isModuleEnabled(moduleId);
          })
          .map((mi) => ({
            labelKey: mi.labelKey,
            to: mi.to,
            icon: mi.icon,
            moduleKey: mi.to.slice(1),
            advancedOnly: mi.advancedOnly,
          }));

        const allItems = [...group.items, ...dynamicItems];
        const visibleItems = allItems.filter(
          (item) =>
            (!item.moduleKey || isModuleEnabled(item.moduleKey)) &&
            (!item.advancedOnly || isAdvanced),
        );
        return { group, visibleItems };
      })
      .filter(({ visibleItems }) => visibleItems.length > 0);
  }, [isAdvanced, isModuleEnabled]);

  const hasActiveModule = useMemo(() => {
    return renderedGroups.some(({ visibleItems }) =>
      visibleItems.some((item) => {
        const [pathname] = item.to.split('?');
        return (
          location.pathname === pathname ||
          (pathname !== '/' && location.pathname.startsWith(pathname + '/'))
        );
      }),
    );
  }, [renderedGroups, location.pathname]);

  return (
    <div className="relative" ref={ref}>
      <button
        type="button"
        onClick={() => setOpen((p) => !p)}
        aria-expanded={open}
        aria-haspopup="true"
        data-tour="modules-menu"
        className={clsx(
          'flex h-8 items-center gap-1.5 rounded-lg px-2.5',
          'text-xs font-medium',
          'transition-all duration-fast ease-oe',
          open || hasActiveModule
            ? 'bg-oe-blue-subtle text-oe-blue border border-oe-blue/20'
            : 'text-content-secondary border border-border-light hover:bg-surface-secondary hover:text-content-primary',
        )}
      >
        <Grid3x3 size={14} strokeWidth={1.75} />
        <span>{t('nav.modules', { defaultValue: 'Modules' })}</span>
        <ChevronDown
          size={12}
          className={clsx('transition-transform duration-fast', open && 'rotate-180')}
        />
      </button>

      {open && (
        <div
          role="menu"
          className={clsx(
            'absolute left-0 top-full mt-1.5 z-50',
            'w-[min(92vw,840px)]',
            'rounded-xl border border-border-light bg-surface-elevated shadow-xl',
            'animate-scale-in overflow-hidden',
          )}
        >
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-x-4 gap-y-3 p-4 max-h-[70vh] overflow-y-auto">
            {renderedGroups.map(({ group, visibleItems }) => (
              <ModulesColumn
                key={group.id}
                label={t(group.labelKey, { defaultValue: group.id })}
                items={visibleItems}
                badgeMap={badgeMap}
                onNavigate={close}
              />
            ))}
          </div>

          {/* Add module CTA — sits at the bottom edge so the panel reads
              "here are your modules, here's how to add more". */}
          <div className="border-t border-border-light bg-surface-secondary/40 px-4 py-3">
            <NavLink
              to="/modules/developer-guide"
              onClick={close}
              className="group flex items-center gap-2.5 rounded-lg border border-dashed border-oe-blue/40 bg-gradient-to-br from-oe-blue/5 via-transparent to-blue-50/40 dark:from-oe-blue/10 dark:via-transparent dark:to-slate-900/30 px-3 py-2 hover:border-oe-blue hover:from-oe-blue/10 hover:shadow-sm transition-all"
            >
              <span className="shrink-0 flex h-7 w-7 items-center justify-center rounded-md bg-oe-blue/10 text-oe-blue group-hover:bg-oe-blue group-hover:text-white transition-colors">
                <Plus size={14} strokeWidth={2.5} />
              </span>
              <span className="min-w-0 flex-1">
                <span className="block text-xs font-semibold text-content-primary leading-tight">
                  {t('nav.add_module', { defaultValue: 'Add module' })}
                </span>
                <span className="block text-[10px] text-content-tertiary leading-tight mt-0.5 truncate">
                  {t('nav.add_module_hint', { defaultValue: 'Build your own · developer guide' })}
                </span>
              </span>
            </NavLink>
          </div>
        </div>
      )}
    </div>
  );
}

function ModulesColumn({
  label,
  items,
  badgeMap,
  onNavigate,
}: {
  label: string;
  items: NavItem[];
  badgeMap: Record<string, number>;
  onNavigate: () => void;
}) {
  const { t } = useTranslation();
  return (
    <div className="min-w-0">
      <h3 className="px-2 mb-1 text-2xs font-semibold uppercase tracking-wider text-content-tertiary">
        {label}
      </h3>
      <ul className="space-y-0.5">
        {items.map((item) => (
          <li key={item.to}>
            <MegaMenuItem
              item={item}
              label={t(item.labelKey)}
              numericBadge={badgeMap[item.to]}
              onNavigate={onNavigate}
            />
          </li>
        ))}
      </ul>
    </div>
  );
}

function MegaMenuItem({
  item,
  label,
  numericBadge,
  onNavigate,
}: {
  item: NavItem;
  label: string;
  numericBadge?: number;
  onNavigate: () => void;
}) {
  const Icon = item.icon;
  const location = useLocation();

  const hasQuery = item.to.includes('?');
  const computeActive = (routerIsActive: boolean): boolean => {
    if (!hasQuery) return routerIsActive;
    const [pathname, queryString] = item.to.split('?');
    if (location.pathname !== pathname) return false;
    const itemParams = new URLSearchParams(queryString);
    const currentParams = new URLSearchParams(location.search);
    for (const [key, value] of itemParams.entries()) {
      if (currentParams.get(key) !== value) return false;
    }
    return true;
  };

  const routerIsActive =
    location.pathname === item.to ||
    (!hasQuery && item.to !== '/' && location.pathname.startsWith(item.to + '/'));
  const isActive = computeActive(routerIsActive);

  return (
    <NavLink
      to={item.to}
      end={item.to === '/' || hasQuery}
      onClick={onNavigate}
      title={label}
      {...(item.tourId ? { 'data-tour': item.tourId } : {})}
      className={({ isActive: ria }) => {
        const active = computeActive(ria);
        return clsx(
          'flex items-center gap-2 rounded-md px-2 py-1.5',
          'text-[13px] font-medium transition-all duration-fast ease-oe',
          item.highlight && !active
            ? 'bg-gradient-to-r from-[#7c3aed]/10 to-[#0ea5e9]/10 text-[#6d28d9] hover:from-[#7c3aed]/15 hover:to-[#0ea5e9]/15'
            : active
              ? 'bg-oe-blue-subtle text-oe-blue'
              : 'text-content-secondary hover:bg-surface-secondary hover:text-content-primary',
        );
      }}
    >
      <Icon size={15} strokeWidth={1.75} className="shrink-0" />
      <span className="truncate flex-1">{label}</span>
      {numericBadge != null && numericBadge > 0 && (
        <span
          className={clsx(
            'ms-auto flex h-4 min-w-[1.25rem] items-center justify-center rounded-full text-2xs font-bold px-1',
            isActive ? 'bg-oe-blue text-white' : 'bg-surface-tertiary text-content-secondary',
          )}
        >
          {numericBadge > 99 ? '99+' : numericBadge}
        </span>
      )}
      {item.badge && (
        <span
          className={clsx(
            item.badge === 'BETA'
              ? 'ms-auto text-[9px] font-medium uppercase tracking-wide px-1.5 py-px rounded text-content-quaternary bg-surface-tertiary/60 dark:bg-surface-tertiary/40'
              : 'ms-auto text-2xs font-semibold px-1.5 py-0.5 rounded-full text-content-tertiary',
          )}
        >
          {item.badge === 'BETA' ? 'beta' : item.badge}
        </span>
      )}
    </NavLink>
  );
}
