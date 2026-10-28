import { describe, it, expect } from "vitest";
import {
  compileClauseToAST,
  astToReadableString,
  isValidDateFormat,
  type QueryGroupClause,
} from "../features/search/astCompiler";

describe("astCompiler", () => {
  describe("isValidDateFormat", () => {
    it("accepts valid publication years and ISO dates", () => {
      expect(isValidDateFormat("2024")).toBe(true);
      expect(isValidDateFormat("2024-05")).toBe(true);
      expect(isValidDateFormat("2024-05-18")).toBe(true);
      expect(isValidDateFormat("")).toBe(true); // optional empty
    });

    it("rejects invalid date strings", () => {
      expect(isValidDateFormat("invalid-date")).toBe(false);
      expect(isValidDateFormat("24")).toBe(false);
      expect(isValidDateFormat("2024-13")).toBe(false); // invalid month
      expect(isValidDateFormat("2024-05-32")).toBe(false); // invalid day
      expect(isValidDateFormat("2024/05/18")).toBe(false); // wrong delimiter
    });
  });

  describe("compileClauseToAST", () => {
    it("compiles a single group with single term into a leaf AST node", () => {
      const groups: QueryGroupClause[] = [
        {
          id: "g1",
          operator: "OR",
          clauses: [{ id: "c1", field: "all", term: "metformin" }],
        },
      ];

      const ast = compileClauseToAST(groups, "AND");
      expect(ast.term).toBe("metformin");
      expect(ast.operator).toBeNull();
      expect(ast.children).toBeNull();
    });

    it("compiles multiple terms within a group using the group operator", () => {
      const groups: QueryGroupClause[] = [
        {
          id: "g1",
          operator: "OR",
          clauses: [
            { id: "c1", field: "all", term: "metformin" },
            { id: "c2", field: "all", term: "glucophage" },
          ],
        },
      ];

      const ast = compileClauseToAST(groups, "AND");
      expect(ast.operator).toBe("OR");
      expect(ast.children).toHaveLength(2);
      expect(ast.children![0].term).toBe("metformin");
      expect(ast.children![1].term).toBe("glucophage");
    });

    it("compiles multi-group Boolean queries with inter-group operator", () => {
      const groups: QueryGroupClause[] = [
        {
          id: "g1",
          operator: "OR",
          clauses: [
            { id: "c1", field: "all", term: "metformin" },
            { id: "c2", field: "all", term: "glucophage" },
          ],
        },
        {
          id: "g2",
          operator: "OR",
          clauses: [
            { id: "c3", field: "all", term: "type 2 diabetes" },
            { id: "c4", field: "all", term: "T2D" },
          ],
        },
      ];

      const ast = compileClauseToAST(groups, "AND");
      expect(ast.operator).toBe("AND");
      expect(ast.children).toHaveLength(2);
      expect(ast.children![0].operator).toBe("OR");
      expect(ast.children![1].operator).toBe("OR");
    });

    it("ignores whitespace-only empty terms", () => {
      const groups: QueryGroupClause[] = [
        {
          id: "g1",
          operator: "AND",
          clauses: [
            { id: "c1", field: "all", term: "metformin" },
            { id: "c2", field: "all", term: "   " },
          ],
        },
      ];

      const ast = compileClauseToAST(groups, "AND");
      expect(ast.term).toBe("metformin");
      expect(ast.children).toBeNull();
    });

    it("falls back to wildcard if all groups are empty", () => {
      const groups: QueryGroupClause[] = [
        {
          id: "g1",
          operator: "OR",
          clauses: [{ id: "c1", field: "all", term: "" }],
        },
      ];

      const ast = compileClauseToAST(groups, "AND");
      expect(ast.term).toBe("*");
    });
  });

  describe("astToReadableString", () => {
    it("renders simple leaf terms and quotes multi-word phrases", () => {
      expect(astToReadableString({ term: "metformin", operator: null, children: null })).toBe("metformin");
      expect(astToReadableString({ term: "type 2 diabetes", operator: null, children: null })).toBe('"type 2 diabetes"');
    });

    it("renders grouped Boolean expressions with parentheses", () => {
      const ast = {
        operator: "AND" as const,
        children: [
          {
            operator: "OR" as const,
            children: [
              { term: "metformin", operator: null, children: null },
              { term: "glucophage", operator: null, children: null },
            ],
          },
          {
            operator: "OR" as const,
            children: [
              { term: "type 2 diabetes", operator: null, children: null },
              { term: "T2D", operator: null, children: null },
            ],
          },
        ],
      };

      const readable = astToReadableString(ast);
      expect(readable).toBe('(metformin OR glucophage) AND ("type 2 diabetes" OR T2D)');
    });
  });
});
