import { lazy, type ComponentType, type LazyExoticComponent } from 'react';
import { ScatterChart } from 'lucide-react';
import type { ModuleManifest } from '../_types';

const VisualBimPage = lazy(
  () => import('./VisualBimPage'),
) as unknown as LazyExoticComponent<ComponentType<unknown>>;

export const manifest: ModuleManifest = {
  id: 'visualbim',
  name: 'BIM Analytics',
  description: 'Multi-dimensional point-cloud visualization of BIM project parameters',
  version: '1.0.0',
  icon: ScatterChart,
  category: 'tools',
  defaultEnabled: true,
  routes: [
    {
      path: '/visualbim',
      title: 'BIM Analytics',
      component: VisualBimPage,
    },
  ],
  navItems: [
    {
      labelKey: 'nav.visualbim',
      to: '/visualbim',
      icon: ScatterChart,
      group: 'tools',
    },
  ],
  searchEntries: [
    {
      label: 'BIM Analytics',
      path: '/visualbim',
      keywords: [
        'visualbim', 'analytics', 'bim', 'point cloud', 'scatter', 'plotly',
        'compare', 'snapshot', 'dna', 'parameter cloud',
      ],
    },
  ],
};
