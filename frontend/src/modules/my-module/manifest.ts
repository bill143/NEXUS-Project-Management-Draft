import { lazy } from 'react';
import { Sparkles } from 'lucide-react';
import type { ModuleManifest } from '../_types';

const MyModule = lazy(() => import('./MyModule'));

export const manifest: ModuleManifest = {
  id: 'my-module',
  name: 'mymodule.title',
  description: 'mymodule.description',
  version: '0.1.0',
  icon: Sparkles,
  category: 'tools',
  defaultEnabled: false,
  depends: ['projects'],

  routes: [
    {
      path: '/my-module',
      title: 'My Module',
      component: MyModule,
    },
  ],

  navItems: [
    {
      labelKey: 'mymodule.nav',
      to: '/my-module',
      icon: Sparkles,
      group: 'tools',
      advancedOnly: true,
    },
  ],

  searchEntries: [
    {
      label: 'My Module',
      path: '/my-module',
      keywords: ['my', 'module', 'items', 'community'],
    },
  ],

  translations: {
    en: {
      'mymodule.title': 'My Module',
      'mymodule.description': 'Example community module — manage items per project.',
      'mymodule.nav': 'My Module',
      'mymodule.heading': 'My Module',
      'mymodule.subtitle': 'Manage items belonging to a project.',
      'mymodule.empty': 'No items yet.',
    },
    de: {
      'mymodule.title': 'Mein Modul',
      'mymodule.description': 'Beispiel-Community-Modul — Elemente pro Projekt verwalten.',
      'mymodule.nav': 'Mein Modul',
      'mymodule.heading': 'Mein Modul',
      'mymodule.subtitle': 'Verwalten Sie projektbezogene Elemente.',
      'mymodule.empty': 'Noch keine Elemente.',
    },
    ru: {
      'mymodule.title': 'Мой модуль',
      'mymodule.description': 'Пример community-модуля — элементы по проекту.',
      'mymodule.nav': 'Мой модуль',
      'mymodule.heading': 'Мой модуль',
      'mymodule.subtitle': 'Управление элементами в рамках проекта.',
      'mymodule.empty': 'Пока нет элементов.',
    },
  },
};
