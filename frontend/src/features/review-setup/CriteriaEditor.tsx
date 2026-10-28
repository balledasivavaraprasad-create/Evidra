import React, { useState } from "react";
import { CheckCircle2, Sliders, ShieldCheck, AlertCircle, Save } from "lucide-react";
import { api, type CriteriaVersionResponse, type CriterionDefinition } from "../../api/client";

export const DEFAULT_FRONTEND_CRITERIA: CriterionDefinition[] = [
  {
    id: "population_adults_t2d",
    name: "Target Population: Adults with Type 2 Diabetes",
    category: "population",
    is_inclusion: true,
    rationale: "Study must evaluate human adult patients diagnosed with type 2 diabetes mellitus.",
    metadata_first: true,
  },
  {
    id: "comparative_clinical_design",
    name: "Study Design: Comparative Clinical Investigation",
    category: "study_design",
    is_inclusion: true,
    rationale: "Study must be an empirical clinical trial, randomized trial, or comparative cohort study.",
    metadata_first: true,
  },
  {
    id: "exclude_animal_only",
    name: "Exclude Animal-Only Preclinical Studies",
    category: "species",
    is_inclusion: false,
    rationale: "Preclinical animal models (rats, mice, rodents) without human clinical evaluation must be excluded.",
    metadata_first: true,
  },
  {
    id: "exclude_simulation_only",
    name: "Exclude Simulation-Only Studies",
    category: "methodology",
    is_inclusion: false,
    rationale: "In silico, computational docking, or purely theoretical modeling without patient data must be excluded.",
    metadata_first: true,
  },
  {
    id: "exclude_case_reports",
    name: "Exclude Single Case Reports",
    category: "study_design",
    is_inclusion: false,
    rationale: "Individual patient case reports lack comparative control groups and must be excluded.",
    metadata_first: true,
  },
  {
    id: "english_language",
    name: "Language: English Reviewable",
    category: "language",
    is_inclusion: true,
    rationale: "Article must be reviewable in English as per protocol capacity constraints.",
    metadata_first: true,
  },
  {
    id: "abstract_available",
    name: "Content: Abstract Text Availability",
    category: "content",
    is_inclusion: true,
    rationale: "Record must have an accessible abstract for title/abstract screening stage.",
    metadata_first: false,
  },
];

interface CriteriaEditorProps {
  workspaceId: string;
  /** Starting question for a new review (defaults to the metformin example) */
  defaultQuestion?: string;
  /** Starting PICO for a new review (defaults to the metformin example) */
  defaultPico?: Record<string, string>;
  onCriteriaSaved?: (criteriaVersion: CriteriaVersionResponse) => void;
  savedCriteria?: CriteriaVersionResponse | null;
}

