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
export type CapabilitiesResponse = components["schemas"]["CapabilitiesResponse"];
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
export type DevilsAdvocateChallengeResponse = components["schemas"]["DevilsAdvocateChallengeResponse"];
export type DevilsAdvocateDashboardResponse = components["schemas"]["DevilsAdvocateDashboardResponse"];
export type DevilsAdvocateDashboardItem = components["schemas"]["DevilsAdvocateDashboardItem"];
export type DevilsAdvocateDispositionRequest = components["schemas"]["DevilsAdvocateDispositionRequest"];
export type DevilsAdvocateGenerateRequest = components["schemas"]["DevilsAdvocateGenerateRequest"];
export type CounterArgumentItem = components["schemas"]["CounterArgumentItem"];
export type ChallengeRecommendation = components["schemas"]["ChallengeRecommendation"];
export type ChallengeDisposition = components["schemas"]["ChallengeDisposition"];
export type VulnerabilityFlag = components["schemas"]["VulnerabilityFlag"];
export type DuplicateGroupGenealogyResponse = components["schemas"]["DuplicateGroupGenealogyResponse"];
export type DuplicateWorkspaceSummaryResponse = components["schemas"]["DuplicateWorkspaceSummaryResponse"];
export type DuplicateWorkspaceSummaryItem = components["schemas"]["DuplicateWorkspaceSummaryItem"];
export type DuplicateRecordMemberDetail = components["schemas"]["DuplicateRecordMemberDetail"];
export type DuplicateMatchSignalDetail = components["schemas"]["DuplicateMatchSignalDetail"];
export type DecisionConflictDetail = components["schemas"]["DecisionConflictDetail"];
export type FieldProvenanceItem = components["schemas"]["FieldProvenanceItem"];
export type DuplicateMergeHistoryItem = components["schemas"]["DuplicateMergeHistoryItem"];
export type DuplicateReconcileRequest = components["schemas"]["DuplicateReconcileRequest"];
export type DuplicateSplitRequest = components["schemas"]["DuplicateSplitRequest"];
export type DuplicateReverseMergeRequest = components["schemas"]["DuplicateReverseMergeRequest"];
export type DuplicateRelationshipStatus = components["schemas"]["DuplicateRelationshipStatus"];
export type DuplicateConflictClassification = components["schemas"]["DuplicateConflictClassification"];
export type DuplicateMergeOperation = components["schemas"]["DuplicateMergeOperation"];
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
    // FastAPI's built-in errors use {"detail": "..."} instead of the Evidra envelope
    const rawDetail = (envelope as { detail?: unknown }).detail;
    const detail =
      typeof rawDetail === "string" && !["Not Found", "Internal Server Error"].includes(rawDetail) ? rawDetail : null;
    const fallback =
      status === 404 ? FRIENDLY_ERRORS.notFound : status >= 500 ? FRIENDLY_ERRORS.server : "The request couldn't be completed.";
    return new ApiError(
      status,
      envelope.code || (status === 404 ? "NOT_FOUND" : status >= 500 ? "SERVER_ERROR" : "UNKNOWN_ERROR"),
      envelope.message || detail || fallback,
      envelope.retryable ?? status >= 500,
      envelope.details
    );
  }
}

const API_BASE = "";

/** Plain-language messages for failures that carry no useful server message. */
export const FRIENDLY_ERRORS = {
  unreachable: "Evidra can't reach the review service. Start the backend, then try again.",
  server: "The review service hit an unexpected problem while loading this. Try again; if it keeps happening, check the backend terminal for details.",
  notFound: "This item doesn't exist in the current review. It may have been removed or belongs to another workspace.",
  authRequired: "Enter the site password to continue.",
} as const;

/** Fired on window when the server says this browser needs to sign in (AUTH_MODE=password). */
export const AUTH_REQUIRED_EVENT = "evidra:auth-required";

export type AuthSession = components["schemas"]["AuthSessionResponse"];

/** True when the backend could not be reached at all (stopped, crashed or proxy can't connect). */
export function isServiceUnreachable(err: unknown): boolean {
  return err instanceof ApiError && err.code === "SERVICE_UNREACHABLE";
}

