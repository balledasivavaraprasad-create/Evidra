"""Synthetic biomedical literature fixtures for testing contracts, deduplication, screening, and PICO."""
import hashlib
from datetime import UTC, datetime


def compute_hash(text: str) -> str:
    """Calculate SHA-256 fingerprint for text."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


# 1. Exact Duplicate Pair (PubMed + Europe PMC)
TEXT_EXACT_A = (
    "Background: In adults with type 2 diabetes, metformin is commonly used as first-line therapy. "
    "Methods: A randomized double-blind placebo-controlled trial evaluated metformin versus placebo over 24 weeks. "
    "Results: Patients receiving metformin achieved a statistically significant reduction in HbA1c of 1.1%. "
    "Conclusion: Metformin monotherapy significantly improves glycemic control compared with placebo."
)

RECORD_EXACT_PUBMED = {
    "id": "rec-synth-0001",
    "source_record_id": "src-synth-0001",
    "source": "pubmed",
    "source_namespace": "pubmed",
    "external_id": "38100001",
    "content_hash": compute_hash(TEXT_EXACT_A),
    "title": "Efficacy of metformin versus placebo in type 2 diabetes: a randomized controlled trial",
    "abstract_text": TEXT_EXACT_A,
    "authors": ["Miller AB", "Davis KR", "Chen L"],
    "year": 2024,
    "journal": "New England Journal of Medicine",
    "pages": "101-110",
    "language": ["eng"],
    "publication_types": ["Randomized Controlled Trial"],
    "doi": "10.1056/nejmoa2024001",
    "pmid": "38100001",
    "metadata_json": {"mesh_headings": ["Diabetes Mellitus, Type 2", "Metformin", "Glycated Hemoglobin"]},
    "fetched_at": datetime(2026, 10, 27, 0, 0, 0, tzinfo=UTC),
}

RECORD_EXACT_EUROPEPMC = {
    "id": "rec-synth-0002",
    "source_record_id": "src-synth-0002",
    "source": "europepmc",
    "source_namespace": "europepmc",
    "external_id": "PMC1099901",
    "content_hash": compute_hash(TEXT_EXACT_A),
    "title": "Efficacy of metformin versus placebo in type 2 diabetes: a randomized controlled trial",
    "abstract_text": TEXT_EXACT_A,
    "authors": ["Miller A.B.", "Davis K.R.", "Chen L."],
    "year": 2024,
    "journal": "N Engl J Med",
    "pages": "101-110",
    "language": ["en"],
    "publication_types": ["Clinical Trial"],
    "doi": "10.1056/nejmoa2024001",
    "pmid": "38100001",
    "metadata_json": {"source": "MED"},
    "fetched_at": datetime(2026, 10, 27, 0, 0, 0, tzinfo=UTC),
}

# 2. Uncertain Duplicate Pair (Author variant & punctuation change, no DOI)
TEXT_UNCERTAIN = (
    "Objective: To investigate whether oral metformin decreases hemoglobin A1c in diabetic adults. "
    "Design: Comparative cohort study comparing metformin to lifestyle intervention alone. "
    "Findings: Metformin group exhibited lower HbA1c at 6 months follow-up."
)

RECORD_UNCERTAIN_A = {
    "id": "rec-synth-0003",
    "source_record_id": "src-synth-0003",
    "source": "pubmed",
    "source_namespace": "pubmed",
    "external_id": "38100003",
    "content_hash": compute_hash(TEXT_UNCERTAIN),
    "title": "Metformin therapy in type 2 diabetes - a prospective evaluation",
    "abstract_text": TEXT_UNCERTAIN,
    "authors": ["Johnson SM", "Taylor W"],
    "year": 2023,
    "journal": "Diabetes Care",
    "pages": "45-52",
    "language": ["eng"],
    "publication_types": ["Journal Article"],
    "doi": None,
    "pmid": "38100003",
    "metadata_json": {},
    "fetched_at": datetime(2026, 10, 27, 0, 0, 0, tzinfo=UTC),
}

RECORD_UNCERTAIN_B = {
    "id": "rec-synth-0004",
    "source_record_id": "src-synth-0004",
    "source": "europepmc",
    "source_namespace": "europepmc",
    "external_id": "PPR123456",
    "content_hash": compute_hash(TEXT_UNCERTAIN),
    "title": "Metformin therapy in type 2 diabetes: a prospective evaluation",
    "abstract_text": TEXT_UNCERTAIN,
    "authors": ["Johnson Samuel M", "Taylor William"],
    "year": 2023,
    "journal": "Diabetes Care",
    "pages": "45-52",
    "language": ["eng"],
    "publication_types": ["Article"],
    "doi": None,
    "pmid": None,
    "metadata_json": {},
    "fetched_at": datetime(2026, 10, 27, 0, 0, 0, tzinfo=UTC),
}

# 3. Same Clinical Study, Distinct Reports (Negative Duplicate Pair)
TEXT_PROTOCOL = (
    "Protocol: Design and rationale of the MET-DIAB trial (NCT04567890). "
    "A multicenter randomized trial assessing metformin vs glipizide in newly diagnosed adults. "
    "Primary endpoint will be HbA1c at 52 weeks."
)
RECORD_SAME_STUDY_PROTOCOL = {
    "id": "rec-synth-0005",
    "source_record_id": "src-synth-0005",
    "source": "pubmed",
    "source_namespace": "pubmed",
    "external_id": "38100005",
    "content_hash": compute_hash(TEXT_PROTOCOL),
    "title": "Study design and baseline characteristics of the MET-DIAB trial (NCT04567890)",
    "abstract_text": TEXT_PROTOCOL,
    "authors": ["Garcia E", "Adams J"],
    "year": 2021,
    "journal": "Trials",
    "pages": "12",
    "language": ["eng"],
    "publication_types": ["Study Protocol"],
    "doi": "10.1186/s13063-021-05001-x",
    "pmid": "38100005",
    "metadata_json": {"clinical_trial_number": "NCT04567890"},
    "fetched_at": datetime(2026, 10, 27, 0, 0, 0, tzinfo=UTC),
}

TEXT_RESULTS = (
    "Results: Primary findings from the MET-DIAB trial (NCT04567890). "
    "In 800 adults with type 2 diabetes, metformin reduced HbA1c by 1.2% versus 0.8% with glipizide. "
    "Hypoglycemia incidence was significantly lower with metformin."
)
RECORD_SAME_STUDY_RESULTS = {
    "id": "rec-synth-0006",
    "source_record_id": "src-synth-0006",
    "source": "pubmed",
    "source_namespace": "pubmed",
    "external_id": "38100006",
    "content_hash": compute_hash(TEXT_RESULTS),
    "title": "Metformin versus glipizide in type 2 diabetes: primary results of the MET-DIAB trial",
    "abstract_text": TEXT_RESULTS,
    "authors": ["Garcia E", "Adams J", "Roberts C"],
    "year": 2023,
    "journal": "The Lancet",
    "pages": "220-230",
    "language": ["eng"],
    "publication_types": ["Randomized Controlled Trial"],
    "doi": "10.1016/s0140-6736(23)00123-4",
    "pmid": "38100006",
    "metadata_json": {"clinical_trial_number": "NCT04567890"},
    "fetched_at": datetime(2026, 10, 27, 0, 0, 0, tzinfo=UTC),
}

TEXT_FOLLOWUP = (
    "Follow-up: 5-year microvascular outcomes of participants in the MET-DIAB trial (NCT04567890). "
    "Sustained glycemic durability and reduced retinopathy risk observed in metformin cohort."
)
RECORD_SAME_STUDY_FOLLOWUP = {
    "id": "rec-synth-0007",
    "source_record_id": "src-synth-0007",
    "source": "pubmed",
    "source_namespace": "pubmed",
    "external_id": "38100007",
    "content_hash": compute_hash(TEXT_FOLLOWUP),
    "title": "Five-year durability and microvascular outcomes from the MET-DIAB cohort",
    "abstract_text": TEXT_FOLLOWUP,
    "authors": ["Roberts C", "Garcia E"],
    "year": 2025,
    "journal": "Lancet Diabetes & Endocrinology",
    "pages": "50-60",
    "language": ["eng"],
    "publication_types": ["Journal Article"],
    "doi": "10.1016/s2213-8587(25)00010-1",
    "pmid": "38100007",
    "metadata_json": {"clinical_trial_number": "NCT04567890"},
    "fetched_at": datetime(2026, 10, 27, 0, 0, 0, tzinfo=UTC),
}

# 4. Missing Data Records
RECORD_MISSING_ABSTRACT = {
    "id": "rec-synth-0008",
    "source_record_id": "src-synth-0008",
    "source": "pubmed",
    "source_namespace": "pubmed",
    "external_id": "38100008",
    "content_hash": compute_hash("Glycemic control in primary care diabetes"),
    "title": "Glycemic control in primary care diabetes",
    "abstract_text": None,
    "authors": ["White P"],
    "year": 2022,
    "journal": "BMJ",
    "pages": None,
    "language": ["eng"],
    "publication_types": ["Letter"],
    "doi": None,
    "pmid": "38100008",
    "metadata_json": {"note": "letter to editor, no abstract"},
    "fetched_at": datetime(2026, 10, 27, 0, 0, 0, tzinfo=UTC),
}

RECORD_MISSING_METADATA = {
    "id": "rec-synth-0009",
    "source_record_id": "src-synth-0009",
    "source": "europepmc",
    "source_namespace": "europepmc",
    "external_id": "PMC9999999",
    "content_hash": compute_hash("Metformin review in clinical practice"),
    "title": "Metformin review in clinical practice",
    "abstract_text": "Brief clinical overview of biguanides and insulin sensitizers in adult diabetes.",
    "authors": [],
    "year": None,
    "journal": None,
    "pages": None,
    "language": [],
    "publication_types": [],
    "doi": None,
    "pmid": None,
    "metadata_json": {},
    "fetched_at": datetime(2026, 10, 27, 0, 0, 0, tzinfo=UTC),
}

# 5. Exclusion Criteria Test Records
TEXT_ANIMAL = (
    "Objective: To assess hepatic gluconeogenesis suppression in male Sprague-Dawley rats. "
    "Methods: Rats were induced with streptozotocin and treated with metformin 250 mg/kg daily. "
    "Results: Metformin decreased blood glucose and hepatic enzyme expression in treated rodents."
)
RECORD_ANIMAL_STUDY = {
    "id": "rec-synth-0010",
    "source_record_id": "src-synth-0010",
    "source": "pubmed",
    "source_namespace": "pubmed",
    "external_id": "38100010",
    "content_hash": compute_hash(TEXT_ANIMAL),
    "title": "Metformin regulates gluconeogenic enzymes in streptozotocin-induced diabetic rats",
    "abstract_text": TEXT_ANIMAL,
    "authors": ["Kim H", "Park S"],
    "year": 2023,
    "journal": "Molecular and Cellular Endocrinology",
    "pages": "111-120",
    "language": ["eng"],
    "publication_types": ["Journal Article"],
    "doi": "10.1016/j.mce.2023.111900",
    "pmid": "38100010",
    "metadata_json": {"mesh_headings": ["Rats, Sprague-Dawley", "Animals"]},
    "fetched_at": datetime(2026, 10, 27, 0, 0, 0, tzinfo=UTC),
}

TEXT_SIMULATION = (
    "A computational docking and molecular dynamics simulation explored metformin interaction with AMPK. "
    "In silico binding energy was calculated at -7.8 kcal/mol. No human patients or living tissues were examined."
)
RECORD_SIMULATION_STUDY = {
    "id": "rec-synth-0011",
    "source_record_id": "src-synth-0011",
    "source": "europepmc",
    "source_namespace": "europepmc",
    "external_id": "PMC8888001",
    "content_hash": compute_hash(TEXT_SIMULATION),
    "title": "In silico molecular modeling of biguanide binding kinetics to human AMPK complex",
    "abstract_text": TEXT_SIMULATION,
    "authors": ["Novak V", "Ivanov D"],
    "year": 2024,
    "journal": "Journal of Computer-Aided Molecular Design",
    "pages": "301-315",
    "language": ["eng"],
    "publication_types": ["Comparative Study"],
    "doi": "10.1007/s10822-024-00500-1",
    "pmid": None,
    "metadata_json": {"mesh_headings": ["Molecular Dynamics Simulation", "Computer Simulation"]},
    "fetched_at": datetime(2026, 10, 27, 0, 0, 0, tzinfo=UTC),
}

TEXT_CASE_REPORT = (
    "We present a single case report of an 82-year-old female presenting with severe lactic acidosis "
    "associated with supratherapeutic metformin accumulation during acute kidney injury. Hemodialysis led to recovery."
)
RECORD_CASE_REPORT = {
    "id": "rec-synth-0012",
    "source_record_id": "src-synth-0012",
    "source": "pubmed",
    "source_namespace": "pubmed",
    "external_id": "38100012",
    "content_hash": compute_hash(TEXT_CASE_REPORT),
    "title": "Metformin-induced lactic acidosis in a patient with acute renal failure: a case report",
    "abstract_text": TEXT_CASE_REPORT,
    "authors": ["Lemoine G", "Dupond M"],
    "year": 2022,
    "journal": "American Journal of Case Reports",
    "pages": "e935000",
    "language": ["eng"],
    "publication_types": ["Case Reports"],
    "doi": "10.12659/ajcr.935000",
    "pmid": "38100012",
    "metadata_json": {"publication_types": ["Case Reports"]},
    "fetched_at": datetime(2026, 10, 27, 0, 0, 0, tzinfo=UTC),
}

# 6. Unicode Non-BMP and Greek Character Span Verification
TEXT_UNICODE = (
    "Clinical evaluation in adults with type 2 diabetes (T2D): metformin enhances β-cell preservation "
    "and suppresses α-glucosidase. Compared with placebo, metformin reduced mean HbA1c by 1.3% (p < 0.001) 💉."
)
RECORD_UNICODE_SPANS = {
    "id": "rec-synth-0013",
    "source_record_id": "src-synth-0013",
    "source": "pubmed",
    "source_namespace": "pubmed",
    "external_id": "38100013",
    "content_hash": compute_hash(TEXT_UNICODE),
    "title": "Metformin action on β-cell preservation and HbA1c in type 2 diabetes",
    "abstract_text": TEXT_UNICODE,
    "authors": ["Svensson E", "Björk T"],
    "year": 2024,
    "journal": "Acta Diabetologica",
    "pages": "201-209",
    "language": ["eng"],
    "publication_types": ["Randomized Controlled Trial"],
    "doi": "10.1007/s00592-024-02200-2",
    "pmid": "38100013",
    "metadata_json": {},
    "fetched_at": datetime(2026, 10, 27, 0, 0, 0, tzinfo=UTC),
}

# 7. Repeated Phrase Verification (Disambiguating First Match vs Specific Span)
TEXT_REPEATED = (
    "Metformin is widely prescribed. In this trial of metformin, metformin was given to adult diabetics. "
    "Placebo was compared to metformin; placebo showed no change, whereas metformin reduced HbA1c."
)
RECORD_REPEATED_PHRASES = {
    "id": "rec-synth-0014",
    "source_record_id": "src-synth-0014",
    "source": "pubmed",
    "source_namespace": "pubmed",
    "external_id": "38100014",
    "content_hash": compute_hash(TEXT_REPEATED),
    "title": "Dose response of metformin monotherapy in adults with diabetes",
    "abstract_text": TEXT_REPEATED,
    "authors": ["Lee K", "Tanaka H"],
    "year": 2023,
    "journal": "Diabetes Research and Clinical Practice",
    "pages": "77-85",
    "language": ["eng"],
    "publication_types": ["Clinical Trial"],
    "doi": "10.1016/j.diabres.2023.109999",
    "pmid": "38100014",
    "metadata_json": {},
    "fetched_at": datetime(2026, 10, 27, 0, 0, 0, tzinfo=UTC),
}

# 8. Single-Arm Study with Missing Comparator (Valid C Absent)
TEXT_SINGLE_ARM = (
    "A single-arm prospective trial investigated metformin extended-release in 120 adult diabetic patients. "
    "No comparator or control group was included. HbA1c declined from 8.4% to 7.2%."
)
RECORD_SINGLE_ARM_NO_COMPARATOR = {
    "id": "rec-synth-0015",
    "source_record_id": "src-synth-0015",
    "source": "pubmed",
    "source_namespace": "pubmed",
    "external_id": "38100015",
    "content_hash": compute_hash(TEXT_SINGLE_ARM),
    "title": "Open-label single-arm evaluation of metformin extended release",
    "abstract_text": TEXT_SINGLE_ARM,
    "authors": ["O'Connor B", "Morales F"],
    "year": 2022,
    "journal": "Clinical Therapeutics",
    "pages": "1400-1410",
    "language": ["eng"],
    "publication_types": ["Clinical Trial"],
    "doi": "10.1016/j.clinthera.2022.08.005",
    "pmid": "38100015",
    "metadata_json": {},
    "fetched_at": datetime(2026, 10, 27, 0, 0, 0, tzinfo=UTC),
}

# 9. Conflicting Decision Parent Pair (for Level 2 Merge Conflict)
RECORD_CONFLICT_A = {
    "id": "rec-synth-0016",
    "source_record_id": "src-synth-0016",
    "source": "pubmed",
    "source_namespace": "pubmed",
    "external_id": "38100016",
    "content_hash": compute_hash("Conflicting study report A on glycemic durability"),
    "title": "Glycemic durability of metformin versus sulfonylurea",
    "abstract_text": "Adult diabetic patients receiving metformin monotherapy experienced sustained HbA1c lowering.",
    "authors": ["Zhao Y", "Guo Q"],
    "year": 2024,
    "journal": "Diabetes Therapy",
    "pages": "120-130",
    "language": ["eng"],
    "publication_types": ["Comparative Study"],
    "doi": "10.1007/s13300-024-01500-1",
    "pmid": "38100016",
    "metadata_json": {"prior_human_decision": "include"},
    "fetched_at": datetime(2026, 10, 27, 0, 0, 0, tzinfo=UTC),
}

ALL_SYNTHETIC_RECORDS = [
    RECORD_EXACT_PUBMED,
    RECORD_EXACT_EUROPEPMC,
    RECORD_UNCERTAIN_A,
    RECORD_UNCERTAIN_B,
    RECORD_SAME_STUDY_PROTOCOL,
    RECORD_SAME_STUDY_RESULTS,
    RECORD_SAME_STUDY_FOLLOWUP,
    RECORD_MISSING_ABSTRACT,
    RECORD_MISSING_METADATA,
    RECORD_ANIMAL_STUDY,
    RECORD_SIMULATION_STUDY,
    RECORD_CASE_REPORT,
    RECORD_UNICODE_SPANS,
    RECORD_REPEATED_PHRASES,
    RECORD_SINGLE_ARM_NO_COMPARATOR,
    RECORD_CONFLICT_A,
]
