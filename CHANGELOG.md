# Changelog

All notable changes to this project are documented here. Versions follow Semantic Versioning while the public contract stabilizes.

## [2.3.0] - 2026-07-24

### Changed

- Promoted the verified `2.2.0-beta.5` protocol to the stable public `2.3.0` release without changing its workflow behavior.
- Made stable minor releases the public default: each normal publication increments the minor version, while prereleases require an explicit project-owner request.

### Compatibility

- `2.3.0` keeps the protocol, installer, package manifest and compatibility boundary verified in `2.2.0-beta.5`; only release metadata and the standing publication policy changed.
- Existing beta installations can use the backup-preserving installer `update` action. The previous `2.2.0-beta.5` prerelease remains available as a rollback point.

### Release status

- Stable public release target: `2.3.0`.

## [2.2.0-beta.5] - 2026-07-24

### Added

- A single execution-site validity check before mutating a new or resumed Task, covering Task binding, target baseline, freshness source, source fingerprint, dirty-change ownership, isolation and writability.
- Execution-site evidence in bounded handoff capsules so a new executor can distinguish a fresh Task site, the same active Task, an absorbed historical site and a read-only inspection.
- A context-identity gate that separates a new user result, post-delivery defect or cross-owner change into an independent side-task capsule instead of carrying forward a stale thread by habit.
- Symlink-aware installer updates that preserve a managed source link and fail closed when the linked source differs from the candidate.

### Changed

- Allowed target movement during the same active Task without forcing an immediate rebase, while preserving project-defined synchronization before delivery.
- Made 验收交付 record whether the site continues the same Task, remains read-only evidence or awaits authorized cleanup after the result reaches its target.
- Strengthened 执行任务、验收交付 and 有界上下文交接 without adding a stage, status owner, Git-specific command or persistent workspace state.
- Reconciled a concurrently installed workflow improvement into the release candidate instead of overwriting the managed local truth.

### Fixed

- Prevented a completed feature workspace already absorbed by its target from being silently reused for a new Task.
- Prevented a clean feature branch or cached remote-tracking ref from being mistaken for proof that the execution site is current.
- Prevented blanket `behind > 0` handling from rewriting active or published work without considering Task identity and project rules.
- Prevented `update` from replacing a managed workflow symlink with an unrelated copied directory.

### Release status

- Published as the public `2.2.0-beta.5` prerelease after fresh verification and mainline integration.

## [2.2.0-beta.4] - 2026-07-23

### Added

- A requirement maturity hard gate covering user and pain, target and observable success, scope and non-scope, constraints and trade-offs, and authority and ownership.
- Stable numbered question batches so users can answer compactly with forms such as `1B 2A 3C`; independent high-value decisions may be asked together while dependent branches remain sequential.
- A decision-tree loop that reuses the same question number for vague, evasive, or contradictory answers and keeps drilling until each load-bearing branch is resolved, testable, explicitly deferred, or blocked.
- A project-scoped standing release authorization for verified `workflow/` changes, allowing commit, push, mainline integration, and publication without repeated approval while retaining P0, scope, and no-force gates.

### Changed

- Made the requirement card a post-clarification result instead of a speculative discovery substitute.
- Made decision challenge mandatory when requirement clarification still contains a key trade-off, vague answer, or contradiction.
- Removed any total question-count ceiling while retaining a strict information-value gate and short batched feedback loops.

### Fixed

- Prevented standard and project work from skipping user judgment and immediately emitting a completed requirement card.
- Prevented AI recommendations, silence, and vague agreement from being persisted as confirmed user requirements.
- Prevented one-question-per-turn ceremony from slowing down independent decisions that users can answer efficiently in one numbered batch.

### Release status

- Integrated into the public `2.2.0-beta.5` prerelease; no separate public beta.4 tag was created.

## [2.2.0-beta.3] - 2026-07-23

### Added

- A decision-ready evolution proposal that separates observed pain from the AI-inferred need, smallest change, business value, and accept / adjust / defer decision.
- Owner-local handoff: current-project improvements collapse into appended Plan/Task work, while cross-project and cross-skill improvements use the existing bounded task capsule.

### Changed

- Replaced the occurrence-count promotion gate with model judgment over evidence, impact, change size, reversibility, and long-term ROI.
- Made proposal acceptance authorize planning only; complete Plan confirmation, external-side-effect authorization, and fresh verification remain separate gates.
- Routed 回灌改进、拆成任务、执行任务 by the current business question without adding a new stage or duplicating implementation status.

### Fixed

- Prevented an inferred user need from silently becoming a permanent rule.
- Prevented a generated handoff prompt from being reported as completed before the target truth owner returns actual changes and fresh verification.

### Release status

- Integrated into the public `2.2.0-beta.5` prerelease; no separate public beta.3 tag was created.

## [2.2.0-beta.2] - 2026-07-23

### Added

- An event-driven status snapshot that appears at the top of the next visible message only when stage, active references, valid results, or the active Plan/Task path changes.
- Clickable Chinese labels for the workflow references actually used in the current work.
- A compact text-only active path such as `✓ P01 → ● P02 / T03 → ○ P03`.

### Changed

- Removed host probing, native Plan/Task presentation, generated DAG visuals, and Ready Queue output from the user-facing status contract.
- Split every real handoff into two mandatory user action exits: `建议下一步｜` and `回复建议｜`.
- Kept status broadcasts non-blocking: AI may report a changed state and immediately continue working without asking the user to take over.
- Applied the presentation contract without adding a new stage across 需求澄清、选定方案、拆成任务、执行任务、验收交付、提炼经验、回灌改进.

