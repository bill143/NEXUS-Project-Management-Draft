/**
 * User Management Page — admin panel for managing users, roles, module access.
 *
 * Features:
 * - User list with role badges and status
 * - Invite new users
 * - Change roles (admin/manager/editor/viewer)
 * - Activate/deactivate users
 * - Per-user module access matrix (visible + access level per module)
 * - Custom role names
 */

import { useState, useCallback, useMemo } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import clsx from 'clsx';
import {
  Users,
  Shield,
  ShieldCheck,
  UserPlus,
  Search,
  Check,
  X,
  Mail,
  Clock,
  Crown,
  Eye,
  Edit3,
  ChevronDown,
  Settings2,
  Lock,
  Unlock,
  Save,
  Trash2,
  KeyRound,
  UserCircle,
  Phone,
  Briefcase,
  Building2,
  CalendarDays,
  StickyNote,
  AlertTriangle,
} from 'lucide-react';
import { Card, Badge } from '@/shared/ui';
import { useToastStore } from '@/stores/useToastStore';
import {
  fetchUsers,
  updateUser,
  inviteUser,
  deleteUser,
  getUserModuleAccess,
  setUserModuleAccess,
  getUserProfile,
  setUserProfile,
  requestPasswordResetForUser,
  type User,
  type UserRole,
  type ModuleAccessLevel,
  type ModuleAccess,
  type UserProfile,
} from './api';

const inputCls =
  'h-10 w-full rounded-lg border border-border bg-surface-primary px-3 text-sm focus:outline-none focus:ring-2 focus:ring-oe-blue/30 focus:border-oe-blue';

const ROLE_CONFIG: Record<
  UserRole,
  {
    icon: React.ElementType;
    label: string;
    color: string;
    variant: 'neutral' | 'blue' | 'success' | 'warning' | 'error';
  }
> = {
  admin: { icon: Crown, label: 'Admin', color: 'text-red-600 dark:text-red-400', variant: 'error' },
  manager: {
    icon: ShieldCheck,
    label: 'Manager',
    color: 'text-amber-600 dark:text-amber-400',
    variant: 'warning',
  },
  editor: { icon: Edit3, label: 'Editor', color: 'text-blue-600 dark:text-blue-400', variant: 'blue' },
  viewer: { icon: Eye, label: 'Viewer', color: 'text-content-tertiary', variant: 'neutral' },
};

const ROLES: UserRole[] = ['admin', 'manager', 'editor', 'viewer'];

const ACCESS_LEVELS: { value: ModuleAccessLevel; label: string; color: string }[] = [
  { value: 'none', label: 'None', color: 'text-content-quaternary' },
  { value: 'view', label: 'View', color: 'text-blue-600' },
  { value: 'edit', label: 'Edit', color: 'text-amber-600' },
  { value: 'full', label: 'Full', color: 'text-green-600' },
];

// All manageable modules grouped by category
const MODULE_GROUPS = [
  {
    label: 'Core',
    modules: [
      { id: 'projects', name: 'Projects' },
      { id: 'boq', name: 'Bill of Quantities' },
      { id: 'costs', name: 'Cost Database' },
      { id: 'assemblies', name: 'Assemblies' },
      { id: 'validation', name: 'Validation' },
    ],
  },
  {
    label: 'Planning & Finance',
    modules: [
      { id: 'schedule', name: '4D Schedule' },
      { id: 'costmodel', name: '5D Cost Model' },
      { id: 'finance', name: 'Finance' },
      { id: 'procurement', name: 'Procurement' },
      { id: 'changeorders', name: 'Change Orders' },
    ],
  },
  {
    label: 'Communication',
    modules: [
      { id: 'tasks', name: 'Tasks' },
      { id: 'meetings', name: 'Meetings' },
      { id: 'rfi', name: 'RFI' },
      { id: 'correspondence', name: 'Correspondence' },
      { id: 'transmittals', name: 'Transmittals' },
    ],
  },
  {
    label: 'Quality & Safety',
    modules: [
      { id: 'inspections', name: 'Inspections' },
      { id: 'ncr', name: 'NCR' },
      { id: 'safety', name: 'Safety' },
      { id: 'punchlist', name: 'Punch List' },
      { id: 'submittals', name: 'Submittals' },
    ],
  },
  {
    label: 'Documents & BIM',
    modules: [
      { id: 'documents', name: 'Documents' },
      { id: 'cde', name: 'CDE (ISO 19650)' },
      { id: 'bim_hub', name: 'BIM Hub' },
      { id: 'fieldreports', name: 'Field Reports' },
      { id: 'contacts', name: 'Contacts' },
    ],
  },
  {
    label: 'AI & Analytics',
    modules: [
      { id: 'ai', name: 'AI Estimation' },
      { id: 'takeoff', name: 'Takeoff' },
      { id: 'reporting', name: 'Reporting' },
      { id: 'risk', name: 'Risk Register' },
    ],
  },
];

/* ── Invite User Modal ───────────────────────────────────────────────── */

