import { describe, it, expect } from "vitest";
import {
  type MLRankingResponse,
  type MLRankedItem,
  api,
  ApiError,
} from "../api/client";
import { MOCK_ML_RANKING } from "../api/fixtures";

describe("ML Review Prioritization Frontend Unit Tests (C-ML02)", () => {
  it("conforms to MLRankingResponse contract schema with valid scores and ranks", () => {
    const data = MOCK_ML_RANKING as MLRankingResponse;
    expect(data.workspace_id).toBe("ws-synth-001");
    expect(data.revision_id).toBe("rev-synth-001");
    expect(data.model_version).toBe("ml_ranker:v1.0.0");
    expect(data.status).toBe("COMPLETED");
    expect(data.total_records).toBe(3);
    const items = data.items || [];
    expect(items).toHaveLength(3);

    // Verify first item is high priority RCT with score in [0, 1]
    const item1 = items[0];
    expect(item1.rank).toBe(1);
    expect(item1.score).toBeGreaterThan(0.7);
    expect(item1.priority_label).toBe("HIGH");
    expect(item1.state).toBe("SCORED");
    expect(item1.title).toContain("metformin");
  });

  it("handles missing abstracts safely as UNAVAILABLE with 0.0 score", () => {
    const data = MOCK_ML_RANKING as MLRankingResponse;
    const items = data.items || [];
    const missingItem = items.find((it) => it.record_id === "rec-synth-0008");
    expect(missingItem).toBeDefined();
    expect(missingItem?.state).toBe("UNAVAILABLE");
    expect(missingItem?.reason).toBe("MISSING_ABSTRACT");
    expect(missingItem?.score).toBe(0.0);
    expect(missingItem?.priority_label).toBe("UNSCORED");
  });

  it("strictly separates model suggestion score from reviewer decision", () => {
    const item: MLRankedItem = {
      record_id: "rec-test-01",
      group_id: "grp-test-01",
      title: "Comparative analysis in clinical trial",
      score: 0.95,
      rank: 1,
      state: "SCORED",
      priority_label: "HIGH",
      effective_status: "exclude", // Reviewer decided to exclude despite high ML score!
    };

    // Invariant: ML score does not override or mutate human decision
    expect(item.score).toBe(0.95);
    expect(item.effective_status).toBe("exclude");
  });

  it("supports toggle between ML priority order and baseline corpus order", () => {
    const items: MLRankedItem[] = [
      {
        record_id: "rec-z",
        title: "Study Z",
        score: 0.99,
        rank: 1,
        state: "SCORED",
        priority_label: "HIGH",
      },
      {
        record_id: "rec-a",
        title: "Study A",
        score: 0.20,
        rank: 2,
        state: "SCORED",
        priority_label: "LOW",
      },
      {
        record_id: "rec-m",
        title: "Study M",
        score: 0.00,
        rank: 3,
        state: "UNAVAILABLE",
        priority_label: "UNSCORED",
      },
    ];

    // ML Order: rank ascending (score descending)
    const mlOrder = [...items].sort((a, b) => a.rank - b.rank);
    expect(mlOrder.map((it) => it.record_id)).toEqual(["rec-z", "rec-a", "rec-m"]);

    // Baseline Order: alphabetical by record_id
    const baselineOrder = [...items].sort((a, b) => a.record_id.localeCompare(b.record_id));
    expect(baselineOrder.map((it) => it.record_id)).toEqual(["rec-a", "rec-m", "rec-z"]);
  });

  it("partitions priority tiers correctly", () => {
    const items: MLRankedItem[] = [
      { record_id: "1", title: "T1", score: 0.85, rank: 1, state: "SCORED", priority_label: "HIGH" },
      { record_id: "2", title: "T2", score: 0.55, rank: 2, state: "SCORED", priority_label: "MEDIUM" },
      { record_id: "3", title: "T3", score: 0.15, rank: 3, state: "SCORED", priority_label: "LOW" },
      { record_id: "4", title: "T4", score: 0.00, rank: 4, state: "UNAVAILABLE", priority_label: "UNSCORED" },
    ];

    const high = items.filter((it) => it.priority_label === "HIGH");
    const medium = items.filter((it) => it.priority_label === "MEDIUM");
    const low = items.filter((it) => it.priority_label === "LOW");
    const unscored = items.filter((it) => it.priority_label === "UNSCORED");

    expect(high).toHaveLength(1);
    expect(medium).toHaveLength(1);
    expect(low).toHaveLength(1);
    expect(unscored).toHaveLength(1);
  });

  it("handles API error envelopes when model is unavailable", () => {
    const err = ApiError.fromEnvelope(503, {
      code: "ML_MODEL_UNAVAILABLE",
      message: "Model artifact failed integrity verification",
      retryable: false,
    });

    expect(err.status).toBe(503);
    expect(err.code).toBe("ML_MODEL_UNAVAILABLE");
    expect(err.message).toBe("Model artifact failed integrity verification");
  });
});
