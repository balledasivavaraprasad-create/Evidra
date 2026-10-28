import React, { useRef, useState } from "react";
import { Search, Plus, Trash2, Calendar, Database, Play, AlertCircle, FileCode, CheckSquare } from "lucide-react";
import {
  api,
  type BooleanOperator,
  type QueryASTNodeInput,
  type QueryVersionResponse,
  type SearchExecutionResponse,
  type SourceNamespace,
} from "../../api/client";
import {
  astToGroups,
  astToReadableString,
  compileClauseToAST,
  isValidDateFormat,
  type QueryGroupClause,
} from "./astCompiler";
import { executionLabel, selectedIds, sortExecutions, upsertExecution, withSelection } from "./executions";

/** Shown while there is no saved review question to attach the query to. */
export const SAVE_QUESTION_HINT = "Save the review question first.";

const SEARCHABLE_SOURCES: SourceNamespace[] = ["pubmed", "europepmc"];

interface QueryBuilderProps {
  workspaceId: string;
  /** The saved review question this query belongs to. Saving and searching stay off until it exists. */
  criteriaVersionId?: string | null;
  /** The latest saved search; the builder starts from it and treats it as the active query. */
  savedQuery?: QueryVersionResponse | null;
  /** The saved counts of that search; ticked ones are those with selected_for_import. */
  savedExecutions?: SearchExecutionResponse[];
  onQuerySaved?: (query: QueryVersionResponse) => void;
  /** Called with the ticked execution ids whenever counts are added, ticked, unticked or reset. */
  onExecutionSelected?: (selectedIds: string[]) => void;
  /** Starting terms for a review with no saved query, one inner list per OR-group (from the PICO). */
  initialTerms?: string[][];
}

function starterGroups(terms: string[][] | undefined): QueryGroupClause[] {
  const source = terms && terms.length > 0 ? terms : [[""]];
  return source.map((group, gi) => ({
    id: `grp-${gi + 1}`,
    operator: "OR" as BooleanOperator,
    clauses: (group.length ? group : [""]).map((term, ci) => ({ id: `c-${gi + 1}-${ci + 1}`, field: "all" as const, term })),
  }));
}

/** Rebuild the editor from the saved search; tooNested means its AST has no group form to show. */
function startingPoint(savedQuery: QueryVersionResponse | null | undefined, initialTerms: string[][] | undefined) {
  const parsed = savedQuery ? astToGroups(savedQuery.ast as QueryASTNodeInput) : null;
  if (parsed) {
    return {
      rootOperator: parsed.rootOperator,
      groups: parsed.groups.length > 0 ? parsed.groups : starterGroups(undefined),
      tooNested: false,
    };
  }
  return { rootOperator: "AND" as BooleanOperator, groups: starterGroups(initialTerms), tooNested: !!savedQuery };
}

function messageOf(err: unknown, fallback: string): string {
  return err instanceof Error ? err.message : fallback;
}

