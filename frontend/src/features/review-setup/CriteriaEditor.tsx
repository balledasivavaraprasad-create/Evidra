import React, { useEffect, useRef, useState } from "react";
import { AlertCircle, Plus, Save, ShieldCheck, Sliders, Sparkles, Trash2, X } from "lucide-react";
import { api, type CriteriaVersionResponse, type CriterionDefinition } from "../../api/client";
import {
  addCustomRule,
  addKeywords,
  isAiKeyword,
  picoIsReady,
  removeKeyword,
  removeRule,
  usesKeywords,
  validateRules,
  type KeywordKind,
  type PicoFields,
} from "./ruleEditing";

interface CriteriaEditorProps {
  workspaceId: string;
  /** Starting question for a review with nothing saved (its title) */
  defaultQuestion?: string;
  onCriteriaSaved?: (criteriaVersion: CriteriaVersionResponse) => void;
  savedCriteria?: CriteriaVersionResponse | null;
}

const AUTO_GENERATE_DELAY_MS = 1200;

const KeywordChips: React.FC<{
  rule: CriterionDefinition;
  kind: KeywordKind;
  label: string;
  onAdd: (text: string) => void;
  onRemove: (keyword: string) => void;
}> = ({ rule, kind, label, onAdd, onRemove }) => {
  const [draft, setDraft] = useState("");
  const words = rule[kind] ?? [];
  const commit = () => {
    if (draft.trim()) onAdd(draft);
    setDraft("");
  };
  return (
    <div className="mt-2">
      <span className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">{label}</span>
      <div className="mt-1 flex flex-wrap items-center gap-1.5">
        {words.map((word) => {
          const ai = kind === "keywords" && isAiKeyword(rule, word);
          return (
            <span
              key={word}
              className={`inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[11px] ${
                kind === "exclude_keywords"
                  ? "border-amber-800/50 bg-amber-950/40 text-amber-200"
                  : ai
                    ? "border-violet-700/60 bg-violet-950/40 text-violet-200"
                    : "border-slate-700 bg-slate-800/70 text-slate-200"
              }`}
              title={ai ? "Suggested by AI. Remove it if it doesn't fit." : undefined}
            >
              {ai && <Sparkles className="h-3 w-3" aria-hidden="true" />}
              {ai && <span className="sr-only">AI suggested: </span>}
              {word}
              <button
                type="button"
                onClick={() => onRemove(word)}
                aria-label={`Remove ${word} from ${rule.name}`}
                className="rounded-full p-0.5 hover:bg-slate-700"
              >
                <X className="h-3 w-3" />
              </button>
            </span>
          );
        })}
        <input
          type="text"
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" || e.key === ",") {
              e.preventDefault();
              commit();
            }
          }}
          onBlur={commit}
          aria-label={`${kind === "keywords" ? "Add keyword" : "Add excluded word"} to ${rule.name}`}
          placeholder={kind === "keywords" ? "Add keyword" : "Add excluded word"}
          className="w-32 rounded border border-slate-800 bg-slate-950/70 px-2 py-0.5 text-[11px] text-white focus:border-indigo-500 focus:outline-none"
        />
      </div>
    </div>
  );
};

