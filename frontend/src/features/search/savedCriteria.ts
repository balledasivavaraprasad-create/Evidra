import { api, ApiError, type CriteriaVersionResponse } from "../../api/client";

// The demo seed stores PICO under one-letter keys; the editor reads the long names.
const LONG_PICO_KEYS: Record<string, string> = {
  P: "population",
  I: "intervention",
  C: "comparator",
  O: "outcome",
};

function withLongPicoKeys(pico: Record<string, string>): Record<string, string> {
  const out: Record<string, string> = {};
  for (const [key, value] of Object.entries(pico)) {
    const longKey = LONG_PICO_KEYS[key] ?? key;
    if (!(longKey in out) || longKey === key) out[longKey] = value;
  }
  return out;
}

/** The newest saved review question for a workspace, or null when none has been saved yet. */
export async function loadSavedCriteria(workspaceId: string): Promise<CriteriaVersionResponse | null> {
  try {
    const saved = await api.criteria.latest(workspaceId);
    return { ...saved, pico_description: withLongPicoKeys(saved.pico_description) };
  } catch (err) {
    if (err instanceof ApiError && err.status === 404) return null;
    throw err;
  }
}
