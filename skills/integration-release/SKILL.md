---
name: integration-release
description: Integrate Mini-Rayyan team branches and shared contracts, validate dependency locks and migrations, prepare release evidence, and maintain the completion audit.
---

Read `../../docs/team-execution.md`, `../../docs/dependencies.md`, and `../../audit.md`. For release work also read `../../docs/verification-and-release.md`.

Check which artifacts are real implementation versus planning/probes before taking action. Contract additions merge before dependent providers/consumers. T4 serializes migrations and backend lock changes; T1 serializes frontend lock changes and generated API types. Do not manually splice locks or use peer-conflict bypass flags.

Use frozen installs. After a dependency change, run the affected import/build probe and application tests that exercise that dependency. After a migration change, check the revision graph and upgrade/restore behavior. Resolve conflicts semantically and test the combined result; a clean merge is not proof of correctness.

Protect `main`, use short branches, and follow explicit current user authorization for remote mutation/publication. Preserve unrelated teammate changes. At release, verify persistent storage, secrets/auth, backup restoration, clean setup and the actual judge access arrangement.

Update the audit with date, scope, evidence and remaining limits. Never mark planned features tested/deployed, infer unavailable organizer scores, or claim zero dependency/security risk from a successful resolver.
