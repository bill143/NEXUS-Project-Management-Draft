/**
 * AboutPage — Platform info, team story, services, and support.
 */

import { useTranslation } from 'react-i18next';
import {
  Mail, Shield, BookOpen, Users, Award,
  Code2, Building2, Briefcase, Globe, ExternalLink,
  Star, Coffee, Rocket, ArrowRight, Handshake,
  MessageCircle,
} from 'lucide-react';
import { Card, Button, Badge } from '@/shared/ui';
import { APP_VERSION } from '@/shared/lib/version';
import { UpdateNotification } from '@/shared/ui/UpdateChecker';
import { Changelog } from './Changelog';

export function AboutPage() {
  const { t } = useTranslation();

  return (
    <div className="max-w-3xl mx-auto space-y-6 animate-fade-in">
      <div className="-mx-4 sm:-mx-7">
        <UpdateNotification forceShow hideDismiss />
      </div>

      {/* Header */}
      <div className="text-center py-6">
        <a
          href="https://nexus.eliteal.info?utm_source=app&utm_medium=about"
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-1.5 text-xs font-semibold text-oe-blue hover:text-oe-blue-dark transition-colors mb-4"
        >
          <Globe size={13} />
          nexus.eliteal.info
          <ExternalLink size={11} />
        </a>
        <div className="flex items-center justify-center gap-2 mb-4">
          <span className="relative flex h-2.5 w-2.5">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75" />
            <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-emerald-500" />
          </span>
          <span className="text-xs font-semibold uppercase tracking-widest text-emerald-600">Open Source</span>
        </div>
        <h1 className="text-3xl font-bold text-content-primary tracking-tight">NEXUS</h1>
        <p className="mt-2 text-base text-content-secondary">
          {t('about.tagline', { defaultValue: 'The #1 open-source platform for construction cost estimation' })}
        </p>
        <div className="mt-3 flex items-center justify-center gap-3 text-sm text-content-tertiary">
          <span className="font-mono">v{APP_VERSION}</span>
          <span>&middot;</span>
          <span>2026</span>
        </div>
      </div>

      {/* Platform Stats */}
      <Card className="animate-card-in" style={{ animationDelay: '50ms' }}>
        <div className="p-6">
          <div className="flex items-center gap-2 mb-4">
            <Award size={18} className="text-amber-500" />
            <h2 className="text-lg font-semibold text-content-primary">
              {t('about.platform_title', { defaultValue: 'Platform Capabilities' })}
            </h2>
          </div>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            {[
              { value: '55K+', label: t('about.stat_costs', { defaultValue: 'Cost Items (CWICR)' }) },
              { value: '20+', label: t('about.stat_langs', { defaultValue: 'Languages' }) },
              { value: '11', label: t('about.stat_regions', { defaultValue: 'Regional Databases' }) },
              { value: '4', label: t('about.stat_cad_formats', { defaultValue: 'CAD/BIM formats supported' }) },
            ].map((s, i) => (
              <div key={i} className="text-center rounded-xl bg-surface-secondary/50 p-4">
                <div className="text-2xl font-bold text-content-primary">{s.value}</div>
                <div className="text-xs text-content-tertiary mt-1">{s.label}</div>
              </div>
            ))}
          </div>
          <p className="mt-4 text-sm text-content-secondary leading-relaxed">
            {t('about.platform_desc', { defaultValue: 'NEXUS covers the full construction estimation workflow — BOQ editing, 4D scheduling, 5D cost modeling, AI-powered estimation, CAD/BIM quantity takeoff (RVT, IFC, DWG, DGN), tendering, and reporting. Supports regional classification standards and custom schemas.' })}
          </p>
        </div>
      </Card>

      {/* Our Story — Team narrative */}
      <Card className="animate-card-in" style={{ animationDelay: '100ms' }}>
        <div className="p-6">
          <div className="flex items-center gap-2 mb-4">
            <Users size={18} className="text-oe-blue" />
            <h2 className="text-lg font-semibold text-content-primary">
              {t('about.story_title', { defaultValue: 'Built by Practitioners, for Practitioners' })}
            </h2>
          </div>
          <div className="space-y-3 text-sm text-content-secondary leading-relaxed">
            <p>
              {t('about.story_p1', {
                defaultValue:
                  'NEXUS was not conceived in a boardroom or a startup accelerator. It was born on active construction sites, inside estimating departments, and across late-night data reconciliation sessions — the places where the real pain of fragmented tooling is felt every day.',
              })}
            </p>
            <p>
              {t('about.story_p2', {
                defaultValue:
                  'A dedicated team of construction professionals, engineers, and software developers spanning three countries and bringing over 40 years of combined hands-on experience made this platform possible. Every feature, every data model, and every workflow in NEXUS reflects lessons learned from direct involvement in real-world projects — from federal infrastructure programs to large-scale commercial builds.',
              })}
            </p>
            <p>
              {t('about.story_p3', {
                defaultValue:
                  'Years of field experience revealed a consistent truth: data is not a byproduct of construction — it is the foundation for every cost, schedule, and delivery decision. Existing tools either locked teams into proprietary ecosystems or failed to address the full estimation lifecycle. The team set out to change that.',
              })}
            </p>
            <p>
              {t('about.story_p4', {
                defaultValue:
                  'The work began long before this platform existed — with open-source CAD/BIM data converters for Revit, IFC, DWG, and DGN formats, and with the CWICR multilingual database of over 55,000 construction work items across 11 languages. These foundational efforts, shaped by thousands of hours of research, testing, and iteration across major construction firms and consulting practices, became the building blocks of NEXUS.',
              })}
            </p>
            <p>
              {t('about.story_p5', {
                defaultValue:
                  'The recent generation of AI tooling finally made it feasible to consolidate that collective expertise — methodology, data models, and prior implementations — into a single, cohesive platform. Today, NEXUS is public, open source, and actively maintained by the same team that built it from the ground up.',
              })}
            </p>
            <p className="border-l-2 border-oe-blue/40 pl-3 italic text-content-primary">
              {t('about.story_quote', {
                defaultValue:
                  'Progress is born from dialogue — from the clash of perspectives and openness to new approaches. We invite you to participate in building a more transparent, data-driven future for construction estimation.',
              })}
            </p>
          </div>
        </div>
      </Card>

      {/* Company */}
      <Card className="animate-card-in" style={{ animationDelay: '150ms' }}>
        <div className="p-6">
          <div className="flex items-center gap-2 mb-3">
            <Building2 size={18} className="text-oe-blue" />
            <h2 className="text-lg font-semibold text-content-primary">
              {"O'Neill Contractors, Inc."}
            </h2>
          </div>
          <p className="text-sm text-content-secondary leading-relaxed mb-4">
            {t('about.company_desc', { defaultValue: 'Federal construction management serving SDVOSB, VOSB, and EDWOSB certified projects across the United States.' })}
          </p>
          <a
            href="https://nexus.eliteal.info"
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1.5 text-sm text-oe-blue hover:underline"
          >
            nexus.eliteal.info
            <ExternalLink size={13} className="text-content-quaternary" />
          </a>
        </div>
      </Card>

      {/* Community */}
      <Card className="animate-card-in" style={{ animationDelay: '175ms' }}>
        <div className="p-6">
          <div className="flex items-start gap-3 mb-4">
            <div className="shrink-0 h-9 w-9 rounded-xl bg-oe-blue/10 text-oe-blue flex items-center justify-center">
              <MessageCircle size={18} />
            </div>
            <div className="min-w-0 flex-1">
              <h3 className="text-sm font-semibold text-content-primary">
                {t('about.community_title', { defaultValue: 'Join the Community' })}
              </h3>
              <p className="text-xs text-content-secondary mt-1 leading-relaxed">
                {t('about.community_desc', {
                  defaultValue: 'Your feedback shapes the roadmap. Every release in the changelog started as a user request.',
                })}
              </p>
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
            <a
              href="https://t.me/nexus.eliteal"
              target="_blank"
              rel="noopener noreferrer"
              className="group flex items-center gap-2.5 rounded-lg border border-border-light bg-surface-primary px-3 py-2.5 hover:border-[#26A5E4]/50 hover:bg-[#26A5E4]/[0.04] transition-all"
            >
              <span className="shrink-0 h-8 w-8 rounded-md bg-[#26A5E4]/10 text-[#26A5E4] flex items-center justify-center">
                <svg viewBox="0 0 24 24" fill="currentColor" className="h-4 w-4" aria-hidden>
                  <path d="M9.78 18.65l.28-4.23 7.68-6.92c.34-.31-.07-.46-.52-.19L7.74 13.3 3.64 12c-.88-.25-.89-.86.2-1.3l15.97-6.16c.73-.33 1.43.18 1.15 1.3l-2.72 12.81c-.19.91-.74 1.13-1.5.71l-4.14-3.06-1.99 1.93c-.23.23-.42.42-.83.42z" />
                </svg>
              </span>
              <div className="min-w-0 flex-1">
                <p className="text-xs font-semibold text-content-primary leading-tight">Telegram</p>
                <p className="text-[10px] text-content-tertiary truncate">
                  {t('about.community_telegram', { defaultValue: 'Live chat & support' })}
                </p>
              </div>
              <ExternalLink size={11} className="text-content-quaternary group-hover:text-[#26A5E4] shrink-0" />
            </a>

            <a
              href="https://x.com/nexus.eliteal"
              target="_blank"
              rel="noopener noreferrer"
              className="group flex items-center gap-2.5 rounded-lg border border-border-light bg-surface-primary px-3 py-2.5 hover:border-slate-700 hover:bg-slate-900/[0.04] dark:hover:border-slate-300 transition-all"
            >
              <span className="shrink-0 h-8 w-8 rounded-md bg-slate-900 text-white dark:bg-slate-100 dark:text-slate-900 flex items-center justify-center">
                <svg viewBox="0 0 24 24" fill="currentColor" className="h-3.5 w-3.5" aria-hidden>
                  <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231 5.45-6.231zm-1.161 17.52h1.833L7.084 4.126H5.117l11.966 15.644z" />
                </svg>
              </span>
              <div className="min-w-0 flex-1">
                <p className="text-xs font-semibold text-content-primary leading-tight">X / Twitter</p>
                <p className="text-[10px] text-content-tertiary truncate">
                  {t('about.community_x', { defaultValue: 'Release announcements' })}
                </p>
              </div>
              <ExternalLink size={11} className="text-content-quaternary group-hover:text-content-primary shrink-0" />
            </a>
          </div>

          <p className="mt-4 text-[11px] text-content-tertiary text-center">
            {t('about.community_cta', {
              defaultValue: 'Have a feature idea or found a bug? Reach out — we respond to every message.',
            })}
          </p>
        </div>
      </Card>

      {/* Consulting Services */}
      <Card className="animate-card-in" style={{ animationDelay: '200ms' }}>
        <div className="p-6">
          <div className="flex items-center gap-2 mb-4">
            <Briefcase size={18} className="text-oe-blue" />
            <h2 className="text-lg font-semibold text-content-primary">
              {t('about.services_title', { defaultValue: 'Consulting & Professional Services' })}
            </h2>
          </div>
          <p className="text-sm text-content-secondary leading-relaxed mb-4">
            {t('about.services_desc', { defaultValue: 'Professional consulting services for construction companies, cost estimators, and technology teams worldwide.' })}
          </p>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {[
              { icon: Building2, title: t('about.service_estimation', { defaultValue: 'Cost Estimation Consulting' }), desc: t('about.service_estimation_desc', { defaultValue: 'Expert BOQ preparation, cost analysis, and estimation methodology for projects of any scale.' }) },
              { icon: Code2, title: t('about.service_implementation', { defaultValue: 'Platform Implementation' }), desc: t('about.service_implementation_desc', { defaultValue: 'Custom deployment, integration with existing systems (SAP, Procore, MS Project), and team training.' }) },
              { icon: BookOpen, title: t('about.service_databases', { defaultValue: 'Cost Database Development' }), desc: t('about.service_databases_desc', { defaultValue: 'Regional cost database creation, CWICR licensing, and data pipeline setup for your organization.' }) },
              { icon: Users, title: t('about.service_training', { defaultValue: 'Training & Workshops' }), desc: t('about.service_training_desc', { defaultValue: 'Team training on digital estimation, AI-powered workflows, and BIM quantity takeoff.' }) },
            ].map((s, i) => (
              <div key={i} className="rounded-xl border border-border-light p-4 hover:bg-surface-secondary/30 transition-colors">
                <div className="flex items-center gap-2 mb-2">
                  <s.icon size={16} className="text-oe-blue" />
                  <span className="text-sm font-semibold text-content-primary">{s.title}</span>
                </div>
                <p className="text-xs text-content-tertiary leading-relaxed">{s.desc}</p>
              </div>
            ))}
          </div>

          <div className="mt-4 flex items-center gap-3">
            <a href="https://nexus.eliteal.info/contact-support/" target="_blank" rel="noopener noreferrer">
              <Button variant="primary" size="sm" icon={<Mail size={14} />}>
                {t('about.contact_us', { defaultValue: 'Contact Us' })}
              </Button>
            </a>
            <span className="text-xs text-content-tertiary">
              {t('about.contact_hint', { defaultValue: 'Available worldwide' })}
            </span>
          </div>
        </div>
      </Card>

      {/* Documentation */}
      <Card className="animate-card-in" style={{ animationDelay: '240ms' }}>
        <div className="p-6">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-oe-blue-subtle">
              <BookOpen size={20} className="text-oe-blue" />
            </div>
            <div className="flex-1">
              <h2 className="text-lg font-semibold text-content-primary">
                {t('about.docs_title', { defaultValue: 'Documentation' })}
              </h2>
              <p className="text-xs text-content-tertiary">
                {t('about.docs_desc', { defaultValue: 'Installation guides, feature overview, API reference, and tutorials' })}
              </p>
            </div>
            <a
              href="https://nexus.eliteal.info/docs.html"
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1.5 rounded-lg bg-oe-blue px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-oe-blue/90 transition-colors"
            >
              <BookOpen size={14} />
              {t('about.docs_open', { defaultValue: 'Open Docs' })}
              <ExternalLink size={12} />
            </a>
          </div>
        </div>
      </Card>

      {/* Support NEXUS */}
      <Card
        padding="none"
        className="animate-card-in overflow-hidden"
        style={{ animationDelay: '250ms' }}
      >
        <div className="relative">
          <div className="absolute inset-0 bg-gradient-to-br from-amber-500/[0.10] via-orange-500/[0.06] to-rose-500/[0.10]" />
          <div className="absolute inset-0 bg-[radial-gradient(circle_at_20%_0%,rgba(251,191,36,0.12),transparent_50%),radial-gradient(circle_at_90%_100%,rgba(244,63,94,0.12),transparent_55%)]" />

          <div className="relative">
            <div className="text-center pt-8 pb-6 px-6">
              <div className="inline-flex items-center gap-2.5 mb-3">
                <div className="flex h-9 w-9 items-center justify-center rounded-full bg-white/70 dark:bg-white/5 shadow-sm ring-1 ring-black/[0.04] dark:ring-white/[0.06]">
                  <Handshake size={18} className="text-oe-blue" />
                </div>
                <h2 className="text-2xl font-bold tracking-tight text-content-primary">
                  {t('about.support_title', { defaultValue: 'Support NEXUS' })}
                </h2>
              </div>
              <p className="text-sm text-content-secondary leading-relaxed max-w-xl mx-auto">
                {t('about.support_desc', { defaultValue: 'This project is free and open-source — built by construction professionals, for construction professionals. Your support keeps it alive and growing.' })}
              </p>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-px bg-border-light/60 dark:bg-white/[0.06]">
              <a
                href="https://github.com/nexus.eliteal"
                target="_blank"
                rel="noopener noreferrer"
                className="group relative flex flex-col items-center gap-2 bg-surface-primary/80 backdrop-blur-sm px-5 py-6 hover:bg-amber-50/70 dark:hover:bg-amber-900/15 transition-colors"
              >
                <Star size={30} className="text-amber-500 transition-transform group-hover:scale-110 group-hover:-rotate-6" fill="currentColor" />
                <span className="text-sm font-bold text-content-primary">
                  {t('about.support_star', { defaultValue: 'Star on GitHub' })}
                </span>
                <span className="text-2xs text-content-tertiary text-center leading-snug">
                  {t('about.support_star_desc', { defaultValue: 'Help others discover the project' })}
                </span>
              </a>

              <a
                href="https://github.com/sponsors/nexus.eliteal"
                target="_blank"
                rel="noopener noreferrer"
                className="group relative flex flex-col items-center gap-2 bg-surface-primary/80 backdrop-blur-sm px-5 py-6 hover:bg-rose-50/70 dark:hover:bg-rose-900/15 transition-colors"
              >
                <Coffee size={30} className="text-rose-500 transition-transform group-hover:scale-110" />
                <span className="text-sm font-bold text-content-primary">
                  {t('about.support_sponsor', { defaultValue: 'Become a Sponsor' })}
                </span>
                <span className="text-2xs text-content-tertiary text-center leading-snug">
                  {t('about.support_sponsor_desc', { defaultValue: 'Fund new features and keep the project free' })}
                </span>
              </a>

              <a
                href="https://nexus.eliteal.info/contact-support/"
                target="_blank"
                rel="noopener noreferrer"
                className="group relative flex flex-col items-center gap-2 bg-surface-primary/80 backdrop-blur-sm px-5 py-6 hover:bg-oe-blue/[0.06] dark:hover:bg-blue-900/15 transition-colors"
              >
                <Rocket size={30} className="text-oe-blue transition-transform group-hover:scale-110 group-hover:-translate-y-0.5" />
                <span className="text-sm font-bold text-content-primary">
                  {t('about.support_consulting', { defaultValue: 'Order Consulting' })}
                </span>
                <span className="text-2xs text-content-tertiary text-center leading-snug">
                  {t('about.support_consulting_desc', { defaultValue: 'Custom features, deployment, or training worldwide' })}
                </span>
              </a>
            </div>

            <div className="px-6 py-5 border-t border-border-light/60 dark:border-white/[0.06]">
              <p className="text-xs font-semibold uppercase tracking-wider text-content-tertiary mb-3 flex items-center gap-1.5">
                <Rocket size={12} className="text-oe-blue" />
                {t('about.support_enables', { defaultValue: 'Your support enables:' })}
              </p>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-x-6 gap-y-1.5">
                {[
                  t('about.support_e1', { defaultValue: 'New regional cost databases (CWICR)' }),
                  t('about.support_e2', { defaultValue: 'AI estimation improvements' }),
                  t('about.support_e3', { defaultValue: 'More CAD/BIM format support' }),
                  t('about.support_e4', { defaultValue: 'Better PDF takeoff tools' }),
                  t('about.support_e5', { defaultValue: 'Mobile app development' }),
                  t('about.support_e6', { defaultValue: 'Free workshops and documentation' }),
                ].map((item, i) => (
                  <div key={i} className="flex items-center gap-1.5 text-xs text-content-secondary">
                    <ArrowRight size={10} className="text-oe-blue shrink-0" />
                    {item}
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </Card>

      {/* Free Guidebook */}
      <Card className="animate-card-in" style={{ animationDelay: '300ms' }}>
        <div className="p-6">
          <div className="flex items-center gap-2 mb-3">
            <BookOpen size={18} className="text-oe-blue" />
            <h2 className="text-lg font-semibold text-content-primary">
              {t('about.book_title', { defaultValue: 'Free Guidebook: Data Driven Construction' })}
            </h2>
            <Badge variant="blue" size="sm">Free Download</Badge>
          </div>
          <a
            href="https://nexus.eliteal.info/books/"
            target="_blank"
            rel="noopener noreferrer"
            className="group mb-4 block overflow-hidden rounded-xl bg-gradient-to-br from-slate-50 via-white to-blue-50 dark:from-slate-900 dark:via-slate-900 dark:to-slate-800 border border-border-light hover:border-oe-blue/40 hover:shadow-lg transition-all"
          >
            <img
              src="/brand/ddc-book.png"
              alt={t('about.book_title', { defaultValue: 'Free Guidebook: Data Driven Construction' })}
              className="block w-full h-auto transition-transform duration-500 group-hover:scale-[1.02]"
              loading="lazy"
            />
          </a>
          <p className="text-sm text-content-secondary leading-relaxed mb-4">
            {t('about.book_desc', { defaultValue: 'A comprehensive guide to digital transformation in the construction industry. Covers project data management, cost estimation automation, AI in construction, and data-driven decision making.' })}
          </p>
          <a
            href="https://nexus.eliteal.info/books/"
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-2 rounded-lg bg-oe-blue px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 transition-colors shadow-sm"
          >
            <BookOpen size={14} />
            {t('about.book_download', { defaultValue: 'Download Free Guide' })}
            <ExternalLink size={12} />
          </a>
        </div>
      </Card>

      {/* License */}
      <Card className="animate-card-in" style={{ animationDelay: '350ms' }}>
        <div className="p-6">
          <div className="flex items-center gap-2 mb-3">
            <Shield size={18} className="text-emerald-500" />
            <h2 className="text-lg font-semibold text-content-primary">
              {t('about.license_title', { defaultValue: 'License & Freedom' })}
            </h2>
          </div>
          <p className="text-sm text-content-secondary leading-relaxed mb-3">
            {t('about.license_desc', { defaultValue: 'NEXUS is free and open-source software. Deploy it on your own infrastructure with full control over your data.' })}
          </p>
          <div className="flex flex-wrap gap-2">
            <Badge variant="success" size="sm">Free to use</Badge>
            <Badge variant="success" size="sm">Open source</Badge>
            <Badge variant="success" size="sm">Self-hosted</Badge>
            <Badge variant="success" size="sm">No vendor lock-in</Badge>
          </div>
        </div>
      </Card>

      {/* Changelog */}
      <Card>
        <div className="p-6">
          <Changelog />
        </div>
      </Card>

      {/* Footer */}
      <div className="text-center py-4 text-xs text-content-quaternary">
        <p className="flex items-center justify-center gap-1">
          &copy; {new Date().getFullYear()} O&apos;Neill Contractors, Inc. &middot; All rights reserved.
        </p>
      </div>
    </div>
  );
}
