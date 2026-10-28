/**
 * The review the menu links point at: the one in the URL, else the last one this browser opened.
 * There is no fallback review: with nothing remembered the menu sends people to their dashboard,
 * so work never lands in someone else's (or a demo) review by accident.
 */
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

export function getRememberedWorkspaceId(): string | null {
  return readStoredWorkspaceId();
}

export function rememberWorkspaceId(id: string): void {
  try {
    localStorage.setItem(STORAGE_KEY, id);
  } catch {
    /* storage unavailable: menu links fall back to the dashboard */
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
 * Check the remembered review against the signed-in user's reviews. One that isn't theirs
 * (another account used this browser, or it was deleted) is forgotten.
 */
export function reconcileRememberedWorkspace(existingIds: readonly string[]): string | null {
  const stored = readStoredWorkspaceId();
  if (stored && existingIds.includes(stored)) return stored;
  if (stored) forgetWorkspaceId();
  return null;
}
