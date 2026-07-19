# Pre-plan Contract：<business-title>

<!-- 只冻结进入 Write 所需的已选决策；Plan 范围和状态仍由 task_plan 持有。 -->

## Readiness evidence

- 入口 / 约束 owner：
- 必需命令 owner：
- 验证路径 owner：
- 结果：no-op / patched existing / one entry created

## Selected Solution Contract

- 目标状态与不变量：
- 选定方案 / 用户确认：
- 关键取舍与删除项：
- 模块 / 数据 / API / 集成边界：
- 适用的安全 / 性能 / 可靠性 / 成本边界：
- 迁移 / 回滚点：
- 可观察验收：

## Experience Contract

- 适用性：UI / non-UI N/A
- 选定方向 / 用户确认：
- 用户旅程、IA、screen/state inventory：
- 视觉与 design-system 约束：
- motion / reduced-motion：
- responsive / accessibility / long-content：
- 完整状态与可测试验收：

## Exit gate

- [ ] Readiness 无阻断。
- [ ] Solution 已选且无改变方向的未知。
- [ ] UI 已选 Experience；或 non-UI N/A 已记录。
- [ ] 剩余未知可由 Write/Act 在既定边界内解决。

任一项未勾选时 Write fail closed：回到对应 Readiness、Solution 或 Experience owner，不得用 TODO、假设或“Act 时再定”绕过。
