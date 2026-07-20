---
scope: runtime-control-plane
owner: 总协调者
persistence: project-request-lifetime
request_id: <RQxx>
active_request_baseline: B01
active_plan_version: V01
updated_at: <YYYY-MM-DD>
---

# 当前进展与运行控制台：<business-result>

<!--
本文件是 Request、Plan、Task 和 Feedback 运行状态的唯一真源，只保存当前可行动快照和证据索引，不复制需求、方案、Task 合同或完整日志。
只有总协调者写本文件。Worker/Reviewer 返回结构化结果；总协调者核对合同版本、source fingerprint、DONE 和 fresh evidence 后更新状态。Git 历史或项目已有版本机制负责历史，不把 progress.md 写成日记。
-->

## 1. Current Checkpoint

- 当前关注对象：只写 Object ID；阶段以 Object State 对应行唯一值为准。
- 最近完成的业务结果：
- 当前正在推进：
- 下一安全动作：
- 需要用户决定：无 / …
- 恢复工作先读：本 checkpoint → Active Object → 对应合同 / 精确证据引用
- 不要重复做：

## 2. Object State

生命周期只表达 `pending / active / completed / superseded`。Ready 由合同、依赖、资源、验证和授权实时推导；Blocked 由当前 Blocker 推导，二者都不保存为第五种状态。

| Object | Contract / 定义真源 | 当前阶段 | Lifecycle | 当前结果 | 下一动作 | Owner | Blocker |
|---|---|---|---|---|---|---|---|
| RQxx | `request.md@active_request_baseline` | 01–08 | active | | | 总协调者 | — / B01 |
| P01 | `plan.md@active_plan_version#P01` | 03–08 | pending | | | Plan owner | — |
| P01-T01 | `tasks/p01-t01.md@C01` | 05 | pending | | | Task owner | — |

## 3. Derived Ready Queue

这是可删除、可重算的派生视图，不是第二状态真源。

- Derived at：
- Basis：active baseline/version + dependencies completed + contract valid + no blocker + write/resource available + verification executable + authorization

| Order / Wave | Task | 为什么 Ready | 写域 / 资源占用 | 派发上下文 |
|---|---|---|---|---|
| W01 | P01-T01 | | | Task 合同 + 本文件切片 + 精确 findings/code refs |

## 4. Current Blockers

这里只保留尚未关闭的 blocker；关闭后从当前快照移除，历史由 Git 保存。

| Blocker | 影响 Object | 阻断事实 | 所需输入 / Owner | 解锁证据 | 返回阶段 |
|---|---|---|---|---|---|
| B01 | | | | | |

## 5. Evidence Index

只保存能支持当前 baseline/version 的证据索引和关键结论；完整输出、截图、日志、构建物保留在原始位置，不粘贴进本文件。

| Evidence | Object | Baseline / Version / Source fingerprint | Fresh 检查 | 结果 / 关键结论 | 原始证据位置 |
|---|---|---|---|---|---|
| EV01 | P01-T01 | B01 / V01 / … | command / scenario | pass / fail | |

## 6. Feedback Queue

新反馈先捕获、批量分类再改定义或代码。运行阶段保存在这里；一旦被接受为需求或方案变更，更新 `request.md` / `plan.md`，本行只保留当前路由结果。

| Feedback | 用户原话 | 影响的 Baseline / Object | 分类 / 路由 | 是否阻塞当前交付 | 当前处理结果 |
|---|---|---|---|---|---|
| F01 | | B01 / P01 | 待分类 / 缺陷 / 遗漏 / 优化 / 新 Plan / 新 Request | | |

## 7. 状态变更事务

这里只保留最近一次尚未闭合的事务；闭合后清空，历史由 Git 保存。

- 触发：无 / Feedback、执行结果、合同变化
- 已核对：active baseline / plan version / Task contract version / source fingerprint
- 需先更新的定义：无 / request / plan / task
- 受影响对象与合同：
- Object State / Evidence Index 更新：
- Ready 重算：
- 闭合条件：

## 8. 快照预算

- Object State 只保留 active、pending、当前 blocker 影响对象，以及仍待 Request 汇合的已完成 Plan；已完成 Task 折叠进 Plan 当前结果。
- Evidence Index 只保留 active baseline/version 和当前交付仍需引用的证据；过期证据由 Git 或原始产物追溯。
- Feedback 完成分类并回写 `request.md` / `plan.md` 后从当前队列移除，只保留 unresolved 项。
- Blocker 关闭即移除；状态事务闭合即清空。`progress.md` 不保留事件流水、每日记录或完整命令输出。
