/**
 * Shared navigation taxonomy for the top-nav Modules mega-menu.
 *
 * The previous Sidebar housed both the brand and the entire module
 * taxonomy inline. The taxonomy now lives here so the Modules dropdown
 * (and any future surface that needs the same grouping — command
 * palette, mobile drawer, onboarding tour) consumes one source of truth.
 *
 * Group ids are stable keys read by `getModuleNavItems(groupId)` from
 * the module registry, so dynamic modules can opt into a column simply
 * by setting their manifest's `group` field.
 */

import {
  LayoutDashboard,
  FolderOpen,
  Table2,
  CalendarDays,
  Database,
  Layers,
  Boxes,
  Box,
  ShieldCheck,
  FileText,
  FileBarChart,
  Package,
  TrendingUp,
  Ruler,
  Sparkles,
  MessageSquare,
  FileEdit,
  ShieldAlert,
  ClipboardCheck,
  ClipboardList,
  PenTool,
  PencilRuler,
  ListChecks,
  Camera,
  TableProperties,
  Wallet,
  HardHat,
  Users,
  HelpCircle,
  AlertOctagon,
  FileCheck,
  Mail,
  Send,
  BrainCircuit,
  SlidersHorizontal,
  Settings,
  Info,
  type LucideIcon,
} from 'lucide-react';

export interface NavItem {
  labelKey: string;
  to: string;
  icon: LucideIcon;
  badge?: string;
  highlight?: boolean;
  moduleKey?: string;
  advancedOnly?: boolean;
  tourId?: string;
}

export interface NavGroup {
  id: string;
  labelKey: string;
  descriptionKey?: string;
  items: NavItem[];
  defaultOpen: boolean;
  hideInSimple?: boolean;
}

