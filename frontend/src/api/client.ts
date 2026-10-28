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
export type MLRankingRequest = components["schemas"]["MLRankingRequest"];
export type MLRankingResponse = components["schemas"]["MLRankingResponse"];
export type MLRankedItem = components["schemas"]["MLRankedItem"];
export type EvidenceItemResponse = components["schemas"]["EvidenceItemResponse"];
export type EvidencePassportBundle = components["schemas"]["EvidencePassportBundle"];
export type EvidencePassportSummary = components["schemas"]["EvidencePassportSummary"];
export type EvidenceCorrectionRequest = components["schemas"]["EvidenceCorrectionRequest"];
export type EvidenceItemCreateRequest = components["schemas"]["EvidenceItemCreateRequest"];
export type EvidenceRevalidateResponse = components["schemas"]["EvidenceRevalidateResponse"];
export type EvidenceCoverageResponse = components["schemas"]["EvidenceCoverageResponse"];
export type EvidenceClaimType = components["schemas"]["EvidenceClaimType"];
export type EvidenceValidationStatus = components["schemas"]["EvidenceValidationStatus"];
export type EvidenceSemanticAssessment = components["schemas"]["EvidenceSemanticAssessment"];
export type EvidenceProvenance = components["schemas"]["EvidenceProvenance"];
export type SearchEvolutionVersionSummary = components["schemas"]["SearchEvolutionVersionSummary"];
export type SearchEvolutionDiffResponse = components["schemas"]["SearchEvolutionDiffResponse"];
export type SearchEvolutionDiffSummary = components["schemas"]["SearchEvolutionDiffSummary"];
export type SearchEvolutionRecordDiff = components["schemas"]["SearchEvolutionRecordDiff"];
export type SearchEvolutionMetadataFieldDiff = components["schemas"]["SearchEvolutionMetadataFieldDiff"];
export type SearchEvolutionCategory = components["schemas"]["SearchEvolutionCategory"];
export type SearchRestoreRequest = components["schemas"]["SearchRestoreRequest"];
export type SearchRestoreResponse = components["schemas"]["SearchRestoreResponse"];
export type ArticleRadarResponse = components["schemas"]["ArticleRadarResponse"];
export type ReviewRadarResponse = components["schemas"]["ReviewRadarResponse"];
export type RadarFieldDetail = components["schemas"]["RadarFieldDetail"];
export type ReviewRadarDimensionSummary = components["schemas"]["ReviewRadarDimensionSummary"];
export type ReviewRadarArticleRow = components["schemas"]["ReviewRadarArticleRow"];
export type RadarEvidenceStatus = components["schemas"]["RadarEvidenceStatus"];
export type RadarHumanReviewStatus = components["schemas"]["RadarHumanReviewStatus"];
export type RadarConfirmRequest = components["schemas"]["RadarConfirmRequest"];
export type RadarCorrectRequest = components["schemas"]["RadarCorrectRequest"];
export type RadarFlagUncertainRequest = components["schemas"]["RadarFlagUncertainRequest"];
export type RadarFlagConflictRequest = components["schemas"]["RadarFlagConflictRequest"];
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
  ml: {
    computeRanking: (workspaceId: string, revisionId: string, payload?: MLRankingRequest) =>
      request<MLRankingResponse>(
        `/api/v1/workspaces/${encodeURIComponent(workspaceId)}/revisions/${encodeURIComponent(revisionId)}/ml-ranking`,
        {
          method: "POST",
          body: payload ? JSON.stringify(payload) : undefined,
        }
      ),
    getRanking: (workspaceId: string, revisionId: string, limit = 100, offset = 0, forceRecompute = false) => {
      const q = new URLSearchParams({
        limit: String(limit),
        offset: String(offset),
        force_recompute: String(forceRecompute),
      });
      return request<MLRankingResponse>(
        `/api/v1/workspaces/${encodeURIComponent(workspaceId)}/revisions/${encodeURIComponent(revisionId)}/ml-ranking?${q.toString()}`,
        {
          method: "GET",
        }
      );
    },
  },
  evidence: {
    getBundle: (workspaceId: string, groupId: string) =>
      request<EvidencePassportBundle>(`/api/v1/workspaces/${encodeURIComponent(workspaceId)}/groups/${encodeURIComponent(groupId)}/evidence`),
    correctItem: (workspaceId: string, evidenceId: string, payload: EvidenceCorrectionRequest) =>
      request<EvidenceItemResponse>(
        `/api/v1/workspaces/${encodeURIComponent(workspaceId)}/evidence/${encodeURIComponent(evidenceId)}/correct`,
        {
          method: "POST",
          body: JSON.stringify(payload),
        }
      ),
    createItem: (workspaceId: string, groupId: string, payload: EvidenceItemCreateRequest) =>
      request<EvidenceItemResponse>(
        `/api/v1/workspaces/${encodeURIComponent(workspaceId)}/groups/${encodeURIComponent(groupId)}/evidence`,
        {
          method: "POST",
          body: JSON.stringify(payload),
        }
      ),
    revalidateGroup: (workspaceId: string, groupId: string) =>
      request<EvidenceRevalidateResponse>(
        `/api/v1/workspaces/${encodeURIComponent(workspaceId)}/groups/${encodeURIComponent(groupId)}/evidence/revalidate`,
        {
          method: "POST",
        }
      ),
    getSummary: (workspaceId: string) =>
      request<EvidenceCoverageResponse>(`/api/v1/workspaces/${encodeURIComponent(workspaceId)}/evidence/summary`),
    exportUrl: (workspaceId: string) => `/api/v1/workspaces/${encodeURIComponent(workspaceId)}/evidence/export`,
  },
  searchEvolution: {
    listVersions: (workspaceId: string) =>
      request<SearchEvolutionVersionSummary[]>(`/api/v1/workspaces/${encodeURIComponent(workspaceId)}/search-versions`),
    getVersion: (workspaceId: string, versionId: string) =>
      request<SearchEvolutionVersionSummary>(`/api/v1/workspaces/${encodeURIComponent(workspaceId)}/search-versions/${encodeURIComponent(versionId)}`),
    getDiff: (workspaceId: string, targetVersionId: string, baseVersionId?: string) => {
      const q = baseVersionId ? `?base_version_id=${encodeURIComponent(baseVersionId)}` : "";
      return request<SearchEvolutionDiffResponse>(
        `/api/v1/workspaces/${encodeURIComponent(workspaceId)}/search-versions/${encodeURIComponent(targetVersionId)}/diff${q}`
      );
    },
    restoreVersion: (workspaceId: string, versionId: string, payload: SearchRestoreRequest) =>
      request<SearchRestoreResponse>(
        `/api/v1/workspaces/${encodeURIComponent(workspaceId)}/search-versions/${encodeURIComponent(versionId)}/restore`,
        {
          method: "POST",
          body: JSON.stringify(payload),
        }
      ),
  },
  radar: {
    getOverview: (
      workspaceId: string,
      params?: {
        dimension_filter?: string;
        status_filter?: string;
        needs_review_only?: boolean;
        query?: string;
        limit?: number;
        offset?: number;
      }
    ) => {
      const q = new URLSearchParams();
      if (params?.dimension_filter) q.set("dimension_filter", params.dimension_filter);
      if (params?.status_filter) q.set("status_filter", params.status_filter);
      if (params?.needs_review_only) q.set("needs_review_only", "true");
      if (params?.query) q.set("query", params.query);
      if (params?.limit) q.set("limit", String(params.limit));
      if (params?.offset) q.set("offset", String(params.offset));
      const qs = q.toString() ? `?${q.toString()}` : "";
      return request<ReviewRadarResponse>(
        `/api/v1/workspaces/${encodeURIComponent(workspaceId)}/pico-radar${qs}`
      );
    },
    getArticleRadar: (workspaceId: string, groupId: string) =>
      request<ArticleRadarResponse>(
        `/api/v1/workspaces/${encodeURIComponent(workspaceId)}/groups/${encodeURIComponent(groupId)}/pico-radar`
      ),
    confirmField: (workspaceId: string, groupId: string, fieldType: string, payload: RadarConfirmRequest) =>
      request<ArticleRadarResponse>(
        `/api/v1/workspaces/${encodeURIComponent(workspaceId)}/groups/${encodeURIComponent(groupId)}/pico-radar/${encodeURIComponent(fieldType)}/confirm`,
        {
          method: "POST",
          body: JSON.stringify(payload),
        }
      ),
    correctField: (workspaceId: string, groupId: string, fieldType: string, payload: RadarCorrectRequest) =>
      request<ArticleRadarResponse>(
        `/api/v1/workspaces/${encodeURIComponent(workspaceId)}/groups/${encodeURIComponent(groupId)}/pico-radar/${encodeURIComponent(fieldType)}/correct`,
        {
          method: "POST",
          body: JSON.stringify(payload),
        }
      ),
    flagUncertain: (workspaceId: string, groupId: string, fieldType: string, payload: RadarFlagUncertainRequest) =>
      request<ArticleRadarResponse>(
        `/api/v1/workspaces/${encodeURIComponent(workspaceId)}/groups/${encodeURIComponent(groupId)}/pico-radar/${encodeURIComponent(fieldType)}/flag-uncertain`,
        {
          method: "POST",
          body: JSON.stringify(payload),
        }
      ),
    flagConflict: (workspaceId: string, groupId: string, fieldType: string, payload: RadarFlagConflictRequest) =>
      request<ArticleRadarResponse>(
        `/api/v1/workspaces/${encodeURIComponent(workspaceId)}/groups/${encodeURIComponent(groupId)}/pico-radar/${encodeURIComponent(fieldType)}/flag-conflict`,
        {
          method: "POST",
          body: JSON.stringify(payload),
        }
      ),
    revalidateField: (workspaceId: string, groupId: string, fieldType: string) =>
      request<ArticleRadarResponse>(
        `/api/v1/workspaces/${encodeURIComponent(workspaceId)}/groups/${encodeURIComponent(groupId)}/pico-radar/${encodeURIComponent(fieldType)}/revalidate`,
        {
          method: "POST",
        }
      ),
  },
};