function InviteModal({
  onClose,
  onSubmit,
  isPending,
}: {
  onClose: () => void;
  onSubmit: (data: { email: string; password: string; full_name: string; role: UserRole }) => void;
  isPending: boolean;
}) {
  const { t } = useTranslation();
  const [form, setForm] = useState({
    email: '',
    password: '',
    full_name: '',
    role: 'editor' as UserRole,
  });

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm animate-fade-in"
      onClick={onClose}
    >
      <div
        className="bg-surface-primary rounded-xl shadow-2xl border border-border w-full max-w-md mx-4 animate-scale-in"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between px-5 py-4 border-b border-border">
          <div className="flex items-center gap-2">
            <UserPlus size={18} className="text-oe-blue" />
            <h3 className="text-base font-semibold">
              {t('users.invite_user', { defaultValue: 'Invite User‌⁠‍' })}
            </h3>
          </div>
          <button onClick={onClose} className="p-1 rounded hover:bg-surface-secondary">
            <X size={16} />
          </button>
        </div>
        <div className="p-5 space-y-4">
          <div>
            <label className="block text-xs font-medium text-content-secondary mb-1">
              {t('users.full_name', { defaultValue: 'Full Name‌⁠‍' })}
            </label>
            <input
              className={inputCls}
              value={form.full_name}
              onChange={(e) => setForm({ ...form, full_name: e.target.value })}
              placeholder="John Doe"
              autoFocus
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-content-secondary mb-1">
              {t('users.email', { defaultValue: 'Email' })}
            </label>
            <input
              className={inputCls}
              type="email"
              value={form.email}
              onChange={(e) => setForm({ ...form, email: e.target.value })}
              placeholder="john@company.com"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-content-secondary mb-1">
              {t('users.password', { defaultValue: 'Password‌⁠‍' })}
            </label>
            <input
              className={inputCls}
              type="password"
              value={form.password}
              onChange={(e) => setForm({ ...form, password: e.target.value })}
              placeholder="Min 6 characters"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-content-secondary mb-1">
              {t('users.role', { defaultValue: 'Role' })}
            </label>
            <div className="grid grid-cols-4 gap-2">
              {ROLES.map((r) => {
                const cfg = ROLE_CONFIG[r];
                const Icon = cfg.icon;
                return (
                  <button
                    key={r}
                    onClick={() => setForm({ ...form, role: r })}
                    className={clsx(
                      'flex flex-col items-center gap-1 p-2 rounded-lg border text-xs font-medium transition-all',
                      form.role === r
                        ? 'border-oe-blue bg-oe-blue/5 ring-2 ring-oe-blue/20'
                        : 'border-border hover:border-border-hover',
                    )}
                  >
                    <Icon size={16} className={cfg.color} />
                    {cfg.label}
                  </button>
                );
              })}
            </div>
          </div>
        </div>
        <div className="flex justify-end gap-2 px-5 py-3 border-t border-border">
          <button onClick={onClose} className="px-4 py-2 text-sm rounded-lg hover:bg-surface-secondary">
            {t('common.cancel', { defaultValue: 'Cancel‌⁠‍' })}
          </button>
          <button
            onClick={() => onSubmit(form)}
            disabled={isPending || !form.email || !form.full_name || !form.password}
            className="px-4 py-2 text-sm font-medium rounded-lg bg-oe-blue text-white hover:bg-oe-blue-dark disabled:opacity-50"
          >
            {isPending
              ? t('common.creating', { defaultValue: 'Creating...‌⁠‍' })
              : t('users.invite', { defaultValue: 'Invite' })}
          </button>
        </div>
      </div>
    </div>
  );
}

/* ── Module Access Form (renders inside the user-detail slide-over) ─── */

