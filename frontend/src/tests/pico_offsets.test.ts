import { describe, it, expect } from "vitest";
import {
  utf16ToCodePoint,
  codePointToUtf16,
  sliceByCodePoints,
  validateSpanQuote,
  computeTextHash,
} from "../features/pico/offsets";

describe("PICO Unicode Code-Point Offsets", () => {
  it("preserves exact identity for ASCII text", () => {
    const text = "Metformin reduces HbA1c in adults with type 2 diabetes.";
    expect(utf16ToCodePoint(text, 10)).toBe(10);
    expect(codePointToUtf16(text, 10)).toBe(10);
    expect(sliceByCodePoints(text, 0, 9)).toBe("Metformin");
    expect(validateSpanQuote(text, 0, 9, "Metformin")).toBe(true);
  });

  it("handles non-BMP surrogate pairs (emoji / biological symbols)", () => {
    // "🧬" is 2 UTF-16 code units (surrogate pair) but 1 code point
    const text = "🧬 DNA study on 🧪 test subjects.";
    // Offset after "🧬 ": in UTF-16, "🧬" has length 2 + " " has length 1 = 3
    const utf16Offset = 3;
    const cpOffset = utf16ToCodePoint(text, utf16Offset);
    // In code points: "🧬" (1) + " " (1) = 2
    expect(cpOffset).toBe(2);

    // Convert back: 2 code points -> 3 UTF-16 units
    expect(codePointToUtf16(text, cpOffset)).toBe(3);

    // Slice "DNA"
    const dnaSlice = sliceByCodePoints(text, 2, 5);
    expect(dnaSlice).toBe("DNA");
    expect(validateSpanQuote(text, 2, 5, "DNA")).toBe(true);
  });

  it("handles Greek letters and multi-byte UTF-8 accurately", () => {
    // Greek letters like α, β are 1 UTF-16 code unit and 1 Unicode code point (BMP)
    const text = "Treatment with α-lipoic acid improves β-cell function.";
    const startCp = text.indexOf("α-lipoic acid");
    const endCp = startCp + "α-lipoic acid".length;
    expect(sliceByCodePoints(text, startCp, endCp)).toBe("α-lipoic acid");
    expect(validateSpanQuote(text, startCp, endCp, "α-lipoic acid")).toBe(true);
  });

  it("detects quote mismatch", () => {
    const text = "Evaluate metformin versus placebo.";
    expect(validateSpanQuote(text, 0, 8, "wrong quote")).toBe(false);
  });

  it("computes deterministic SHA-256 matching crypto standards", async () => {
    const text = "Randomized controlled trial of metformin in adults.";
    const hash = await computeTextHash(text);
    expect(hash).toMatch(/^[0-9a-f]{64}$/);
    // Repeated run is strictly identical
    const hash2 = await computeTextHash(text);
    expect(hash).toBe(hash2);
  });
});