### Fixed

- Prevented removal of AI scheduling details such as `下一 Ready` from also removing the user's recommended next action and directly reusable reply.

### Release status

- Integrated into the public `2.2.0-beta.5` prerelease; no separate public beta.2 tag was created.

## [2.2.0-beta.1] - 2026-07-23

### Added

- A Chinese-first three-part business loop: 计划、执行、复盘.
- Four explicit unknown routes: 事实可查、取舍待定、假设待验、外部待解.
- H0–H3 adaptive depth with seven primary owners and seven on-demand harnesses.
- A minimal review and controlled evolution loop that updates the unique truth owner without expanding documentation by default.
- Restored parallel merge governance as a dedicated seventh harness: isolated worktrees may edit the same source, while late mergers serialize, rebase, preserve conflicts for AI resolution, and rerun both sides' verification.
- Added the portable `scripts/safe_merge.py` mechanical path for local merge locking, bounded overtaking retries, fast-forward-only push, and resumable conflict handling without shell-script runtime.
- Added a portable fresh-start contract for parallel delivery: fetch the target remote before creating each worktree, then let the project release contract choose CI/MR versus direct mainline delivery.
- Added one active, project-relative result route per completed stage, including document, visual and collection targets carried by the context capsule.
- Added repository ignores for Python bytecode, test caches and desktop metadata so generated files cannot pollute a release candidate.

### Changed

- Restored the integrated release gate inside 验收交付: derive the release contract from project truth, perform authorized commit/merge/release as one bounded flow, reverify after integration, and prove the real remote or deployed state.
- Renamed the first canonical action from 看清目标 to 需求澄清; 看清目标 remains a read-boundary compatibility alias only.
- Replaced the nine internal stage values with seven canonical Chinese actions: 需求澄清、选定方案、拆成任务、执行任务、验收交付、提炼经验、回灌改进.
- Consolidated the main workflow references while retaining 14 references aligned to seven owners and seven harnesses.
- Rebuilt the generated visual contract around the seven actions, four unknown routes, adaptive depth, and the 14 reference owners.
- Made semantic rebase resolution explicitly compare both changes' assumptions, chronology, invariants and affected tests; whole-file side selection is prohibited.
- Changed user handoffs to stop only for real human input, lead with the business conclusion, show seven-stage progress, and keep native Plan/Task views as optional derived presentation.
- Removed human code review as a default delivery assumption: AI owns diff review and fresh verification, while PR/MR and other release nodes exist only when project truth gives them independent value.

### Reference migration

- `project-discovery.md + context-discovery.md + clarify-prioritize.md → understand-goal.md`
- `solution-design.md → decide-solution.md`; `experience-design.md → shape-experience.md`; `design-system.md → maintain-design.md`
- `write-plan.md → plan-tasks.md`; `act-plan.md → execute-tasks.md`; `delegation.md → coordinate-agents.md`; `debugging-recovery.md → fix-failures.md`
- `verification.md + finish-release.md → verify-deliver.md`; `context-handoff.md → handoff-context.md`; `evolution-loop.md → evolve-system.md`
- Added `challenge-decisions.md` and `learn-review.md` as the missing decision-challenge and review owners.

### Compatibility

- Older stage values are accepted only at the read boundary for one release cycle; all new writes use the seven Chinese values.
- Compatibility remains through the 2.x release cycle and is removed in 3.0.0; no deprecated value may re-enter public formal sources.
- Publishing a tag or release still requires separate authorization.

### Migration from 2.1.0-beta.3

- This is a substantial beta protocol upgrade: the prior eight-stage thin orchestration is replaced by seven business stages, completion becomes an independent status, and completed stages may route directly to their result files, visual plans, or result collections.
- Integrated delivery returns to 验收交付. When release is in scope, project release truth drives the authorized commit, merge, release, and post-release verification flow; a local green check is only an intermediate state.
- Runtime tooling now requires Python 3.9+; `2.1.0-beta.3` itself was zero-Python. Use the backup-preserving installer `update` action, and keep its reported backup until the new package passes `check` in the target Agent environment.
- To roll back, restore the installer backup or reinstall the verified `2.1.0-beta.3` tag.

## [2.1.0-beta.3] - 2026-07-21

### Added

- A thin orchestration protocol with four unique truth sources for requirements, approved plans, implementation contracts, and current progress.
- Behavior scenarios and an interactive visual walkthrough for validating the workflow contract without a Python runtime.

### Changed

- Made light work use a zero-ceremony path and kept specialist references progressive rather than loading the whole workflow at once.
- Consolidated Git ownership under the coordinator and kept delivery authorization explicit.

### Release status

- Published as the public `2.1.0-beta.3` prerelease and retained as the rollback point for the 2.2 migration.

## [2.0.0-beta.2] - Unreleased

### Added

- An expert roundtable in Solution: independent divergence, cross-examination, a fact-labelled forest map, and evidence-based convergence.
- Business-language explanations across the public README and generated visual introduction.

### Changed

- Reframed the public workflow as “think it through, build it, prove it” and an eight-step business path with Debug as a side loop.
- Replaced formal `Intake` state with a write-free entry router that either handles light work directly or enters Clarify.
- Added `zhonglin` as the author and aligned MIT attribution.

### Compatibility

- Existing plans with `stage: Intake` remain readable; new plans start at `Clarify`.
- This is a local release candidate only. Publishing a new tag or release requires separate authorization.

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

- Published as the first public beta after provenance confirmation and explicit release authorization.
