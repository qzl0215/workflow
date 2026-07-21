# workflow

把一句还没想完整的复杂需求，推进成已经做完、验明白，并让下一次更省事的结果。纯问答、单文件明确小修和一次性轻操作默认不触发；显式调用时也只走零额外仪式的轻路径。

当前协议版本：`2.1.0-beta.3`。

你只需要说目标。workflow 会先查事实、收敛真正需求与推荐方案，再把工作编排成可验收的 Plan 和 Task，持续实施、验收、处理反馈，并把值得复用的经验写回正确位置。

它是 dependency-closed 的单 Skill：不默认安装任何其他 skill、脚本或特定平台能力；有用户指定或宿主原生能力时优先使用，缺失时才加载包内一个最小 fallback。

[下载或本地打开可视化 HTML](docs/index.html)

## 你会感受到什么

- **先查再问**：能从项目、文档、代码和可用工具确认的事实不重新问你。
- **先给推荐**：只有真实业务取舍才让你选择；安全、可逆且方向明确时给出默认并继续。
- **小任务不被流程化**：根协议足够判断时直接做；零文档、零子 Agent、零额外确认、零机械 worktree，只做一次相称验证。
- **一次批准后持续推进**：正式计划只设置一次开工批准，之后持续做到 AI 验收和授权范围内的交付。
- **结果和进展不打架**：需求、正式方案、复杂实施合同、当前进展各有唯一真源。
- **变化只重验影响面**：证据仍覆盖当前对象和输入时复用；发生实质变化时只重验受影响路径。

## 七阶段与一个开工门

| 阶段 | 只解决什么 | 典型产出 |
|---|---|---|
| 01 看清需求 | 为谁解决什么，边界、验收和最贵未知是什么 | 需求 baseline、事实、推断、未知、需求确认卡 |
| 02 方案选型 | 最终做成什么样，为什么选择这条路线 | 推荐方向、最终 PRD / 体验草案、决定依据 |
| 03 计划编排 | 怎样拆成低冲突、可验收的 Plan 与 Task | 在既有安全计划区或对话形成 Plan Portfolio、P-DAG、Task 业务索引、按需复杂合同 |
| ◆开工门 | `plan_mode / approval_state` 是否允许写入，当前现场与基线是否安全 | 通过后才建立或确认相称隔离并开始产品写入 |
| 04 执行建设 | 当前 Task 怎样做到并证明局部正确 | 实现产物、结构化返回、局部验证 |
| 05 质量验收 | 当前结果是否简单、正确、完整 | AI 复核、代码瘦身、fresh 验收 |
| 06 集成交付 | 怎样基于最新目标安全落地 | 冲突理解与合成、集成验证、授权内交付 |
| 07 复盘升级（有信号才进入） | 什么应留下，哪里应永久变好 | 项目事实回写、可复用经验、受控进化；无信号直接 no-op 结束 |

阶段是 AI 的责任边界和问题索引，不是多次会议或必须逐个加载的文件。根协议与现有证据足够时，一次连续执行可快速通过多个阶段。简单、可逆、无需正式计划的任务记录 `plan_mode=inline / approval_state=not-required`，用户原始执行请求直接作为范围内本地实施授权，不增加确认仪式或独立需求卡；正式路径从选择之时起就是 `plan_mode=formal`，草案无论只在对话、还是用户或宿主提供的一个既有安全计划区，都必须 `approval_state=approved` 才能开工。开工门先复用 Codex thread、用户或兼容 harness 已提供且满足归属、隔离和最新基线的工作现场；只有现有现场不足时才新建 Request branch / worktree。批准版计划只在需要迁移时原子迁入并删除临时草案，不保留两份可编辑副本，随后才开始首次实现写入。

## 四份唯一真源

需要跨会话恢复、长期持久化或多人协作的 Request 使用 `<project>/plans/<request-id>/`。只有内容真实需要持久化时才建文件：

```text
plans/<request-id>/
├── findings.md
├── task_plan.md
├── implementation-plan.md   # 仅复杂实施按需创建
└── progress.md
```

