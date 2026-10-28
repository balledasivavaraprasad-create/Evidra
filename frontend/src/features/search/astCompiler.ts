/** Helper functions for compiling, validating, and formatting Query AST nodes. */
import type { BooleanOperator, QueryASTNodeInput } from "../../api/client";

export interface QueryTermClause {
  id: string;
  field: "all" | "title_abstract" | "mesh";
  term: string;
}

export interface QueryGroupClause {
  id: string;
  operator: BooleanOperator;
  clauses: QueryTermClause[];
}

const DATE_REGEX = /^\d{4}(?:-(?:0[1-9]|1[0-2])(?:-(?:0[1-9]|[12]\d|3[01]))?)?$/;

export function isValidDateFormat(val: string): boolean {
  if (!val.trim()) return true;
  return DATE_REGEX.test(val.trim());
}

export function compileClauseToAST(groups: QueryGroupClause[], rootOperator: BooleanOperator = "AND"): QueryASTNodeInput {
  const groupNodes: QueryASTNodeInput[] = [];

  for (const grp of groups) {
    const validTerms = grp.clauses.filter((c) => c.term.trim().length > 0);
    if (validTerms.length === 0) continue;

    if (validTerms.length === 1) {
      groupNodes.push({
        term: validTerms[0].term.trim(),
        operator: null,
        children: null,
      });
    } else {
      groupNodes.push({
        operator: grp.operator,
        children: validTerms.map((c) => ({
          term: c.term.trim(),
          operator: null,
          children: null,
        })),
      });
    }
  }

  if (groupNodes.length === 0) {
    return {
      term: "*",
      operator: null,
      children: null,
    };
  }

  if (groupNodes.length === 1) {
    return groupNodes[0];
  }

  return {
    operator: rootOperator,
    children: groupNodes,
  };
}

export function astToReadableString(node: QueryASTNodeInput, isRoot: boolean = true): string {
  if (node.term) {
    return node.term.includes(" ") ? `"${node.term}"` : node.term;
  }

  if (!node.children || node.children.length === 0) {
    return "";
  }

  const op = node.operator || "AND";
  const childStrings = node.children.map((c) => astToReadableString(c, false)).filter(Boolean);

  if (childStrings.length === 1) {
    return childStrings[0];
  }

  const inner = childStrings.join(` ${op} `);
  return isRoot ? inner : `(${inner})`;
}

function isTermNode(node: QueryASTNodeInput): boolean {
  return typeof node.term === "string" && node.term.length > 0;
}

function termClauses(terms: string[], groupIndex: number): QueryTermClause[] {
  return terms.map((term, ci) => ({ id: `c-${groupIndex + 1}-${ci + 1}`, field: "all", term }));
}

/**
 * Inverse of compileClauseToAST: rebuild the builder's groups from a saved query's AST.
 *
 * Handles a lone term, a match-all "*" (no groups), a single flat group, and one level of
 * groups under a root operator. Returns null for anything nested deeper, which the builder
 * cannot show as groups. compileClauseToAST(astToGroups(ast)) gives back the same AST; the one
 * ambiguity is a root whose children are all bare terms, shown as a single group with that
 * operator (it compiles identically to separate one-term groups).
 */
export function astToGroups(
  ast: QueryASTNodeInput,
): { rootOperator: BooleanOperator; groups: QueryGroupClause[] } | null {
  // Lone term; "*" is how an empty query compiles
  if (isTermNode(ast)) {
    if (ast.term === "*") return { rootOperator: "AND", groups: [] };
    return { rootOperator: "AND", groups: [{ id: "grp-1", operator: "OR", clauses: termClauses([ast.term as string], 0) }] };
  }

  const children = ast.children ?? [];
  if (children.length === 0) return { rootOperator: "AND", groups: [] };
  const rootOperator = (ast.operator ?? "AND") as BooleanOperator;

  // Every child is a bare term: one group with the root's operator
  if (children.every(isTermNode)) {
    return {
      rootOperator: "AND",
      groups: [{ id: "grp-1", operator: rootOperator, clauses: termClauses(children.map((c) => c.term as string), 0) }],
    };
  }

  const groups: QueryGroupClause[] = [];
  for (const [gi, child] of children.entries()) {
    if (isTermNode(child)) {
      groups.push({ id: `grp-${gi + 1}`, operator: "OR", clauses: termClauses([child.term as string], gi) });
      continue;
    }
    const grandchildren = child.children ?? [];
    if (grandchildren.length === 0 || !grandchildren.every(isTermNode)) return null;
    groups.push({
      id: `grp-${gi + 1}`,
      operator: (child.operator ?? "OR") as BooleanOperator,
      clauses: termClauses(grandchildren.map((c) => c.term as string), gi),
    });
  }
  return { rootOperator, groups };
}
