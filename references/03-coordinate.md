---
kind: fallback
stage: 03
method_role: fallback
concern: agent-coordination
---

# 03 fallback｜多 Plan / Task / Agent 协作

只有存在两个以上独立工作项且当前关注点没有用户指定或宿主原生协作能力时才读取。单一工作项、共享状态过多或协调成本高于收益时保持 solo。

## 最小输入

Plan/Task 拓扑、工作项状态切片、写冲突矩阵、可用 Agent、授权，以及开工门将建立的 Request 工作区规格。计划阶段不假设 worktree 已存在。

## 最小方法

1. 从 `task_plan.md` 依赖推导当前可开始的工作项，再检查文件、符号、schema、lockfile、生成物和共享可变资源；冲突工作合并为一个写 owner 或串行。
2. 只有无依赖路径、写域独立、验证环境独立且并行收益为正时并行。接口前后依赖、共享资源、集成与最终交付保持串行。
3. 同一 Request 的 Agent 在开工门后共享一个 worktree；子 Agent 不自行创建 branch/worktree，不 commit、rebase、push，也不修改四份真源。
4. 复杂或委派工作在派发前必须有版本化执行合同。Agent 只获得该合同、`progress.md` 当前切片和精确事实/代码引用，不默认收到完整聊天、全部计划或无关历史。
5. 执行者返回实际 diff、命令与结果、失败、已排除假设、新事实、偏差和上下文缺口；总协调者读取真实产物后更新 `progress.md`。
6. 实现与复核职责分开；没有更多 Agent 时，同一模型显式切换职责并串行执行，不降低验收。

## 输出与返回

输出 Agent/Task 分配、串并行波次、写域与共享资源边界、按需执行合同、最小上下文和汇合验收。依赖和波次只写 `task_plan.md`；复杂合同只写 `implementation-plan.md`。并行收益消失时立即收敛为 solo，随后返回 03 主协议。
