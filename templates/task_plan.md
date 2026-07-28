---
id: <yymmdd-summary>
title: <business-title>
status: active
stage: 需求澄清
updated_at: <YYYY-MM-DD>
summary: <one-line outcome>
---

# 用户计划：<business-title>
<!-- 仅在需要持久恢复时创建。标准任务使用紧凑模式，只保留决策摘要、范围、验收、当前 Task、下一步和必要证据；复杂项目才配套 findings/progress。复杂实施才创建 implementation-plan。删除不适用章节。 -->

## Current Snapshot

- 当前阶段：需求澄清 / 选定方案 / 拆成任务 / 执行任务 / 验收交付 / 提炼经验 / 回灌改进
- 当前范围：待确认 / 已确认；纳入/暂缓哪些 Plan
- 活跃 Plan / Task：
- 最近完成：
- 下一步：
- Blocker：无 / Bxx
- 必跑验证：
- 当前风险：

## 阶段成果路由

每个已完成阶段最多一个活动入口；目标类型只允许 `document / visual / collection`，只保存项目相对路径。没有当前有效成果时不填占位行；上游变化后删除受影响的下游活动入口，历史证据留在 findings/progress。

| 阶段 | 目标类型 | 项目相对入口 |
|---|---|---|

## 1. 需求与边界

- 目标用户 / 场景：
- 期望业务结果：
- 关键约束：
- 明确非范围：
- 仍需用户纠正的理解：无 / …

## 2. 现状诊断

| ID | 差距 | 业务影响 | 判断 | findings 证据 |
|---|---|---|---|---|
| D01 | | | | E01 |

## 3. 验收标准

- 整体用户结果：
- 关键场景 / 边界：
- 跨 Plan 集成：
- 证据要求：实际输出只写 progress。

## 4. Plan Portfolio

状态只允许 `pending / in_progress / completed / blocked`；ID 只用于引用，不代表优先级。跨 owner 的实施状态只在目标项目维护，来源任务只记录提案决策、目标入口和最终回执。

#### P01｜<business-result>

- 来源：原始需求 / 回灌提案 / 外部 handoff
- 价值 / 解决的问题：
- 交付结果：
- 前置依赖：— / Pxx
- 业务 DONE：
- 范围决定：待确认 / 纳入 / 暂缓 / 不做
- 状态：pending

### 范围决策

| Plan | 必要性 | AI 建议 | 不做的损失 | 当前决定 |
|---|---|---|---|---|
| P01 | 必做 / 推荐 / 可选 | 纳入 / 暂缓 / 不做 | | 待确认 |

### Plan DAG

<!-- 仅在存在两个以上分支、汇合、跨 owner、共享资源竞争或表格无法直接表达的依赖时保留；不满足 DAG 触发门时删除本节。 -->

```mermaid
flowchart LR
  P01["P01｜result"] --> P02["P02｜result"]
```

## 5. Task Register

Ready 由“范围纳入 + 依赖 completed + 无 blocker + 授权具备”实时计算，不作为第五种状态。
单 Plan、少量串行 Task 默认只使用本紧凑 Task 表；仅在通过 DAG 触发门时增加局部 DAG。

| Task | 用户价值 / 产物 | 依赖 | 文件域 / 共享资源 | 上下文引用 | DONE / 验证 | 状态 |
|---|---|---|---|---|---|---|
| P01-T01 | | — | | `findings:E01`；复杂时 `implementation:P01-T01` | | pending |

## 6. 执行门槛
- 目标和边界已经看清；方案已经选定。
- UI 范围已有体验契约；非 UI 已记录不适用。
- Plan 范围已确认，依赖和 blocker 已闭合；每个 Task 有 owner、边界、DONE 和验证。
- 用户对“实施”的授权不自动包含 commit、push、merge、deploy、delete 或公开 release。

## Blockers

| ID | Plan / Task | 阻断事实 | 所需输入 / owner | 解锁证据 |
|---|---|---|---|---|

## Completed milestones

完成的 Plan/Task 只保留 1–3 行业务结果与证据入口；详细历史留在 Git 和 progress 的证据位置，不复制为归档章节。

| Plan | 业务结果 | 交付状态 | progress 证据 | 完成时间 |
|---|---|---|---|---|

## Plan 退休检查（仅在 Plan 完成或终止时保留）

只记录实际存在的结果；全部为“无”时保持五行，不展开分类矩阵。

- 长期知识：无 / `<使用场景 → 核心结论或行动 → 唯一真源 / 检索路径>`；必须通过消费价值与可发现性门才能进入长期知识层。
- 临时证据：已在验收和退休后及时删除。
- 例外保留证据：无 / `<不可重现原因 + 审计/回滚/事故恢复用途 + 现有证据系统入口>`。
- 未解决项：无 / `<仍影响恢复的事实>`。
- Plan 处置：活动 / 已退出默认上下文；保留 Plan / 等待精确删除授权 / 已授权删除。

未解决项仍影响恢复、例外证据没有现有恢复入口或无精确删除授权时，不得物理删除 Plan。

## 真源链接

- `findings.md`（复杂项目若存在）：证据与为什么。
- `progress.md`（复杂项目若存在）：实际发生、验证和 handoff。
- `implementation-plan.md`（若存在）：复杂任务怎么做；不保存状态。