| 文件 | 面向谁 | 唯一拥有 | 不保存什么 |
|---|---|---|---|
| `findings.md` | 人与 AI | 完整需求 baseline、背景、事实、推断、未知、授权与方案依据；顶部字段直接渲染“需求确认卡｜我将按此继续” | 最终 PRD、任务编排、运行进展 |
| `task_plan.md` | 人 | 一屏决策、最终 PRD / 体验方案、范围、Plan Portfolio、P-DAG、Task 业务索引、所有 Plan / Task 依赖与波次、规划基线和正式批准状态 | 第二份授权事实、执行阶段、工作项状态、实际验收结果 |
| `implementation-plan.md` | AI | 从已批准计划派生的只读 P/T DAG，以及复杂 Task 的输入、写域、DONE、验证、停止条件合同 | 简单 Task、拓扑决定、运行进展、实际验收结果 |
| `progress.md` | 人与 AI | “当前 / 工作进展 / 验收记录”三块最新快照 | 第二份定义、派生调度表、事件日记、完整日志 |

不为迁移制造兼容副本，也不默认建立每 Plan、每 Agent、每证据或每次交接的文档。完整日志、截图和构建物留在原产物位置，四份真源只保存可决定下一步的信息。

四个模板都是菜单，不是待填满的表单：只保留当前 Request 的真实章节、节点和字段；不存在的 Plan/Task、空表和占位内容必须删除。

## P / T 双 DAG 怎样读

`task_plan.md` 是 Plan / Task 依赖、波次与汇合拓扑的唯一 owner。它先展示 P-DAG：每个 `Pxx` 是一个可独立验收的业务结果，边表示业务结果的依赖和汇合。

复杂实施再由 `implementation-plan.md` 展示从已批准计划派生的只读双图：先看 P-DAG 的业务结果全景，再看按 Plan 分组的 T-DAG。每个 Task 带执行波次；同波次、无依赖的节点可并行，Plan 内边留在组内，跨 Plan 边明确写在组外。图节点与摘要表中的 `Pxx / Pxx-Txx` 都必须能点击定位同 ID 摘要或合同；拓扑变化先更新 `task_plan.md`，再同步派生图与受影响合同。

简单 Task 直接在 `task_plan.md` 的业务索引中写最小 inline 约定。只有需要委派、跨会话、复杂依赖或高写冲突控制的 Task 才展开完整合同；一个 Request 只使用一份 `implementation-plan.md`，不按 Agent 数量复制。

## 用户交互预算

- 看清需求结束时，如果关键事实已查清、剩余假设都有安全可逆默认，workflow 从 `findings.md`（简单路径则从当前对话事实）展示一张简短的“需求确认卡｜我将按此继续”，不问泛化的确认问题，随后自动进入方案选型。
- 只有答案会改变用户结果、范围、验收、授权或难逆风险且没有安全默认时才暂停。一轮围绕一个决策主题，通常只问 1–3 个互斥问题，并说明推荐与影响。
- 存在必须由人承担的体验、成本、风险或难逆方向取舍时，在方案选型阶段呈现最合适的选择材料并等待一次决定；已选方向不在正式计划中重复询问。
- 选择正式计划路径时，用户一次批准需求 baseline、最终方案、范围和编排；批准门不取决于 `task_plan.md` 是否已经落盘。开工后默认连续推进，只有新的业务契约变化、未授权外部副作用或没有安全默认的难逆决定才中断。
- 用户只要求计划时，交付计划后结束，不进入开工门或实施。
- 验收反馈先按缺陷、遗漏、同目标优化、新 Plan 或新 Request 分类；未受影响工作继续，不把每条反馈直接塞进正在执行的 Task。

## Native-first 与安全降级

同一关注点只保留一个方法 owner：

1. 用户明确指定方法时遵循用户选择，并让结果回到四份真源。
2. 否则，宿主已有设计、协作、调试、验证、浏览或 Git 等原生能力时，直接使用对应原生能力。
3. 业务阶段协议只给边界和输出；宿主缺少某项方法时，才为该关注点加载包内一个最小 fallback。命中原生能力后不执行、不叠加同类 fallback。

