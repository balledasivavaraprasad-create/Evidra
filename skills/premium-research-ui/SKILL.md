---
name: premium-research-ui
description: Implement or refine the Mini-Rayyan React review interface and original Three.js/R3F visual experience, including accessibility, performance and annotation correctness.
---

Read `../../docs/frontend-design.md`; use `../../docs/architecture.md` for contracts and PICO offsets. React supersedes the earlier Streamlit suggestion.

Keep original 3D visuals isolated to a lazy-loaded landing scene. Core query/review/annotation/export controls remain semantic DOM and usable with no WebGL or motion. One canvas, bounded DPR, resource disposal and offscreen pausing are preferred. Do not add multiple animation engines or expensive shaders without profiling.

Use the linked reference pages as design direction; do not copy unlicensed models, artwork or branding. Pinterest links are search-discovered leads, not visually verified implementations. Maintain attribution for assets actually used.

Build empty/loading/partial/error/conflict states with the same care as populated screens. Distinguish model suggestions from persisted human decisions. Preserve drafts after failures, handle HTTP 409 explicitly and scope caches to workspace/revision.

Convert browser UTF-16 selections to code-point offsets against exact saved text. Test overlapping spans, repeated quotes, non-BMP characters and changed text. Keep selection surfaces free of motion that disrupts selection. Check keyboard flow, focus, reduced motion, 200% zoom, mobile width and WebGL loss before marking the experience tested.
