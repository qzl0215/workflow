# Changelog

All notable changes to this project are documented here. Versions follow Semantic Versioning while the public contract stabilizes.

## [2.15.0] - 2026-07-29

### Added

- Added a locked worktree lifecycle for parallel writers: one writable owner per worktree, explicit `workflow:<Task ID>` ownership, guarded cleanup after verified integration, and fail-closed preservation of dirty, active or unabsorbed sites.
- Added target-first merge integration that keeps the latest target as first parent, preserves candidate commits, serializes each integration attempt, and rebuilds safely when the remote target advances.
- Added integration coverage for same-file multi-commit conflicts, first-parent topology, candidate identity, mandatory push verification, locked worktree cleanup and dirty-worktree preservation.

### Changed

- Replaced commit replay in the managed parallel-delivery path with one serial merge per requirement branch; repositories that explicitly require linear history defer to their platform squash-merge contract.
- Required every parallel mutating thread to use an independent worktree while allowing different worktrees to modify the same original file and resolve semantic overlap during serial integration.
- Made `--push` fail closed without an explicit verification command and retained local branches when completed worktrees are removed.

### Compatibility

- The existing `scripts/safe_merge.py --target ... --verify ... --push` and `--continue` entry points remain available; their integration result now preserves the candidate branch instead of rewriting it.
- Existing unmarked worktrees are reported as legacy candidates and are never deleted automatically.

## [2.14.0] - 2026-07-28

### Added

- Added one closeout review gate before completion, termination or a long-lived blocker handoff.
- Made review mandatory when actual execution time strictly exceeds one hour or platform-reported task tokens strictly exceed two million, while refusing to guess unavailable telemetry.

### Changed

- Made a complete writeback proposal serve as the minimal full Plan: one explicit user confirmation now starts in-scope writeback without a duplicate Plan confirmation.
- Kept no-op reviews valid and retained separate authorization for external side effects.

## [2.13.2] - 2026-07-28

### Changed

- Made each `findings.md` decision topic keep one current decision receipt instead of preserving flip-flop history as parallel conclusions.
- Let clear, high-confidence newer user goals replace older decisions in place, while requiring user confirmation when supersession is ambiguous or an incorrect overwrite carries material risk.
- Compressed expert, requirement, solution, and handoff writers onto the same current-decision rule; audit history stays in an existing audit system rather than the hot findings source.

## [2.13.1] - 2026-07-28

### Changed

- Added three progressive UI decision gates: three static rough directions for `方向粗选`, one mock-data HTML for `方案精修`, and explicit `确认开动` before real implementation.
- Kept parallel direction generation available whenever it reduces elapsed time, while bounding first-round cost through static fidelity, same-batch delivery, and no pre-selection HTML polish.
- Deferred real field contracts, extreme fixtures, responsive behavior, interaction, and accessibility validation to implementation without weakening the final evidence gate.

## [2.13.0] - 2026-07-28

### Added

- Added a minimal consumption-value and discoverability gate for long-term knowledge: future use scenario, changed core decision or action, and the route from the question to one canonical source.

### Changed

- Made knowledge promotion a semantic integration into the canonical owner instead of an append-only patch; Knowledge Delta now serves only as a writeback receipt.
- Limited project knowledge navigation updates to topology changes such as creating, moving, replacing, or retiring an owner, while keeping ordinary owner-local content edits out of the root index.
- Kept in-scope knowledge promotion inside the originating Plan retirement transaction; only new user outcomes or independently deliverable cross-owner changes create another Plan.
- Removed mandatory per-claim owner, invalidation, maintenance, and net-value fields; mutable facts prefer code, configuration, or fresh probes.
- Made temporary evidence deletion the default after verification and retirement; only non-reproducible evidence explicitly required for audit, rollback, or incident recovery may reuse an existing retention system.
- Replaced the retirement classification matrix with a five-line check and prohibited a human/AI split knowledge source or a new cold-evidence management process.

## [2.12.0] - 2026-07-27

### Added

