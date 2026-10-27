import type { components, paths } from "./schema";

export type WorkspaceCreate = components["schemas"]["WorkspaceCreate"];
export type WorkspaceResponse = components["schemas"]["WorkspaceResponse"];
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
};
