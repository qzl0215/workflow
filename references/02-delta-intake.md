---
kind: conditional
stage: 02
---

# 02 条件｜变化需求接入

## 触发

Build、Verify、交付或用户验收中出现一项或一串新要求、修正、优化建议或与当前工作弱相关的新目标时触发。

## 最小上下文与角色

需求 owner 只接收冻结的原验收 baseline、新反馈原话、`progress.md` 当前对象状态、相关 diff 和影响证据；不默认读取全部历史。总协调者唯一更新 Feedback Queue、定义版本和路由。

## 做法

1. 先冻结当前 request baseline、plan version 和已通过证据，在 `progress.md` 为每条反馈建立稳定 Feedback ID；分类前不直接修改定义或代码。
2. 对每条反馈查项目事实，澄清期望结果、影响范围和与既有 Requirement 的关系；关键问题一次集中 Grill。
3. 分为五路：
   - **原需求未满足**：不是新范围，不升级 baseline/version；重开原 Task，Plan 回 05；
   - **方案/体验遗漏**：仍属原目标，升级受影响的 plan version，Plan 回 03；
   - **同目标小幅优化**：在当前 Plan 增加 Task、安排后续或明确不做；
   - **新业务结果**：同一最终交付意图下先建立 Requirement/Feedback Cell 在 02 澄清，确认后创建 Plan，从 03 开始；
   - **不相关新需求**：新建 Request，并按 01 建新 worktree。
4. 若需求含义、服务对象、约束或验收改变，先升级 `request.md` baseline；随后升级 `plan.md` version，失效或升级受影响 Task 合同，再重算 Ready Queue。
5. 为一批反馈建立依赖、冲突、共享基础和串并行关系；只把会阻断原验收的项目纳入当前交付基线。
6. 未受影响 Plan/Task 保持原阶段和证据；不得因一条反馈把整个 Request 全局回退。

## 输出与返回

输出 Feedback 分类表、影响图、baseline/version 变化、受影响合同、当前交付继续/暂停建议、目标阶段与 owner，并写入 `progress.md` 当前快照。分类后的 Feedback 转成重开 Task、新 Task、新 Plan、新 Request、暂缓或关闭；返回相应阶段，Delta Intake 自身不成为第九阶段。
