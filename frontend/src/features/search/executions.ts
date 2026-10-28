import type { SearchExecutionResponse } from "../../api/client";

/** Newest count first, the order the list is shown in. */
export function sortExecutions(list: readonly SearchExecutionResponse[]): SearchExecutionResponse[] {
  return [...list].sort((a, b) => b.counted_at.localeCompare(a.counted_at));
}

/**
 * Add a count to the list, or replace the row with the same id. Counting the same saved query
 * again returns the recorded execution, so it must never create a second row.
 */
export function upsertExecution(
  list: readonly SearchExecutionResponse[],
  exec: SearchExecutionResponse,
): SearchExecutionResponse[] {
  return list.some((e) => e.id === exec.id) ? list.map((e) => (e.id === exec.id ? exec : e)) : [exec, ...list];
}

/** Flip the tick on one row only. */
export function withSelection(
  list: readonly SearchExecutionResponse[],
  id: string,
  selected: boolean,
): SearchExecutionResponse[] {
  return list.map((e) => (e.id === id ? { ...e, selected_for_import: selected } : e));
}

/** Ids of the ticked rows, each once. */
export function selectedIds(list: readonly SearchExecutionResponse[]): string[] {
  return [...new Set(list.filter((e) => e.selected_for_import).map((e) => e.id))];
}

/** How a count is labelled in the list: its source and the last 8 characters of its id. */
export function executionLabel(exec: Pick<SearchExecutionResponse, "source" | "id">): string {
  return `${exec.source} · ${exec.id.slice(-8)}`;
}
