import type { CriterionDefinition } from "../../api/client";

export type KeywordKind = "keywords" | "exclude_keywords";

/** The PICO fields the rules are built from. */
export interface PicoFields {
  population?: string;
  intervention?: string;
  comparator?: string;
  outcome?: string;
}

/** Enough to build useful rules: who was studied and what was done to them. */
export function picoIsReady(pico: PicoFields): boolean {
  return !!(pico.population?.trim() && pico.intervention?.trim());
}

/** "a, b; c" typed into a keyword box becomes separate keywords. */
export function parseKeywordInput(text: string): string[] {
  return text
    .split(/[,;\n]/)
    .map((t) => t.replace(/\s+/g, " ").trim())
    .filter(Boolean);
}

/** Rules that are matched by their keywords; the topic-neutral ones use built-in checks. */
export function usesKeywords(rule: CriterionDefinition): boolean {
  return rule.source !== "generic" || (rule.keywords?.length ?? 0) > 0 || (rule.exclude_keywords?.length ?? 0) > 0;
}

export function addKeywords(
  rules: CriterionDefinition[],
  ruleId: string,
  kind: KeywordKind,
  input: string,
): CriterionDefinition[] {
  const added = parseKeywordInput(input);
  if (added.length === 0) return rules;
  return rules.map((r) => {
    if (r.id !== ruleId) return r;
    const have = r[kind] ?? [];
    const known = new Set(have.map((k) => k.toLowerCase()));
    const fresh = added.filter((k, i) => !known.has(k.toLowerCase()) && added.findIndex((x) => x.toLowerCase() === k.toLowerCase()) === i);
    return fresh.length ? { ...r, [kind]: [...have, ...fresh] } : r;
  });
}

export function removeKeyword(
  rules: CriterionDefinition[],
  ruleId: string,
  kind: KeywordKind,
  keyword: string,
): CriterionDefinition[] {
  return rules.map((r) => {
    if (r.id !== ruleId) return r;
    const next = { ...r, [kind]: (r[kind] ?? []).filter((k) => k !== keyword) };
    if (kind === "keywords") next.ai_suggested_keywords = (r.ai_suggested_keywords ?? []).filter((k) => k !== keyword);
    return next;
  });
}

export function removeRule(rules: CriterionDefinition[], ruleId: string): CriterionDefinition[] {
  return rules.filter((r) => r.id !== ruleId);
}

/** A reviewer's own rule. Its id never collides with an existing one. */
export function addCustomRule(
  rules: CriterionDefinition[],
  name: string,
  isInclusion: boolean,
  keywordsText: string,
): CriterionDefinition[] {
  const keywords = parseKeywordInput(keywordsText);
  const title = name.trim();
  if (!title || keywords.length === 0) return rules;
  let n = rules.filter((r) => r.source === "custom").length + 1;
  while (rules.some((r) => r.id === `custom_${n}`)) n += 1;
  return [
    ...rules,
    {
      id: `custom_${n}`,
      name: title,
      category: "custom",
      is_inclusion: isInclusion,
      rationale: isInclusion
        ? "Added by the reviewer: the title or abstract should mention one of these terms."
        : "Added by the reviewer: exclude a record that mentions one of these terms.",
      metadata_first: false,
      keywords,
      exclude_keywords: [],
      source: "custom",
      ai_suggested_keywords: [],
    },
  ];
}

/** Why these rules can't be saved yet, or null. */
export function validateRules(rules: CriterionDefinition[]): string | null {
  if (rules.length === 0) return "Add at least one screening rule, or generate them from your question.";
  const empty = rules.find((r) => r.source !== "generic" && (r.keywords?.length ?? 0) === 0);
  if (empty) return `Add at least one keyword to “${empty.name}”, or remove that rule.`;
  return null;
}

export function isAiKeyword(rule: CriterionDefinition, keyword: string): boolean {
  return (rule.ai_suggested_keywords ?? []).includes(keyword);
}
