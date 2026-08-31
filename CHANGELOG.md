# 变更记录

本项目的重要变化记录于此，并遵循语义化版本。

## [3.8.0] - 2026-08-31

### 干净验证失败自动恢复

- target-first 最终集成验证失败且现场仍干净时，自动回到原候选分支并清除临时集成状态，让修复后可以直接重新发布。
- 失败集成分支和完整失败日志继续保留用于诊断；候选提交和远端目标都不改写。
- 验证副作用、未解决冲突或进行中的 Git 操作仍保留原现场并失败关闭，不用自动恢复掩盖脏状态。

## [3.7.0] - 2026-08-31

### 原子发布与安全拒绝恢复

- 新增项目唯一发布入口，以最薄编排复用既有合并、完整发布门、不可变制品构建、GitHub Release 和本机同步责任者；完整测试只在最终集成 SHA 上执行一次。
- `safe_merge.py` 可把验证后的 target-first 集成 SHA 原子推送到目标分支和新版本标签；同版本并发只有一个赢家，标签已存在时失败关闭，不增加发布数据库或长期锁。
- 宿主实际拒绝外部写入后立即停止并保留候选；仅当拒绝明确允许授权解锁时，展示精确载荷、目标与后续动作。原契约未变化时不重走确认门，也不新增协议回执。

## [3.6.0] - 2026-08-31

### 持续推进与决策引导

- 协调者始终维护下一动作与责任者；只要仍有安全、已授权且可执行的路径，就继续推进，不把计划、子任务、测试绿灯、候选结果或进展汇报当成终点。
- 只有承重取舍、范围外授权或无法自行取得的外部输入才交回用户；可调查事实和契约内安全细节继续由模型解决。
- 每次真实交接把相关选择合并成一次紧凑决策包，提供推荐及理由、备选取舍、不决定的影响、最短回复与明确委托入口。

## [3.5.0] - 2026-08-31

### 确认驱动与回灌边界

- 所有状态变更任务显式经过需求澄清、需求确认，以及“局部适配型 Demo + 完整文字方案”的方案确认；请求表达和方案出现前的“开动”不再被推断为执行授权。
- 需求契约纳入关键取舍的逐项选择或委托；简单任务只有在需求理解把握超过 90%、无承重决策和冲突真源、局部可逆且无高风险副作用时，才能把两道确认门合并为一次。
- 长任务的 `work.md` 可记录 `requirement_receipt`、`solution_receipt` 和 `writeback_receipt`；执行与交付在凭证缺失、失效或身份不匹配时失败关闭。
- 完成陈述后分别识别项目级更新与 workflow 级更新；双 `no-op` 不要求回复，有候选时分别确认。回灌只建立独立新需求，不继承原任务授权，也不改写原任务完成事实。

### 存量项目初始化

- 新增兼容代际机器门、有界项目清单和首轮 AI 项目兼容改造指南；已登记当前代际的项目在常数级检查后退出，不因普通 workflow 版本或日常任务重复诊断。
- 初始化诊断覆盖 AI 真源导航、代码定位、验证效率、交付安全、提示词与模型配置、结构化输出、数据集、评测、追踪、复现和成本边界，并以 `comment_summary` 与 `ranking_app` 展示按真实缺口适配而非统一脚手架。

## [3.4.0] - 2026-08-31

### 最轻并行交付

- 只读任务不再承担 worktree 成本；写任务复用一个宿主隔离现场，首次写入前只对干净、未分叉的基线执行 fast-forward。
- `safe_merge.py` 进入精简运行时，提供 `--sync-baseline`，并以项目传入的 remote 和目标分支执行平台中立的 target-first 集成。
- 已被目标包含的候选直接返回 no-op；验证必须保持同一集成 SHA 和干净工作树，否则拒绝 push。
- GitHub/GitLab、仓库参数、验证和发布/reconciler 继续由项目真源持有；workflow 不再要求每个长期任务重复发现发布契约或创建第二个交付 worktree。