function ModuleAccessForm({ user }: { user: User }) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const addToast = useToastStore((s) => s.addToast);
  const [customRoleName, setCustomRoleName] = useState('');
  const [modules, setModules] = useState<Record<string, ModuleAccess>>({});
  const [dirty, setDirty] = useState(false);
  const [initialized, setInitialized] = useState(false);

  const { data: accessData, isLoading } = useQuery({
    queryKey: ['user-module-access', user.id],
    queryFn: () => getUserModuleAccess(user.id),
  });

  // Sync state from query data on first load
  if (accessData && !initialized) {
    setModules(accessData.modules || {});
    setCustomRoleName(accessData.custom_role_name || '');
    setInitialized(true);
  }

  const saveMut = useMutation({
    mutationFn: () =>
      setUserModuleAccess(user.id, { modules, custom_role_name: customRoleName || null }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['user-module-access', user.id] });
      setDirty(false);
      addToast({
        type: 'success',
        title: t('users.access_saved', { defaultValue: 'Access settings saved' }),
      });
    },
    onError: (e: Error) => {
      addToast({
        type: 'error',
        title: t('common.error', { defaultValue: 'Error' }),
        message: e.message,
      });
    },
  });

  const getModuleAccess = (modId: string): ModuleAccess =>
    modules[modId] || { visible: true, access: 'edit' };

  const toggleVisible = (modId: string) => {
    const cur = getModuleAccess(modId);
    setModules({ ...modules, [modId]: { ...cur, visible: !cur.visible } });
    setDirty(true);
  };

  const setAccessLevel = (modId: string, level: ModuleAccessLevel) => {
    const cur = getModuleAccess(modId);
    setModules({ ...modules, [modId]: { ...cur, access: level, visible: level !== 'none' } });
    setDirty(true);
  };

  const applyPreset = (preset: 'all' | 'viewer' | 'minimal') => {
    const newModules: Record<string, ModuleAccess> = {};
    for (const group of MODULE_GROUPS) {
      for (const mod of group.modules) {
        if (preset === 'all') {
          newModules[mod.id] = { visible: true, access: 'full' };
        } else if (preset === 'viewer') {
          newModules[mod.id] = { visible: true, access: 'view' };
        } else {
          const isCore = ['projects', 'boq', 'costs', 'tasks', 'documents'].includes(mod.id);
          newModules[mod.id] = { visible: isCore, access: isCore ? 'edit' : 'none' };
        }
      }
    }
    setModules(newModules);
    setDirty(true);
  };

  const enabledCount = Object.values(modules).filter((m) => m.visible).length;
  const totalCount = MODULE_GROUPS.reduce((n, g) => n + g.modules.length, 0);

  return (
    <div className="flex flex-col h-full">
      {/* Custom role name + presets */}
      <div className="px-5 py-3 border-b border-border shrink-0">
        <label className="block text-2xs font-medium text-content-tertiary mb-1">
          {t('users.custom_role', { defaultValue: 'Custom Role Name' })}
        </label>
        <input
          className="h-8 w-full rounded-md border border-border bg-surface-primary px-2 text-xs focus:outline-none focus:ring-1 focus:ring-oe-blue/30"
          value={customRoleName}
          onChange={(e) => {
            setCustomRoleName(e.target.value);
            setDirty(true);
          }}
          placeholder="e.g. Site Engineer, Cost Manager..."
        />
        <div className="mt-2 flex flex-wrap items-center gap-1.5">
          <span className="text-2xs text-content-tertiary">
            {t('users.presets', { defaultValue: 'Presets' })}:
          </span>
          {[
            { key: 'all' as const, label: 'Full Access' },
            { key: 'viewer' as const, label: 'View Only' },
            { key: 'minimal' as const, label: 'Minimal' },
          ].map((p) => (
            <button
              key={p.key}
              onClick={() => applyPreset(p.key)}
              className="px-2 py-1 text-2xs rounded border border-border hover:bg-surface-secondary transition-colors"
            >
              {p.label}
            </button>
          ))}
        </div>
      </div>

      {/* Module matrix */}
      <div className="flex-1 overflow-y-auto px-5 py-3">
        {isLoading ? (
          <div className="text-center py-8 text-content-tertiary text-sm">Loading...</div>
        ) : (
          MODULE_GROUPS.map((group) => (
            <div key={group.label} className="mb-4">
              <h4 className="text-2xs font-semibold uppercase tracking-wider text-content-tertiary mb-2">
                {group.label}
              </h4>
              <div className="space-y-1">
                {group.modules.map((mod) => {
                  const acc = getModuleAccess(mod.id);
                  return (
                    <div
                      key={mod.id}
                      className={clsx(
                        'flex items-center gap-3 px-3 py-2 rounded-lg transition-colors',
                        acc.visible ? 'bg-surface-secondary/50' : 'opacity-50',
                      )}
                    >
                      <button
                        onClick={() => toggleVisible(mod.id)}
                        className={clsx(
                          'w-5 h-5 rounded border flex items-center justify-center transition-colors shrink-0',
                          acc.visible
                            ? 'bg-oe-blue border-oe-blue text-white'
                            : 'border-border hover:border-border-hover',
                        )}
                      >
                        {acc.visible && <Check size={12} />}
                      </button>
                      <span className="text-sm font-medium flex-1 min-w-0 truncate">{mod.name}</span>
                      <div className="flex items-center gap-0.5 bg-surface-primary rounded-md border border-border p-0.5">
                        {ACCESS_LEVELS.map((lvl) => (
                          <button
                            key={lvl.value}
                            onClick={() => setAccessLevel(mod.id, lvl.value)}
                            className={clsx(
                              'px-2 py-0.5 text-2xs font-medium rounded transition-all',
                              acc.access === lvl.value
                                ? 'bg-oe-blue text-white shadow-sm'
                                : 'hover:bg-surface-secondary text-content-secondary',
                            )}
                          >
                            {lvl.label}
                          </button>
                        ))}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          ))
        )}
      </div>

      {/* Footer */}
      <div className="flex items-center justify-between px-5 py-3 border-t border-border shrink-0">
        <div className="text-xs text-content-tertiary">
          {enabledCount} / {totalCount}{' '}
          {t('users.modules_enabled', { defaultValue: 'modules enabled' })}
        </div>
        <button
          onClick={() => saveMut.mutate()}
          disabled={!dirty || saveMut.isPending}
          className="flex items-center gap-1.5 px-4 py-2 text-sm font-medium rounded-lg bg-oe-blue text-white hover:bg-oe-blue-dark disabled:opacity-50 transition-colors"
        >
          <Save size={14} />
          {saveMut.isPending
            ? t('common.saving', { defaultValue: 'Saving...' })
            : t('common.save', { defaultValue: 'Save' })}
        </button>
      </div>
    </div>
  );
}

/* ── Profile Form (Profile tab inside the user-detail slide-over) ───── */

function UserProfileForm({ user }: { user: User }) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const addToast = useToastStore((s) => s.addToast);
  const [form, setForm] = useState<UserProfile>({});
  const [fullName, setFullName] = useState(user.full_name);
  const [dirty, setDirty] = useState(false);
  const [initialized, setInitialized] = useState(false);

  const { data: profile, isLoading } = useQuery({
    queryKey: ['user-profile', user.id],
    queryFn: () => getUserProfile(user.id),
  });

  if (profile && !initialized) {
    setForm(profile);
    setInitialized(true);
  }

  const saveMut = useMutation({
    mutationFn: async () => {
      const tasks: Promise<unknown>[] = [setUserProfile(user.id, form)];
      if (fullName !== user.full_name) {
        tasks.push(updateUser(user.id, { full_name: fullName }));
      }
      await Promise.all(tasks);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['user-profile', user.id] });
      queryClient.invalidateQueries({ queryKey: ['users'] });
      setDirty(false);
      addToast({
        type: 'success',
        title: t('users.profile_saved', { defaultValue: 'Profile saved' }),
      });
    },
    onError: (e: Error) => {
      addToast({
        type: 'error',
        title: t('common.error', { defaultValue: 'Error' }),
        message: e.message,
      });
    },
  });

  const update = (patch: Partial<UserProfile>) => {
    setForm({ ...form, ...patch });
    setDirty(true);
  };

  const initials = useMemo(() => {
    const fn = form.first_name?.trim() ?? '';
    const ln = form.last_name?.trim() ?? '';
    if (fn || ln) return `${fn[0] ?? ''}${ln[0] ?? ''}`.toUpperCase();
    return user.full_name?.[0]?.toUpperCase() || '?';
  }, [form.first_name, form.last_name, user.full_name]);

  if (isLoading && !initialized) {
    return (
      <div className="flex-1 flex items-center justify-center text-content-tertiary text-sm">
        Loading...
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full">
      <div className="flex-1 overflow-y-auto px-5 py-4 space-y-4">
        {/* Avatar */}
        <div className="flex items-center gap-3">
          <div className="w-16 h-16 rounded-full bg-oe-blue flex items-center justify-center text-white text-xl font-bold shrink-0">
            {initials}
          </div>
          <div className="min-w-0">
            <div className="text-sm font-semibold truncate">{user.full_name}</div>
            <div className="text-xs text-content-secondary truncate">{user.email}</div>
          </div>
        </div>

        {/* Full name (mirrors User.full_name) */}
        <div>
          <label className="block text-xs font-medium text-content-secondary mb-1">
            {t('users.full_name', { defaultValue: 'Full Name' })}
          </label>
          <input
            className={inputCls}
            value={fullName}
            onChange={(e) => {
              setFullName(e.target.value);
              setDirty(true);
            }}
          />
        </div>

        {/* First / last name */}
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="block text-xs font-medium text-content-secondary mb-1">
              {t('users.first_name', { defaultValue: 'First Name' })}
            </label>
            <input
              className={inputCls}
              value={form.first_name ?? ''}
              onChange={(e) => update({ first_name: e.target.value })}
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-content-secondary mb-1">
              {t('users.last_name', { defaultValue: 'Last Name' })}
            </label>
            <input
              className={inputCls}
              value={form.last_name ?? ''}
              onChange={(e) => update({ last_name: e.target.value })}
            />
          </div>
        </div>

        {/* Email (read-only) */}
        <div>
          <label className="text-xs font-medium text-content-secondary mb-1 flex items-center gap-1.5">
            <Mail size={12} /> {t('users.email', { defaultValue: 'Email' })}
          </label>
          <input
            className={clsx(inputCls, 'bg-surface-secondary cursor-not-allowed')}
            value={user.email}
            readOnly
            title="Email cannot be changed here"
          />
        </div>

        {/* Phone */}
        <div>
          <label className="text-xs font-medium text-content-secondary mb-1 flex items-center gap-1.5">
            <Phone size={12} /> {t('users.phone', { defaultValue: 'Phone' })}
          </label>
          <input
            className={inputCls}
            type="tel"
            value={form.phone ?? ''}
            onChange={(e) => update({ phone: e.target.value })}
            placeholder="+1 555 123 4567"
          />
        </div>

        {/* Position / Department */}
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="text-xs font-medium text-content-secondary mb-1 flex items-center gap-1.5">
              <Briefcase size={12} /> {t('users.title', { defaultValue: 'Position / Title' })}
            </label>
            <input
              className={inputCls}
              value={form.title ?? ''}
              onChange={(e) => update({ title: e.target.value })}
              placeholder="Senior Estimator"
            />
          </div>
          <div>
            <label className="text-xs font-medium text-content-secondary mb-1 flex items-center gap-1.5">
              <Building2 size={12} /> {t('users.department', { defaultValue: 'Department' })}
            </label>
            <input
              className={inputCls}
              value={form.department ?? ''}
              onChange={(e) => update({ department: e.target.value })}
              placeholder="Pre-Construction"
            />
          </div>
        </div>

        {/* Date of commencement */}
        <div>
          <label className="text-xs font-medium text-content-secondary mb-1 flex items-center gap-1.5">
            <CalendarDays size={12} />{' '}
            {t('users.date_of_commencement', { defaultValue: 'Date of Commencement' })}
          </label>
          <input
            className={inputCls}
            type="date"
            value={form.date_of_commencement ?? ''}
            onChange={(e) => update({ date_of_commencement: e.target.value })}
          />
        </div>

        {/* Notes */}
        <div>
          <label className="text-xs font-medium text-content-secondary mb-1 flex items-center gap-1.5">
            <StickyNote size={12} /> {t('users.notes', { defaultValue: 'Notes' })}
          </label>
          <textarea
            rows={4}
            className={clsx(inputCls, 'h-auto py-2 resize-y')}
            value={form.notes ?? ''}
            onChange={(e) => update({ notes: e.target.value })}
            placeholder="Internal notes about this user…"
          />
        </div>
      </div>

      {/* Footer */}
      <div className="flex items-center justify-end px-5 py-3 border-t border-border shrink-0">
        <button
          onClick={() => saveMut.mutate()}
          disabled={!dirty || saveMut.isPending}
          className="flex items-center gap-1.5 px-4 py-2 text-sm font-medium rounded-lg bg-oe-blue text-white hover:bg-oe-blue-dark disabled:opacity-50 transition-colors"
        >
          <Save size={14} />
          {saveMut.isPending
            ? t('common.saving', { defaultValue: 'Saving...' })
            : t('common.save', { defaultValue: 'Save' })}
        </button>
      </div>
    </div>
  );
}

/* ── User Detail Slide-over ─────────────────────────────────────────── */

type DetailTab = 'profile' | 'access';

function UserDetailSlideOver({
  user,
  initialTab,
  onClose,
}: {
  user: User;
  initialTab: DetailTab;
  onClose: () => void;
}) {
  const { t } = useTranslation();
  const [tab, setTab] = useState<DetailTab>(initialTab);

  return (
    <div
      className="fixed inset-0 z-50 flex justify-end bg-black/40 backdrop-blur-sm animate-fade-in"
      onClick={onClose}
    >
      <div
        className="bg-surface-primary shadow-2xl border-l border-border w-full max-w-md h-full flex flex-col animate-slide-in-right"
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-label={`${user.full_name} details`}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-border shrink-0">
          <div className="flex items-center gap-2 min-w-0">
            <UserCircle size={18} className="text-oe-blue shrink-0" />
            <div className="min-w-0">
              <h3 className="text-base font-semibold truncate">{user.full_name}</h3>
              <p className="text-xs text-content-secondary truncate">{user.email}</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded hover:bg-surface-secondary shrink-0"
            aria-label="Close"
          >
            <X size={16} />
          </button>
        </div>

        {/* Tabs */}
        <div className="flex border-b border-border shrink-0">
          {([
            { key: 'profile' as const, label: t('users.profile', { defaultValue: 'Profile' }), icon: UserCircle },
            { key: 'access' as const, label: t('users.module_access', { defaultValue: 'Module Access' }), icon: Settings2 },
          ]).map((tabDef) => {
            const Icon = tabDef.icon;
            const active = tab === tabDef.key;
            return (
              <button
                key={tabDef.key}
                onClick={() => setTab(tabDef.key)}
                className={clsx(
                  'flex items-center gap-1.5 px-4 py-2.5 text-sm font-medium border-b-2 transition-colors',
                  active
                    ? 'border-oe-blue text-oe-blue'
                    : 'border-transparent text-content-secondary hover:text-content-primary',
                )}
              >
                <Icon size={14} />
                {tabDef.label}
              </button>
            );
          })}
        </div>

        {/* Tab content */}
        <div className="flex-1 min-h-0">
          {tab === 'profile' ? (
            <UserProfileForm user={user} />
          ) : (
            <ModuleAccessForm user={user} />
          )}
        </div>
      </div>
    </div>
  );
}

/* ── Delete Confirmation Dialog ─────────────────────────────────────── */

function DeleteUserDialog({
  user,
  onCancel,
  onConfirm,
  isPending,
}: {
  user: User;
  onCancel: () => void;
  onConfirm: () => void;
  isPending: boolean;
}) {
  const { t } = useTranslation();
  return (
    <div
      className="fixed inset-0 z-[60] flex items-center justify-center bg-black/50 backdrop-blur-sm animate-fade-in"
      onClick={onCancel}
    >
      <div
        className="bg-surface-primary rounded-xl shadow-2xl border border-border w-full max-w-md mx-4 animate-scale-in"
        onClick={(e) => e.stopPropagation()}
        role="alertdialog"
        aria-labelledby="delete-user-title"
      >
        <div className="px-5 py-4 border-b border-border flex items-center gap-2">
          <AlertTriangle size={18} className="text-red-600" />
          <h3 id="delete-user-title" className="text-base font-semibold">
            {t('users.delete_user', { defaultValue: 'Delete User' })}
          </h3>
        </div>
        <div className="px-5 py-4 text-sm text-content-primary">
          {t('users.delete_confirm', {
            defaultValue: 'Are you sure you want to permanently delete {{name}}? This action cannot be undone.',
            name: user.full_name,
          })}
        </div>
        <div className="flex justify-end gap-2 px-5 py-3 border-t border-border">
          <button
            onClick={onCancel}
            disabled={isPending}
            className="px-4 py-2 text-sm rounded-lg hover:bg-surface-secondary disabled:opacity-50"
          >
            {t('common.cancel', { defaultValue: 'Cancel' })}
          </button>
          <button
            onClick={onConfirm}
            disabled={isPending}
            className="flex items-center gap-1.5 px-4 py-2 text-sm font-medium rounded-lg bg-red-600 text-white hover:bg-red-700 disabled:opacity-50 transition-colors"
          >
            <Trash2 size={14} />
            {isPending
              ? t('users.deleting', { defaultValue: 'Deleting…' })
              : t('common.delete', { defaultValue: 'Delete' })}
          </button>
        </div>
      </div>
    </div>
  );
}

/* ── Role Dropdown ───────────────────────────────────────────────────── */

function RoleDropdown({
  currentRole,
  userId,
  onUpdate,
}: {
  currentRole: UserRole;
  userId: string;
  onUpdate: (userId: string, role: UserRole) => void;
}) {
  const [open, setOpen] = useState(false);
  const cfg = ROLE_CONFIG[currentRole] ?? ROLE_CONFIG.viewer;
  const Icon = cfg.icon;

  return (
    <div className="relative">
      <button
        onClick={() => setOpen(!open)}
        className="flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-medium transition-colors hover:bg-surface-secondary cursor-pointer"
      >
        <Icon size={13} className={cfg.color} />
        {cfg.label}
        <ChevronDown size={12} className="text-content-quaternary" />
      </button>
      {open && (
        <>
          <div className="fixed inset-0 z-40" onClick={() => setOpen(false)} />
          <div className="absolute right-0 top-full mt-1 z-50 w-36 bg-surface-primary rounded-lg shadow-lg border border-border py-1 animate-fade-in">
            {ROLES.map((r) => {
              const rc = ROLE_CONFIG[r];
              const RIcon = rc.icon;
              return (
                <button
                  key={r}
                  onClick={() => {
                    onUpdate(userId, r);
                    setOpen(false);
                  }}
                  className={clsx(
                    'flex items-center gap-2 w-full px-3 py-1.5 text-xs hover:bg-surface-secondary',
                    r === currentRole && 'bg-surface-secondary font-medium',
                  )}
                >
                  <RIcon size={13} className={rc.color} />
                  {rc.label}
                  {r === currentRole && <Check size={12} className="ml-auto text-oe-blue" />}
                </button>
              );
            })}
          </div>
        </>
      )}
    </div>
  );
}

/* ── Main Page ───────────────────────────────────────────────────────── */

export function UserManagementPage() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const addToast = useToastStore((s) => s.addToast);
  const [search, setSearch] = useState('');
  const [filterActive, setFilterActive] = useState<'all' | 'active' | 'inactive'>('all');
  const [showInvite, setShowInvite] = useState(false);
  const [detail, setDetail] = useState<{ user: User; tab: DetailTab } | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<User | null>(null);

  const { data: users = [], isLoading } = useQuery({
    queryKey: ['users', filterActive],
    queryFn: () =>
      fetchUsers({
        is_active: filterActive === 'all' ? undefined : filterActive === 'active',
        limit: 100,
      }),
  });

  const updateMut = useMutation({
    mutationFn: ({ id, data }: { id: string; data: { role?: UserRole; is_active?: boolean } }) =>
      updateUser(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['users'] });
      addToast({ type: 'success', title: t('users.updated', { defaultValue: 'User updated' }) });
    },
    onError: (e: Error) => {
      addToast({
        type: 'error',
        title: t('common.error', { defaultValue: 'Error' }),
        message: e.message,
      });
    },
  });

  const inviteMut = useMutation({
    mutationFn: inviteUser,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['users'] });
      setShowInvite(false);
      addToast({
        type: 'success',
        title: t('users.invited', { defaultValue: 'User invited successfully' }),
      });
    },
    onError: (e: Error) => {
      addToast({
        type: 'error',
        title: t('common.error', { defaultValue: 'Error' }),
        message: e.message,
      });
    },
  });

  const deleteMut = useMutation({
    mutationFn: (id: string) => deleteUser(id),
    onSuccess: (_data, id) => {
      queryClient.invalidateQueries({ queryKey: ['users'] });
      const name = deleteTarget?.full_name ?? '';
      setDeleteTarget(null);
      if (detail?.user.id === id) setDetail(null);
      addToast({
        type: 'success',
        title: t('users.deleted', { defaultValue: 'User deleted' }),
        message: name,
      });
    },
    onError: (e: Error) => {
      addToast({
        type: 'error',
        title: t('common.error', { defaultValue: 'Error' }),
        message: e.message,
      });
    },
  });

  const resetPwMut = useMutation({
    mutationFn: (email: string) => requestPasswordResetForUser(email),
    onSuccess: (_data, email) => {
      addToast({
        type: 'success',
        title: t('users.reset_sent', {
          defaultValue: 'Password reset email sent to {{email}}',
          email,
        }),
      });
    },
    onError: (e: Error) => {
      addToast({
        type: 'error',
        title: t('common.error', { defaultValue: 'Error' }),
        message: e.message,
      });
    },
  });

  const handleRoleChange = useCallback(
    (userId: string, role: UserRole) => {
      updateMut.mutate({ id: userId, data: { role } });
    },
    [updateMut],
  );

  const handleToggleActive = useCallback(
    (user: User) => {
      updateMut.mutate({ id: user.id, data: { is_active: !user.is_active } });
    },
    [updateMut],
  );

  const filtered = useMemo(() => {
    if (!search) return users;
    const q = search.toLowerCase();
    return users.filter(
      (u) => u.full_name.toLowerCase().includes(q) || u.email.toLowerCase().includes(q),
    );
  }, [users, search]);

  const stats = {
    total: users.length,
    active: users.filter((u) => u.is_active).length,
    admins: users.filter((u) => u.role === 'admin').length,
    managers: users.filter((u) => u.role === 'manager').length,
  };

  return (
    <div className="w-full animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-xl font-bold flex items-center gap-2">
            <Users size={22} className="text-oe-blue" />
            {t('users.management', { defaultValue: 'User Management' })}
          </h1>
          <p className="text-sm text-content-secondary mt-0.5">
            {t('users.management_desc', { defaultValue: 'Manage team members, roles, and access' })}
          </p>
        </div>
        <button
          onClick={() => setShowInvite(true)}
          className="flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-lg bg-oe-blue text-white hover:bg-oe-blue-dark transition-colors"
        >
          <UserPlus size={16} />
          {t('users.invite_user', { defaultValue: 'Invite User' })}
        </button>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-4 gap-3 mb-5">
        {[
          { label: t('users.total', { defaultValue: 'Total Users' }), value: stats.total, icon: Users, color: 'text-oe-blue' },
          { label: t('users.active', { defaultValue: 'Active' }), value: stats.active, icon: Check, color: 'text-green-600' },
          { label: t('users.admins', { defaultValue: 'Admins' }), value: stats.admins, icon: Crown, color: 'text-red-500' },
          { label: t('users.managers', { defaultValue: 'Managers' }), value: stats.managers, icon: ShieldCheck, color: 'text-amber-500' },
        ].map((s) => (
          <Card key={s.label} className="p-3">
            <div className="flex items-center gap-2">
              <s.icon size={16} className={s.color} />
              <span className="text-xs text-content-secondary">{s.label}</span>
            </div>
            <div className="text-xl font-bold mt-1">{s.value}</div>
          </Card>
        ))}
      </div>

      {/* Filters */}
      <div className="flex items-center gap-3 mb-4">
        <div className="relative flex-1 max-w-xs">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-content-quaternary" />
          <input
            className={clsx(inputCls, 'pl-8')}
            placeholder={t('users.search', { defaultValue: 'Search by name or email...' })}
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
        <div className="flex items-center gap-1 bg-surface-secondary rounded-lg p-0.5">
          {(['all', 'active', 'inactive'] as const).map((f) => (
            <button
              key={f}
              onClick={() => setFilterActive(f)}
              className={clsx(
                'px-3 py-1.5 text-xs font-medium rounded-md transition-colors',
                filterActive === f ? 'bg-surface-primary shadow-sm' : 'hover:bg-surface-primary/50',
              )}
            >
              {f === 'all'
                ? t('common.all', { defaultValue: 'All' })
                : f === 'active'
                  ? t('users.active', { defaultValue: 'Active' })
                  : t('users.inactive', { defaultValue: 'Inactive' })}
            </button>
          ))}
        </div>
      </div>

      {/* Users Table */}
      <Card className="overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border bg-surface-secondary/50">
                <th className="text-left px-4 py-2.5 text-xs font-semibold text-content-secondary uppercase tracking-wider">
                  {t('users.name', { defaultValue: 'Name' })}
                </th>
                <th className="text-left px-4 py-2.5 text-xs font-semibold text-content-secondary uppercase tracking-wider">
                  {t('users.email', { defaultValue: 'Email' })}
                </th>
                <th className="text-left px-4 py-2.5 text-xs font-semibold text-content-secondary uppercase tracking-wider">
                  {t('users.role', { defaultValue: 'Role' })}
                </th>
                <th className="text-left px-4 py-2.5 text-xs font-semibold text-content-secondary uppercase tracking-wider">
                  {t('users.status', { defaultValue: 'Status' })}
                </th>
                <th className="text-left px-4 py-2.5 text-xs font-semibold text-content-secondary uppercase tracking-wider">
                  {t('users.last_login', { defaultValue: 'Last Login' })}
                </th>
                <th className="text-right px-4 py-2.5 text-xs font-semibold text-content-secondary uppercase tracking-wider">
                  {t('users.actions', { defaultValue: 'Actions' })}
                </th>
              </tr>
            </thead>
            <tbody>
              {isLoading ? (
                Array.from({ length: 5 }).map((_, i) => (
                  <tr key={i} className="border-b border-border/50">
                    <td colSpan={6} className="px-4 py-3">
                      <div className="h-4 w-full bg-surface-secondary rounded animate-pulse" />
                    </td>
                  </tr>
                ))
              ) : filtered.length === 0 ? (
                <tr>
                  <td colSpan={6} className="text-center py-12 text-content-tertiary">
                    <Users size={32} className="mx-auto mb-2 opacity-30" />
                    <p>{t('users.no_users', { defaultValue: 'No users found' })}</p>
                  </td>
                </tr>
              ) : (
                filtered.map((user) => (
                  <tr
                    key={user.id}
                    className="border-b border-border/50 hover:bg-surface-secondary/30 transition-colors"
                  >
                    <td className="px-4 py-2.5">
                      <button
                        onClick={() => setDetail({ user, tab: 'profile' })}
                        className="group flex items-center gap-2.5 text-left rounded -mx-1 px-1 py-0.5 hover:bg-surface-secondary/50 transition-colors"
                        title={t('users.view_details', { defaultValue: 'View details' })}
                      >
                        <div
                          className={clsx(
                            'w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold text-white',
                            user.is_active ? 'bg-oe-blue' : 'bg-gray-400',
                          )}
                        >
                          {user.full_name?.[0]?.toUpperCase() || '?'}
                        </div>
                        <span className="font-medium group-hover:text-oe-blue group-hover:underline">
                          {user.full_name}
                        </span>
                      </button>
                    </td>
                    <td className="px-4 py-2.5 text-content-secondary">
                      <div className="flex items-center gap-1.5">
                        <Mail size={12} className="text-content-quaternary" />
                        {user.email}
                      </div>
                    </td>
                    <td className="px-4 py-2.5">
                      <RoleDropdown
                        currentRole={user.role}
                        userId={user.id}
                        onUpdate={handleRoleChange}
                      />
                    </td>
                    <td className="px-4 py-2.5">
                      <Badge variant={user.is_active ? 'success' : 'neutral'}>
                        {user.is_active
                          ? t('users.active', { defaultValue: 'Active' })
                          : t('users.inactive', { defaultValue: 'Inactive' })}
                      </Badge>
                    </td>
                    <td className="px-4 py-2.5 text-content-tertiary text-xs">
                      {user.last_login_at ? (
                        <div className="flex items-center gap-1">
                          <Clock size={11} />
                          {new Date(user.last_login_at).toLocaleDateString()}
                        </div>
                      ) : (
                        <span className="text-content-quaternary">
                          {t('users.never', { defaultValue: 'Never' })}
                        </span>
                      )}
                    </td>
                    <td className="px-4 py-2.5 text-right">
                      <div className="flex items-center justify-end gap-1">
                        <button
                          onClick={() => setDetail({ user, tab: 'access' })}
                          className="flex items-center gap-1 px-2 py-1 rounded text-xs font-medium text-oe-blue hover:bg-oe-blue/10 transition-colors"
                          title={t('users.module_access', { defaultValue: 'Module Access' })}
                        >
                          <Settings2 size={13} />
                          {t('users.access', { defaultValue: 'Access' })}
                        </button>
                        <button
                          onClick={() => resetPwMut.mutate(user.email)}
                          disabled={resetPwMut.isPending}
                          className="flex items-center gap-1 px-2 py-1 rounded text-xs font-medium text-amber-700 dark:text-amber-400 hover:bg-amber-50 dark:hover:bg-amber-950/30 transition-colors disabled:opacity-50"
                          title={t('users.reset_password', { defaultValue: 'Reset Password' })}
                        >
                          <KeyRound size={13} />
                          {t('users.reset_password', { defaultValue: 'Reset Password' })}
                        </button>
                        <button
                          onClick={() => handleToggleActive(user)}
                          className={clsx(
                            'flex items-center gap-1 px-2 py-1 rounded text-xs font-medium transition-colors',
                            user.is_active
                              ? 'text-red-600 hover:bg-red-50 dark:hover:bg-red-950/30'
                              : 'text-green-600 hover:bg-green-50 dark:hover:bg-green-950/30',
                          )}
                        >
                          {user.is_active ? <Lock size={13} /> : <Unlock size={13} />}
                          {user.is_active
                            ? t('users.deactivate', { defaultValue: 'Deactivate' })
                            : t('users.activate', { defaultValue: 'Activate' })}
                        </button>
                        <button
                          onClick={() => setDeleteTarget(user)}
                          className="flex items-center gap-1 px-2 py-1 rounded text-xs font-medium text-red-600 hover:bg-red-50 dark:hover:bg-red-950/30 transition-colors"
                          title={t('users.delete_user', { defaultValue: 'Delete User' })}
                        >
                          <Trash2 size={13} />
                          {t('common.delete', { defaultValue: 'Delete' })}
                        </button>
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </Card>

      {/* Role Legend */}
      <div className="mt-4 flex items-center gap-4 text-xs text-content-tertiary">
        <Shield size={13} />
        {ROLES.map((r) => {
          const cfg = ROLE_CONFIG[r];
          const Icon = cfg.icon;
          return (
            <span key={r} className="flex items-center gap-1">
              <Icon size={11} className={cfg.color} />
              <strong>{cfg.label}</strong>:{' '}
              {r === 'admin'
                ? t('users.role_admin_desc', { defaultValue: 'Full access' })
                : r === 'manager'
                  ? t('users.role_manager_desc', { defaultValue: 'Project management' })
                  : r === 'editor'
                    ? t('users.role_editor_desc', { defaultValue: 'Create & edit' })
                    : t('users.role_viewer_desc', { defaultValue: 'Read-only' })}
            </span>
          );
        })}
      </div>

      {/* Invite Modal */}
      {showInvite && (
        <InviteModal
          onClose={() => setShowInvite(false)}
          onSubmit={(data) => inviteMut.mutate(data)}
          isPending={inviteMut.isPending}
        />
      )}

      {/* User Detail Slide-over (Profile + Module Access tabs) */}
      {detail && (
        <UserDetailSlideOver
          user={detail.user}
          initialTab={detail.tab}
          onClose={() => setDetail(null)}
        />
      )}

      {/* Delete Confirmation */}
      {deleteTarget && (
        <DeleteUserDialog
          user={deleteTarget}
          isPending={deleteMut.isPending}
          onCancel={() => setDeleteTarget(null)}
          onConfirm={() => deleteMut.mutate(deleteTarget.id)}
        />
      )}
    </div>
  );
}
