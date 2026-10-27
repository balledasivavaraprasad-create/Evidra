import type { PaperGroupSummary, PaperGroupDetail, DedupProposal } from "./client";

export const MOCK_GROUPS: PaperGroupSummary[] = [
  {
    id: "grp-001",
    workspace_id: "ws-demo-01",
    member_count: 2,
    effective_status: "include",
    has_conflict: false,
    has_human_decision: true,
    last_decision_at: "2026-10-27T10:00:00Z",
    representative_revision: {
      id: "rec-synth-0001",
      source_record_id: "src-synth-0001",
      source: "pubmed",
      source_namespace: "pubmed",
      external_id: "38100001",
      content_hash: "a1b2c3d4",
      title: "Efficacy of metformin versus placebo in type 2 diabetes: a randomized controlled trial",
      abstract_text:
        "Background: In adults with type 2 diabetes, metformin is commonly used as first-line therapy. " +
        "Methods: A randomized double-blind placebo-controlled trial evaluated metformin versus placebo over 24 weeks. " +
        "Results: Patients receiving metformin achieved a statistically significant reduction in HbA1c of 1.1%. " +
        "Conclusion: Metformin monotherapy significantly improves glycemic control compared with placebo.",
      authors: ["Miller AB", "Davis KR", "Chen L"],
      year: 2024,
      journal: "New England Journal of Medicine",
      pages: "101-110",
      language: ["eng"],
      publication_types: ["Randomized Controlled Trial"],
      doi: "10.1056/nejmoa2024001",
      pmid: "38100001",
      metadata_json: {},
      fetched_at: "2026-10-27T00:00:00Z",
    },
  },
  {
    id: "grp-002",
    workspace_id: "ws-demo-01",
    member_count: 1,
    effective_status: "exclude",
    has_conflict: false,
    has_human_decision: false,
    last_decision_at: null,
    representative_revision: {
      id: "rec-synth-0005",
      source_record_id: "src-synth-0005",
      source: "pubmed",
      source_namespace: "pubmed",
      external_id: "38100005",
      content_hash: "e5f6a7b8",
      title: "Metformin modulates hepatic glucose output in diabetic Wistar rats",
      abstract_text:
        "Objective: To study the effect of metformin on hepatic gluconeogenesis in male Wistar rats. " +
        "Methods: Rats were treated with metformin (100 mg/kg) daily for 4 weeks. " +
        "Results: Rat liver tissue showed down-regulated PEPCK expression.",
      authors: ["Patel R", "Gupta V"],
      year: 2023,
      journal: "Journal of Endocrinology",
      pages: "215-224",
      language: ["eng"],
      publication_types: ["Animal Study"],
      doi: "10.1530/joe-2023-005",
      pmid: "38100005",
      metadata_json: {},
      fetched_at: "2026-10-27T00:00:00Z",
    },
  },
  {
    id: "grp-003",
    workspace_id: "ws-demo-01",
    member_count: 2,
    effective_status: "conflict",
    has_conflict: true,
    has_human_decision: true,
    last_decision_at: "2026-10-27T09:30:00Z",
    representative_revision: {
      id: "rec-synth-0010",
      source_record_id: "src-synth-0010",
      source: "pubmed",
      source_namespace: "pubmed",
      external_id: "38100010",
      content_hash: "c9d8e7f6",
      title: "Metformin in prediabetes: 5-year follow-up of glycemic parameters",
      abstract_text:
        "Context: Long-term outcomes of metformin in adults with impaired fasting glucose. " +
        "Design: Extended observational cohort of 450 prediabetic adults. " +
        "Findings: Metformin delayed progression to overt type 2 diabetes by 31%.",
      authors: ["Evans D", "Whitehead J"],
      year: 2022,
      journal: "Diabetes Care",
      pages: "88-95",
      language: ["eng"],
      publication_types: ["Observational Study"],
      doi: "10.2337/dc22-0010",
      pmid: "38100010",
      metadata_json: {},
      fetched_at: "2026-10-27T00:00:00Z",
    },
  },
];
