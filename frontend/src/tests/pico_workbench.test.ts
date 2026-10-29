import { describe, expect, it } from "vitest";
import type { PaperGroupDetail, PicoSpan } from "../api/client";
import { isDetailFor, spansForViewer, textHashForSave } from "../features/pico/spans";

const span = (label: PicoSpan["label"], start: number, end: number, quote: string, provenance = "rule:pico:v1.0"): PicoSpan => ({
  label,
  start_cp: start,
  end_cp: end,
  quote,
  provenance,
});

const machine = [span("P", 0, 5, "adult"), span("I", 10, 20, "empagliflozin")];

const detail = (over: Partial<PaperGroupDetail> = {}, groupId = "g1"): PaperGroupDetail =>
  ({
    group: { id: groupId },
    members: [],
    events: [],
    conflicts: [],
    pico_result: { record_revision_id: "r1", content_hash: "text-hash-1", spans: machine },
    human_pico: null,
    ...over,
  }) as unknown as PaperGroupDetail;

describe("which PICO spans the workbench shows", () => {
  it("shows what processing found when nobody has edited", () => {
    expect(spansForViewer(detail())).toEqual(machine);
  });

  it("shows the reviewer's saved spans instead once they have edited", () => {
    const saved = [span("O", 30, 40, "hospitalization", "human_override")];
    expect(spansForViewer(detail({ human_pico: saved }))).toEqual(saved);
  });

  it("an edit that removed every span stays removed: it is not 'never edited'", () => {
    expect(spansForViewer(detail({ human_pico: [] }))).toEqual([]);
  });

  it("shows nothing, rather than failing, when there is no detail or no PICO result", () => {
    expect(spansForViewer(null)).toEqual([]);
    expect(spansForViewer(undefined)).toEqual([]);
    expect(spansForViewer(detail({ pico_result: null }))).toEqual([]);
  });
});

describe("saving PICO against the right paper's text hash", () => {
  it("uses the abstract-text hash from this paper's detail", () => {
    expect(textHashForSave(detail(), "g1")).toBe("text-hash-1");
  });

  it("refuses to use another paper's detail while this one is still loading", () => {
    expect(isDetailFor(detail({}, "g1"), "g2")).toBe(false);
    expect(textHashForSave(detail({}, "g1"), "g2")).toBeNull();
    expect(textHashForSave(null, "g1")).toBeNull();
  });
});
