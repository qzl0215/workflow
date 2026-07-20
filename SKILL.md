---
name: workflow
description: 把复杂目标从“还没想完整”推进到“已经做完、验明白并让下一次更高效”的单技能工作流。它以阶段化、最小上下文和证据路由完成需求澄清、方案设计、计划编排、实施、验收、交付、复盘和受控进化；不用于纯问答或一次性小操作。
version: 2.1.0-beta.1
author: zhonglin
license: MIT
---

# workflow

workflow 是复杂工作的 AI 总导演。对使用者，它只承诺四件事：看清真正目标、给出推荐方向、持续做到并验明白、把有效经验留给下一次。对执行者，它把每个工作对象放入明确阶段，只提供完成当前职责所需的最小充分上下文。

本包 dependency-closed：用户只安装本目录即可运行，不默认存在其他 skill、脚本、人工 Reviewer 或特定平台能力。能由模型完成的判断交给模型；只有机械安全、状态唯一性、证据和授权属于硬约束。

## 总体方针

> 阶段明确，背景降噪，分工明确，深度发力。

- **计划前深度发力**：先调查、Grill、专家发散、体验设计和方案挑战，再拆任务；不能把方向性未知留给 Build。
- **阶段内专注**：一个 Cell 只处理当前阶段的问题，不预加载后续协议。
- **最小充分上下文**：不是越少越好，而是足以让责任角色独立说明目标、边界、输入、输出、验证和停止条件。
- **证据决定路由**：完成、回退、阻塞或分流都由 fresh evidence 决定，不由叙事、角色资历或阶段顺序推定。

## Workflow Cell

Workflow Cell 是最小工作单元，不是新文档。对复杂、委派或跨会话 Task，先从 Task 合同和当前运行状态生成一次性的执行上下文包：

```text
工作对象 + 当前阶段 + 最小上下文 + 责任角色 + 阶段能力
+ 权限边界 + 明确输出 + 通过证据 + 下一路由
```

每次派工或角色切换都生成一个有界执行上下文包，至少回答：

1. 当前处理哪个 Request / Plan / Task / Feedback；
2. 当前阶段只解决什么问题；
3. 已知输入和证据在哪里，哪些事实最易过期；
4. 谁对输出负责，可读、可写和禁止范围是什么；
5. 使用当前阶段的哪些内置能力，何时才加载条件协议；
6. 必须返回什么产物、fresh evidence、偏差、上下文缺口和下一路由。

执行上下文包从 `task.md` 或 Plan 内联 Task 合同、`progress.md` 当前切片和精确事实引用即时生成，不持久化、不保存第二份状态。上下文不足时只请求 `gap / target / expected_answer` 指向的切片；补足后停止扩张，不默认加载全聊天、全仓文档或其他阶段历史。

真源引用统一写成 `file@version#ID` 或 `file#heading`：ID 在目标文件内必须唯一，读取者先校验版本再精确搜索 ID；不得用宽目录引用代替“需要读什么”。目录确为边界时必须同时列出允许读取的文件集合或筛选条件。

## 契约与运行状态所有权

唯一真源不是“所有内容放进一个文件”，而是每类信息只有一个 owner。定义类文档只保存当前有效契约和版本，运行状态集中在 `progress.md`：

| 真源 / 对象 | 唯一拥有 | 不拥有 |
|---|---|---|
| **request.md / Requirement** | 真实用户、背景、原因、期望结果、需求关系、约束、授权和验收 baseline | 调查证据、最终方案、Task、stage/status、Feedback Queue |
| **findings.md / Evidence** | 事实、来源、推断、未知、Grill、专家结论、方案比较和决定依据 | 需求定义、最终批准方案、运行状态和执行日志 |
| **plan.md / Plan** | 完整批准方案、Plan Portfolio/DAG、Task stub、写域、依赖、集成和验收设计 | 实时 stage/status、blocker、执行流水和实际证据 |
| **task.md / Task** | 按需冻结的输入、输出、上下文引用、写 owner、边界、DONE、验证和停止条件 | 运行状态、其他 Task 范围和自行扩大的权限 |
| **progress.md / Runtime** | Request/Plan/Task 当前阶段与 lifecycle、Ready 派生视图、Blocker、Evidence Index、Feedback Queue 和 handoff | 需求、方案、Task 合同和完整日志 |

多 Plan 可以同时处在不同阶段，例如 `P01 验收、P02 执行、P03 等待外部输入`，都只在 `progress.md` 各对象行更新。Lifecycle 只表达 `pending / active / completed / superseded`；Ready 由纳入范围、合同版本、依赖、blocker、写域、资源、验证和授权实时推导，Blocked 由未关闭 Blocker 推导，二者都不另存为状态。

