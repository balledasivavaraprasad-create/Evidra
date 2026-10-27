# Premium React and 3D experience plan

## Visual direction: an evidence observatory

Build an original scientific workspace with luminous translucent forms, carefully spaced typography and a calm, precise reading surface. Working visual concept: an abstract cluster of paper-like glass layers orbiting a central evidence lens. The composition suggests finding and clarifying evidence without implying a medically accurate molecular model.

Use a graphite/ink landing background (`#0B1220`), pale reading surfaces (`#F7F9FC`), cool teal (`#5EEAD4`) and restrained blue (`#7CA8FF`). These are proposed design tokens, not extracted brand assets. Separate status colors from PICO colors; use text/icon labels as well as color. Start with one locally available/system sans-serif stack; self-host a licensed font only after checking its license. Keep abstract text at 16–18px, 1.55–1.7 line height and a comfortable reading width.

## Reference board and what to adapt

These references inform composition/material/motion; create original geometry, layouts and branding. No third-party model, animation or paid asset is licensed merely because it appears on Pinterest/Dribbble.

| Reference | Useful direction | How this project adapts it |
|---|---|---|
| [Designed Cells — Apexy Team](https://dribbble.com/shots/26682784-Designed-Cells-Emotional-3D-Website) | Scientific organic forms, restrained interface and paced motion described by its creators | A single original evidence-lens hero; quiet UI around it |
| [Biotechnology Landing Page — Tridimensi](https://dribbble.com/shots/27144916-Biotechnology-Landing-Page) | An abstract biotech animation used as the hero focal point | Split composition with readable product promise and immediate “Start review” action |
| [Biotech animation — Zajno](https://dribbble.com/shots/20429307-The-3D-Animation-for-the-Biotech-Startup) | Creator-described transitions across connected cell scales | Optional short transition from scattered paper cards to organized groups, never a blocked navigation sequence |
| [Pinterest: 3D glass hover card](https://www.pinterest.com/pin/glassmorphism-card-with-3d-hover-effect--580331101981710342/) | Surface-depth/hover reference discovered in search | Very subtle card tilt on landing only; keyboard focus has an equivalent static treatment |
| [Pinterest: glass-effect chart landing concept](https://in.pinterest.com/pin/3d-chart-with-glass-effect-glassmorphism-future-security-landing-page-template-in-2025--432978951698173571/) | Search-indexed glass/depth reference | Translucent decorative dashboard preview, with solid readable production tables |

Research limitation: Dribbble creator descriptions and published pages were inspected; the linked Pinterest pages were discoverable in search but direct access was restricted. They are reference leads, not claimed pixel-level visual audits or verified live-WebGL implementations. T1 should visually inspect the boards at kickoff before finalizing the moodboard; do not claim a static render is a working 3D reference.

## Routes and interaction specification

| Screen | Required behavior | Visual / interaction treatment |
|---|---|---|
| `/` | Explain product, enter workspace | One 3D focal composition, direct CTA, short pipeline explanation, no fabricated user/accuracy statistics |
| `/reviews` | Create/select review, resume saved work | Clean cards with real counts and last-updated dates |
| `/reviews/:id/setup` | Question/PICO/criteria with reasons | Guided form, visible version, save feedback, active-rule toggles |
| `/reviews/:id/search` | Boolean builder, dates, source options, counts, selection, approved import | Query chips plus editable structured form, compact search-history cards, honest count/import distinction |
| `/reviews/:id/records` | Filter/page review queue, include/exclude/maybe, undo, notes | Three regions: filters/list, abstract reader, evidence/actions. Collapse to stacked panels on small screens |
| `/reviews/:id/duplicates` | Side-by-side candidates, identifiers, evidence and override | Synchronized readable panels; reject/confirm with explicit effect and reason |
| `/reviews/:id/records/:group` | Editable PICO and decision provenance | Native DOM text selection, P/I/C/O labels, quote preview, save/cancel, stale-edit conflict recovery |
| `/reviews/:id/history` | Query/corpus versions and optional diff/revert | Flat timeline with added/removed/merged counts and exact snapshot labels |
| `/reviews/:id/runs` | Progress, failed step, retry/cancel | Real stage status and safe errors; no invented percentage when total is unknown |
| Export panel | Confirm revision and included count, download CSV | Explain unresolved-conflict omissions and provenance manifest |

All screens need empty, loading, populated, partial, error, unavailable and permission-denied states. Preserve unsaved annotations on a recoverable request failure. A 409 offers reload/compare and deliberate resubmission, not an automatic overwrite. Distinguish a model suggestion from a saved human decision through explicit provenance text.

## Component and state architecture

React + TypeScript + Vite; React Router for routes; TanStack Query for server state and mutation invalidation; local state for drafts and view controls. Avoid a second global store unless a real cross-route draft requirement emerges. Generated API types come from backend OpenAPI. CSS variables and scoped component styles are sufficient; do not add multiple UI/theming frameworks just for visual polish.

Planned modules: `features/landing`, `features/review-setup`, `features/search`, `features/review-queue`, `features/duplicates`, `features/pico`, `features/history`, `features/assistant`; shared `components`, `api`, `styles`, `accessibility`. Scene code is lazy-loaded and isolated under `features/landing/scene`.

Freeze PICO offset convention with T3/T4. DOM text is canonical; avoid wrapping each token in animated elements that corrupt selections. Convert browser UTF-16 positions to code-point offsets before saving. Derive highlights from validated spans and the same text hash. Handle overlapping labels, emoji/non-BMP characters, multiline abstracts, repeated phrases and keyboard annotation.

Never optimistically show a decision as durably saved before the API confirms. A pending indicator is acceptable; preserve draft state and explain retries. Query-cache keys include workspace/revision/filter/page. Cancellation and request identity prevent late old-query responses replacing new results.

## 3D implementation, bounded to the event

React Three Fiber renders Three.js; Drei supplies selected helpers. React and Fiber major versions must align: the installed v9 family supports React 19 ([installation documentation](https://r3f.docs.pmnd.rs/getting-started/installation)). Exact peer resolution is recorded in the dependency evidence. Avoid importing another copy of React or mixing R3F v10 prereleases with Drei v10's v9 peer contract.

**Hero v1 (4–6 focused hours after core UI):** procedural instanced glass-like cards/orbs, subtle orbital motion, soft lighting and pointer response. Use inexpensive opaque/translucent materials first; physically expensive transmission/refraction and postprocessing are optional upgrades only after profiling. The 3D element is decorative; all headings/actions exist in semantic HTML.

**Motion:** page transitions 160–240ms; card/focus transitions 120–180ms; slow ambient hero cycle. Use Motion for DOM transitions and R3F `useFrame`/refs for scene updates. No React `setState` on every animation frame. Do not install both GSAP and Motion without a specific unmet need. No scroll hijacking or mandatory intro sequence.

**Rendering:** one canvas, lazy import after primary content, cap DPR at 1.5 initially, reuse geometry/materials, instancing for repetitions, no dynamic high-resolution shadows by default. Pause when offscreen or the tab is hidden, dispose resources on unmount, and use demand rendering when the scene is at rest. R3F documents on-demand rendering and resource reuse as performance techniques ([performance guide](https://r3f.docs.pmnd.rs/advanced/scaling-performance)).

**Fallbacks:** `prefers-reduced-motion`, user “Reduce visual effects” control, small screens and WebGL/context-loss errors all get a static authored SVG/CSS composition with identical product actions. Low performance can reduce scene detail without changing review functionality. Do not fingerprint devices or require 3D support to enter the app.

## Internal quality targets, not verified scores

- All primary tasks keyboard accessible; visible focus; dialogs trap/return focus; skip navigation; labels and error associations.
- Target WCAG 2.2 AA contrast and interactions; check actual colors, including PICO highlights, rather than assuming palette compliance.
- Honor reduced motion and provide pause for continuous decorative motion. Avoid parallax over abstract-reading surfaces.
- Initial core route JS target ≤300KB gzip excluding deferred 3D; total deferred scene assets target ≤1.5MB compressed. Measure with actual production build and tune, not guess.
- Target LCP ≤2.5s, INP ≤200ms and CLS ≤0.1 on an agreed test profile; report device/network/run count. These are project targets, not measurements or guarantees.
- Aim for smooth 60fps on the chosen desktop and usable 30fps fallback; frame rate is measured on actual demo hardware. The reviewer queue has no continuously rendering canvas.
- Test 390px mobile, 768px tablet and 1440px desktop, 200% zoom, keyboard-only flow, missing WebGL and a slow network.

At hour 36 the usable workbench and one cohesive visual system must exist. At hour 60 stop adding scenes. If polish competes with data integrity, retain the original static visual, crisp typography and functional motion while fixing integrity first. This preserves the premium direction without risking the required review workflow.
