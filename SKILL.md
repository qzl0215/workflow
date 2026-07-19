---
name: workflow
description: 复杂任务的单技能总导演。用于多步骤、多需求、跨会话或需要从需求发现、方案与体验设计、计划、执行、调试、验证到交付的闭环；不用于纯问答、单文件小修或一次性轻操作。
version: 2.0.0-beta.1
author: qzl0215 and contributors
license: MIT
---

# workflow

workflow 是 dependency-closed 的复杂任务状态机。用户只安装本目录即可运行；根入口负责判级和路由，详细协议按当前阶段从包内 reference 读取。

## 不变量

1. 先查项目、工具和已有真源，只向用户询问会改变目标、取舍、验收或授权的未知。
2. 一次只推进当前阶段；出口不满足就回到产生缺口的阶段。
3. 视觉、交互或品牌任务必须先选定 Experience Design Contract，再写工程计划；非 UI 任务明确记录 N/A。
4. 能补现有真源就不建新文档；Readiness 最多在没有 owner 且确实阻断时创建一份入口文档。
5. 未经明确授权，不 commit、push、merge、deploy、delete 或触发其他外部副作用。
6. 没有 fresh verification 证据，不声称完成。

## 判级

- **轻任务**：答案明确、影响局部、可在一次安全操作内完成。直接处理并做相称验证，不立项。
- **标准任务**：需要多个相关步骤但单会话可闭环。只走必要阶段，计划可留在对话中。
- **项目任务**：跨文件、跨会话、多 Plan、并行、高风险或要发布。建立文件真源并维护状态。

## 状态接口与硬门

| 阶段 | Entry / Input | Allowed writes | Exit | Fallback |
|---|---|---|---|---|
| Intake | 新请求、现有对话与环境 | 轻任务不建档；项目任务只定位真源 | 已判级、判项目/用户级并识别事实缺口 | Context Discovery |
| Clarify | 请求、已证实事实、用户约束 | findings；项目任务可更新 task plan 范围 | 目标、关系、验收和授权边界足够 | Intake / Context |
| Readiness | 当前任务与下一阶段所需证据 | 默认 no-op；只 patch 现有真源，极端时一份入口文档 | 无需猜入口、约束、命令或验证路径 | Clarify / blocker |
| Solution | 需求、findings、readiness 证据 | findings 与 pre-plan contract | 推荐方案、边界、取舍和回滚点已收敛 | Clarify / Readiness |
| Experience | Solution Contract、现有设计真源 | 设计契约/预览；必要时补现有设计真源 | UI 已选型且状态齐；非 UI 已记录 N/A | Solution |
| Write | 已选 Solution + Experience/N/A | 五个计划真源；不写产品实现 | Plan/Task、owner、依赖、验收和验证可执行且已确认 | Readiness / Solution / Experience |
| Act | 当前 Ready Task 与确认计划 | Task 文件域、progress、唯一状态真源 | 产物完成并有 Task 级 fresh evidence | Debug / 上游缺口阶段 |
| Debug | 复现、错误证据、失败假设 | 可观测性、最小修复、progress | 根因已修复且复现/相邻回归转绿 | Act / 上游缺口 / blocker |
| Verify | 验收、实际 diff/产物、验证命令 | progress 证据；通过后更新唯一状态真源 | Task→Plan→整体均有 fresh evidence | Act / Debug / 上游缺口 |
| Finish | 已验证状态与明确授权 | 交付摘要、版本/迁移；仅执行已授权副作用 | 实际交付/发布状态、风险和下一步明确 | Verify / blocker |

严格顺序：`Clarify → Readiness → Solution → Experience/N/A → Write → Act ↔ Debug → Verify → Finish`。

## 按需路由

| 信号 | 仅读取 |
|---|---|
| 项目进场或下一阶段可能要猜 | `references/project-discovery.md` |
| 缺少项目、工具或环境事实 | `references/context-discovery.md` |
| 需求混杂、优先级或验收不清 | `references/clarify-prioritize.md` |
| 方案、架构、非功能边界未收敛 | `references/solution-design.md` |
| UI、视觉、动效、状态或无障碍范围 | `references/experience-design.md` |
| 需要建立或补齐长期设计真源 | `references/design-system.md` |
| 已有计划前契约，需要工程计划 | `references/write-plan.md` |
| 已有确认计划，需要逐 Task 实现 | `references/act-plan.md` |
| Task 可独立并行，或需要审查协作 | `references/delegation.md` |
| bug、测试失败、异常或连续失败 | `references/debugging-recovery.md` |
| 准备声明 Task、Plan 或整体完成 | `references/verification.md` |
| 准备交付、Git 操作、发布或总结 | `references/finish-release.md` |
| 上下文将满、跨会话或交接执行者 | `references/context-handoff.md` |
| 修改 workflow 自身或复盘可复用改进 | `references/evolution-loop.md` |

默认只加载当前阶段的一个 reference；只有记录了明确上下文缺口，才加载相邻阶段或更深证据。

## 文件真源

项目任务默认放在 `<project>/plans/<yymmdd-summary>/`：

- `task_plan.md`：范围、Plan/Task DAG、owner、验收和唯一状态真源。
- `findings.md`：证据、发现、方案比较与决策依据。
- `implementation-plan.md`：复杂任务的实施导航；不保存状态。
- `progress.md`：实际动作、失败、验证证据与 handoff。
- `index.md`：多个任务的发现入口；不是第二状态真源。

用户级任务使用用户明确指定或当前运行环境提供的数据目录，不假设固定用户名、绝对路径或公司文件系统。

## 角色与权限

- **Orchestrator**：判断阶段、维护 Ready Queue、分配 owner，并且唯一有权更新范围与状态真源。
- **Owner**：对一个 Plan 的业务结果、集成和 Plan 级验收负责；不能用 Task 绿灯替代 Plan 结果。
- **Worker**：只在 Task capsule 的文件域和授权内实现，返回 diff、证据、失败和上下文请求。
- **Reviewer**：从验收和 fresh diff 独立复核，重跑关键证据；不继承 Worker 的完成判断。

角色可以由同一 Agent 依次承担，但每次切换必须保留职责边界。任何角色都不能扩大用户授权。

## 能力降级

- 无 subagent：Orchestrator 以 solo 顺序执行同一 Task 契约，验收不降低。
- 无浏览器或图像能力：改用仓库证据、结构化设计 spec 和可运行预览；明确未做视觉实机检查。
- 无 memory：只以文件真源和当前对话恢复，不假设隐藏历史。
- 无 Git：仍可交付文件和验证证据，不伪造 commit、PR 或发布状态。
- 无执行工具或权限：停在可执行计划或 blocker，说明缺什么，不声称完成。

## 维护

修改本包前先进入路由表中的 Evolution 阶段。完成前运行 `python3 scripts/workflow_doctor.py` 及受影响测试；生成文档只从正式真源重建，不手改派生产物。
