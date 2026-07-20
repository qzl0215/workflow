---
name: workflow
description: 把复杂目标从“还没想完整”推进到“已经做完、验明白并让下一次更高效”的单技能工作流。它以阶段化、最小上下文和证据路由完成需求澄清、方案设计、计划编排、实施、验收、交付、复盘和受控进化；不用于纯问答或一次性小操作。
version: 2.1.0-beta.2
author: zhonglin
license: MIT
---

# workflow

workflow 是复杂工作的 AI 总导演。对用户只承诺四件事：看清真正目标、给出推荐方向、持续做到并验明白、把有效经验留给下一次。

本包 dependency-closed：只安装本目录即可运行，不默认存在其他 skill、脚本、人工 Reviewer 或特定平台能力。能由模型判断的交给模型；安全、状态唯一性、证据与授权才设硬门。

## 运行原则

> 阶段明确，背景降噪，分工明确，深度发力。

1. **先调查再提问**：先读可用记忆、项目规则、代码和文档；只把会改变方向且无法可靠发现的决定交给用户。
2. **计划前想透**：需求、验收、专家挑战、体验和关键取舍在 Build 前收敛，不让执行者猜方向。
3. **阶段降噪**：按 `对象 + 阶段 + 触发信号` 只加载一个主协议和必要条件协议；角色只读合同、当前状态切片和精确证据。
4. **唯一 owner**：每类定义、运行状态和写域只有一个 owner；总协调者维护编排，Worker 不越权。
5. **证据与授权守门**：可复核证据决定路由；未经明确授权，不 commit、push、merge、deploy、delete、公开发布或触发其他外部副作用。

## 按难度投入：H0–H3

选择能守住结果的最低级别；出现新风险再升级。

| 级别 | 适用情况 | 默认投入 |
|---|---|---|
| **H0 快速通过** | 答案和证据已存在，无新取舍、写操作或过期事实 | 复核现有证据；不建文档、不派 Agent、不重跑相同检查 |
| **H1 标准推进** | 单一、清楚、可逆、局部 | 一个 owner；对话内短计划；定向实施与责任切换复核 |
| **H2 深度协作** | 多 Plan、重要取舍、跨域、体验方向选择或并行 Agent | 定向调查、2–3 个视角、按需真源、完整方案、独立复核 |
| **H3 高风险交付** | 难逆迁移、安全或高影响发布、重大数据/业务风险 | 3–5 个独立视角与交叉挑战、正式确认、回滚与交付证据 |

明确要求 Grill、专家圆桌/森林、视觉选型或多 Agent 时至少 H2；完整专家会议使用 H3 机制。H0/H1 无方向性未知时，明确执行请求可作计划授权；H2/H3 先用业务语言和必要可视化确认完整方案。开工后持续到 AI 验收和授权内交付，只有重大未授权决策才中断。

## 最小工作单元

Workflow Cell 是运行时交接，不是新文档：

```text
工作对象 + 当前阶段 + 最小上下文 + 责任角色 + 阶段能力
+ 权限边界 + 明确输出 + 通过证据 + 下一路由
```

复杂、委派或跨会话 Task 从合同、`progress.md` 当前切片和精确引用即时生成 Cell，不保存第二份上下文包。缺信息只请求 `gap / target / expected_answer`；引用用 `file@version#ID` 或 `file#heading`。

定义与状态分工：

| 真源 | 唯一拥有 |
|---|---|
| `request.md` | 用户、背景、原因、需求、约束、授权、验收 baseline |
| `findings.md` | 事实、来源、推断、未知、专家综合与决定依据；按需创建 |
| `plan.md` | 确认方案、Plan/Task 顶层编排、写域、依赖与验收 |
| `task.md` | 复杂/委派/跨会话 Task 的执行合同 |
| `progress.md` | 阶段/lifecycle、Ready、Blocker、证据索引与反馈队列 |

只有总协调者更新编排真源。Worker 返回实际变更、证据、偏差和 gap；Reviewer 从验收、diff 和证据开始。Lifecycle 只用 `pending / active / completed / superseded`；Ready/Blocked 实时推导。

## 八阶段业务路由

阶段是当前对象正在解决的业务问题，不是八次用户会议。证据已存在时快速通过。

| 阶段 | 对象 | 只解决什么 | 主协议 |
|---|---|---|---|
| 01 立项隔离 | Request | 从哪里安全开始？ | `references/01-start-request.md` |
| 02 看清需求 | Request / Requirement / Feedback | 真正要解决什么？ | `references/02-understand.md` |
| 03 选定设计 | Request / Plan | 做成什么样，为什么？ | `references/03-design.md` |
| 04 计划编排 | Request / Plan | 怎样拆成低冲突、可验收的串并行工作？ | `references/04-plan.md` |
| 05 执行建设 | Task / Plan | 当前 Task 怎样做到并证明局部正确？ | `references/05-build.md` |
| 06 质量验收 | Plan | 当前结果是否简单、正确、完整？ | `references/06-verify.md` |
| 07 集成交付 | Request | 怎样基于最新目标安全落地？ | `references/07-deliver.md` |
| 08 复盘升级 | Request / Plan | 什么应留下，哪里应永久变好？ | `references/08-review.md` |

