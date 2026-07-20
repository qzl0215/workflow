---
kind: conditional
stage: 04
---

# 04 条件｜多 Plan / Task / Agent 编排

## 触发

存在多个 Plan、两个以上 Ready Task、只读专家并行价值、独立 AI review，或跨会话执行者切换。单 Task 或协调成本高于收益时不加载。

## 最小上下文与角色

总协调者接收 Request/Plan DAG、`progress.md` 派生 Ready Queue、冲突矩阵、Agent 槽位、Request worktree 和授权。Plan owner 只看本 Plan；Worker/Reviewer 只获得各自 Task 合同和当前上下文包。只有总协调者写编排真源。

## 做法

1. 先按依赖计算 Ready，再按文件、符号、生成物和共享可变资源检查写冲突；冲突 Task 合并为一个写 owner 或串行。
2. 可以并行：独立只读发散、独立文件域实现、独立验证和无共享可变资源的工作。必须串行：接口前后依赖、同一 symbol/schema/lockfile、共享 build/release、Plan 集成和最终交付。
3. 同一 Request 的 Agent 默认共享一个 worktree；子 Agent 不再创建 worktree、branch，不 commit、rebase、push，也不修改 `request.md`、`findings.md`、`plan.md`、Task 合同或 `progress.md`。
4. 每个 Agent 只获得一个 Workflow Cell 上下文包：版本化 Task 合同、当前状态切片、精确证据引用、允许/禁止写域、输入、输出、验证、权限、停止和返回格式。
5. Worker 返回实际变更、命令、失败、排除假设、新事实和上下文 gap；总协调者读实际 diff，校验合同版本和 source fingerprint，更新 `progress.md` 的 Object State/Evidence Index 并重算 Ready Queue。
6. Reviewer 与实现职责分开；没有可用 Agent 时按同一契约 solo 串行执行，不降低质量门。

## 输出与返回

输出 Agent/Task 分配、串并行波次、写域与共享资源边界、按需 Task 合同、一次性上下文包和汇合验收。任意写域冲突在计划期消除；并行收益消失时立即收敛为 solo。完成后返回 04 主协议形成可执行计划。
