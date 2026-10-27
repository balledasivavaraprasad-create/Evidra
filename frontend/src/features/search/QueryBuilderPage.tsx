import React, { useState } from "react";
import { useParams, Link } from "react-router-dom";
import { Search, ArrowRight, CheckCircle2 } from "lucide-react";
import { CriteriaEditor } from "../review-setup/CriteriaEditor";
import { QueryBuilder } from "./QueryBuilder";
import { ImportWorkflow } from "../runs/ImportWorkflow";
import type { CriteriaVersionResponse, QueryVersionResponse, JobResponse } from "../../api/client";

export const QueryBuilderPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const workspaceId = id || "ws-default";

  const [criteriaVersion, setCriteriaVersion] = useState<CriteriaVersionResponse | null>(null);
  const [activeQuery, setActiveQuery] = useState<QueryVersionResponse | null>(null);
  const [selectedExecIds, setSelectedExecIds] = useState<string[]>([]);
  const [completedJob, setCompletedJob] = useState<JobResponse | null>(null);

  return (
    <div className="space-y-6 pb-16">
      {/* Page Header */}
      <div className="border-b border-slate-800 pb-4 flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-white flex items-center gap-2">
            <Search className="w-5 h-5 text-indigo-400" />
            <span>Search Strategy & Approved Literature Ingestion</span>
          </h1>
          <p className="text-slate-400 text-xs mt-0.5">
            Workspace: <code className="text-indigo-300 font-mono">{workspaceId}</code> • Define screening criteria, build Boolean queries, verify provider counts, and trigger background imports.
          </p>
        </div>

        {completedJob && (
          <Link
            to={`/reviews/${workspaceId}/records`}
            className="flex items-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-xs font-semibold transition"
          >
            <span>Proceed to Screening Queue</span>
            <ArrowRight className="w-4 h-4" />
          </Link>
        )}
      </div>

      {completedJob && (
        <div className="p-4 bg-emerald-950/40 border border-emerald-500/40 rounded-xl flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <CheckCircle2 className="w-5 h-5 text-emerald-400 shrink-0" />
            <div>
              <h4 className="text-sm font-semibold text-white">Literature Ingestion Succeeded</h4>
              <p className="text-xs text-slate-300">
                {completedJob.processed_items ?? 0} records have been imported, normalized, and indexed into this workspace.
              </p>
            </div>
          </div>
          <Link
            to={`/reviews/${workspaceId}/records`}
            className="px-3 py-1.5 bg-emerald-600 hover:bg-emerald-500 text-white rounded text-xs font-medium transition"
          >
            Review Records
          </Link>
        </div>
      )}

      {/* 1. Review Setup & Criteria Editor */}
      <section aria-labelledby="section-criteria">
        <CriteriaEditor
          workspaceId={workspaceId}
          savedCriteria={criteriaVersion}
          onCriteriaSaved={(crit) => setCriteriaVersion(crit)}
        />
      </section>

      {/* 2. Boolean Query Builder & Search Count Acquisition */}
      <section aria-labelledby="section-query-builder">
        <QueryBuilder
          workspaceId={workspaceId}
          criteriaVersionId={criteriaVersion?.id || "crit-ver-default"}
          onQuerySaved={(q) => setActiveQuery(q)}
          onExecutionSelected={(ids) => setSelectedExecIds(ids)}
        />
      </section>

      {/* 3. Approved Record Ingestion & Durable Job Tracker */}
      <section aria-labelledby="section-import-runs">
        <ImportWorkflow
          workspaceId={workspaceId}
          selectedExecutionIds={selectedExecIds}
          onImportComplete={(job) => setCompletedJob(job)}
        />
      </section>
    </div>
  );
};
