import React, { useState } from "react";
import { Link } from "react-router-dom";
import { Plus, FolderPlus, ArrowRight, Layers, Calendar, CheckCircle2, AlertCircle, Loader2 } from "lucide-react";
import { api, type WorkspaceResponse } from "../../api/client";

export const WorkspacesPage: React.FC = () => {
  const [workspaces, setWorkspaces] = useState<WorkspaceResponse[]>([
    {
      id: "ws-demo-01",
      title: "Type 2 Diabetes: Metformin vs Placebo Review",
      description: "Evaluation of HbA1c reduction from metformin monotherapy in adult type 2 diabetes patients.",
      created_by: "reviewer_local",
      created_at: new Date().toISOString(),
      current_revision_id: "rev-001",
      row_version: 1,
    },
  ]);

  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [feedback, setFeedback] = useState<{ type: "success" | "error"; message: string } | null>(null);

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
      setTitle("");
      setDescription("");
      setFeedback({ type: "success", message: `Workspace '${newWs.title}' created successfully on SQLite database!` });
    } catch (err: any) {
      setFeedback({
        type: "error",
        message: err.message || "Failed to create workspace via backend API.",
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="space-y-8 pb-12">
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 border-b border-slate-800 pb-6">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight">Review Workspaces</h1>
          <p className="text-slate-400 text-sm">
            Manage your systematic reviews, protocol criteria, and literature corpuses.
          </p>
        </div>
      </div>

      {feedback && (
        <div
          className={`p-4 rounded-xl flex items-center gap-3 text-xs font-mono border ${
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

      {/* Create Workspace Form */}
      <div className="glass-panel p-6 border-slate-800">
        <h2 className="text-base font-semibold text-white mb-4 flex items-center gap-2">
          <FolderPlus className="w-4 h-4 text-cyan-400" />
          <span>Create New Review Workspace</span>
        </h2>
        <form onSubmit={handleCreate} className="space-y-4 max-w-2xl">
          <div>
            <label htmlFor="ws-title" className="block text-xs font-medium text-slate-300 mb-1">
              Review Title *
            </label>
            <input
              id="ws-title"
              type="text"
              required
              placeholder="e.g. In adults with T2D, how does Metformin affect HbA1c?"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              className="w-full px-3.5 py-2.5 rounded-lg bg-slate-900 border border-slate-700 text-white text-sm focus:border-cyan-500 focus:outline-none"
            />
          </div>
          <div>
            <label htmlFor="ws-desc" className="block text-xs font-medium text-slate-300 mb-1">
              Protocol Context & Scope (Optional)
            </label>
            <textarea
              id="ws-desc"
              rows={2}
              placeholder="Brief context regarding question, population, and planned synthesis..."
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              className="w-full px-3.5 py-2 rounded-lg bg-slate-900 border border-slate-700 text-white text-sm focus:border-cyan-500 focus:outline-none"
            />
          </div>
          <button
            type="submit"
            disabled={isSubmitting || !title.trim()}
            className="inline-flex items-center gap-2 px-5 py-2.5 rounded-lg bg-cyan-600 hover:bg-cyan-500 disabled:opacity-50 text-white font-medium text-xs transition"
          >
            {isSubmitting ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Plus className="w-3.5 h-3.5" />}
            <span>Create Workspace (POST /api/v1/workspaces)</span>
          </button>
        </form>
      </div>

      {/* Workspaces List */}
      <div className="space-y-4">
        <h3 className="text-sm font-semibold text-slate-300 uppercase tracking-wider font-mono">
          Available Workspaces ({workspaces.length})
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {workspaces.map((ws) => (
            <div key={ws.id} className="glass-panel p-5 space-y-4 glass-panel-hover flex flex-col justify-between">
              <div className="space-y-2">
                <div className="flex items-center justify-between gap-2">
                  <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700">
                    {ws.id}
                  </span>
                  <span className="text-[11px] text-slate-500 flex items-center gap-1">
                    <Calendar className="w-3 h-3" />
                    {new Date(ws.created_at).toLocaleDateString()}
                  </span>
                </div>
                <h4 className="font-semibold text-white text-base leading-snug">{ws.title}</h4>
                {ws.description && <p className="text-slate-400 text-xs line-clamp-2">{ws.description}</p>}
              </div>

              <div className="pt-2 border-t border-slate-800/80 flex items-center justify-between">
                <span className="text-[11px] text-cyan-400 font-mono">Revision: {ws.current_revision_id || "Initial"}</span>
                <Link
                  to={`/reviews/${ws.id}/records`}
                  className="inline-flex items-center gap-1.5 text-xs font-semibold text-cyan-400 hover:text-cyan-300 transition"
                >
                  <span>Open Workbench</span>
                  <ArrowRight className="w-3.5 h-3.5" />
                </Link>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
