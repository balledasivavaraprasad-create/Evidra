import {
  api,
  ApiError,
  type CriteriaVersionResponse,
  type JobResponse,
  type QueryVersionResponse,
  type SearchExecutionResponse,
  type WorkspaceResponse,
} from "../../api/client";
import { sortExecutions } from "./executions";
import { loadSavedCriteria } from "./savedCriteria";

/** Everything the Query page shows, as the server has it. */
export interface SetupData {
  workspace: WorkspaceResponse | null;
  criteria: CriteriaVersionResponse | null;
  query: QueryVersionResponse | null;
  executions: SearchExecutionResponse[];
  importJob: JobResponse | null;
}

/** Latest saved search, or null when none has been saved yet (404). */
export async function loadLatestQuery(workspaceId: string): Promise<QueryVersionResponse | null> {
  try {
    return await api.queries.latest(workspaceId);
  } catch (err) {
    if (err instanceof ApiError && err.status === 404) return null;
    throw err;
  }
}

/** Newest import job; the list is sorted here rather than trusting the server's order. */
export function newestJob(jobs: readonly JobResponse[]): JobResponse | null {
  return [...jobs].sort((a, b) => b.created_at.localeCompare(a.created_at))[0] ?? null;
}

export async function loadLatestImportJob(workspaceId: string): Promise<JobResponse | null> {
  return newestJob(await api.jobs.listForWorkspace(workspaceId, "import_records", 5));
}

/**
 * Load the review, its saved question, latest query with its counts, and latest import in
 * parallel. A 404 for the question or query means "nothing saved yet". Any other failure rejects,
 * so the page shows an error instead of quietly showing an empty form over saved work.
 */
export async function loadSetupData(workspaceId: string): Promise<SetupData> {
  const [workspaces, criteria, queryAndCounts, importJob] = await Promise.all([
    api.workspaces.list(),
    loadSavedCriteria(workspaceId),
    loadLatestQuery(workspaceId).then(async (query) => ({
      query,
      executions: query ? sortExecutions(await api.queries.listExecutions(workspaceId, query.id)) : [],
    })),
    loadLatestImportJob(workspaceId),
  ]);
  return {
    workspace: workspaces.find((w) => w.id === workspaceId) ?? null,
    criteria,
    query: queryAndCounts.query,
    executions: queryAndCounts.executions,
    importJob,
  };
}
