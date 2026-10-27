/**
 * Exact Unicode code-point offset conversions for PICO text annotations.
 * 
 * In JavaScript, string.length and DOM selection offsets operate in UTF-16 code units.
 * The backend domain invariant requires half-open Unicode code-point offsets [start_cp, end_cp).
 */

/**
 * Convert a UTF-16 string index (as returned by DOM selection or indexOf) to a Unicode code-point index.
 */
export function utf16ToCodePoint(text: string, utf16Offset: number): number {
  if (utf16Offset <= 0) return 0;
  if (utf16Offset >= text.length) return Array.from(text).length;
  return Array.from(text.slice(0, utf16Offset)).length;
}

/**
 * Convert a Unicode code-point index to a UTF-16 string index for DOM rendering or substring slicing.
 */
export function codePointToUtf16(text: string, codePointOffset: number): number {
  if (codePointOffset <= 0) return 0;
  const chars = Array.from(text);
  if (codePointOffset >= chars.length) return text.length;
  return chars.slice(0, codePointOffset).join("").length;
}

/**
 * Extract a substring using half-open Unicode code-point indices [startCp, endCp).
 */
export function sliceByCodePoints(text: string, startCp: number, endCp: number): string {
  if (startCp >= endCp) return "";
  return Array.from(text).slice(startCp, endCp).join("");
}

/**
 * Compute SHA-256 hex digest of a UTF-8 string matching the backend validator.
 */
export async function computeTextHash(text: string): Promise<string> {
  const encoder = new TextEncoder();
  const data = encoder.encode(text);
  const hashBuffer = await crypto.subtle.digest("SHA-256", data);
  const hashArray = Array.from(new Uint8Array(hashBuffer));
  return hashArray.map((b) => b.toString(16).padStart(2, "0")).join("");
}

/**
 * Validate that a span quote strictly matches the code-point slice of the source text.
 */
export function validateSpanQuote(text: string, startCp: number, endCp: number, expectedQuote: string): boolean {
  const actualQuote = sliceByCodePoints(text, startCp, endCp);
  return actualQuote === expectedQuote;
}