export const CriteriaEditor: React.FC<CriteriaEditorProps> = ({
  workspaceId,
  onCriteriaSaved,
  savedCriteria = null,
  defaultQuestion,
  defaultPico,
}) => {
  const [question, setQuestion] = useState(
    savedCriteria?.question ||
      defaultQuestion ||
      "In adults with type 2 diabetes, how does metformin, compared with placebo or another glucose-lowering intervention, affect HbA1c?"
  );

  const [pico, setPico] = useState<Record<string, string>>(
    savedCriteria?.pico_description || defaultPico || {
      population: "Adults with type 2 diabetes",
      intervention: "Metformin",
      comparator: "Placebo or another glucose-lowering intervention",
      outcome: "Change in HbA1c",
    }
  );

  const [activeCriteria, setActiveCriteria] = useState<CriterionDefinition[]>(
    savedCriteria?.criteria || DEFAULT_FRONTEND_CRITERIA
  );

  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [currentVersion, setCurrentVersion] = useState<CriteriaVersionResponse | null>(savedCriteria);

  const toggleCriterion = (id: string) => {
    if (activeCriteria.some((c) => c.id === id)) {
      if (activeCriteria.length <= 1) {
        setError("At least one screening criterion must remain active.");
        return;
      }
      setActiveCriteria(activeCriteria.filter((c) => c.id !== id));
    } else {
      const found = DEFAULT_FRONTEND_CRITERIA.find((c) => c.id === id);
      if (found) {
        setActiveCriteria([...activeCriteria, found]);
      }
    }
    setError(null);
  };

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!question.trim()) {
      setError("Review question is required.");
      return;
    }
    if (activeCriteria.length === 0) {
      setError("At least one criterion must be selected.");
      return;
    }

    setSaving(true);
    setError(null);

    try {
      const resp = await api.criteria.create(workspaceId, {
        question: question.trim(),
        pico_description: pico,
        criteria: activeCriteria,
      });
      setCurrentVersion(resp);
      if (onCriteriaSaved) {
        onCriteriaSaved(resp);
      }
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Failed to save review criteria version";
      setError(message);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="card p-6 border border-slate-700/60 bg-slate-900/40 rounded-xl mb-6">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Sliders className="w-5 h-5 text-indigo-400" />
          <h2 className="text-lg font-semibold text-white">Review Question & Screening Protocol</h2>
        </div>
        {currentVersion && (
          <div className="flex items-center gap-2 px-3 py-1 bg-emerald-950/60 border border-emerald-500/40 rounded-full text-xs text-emerald-300">
            <ShieldCheck className="w-3.5 h-3.5" />
            <span>Criteria Seq #{currentVersion.sequence} (Hash: {currentVersion.content_hash.slice(0, 8)})</span>
          </div>
        )}
      </div>

      <p className="text-xs text-slate-400 mb-4">
        Screening criteria are strictly immutable per version. Modifying rules generates a new criteria version sequence
        and triggers cache invalidation.
      </p>

      {error && (
        <div className="mb-4 p-3 bg-red-950/40 border border-red-800/60 rounded-lg text-sm text-red-300 flex items-center gap-2">
          <AlertCircle className="w-4 h-4 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      <form onSubmit={handleSave}>
        <div className="mb-4">
          <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1">
            Primary Review Question
          </label>
          <input
            type="text"
            className="w-full px-3 py-2 bg-slate-950/70 border border-slate-700 rounded-lg text-sm text-white focus:outline-none focus:border-indigo-500"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            placeholder="e.g. In adults with type 2 diabetes, how does metformin affect HbA1c?"
          />
        </div>

        {/* PICO Grid */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-3 mb-5">
          <div>
            <label className="block text-xs font-medium text-slate-400 mb-1">Population (P)</label>
            <input
              type="text"
              className="w-full px-2.5 py-1.5 bg-slate-950/70 border border-slate-800 rounded text-xs text-white"
              value={pico.population || ""}
              placeholder="e.g. Adults with type 2 diabetes"
              onChange={(e) => setPico({ ...pico, population: e.target.value })}
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-400 mb-1">Intervention (I)</label>
            <input
              type="text"
              className="w-full px-2.5 py-1.5 bg-slate-950/70 border border-slate-800 rounded text-xs text-white"
              value={pico.intervention || ""}
              placeholder="e.g. Metformin"
              onChange={(e) => setPico({ ...pico, intervention: e.target.value })}
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-400 mb-1">Comparator (C)</label>
            <input
              type="text"
              className="w-full px-2.5 py-1.5 bg-slate-950/70 border border-slate-800 rounded text-xs text-white"
              value={pico.comparator || ""}
              placeholder="e.g. Placebo"
              onChange={(e) => setPico({ ...pico, comparator: e.target.value })}
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-400 mb-1">Outcome (O)</label>
            <input
              type="text"
              className="w-full px-2.5 py-1.5 bg-slate-950/70 border border-slate-800 rounded text-xs text-white"
              value={pico.outcome || ""}
              placeholder="e.g. Change in HbA1c"
              onChange={(e) => setPico({ ...pico, outcome: e.target.value })}
            />
          </div>
        </div>

        {/* Screening Rules Checklist */}
        <div className="mb-5">
          <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-2">
            Active Screening Rules ({activeCriteria.length} active)
          </label>
          <div className="space-y-2">
            {DEFAULT_FRONTEND_CRITERIA.map((crit) => {
              const isActive = activeCriteria.some((c) => c.id === crit.id);
              return (
                <div
                  key={crit.id}
                  onClick={() => toggleCriterion(crit.id)}
                  className={`flex items-start justify-between p-3 rounded-lg border cursor-pointer transition-colors ${
                    isActive
                      ? "bg-slate-800/60 border-indigo-500/40"
                      : "bg-slate-950/40 border-slate-800/80 opacity-60"
                  }`}
                >
                  <div className="flex items-start gap-2.5">
                    <input
                      type="checkbox"
                      checked={isActive}
                      onChange={() => {}}
                      className="mt-0.5 rounded border-slate-700 text-indigo-600 focus:ring-0"
                    />
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="text-xs font-medium text-white">{crit.name}</span>
                        <span
                          className={`text-[10px] px-1.5 py-0.5 rounded ${
                            crit.is_inclusion
                              ? "bg-emerald-950 text-emerald-300 border border-emerald-800/40"
                              : "bg-amber-950 text-amber-300 border border-amber-800/40"
                          }`}
                        >
                          {crit.is_inclusion ? "Inclusion" : "Exclusion"}
                        </span>
                        <span className="text-[10px] px-1.5 py-0.5 bg-slate-800 text-slate-400 rounded">
                          {crit.category}
                        </span>
                      </div>
                      <p className="text-xs text-slate-400 mt-0.5">{crit.rationale}</p>
                    </div>
                  </div>
                  {isActive && <CheckCircle2 className="w-4 h-4 text-indigo-400 shrink-0 mt-0.5" />}
                </div>
              );
            })}
          </div>
        </div>

        <div className="flex justify-end">
          <button
            type="submit"
            disabled={saving}
            className="flex items-center gap-1.5 px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-xs font-medium transition disabled:opacity-50"
          >
            <Save className="w-3.5 h-3.5" />
            <span>{saving ? "Saving Criteria..." : "Save Criteria Version"}</span>
          </button>
        </div>
      </form>
    </div>
  );
};
