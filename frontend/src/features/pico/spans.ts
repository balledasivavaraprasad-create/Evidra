import type { PaperGroupDetail, PicoSpan } from "../../api/client";

type Detail = Pick<PaperGroupDetail, "group" | "pico_result" | "human_pico"> | null | undefined;

/** Whether this detail is the one for the group on screen (it loads a moment after the list). */
export function isDetailFor(detail: Detail, groupId: string | null | undefined): boolean {
  return !!detail && !!groupId && detail.group.id === groupId;
}

/**
 * The spans to show: the reviewer's own saved ones when they have edited (each edit stores the
 * complete list, so it replaces the machine's), otherwise what processing found.
 */
export function spansForViewer(detail: Detail): PicoSpan[] {
  if (!detail) return [];
  return detail.human_pico ?? detail.pico_result?.spans ?? [];
}

/** The abstract-text hash the server checks a PICO save against; null until the detail has loaded. */
export function textHashForSave(detail: Detail, groupId: string | null | undefined): string | null {
  return isDetailFor(detail, groupId) ? (detail?.pico_result?.content_hash ?? null) : null;
}
