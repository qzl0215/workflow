# Delegation

## 触发

已有确认计划，至少两个 Ready Task 可独立执行，且并行收益高于协调成本。能力不可用时使用完全相同的契约 solo 执行。

## 编排协议

1. Orchestrator 唯一更新范围和状态，按依赖、blocker、授权、文件域与共享资源计算 Ready Queue。
2. 每个 Worker 只接收一个 Task capsule：目标、上下文引用、允许/禁止文件、输出、验收、验证、权限和停止条件。
3. 冲突文件域或共享 release candidate 串行；只读审计可并行。不要用更多执行者掩盖未拆清的任务。
4. Worker 返回实际变更、命令、结果、失败与上下文请求，不自行扩范围或宣称 Plan 完成。
5. Reviewer 从 Task 契约和 fresh diff 开始，先审需求符合性，再审实现质量；关键命令由 Reviewer 或 Orchestrator 重跑。
6. 失败重派必须携带已排除假设和新策略；共享 workspace 下不覆盖、重置或清理他人改动。

## 降级与出口

无委派能力时，Orchestrator 按 Ready Queue 串行执行并保留审查步骤。所有 Task 合并后重新运行 Plan 级验证，而不是拼接各 Worker 的“通过”声明。
