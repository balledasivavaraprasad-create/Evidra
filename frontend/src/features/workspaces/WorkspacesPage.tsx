import React, { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Plus, FolderPlus, ArrowRight, Calendar, CheckCircle2, AlertCircle, Loader2 } from "lucide-react";
import { api, type WorkspaceResponse } from "../../api/client";
import { ErrorState, LoadingRegion, SkeletonCard } from "../../components/Feedback";
import { DEMO_WORKSPACE_ID, rememberWorkspaceId } from "../../context/currentWorkspace";

export const WorkspacesPage: React.FC = () => {
  const navigate = useNavigate();
  const [workspaces, setWorkspaces] = useState<WorkspaceResponse[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [loadError, setLoadError] = useState<unknown>(null);
  const [reloadKey, setReloadKey] = useState(0);

  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [feedback, setFeedback] = useState<{ type: "success" | "error"; message: string } | null>(null);

  useEffect(() => {
    let mounted = true;
    setIsLoading(true);
    setLoadError(null);
    api.workspaces
      .list()
      .then((list) => {
        if (mounted) setWorkspaces(list);
      })
      .catch((err: unknown) => {
        if (mounted) setLoadError(err);
      })
      .finally(() => {
        if (mounted) setIsLoading(false);
      });
    return () => {
      mounted = false;
    };
  }, [reloadKey]);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim()) return;

    setIsSubmitting(true);
    setFeedback(null);

    try {
      const newWs = await api.workspaces.create({
        title: title.trim(),
        description: description.trim() || undefined,
      });
      setWorkspaces((prev) => [newWs, ...prev]);
      rememberWorkspaceId(newWs.id);
      // Next step: set up the review question, search and import for the new review
      navigate(`/reviews/${encodeURIComponent(newWs.id)}/setup`, { state: { createdTitle: newWs.title } });
    } catch (err: unknown) {
      setFeedback({
        type: "error",
        message:
          err instanceof Error
            ? err.message
            : "Couldn’t create the workspace. Check that the backend is running, then try again.",
      });
      setIsSubmitting(false);
    }
  };

  return (
    <div className="space-y-10 pb-12">
      <header className="max-w-2xl space-y-2">
        <h1 className="text-2xl text-[var(--text-primary)]">Review workspaces</h1>
        <p className="text-[var(--text-secondary)]">
          Each workspace holds one systematic review: its protocol, criteria versions and literature corpus.
        </p>
      </header>

      {feedback && (
        <div
          role="status"
          className={`p-4 rounded-xl flex items-center gap-3 text-sm border ${
            feedback.type === "success"
              ? "bg-emerald-950/60 text-emerald-300 border-emerald-800/80"
              : "bg-red-950/60 text-red-300 border-red-800/80"
          }`}
        >
          {feedback.type === "success" ? (
            <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
          ) : (
            <AlertCircle className="w-4 h-4 text-red-400 shrink-0" />
          )}
          <span>{feedback.message}</span>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
        {/* Workspaces list */}
        <section aria-labelledby="ws-list-heading" className="lg:col-span-7 xl:col-span-8 space-y-4">
          <div className="flex items-baseline justify-between">
            <h2 id="ws-list-heading" className="text-xl text-[var(--text-primary)]">
              Your reviews
            </h2>
            <span className="text-sm text-[var(--text-muted)]">
              {isLoading ? "" : `${workspaces.length} ${workspaces.length === 1 ? "workspace" : "workspaces"}`}
            </span>
          </div>

          {isLoading ? (
            <LoadingRegion label="Loading your reviews" className="space-y-3">
              <SkeletonCard />
              <SkeletonCard />
            </LoadingRegion>
          ) : loadError != null ? (
            <ErrorState compact error={loadError} onRetry={() => setReloadKey((k) => k + 1)} what="Your reviews" />
          ) : workspaces.length === 0 ? (
            <div className="glass-panel p-6 text-center space-y-2">
              <p className="font-semibold text-[var(--text-primary)]">No reviews yet</p>
              <p className="text-sm text-[var(--text-muted)]">
                Create your first workspace with the form, or explore the{" "}
                <Link to={`/reviews/${DEMO_WORKSPACE_ID}/records`} className="text-[var(--accent-gold)]">
                  demo review
                </Link>
                .
              </p>
            </div>
          ) : (
          <ul className="space-y-3">
            {workspaces.map((ws) => (
              <li key={ws.id}>
                <Link
                  to={`/reviews/${encodeURIComponent(ws.id)}/${ws.current_revision_id ? "records" : "setup"}`}
                  onClick={() => rememberWorkspaceId(ws.id)}
                  className="group glass-panel flex flex-col sm:flex-row sm:items-center gap-4 p-5 sm:p-6 hover:border-[var(--border-gold)]"
                >
                  <div className="flex-1 min-w-0 space-y-1.5">
                    <h3 className="font-semibold text-[var(--text-primary)] text-base leading-snug">{ws.title}</h3>
                    {ws.description && (
                      <p className="text-sm text-[var(--text-muted)] line-clamp-2">{ws.description}</p>
                    )}
                    <p className="flex flex-wrap items-center gap-x-4 gap-y-1 pt-1 text-xs text-[var(--text-muted)]">
                      <span className="font-mono">{ws.id}</span>
                      <span className="inline-flex items-center gap-1">
                        <Calendar className="w-3 h-3" />
                        Created {new Date(ws.created_at).toLocaleDateString()}
                      </span>
                      <span>{ws.current_revision_id ? "Screening in progress" : "Setup not finished"}</span>
                    </p>
                  </div>
                  <span className="inline-flex items-center gap-1.5 text-sm font-medium text-[var(--accent-gold)] shrink-0">
                    {ws.current_revision_id ? "Open workbench" : "Continue setup"}
                    <ArrowRight className="w-4 h-4 transition-transform group-hover:translate-x-0.5" />
                  </span>
                </Link>
              </li>
            ))}
          </ul>
          )}
        </section>

        {/* Create form */}
        <aside className="lg:col-span-5 xl:col-span-4 lg:sticky lg:top-24">
          <div className="glass-panel-luxury p-6 space-y-5">
            <div className="flex items-center gap-3">
              <span className="grid place-items-center w-9 h-9 rounded-lg border border-[var(--border-gold)] bg-[var(--gold-glow)]">
                <FolderPlus className="w-4 h-4 text-[var(--accent-gold)]" strokeWidth={1.75} />
              </span>
              <h2 className="text-xl text-[var(--text-primary)]">New workspace</h2>
            </div>
            <form onSubmit={handleCreate} className="space-y-4">
              <div className="space-y-1.5">
                <label htmlFor="ws-title" className="block text-sm font-medium text-[var(--text-secondary)]">
                  Review question
                </label>
                <input
                  id="ws-title"
                  type="text"
                  required
                  placeholder="In adults with T2D, how does metformin affect HbA1c?"
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  className="w-full px-3.5 py-2.5 bg-[var(--bg-base)]/60 border border-[var(--border-silver)] text-[var(--text-primary)] text-sm"
                />
              </div>
              <div className="space-y-1.5">
                <label htmlFor="ws-desc" className="block text-sm font-medium text-[var(--text-secondary)]">
                  Protocol context <span className="font-normal text-[var(--text-muted)]">(optional)</span>
                </label>
                <textarea
                  id="ws-desc"
                  rows={3}
                  placeholder="Population, comparators and planned synthesis"
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  className="w-full px-3.5 py-2.5 bg-[var(--bg-base)]/60 border border-[var(--border-silver)] text-[var(--text-primary)] text-sm resize-y"
                />
              </div>
              <button
                type="submit"
                disabled={isSubmitting || !title.trim()}
                className="btn-gold w-full disabled:opacity-50 disabled:filter-none"
              >
                {isSubmitting ? <Loader2 className="w-4 h-4 animate-spin" /> : <Plus className="w-4 h-4" />}
                Create workspace
              </button>
            </form>
          </div>
        </aside>
      </div>
    </div>
  );
};
