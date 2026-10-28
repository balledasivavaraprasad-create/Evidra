/** The review the menu links point at: the one in the URL, else the last one opened, else the demo. */
export const DEMO_WORKSPACE_ID = "ws-synth-001";
const STORAGE_KEY = "evidra-current-workspace";

export function workspaceIdFromPath(pathname: string): string | null {
  const match = pathname.match(/^\/reviews\/([^/]+)/);
  return match ? decodeURIComponent(match[1]) : null;
}

export function getRememberedWorkspaceId(): string {
  try {
    return localStorage.getItem(STORAGE_KEY) || DEMO_WORKSPACE_ID;
  } catch {
    return DEMO_WORKSPACE_ID;
  }
}

export function rememberWorkspaceId(id: string): void {
  try {
    localStorage.setItem(STORAGE_KEY, id);
  } catch {
    /* storage unavailable: menu falls back to the demo review */
  }
}