## [3.3.0] - 2026-08-31

### 完成后的自动优化识别

- 每个面向用户的目标完成并陈述结果后，自动进行一次最小优化识别；有可行动发现时展示问题诊断、推荐方案与验收，用户确认后再作为新目标实施。
- 浏览器视觉优化在方案确认前展示基于真实源码的局部视觉演示，目标区域承载变化，原页面其他元素继续复用。
- 成功验证在主上下文中保留范围、总结果与证据入口，失败时展开具体错误；本项目完整测试同步使用简洁输出。

## [3.2.0] - 2026-08-31

### 发布后启用

- Codex 本机发布完成后立即同步并验证活动 workflow，让 GitHub Release 与本机实际使用版本保持一致。
- 安装器支持 `--target codex`，由程序识别 Codex skills 目录，不把个人绝对路径写入项目真源。
- 登录时及每 24 小时的自动同步继续兜底；新任务使用磁盘上的新版本，已经打开的任务保留宿主已有上下文。

## [3.1.0] - 2026-08-31

### 确认驱动与上下文治理

- 结果契约默认只需要目标与验收；范围、授权、风险和其他边界只在确实会改变方案、执行或用户决定时补充。
- 首次状态变更前展示目标、推荐方案、验收和交付路径；用户确认、明确委托或说“开动”后形成方案就绪，并连续完成实施、验真与真实交付。
- 上下文压缩成为稳定治理信号，复盘检查工作规则、项目入口、信息冗余、唯一真源、导航和恢复成本；现有治理已经充分时仍可 `no-op`。
- 业务流中的每个动作都承载独立的结果、风险、可恢复性或证据价值；价值重叠的动作合并，没有消费价值的动作退役。
- 用户文字以真正看懂和帮助决策为目的，优先使用熟悉的词与具体结果，专业术语先解释实际含义再按需保留。

## [3.0.2] - 2026-08-31

### 现有页面局部修改

- 默认在真实源码中划定改动面与保护面，并优先通过复用真实登录态的只读独立验收入口展示同一候选；本地样例不冒充身份、权限或真实数据链路证据。
- 保护面以继续复用原实现来证明结构性保真，只验证受影响入口与高风险连接点，不做全量人工前后对比；独立概念稿仅用于确有承重方向分歧的探索。

## [3.0.1] - 2026-08-31

### 用户汇报

- workflow 启动后的首次进展、环节实质变化、真实阻断、最终交付和交回控制权，强制使用“结论 + 进度 / 技能 / 成果 / 路径”画面；状态不变仍不重复，轻量任务可只在最终出口展示一次。
- 用户主视图先表达业务结果、实际影响、可用状态、风险和必要行动，不再用文件数量、`runtime`、`Manifest`、`doctor`、测试命令、哈希或内部编号冒充成果。
- 技术事实继续作为可追溯证据保留，但只有影响决定、风险或可信度时才展开，并先翻译它对用户意味着什么。

## [3.0.0] - 2026-08-28

### 核心协议

- 将用户可见主链收束为“目标框定 → 结果规划 → 任务执行 → 结果验真”，真实交付与经验复盘改为由结果触发的条件环节。
- 参考能力改为按需进入、按真实信号加深并在充分时返回的渐进路由；不要求统一章节或文件形态，也不再固定题数、轮数、智能体数量、重试次数或唯一执行方法。
- 将最小研究、深度质询和体验探索放回目标框定：通常先取得最少必要事实，承重决定仍不稳才质询，体验会改变方向才探索；只在独立且有净收益时并行取得候选输入。
- 保留 `grill-me` 兼容入口，并把它明确为对承重假设、反例、失败代价和可逆替代方向的深度挑战，而非固定问卷。

### 规划、执行与验真

