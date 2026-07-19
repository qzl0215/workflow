# Act Plan

## 进入条件

已有确认的 Task 与验收。先从 Snapshot、当前 Task、相关 findings 和 progress handoff 恢复，不默认读取全部历史。

## 单 Task 循环

1. 将 Task 标为 `in_progress`，冻结输入、source fingerprint、文件域、共享资源、授权边界和验证方法。
2. 先获得最小失败证据或缺口证据，再做满足验收的最小实现。
3. 只修改 Task 范围内文件；发现方案/设计/Readiness 缺口时回退，不在 Act 偷做新决策。
4. 运行最小相关验证，再扩大到 Plan 级回归；实际命令和输出写入 `progress.md`。
5. 失败先进入 Debug；同一路径连续失败时改变假设或手段，不机械重试。
6. 用 fresh evidence 对照验收后才标 `completed`，再重算 Ready Queue；source 已变化则先重建证据。

只有两个以上 Task 可独立、文件域不冲突且并行收益明确时，才加载 delegation 协议；否则 solo 更简单。

## 出口

Task 产物、diff、验证证据、残余风险和下一步均可被另一位执行者复核。
