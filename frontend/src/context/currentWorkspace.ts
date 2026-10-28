/** The review the menu links point at: the one in the URL, else the last one opened, else the demo. */
export const DEMO_WORKSPACE_ID = "ws-synth-001";
const STORAGE_KEY = "evidra-current-workspace";

export function workspaceIdFromPath(pathname: string): string | null {
  const match = pathname.match(/^\/reviews\/([^/]+)/);
  return match ? decodeURIComponent(match[1]) : null;
}

function readStoredWorkspaceId(): string | null {
  try {
    return localStorage.getItem(STORAGE_KEY) || null;
  } catch {
    return null;
  }
}

export function getRememberedWorkspaceId(): string {
  return readStoredWorkspaceId() ?? DEMO_WORKSPACE_ID;
}

export function rememberWorkspaceId(id: string): void {
  try {
    localStorage.setItem(STORAGE_KEY, id);
  } catch {
    /* storage unavailable: menu falls back to the demo review */
  }
}

/** Forget the remembered review; with `onlyIf`, only when it is that exact review. */
export function forgetWorkspaceId(onlyIf?: string): void {
  try {
    if (onlyIf !== undefined && localStorage.getItem(STORAGE_KEY) !== onlyIf) return;
    localStorage.removeItem(STORAGE_KEY);
  } catch {
    /* storage unavailable: nothing was remembered anyway */
  }
}

/**
 * Check the remembered review against the reviews the server really has. A review that is gone
 * (for example after the server restarted with an empty database) is forgotten, and the demo is used.
 */
export function reconcileRememberedWorkspace(existingIds: readonly string[]): string {
  const stored = readStoredWorkspaceId();
  if (stored && existingIds.includes(stored)) return stored;
  if (stored) forgetWorkspaceId();
  return DEMO_WORKSPACE_ID;
}
