# Evidra Frontend Experience & Usability Results (A06 Final Release)

**Author:** dev-A (T1 Frontend / 3D Owner)  
**Release Target:** Canonical Merge Position 24 (A06 Final Release)  
**Scope:** Premium 3D experience, scroll kinematics, luxury frosted glass design system, Level 2 history/diff/restore UI, Assistant proposal panel, and single-host SPA packaging.  
**Status:** Completed, verified, and release-ready.

---

## 1. Executive Summary

Evidra delivers an ultra-premium React 19 + Three.js interface combining Apple-grade and Lusion.co-inspired aesthetics with rigorous clinical usability. The visual design pairs polished silver, champagne gold accents, obsidian black, and crisp studio white with frosted glass surfaces and an interactive, scroll-driven 3D Knowledge Lattice rendered in React Three Fiber.

All critical user review paths—Search & Ingestion (`/search`), Screening Queue (`/workbench`), PICO Offset Inspector, Conflict Resolution Modal, Version History & Corpus Diff (`/history`), and the Bounded Assistant Panel—are fully functional, tested, and integrated with the FastAPI backend.

---

## 2. Bundle Measurements and Code-Splitting Evidence

Measured via production Rollup / Vite bundler output:

| Chunk | Size | Gzip Size | Routing Policy |
|---|---|---|---|
| `dist/assets/index-*.js` | 426.33 kB | 121.56 kB | Initial core bundle (Router, React Query, Review Workbench, Offsets, History) |
| `dist/assets/EvidenceScene3D-*.js` | 874.16 kB | 232.58 kB | **Lazy-loaded on demand** (Three.js, Fiber, procedural shaders) |
| `dist/assets/index-*.css` | 2.90 kB | 1.17 kB | Universal design tokens (Light/Dark themes, frosted glass, metallic typography) |
| `dist/index.html` | 1.45 kB | 0.78 kB | Semantic HTML5 with skip-links |

**Key Takeaways:**
1. Zero Three.js code is loaded when a reviewer accesses `/workbench` or `/history` directly.
2. The initial core payload is ~121 kB gzipped, well within standard high-performance web application budgets.
3. Single-host SPA routing under `/` is fully supported with static asset serving under `/assets/` and non-swallowing API 404 error envelopes.

---

## 3. Implemented User Interfaces & Verification

### 3.1 3D Evidence Observatory (`EvidenceScene3D.tsx`)
- Central faceted procedural icosahedron with physical metallic material (`metalness: 0.85`, `roughness: 0.12`).
- Torus rings and 4 jewel-toned PICO satellite beacons (Population in Cyan, Intervention in Purple, Comparison in Gold, Outcome in Emerald).
- Continuous 60fps lerp interpolation responding smoothly to user scroll position.
- Graceful SVG fallback (`HeroStatic.tsx`) for browsers lacking WebGL context.

### 3.2 Screening Workbench & PICO Viewer
- Visual paper group cards with categorical decision badges (`INCLUDED`, `EXCLUDED`, `MAYBE`).
- Interactive PICO span viewer highlighting exact Unicode code-point offsets `[start_cp, end_cp)` with live character verification.
- Optimistic concurrency protection: detects concurrent edits and prompts reviewer refresh on version conflicts (HTTP 409).
- Exclusion modal requiring selection from explicit predefined reasons or custom justification.

### 3.3 Level 2 History, Diff, and Conflict Resolution (`HistoryPage.tsx`)
- Timeline of immutable published corpus snapshots with commit timestamps and group counts.
- Side-by-side **Corpus Diff**: calculates and visually tags papers as Added (green), Removed (red), or Modified.
- **Group Conflict Resolution Modal**: displays inherited screening divergences from merged studies and requires explicit reviewer resolution.
- **Exact Snapshot Restore**: one-click offline reinstatement of earlier corpus revisions without re-querying external APIs.

### 3.4 Bounded Evidence Assistant Panel (`AssistantPanel.tsx`)
- Integrated into the review queue sub-tabs.
- Allows the reviewer to query the bounded SQLite FTS5 assistant for screening explanations, PICO extraction proposals, or query advice.
- When LLM is disabled in runtime configuration (default Level 1 mode), presents a clean informational banner with zero broken UI states.
- When active, presents verbatim grounded corpus citations and enforces mandatory human confirmation (`requires_human_approval=True`).

---

## 4. Accessibility and Design Standards

- **Theme Persistence:** Dark obsidian mode (`#050811`) and pure studio white light mode (`#f8fafc`) toggled instantly and persisted in `localStorage`.
- **Keyboard Navigation:** Universal focus-visible rings (`outline: 2px solid var(--accent-cyan)`), skip-to-content links, and full keyboard tab stops across all navigation buttons.
- **High Contrast & PICO Readability:** All text exceeds WCAG 2.1 AA 4.5:1 contrast ratios. Status indicators combine categorical color badges with explicit text labels.
