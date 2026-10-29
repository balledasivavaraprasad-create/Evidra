import type { JobResponse } from "../../api/client";

/** Where an import is on its way into the screening queue. */
export type ImportPhase = "importing" | "processing" | "ready" | "import-failed" | "processing-failed";

const ACTIVE = ["queued", "running"];

export function isActiveJob(job: JobResponse | null | undefined): boolean {
  return !!job && ACTIVE.includes(job.state);
}

/**
 * Processing is finished when it succeeded, or paused for the reviewer (waiting_human): the papers
 * are processed and can be screened, with some left to confirm.
 */
export function isProcessingDone(job: JobResponse | null | undefined): boolean {
  return !!job && (job.state === "succeeded" || job.state === "waiting_human");
}

export function isProcessingFailed(job: JobResponse | null | undefined): boolean {
  return !!job && (job.state === "failed" || job.state === "cancelled" || job.state === "partial");
}

/**
 * Importing -> Processing -> Ready for the newest import and the newest processing job.
 * A processing job counts for this import only if it was created at or after the import.
 * `processingKnown` is false until the lookup of the processing job has completed.
 */
export function importPhase(
  importJob: JobResponse,
  processingJob: JobResponse | null,
  processingKnown = true,
): ImportPhase {
  if (isActiveJob(importJob)) return "importing";
  if (importJob.state !== "succeeded") return "import-failed";
  // An import that just finished has queued processing. Until we have looked that job up, "no job
  // yet" means we don't know, not that it is ready: never flash Ready early.
  if (!processingKnown) return "processing";
  const forThisImport = processingJob && processingJob.created_at >= importJob.created_at ? processingJob : null;
  if (!forThisImport) return "ready"; // an import from before imports were processed automatically
  if (isActiveJob(forThisImport)) return "processing";
  if (isProcessingFailed(forThisImport)) return "processing-failed";
  return "ready";
}

/**
 * Whether we know which processing job (if any) belongs to this import.
 *
 * - An import that was already finished when the page opened: known once the first lookup is done.
 * - An import that finished while the page was open: known only once the lookup made *after* it
 *   finished is done. Before that, "no processing job yet" just means we haven't asked.
 */
export function processingLookupDone(state: {
  loaded: boolean;
  importId: string | undefined;
  lookedUpFor: string | null;
  finishedBeforeLoadId: string | null;
}): boolean {
  if (!state.loaded || !state.importId) return false;
  return state.lookedUpFor === state.importId || state.finishedBeforeLoadId === state.importId;
}

export const PHASE_LABELS: Record<ImportPhase, string> = {
  importing: "Importing",
  processing: "Processing",
  ready: "Ready",
  "import-failed": "Import stopped",
  "processing-failed": "Processing stopped",
};

/** A short line for the processing job: its stage and how far along it is. */
export function processingLine(job: JobResponse): string {
  if (job.state === "queued") return "Waiting to start";
  if (job.state === "running") return "Removing duplicates, screening papers and finding PICO evidence";
  if (isProcessingDone(job)) return "Done";
  return job.error?.message ?? "Processing stopped";
}