- Added a proactive requirement-clarification trigger whenever a surface request still requires direction-changing inference about the real user result, without waiting for the user to ask for clarification.
- Added the target chain `表面请求 → 当前痛点 → 本质目标 → 成功信号` and persisted it in the findings template.
- Added a question-leverage rule that selects one batch of 1–3 questions by decision impact, uncertainty, error cost, and user effort, with the current understanding or recommendation attached to every question.

### Changed

- Focused clarification on why the work matters, what must actually change, and which outcome matters most, while retaining self-service research and the zero-question fast path for clear, reversible work.

## [2.11.1] - 2026-07-27

### Fixed

- Bounded legacy mixed-status Plan indexes to the `Active` section during normal work, preventing completed summaries from entering context before a specific recovery or audit need exists.

## [2.11.0] - 2026-07-27

### Added

- Added a repo-native project knowledge entry that navigates to code, runtime, normative, rationale, authorization, active-work, and derived truth owners without copying code facts into a second encyclopedia.
- Added a retirement gate that removes completed Plans from default context immediately while preserving decisions, experiments, acceptance, rollback, and residual-risk evidence until each item has an owner and recovery path.

### Changed

- Made `progress.md` and implementation details conditional for minimal Task capsules, moved stable Task contracts before dynamic handoff state for cache reuse, and changed fixed byte and selection-ratio limits into observable warnings rather than correctness failures.
- Added explicit audit-only loading for completed Plans and content fingerprints for derived context capsules.

## [2.10.0] - 2026-07-27

### Added

- Added a solution-confirmation causal chain that connects the decision-relevant intermediate actions to their positive effects, negative consequences, and the trade-off the user is being asked to accept.

### Changed

- Made direction handoffs explain real costs, limits, long-term trade-offs, and available mitigation or rollback without expanding ordinary implementation steps.
- Kept lightweight, safely reversible choices on the fast path instead of forcing a mechanical confirmation template.

## [2.9.0] - 2026-07-27

### Added

- Added a root-cause closure and bounded homologous-defect audit for failures caused by shared mechanisms, public boundaries, or missing system invariants.
- Added an optional `progress.md` evidence shape for the symptom, minimal reproduction, proven root cause, broken invariant, bounded impact set, included and excluded paths, residual risk, stopping basis, and verification.

### Changed

- Redefined the minimum fix as the smallest complete repair that removes the proven root cause across the proven homologous impact set, while retaining a proportionate fast path for isolated typos and local condition errors.
- Required shared-mechanism fixes to pass symptom, mechanism, and impact-surface evidence; restoring only the original page or test no longer closes the result.

## [2.8.2] - 2026-07-27

### Changed

- Moved project freshness from an Act-only safeguard to the research entrance: a new request whose conclusions depend on mutable project state refreshes the project truth once, pins its source fingerprint, and keeps the same site through research, planning, and implementation.
- Kept the rule intentionally small: conceptual questions do not refresh, resumed work keeps its bound site, there is no commit-count threshold, and the target is synchronized only once more before delivery.

## [2.8.1] - 2026-07-26

### Changed

- Made the minimum sufficient fast path the default; file count, project importance, routine release work, and workflow self-modification no longer escalate a task by themselves.
- Replaced questionnaire-first clarification with a complete recommended requirement contract and at most one default batch of material exceptions.
- Tiered project truth by recovery need: simple work creates no documents, standard work uses at most one minimal plan when persistence is required, and only complex projects use the three hot sources.
- Bound reusable verification to command-scoped source content, verification command, and environment class so content-equivalent rebases, copies, and artifacts reuse evidence.
- Converged routine delivery on one final source validation, content equivalence, one released artifact, and a fresh installation smoke test.
- Added a six-question process Occam gate without adding a new owner, harness, method pack, status, or report.
- Adopted normal SemVer patch/minor/major selection for future stable releases.

## [2.8.0] - 2026-07-25

### Added

- Added a research-sufficiency gate, explicit requirement-contract confirmation for standard/project work, and the evidence ladder from project truth through minimal experiments.
- Added four lazy-loaded PUA/P10 method packs: strategic value, essence subtraction, experiment attack, and delivery compounding.
- Added minimum-cover expert capsules and a vetoing Occam gate for the final recommendation and every material revision.
- Added a measurable activity-context budget with long-history, oversized-slice, ratio, and conditional implementation-plan coverage.