async function request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const url = `${API_BASE}${endpoint}`;
  let response: Response;
  try {
    response = await fetch(url, {
      ...options,
      headers: {
        "Content-Type": "application/json",
        Accept: "application/json",
        ...options.headers,
      },
    });
  } catch {
    // Network failure: backend down, wrong port or no connection
    throw new ApiError(0, "SERVICE_UNREACHABLE", FRIENDLY_ERRORS.unreachable, true);
  }

  const contentType = response.headers.get("content-type") || "";
  const isJson = contentType.includes("application/json");

  if (!response.ok) {
    if (isJson) {
      const errorData = (await response.json()) as ErrorEnvelope;
      const err = ApiError.fromEnvelope(response.status, errorData);
      if (err.status === 401 && err.code === "AUTH_REQUIRED" && typeof window !== "undefined") {
        window.dispatchEvent(new CustomEvent(AUTH_REQUIRED_EVENT));
      }
      throw err;
    }
    // Non-JSON errors come from the dev proxy or an unhandled crash, never from the API's own
    // error envelope, so replace the bare status text with something a reviewer can act on.
    if (response.status === 502 || response.status === 503 || response.status === 504) {
      throw new ApiError(response.status, "SERVICE_UNREACHABLE", FRIENDLY_ERRORS.unreachable, true);
    }
    if (response.status >= 500) {
      throw new ApiError(response.status, "SERVER_ERROR", FRIENDLY_ERRORS.server, true);
    }
    if (response.status === 404) {
      throw new ApiError(404, "NOT_FOUND", FRIENDLY_ERRORS.notFound);
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
  auth: {
    session: () => request<AuthSession>("/api/v1/auth/session"),
    login: (password: string) =>
      request<void>("/api/v1/auth/login", { method: "POST", body: JSON.stringify({ password }) }),
    logout: () => request<void>("/api/v1/auth/logout", { method: "POST" }),
  },
  capabilities: {
    get: () => request<CapabilitiesResponse>("/api/v1/capabilities"),
  },
  health: {
    live: () => request<{ status: string; app: string; version: string; env: string }>("/health/live"),
    ready: () => request<{ status: string; database: string }>("/health/ready"),
  },
  workspaces: {
    list: () => request<WorkspaceResponse[]>("/api/v1/workspaces"),
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
  devilsAdvocate: {
    getChallenge: (workspaceId: string, groupId: string) =>
      request<DevilsAdvocateChallengeResponse>(
        `/api/v1/workspaces/${encodeURIComponent(workspaceId)}/groups/${encodeURIComponent(groupId)}/devils-advocate`
      ),
    generateChallenge: (workspaceId: string, groupId: string, payload: DevilsAdvocateGenerateRequest) =>
      request<DevilsAdvocateChallengeResponse>(
        `/api/v1/workspaces/${encodeURIComponent(workspaceId)}/groups/${encodeURIComponent(groupId)}/devils-advocate/generate`,
        {
          method: "POST",
          body: JSON.stringify(payload),
        }
      ),
    recordDisposition: (workspaceId: string, groupId: string, payload: DevilsAdvocateDispositionRequest) =>
      request<DevilsAdvocateChallengeResponse>(
        `/api/v1/workspaces/${encodeURIComponent(workspaceId)}/groups/${encodeURIComponent(groupId)}/devils-advocate/disposition`,
        {
          method: "POST",
          body: JSON.stringify(payload),
        }
      ),
    getDashboard: (
      workspaceId: string,
      params?: {
        disposition?: string;
        high_vulnerability_only?: boolean;
        limit?: number;
        offset?: number;
      }
    ) => {
      const q = new URLSearchParams();
      if (params?.disposition) q.set("disposition", params.disposition);
      if (params?.high_vulnerability_only) q.set("high_vulnerability_only", "true");
      if (params?.limit) q.set("limit", String(params.limit));
      if (params?.offset) q.set("offset", String(params.offset));
      const qs = q.toString() ? `?${q.toString()}` : "";
      return request<DevilsAdvocateDashboardResponse>(
        `/api/v1/workspaces/${encodeURIComponent(workspaceId)}/devils-advocate${qs}`
      );
    },
  },
  genealogy: {
    getOverview: (
      workspaceId: string,
      params?: {
        conflict_only?: boolean;
        limit?: number;
        offset?: number;
      }
    ) => {
      const q = new URLSearchParams();
      if (params?.conflict_only) q.set("conflict_only", "true");
      if (params?.limit) q.set("limit", String(params.limit));
      if (params?.offset) q.set("offset", String(params.offset));
      const qs = q.toString() ? `?${q.toString()}` : "";
      return request<DuplicateWorkspaceSummaryResponse>(
        `/api/v1/workspaces/${encodeURIComponent(workspaceId)}/duplicates${qs}`
      );
    },
    getGroupGenealogy: (workspaceId: string, groupId: string) =>
      request<DuplicateGroupGenealogyResponse>(
        `/api/v1/workspaces/${encodeURIComponent(workspaceId)}/groups/${encodeURIComponent(groupId)}/genealogy`
      ),
    reconcileConflict: (workspaceId: string, groupId: string, payload: DuplicateReconcileRequest) =>
      request<DuplicateGroupGenealogyResponse>(
        `/api/v1/workspaces/${encodeURIComponent(workspaceId)}/groups/${encodeURIComponent(groupId)}/reconcile`,
        {
          method: "POST",
          body: JSON.stringify(payload),
        }
      ),
    splitGroup: (workspaceId: string, groupId: string, payload: DuplicateSplitRequest) =>
      request<DuplicateGroupGenealogyResponse>(
        `/api/v1/workspaces/${encodeURIComponent(workspaceId)}/groups/${encodeURIComponent(groupId)}/split`,
        {
          method: "POST",
          body: JSON.stringify(payload),
        }
      ),
    reverseMerge: (workspaceId: string, groupId: string, payload: DuplicateReverseMergeRequest) =>
      request<DuplicateGroupGenealogyResponse>(
        `/api/v1/workspaces/${encodeURIComponent(workspaceId)}/groups/${encodeURIComponent(groupId)}/reverse-merge`,
        {
          method: "POST",
          body: JSON.stringify(payload),
        }
      ),
  },
};

