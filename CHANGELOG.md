# Changelog

All notable changes to this project are documented here. Versions follow Semantic Versioning while the public contract stabilizes.

## [2.0.0-beta.1] - 2026-07-19

### Added

- One dependency-closed `workflow` skill with 14 progressive references.
- Minimum Readiness Gate with mature/no-op, patch-existing, and one-entry behavior.
- Solution→UX/IA→Design System→Visual/Motion→Selection contract before Write.
- Built-in Write, Act/Delegation, Debug/Recovery, Fresh Verification, Finish, and safe capability degradation.
- Context capsule, visual map generator, doctor, release gate, portable installer, and clean-room tests.
- Chinese-first onboarding, a copy-to-Agent installation prompt, safe skills-directory detection, and a standalone responsive HTML introduction.

### Changed

- Replaced package-external workflow routes with package-relative references.
- Replaced fixed user/company paths and platform identities with capability discovery and portable paths.
- Consolidated state, evidence, implementation, progress, and index ownership; Plan/Task status now has one owner.
- Reworked the README and generated visual map around a 30-second Chinese reading path while keeping the package at 39 files.
- Made doctor, release gates, and clean-room tests work from a real Git checkout by excluding `.git` metadata from the public payload boundary.

### Removed

- Nested skills, duplicated strategy/reviewer templates, organization-specific release implementations, fixed server paths, historical logs, and the broad Foundation document system.

### Migration

- Install beta into a separate skills directory or use the installer's backup-preserving `update` action.
- Existing task plans remain readable; new work should use the five truth-source roles and the `Experience/N/A` gate.
- Roll back by restoring the installer's reported backup directory or the previous verified Git tag.

### Release status

- Candidate prepared locally. The first public tag remains gated on final provenance confirmation and explicit release authorization.
