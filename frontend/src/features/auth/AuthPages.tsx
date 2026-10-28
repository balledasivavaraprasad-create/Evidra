import React, { useState } from "react";
import { Link, Navigate, useNavigate, useSearchParams } from "react-router-dom";
import { ArrowRight, Eye, EyeOff, Loader2, Lock, Mail, User } from "lucide-react";
import { api, ApiError, isServiceUnreachable, type AuthUser } from "../../api/client";
import { safeNextPath, useAuth } from "../../context/AuthContext";
import { GoogleSignInButton } from "./GoogleSignInButton";

type Mode = "signin" | "signup";

const inputClass =
  "w-full pl-10 pr-3.5 py-3 bg-[var(--bg-base)]/60 border border-[var(--border-silver)] text-[var(--text-primary)] text-sm";

function messageFor(err: unknown): string {
  if (isServiceUnreachable(err)) {
    return "The server is waking up or unreachable. Wait a few seconds, then try again.";
  }
  if (err instanceof ApiError) {
    if (err.status === 422 && err.code !== "INVALID_EMAIL") {
      return "Check the form: passwords need at least 8 characters.";
    }
    return err.message;
  }
  return err instanceof Error ? err.message : "Something went wrong. Try again.";
}

const Field: React.FC<{
  id: string;
  label: string;
  icon: React.ReactNode;
  children: React.ReactNode;
  hint?: string;
}> = ({ id, label, icon, children, hint }) => (
  <div className="space-y-1.5">
    <label htmlFor={id} className="block text-sm font-medium text-[var(--text-secondary)]">
      {label}
    </label>
    <div className="relative">
      <span className="absolute left-3.5 top-1/2 -translate-y-1/2 text-[var(--text-muted)]" aria-hidden="true">
        {icon}
      </span>
      {children}
    </div>
    {hint && <p className="text-xs text-[var(--text-muted)]">{hint}</p>}
  </div>
);

const AuthForm: React.FC<{ mode: Mode }> = ({ mode }) => {
  const { status, setSignedIn, googleClientId, authRequired } = useAuth();
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const next = safeNextPath(params.get("next"));

  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [visible, setVisible] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (status === "signed-in" || !authRequired) {
    return <Navigate to={next} replace />;
  }

  const finish = (user: AuthUser) => {
    setSignedIn(user);
    navigate(next, { replace: true });
  };

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      const user =
        mode === "signup"
          ? await api.auth.signUp({ name: name.trim(), email: email.trim(), password })
          : await api.auth.login({ email: email.trim(), password });
      finish(user);
    } catch (err) {
      setError(messageFor(err));
      setSubmitting(false);
    }
  };

  const onGoogle = async (credential: string) => {
    setSubmitting(true);
    setError(null);
    try {
      finish(await api.auth.google(credential));
    } catch (err) {
      setError(messageFor(err));
      setSubmitting(false);
    }
  };

  const isSignup = mode === "signup";
  const canSubmit = email.trim() && password && (!isSignup || (name.trim() && password.length >= 8));
  const otherLink = `${isSignup ? "/signin" : "/signup"}${params.get("next") ? `?next=${encodeURIComponent(next)}` : ""}`;

  return (
    <div className="relative min-h-[calc(100vh-4rem)] grid place-items-center px-4 py-12">
      <div className="w-full max-w-md space-y-6">
        <div className="space-y-2 text-center">
          <h1 className="text-3xl text-[var(--text-primary)]">{isSignup ? "Create your account" : "Sign in to Evidra"}</h1>
          <p className="text-sm text-[var(--text-secondary)]">
            {isSignup
              ? "Your reviews are private to your account and saved permanently."
              : "Pick up your reviews where you left off."}
          </p>
        </div>

        <div className="glass-panel-luxury p-7 sm:p-8 space-y-6">
          {googleClientId && (
            <>
              <GoogleSignInButton
                clientId={googleClientId}
                text={isSignup ? "signup_with" : "continue_with"}
                onCredential={(c) => void onGoogle(c)}
              />
              <div className="flex items-center gap-3 text-xs text-[var(--text-muted)]">
                <span className="h-px flex-1 bg-[var(--border-silver)]" />
                or with email
                <span className="h-px flex-1 bg-[var(--border-silver)]" />
              </div>
            </>
          )}

          <form onSubmit={submit} className="space-y-4" noValidate>
            {isSignup && (
              <Field id="auth-name" label="Name" icon={<User className="w-4 h-4" />}>
                <input
                  id="auth-name"
                  type="text"
                  autoComplete="name"
                  required
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  className={inputClass}
                />
              </Field>
            )}
            <Field id="auth-email" label="Email" icon={<Mail className="w-4 h-4" />}>
              <input
                id="auth-email"
                type="email"
                autoComplete="email"
                autoFocus={!isSignup}
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className={inputClass}
              />
            </Field>
            <Field
              id="auth-password"
              label="Password"
              icon={<Lock className="w-4 h-4" />}
              hint={isSignup ? "At least 8 characters." : undefined}
            >
              <input
                id="auth-password"
                type={visible ? "text" : "password"}
                autoComplete={isSignup ? "new-password" : "current-password"}
                required
                minLength={isSignup ? 8 : undefined}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                aria-invalid={error ? true : undefined}
                aria-describedby={error ? "auth-error" : undefined}
                className={`${inputClass} pr-11`}
              />
              <button
                type="button"
                onClick={() => setVisible((v) => !v)}
                aria-label={visible ? "Hide password" : "Show password"}
                className="absolute right-2 top-1/2 -translate-y-1/2 grid place-items-center w-8 h-8 rounded-md text-[var(--text-muted)] hover:text-[var(--accent-gold)]"
              >
                {visible ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
              </button>
            </Field>

            {error && (
              <p id="auth-error" role="alert" className="text-sm text-rose-400">
                {error}
              </p>
            )}

            <button type="submit" disabled={submitting || !canSubmit} className="btn-ink w-full disabled:opacity-50">
              {submitting ? <Loader2 className="w-4 h-4 animate-spin" /> : null}
              {submitting ? (isSignup ? "Creating account…" : "Signing in…") : isSignup ? "Create account" : "Sign in"}
              {!submitting && <ArrowRight className="w-4 h-4" />}
            </button>
          </form>
        </div>

        <p className="text-center text-sm text-[var(--text-secondary)]">
          {isSignup ? "Already have an account? " : "New to Evidra? "}
          <Link to={otherLink} className="font-medium text-[var(--accent-gold)] hover:underline">
            {isSignup ? "Sign in" : "Create an account"}
          </Link>
        </p>
      </div>
    </div>
  );
};

export const SignInPage: React.FC = () => <AuthForm mode="signin" />;
export const SignUpPage: React.FC = () => <AuthForm mode="signup" />;
