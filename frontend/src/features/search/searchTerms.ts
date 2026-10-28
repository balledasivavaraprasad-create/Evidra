import type { CriteriaVersionResponse } from "../../api/client";

/**
 * Split one PICO field into separate search terms on commas, semicolons, " or ", "/" and
 * parentheses. "SGLT2 inhibitor, empagliflozin (Jardiance) or dapagliflozin" becomes
 * ["SGLT2 inhibitor", "empagliflozin", "Jardiance", "dapagliflozin"].
 */
export function splitPicoTerms(field: string | undefined | null): string[] {
  const seen = new Set<string>();
  const terms: string[] = [];
  for (const raw of (field ?? "").split(/[,;/()]|\s+or\s+/i)) {
    const term = raw.trim();
    const key = term.toLowerCase();
    if (term && !seen.has(key)) {
      seen.add(key);
      terms.push(term);
    }
  }
  return terms;
}

/**
 * Starting search terms for a review with no saved query: an OR-group for the intervention, then
 * one for the population, each term separate. With no PICO there is a single empty group, never
 * example terms.
 */
export function termsFromPico(crit: CriteriaVersionResponse | null): string[][] {
  const pico = (crit?.pico_description ?? {}) as Record<string, string>;
  const groups = [splitPicoTerms(pico.intervention), splitPicoTerms(pico.population)].filter((g) => g.length > 0);
  return groups.length ? groups : [[""]];
}
