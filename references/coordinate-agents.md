# 协调 Agent

## 何时进入

默认 solo。只有动态专家的**只读独立视角**会改变推荐、两个以上可并行实施 Task 有正并行收益、独立 Reviewer 能覆盖高风险或证据冲突，或复杂交接无法靠当前 owner 恢复时才进入。单 Task、共享文件、项目重要、自修改或协调成本高于收益时不加载。

## 已知输入

- 当前动作、目标、P9 六要素、证据路径和停止条件；
- Plan/Task DAG、Ready Queue、允许/禁止文件和共享资源；
- 可用 agent 槽位、隔离方式、上下文预算和授权边界；
- 需要的是方案期独立判断、实现工作还是 fresh review。

## 深度判断

三类协作严格分开：方案期可在确认计划前获取只读独立视角；实现委派只能在**确认计划后**，且至少两个 Ready Task 具备独立 worktree、独立验证和正并行 ROI；独立 Reviewer 不是默认门，只在高风险、证据冲突或真实 reviewer 要求时从验收与 fresh diff 开始。

没有独立 agent 时同一 AI 可按视角顺序模拟，但必须标注为模拟。不要用更多 agent 掩盖任务没拆清，也不要为省几分钟引入合并与上下文成本。同一 workspace/worktree 同时只能有一个可写 owner；只读线程可以共享，任何并行写线程必须进入独立 worktree。

## 核心动作

1. 总协调者唯一维护范围、状态、依赖与 Ready Queue；每个 Task 对应一个写 owner和一个独立写现场。并行时主 workspace 只做协调或集成，不承载第二个写 owner。
2. 每位参与者只收最小 capsule：目标、P9、上下文引用、允许/禁止文件、输出、验收、验证、权限与停止条件。
3. 方案期各视角先独立发散再交叉质询；只读，不改正式真源，由总协调者综合并标证据等级。往返观点只合并为一条当前 decision receipt；尚未消除且会改变结论的分歧标为风险，不保存会议流水。
4. 同一 worktree、共享 release candidate 和顺序依赖串行；只读审计或独立 worktree Task 可并行。不同 worktree 可以修改同一原始文件，但 capsule 必须携带双方目标、不变量和验证，交付时转入 Git/worktree adapter 做串行 target-first merge。
5. Worker 返回实际变更、命令、失败、排除假设和上下文请求，不扩范围、不自行宣布 Plan 完成。
6. Reviewer 先审需求符合性，再审实现质量和安全；关键命令优先复用同一源码、命令和环境的有效 RC 回执，输入变化或独立复核确有新增证据时才 fresh 重跑。
7. 发现另一写 owner 已占用当前 workspace 时，在任何编辑、Git index 或构建写入前停止并创建独立 worktree；不得覆盖、重置、删除或清理他人改动。独立 worktree 的 merge 冲突保留集成现场，由后合并者按双方意图消解。

## 写入真源

范围与状态只由 `task_plan.md` 持有；实际调度、失败、证据和 handoff 写入 `progress.md`。专家观点合并进现有 `findings.md`，不为每个 agent 新建会议文档；Worker 只写获准文件域。

## 停止 / 通过

每个 agent 的目标、worktree、文件域、证据和权限清楚；每个 worktree 只有一个可写 owner；返回结果已由总协调者读 diff 并重验。并行收益消失时立即收敛为 solo；角色相同也保持 owner/reviewer 职责边界。

## 失败回路 / 能力缺口

委派失败时携带已排除假设和新策略，不原样重派。同一 workspace 已有写 owner就等待或创建独立 worktree；跨线程独立 worktree 的文件重叠留给合并期兼容。槽位不足就按 Ready Queue solo；上下文不足只请求具体缺口，不全文加载。任何 agent 请求外部副作用都返回总协调者授权门。
