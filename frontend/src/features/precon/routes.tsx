/**
 * Precon route definitions — namespaced under `/precon/*`.
 *
 * Exported as a function returning a list of `<Route>` elements so the
 * OCERP `App.tsx` can splice them into its existing `<Routes>` block
 * without us touching App.tsx itself.
 *
 * Usage (from a future drop-in registration):
 *
 *     import { preconRoutes } from '@/features/precon/routes';
 *     <Routes>
 *       ...existing routes...
 *       {preconRoutes}
 *     </Routes>
 *
 * Auth gating happens inside each page via `isPreconRole(useAuthStore.userRole)`
 * so we don't depend on a specific layout wrapper.
 */

import { lazy, Suspense } from 'react';
import { Route } from 'react-router-dom';

const PipelinePage = lazy(() =>
  import('./PipelinePage').then((m) => ({ default: m.PipelinePage })),
);
const BidManagementPage = lazy(() =>
  import('./BidManagementPage').then((m) => ({ default: m.BidManagementPage })),
);
const PreconDashboardPage = lazy(() =>
  import('./PreconDashboardPage').then((m) => ({ default: m.PreconDashboardPage })),
);
const SolicitationDetailPage = lazy(() =>
  import('./SolicitationDetailPage').then((m) => ({ default: m.SolicitationDetailPage })),
);

function Fallback() {
  return (
    <div className="p-6 text-sm text-gray-500" role="status">
      Loading Precon…
    </div>
  );
}

function L({ children }: { children: React.ReactNode }) {
  return <Suspense fallback={<Fallback />}>{children}</Suspense>;
}

/**
 * Route fragment — drop the array into the parent `<Routes>` element.
 *
 * Don't wrap in a `<Routes>` here: react-router v6 requires `<Route>`
 * elements to be direct children of `<Routes>`, not nested another level.
 */
export const preconRoutes = (
  <>
    <Route path="/precon" element={<L><PreconDashboardPage /></L>} />
    <Route path="/precon/dashboard" element={<L><PreconDashboardPage /></L>} />
    <Route path="/precon/pipeline" element={<L><PipelinePage /></L>} />
    <Route path="/precon/bids" element={<L><BidManagementPage /></L>} />
    <Route path="/precon/solicitations/:projectId" element={<L><SolicitationDetailPage /></L>} />
  </>
);

/**
 * Plain object form for the OCERP module loader (`useModuleRouteElements`).
 *
 * The OCERP module loader expects an array of `{ path, Component }` or
 * `{ path, element }` records — depending on the loader version.  Both
 * shapes are exported so consumers can pick the one their loader supports.
 */
export const preconRouteRecords = [
  { path: '/precon', component: PreconDashboardPage },
  { path: '/precon/dashboard', component: PreconDashboardPage },
  { path: '/precon/pipeline', component: PipelinePage },
  { path: '/precon/bids', component: BidManagementPage },
  { path: '/precon/solicitations/:projectId', component: SolicitationDetailPage },
] as const;