export const CriteriaEditor: React.FC<CriteriaEditorProps> = ({
  workspaceId,
  onCriteriaSaved,
  savedCriteria = null,
  defaultQuestion,
}) => {
  const [question, setQuestion] = useState(savedCriteria?.question || defaultQuestion || "");
  const [pico, setPico] = useState<PicoFields>((savedCriteria?.pico_description as PicoFields) || {});
  const [rules, setRules] = useState<CriterionDefinition[]>(savedCriteria?.criteria ?? []);

  const [generating, setGenerating] = useState(false);
  const [aiUsed, setAiUsed] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);
  // Rules follow the PICO automatically until the reviewer edits them by hand
  const [autoMode, setAutoMode] = useState(!savedCriteria);
  const [edited, setEdited] = useState(false);
  const [confirmReplace, setConfirmReplace] = useState(false);
  const latestRequest = useRef(0);

  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [currentVersion, setCurrentVersion] = useState<CriteriaVersionResponse | null>(savedCriteria);

  const [showAdd, setShowAdd] = useState(false);
  const [newName, setNewName] = useState("");
  const [newInclusion, setNewInclusion] = useState(true);
  const [newKeywords, setNewKeywords] = useState("");

  const changeRules = (next: CriterionDefinition[]) => {
    setRules(next);
    setEdited(true);
    setAutoMode(false);
    setConfirmReplace(false);
    setError(null);
  };

  const generate = async () => {
    const request = ++latestRequest.current;
    setGenerating(true);
    setError(null);
    try {
      const resp = await api.criteria.suggest(workspaceId, {
        question: question.trim(),
        pico: {
          population: pico.population ?? "",
          intervention: pico.intervention ?? "",
          comparator: pico.comparator ?? "",
          outcome: pico.outcome ?? "",
        },
      });
      if (request !== latestRequest.current) return; // a newer request replaced this one
      setRules(resp.criteria);
      setAiUsed(resp.ai_synonyms_used);
      setNotice(resp.notice ?? null);
      setEdited(false);
      setConfirmReplace(false);
    } catch (err: unknown) {
      if (request === latestRequest.current) {
        setError(err instanceof Error ? err.message : "Couldn't generate rules from your question.");
      }
    } finally {
      if (request === latestRequest.current) setGenerating(false);
    }
  };

  const handleGenerateClick = () => {
    if (edited && rules.length > 0 && !confirmReplace) {
      setConfirmReplace(true);
      return;
    }
    void generate();
  };

  // Build the rules by themselves once the PICO is filled in, and keep them in step while untouched
  useEffect(() => {
    if (!autoMode || !picoIsReady(pico)) return;
    const timer = window.setTimeout(() => void generate(), AUTO_GENERATE_DELAY_MS);
    return () => window.clearTimeout(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [autoMode, pico.population, pico.intervention, pico.comparator, pico.outcome]);

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!question.trim()) {
      setError("Review question is required.");
      return;
    }
    const problem = validateRules(rules);
    if (problem) {
      setError(problem);
      return;
    }

    setSaving(true);
    setError(null);

    try {
      const resp = await api.criteria.create(workspaceId, {
        question: question.trim(),
        pico_description: pico as Record<string, string>,
        criteria: rules,
      });
      setCurrentVersion(resp);
      setEdited(false);
      onCriteriaSaved?.(resp);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to save review criteria version");
    } finally {
      setSaving(false);
    }
  };

  const picoInput = (key: keyof PicoFields, label: string, placeholder: string) => (
    <div>
      <label htmlFor={`pico-${key}`} className="block text-xs font-medium text-slate-400 mb-1">
        {label}
      </label>
      <input
        id={`pico-${key}`}
        type="text"
        className="w-full px-2.5 py-1.5 bg-slate-950/70 border border-slate-800 rounded text-xs text-white"
        value={pico[key] || ""}
        placeholder={placeholder}
        onChange={(e) => setPico({ ...pico, [key]: e.target.value })}
      />
    </div>
  );

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
        Screening rules are built from your question and PICO. Edit the keywords or add rules, then save. Saving makes a
        new criteria version; earlier versions are kept.
      </p>

      {error && (
        <div role="alert" className="mb-4 p-3 bg-red-950/40 border border-red-800/60 rounded-lg text-sm text-red-300 flex items-center gap-2">
          <AlertCircle className="w-4 h-4 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      <form onSubmit={handleSave}>
        <div className="mb-4">
          <label htmlFor="review-question" className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1">
            Primary Review Question
          </label>
          <input
            id="review-question"
            type="text"
            className="w-full px-3 py-2 bg-slate-950/70 border border-slate-700 rounded-lg text-sm text-white focus:outline-none focus:border-indigo-500"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            placeholder="e.g. In adults with hypertension, does an ACE inhibitor reduce stroke compared with placebo?"
          />
        </div>

        {/* PICO Grid */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-3 mb-5">
          {picoInput("population", "Population (P)", "e.g. Adults with hypertension")}
          {picoInput("intervention", "Intervention (I)", "e.g. ACE inhibitor, ramipril, lisinopril")}
          {picoInput("comparator", "Comparator (C)", "e.g. Placebo")}
          {picoInput("outcome", "Outcome (O)", "e.g. Stroke")}
        </div>

        {/* Screening rules */}
        <div className="mb-5">
          <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
            <h3 className="block text-xs font-semibold text-slate-300 uppercase tracking-wider">
              Active Screening Rules ({rules.length} active)
            </h3>
            <button
              type="button"
              onClick={handleGenerateClick}
              disabled={generating || !picoIsReady(pico)}
              className="flex items-center gap-1.5 px-3 py-1.5 bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-100 rounded-lg text-xs font-medium transition disabled:opacity-50"
            >
              <Sparkles className="w-3.5 h-3.5 text-amber-300" />
              <span>
                {generating
                  ? "Generating rules..."
                  : confirmReplace
                    ? "Click again to replace your edits"
                    : "Generate rules from my question"}
              </span>
            </button>
          </div>
          {!picoIsReady(pico) && (
            <p className="mb-2 text-xs text-slate-500">Fill in at least the population and the intervention to generate rules.</p>
          )}
          {aiUsed && (
            <p className="mb-2 text-xs text-violet-300">
              AI added some synonyms (marked with a sparkle). Check them before you save; remove any that don't fit.
            </p>
          )}
          {notice && <p className="mb-2 text-xs text-amber-300">{notice}</p>}

          {rules.length === 0 ? (
            <p className="rounded-lg border border-dashed border-slate-700 p-4 text-xs text-slate-400">
              No screening rules yet. Fill in your PICO and they are built for you, or add your own below.
            </p>
          ) : (
            <ul className="space-y-2">
              {rules.map((rule) => (
                <li key={rule.id} className="rounded-lg border border-indigo-500/30 bg-slate-800/50 p-3">
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0">
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="text-xs font-medium text-white">{rule.name}</span>
                        <span
                          className={`text-[10px] px-1.5 py-0.5 rounded ${
                            rule.is_inclusion
                              ? "bg-emerald-950 text-emerald-300 border border-emerald-800/40"
                              : "bg-amber-950 text-amber-300 border border-amber-800/40"
                          }`}
                        >
                          {rule.is_inclusion ? "Inclusion" : "Exclusion"}
                        </span>
                        <span className="text-[10px] px-1.5 py-0.5 bg-slate-800 text-slate-400 rounded">{rule.category}</span>
                        {!usesKeywords(rule) && (
                          <span className="text-[10px] px-1.5 py-0.5 bg-slate-800 text-slate-400 rounded">Built-in check</span>
                        )}
                      </div>
                      <p className="mt-0.5 text-xs text-slate-400">{rule.rationale}</p>
                    </div>
                    <button
                      type="button"
                      onClick={() => changeRules(removeRule(rules, rule.id))}
                      aria-label={`Remove rule ${rule.name}`}
                      className="shrink-0 rounded p-1 text-slate-500 hover:text-red-400"
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </button>
                  </div>
                  {usesKeywords(rule) && (
                    <>
                      <KeywordChips
                        rule={rule}
                        kind="keywords"
                        label={rule.is_inclusion ? "Looks for any of" : "Excludes if it mentions any of"}
                        onAdd={(text) => changeRules(addKeywords(rules, rule.id, "keywords", text))}
                        onRemove={(word) => changeRules(removeKeyword(rules, rule.id, "keywords", word))}
                      />
                      <KeywordChips
                        rule={rule}
                        kind="exclude_keywords"
                        label="Fails the rule if it mentions"
                        onAdd={(text) => changeRules(addKeywords(rules, rule.id, "exclude_keywords", text))}
                        onRemove={(word) => changeRules(removeKeyword(rules, rule.id, "exclude_keywords", word))}
                      />
                    </>
                  )}
                </li>
              ))}
            </ul>
          )}

          {showAdd ? (
            <div className="mt-3 rounded-lg border border-slate-700 bg-slate-950/50 p-3 space-y-2">
              <div className="grid grid-cols-1 gap-2 md:grid-cols-[1fr_9rem]">
                <input
                  type="text"
                  value={newName}
                  onChange={(e) => setNewName(e.target.value)}
                  aria-label="New rule name"
                  placeholder="Rule name, e.g. Adults only"
                  className="rounded border border-slate-800 bg-slate-900 px-2.5 py-1.5 text-xs text-white"
                />
                <select
                  value={newInclusion ? "include" : "exclude"}
                  onChange={(e) => setNewInclusion(e.target.value === "include")}
                  aria-label="New rule type"
                  className="rounded border border-slate-800 bg-slate-900 px-2 py-1.5 text-xs text-slate-200"
                >
                  <option value="include">Inclusion</option>
                  <option value="exclude">Exclusion</option>
                </select>
              </div>
              <input
                type="text"
                value={newKeywords}
                onChange={(e) => setNewKeywords(e.target.value)}
                aria-label="New rule keywords"
                placeholder="Keywords, separated by commas"
                className="w-full rounded border border-slate-800 bg-slate-900 px-2.5 py-1.5 text-xs text-white"
              />
              <div className="flex gap-2">
                <button
                  type="button"
                  disabled={!newName.trim() || !newKeywords.trim()}
                  onClick={() => {
                    changeRules(addCustomRule(rules, newName, newInclusion, newKeywords));
                    setNewName("");
                    setNewKeywords("");
                    setShowAdd(false);
                  }}
                  className="rounded bg-indigo-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-indigo-500 disabled:opacity-50"
                >
                  Add rule
                </button>
                <button type="button" onClick={() => setShowAdd(false)} className="rounded px-3 py-1.5 text-xs text-slate-300 hover:text-white">
                  Cancel
                </button>
              </div>
            </div>
          ) : (
            <button
              type="button"
              onClick={() => setShowAdd(true)}
              className="mt-3 flex items-center gap-1 text-[11px] font-medium text-indigo-400 hover:text-indigo-300"
            >
              <Plus className="h-3 w-3" />
              <span>Add your own rule</span>
            </button>
          )}
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