export const navGroups: NavGroup[] = [
  {
    id: 'overview',
    labelKey: 'nav.group_overview',
    defaultOpen: true,
    items: [
      { labelKey: 'nav.dashboard', to: '/', icon: LayoutDashboard },
      { labelKey: 'projects.title', to: '/projects', icon: FolderOpen, tourId: 'projects' },
    ],
  },
  {
    id: 'estimation',
    labelKey: 'nav.group_estimation',
    descriptionKey: 'nav.group_estimation_desc',
    defaultOpen: true,
    items: [
      { labelKey: 'boq.title', to: '/boq', icon: Table2, tourId: 'boq' },
      { labelKey: 'costs.title', to: '/costs', icon: Database, tourId: 'costs' },
      { labelKey: 'nav.assemblies', to: '/assemblies', icon: Layers },
      { labelKey: 'catalog.title', to: '/catalog', icon: Boxes },
      { labelKey: 'nav.quantity_rules', to: '/bim/rules', icon: ClipboardCheck, badge: 'BETA' },
    ],
  },
  {
    id: 'takeoff',
    labelKey: 'nav.group_takeoff',
    defaultOpen: true,
    items: [
      { labelKey: 'nav.pdf_measurements', to: '/takeoff?tab=measurements', icon: Ruler },
      { labelKey: 'nav.dwg_takeoff', to: '/dwg-takeoff', icon: PencilRuler },
      { labelKey: 'nav.cad_bim_explorer', to: '/data-explorer', icon: TableProperties },
      { labelKey: 'nav.bim_viewer', to: '/bim', icon: Box },
      { labelKey: 'nav.bim_rules', to: '/bim/rules?mode=requirements', icon: SlidersHorizontal, badge: 'BETA' },
    ],
  },
  {
    id: 'ai',
    labelKey: 'nav.group_ai_estimation',
    defaultOpen: true,
    hideInSimple: true,
    items: [
      { labelKey: 'nav.ai_estimate', to: '/ai-estimate', icon: Sparkles, badge: 'BETA' },
      { labelKey: 'nav.ai_advisor', to: '/advisor', icon: MessageSquare },
      { labelKey: 'nav.estimation_dashboard', to: '/project-intelligence', icon: BrainCircuit, badge: 'BETA' },
      { labelKey: 'nav.erp_chat', to: '/chat', icon: MessageSquare, badge: 'BETA' },
    ],
  },
  {
    id: 'planning',
    labelKey: 'nav.group_planning',
    descriptionKey: 'nav.group_planning_desc',
    defaultOpen: false,
    hideInSimple: true,
    items: [
      { labelKey: 'schedule.title', to: '/schedule', icon: CalendarDays, moduleKey: 'schedule' },
      { labelKey: 'tasks.title', to: '/tasks', icon: ClipboardList },
      { labelKey: 'nav.5d_cost_model', to: '/5d', icon: TrendingUp, moduleKey: '5d', advancedOnly: true },
      { labelKey: 'nav.risk_register', to: '/risks', icon: ShieldAlert, advancedOnly: true },
    ],
  },
  {
    id: 'finance',
    labelKey: 'nav.group_finance',
    defaultOpen: false,
    hideInSimple: true,
    items: [
      { labelKey: 'finance.title', to: '/finance', icon: Wallet, advancedOnly: true },
      { labelKey: 'procurement.title', to: '/procurement', icon: Package, advancedOnly: true },
      { labelKey: 'tendering.title', to: '/tendering', icon: FileText, moduleKey: 'tendering', advancedOnly: true },
      { labelKey: 'nav.change_orders', to: '/changeorders', icon: FileEdit, advancedOnly: true },
    ],
  },
  {
    id: 'communication',
    labelKey: 'nav.group_communication',
    defaultOpen: false,
    hideInSimple: true,
    items: [
      { labelKey: 'contacts.title', to: '/contacts', icon: Users },
      { labelKey: 'meetings.title', to: '/meetings', icon: CalendarDays },
      { labelKey: 'rfi.title', to: '/rfi', icon: HelpCircle, advancedOnly: true },
      { labelKey: 'submittals.title', to: '/submittals', icon: FileCheck, advancedOnly: true },
      { labelKey: 'transmittals.title', to: '/transmittals', icon: Send, advancedOnly: true },
      { labelKey: 'correspondence.title', to: '/correspondence', icon: Mail, advancedOnly: true },
    ],
  },
  {
    id: 'documentation',
    labelKey: 'nav.group_documentation',
    defaultOpen: false,
    hideInSimple: true,
    items: [
      { labelKey: 'nav.documents', to: '/documents', icon: FolderOpen },
      { labelKey: 'nav.assets', to: '/assets', icon: Package, badge: 'NEW' },
      { labelKey: 'cde.title', to: '/cde', icon: Database },
      { labelKey: 'nav.photos', to: '/photos', icon: Camera },
      { labelKey: 'nav.markups', to: '/markups', icon: PenTool },
      { labelKey: 'nav.field_reports', to: '/field-reports', icon: ClipboardList, advancedOnly: true },
      { labelKey: 'nav.reports', to: '/reports', icon: FileBarChart, advancedOnly: true },
    ],
  },
  {
    id: 'quality',
    labelKey: 'nav.group_quality',
    defaultOpen: false,
    hideInSimple: true,
    items: [
      { labelKey: 'validation.title', to: '/validation', icon: ShieldCheck, moduleKey: 'validation' },
      { labelKey: 'inspections.title', to: '/inspections', icon: ClipboardCheck },
      { labelKey: 'ncr.title', to: '/ncr', icon: AlertOctagon },
      { labelKey: 'safety.title', to: '/safety', icon: HardHat },
      { labelKey: 'nav.punchlist', to: '/punchlist', icon: ListChecks },
    ],
  },
];

/**
 * Top-nav user menu items that used to live in the sidebar bottom bar.
 * Settings/Logout still come from the existing UserMenu in Header.tsx;
 * these are the "everything else" admin entries.
 */
export const userMenuExtras: NavItem[] = [
  { labelKey: 'users.management', to: '/users', icon: Users },
  { labelKey: 'modules.title', to: '/modules', icon: Package },
  { labelKey: 'nav.settings', to: '/settings', icon: Settings },
  { labelKey: 'nav.about', to: '/about', icon: Info },
];