只有总协调者更新编排真源。Worker 只改执行上下文包授权的产品文件并返回结构化结果；总协调者校验 baseline/version、source fingerprint、DONE 和 fresh evidence 后更新 `progress.md`。Reviewer 从验收、实际 diff 和 fresh evidence 开始，不继承实现者的完成判断。

## 八阶段业务主链

阶段是当前工作对象的主问题，不是要求用户参加八次会议。输入和通过证据已存在时可以快速通过，但不能伪造未完成的判断。

| 阶段 | 允许进入该阶段的对象 | 业务问题 | 主协议 |
|---|---|---|---|
| 01 立项隔离 | Request | 从哪里安全开始？ | `references/01-start-request.md` |
| 02 看清需求 | Request / Requirement / Feedback | 真正要解决什么？ | `references/02-understand.md` |
| 03 选定设计 | Request / Plan | 做成什么样、为什么这样做？ | `references/03-design.md` |
| 04 计划编排 | Request / Plan | 怎样拆成可执行、低冲突的串并行工作？ | `references/04-plan.md` |
| 05 执行建设 | Task / Plan | 当前 Task 怎样做到并证明局部正确？ | `references/05-build.md` |
| 06 质量验收 | Plan | 当前独立结果是否简单、正确、完整？ | `references/06-verify.md` |
| 07 集成交付 | Request | 怎样把所有纳入 Plan 基于最新目标安全落地？ | `references/07-deliver.md` |
| 08 复盘升级 | Request / Plan | 什么应留下，哪里应永久变好？ | `references/08-review.md` |

这是对象—阶段的唯一兼容契约：Request 只进入 `01/02/03/04/07/08`，Requirement 与 Feedback 只进入 `02`，Plan 只进入 `03/04/05/06/08`，Task 只进入 `05`。任何路由都必须同时写明“创建/保持/重开哪个对象 + 目标阶段”，不能只写阶段号；Request 的 07 失败时保持 07 active 并建立 Blocker，同时重开受影响 Plan/Task，不把 Request 改成 05/06。

## 阶段硬门

| 阶段 | 必须通过的证据门 |
|---|---|
| 01 | 项目规则、基线、worktree/工作目录和外部权限明确，不覆盖现有改动 |
| 02 | 用户结果、验收、非范围、需求关系和关键未知足够清楚，能查的事实没有问用户 |
| 03 | 最终画面、选定方案、关键取舍、体验和回滚点清楚，方向性未知不留给实施 |
| 04 | 用户确认完整方案；每个 Ready 候选 Task 的结果/依赖/写域/DONE 足以消除冲突，需持久化的 Task 合同已冻结 |
| 05 | Task 产物满足验收，实际 diff 与 fresh 定向证据可复核 |
| 06 | simplify、AI review 与当前 Plan 业务验收覆盖实际影响面并 fresh 通过 |
| 07 | 所有纳入 Plan 通过；Request 基于最新目标集成，冲突按双方意图解决，rebase 后整体证据重验，副作用已授权 |
| 08 | 计划与实际完成偏差检查；晋升有复现、唯一 owner 和可失败验收，或明确 no-op |

未经明确授权，不 commit、push、merge、deploy、delete、公开发布或触发其他外部副作用。已有请求、项目规则或 active Plan 给出的明确长期授权不重复询问；未覆盖目标和破坏性例外仍停在授权门。

## 渐进式读取

根入口根据 `工作对象 + 当前阶段 + 触发信号` 只加载一个阶段主协议；条件成立时最多叠加本阶段所需协议。阶段文件只链接本阶段条件协议，不跨阶段深链。

| 阶段 | 条件信号 | 按需协议 |
|---|---|---|
| 02 | 存在会改变方向且无法自行发现的关键取舍 | `references/02-grill.md` |
| 02 | 执行或验收中产生一批新反馈 | `references/02-delta-intake.md` |
| 03 | 多路线、跨域、难逆或局部最优可能伤害全局 | `references/03-expert-forest.md` |
| 03 | UI、旅程、视觉、交互、动效或无障碍 | `references/03-experience.md` |
| 04 | 多 Plan、多 Ready Task 或需要多个 Agent | `references/04-coordinate.md` |
| 04 | 缺少会阻碍当前 Request 安全实施、验证、部署或交接的最小项目地基 | `references/04-foundation.md` |
| 05 | bug、测试失败、异常、空结果或连续失败 | `references/05-debug.md` |
| 06 | 存在非平凡代码 diff | `references/06-simplify.md` |
| 07 | Git 项目需要 commit、rebase、push 或 merge | `references/07-git-integrate.md` |
| 08 | 候选经验准备进入长期真源或修改本 workflow | `references/08-evolve.md` |

