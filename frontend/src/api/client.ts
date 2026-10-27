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
export type PaperGroupSummary = components["schemas"]["PaperGroupSummary"];
export type PaperGroupDetail = components["schemas"]["PaperGroupDetail"];
export type DedupOverrideRequest = components["schemas"]["DedupOverrideRequest"];
export type ScreenResult = components["schemas"]["ScreenResult"];
export type PicoResult = components["schemas"]["PicoResult"];

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
};
