import { useState, useRef, useEffect, useMemo, type FormEvent } from 'react';
import { useTranslation } from 'react-i18next';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import {
  ArrowLeft,
  Lock,
  CheckCircle2,
  AlertTriangle,
  Globe,
  ChevronDown,
} from 'lucide-react';
import { Button, Input, Logo, CountryFlag } from '@/shared/ui';
import { SUPPORTED_LANGUAGES, getLanguageByCode } from '@/app/i18n';
import { AuthBackground } from './AuthBackground';

export function ResetPasswordPage() {
  const { t, i18n } = useTranslation();
  const navigate = useNavigate();
  const currentLang = getLanguageByCode(i18n.language);
  const [searchParams] = useSearchParams();
  const token = searchParams.get('token') ?? '';

  const [password, setPassword] = useState('');
  const [confirm, setConfirm] = useState('');
  const [submitted, setSubmitted] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [langOpen, setLangOpen] = useState(false);
  const langRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (langRef.current && !langRef.current.contains(e.target as Node)) setLangOpen(false);
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  // Auto-redirect to /login a few seconds after a successful reset so the
  // user lands on the sign-in screen ready to use their new password.
  useEffect(() => {
    if (!submitted) return;
    const id = window.setTimeout(() => navigate('/login', { replace: true }), 3000);
    return () => window.clearTimeout(id);
  }, [submitted, navigate]);

  // Mirrors the backend rules in schemas.py (_validate_strong_password):
  // 8+ chars, at least one letter, at least one digit.
  const validationError = useMemo<string | null>(() => {
    if (password.length === 0) return null;
    if (password.length < 8) return t('auth.pw_too_short', 'Password must be at least 8 characters');
    if (!/[A-Za-z]/.test(password)) return t('auth.pw_needs_letter', 'Password must contain at least one letter');
    if (!/\d/.test(password)) return t('auth.pw_needs_digit', 'Password must contain at least one digit');
    if (confirm.length > 0 && password !== confirm) return t('auth.pw_mismatch', 'Passwords do not match');
    return null;
  }, [password, confirm, t]);

  const canSubmit = !!token && !validationError && password.length > 0 && confirm.length > 0;

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (!canSubmit) return;
    setError('');
    setLoading(true);

    try {
      const res = await fetch('/api/v1/users/auth/reset-password/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ token, new_password: password }),
      });

      if (!res.ok) {
        const data = await res.json().catch(() => null);
        const detail = data?.detail;
        const message =
          typeof detail === 'string'
            ? detail
            : Array.isArray(detail) && detail[0]?.msg
              ? detail[0].msg
              : t('auth.reset_error', 'Unable to reset password. The link may have expired.');
        setError(message);
        return;
      }

      setSubmitted(true);
    } catch {
      setError(t('auth.server_error', 'Unable to connect to server. Please try again.'));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="relative flex min-h-screen items-center justify-center bg-surface-secondary p-4 overflow-hidden">
      <AuthBackground />

      {/* Language — top right */}
      <div className="absolute top-3 right-3 z-30" ref={langRef}>
        <button
          onClick={() => setLangOpen(!langOpen)}
          className="flex items-center gap-1.5 rounded-lg border border-border-light bg-surface-elevated/80 backdrop-blur-sm px-2.5 py-1 text-xs text-content-secondary hover:bg-surface-elevated transition-colors shadow-sm"
        >
          <Globe size={12} className="text-content-tertiary" />
          <CountryFlag code={currentLang.country} size={14} />
          <span className="hidden sm:inline">{currentLang.name}</span>
          <ChevronDown
            size={11}
            className={`text-content-tertiary transition-transform ${langOpen ? 'rotate-180' : ''}`}
          />
        </button>
        {langOpen && (
          <div className="absolute right-0 mt-1 w-44 max-h-72 overflow-y-auto rounded-xl border border-border-light bg-surface-elevated shadow-xl py-0.5 animate-stagger-in">
            {SUPPORTED_LANGUAGES.map((lang) => {
              const isActive = i18n.language === lang.code;
              return (
                <button
                  key={lang.code}
                  onClick={() => {
                    i18n.changeLanguage(lang.code);
                    setLangOpen(false);
                  }}
                  className={`flex w-full items-center gap-2 px-2.5 py-1.5 text-xs transition-colors ${
                    isActive
                      ? 'bg-oe-blue/8 text-oe-blue font-medium'
                      : 'text-content-primary hover:bg-surface-secondary'
                  }`}
                >
                  <CountryFlag code={lang.country} size={14} />
                  <span className="truncate">{lang.name}</span>
                </button>
              );
            })}
          </div>
        )}
      </div>

      <div className="relative z-10 w-full max-w-[400px]">
        {/* Logo */}
        <div className="mb-8 text-center animate-stagger-in" style={{ animationDelay: '0ms' }}>
          <div className="mx-auto mb-4 animate-logo-glow rounded-[20px] w-fit">
            <Logo size="xl" animate className="mx-auto shadow-xl" />
          </div>
        </div>

        {/* Form card */}
        <div
          className="glass-strong rounded-2xl p-7 shadow-lg animate-form-scale-in"
          style={{ animationDelay: '150ms' }}
        >
          {!token ? (
            /* Missing-token state — landed here without a link */
            <div className="text-center py-4 animate-stagger-in" style={{ animationDelay: '200ms' }}>
              <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-semantic-error-bg text-semantic-error">
                <AlertTriangle size={28} />
              </div>
              <h2 className="text-lg font-semibold text-content-primary mb-2">
                {t('auth.reset_no_token_title', 'Invalid reset link')}
              </h2>
              <p className="text-sm text-content-secondary mb-6">
                {t(
                  'auth.reset_no_token_body',
                  'This page must be opened from the reset link in your email. Request a new link to continue.',
                )}
              </p>
              <Link
                to="/forgot-password"
                className="inline-flex items-center gap-1.5 text-sm font-medium text-oe-blue hover:text-oe-blue-hover transition-colors"
              >
                {t('auth.request_new_link', 'Request a new link')}
              </Link>
            </div>
          ) : submitted ? (
            /* Success state */
            <div className="text-center py-4 animate-stagger-in" style={{ animationDelay: '200ms' }}>
              <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-semantic-success-bg text-semantic-success">
                <CheckCircle2 size={28} />
              </div>
              <h2 className="text-lg font-semibold text-content-primary mb-2">
                {t('auth.reset_done_title', 'Password updated')}
              </h2>
              <p className="text-sm text-content-secondary mb-6">
                {t(
                  'auth.reset_done_body',
                  'Your password has been changed. Redirecting you to sign in…',
                )}
              </p>
              <Link
                to="/login"
                className="inline-flex items-center gap-1.5 text-sm font-medium text-oe-blue hover:text-oe-blue-hover transition-colors"
              >
                <ArrowLeft size={14} />
                {t('auth.back_to_login', 'Back to sign in')}
              </Link>
            </div>
          ) : (
            /* Form */
            <>
              <div className="animate-stagger-in" style={{ animationDelay: '200ms' }}>
                <Link
                  to="/login"
                  className="mb-4 flex items-center gap-1.5 text-sm text-content-secondary hover:text-content-primary transition-colors"
                >
                  <ArrowLeft size={14} />
                  {t('auth.back_to_login', 'Back to sign in')}
                </Link>

                <h2 className="text-lg font-semibold text-content-primary mb-1">
                  {t('auth.reset_title', 'Set a new password')}
                </h2>
                <p className="text-sm text-content-secondary mb-6">
                  {t(
                    'auth.reset_subtitle',
                    'Choose a strong password. At least 8 characters with one letter and one digit.',
                  )}
                </p>
              </div>

              <form onSubmit={handleSubmit} className="space-y-4">
                <div className="animate-stagger-in" style={{ animationDelay: '300ms' }}>
                  <Input
                    label={t('auth.new_password', 'New password')}
                    type="password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="••••••••"
                    required
                    autoFocus
                    autoComplete="new-password"
                    icon={<Lock size={16} />}
                  />
                </div>

                <div className="animate-stagger-in" style={{ animationDelay: '340ms' }}>
                  <Input
                    label={t('auth.confirm_password', 'Confirm password')}
                    type="password"
                    value={confirm}
                    onChange={(e) => setConfirm(e.target.value)}
                    placeholder="••••••••"
                    required
                    autoComplete="new-password"
                    icon={<Lock size={16} />}
                  />
                </div>

                {/* Inline validation (client-side mirror of backend rules) */}
                {validationError && (
                  <div className="text-xs text-semantic-warning animate-stagger-in">
                    {validationError}
                  </div>
                )}

                {/* Server error */}
                {error && (
                  <div className="flex items-start gap-2 rounded-lg bg-semantic-error-bg px-3.5 py-2.5 text-sm text-semantic-error animate-stagger-in">
                    <span className="shrink-0 mt-0.5">!</span>
                    <span>{error}</span>
                  </div>
                )}

                <div className="animate-stagger-in" style={{ animationDelay: '380ms' }}>
                  <Button
                    type="submit"
                    variant="primary"
                    size="lg"
                    loading={loading}
                    disabled={!canSubmit || loading}
                    className="w-full btn-shimmer"
                  >
                    {t('auth.reset_submit', 'Update password')}
                  </Button>
                </div>
              </form>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
