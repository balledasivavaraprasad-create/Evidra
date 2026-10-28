import React, { useState } from "react";
import { Search, Plus, Trash2, Calendar, Database, Play, AlertCircle, FileCode, CheckSquare } from "lucide-react";
import {
  api,
  type BooleanOperator,
  type QueryVersionResponse,
  type SearchExecutionResponse,
  type SourceNamespace,
} from "../../api/client";
import {
  astToReadableString,
  compileClauseToAST,
  isValidDateFormat,
  type QueryGroupClause,
} from "./astCompiler";

interface QueryBuilderProps {
  workspaceId: string;
  criteriaVersionId?: string;
  onQuerySaved?: (query: QueryVersionResponse) => void;
  onExecutionSelected?: (selectedIds: string[]) => void;
  /** Starting terms, one inner list per OR-group (defaults to the metformin example) */
  initialTerms?: string[][];
}

export const QueryBuilder: React.FC<QueryBuilderProps> = ({
  workspaceId,
  criteriaVersionId = "crit-ver-default",
  onQuerySaved,
  onExecutionSelected,
  initialTerms,
}) => {
  const [rootOperator, setRootOperator] = useState<BooleanOperator>("AND");
  const [groups, setGroups] = useState<QueryGroupClause[]>(() =>
    initialTerms && initialTerms.length > 0
      ? initialTerms.map((terms, gi) => ({
          id: `grp-${gi + 1}`,
          operator: "OR" as BooleanOperator,
          clauses: (terms.length ? terms : [""]).map((term, ci) => ({ id: `c-${gi + 1}-${ci + 1}`, field: "all", term })),
        }))
      : [
    {
      id: "grp-1",
      operator: "OR",
      clauses: [
        { id: "c-1", field: "all", term: "metformin" },
        { id: "c-2", field: "all", term: "glucophage" },
      ],
    },
    {
      id: "grp-2",
      operator: "OR",
      clauses: [
        { id: "c-3", field: "all", term: "type 2 diabetes" },
        { id: "c-4", field: "all", term: "T2D" },
      ],
    },
  ]
  );

  const [startDate, setStartDate] = useState("2020");
  const [endDate, setEndDate] = useState("2026");
  const [selectedSources, setSelectedSources] = useState<SourceNamespace[]>(["pubmed", "europepmc"]);

  const [savingQuery, setSavingQuery] = useState(false);
  const [activeQuery, setActiveQuery] = useState<QueryVersionResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Search Executions
  const [executingSource, setExecutingSource] = useState<string | null>(null);
  const [executions, setExecutions] = useState<SearchExecutionResponse[]>([]);
  const [selectedExecIds, setSelectedExecIds] = useState<string[]>([]);

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

  const handleSaveQuery = async () => {
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
      setActiveQuery(qResp);
      if (onQuerySaved) {
        onQuerySaved(qResp);
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to persist structured query version";
      setError(msg);
    } finally {
      setSavingQuery(false);
    }
  };

  const handleRunSearchCount = async (source: SourceNamespace) => {
    if (!activeQuery) {
      setError("Please save the query version before executing search counts.");
      return;
    }

    setExecutingSource(source);
    setError(null);

    try {
      const execResp = await api.queries.executeSearch(activeQuery.id, {
        source,
        synonym_expansion: false,
      });

      setExecutions((prev) => [execResp, ...prev]);
      // Auto select new execution
      const newSelected = [...selectedExecIds, execResp.id];
      setSelectedExecIds(newSelected);
      if (onExecutionSelected) {
        onExecutionSelected(newSelected);
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : `Failed to execute search count on ${source}`;
      setError(msg);
    } finally {
      setExecutingSource(null);
    }
  };

  const toggleExecutionSelection = (id: string) => {
    const next = selectedExecIds.includes(id)
      ? selectedExecIds.filter((x) => x !== id)
      : [...selectedExecIds, id];
    setSelectedExecIds(next);
    if (onExecutionSelected) {
      onExecutionSelected(next);
    }
  };

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
          disabled={savingQuery}
          className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-xs font-medium transition disabled:opacity-50"
        >
          {savingQuery ? "Saving Query Version..." : "Save Query Version"}
        </button>

        <div className="flex items-center gap-2">
          {selectedSources.map((src) => (
            <button
              key={src}
              type="button"
              disabled={!activeQuery || executingSource === src}
              onClick={() => handleRunSearchCount(src)}
              className="flex items-center gap-1.5 px-3 py-2 bg-slate-800 hover:bg-slate-700 border border-slate-700 text-white rounded-lg text-xs font-medium transition disabled:opacity-40"
            >
              <Play className="w-3 h-3 text-emerald-400" />
              <span>{executingSource === src ? `Counting ${src}...` : `Count on ${src}`}</span>
            </button>
          ))}
        </div>
      </div>

      {/* Search Executions Table */}
      {executions.length > 0 && (
        <div className="mt-6 border-t border-slate-800 pt-5">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-sm font-semibold text-white">Search Executions Comparison</h3>
            <span className="text-xs text-slate-400">
              {selectedExecIds.length} of {executions.length} selected for import
            </span>
          </div>

          <div className="space-y-2.5">
            {executions.map((exec) => {
              const isSelected = selectedExecIds.includes(exec.id);
              return (
                <div
                  key={exec.id}
                  onClick={() => toggleExecutionSelection(exec.id)}
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
                      onChange={() => {}}
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
                    <span className="text-[10px] text-slate-500">ID: {exec.id.slice(0, 8)}</span>
                  </div>
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
