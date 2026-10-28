import type { components } from "./schema";

export type WorkspaceCreate = components["schemas"]["WorkspaceCreate"];
export type WorkspaceResponse = components["schemas"]["WorkspaceResponse"];
export type CriteriaVersionCreate = components["schemas"]["CriteriaVersionCreate"];
export type CriteriaVersionResponse = components["schemas"]["CriteriaVersionResponse"];
export type CriterionDefinition = components["schemas"]["CriterionDefinition"];
export type QueryVersionCreate = components["schemas"]["QueryVersionCreate"];
export type QueryVersionResponse = components["schemas"]["QueryVersionResponse"];
export type QueryASTNodeInput = components["schemas"]["QueryASTNode-Input"];
export type QueryASTNodeOutput = components["schemas"]["QueryASTNode-Output"];
export type BooleanOperator = components["schemas"]["BooleanOperator"];
export type SourceNamespace = components["schemas"]["SourceNamespace"];
export type SearchExecutionCreate = components["schemas"]["SearchExecutionCreate"];
export type SearchExecutionResponse = components["schemas"]["SearchExecutionResponse"];
export type ImportJobCreate = components["schemas"]["ImportJobCreate"];
export type JobResponse = components["schemas"]["JobResponse"];
export type JobState = components["schemas"]["JobState"];
export type JobKind = components["schemas"]["JobKind"];

export type ErrorEnvelope = components["schemas"]["ErrorEnvelope"];
export type CorpusRevisionResponse = components["schemas"]["CorpusRevisionResponse"];
export type PaperGroupSummary = components["schemas"]["PaperGroupSummary"];
export type PaperGroupDetail = components["schemas"]["PaperGroupDetail"];
export type DecisionCommand = components["schemas"]["DecisionCommand"];
export type PicoOverrideRequest = components["schemas"]["PicoOverrideRequest"];
export type PicoSpan = components["schemas"]["PicoSpan"];
export type PicoLabel = components["schemas"]["PicoLabel"];
export type DedupOverrideRequest = components["schemas"]["DedupOverrideRequest"];
export type ConflictResolveRequest = components["schemas"]["ConflictResolveRequest"];
export type ExportRequest = components["schemas"]["ExportRequest"];
export type ExportResponse = components["schemas"]["ExportResponse"];
export type ReviewEventResponse = components["schemas"]["ReviewEventResponse"];
export type ScreenResult = components["schemas"]["ScreenResult"];
export type PicoResult = components["schemas"]["PicoResult"];
export type EffectiveDecisionState = components["schemas"]["EffectiveDecisionState"];
export type EligibilityStatus = components["schemas"]["EligibilityStatus"];
export type CorpusDiffResponse = components["schemas"]["CorpusDiffResponse"];
export type AssistantRequest = components["schemas"]["AssistantRequest"];
export type AssistantProposal = components["schemas"]["AssistantProposal"];
export type RetrievalChunk = components["schemas"]["RetrievalChunk"];
export type ScreeningRankRequest = components["schemas"]["ScreeningRankRequest"];
export type ScreeningRankResponse = components["schemas"]["ScreeningRankResponse"];
export type RankedGroupItem = components["schemas"]["RankedGroupItem"];
export type RestoreMode = "exact_snapshot" | "latest_decisions";

export interface SnapshotRestoreRequest {
  snapshot_id: string;
  mode?: RestoreMode;
  expected_workspace_version?: number;
}

export interface DedupProposal {
  record_id_a: string;
  record_id_b: string;
  score: number;
  method_version: string;
  evidence: Record<string, unknown>;
  status?: "proposed" | "confirmed" | "rejected";
}

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    public readonly code: string,
    message: string,
    public readonly retryable: boolean = false,
    public readonly details?: components["schemas"]["ErrorDetail"][] | null
  ) {
    super(message);
    this.name = "ApiError";
  }

  static fromEnvelope(status: number, envelope: Partial<ErrorEnvelope>): ApiError {
    return new ApiError(
      status,
      envelope.code || "UNKNOWN_ERROR",
      envelope.message || "An unexpected error occurred",
      envelope.retryable ?? false,
      envelope.details
    );
  }
}

const API_BASE = "";

async function request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const url = `${API_BASE}${endpoint}`;
  const response = await fetch(url, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      Accept: "application/json",
      ...options.headers,
    },
  });

  const contentType = response.headers.get("content-type") || "";
  const isJson = contentType.includes("application/json");

  if (!response.ok) {
    if (isJson) {
      const errorData = (await response.json()) as ErrorEnvelope;
      throw ApiError.fromEnvelope(response.status, errorData);
    }
    const text = await response.text();
    throw new ApiError(response.status, "HTTP_ERROR", text || response.statusText);
  }

  if (response.status === 204) {
    return {} as T;
  }

  return (await response.json()) as T;
}

