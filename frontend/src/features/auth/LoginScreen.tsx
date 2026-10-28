import React, { useState } from "react";
import { ArrowRight, Eye, EyeOff, Loader2, Lock, Sparkles } from "lucide-react";
import { api, ApiError } from "../../api/client";
import { DashGridBackground } from "../../components/DashGridBackground";

export const LoginScreen: React.FC<{ onSignedIn: () => void }> = ({ onSignedIn }) => {
  const [password, setPassword] = useState("");
  const [visible, setVisible] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!password) return;
    setSubmitting(true);
    setError(null);
    try {
      await api.auth.login(password);
      onSignedIn();
    } catch (err: unknown) {
      setError(err instanceof ApiError || err instanceof Error ? err.message : "Couldn't sign in. Try again.");
      setSubmitting(false);
    }
  };

  return (
    <div className="relative min-h-screen flex flex-col bg-[var(--bg-base)] text-[var(--text-primary)]">
      <DashGridBackground />
      <main id="main-content" className="relative z-10 flex-1 grid place-items-center px-4 py-16">
        <div className="w-full max-w-md space-y-8">
          <div className="flex items-center justify-center gap-2.5">
            <span className="grid place-items-center w-9 h-9 rounded-lg border border-[var(--border-gold)] bg-[var(--gold-glow)]">
              <Sparkles className="w-4 h-4 text-[var(--accent-gold)]" strokeWidth={1.75} />
            </span>
            <span className="font-serif text-2xl font-medium tracking-tight">Evidra</span>
          </div>

          <form onSubmit={submit} className="glass-panel-luxury p-7 sm:p-8 space-y-6" noValidate>
            <div className="space-y-2 text-center">
              <h1 className="text-3xl text-[var(--text-primary)]">Enter the site password</h1>
              <p className="text-sm text-[var(--text-secondary)]">
                This Evidra demo is private. Ask the team for the password if you don't have it.
              </p>
            </div>

            <div className="space-y-1.5">
              <label htmlFor="site-password" className="block text-sm font-medium text-[var(--text-secondary)]">
                Password
              </label>
              <div className="relative">
                <Lock className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-[var(--text-muted)]" aria-hidden="true" />
                <input
                  id="site-password"
                  type={visible ? "text" : "password"}
                  autoComplete="current-password"
                  autoFocus
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  aria-invalid={error ? true : undefined}
                  aria-describedby={error ? "site-password-error" : undefined}
                  className="w-full pl-10 pr-11 py-3 bg-[var(--bg-base)]/60 border border-[var(--border-silver)] text-[var(--text-primary)] text-sm"
                />
                <button
                  type="button"
                  onClick={() => setVisible((v) => !v)}
                  aria-label={visible ? "Hide password" : "Show password"}
                  className="absolute right-2 top-1/2 -translate-y-1/2 grid place-items-center w-8 h-8 rounded-md text-[var(--text-muted)] hover:text-[var(--accent-gold)]"
                >
                  {visible ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
              {error && (
                <p id="site-password-error" role="alert" className="text-sm text-rose-400">
                  {error}
                </p>
              )}
            </div>

            <button type="submit" disabled={submitting || !password} className="btn-gold w-full disabled:opacity-50">
              {submitting ? <Loader2 className="w-4 h-4 animate-spin" /> : null}
              {submitting ? "Checking…" : "Open Evidra"}
              {!submitting && <ArrowRight className="w-4 h-4" />}
            </button>
          </form>

          <p className="text-center text-xs text-[var(--text-muted)]">
            Systematic literature review with traceable evidence.
          </p>
        </div>
      </main>
    </div>
  );
};

export default LoginScreen;
