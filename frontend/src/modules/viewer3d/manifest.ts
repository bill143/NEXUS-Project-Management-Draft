import { lazy, type ComponentType, type LazyExoticComponent } from 'react';
import { Box } from 'lucide-react';
import type { ModuleManifest } from '../_types';

const Viewer3DPage = lazy(
  () => import('./Viewer3DPage'),
) as unknown as LazyExoticComponent<ComponentType<unknown>>;

export const manifest: ModuleManifest = {
  id: 'viewer3d',
  name: '3D Viewer',
  description: 'Browser-based 3D model viewer (Online3DViewer / three.js)',
  version: '1.0.0',
  icon: Box,
  category: 'tools',
  defaultEnabled: true,
  routes: [
    {
      path: '/viewer3d',
      title: '3D Viewer',
      component: Viewer3DPage,
    },
  ],
  navItems: [
    {
      labelKey: 'nav.viewer3d',
      to: '/viewer3d',
      icon: Box,
      group: 'tools',
    },
  ],
  searchEntries: [
    {
      label: '3D Viewer',
      path: '/viewer3d',
      keywords: ['3d', 'viewer', 'model', 'ifc', 'gltf', 'obj', 'stl', 'fbx', 'three.js'],
    },
  ],
};