### Changed

- Kept seven business action owners while replacing the fixed 7+7 topology with seven owners, six orthogonal harnesses, and one Git/worktree adapter.
- Folded decision challenge into requirement and solution owners; split required result verification from conditional authorized delivery.
- Reduced project hot truth to `task_plan.md`, `findings.md`, and `progress.md`; made implementation navigation and multi-task index conditional.
- Rebased the package on immutable 2.7.0 while preserving the local persistent-cache upgrade acceptance gate.

### Removed

- Removed `challenge-decisions.md`, `verify-deliver.md`, the reference-level parallel merge harness, and `pre-plan-contract.md`.
- Removed fixed owner/harness count equality as an architectural invariant.

## [2.7.0] - 2026-07-25

### Changed

- 为浏览器验收增加有界止损：两种可见控制方式均失败或连接器诊断达到 90 秒后，停止在交付主链反复调试驱动。
- 将浏览器驱动故障与产品验收分流；非交互目标允许用直达 URL、ready 信号、可见内容、网络状态和回归契约组成 fresh 证据。
- 交互本身是验收目标且替代证据不足时，必须明确标记未覆盖并返回 Task 或 blocker，禁止把连接器失败写成产品通过。

### Release status

- Stable public release target: `2.7.0`.

## [2.6.0] - 2026-07-25

### Changed

- 将 DAG 从默认交付物收敛为真实分支、跨 owner 或共享资源冲突时才启用的条件化机制；线性小任务默认使用紧凑 Task 表。
- 引入单一 RC 证据回执：相同 `source fingerprint + impact set + environment + verification profile` 可直接复用，输入变化时只失效受影响验证。
- 将生产形态预检纳入 Verify：覆盖冷/热路径、真实数据规模、资源峰值，以及大 payload、缓存和序列化风险。
- 在 `progress.md` 中记录 RC receipt、复用状态与验证耗时，便于直接识别重复验证成本。

### Release status

- Stable public release target: `2.6.0`.

## [2.5.0] - 2026-07-24

### Added

- A user-level auto-update command for macOS, Linux and Windows that runs once at login or boot and then every 24 hours, outside the workflow invocation path.
- A trusted `sync` action that accepts only the latest stable immutable GitHub Release, a unique `workflow.zip` asset, GitHub's SHA-256 digest and a package version matching the Release tag.
- Single-source enforcement that rejects duplicate discoverable workflow skills and repairs same-version payload drift from the verified Release asset.

### Changed

- Replaced backup-preserving updates with a simpler candidate-first whole-directory replacement: validate in a temporary directory, remove the old active package, then activate the verified package at the canonical `workflow` path.
- Made uninstall permanent after explicit confirmation; updates and removals no longer leave discoverable `backup`, `failed` or `removed` workflow copies.

### Compatibility

- Normal workflow calls remain fully offline and do not pay an update-check cost.
- Existing source-managed symlink installations remain source-managed; remote `sync` refuses to replace a symlink with a copied package.
- Historical installations can run one source update, enable the user-level updater, and then converge automatically to later stable Releases.

### Release status

- Stable public release target: `2.5.0`.

## [2.4.0] - 2026-07-24

### Changed

- Replaced the 12-slide visual lecture with a concise first-person introduction that explains what workflow is, its seven-action path, when the user participates, how unknowns are routed, and how to install it.
- Removed the fixed 1480px content ceiling and presentation-deck controls in favor of a fluid single-page layout that uses about 92% of a 3840px display while remaining a single column without horizontal overflow at 390px.
- Reduced the generated visual document by about 57% and simplified its content model, generator, and tests around the current workflow contract instead of maintaining per-slide teaching payloads.

### Compatibility

- The workflow protocol, seven canonical actions, fourteen routed capabilities, installer, and authorization boundaries are unchanged.
- The visual introduction remains a standalone generated HTML file with no external scripts, fonts, or runtime dependencies.

### Release status

- Stable public release target: `2.4.0`.

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