这种选择不创建第二份计划、状态或确认，也不把任何外部 skill 写成运行前提。没有独立 Agent 时，同一 AI 可以顺序切换责任角色并如实标注；没有浏览器、Git、网络或权限时，明确未覆盖项，不伪造结果。

## 并行与最小上下文

默认 solo。UI、多文件、阶段数量或概念角色都不能单独成为派 Agent 的理由；只有独立决策、独立写域或高风险 fresh 证据的收益明确高于派发、等待、整合与复核成本时才并行，收益消失立即收敛。

同一 Request 的协作者默认共享开工门确认的一个工作现场；需要 worktree 时也只共享这一份。总协调者唯一维护四份真源和 Git 生命周期；执行者不自行创建工作区、commit、rebase、push，也不越过合同写域。

只有依赖独立、写域和共享资源不冲突、验证环境可并行且收益为正的 Task 才并行。同文件不同区域、共享 schema/API、lockfile、migration、生成物和 release candidate 默认合并 owner 或串行。

复杂 Task 只获得其版本化合同、`progress.md` 当前切片和精确事实 / 代码引用；缺什么只请求具体 gap，不默认加载完整需求、专家讨论或其他 Task 历史。

## 安装与自动更新

仓库和运行包都是零 Python。你只需要一个能操作本地文件的 Agent。

### 推荐：发给 Agent 的一句话

第一次发送会安装，以后再次发送同一句会自动更新：

> 请从 `https://github.com/qzl0215/workflow` 安装或更新 workflow：先唯一定位你当前实际使用的 skills 目录，无法唯一定位就停止；把最新 main 解析成一个不可变 commit SHA，再从同一 SHA 将 `SKILL.md`、`references/`、`templates/` 和 `tests/scenarios.md` 下载到临时目录，校验版本、必需文件与全部本地引用后，再原子替换 workflow；有旧版先整体备份，更新失败恢复备份，首次安装失败删除未完成目录；最后报告版本、来源 commit 和安装位置，不要猜固定目录。

Agent 只把根协议、阶段 references、templates 和按需维护契约 `tests/scenarios.md` 放入实际使用的 `workflow` 目录；README、HTML 和其他仓库维护文件不会进入日常运行上下文。

## 开始使用

安装后直接描述目标：

> 用 workflow 推进这个需求。先查项目和现有事实；只有会改变结果且没有安全默认的决定才问我。先给推荐方向，需要正式计划时让我一次批准需求、最终方案、范围和编排；批准后持续实施和验收，直到证据覆盖当前对象、输入、环境与验收，并在我的授权范围内交付。

## 安全边界

- 能自行发现的事实不会重新问用户。
- 未经明确授权，不 commit、push、merge、deploy、delete 或公开发布。
- 没有与当前对象、输入、环境和验收匹配且仍有效的证据，不声称完成。
- 目标分支或实质输入变化后，只让受影响证据失效并 fresh 重验相关路径。
- 没有复用证据，不把一次经验永久写进 workflow。
- 项目地基只补当前交付真正需要的入口、导航或设计契约，不默认铺治理文档。

## 维护检查

把下面一句交给 Agent：

> 请维护检查当前 workflow 仓库：以 `SKILL.md`、阶段 `references/`、`templates/` 和 `tests/scenarios.md` 为真源，检查 frontmatter、全部相对引用与文件可达性、版本和安装提示词同步、零 Python、敏感信息、冲突标记及实际 diff；再逐项判断受影响行为场景能否从协议导出，给出通过、失败、证据位置和最小修复建议，不要只做关键词匹配。

MIT licensed. <sub>Maintained by zhonglin.</sub>

## English

`workflow` turns an incomplete request into a verified delivery through seven stages and one explicit start gate. Four sources of truth hold the requirement baseline and findings, the human-approved PRD and orchestration, complex AI-facing Task contracts, and the current progress snapshot. It prefers user-selected or host-native capabilities, loads one minimal fallback only when needed, and never treats another skill as a prerequisite.
