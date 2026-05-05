/**
 * Ambient declarations for Vite-injected build-time globals used by the
 * OCERP frontend.  These show up in transitive imports (e.g.
 * `shared/lib/version.ts`); declaring them here keeps `tsc --noEmit` clean
 * without us touching the OCERP source tree.
 */

declare const __APP_VERSION__: string;