- 结果规划从验收反推责任；任务编排依据依赖、写入隔离、共享资源和汇合成本选择串联或并联，不按文件数或可用智能体数量机械拆分。
- 每个子任务依据自身未知、可逆性、影响面和失败代价独立确定思考与验证深度；父计划复杂度不再替子任务预设深浅。
- 明确“任务胶囊 → 候选回执 → 协调者接受”的协作边界；胶囊与回执携带目标、父计划和任务契约身份，执行者自报和子任务绿灯不能替代整体验真。
- 证据按结果、输入、环境和作用域复用；相关输入未变时避免重复完整检查，跨真实环境边界时仍要求新鲜验证。

### 工作真源与汇报

- 用协调者独占的稀疏 `work.md` 取代五份重复状态文档；任务胶囊和执行回执默认内联，仅在跨上下文、复杂协作或昂贵证据需要恢复时物化。
- 候选与已接受事实严格分离，子任务执行者不得并发改写控制面。
- 保留“进度 / 技能 / 成果 / 路径”四行阶段画面，只在实质状态变化、真实阻断或交回控制权时更新。

### 交付、复盘与分发

- 有真实复用价值信号时默认 `prove → deliver → learn`；没有信号就跳过复盘。等待交付时可并行收集不依赖最终状态的复盘候选，但最终经验只能在真实交付事实确定后接受。
- 3.x 发布资产改为 manifest 声明的精简运行时；`workflow-package.json` 固定逐文件 SHA-256、运行时 doctor 与源码专用文件边界。
- 2.26.x 安装可直接同步到 3.x；错过 2.26 的旧更新器对未知精简包失败关闭并保留原安装，用户需使用已验证的 3.x 安装器整体替换后重新检查。
- 对外文档和可重复生成的视觉地图同步展示完整 3.0 改造画面。

## [2.26.0] - 2026-08-28

### Added

- Added the compatibility bridge for future slim runtime packages: an exact `workflow-package.json` file set, per-file SHA-256 verification, and one manifest-selected runtime doctor.
- Added bounded member-by-member Release extraction that rejects traversal, duplicate or case-colliding paths, links, special files, encrypted members, ambiguous roots, and oversized payloads.

### Changed

- Staged candidates once on the destination filesystem and activated them with a rename transaction that restores the previous installation after caught post-swap failures.
- Kept the exact 2.25 public payload unchanged so every existing updater can acquire this bridge before the 3.0 package becomes slim.

## [2.25.0] - 2026-08-28

### Changed

- Routed user attention through one load-bearing decision tree: contract-changing choices use explicit selection or free-form answers, while safe contract-local details are selected by AI and shown for adjustment.
- Batched every currently reachable independent decision, expanded dependent children after their parent answers, and used contract stability to determine when questioning is complete.
- Unified the current protocol across the root router, requirement owner, README, findings template, visual introduction, tests and provenance.

## [2.24.0] - 2026-08-28

### Added

- Added four high-level design uplift principles to experience shaping: find the right opportunity, make it useful before making it beautiful, address root causes instead of stacking safe patches, and explore broadly before focusing on one direction.
- Kept the capability inside the existing experience owner without importing a second design workflow, project-specific mechanics or extra artifacts.

## [2.23.0] - 2026-08-25

### Changed

- Made existing-page enhancement the default UI path: visual decisions now use a reversible implementation preview on the real route, owner, components and tokens, and the approved patch continues into implementation instead of being recreated from a demo.
- Limited standalone visual demos to genuine direction exploration, while preserving the three progressive exploration gates when information architecture, shell or visual direction is actually undecided.
- Added scope-drift guards for navigation, summary hierarchy, table density, filter placement and other non-target structures, plus reader contracts that carry the approved preview through planning, execution and verification.

## [2.22.0] - 2026-08-25

### Changed

- Compressed fully successful delivery reports into one linked sentence covering the GitHub commit, merge and publication; incomplete or failed delivery still reports the true gap and required next action.

## [2.21.0] - 2026-08-18

### Changed

- Made visual hierarchy, layout, state, graphics and interaction the default explanation layer for UI work, instead of repeating those relationships in titles, subtitles or helper copy.
- Compressed the content-design gate from five rules to three while retaining deletion, five-second scanning, accessibility and risk safeguards.

