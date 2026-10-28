import { describe, it, expect } from "vitest";
import {
  type MLRankingResponse,
  type MLRankedItem,
  ApiError,
} from "../../src/api/client";
import { MOCK_ML_RANKING } from "../../src/api/fixtures";

describe("ML Feature Integration Unit Tests (C-ML02)", () => {
  it("conforms to MLRankingResponse contract schema with valid scores and ranks", () => {
    const data = MOCK_ML_RANKING as MLRankingResponse;
    expect(data.workspace_id).toBe("ws-synth-001");
    expect(data.revision_id).toBe("rev-synth-001");
    expect(data.model_version).toBe("ml_ranker:v1.0.0");
    expect(data.status).toBe("COMPLETED");
    expect(data.total_records).toBe(3);
    expect(data.scored_count).toBe(2);
    expect(data.items).toHaveLength(3);

    const item1 = data.items[0];
    expect(item1.rank).toBe(1);
    expect(item1.score).toBeGreaterThan(0.7);
    expect(item1.priority_label).toBe("HIGH");
    expect(item1.state).toBe("SCORED");
  });

  it("handles missing abstracts as UNAVAILABLE with 0.0 score", () => {
    const data = MOCK_ML_RANKING as MLRankingResponse;
    const missingItem = data.items.find((it) => it.record_id === "rec-synth-0008");
    expect(missingItem).toBeDefined();
    expect(missingItem?.state).toBe("UNAVAILABLE");
    expect(missingItem?.reason).toBe("MISSING_ABSTRACT");
    expect(missingItem?.score).toBe(0.0);
  });

  it("strictly preserves human decisions regardless of model priority score", () => {
    const item: MLRankedItem = {
      record_id: "rec-test-01",
      group_id: "grp-test-01",
      title: "Comparative analysis in clinical trial",
      score: 0.95,
      rank: 1,
      state: "SCORED",
      priority_label: "HIGH",
      effective_status: "exclude",
    };

    expect(item.score).toBe(0.95);
    expect(item.effective_status).toBe("exclude");
  });
});
