import React, { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { AlertCircle, ArrowRight, Clock, FolderPlus, Loader2, Plus } from "lucide-react";
import { api, type DashboardReviewSummary } from "../../api/client";
import { ErrorState, LoadingRegion, SkeletonCard } from "../../components/Feedback";
import { useAuth } from "../../context/AuthContext";
import { rememberWorkspaceId } from "../../context/currentWorkspace";

function timeAgo(iso: string): string {
  const then = new Date(iso.endsWith("Z") || iso.includes("+") ? iso : `${iso}Z`).getTime();
  const mins = Math.max(0, Math.round((Date.now() - then) / 60000));
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins} min ago`;
  const hours = Math.round(mins / 60);
  if (hours < 24) return `${hours} h ago`;
  const days = Math.round(hours / 24);
  return days < 30 ? `${days} d ago` : new Date(then).toLocaleDateString();
}

const Stat: React.FC<{ label: string; value: number; tone?: string }> = ({ label, value, tone }) => (
  <div className="min-w-[4.5rem]">
    <div className={`text-lg font-semibold tabular-nums ${tone ?? "text-[var(--text-primary)]"}`}>{value}</div>
    <div className="text-[11px] uppercase tracking-wide text-[var(--text-muted)]">{label}</div>
  </div>
);

const ReviewCard: React.FC<{ review: DashboardReviewSummary }> = ({ review }) => {
  const started = review.group_count > 0;
  const target = `/reviews/${encodeURIComponent(review.id)}/${started ? "records" : "setup"}`;
  const progress = review.group_count ? Math.round((review.reviewed_by_human / review.group_count) * 100) : 0;
  return (
    <Link
      to={target}
      onClick={() => rememberWorkspaceId(review.id)}
      className="group glass-panel block p-5 sm:p-6 space-y-4 hover:border-[var(--border-gold)]"
    >
      <div className="flex items-start gap-4">
        <div className="flex-1 min-w-0 space-y-1">
          <h3 className="font-semibold text-[var(--text-primary)] text-base leading-snug">{review.title}</h3>
          <p className="text-sm text-[var(--text-muted)] line-clamp-2">
            {review.question ?? "No review question saved yet."}
          </p>
        </div>
        <span className="inline-flex items-center gap-1.5 text-sm font-medium text-[var(--accent-gold)] shrink-0">
          {started ? "Continue screening" : "Continue setup"}
          <ArrowRight className="w-4 h-4 transition-transform group-hover:translate-x-0.5" />
        </span>
      </div>

      {started ? (
        <>
          <div className="flex flex-wrap gap-x-6 gap-y-3">
            <Stat label="Papers" value={review.group_count} />
            <Stat label="Included" value={review.included} tone="text-emerald-400" />
            <Stat label="Excluded" value={review.excluded} tone="text-rose-400" />
            <Stat label="Maybe" value={review.maybe} tone="text-amber-400" />
            {review.conflicts > 0 && <Stat label="Conflicts" value={review.conflicts} tone="text-orange-400" />}
            <Stat label="To review" value={review.awaiting_review} />
          </div>
          <div className="space-y-1">
            <div
              className="h-1.5 w-full rounded-full bg-[var(--border-subtle)] overflow-hidden"
              role="progressbar"
              aria-valuenow={progress}
              aria-valuemin={0}
              aria-valuemax={100}
              aria-label="Papers reviewed by you"
            >
              <div className="h-full bg-[var(--accent-gold)]" style={{ width: `${progress}%` }} />
            </div>
            <p className="text-xs text-[var(--text-muted)]">
              {review.reviewed_by_human} of {review.group_count} reviewed by you
            </p>
          </div>
        </>
      ) : (
        <p className="text-sm text-[var(--text-secondary)]">
          Next: save the review question, run the search and import papers.
        </p>
      )}

      <p className="flex items-center gap-1.5 text-xs text-[var(--text-muted)]">
        <Clock className="w-3 h-3" /> Last activity {timeAgo(review.last_activity_at)}
      </p>
    </Link>
  );
};

export const DashboardPage: React.FC = () => {
  const navigate = useNavigate();
  const { user } = useAuth();
  const [reviews, setReviews] = useState<DashboardReviewSummary[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [loadError, setLoadError] = useState<unknown>(null);
  const [reloadKey, setReloadKey] = useState(0);

  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);

  useEffect(() => {
    let mounted = true;
    setIsLoading(true);
    setLoadError(null);
    api.dashboard
      .list()
      .then((list) => mounted && setReviews(list))
      .catch((err: unknown) => mounted && setLoadError(err))
      .finally(() => mounted && setIsLoading(false));
    return () => {
      mounted = false;
    };
  }, [reloadKey]);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim()) return;
    setIsSubmitting(true);
    setCreateError(null);
    try {
      const ws = await api.workspaces.create({ title: title.trim(), description: description.trim() || undefined });
      rememberWorkspaceId(ws.id);
      navigate(`/reviews/${encodeURIComponent(ws.id)}/setup`, { state: { createdTitle: ws.title } });
    } catch (err: unknown) {
      setCreateError(err instanceof Error ? err.message : "Couldn't create the review. Try again.");
      setIsSubmitting(false);
    }
  };

  const firstName = user?.name?.split(" ")[0];

  return (
    <div className="space-y-10 pb-12">
      <header className="max-w-2xl space-y-2">
        <h1 className="text-2xl text-[var(--text-primary)]">{firstName ? `Welcome back, ${firstName}` : "Your dashboard"}</h1>
        <p className="text-[var(--text-secondary)]">
          Each review holds one question, its searches, imported papers and your screening decisions.
        </p>
      </header>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
        <section aria-labelledby="reviews-heading" className="lg:col-span-7 xl:col-span-8 space-y-4">
          <div className="flex items-baseline justify-between">
            <h2 id="reviews-heading" className="text-xl text-[var(--text-primary)]">
              Your reviews
            </h2>
            {!isLoading && !loadError && (
              <span className="text-sm text-[var(--text-muted)]">
                {reviews.length} {reviews.length === 1 ? "review" : "reviews"}
              </span>
            )}
          </div>

          {isLoading ? (
            <LoadingRegion label="Loading your reviews" className="space-y-3">
              <SkeletonCard lines={3} />
              <SkeletonCard lines={3} />
            </LoadingRegion>
          ) : loadError != null ? (
            <ErrorState compact error={loadError} onRetry={() => setReloadKey((k) => k + 1)} what="Your reviews" />
          ) : reviews.length === 0 ? (
            <div className="glass-panel p-8 text-center space-y-2">
              <p className="font-semibold text-[var(--text-primary)]">No reviews yet</p>
              <p className="text-sm text-[var(--text-muted)]">Create your first review with the form to get started.</p>
            </div>
          ) : (
            <ul className="space-y-3">
              {reviews.map((r) => (
                <li key={r.id}>
                  <ReviewCard review={r} />
                </li>
              ))}
            </ul>
          )}
        </section>

        <aside className="lg:col-span-5 xl:col-span-4 lg:sticky lg:top-24">
          <div className="glass-panel-luxury p-6 space-y-5">
            <div className="flex items-center gap-3">
              <span className="grid place-items-center w-9 h-9 rounded-lg border border-[var(--border-gold)] bg-[var(--gold-glow)]">
                <FolderPlus className="w-4 h-4 text-[var(--accent-gold)]" strokeWidth={1.75} />
              </span>
              <h2 className="text-xl text-[var(--text-primary)]">New review</h2>
            </div>
            <form onSubmit={handleCreate} className="space-y-4">
              <div className="space-y-1.5">
                <label htmlFor="ws-title" className="block text-sm font-medium text-[var(--text-secondary)]">
                  Review name
                </label>
                <input
                  id="ws-title"
                  type="text"
                  required
                  placeholder="SGLT2i and HF hospitalization in T2D"
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  className="w-full px-3.5 py-2.5 bg-[var(--bg-base)]/60 border border-[var(--border-silver)] text-[var(--text-primary)] text-sm"
                />
                <p className="text-xs text-[var(--text-muted)]">A short name. You'll write the full question next.</p>
              </div>
              <div className="space-y-1.5">
                <label htmlFor="ws-desc" className="block text-sm font-medium text-[var(--text-secondary)]">
                  Notes <span className="font-normal text-[var(--text-muted)]">(optional)</span>
                </label>
                <textarea
                  id="ws-desc"
                  rows={3}
                  placeholder="Protocol context, planned synthesis"
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  className="w-full px-3.5 py-2.5 bg-[var(--bg-base)]/60 border border-[var(--border-silver)] text-[var(--text-primary)] text-sm resize-y"
                />
              </div>
              {createError && (
                <p role="alert" className="flex items-center gap-2 text-sm text-rose-400">
                  <AlertCircle className="w-4 h-4 shrink-0" />
                  {createError}
                </p>
              )}
              <button
                type="submit"
                disabled={isSubmitting || !title.trim()}
                className="btn-gold w-full disabled:opacity-50 disabled:filter-none"
              >
                {isSubmitting ? <Loader2 className="w-4 h-4 animate-spin" /> : <Plus className="w-4 h-4" />}
                Create review
              </button>
            </form>
          </div>
        </aside>
      </div>
    </div>
  );
};

export default DashboardPage;
