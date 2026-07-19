# Write Plan

## 进入条件

Readiness 已通过，Solution Contract 已选定；UI 范围另有选定 Experience Design Contract，非 UI 已记录 N/A。缺任一前置都返回对应阶段。

## 计划协议

1. 恢复或创建 `task_plan.md`、`findings.md`、`progress.md`；复杂实施才增加 `implementation-plan.md`。
2. 先写一页决策摘要、需求理解、现状诊断和可观察验收。
3. 按可独立验收的业务结果拆 Plan，再按单一 owner、清晰文件域和 fresh verification 拆 Task。
4. 为 Plan/Task 写依赖 DAG、输入、输出、非范围、风险、授权门和验证命令/证据。
5. Task ID 稳定且只表示引用；状态只允许 `pending / in_progress / completed / blocked`，只由 `task_plan.md` 持有。
6. `implementation-plan.md` 与 Task ID 一一对应，只写技术导航，不复制状态或决策。
7. 路径、命令或验收未知时写 blocker，不编造；计划中不得残留 TODO 占位。
8. 用户按可独立验收的整个 Plan 确认纳入/暂缓/不做；Task 用于透明展示和编排，不逐项索取无意义批准。

## 出口

用户能理解推荐范围、代价和顺序；每个 Ready Task 可在不重新设计的情况下执行并验证。得到实施授权后进入 Act；外部副作用仍需单独授权。
