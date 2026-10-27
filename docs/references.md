# Source register

Research date: **26 October 2026**. The supplied pre-read is authoritative for hackathon requirements; external sources inform engineering choices. Proposed architecture, thresholds, budgets and timelines are this project's design decisions, not claims made by the sources.

| Source | Checked material / how used | Limitations |
|---|---|---|
| `source/Track1_PS.pdf`, all pp.1–9 | Extracted all text and inspected rendered pages; pipeline, checkpoints, restrictions, loop requirements | Separate Scoring Metrics and kickoff materials absent |
| [NCBI E-utilities introduction](https://www.ncbi.nlm.nih.gov/books/NBK25497/) | Usage, tool/email registration, API rates and batch retrieval | Recheck operational registration before demo |
| [NCBI parameters](https://www.ncbi.nlm.nih.gov/books/NBK25499/) | Identified official parameter reference | Some direct requests hit a browser challenge; verify large-query behavior in integration |
| [Europe PMC REST](https://europepmc.org/RestfulWebService) | Official source for adapter configuration, search indexed documentation | Direct page/API inspection partly restricted; live smoke pending; do not assume defaults |
| [LangGraph persistence](https://docs.langchain.com/oss/python/langgraph/persistence) | Checkpointers vs application storage, durable state | API behavior must match locked package; online docs can advance |
| [LangGraph interrupts](https://docs.langchain.com/oss/python/langgraph/interrupts) | Human pause/resume, replay and idempotence | Persistent domain decisions remain separate |
| [LiteLLM guardrails](https://docs.litellm.ai/docs/proxy/guardrails/quick_start) | Optional pre/post-call policy integration | No deployment or provider behavior verified; proxy optional |
| [OWASP prompt injection](https://genai.owasp.org/llmrisk/llm01-prompt-injection/) | Untrusted retrieved content, deterministic checks and least privilege | Mitigations reduce risk; no guarantee of prompt immunity |
| [OWASP excessive agency](https://genai.owasp.org/llmrisk/llm062025-excessive-agency/) | Narrow tools, minimal authority and user-scoped execution | Application must enforce controls itself |
| [OpenAI harness engineering](https://openai.com/index/harness-engineering/) | Repository guidance, boundaries and feedback loops | Used as engineering inspiration, not an obligation to adopt its full workflow |
| [SYNERGY repository](https://github.com/asreview/synergy-dataset) | Dataset scope, label imbalance and repository license | No dataset downloaded or trained on |
| [EBM-NLP repository](https://github.com/bepnye/EBM-NLP) | PIO annotations, training/test provenance | Pre-read's restriction on redistribution retained; no C label assumed |
| [SQLite WAL](https://www.sqlite.org/wal.html) | Single-host storage and writer/concurrency considerations | Runtime engine version and deployment need verification |
| [uv locking/syncing](https://docs.astral.sh/uv/concepts/projects/sync/) | Frozen reproducible installation | Does not prove runtime behavior or security |
| [R3F installation](https://r3f.docs.pmnd.rs/getting-started/installation) | React/Fiber major-version pairing | npm peer resolution is the selected-version check |
| [R3F performance](https://r3f.docs.pmnd.rs/advanced/scaling-performance) | Demand rendering and resource reuse | Device-specific performance must be measured |
| [PyPI](https://pypi.org/) and [npm registry](https://registry.npmjs.org/) | Exact version and peer metadata; saved manifests/locks | Registry availability does not certify packages |

Visual sources and their inspection limits are recorded individually in [frontend-design.md](frontend-design.md), including Dribbble creator pages and Pinterest search-discovered leads. No source artwork was downloaded into the product or reused as a licensed asset.

Source reconciliation: the pre-read's Europe PMC default settings should be treated as event guidance but made explicit in implementation; the actual selected query options are persisted. EBM-NLP's event restriction remains binding for this project even if another mirror suggests different metadata. Unknown organizer requirements remain unknown rather than inferred from unrelated Rayyan product features.