对象兼容：Request → `01/02/03/04/07/08`；Requirement/Feedback → `02`；Plan → `03/04/05/06/08`；Task → `05`。路由写明“创建/保持/重开哪个对象 + 目标阶段”。进入、退出和失败处理只读对应主协议。

## 条件协议：用到才读

| 阶段 | 触发信号 | 叠加协议 |
|---|---|---|
| 02 | 存在会改变方向且无法自行发现的关键取舍 | `references/02-grill.md` |
| 02 | 执行或验收中产生一批新反馈 | `references/02-delta-intake.md` |
| 03 | H2/H3、多路线、跨域、难逆、局部最优可能伤害全局，或用户要求 | `references/03-expert-forest.md` |
| 03 | 存在旅程、视觉、交互、动效或无障碍方向取舍 | `references/03-experience.md` |
| 04 | 多 Plan、多 Ready Task 或需要多个 Agent | `references/04-coordinate.md` |
| 04 | 缺少会阻碍本 Request 实施、验证、部署或交接的最小项目地基 | `references/04-foundation.md` |
| 05 | bug、测试失败、异常、空结果或连续失败 | `references/05-debug.md` |
| 06 | 存在非平凡代码 diff | `references/06-simplify.md` |
| 07 | Git 项目需要 commit、rebase、push 或 merge | `references/07-git-integrate.md` |
| 08 | 候选经验准备进入长期真源或修改本 workflow | `references/08-evolve.md` |

## 证据新鲜度与复用

证据身份是 `被验对象/产物 + 输入/依赖 fingerprint + 环境 + 命令/场景 + 验收 baseline`，并记录观测时间与有效条件。fresh 表示证据仍覆盖当前判断，不等于每阶段重跑。

- 只有确定性检查、全部实质输入已指纹化、有效条件仍成立且原始结果可复核时才复用；任一项变化，只重跑受影响路径。
- API/远端分支/凭证权限/线上数据/安全状态等外部可变事实，在依赖该事实的决策点重新观测，不能只凭旧 fingerprint 复用。
- Rebase/冲突修复改变 fingerprint；重验受影响 Plan、跨 Plan 集成和 Request 关键路径。
- 发布仍需远端/产物证据；本地绿灯不能替代交付证明。

## Request、并行与反馈

- 同一触发、同一交付意图的一串 Requirement 属于一个 Request。Git 新写入 Request 先只读检查、fetch 最新目标，再建一个 branch + worktree；不覆盖用户改动。
- 子 Agent 默认共享 Request worktree，不自行建 worktree 或操作 Git。计划先划写域；重叠写入合并 owner 或串行。
- 多项需求先编号、查事实和关系，再组成 Plan；Grill 最多 15 问且通常更少。新反馈冻结原 baseline 后走 Delta Intake：缺陷重开 Task，设计/需求变化先升级真源，同目标优化进当前 Plan，新结果建 Plan，弱相关目标建 Request；未受影响工作继续。

## 最小文件预算

跨阶段、跨会话或多人协作才使用 `<project>/plans/<request-id>/`；H0/H1 优先留在对话。文件有真实内容时才建：

```text
plans/<request-id>/
├── request.md
├── findings.md        # 按需
├── plan.md
├── progress.md
└── tasks/             # 按需
    └── p01-t01.md
```

模板：`templates/request.md`、`templates/findings.md`、`templates/plan.md`、`templates/progress.md`、`templates/task.md`。不默认建 evidence、Capsule、每 Plan/角色/Agent 文档；日志和产物留原处，`progress.md` 只存快照与索引。Task 采用合同晋升：生成 `task.md` 后，Plan 只保留 ID、Plan、依赖、波次和链接。

## 降级与维护

没有独立 Agent 时，同一 AI 可顺序承担专家、Worker、Reviewer 和 Integrator，但保持责任切换并如实标注；不默认需要人类 Reviewer。没有浏览器、Git、网络、memory 或执行权限时改变手段并声明未覆盖项，不降低验收，不把未验证写成完成。

修改本包必须进入 08 阶段：先在按需安装的 `tests/scenarios.md` 写会失败的行为场景，再改唯一 owner，并同步真实 reader、writer、README 和 HTML。仓库保持零 Python、零生成注册表；Agent 直接检查 frontmatter、相对引用、可达文件、版本、安装提示词同步、敏感信息、冲突标记、行为场景与实际 diff。语义判断由模型从正式 Markdown 真源完成。