## [2.20.0] - 2026-08-01

### Added

- Added a user-centered content design gate for UI work, including purpose/state/action scanning, copy deletion tests, visual substitution and accessible fallbacks.

### Changed

- Required visible titles, sections, actions and helper text to use the shortest wording that preserves understanding, while retaining complete legal, risk and complex-help meaning through progressive disclosure.
- Routed content design through the existing experience-shaping owner instead of adding a separate copywriting module or global character limits.

## [2.19.1] - 2026-08-01

### Changed

- Required an updated full progress snapshot at the top of every response that hands control back and waits for the user, including H0/H1 and unchanged state.

## [2.19.0] - 2026-08-01

### Added

- Added immutable safe-merge receipts with phase timing and verified-SHA transport retry; transient push failures no longer rerun an unchanged RC.
- Added explicit release-doctor handoff requirements and telemetry-aware retrospective evidence routing.

### Changed

- Standardized delivery ordering as focused checks, semantic/security review, exact candidate commit, target-first integration, one clean RC, fast-forward, deploy and online smoke.
- Removed legacy external submission harnesses from workflow delivery routing; workflow now uses one project-native release harness or its own exact-file and safe-merge path.
- Compressed successful verification output and limited failure expansion to a bounded tail plus an artifact path.

## [2.18.1] - 2026-08-01

### Changed

- Enforced serial, current-stage-only loading: downstream owners, harnesses, design rules and code context cannot be preloaded merely because they may be useful later.
- Gated experience shaping on a confirmed requirement and a direction-changing UI decision; annotated, direction-setting references now use the existing fast path.
- Added the minimal Git freshness fingerprint and heading/symbol-first investigation rule, so dirty working-tree code is included without loading whole plans or large source files.

## [2.18.0] - 2026-07-31

### Changed

- Made workflow the single generic owner for state-changing work; overlapping standalone skills remain available only as explicit compatibility entries.
- Added a compact H0/H1 path that reports only start, real blockers and completion while retaining full snapshots for H2/H3 and handoffs.
- Moved ownership/preflight checks ahead of complete verification when file topology changes, and limited each final source identity to one successful full RC.
- Kept delivery state in Git, manifests and runtime evidence instead of creating documentation-only closure commits.

### Compatibility

- Existing standalone skill files and bodies are retained during the compatibility period; explicit legacy invocations continue to work.

## [2.17.0] - 2026-07-30

### Changed

- Integrated load-bearing decisions, their frontier and the recommended requirement contract into the existing requirement owner and findings source.

### Compatibility

- Existing requirement findings reuse the current remaining-branch field; no migration or new persisted mode is required.

## [2.16.0] - 2026-07-29

### Added

- Added one decision-value filter for all user-visible content, prioritizing user outcomes, actual effects, real costs, key risks and necessary actions.
- Added regression coverage that keeps decision, action, risk and confidence impact as the cross-domain test for whether detail belongs in the main response.

### Changed

- Made technical process and other detail opt-in unless it changes a decision, action, risk assessment or confidence in the conclusion.
- Compressed the existing handoff contract so the new behavior adds no reference, stage, fixed response template or root context cost.

### Compatibility

- Existing status snapshots and action exits remain available, while failures, authorization boundaries and necessary evidence cannot be hidden by concise reporting.

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
- Routed requirement research into one complete recommended contract with explicit user decisions and visible AI-selected details.
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
- A project-scoped standing release authorization for verified `workflow/` changes, allowing commit, push, mainline integration, and publication without repeated approval while retaining P0, scope, and no-force gates.

### Changed

- Made the requirement card a post-clarification result instead of a speculative discovery substitute.

### Fixed

- Prevented standard and project work from skipping user judgment and immediately emitting a completed requirement card.
- Prevented AI recommendations, silence, and vague agreement from being persisted as confirmed user requirements.

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
