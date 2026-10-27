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
