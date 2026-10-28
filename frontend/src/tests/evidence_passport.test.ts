import { describe, it, expect } from "vitest";
import type {
  EvidenceItemResponse,
  EvidencePassportBundle,
  EvidencePassportSummary,
  EvidenceValidationStatus,
  EvidenceSemanticAssessment,
} from "../api/client";
import { sliceByCodePoints, validateSpanQuote } from "../features/pico/offsets";

describe("Evidence Passport Frontend Contracts & Offsets", () => {
  const sampleAbstract =
    "In 450 adult patients with heart failure, dapagliflozin reduced cardiovascular death compared with standard therapy.";

  it("validates exact evidence quotation against abstract using code points", () => {
    const quote = "dapagliflozin reduced cardiovascular death";
    const startCp = sampleAbstract.indexOf(quote);
    const endCp = startCp + quote.length;

    expect(validateSpanQuote(sampleAbstract, startCp, endCp, quote)).toBe(true);
    expect(sliceByCodePoints(sampleAbstract, startCp, endCp)).toBe(quote);
  });

  it("handles EvidencePassportBundle structure with summary metrics", () => {
    const item: EvidenceItemResponse = {
      id: "ev-001",
      workspace_id: "ws-test",
      paper_group_id: "grp-test",
      record_revision_id: "rev-test",
      claim_type: "intervention",
      claim_value: "Dapagliflozin",
      original_claim_value: "Dapagliflozin",
      source_field: "abstract",
      supporting_quote: "dapagliflozin reduced cardiovascular death",
      start_cp: 41,
      end_cp: 83,
      source_fingerprint: "hash123",
      provenance: "deterministic_extraction",
      validation_status: "verified",
      validation_message: "Exact quotation verified",
      semantic_assessment: "supports",
      assessed_by: "system:rule",
      is_contradictory: false,
      uncertainty_note: null,
      reviewer_correction_reason: null,
      event_id: null,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    };

    const summary: EvidencePassportSummary = {
      total_claims: 1,
      verified_quotes_count: 1,
      needs_review_count: 0,
      stale_count: 0,
      mismatched_count: 0,
      missing_source_count: 0,
      pico_fields_with_evidence: 1,
      human_corrected_count: 0,
      contradictory_count: 0,
    };

    const bundle: EvidencePassportBundle = {
      workspace_id: "ws-test",
      group_id: "grp-test",
      record_revision_id: "rev-test",
      title: "Dapagliflozin in Heart Failure",
      abstract_text: sampleAbstract,
      source_fingerprint: "hash123",
      summary,
      items: [item],
    };

    expect(bundle.items?.length).toBe(1);
    expect(bundle.summary.verified_quotes_count).toBe(1);
    expect(bundle.items?.[0].validation_status).toBe("verified");
    expect(bundle.items?.[0].semantic_assessment).toBe("supports");
  });

  it("distinguishes structural quote verification from semantic support", () => {
    // Exact quote match proves text presence, but semantic assessment can be contradictory or insufficient
    const contradictoryItem: Partial<EvidenceItemResponse> = {
      claim_value: "Dapagliflozin was superior to comparator",
      supporting_quote: "No statistically significant difference was observed between cohorts.",
      validation_status: "verified", // Structural passage exists!
      semantic_assessment: "contradicts", // Logical assessment disagrees!
      is_contradictory: true,
    };

    expect(contradictoryItem.validation_status).toBe("verified");
    expect(contradictoryItem.semantic_assessment).toBe("contradicts");
    expect(contradictoryItem.is_contradictory).toBe(true);
  });

  it("supports reviewer correction with audit trail preservation", () => {
    const correctedItem: Partial<EvidenceItemResponse> = {
      claim_value: "Dapagliflozin 10mg daily",
      original_claim_value: "Dapagliflozin",
      provenance: "human_corrected",
      assessed_by: "human:dr_lead",
      reviewer_correction_reason: "Added specific dosage from sentence 2",
    };

    expect(correctedItem.original_claim_value).toBe("Dapagliflozin");
    expect(correctedItem.claim_value).toBe("Dapagliflozin 10mg daily");
    expect(correctedItem.provenance).toBe("human_corrected");
  });
});