export const api = {
  health: {
    live: () => request<{ status: string; app: string; version: string; env: string }>("/health/live"),
    ready: () => request<{ status: string; database: string }>("/health/ready"),
  },
  workspaces: {
    create: (payload: WorkspaceCreate) =>
      request<WorkspaceResponse>("/api/v1/workspaces", {
        method: "POST",
        body: JSON.stringify(payload),
      }),
  },
  criteria: {
    create: (workspaceId: string, payload: CriteriaVersionCreate) =>
      request<CriteriaVersionResponse>(`/api/v1/workspaces/${workspaceId}/criteria`, {
        method: "POST",
        body: JSON.stringify(payload),
      }),
  },
  queries: {
    create: (workspaceId: string, payload: QueryVersionCreate) =>
      request<QueryVersionResponse>(`/api/v1/workspaces/${workspaceId}/queries`, {
        method: "POST",
        body: JSON.stringify(payload),
      }),
    executeSearch: (queryId: string, payload: SearchExecutionCreate) =>
      request<SearchExecutionResponse>(`/api/v1/queries/${queryId}/searches`, {
        method: "POST",
        body: JSON.stringify(payload),
      }),
  },
  imports: {
    trigger: (workspaceId: string, payload: ImportJobCreate) =>
      request<JobResponse>(`/api/v1/workspaces/${workspaceId}/imports`, {
        method: "POST",
        body: JSON.stringify(payload),
      }),
  },
  jobs: {
    get: (jobId: string) => request<JobResponse>(`/api/v1/jobs/${jobId}`),
    cancel: (jobId: string) =>
      request<JobResponse>(`/api/v1/jobs/${jobId}/cancel`, {
        method: "POST",
      }),
  },
  revisions: {
    list: (workspaceId: string) =>
      request<CorpusRevisionResponse[]>(`/api/v1/workspaces/${workspaceId}/revisions`),
    processCorpus: (workspaceId: string, criteriaVersionId?: string) => {
      const url = criteriaVersionId
        ? `/api/v1/workspaces/${workspaceId}/process-corpus?criteria_version_id=${encodeURIComponent(criteriaVersionId)}`
        : `/api/v1/workspaces/${workspaceId}/process-corpus`;
      return request<CorpusRevisionResponse>(url, { method: "POST" });
    },
    listGroups: (revisionId: string, status?: string, limit = 50, offset = 0) => {
      const params = new URLSearchParams({ limit: String(limit), offset: String(offset) });
      if (status) params.set("status", status);
      return request<PaperGroupSummary[]>(`/api/v1/revisions/${revisionId}/groups?${params.toString()}`);
    },
    getDiff: (revisionId: string, baseRevisionId: string) =>
      request<CorpusDiffResponse>(
        `/api/v1/revisions/${encodeURIComponent(revisionId)}/diff?base_revision_id=${encodeURIComponent(baseRevisionId)}`
      ),
    restore: (workspaceId: string, payload: SnapshotRestoreRequest) =>
      request<CorpusRevisionResponse>(
        `/api/v1/workspaces/${encodeURIComponent(workspaceId)}/restore?snapshot_id=${encodeURIComponent(payload.snapshot_id)}`,
        {
          method: "POST",
        }
      ),
  },
  groups: {
    getDetail: (groupId: string, revisionId?: string) => {
      const url = revisionId
        ? `/api/v1/groups/${groupId}?revision_id=${encodeURIComponent(revisionId)}`
        : `/api/v1/groups/${groupId}`;
      return request<PaperGroupDetail>(url);
    },
    recordDecision: (groupId: string, payload: DecisionCommand) =>
      request<ReviewEventResponse>(`/api/v1/groups/${groupId}/decisions`, {
        method: "POST",
        body: JSON.stringify(payload),
      }),
    savePico: (groupId: string, payload: PicoOverrideRequest) =>
      request<ReviewEventResponse>(`/api/v1/groups/${groupId}/pico`, {
        method: "POST",
        body: JSON.stringify(payload),
      }),
  },
  dedup: {
    recordDecision: (workspaceId: string, payload: DedupOverrideRequest) =>
      request<ReviewEventResponse>(`/api/v1/workspaces/${workspaceId}/dedup-decisions`, {
        method: "POST",
        body: JSON.stringify(payload),
      }),
  },
  conflicts: {
    resolve: (conflictId: string, payload: ConflictResolveRequest) =>
      request<ReviewEventResponse>(`/api/v1/conflicts/${conflictId}/resolve`, {
        method: "POST",
        body: JSON.stringify(payload),
      }),
  },
  exports: {
    create: (revisionId: string, payload: ExportRequest) =>
      request<ExportResponse>(`/api/v1/revisions/${revisionId}/exports`, {
        method: "POST",
        body: JSON.stringify(payload),
      }),
    downloadUrl: (exportId: string) => `/api/v1/exports/${exportId}/download`,
  },
  screening: {
    getRank: (workspaceId: string, payload?: ScreeningRankRequest) =>
      request<ScreeningRankResponse>(`/api/v1/workspaces/${encodeURIComponent(workspaceId)}/screening/rank`, {
        method: "POST",
        body: payload ? JSON.stringify(payload) : undefined,
      }),
  },
  assistant: {
    query: (workspaceId: string, payload: AssistantRequest) =>
      request<AssistantProposal>(`/api/v1/workspaces/${encodeURIComponent(workspaceId)}/assistant`, {
        method: "POST",
        body: JSON.stringify(payload),
      }),
  },
};