## Request 与 worktree

- 同一次用户触发中服务于同一交付意图的一串 Requirement 属于一个 Request，不按每条 bullet 新建 worktree。
- GitHub/GitLab 等 Git 项目的新写入 Request，先只读检查工作区和项目规则，fetch 最新远端跟踪分支，再创建一个 Request branch + worktree；不从可能过期的本地分支起步。
- 同一 Request 下的子 Agent 默认共享这个 worktree，不自行创建 worktree、commit、rebase 或 push。
- 计划阶段按文件、符号、生成物、lockfile、schema、build output、端口和 release candidate 划分写域；重叠写入合并为一个 owner 或串行。
- 验收中的相关缺陷、遗漏和同目标优化留在当前 Request；可独立交付且与当前目标弱相关的新目标建立新 Request 和新 worktree。
- 无 Git、纯只读或一次性轻操作时不为形式创建 worktree。

## 连续需求与最少交互

用户一次提出多项要求时，先建立 Requirement Ledger，再判断重复、包含、依赖、冲突、共享基础、可并行、互为备选或无关；之后组成可独立验收的 Plan，而不是“一句话一个 Task”。能查的事实由 AI 查，能并行回答的关键问题一次集中问。

Grill 上限是 **15 个问题，不是目标数量**；通常应更少。每题必须会改变目标、方案、Plan 分组、主要顺序、验收、授权或难逆风险，并提供推荐、互斥选项和默认行为。用户可以回复“全部按推荐”。

执行或验收中新反馈先冻结原验收基线并进入 `progress.md` 的 Feedback Queue，通过 Delta Intake 分类后路由：原验收缺陷重开 Task；设计遗漏升级 plan version；需求含义改变升级 request baseline；同目标优化新增 Task 或暂缓；新业务结果新增 Plan；不相关目标新建 Request。先更新定义和版本，再失效受影响 Task、重算 Ready；未受影响 Plan 保持原阶段。

## 最小文件真源

需要跨阶段、跨会话或多人协作的项目级 Request 默认位于 `<project>/plans/<request-id>/`。轻任务不建文档，短标准任务优先留在对话；其他文件在首次产生真实内容时再创建，不先铺满空模板：

```text
plans/<request-id>/
├── request.md
├── findings.md        # 有跨阶段复用的调查依据时
├── plan.md
├── progress.md
└── tasks/             # 有复杂、委派或跨会话 Task 时
    └── p01-t01.md
```

- `templates/request.md`：问题、Requirement、约束、授权和验收 baseline 的唯一 owner。
- `templates/findings.md`：事实、来源、推断、未知、专家结论、比较和决定依据；按需创建，不复制最终方案。
- `templates/plan.md`：一个 Request 的完整批准方案、Plan DAG、Task 顶层编排、冲突预防和验收设计；默认一份。
- `templates/progress.md`：所有对象运行状态、Blocker、Evidence Index、Feedback Queue 和 handoff 的唯一控制台；只保留当前快照，不写日志日记。
- `templates/task.md`：复杂、委派、跨会话或有写冲突风险的 Task 在派发前按需生成；一个稳定 Task 一份，不按 Agent 数量复制。

不默认建立 `evidence.md`、持久化 Capsule、每 Plan 进度、每角色或每 Agent 文档。完整命令输出、截图和构建物留在原始位置；`progress.md` 只存索引。复杂实施导航优先写入 Plan 局部章节或项目已有真源；信息只存一次，角色只接收当前 Cell 需要的引用切片。

Task 定义采用“合同晋升”而不是复制：生成 `task.md` 前，`plan.md` 的 inline contract 临时拥有结果、owner、写域、DONE 和验证；生成后，Plan 删除这些细节，只保留 Task ID、所属 Plan、依赖、波次和合同链接，完整定义由 `task.md` 唯一拥有。

## 降级与维护

没有独立 Agent 时，同一 AI 可以顺序承担专家、Worker、Reviewer 和 Integrator，但必须保持责任边界并如实标注；不默认需要人类 Reviewer。没有浏览器、Git、网络、memory 或执行权限时改变手段并声明未覆盖项，不降低验收，不把未验证写成完成。

修改本包必须进入 08 阶段：先写可失败验收，再改唯一 owner，并同步真实 reader、writer、测试和派生介绍。不得在 Python 中复制阶段、Reference、模板、角色、状态或业务语义注册表；语义判断和执行上下文包由模型从正式 Markdown 真源生成。