export const QueryBuilder: React.FC<QueryBuilderProps> = ({
  workspaceId,
  criteriaVersionId,
  savedQuery,
  savedExecutions,
  onQuerySaved,
  onExecutionSelected,
  initialTerms,
}) => {
  const [start] = useState(() => startingPoint(savedQuery, initialTerms));
  const [rootOperator, setRootOperator] = useState<BooleanOperator>(start.rootOperator);
  const [groups, setGroups] = useState<QueryGroupClause[]>(start.groups);

  const [startDate, setStartDate] = useState(savedQuery ? (savedQuery.start_date ?? "") : "2020");
  const [endDate, setEndDate] = useState(savedQuery ? (savedQuery.end_date ?? "") : "2026");
  const [selectedSources, setSelectedSources] = useState<SourceNamespace[]>(() => {
    const saved = (savedQuery?.sources ?? []).filter((s) => SEARCHABLE_SOURCES.includes(s));
    return saved.length > 0 ? saved : SEARCHABLE_SOURCES;
  });

  const [savingQuery, setSavingQuery] = useState(false);
  const [activeQuery, setActiveQuery] = useState<QueryVersionResponse | null>(savedQuery ?? null);
  const [error, setError] = useState<string | null>(null);

  // Search executions: the list is the single source of truth, ticks live on its rows
  const [executingSource, setExecutingSource] = useState<string | null>(null);
  const [executions, setExecutions] = useState<SearchExecutionResponse[]>(() => sortExecutions(savedExecutions ?? []));
  const executionsRef = useRef(executions);
  const [countErrors, setCountErrors] = useState<Partial<Record<SourceNamespace, string>>>({});
  const [pendingTicks, setPendingTicks] = useState<ReadonlySet<string>>(new Set());
  const [tickErrors, setTickErrors] = useState<Record<string, string>>({});

  const commitExecutions = (next: SearchExecutionResponse[]) => {
    executionsRef.current = next;
    setExecutions(next);
    onExecutionSelected?.(selectedIds(next));
  };

  const compiledAST = compileClauseToAST(groups, rootOperator);
  const readableQueryString = astToReadableString(compiledAST);

  const addGroup = () => {
    setGroups([
      ...groups,
      {
        id: `grp-${Date.now()}`,
        operator: "OR",
        clauses: [{ id: `c-${Date.now()}`, field: "all", term: "" }],
      },
    ]);
  };

  const removeGroup = (groupId: string) => {
    if (groups.length <= 1) return;
    setGroups(groups.filter((g) => g.id !== groupId));
  };

  const addClause = (groupId: string) => {
    setGroups(
      groups.map((g) => {
        if (g.id !== groupId) return g;
        return {
          ...g,
          clauses: [...g.clauses, { id: `c-${Date.now()}`, field: "all", term: "" }],
        };
      })
    );
  };

  const updateClauseTerm = (groupId: string, clauseId: string, newTerm: string) => {
    setGroups(
      groups.map((g) => {
        if (g.id !== groupId) return g;
        return {
          ...g,
          clauses: g.clauses.map((c) => (c.id === clauseId ? { ...c, term: newTerm } : c)),
        };
      })
    );
  };

  const removeClause = (groupId: string, clauseId: string) => {
    setGroups(
      groups.map((g) => {
        if (g.id !== groupId) return g;
        if (g.clauses.length <= 1) return g;
        return {
          ...g,
          clauses: g.clauses.filter((c) => c.id !== clauseId),
        };
      })
    );
  };

  const toggleSource = (source: SourceNamespace) => {
    if (selectedSources.includes(source)) {
      if (selectedSources.length <= 1) {
        setError("At least one search source database must be selected.");
        return;
      }
      setSelectedSources(selectedSources.filter((s) => s !== source));
    } else {
      setSelectedSources([...selectedSources, source]);
    }
    setError(null);
  };

  const criteriaReady = !!criteriaVersionId;

  const handleSaveQuery = async () => {
    if (!criteriaVersionId) {
      setError(SAVE_QUESTION_HINT);
      return;
    }
    if (!isValidDateFormat(startDate) || !isValidDateFormat(endDate)) {
      setError("Dates must follow YYYY, YYYY-MM, or YYYY-MM-DD format.");
      return;
    }

    setSavingQuery(true);
    setError(null);

    try {
      const qResp = await api.queries.create(workspaceId, {
        ast: compiledAST,
        start_date: startDate.trim() || null,
        end_date: endDate.trim() || null,
        sources: selectedSources,
        criteria_version_id: criteriaVersionId,
        parent_id: activeQuery?.id || null,
      });
      // Counts belong to one saved version; a new version starts with none, as it does after a reload
      if (qResp.id !== activeQuery?.id) {
        commitExecutions([]);
        setCountErrors({});
        setTickErrors({});
      }
      setActiveQuery(qResp);
      onQuerySaved?.(qResp);
    } catch (err: unknown) {
      setError(messageOf(err, "Failed to persist structured query version"));
    } finally {
      setSavingQuery(false);
    }
  };

  const handleRunSearchCount = async (source: SourceNamespace) => {
    if (!criteriaReady) {
      setError(SAVE_QUESTION_HINT);
      return;
    }
    if (!activeQuery) {
      setCountErrors((prev) => ({ ...prev, [source]: "Save the query version before counting." }));
      return;
    }

    setExecutingSource(source);
    setCountErrors((prev) => ({ ...prev, [source]: undefined }));

    try {
      const execResp = await api.queries.executeSearch(activeQuery.id, {
        source,
        synonym_expansion: false,
      });
      // The same saved query counted again returns its recorded row: replace it, never add a second
      commitExecutions(upsertExecution(executionsRef.current, execResp));
    } catch (err: unknown) {
      setCountErrors((prev) => ({ ...prev, [source]: messageOf(err, `Failed to execute search count on ${source}`) }));
    } finally {
      setExecutingSource(null);
    }
  };

  const toggleExecutionSelection = async (id: string) => {
    const row = executionsRef.current.find((e) => e.id === id);
    if (!row || pendingTicks.has(id)) return;
    const next = !row.selected_for_import;

    setPendingTicks((prev) => new Set(prev).add(id));
    setTickErrors((prev) => ({ ...prev, [id]: "" }));
    commitExecutions(withSelection(executionsRef.current, id, next)); // optimistic
    try {
      const saved = await api.queries.setExecutionSelected(id, next);
      commitExecutions(upsertExecution(executionsRef.current, saved));
    } catch (err: unknown) {
      commitExecutions(withSelection(executionsRef.current, id, !next)); // roll back this row only
      setTickErrors((prev) => ({ ...prev, [id]: messageOf(err, "Couldn't save this choice. Try again.") }));
    } finally {
      setPendingTicks((prev) => {
        const rest = new Set(prev);
        rest.delete(id);
        return rest;
      });
    }
  };

  const tickedCount = selectedIds(executions).length;

  return (
    <div className="card p-6 border border-slate-700/60 bg-slate-900/40 rounded-xl mb-6">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Search className="w-5 h-5 text-indigo-400" />
          <h2 className="text-lg font-semibold text-white">Structured Boolean Query Builder</h2>
        </div>
        {activeQuery && (
          <div className="flex items-center gap-2 px-3 py-1 bg-indigo-950/60 border border-indigo-500/40 rounded-full text-xs text-indigo-300">
            <FileCode className="w-3.5 h-3.5" />
            <span>Query Seq #{activeQuery.sequence} ({activeQuery.id.slice(0, 8)})</span>
          </div>
        )}
      </div>

      {error && (
        <div className="mb-4 p-3 bg-red-950/40 border border-red-800/60 rounded-lg text-sm text-red-300 flex items-center gap-2">
          <AlertCircle className="w-4 h-4 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {start.tooNested && (
        <div role="status" className="mb-4 p-3 bg-amber-950/40 border border-amber-800/60 rounded-lg text-sm text-amber-200 flex items-start gap-2">
          <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
          <span>
            The saved search is nested more deeply than this editor can show, so the groups below are a fresh start from
            your PICO terms. Counting still uses the saved search ({astToReadableString(savedQuery?.ast as QueryASTNodeInput)}).
          </span>
        </div>
      )}

      {/* Query Groups Editor */}
      <div className="space-y-4 mb-5">
        <div className="flex items-center gap-3">
          <span className="text-xs font-semibold text-slate-300 uppercase tracking-wider">
            Inter-Group Operator:
          </span>
          <select
            value={rootOperator}
            onChange={(e) => setRootOperator(e.target.value as BooleanOperator)}
            className="px-2.5 py-1 bg-slate-950 border border-slate-700 rounded text-xs text-indigo-300 font-semibold"
          >
            <option value="AND">AND (Intersection)</option>
            <option value="OR">OR (Union)</option>
            <option value="NOT">NOT (Exclusion)</option>
          </select>
        </div>

        {groups.map((group, grpIdx) => (
          <div
            key={group.id}
            className="p-4 bg-slate-950/60 border border-slate-800 rounded-lg relative"
          >
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-2">
                <span className="text-xs text-slate-400 font-medium">Group {grpIdx + 1}</span>
                <select
                  value={group.operator}
                  onChange={(e) =>
                    setGroups(
                      groups.map((g) =>
                        g.id === group.id ? { ...g, operator: e.target.value as BooleanOperator } : g
                      )
                    )
                  }
                  className="px-2 py-0.5 bg-slate-900 border border-slate-700 rounded text-[11px] text-slate-300"
                >
                  <option value="OR">OR (Synonyms)</option>
                  <option value="AND">AND (Co-occurrence)</option>
                  <option value="NOT">NOT</option>
                </select>
              </div>
              {groups.length > 1 && (
                <button
                  type="button"
                  onClick={() => removeGroup(group.id)}
                  className="text-slate-500 hover:text-red-400 p-1 transition"
                  title="Remove group"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                </button>
              )}
            </div>

            <div className="space-y-2">
              {group.clauses.map((clause) => (
                <div key={clause.id} className="flex items-center gap-2">
                  <input
                    type="text"
                    value={clause.term}
                    onChange={(e) => updateClauseTerm(group.id, clause.id, e.target.value)}
                    placeholder="Search term or phrase..."
                    className="flex-1 px-3 py-1.5 bg-slate-900 border border-slate-800 rounded text-xs text-white focus:outline-none focus:border-indigo-500"
                  />
                  {group.clauses.length > 1 && (
                    <button
                      type="button"
                      onClick={() => removeClause(group.id, clause.id)}
                      className="text-slate-600 hover:text-red-400 p-1"
                    >
                      <Trash2 className="w-3 h-3" />
                    </button>
                  )}
                </div>
              ))}
            </div>

            <button
              type="button"
              onClick={() => addClause(group.id)}
              className="mt-2.5 flex items-center gap-1 text-[11px] text-indigo-400 hover:text-indigo-300 font-medium"
            >
              <Plus className="w-3 h-3" />
              <span>Add Term</span>
            </button>
          </div>
        ))}

        <button
          type="button"
          onClick={addGroup}
          className="flex items-center gap-1.5 px-3 py-1.5 bg-slate-800/80 hover:bg-slate-700 border border-slate-700 rounded text-xs text-slate-200 transition"
        >
          <Plus className="w-3.5 h-3.5" />
          <span>Add Query Group</span>
        </button>
      </div>

      {/* Date & Source Controls */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 p-4 bg-slate-950/40 border border-slate-800 rounded-lg mb-5">
        <div>
          <label className="flex items-center gap-1.5 text-xs font-medium text-slate-300 mb-2">
            <Calendar className="w-3.5 h-3.5 text-indigo-400" />
            <span>Publication Date Bounds (YYYY or YYYY-MM-DD)</span>
          </label>
          <div className="flex items-center gap-2">
            <input
              type="text"
              value={startDate}
              onChange={(e) => setStartDate(e.target.value)}
              placeholder="From YYYY"
              className="w-full px-2.5 py-1.5 bg-slate-900 border border-slate-700 rounded text-xs text-white"
            />
            <span className="text-slate-500 text-xs">to</span>
            <input
              type="text"
              value={endDate}
              onChange={(e) => setEndDate(e.target.value)}
              placeholder="To YYYY"
              className="w-full px-2.5 py-1.5 bg-slate-900 border border-slate-700 rounded text-xs text-white"
            />
          </div>
        </div>

        <div>
          <label className="flex items-center gap-1.5 text-xs font-medium text-slate-300 mb-2">
            <Database className="w-3.5 h-3.5 text-indigo-400" />
            <span>Target Databases</span>
          </label>
          <div className="flex items-center gap-4 mt-1">
            <label className="flex items-center gap-2 text-xs text-slate-200 cursor-pointer">
              <input
                type="checkbox"
                checked={selectedSources.includes("pubmed")}
                onChange={() => toggleSource("pubmed")}
                className="rounded border-slate-700 text-indigo-600 focus:ring-0"
              />
              <span>PubMed / MEDLINE</span>
            </label>
            <label className="flex items-center gap-2 text-xs text-slate-200 cursor-pointer">
              <input
                type="checkbox"
                checked={selectedSources.includes("europepmc")}
                onChange={() => toggleSource("europepmc")}
                className="rounded border-slate-700 text-indigo-600 focus:ring-0"
              />
              <span>Europe PMC</span>
            </label>
          </div>
        </div>
      </div>

      {/* Query Preview */}
      <div className="p-3 bg-slate-950 border border-slate-800 rounded-lg mb-5">
        <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block mb-1">
          Compiled AST Query Expression Preview
        </span>
        <code className="text-xs text-indigo-300 break-all">
          {readableQueryString || "* (match all records)"}
        </code>
      </div>

      {/* Save & Run Action Bar */}
      <div className="flex flex-wrap items-center justify-between gap-3 mb-6">
        <button
          type="button"
          onClick={handleSaveQuery}
          disabled={savingQuery || !criteriaReady}
          aria-describedby={criteriaReady ? undefined : "query-criteria-hint"}
          className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-xs font-medium transition disabled:opacity-50"
        >
          {savingQuery ? "Saving Query Version..." : "Save Query Version"}
        </button>

        <div className="flex items-start gap-2">
          {selectedSources.map((src) => (
            <div key={src} className="flex flex-col items-end gap-1">
              <button
                type="button"
                disabled={!criteriaReady || !activeQuery || executingSource === src}
                aria-describedby={
                  countErrors[src] ? `count-error-${src}` : criteriaReady ? undefined : "query-criteria-hint"
                }
                onClick={() => handleRunSearchCount(src)}
                className="flex items-center gap-1.5 px-3 py-2 bg-slate-800 hover:bg-slate-700 border border-slate-700 text-white rounded-lg text-xs font-medium transition disabled:opacity-40"
              >
                <Play className="w-3 h-3 text-emerald-400" />
                <span>{executingSource === src ? `Counting ${src}...` : `Count on ${src}`}</span>
              </button>
              {countErrors[src] && (
                <p id={`count-error-${src}`} role="alert" className="max-w-[16rem] text-right text-[11px] text-red-300">
                  {countErrors[src]}
                </p>
              )}
            </div>
          ))}
        </div>
      </div>
      {!criteriaReady && (
        <p id="query-criteria-hint" className="-mt-3 mb-6 text-xs text-amber-300">
          {SAVE_QUESTION_HINT}
        </p>
      )}

      {/* Search Executions Table */}
      {executions.length > 0 && (
        <div className="mt-6 border-t border-slate-800 pt-5">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-sm font-semibold text-white">Search Executions Comparison</h3>
            <span className="text-xs text-slate-400">
              {tickedCount} of {executions.length} selected for import
            </span>
          </div>

          <div className="space-y-2.5">
            {executions.map((exec) => {
              const isSelected = exec.selected_for_import;
              const pending = pendingTicks.has(exec.id);
              return (
                <div key={exec.id}>
                  <label
                    className={`p-3 rounded-lg border flex items-center justify-between cursor-pointer transition ${
                      isSelected
                        ? "bg-slate-800/80 border-indigo-500/50"
                        : "bg-slate-950/40 border-slate-800 opacity-60"
                    }`}
                  >
                    <div className="flex items-center gap-3">
                      <input
                        type="checkbox"
                        checked={isSelected}
                        disabled={pending}
                        onChange={() => toggleExecutionSelection(exec.id)}
                        aria-label={`Import ${executionLabel(exec)}`}
                        className="rounded border-slate-700 text-indigo-600 focus:ring-0"
                      />
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="text-xs font-bold text-white uppercase">{exec.source}</span>
                          <span className="text-[11px] text-slate-400">
                            {new Date(exec.counted_at).toLocaleTimeString()}
                          </span>
                          {exec.partial && (
                            <span className="text-[10px] px-1.5 py-0.2 bg-amber-950 text-amber-300 rounded">
                              Truncated / Capped
                            </span>
                          )}
                        </div>
                        <p className="text-xs text-slate-400 font-mono mt-0.5 break-all">
                          {exec.exact_query}
                        </p>
                      </div>
                    </div>

                    <div className="text-right shrink-0 ml-4">
                      <div className="text-sm font-bold text-emerald-400">
                        {exec.hit_count.toLocaleString()} hits
                      </div>
                      <span className="text-[10px] text-slate-500">{executionLabel(exec)}</span>
                    </div>
                  </label>
                  {tickErrors[exec.id] && (
                    <p role="alert" className="mt-1 text-[11px] text-red-300">
                      {tickErrors[exec.id]}
                    </p>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Attribution & Legal Notice */}
      <div className="mt-6 pt-4 border-t border-slate-800/80 text-[11px] text-slate-400 flex items-start gap-2">
        <CheckSquare className="w-3.5 h-3.5 text-slate-400 shrink-0 mt-0.5" />
        <p>
          Data sourced from National Center for Biotechnology Information (NCBI) / NLM E-utilities and Europe PMC
          REST APIs. Real queries are labeled live; synthetic tests are labeled fixture. Use conforms to NCBI and
          Europe PMC API terms of service.
        </p>
      </div>
    </div>
  );
};
