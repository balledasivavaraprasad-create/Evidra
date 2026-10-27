# PICO Baseline Extraction & Offset Mapping Guide (C01)

## Overview & Architecture

The **C01 PICO baseline** provides deterministic, zero-LLM evidence span extraction for clinical and biomedical literature abstracts. It extracts exact spans for:
- **P (Population):** Patient cohorts, demographics, medical conditions, and disease diagnoses.
- **I (Intervention):** Pharmacological agents, doses, formulations, and therapeutic interventions.
- **C (Comparator):** Active comparators, placebos, standard of care, or control arms.
- **O (Outcome):** Clinical endpoints, biochemical markers, physiological outcomes, and adverse events.

### Extraction Metadata
- **Extractor Method Version:** `pico_extractor:v1.0`
- **Rule Provenance Tag:** `rule:pico:v1.0`
- **Offset Definition:** Zero-based, half-open Unicode code points `[start_cp, end_cp)` where `quote == abstract_text[start_cp:end_cp]`.
- **Integrity Validation:** SHA-256 fingerprint verified against canonical `abstract_text`.

---

## Guide for dev-A: Unicode Code Points vs. Browser UTF-16 Offsets

JavaScript strings, the browser DOM, and `window.getSelection()` operate on **UTF-16 code units**, not Unicode code points. In contrast, Python 3 strings and backend persistence operate directly on **Unicode code points**.

### The Surrogate Pair Difference

1. **ASCII and BMP Characters (U+0000 to U+FFFF):**
   - Characters like English text, accented letters (`ö`), and Greek letters (`α`, `β`) occupy **1 Unicode code point** and **1 UTF-16 code unit**.
   - For pure BMP text, `code_point_offset == utf16_offset`.

2. **Non-BMP Characters / Emoji (U+10000 and above):**
   - Characters such as medical emojis (e.g., syringe `💉` `\U0001F489`) occupy **1 Unicode code point** in Python, but **2 UTF-16 code units** (a surrogate pair: `\uD83D\uDC89`) in JavaScript.
   - Any character following a non-BMP emoji will experience a +1 offset shift per emoji in JavaScript compared to Python.

### Example for Frontend Highlighting / Selection

Consider this text from `RECORD_UNICODE_SPANS` (`rec-synth-0013`):
```text
Clinical evaluation in adults with type 2 diabetes (T2D): metformin enhances β-cell preservation and suppresses α-glucosidase. Compared with placebo, metformin reduced mean HbA1c by 1.3% (p < 0.001) 💉.
```

- Text Length:
  - Python (Code Points): **196**
  - JavaScript (UTF-16 Units): **197** (due to `💉` at code point 194)

| Span Quote | Label | Python Code Points `[start_cp, end_cp)` | Browser UTF-16 `[start_utf16, end_utf16)` | Note |
|---|---|---|---|---|
| `"adults with type 2 diabetes"` | `P` | `[23, 50)` | `[23, 50)` | Identical (before emoji) |
| `"metformin"` | `I` | `[58, 67)` | `[58, 67)` | Identical (before emoji) |
| `"β-cell preservation"` | `O` | `[77, 98)` | `[77, 98)` | Greek `β` is in BMP; identical |
| `"α-glucosidase"` | `O` | `[114, 127)` | `[114, 127)` | Greek `α` is in BMP; identical |
| `"placebo"` | `C` | `[143, 150)` | `[143, 150)` | Identical (before emoji) |
| `"reduction in HbA1c"` (post-emoji hypothetical) | `O` | `[start_cp, end_cp)` | `[start_cp + 1, end_cp + 1)` | Shifted by +1 in UTF-16 |

### Conversion Functions Provided

The backend provides utility functions in `app.pico.offsets`:
```python
from app.pico.offsets import codepoint_to_utf16_offset, utf16_to_codepoint_offset, span_codepoint_to_utf16

# Convert when preparing payload for React component:
enriched_span = span_codepoint_to_utf16(abstract_text, span)
# Returns: {"label": "O", "start_cp": 77, "end_cp": 98, "start_utf16": 77, "end_utf16": 98, "quote": ...}

# Convert when receiving manual selection from React editor:
start_cp = utf16_to_codepoint_offset(abstract_text, selection.start_utf16)
end_cp = utf16_to_codepoint_offset(abstract_text, selection.end_utf16)
```

In the React frontend (`dev-A`), convert selection offsets using JavaScript:
```typescript
function utf16ToCodePointOffset(text: string, utf16Offset: number): number {
  let cpIndex = 0;
  for (let i = 0; i < utf16Offset; ) {
    const code = text.codePointAt(i);
    if (code === undefined) break;
    i += code > 0xffff ? 2 : 1;
    cpIndex++;
  }
  return cpIndex;
}
```

---

## Clinical Invariants & Absence Handling

1. **Absence of Comparator (Single-Arm Trials):**
   - When a trial evaluates a single intervention (e.g. `RECORD_SINGLE_ARM_NO_COMPARATOR` / `rec-synth-0015`), `has_comparator` is explicitly `false` and zero `C` spans are returned.
   - Clinical negation cues like `"No comparator or control group was included"` or `"without placebo"` are recognized and excluded from active comparator spans.
   - **Under no circumstances does the extractor invent a placebo or control.**

2. **Disambiguating Repeated Phrases:**
   - In abstracts where an intervention (e.g. `metformin`) is mentioned multiple times, the extractor outputs distinct `PicoSpan` entries for each occurrence, each with its unique `[start_cp, end_cp)`.
   - The editor can highlight all occurrences or let the reviewer select the primary mention without collision.

3. **Missing Abstract Text:**
   - When `abstract_text is None` or empty (e.g. `RECORD_MISSING_ABSTRACT` / `rec-synth-0008`), the extractor returns an empty span list and `has_population = has_intervention = has_comparator = has_outcome = False`.

4. **Measured Outcomes vs. Speculative Effect Claims:**
   - The baseline targets measured physiological and biochemical endpoints (e.g. `HbA1c`, `glycemic control`, `blood glucose`, `β-cell preservation`, `lactic acidosis`).
   - It avoids labeling broad speculative conclusions as factual outcomes.

---

## Baseline Limitations

1. **Syntactic Variation:** Highly irregular phrasing, novel acronyms, or non-standard abbreviations outside the rule set may yield `has_* = false`, requiring reviewer manual annotation or optional LLM extraction (C05).
2. **Multi-arm Complex Trials:** When more than two arms exist, all identified candidate comparators and interventions are extracted; grouping them into explicit comparison pairs is handled in higher-level review services.
