---
scope: task-contract
owner: 总协调者
persistence: task-lifetime-when-needed
request_id: <RQxx>
task_id: <Pxx-Txx>
request_baseline: B01
plan_version: V01
contract_version: C01
source_fingerprint: <base-sha-plus-diff-or-artifact-digest>
updated_at: <YYYY-MM-DD>
---

# 执行合同：<task-result>

<!--
只为复杂、委派、跨会话或存在写冲突风险的 Task 创建；简单 solo Task 使用 plan.md 的 inline stub。
本文件冻结“做什么、允许改什么、怎样算完成”，不保存 stage/status、执行流水或证据结果。运行状态与 evidence index 只写 progress.md。一个 Task 可以更换 Agent，不因执行者变化复制合同。
-->

## 1. 任务身份与结果

- 所属 Plan：frontmatter `plan_version` 对应的 `plan.md#Pxx`
- 覆盖 Requirement / Acceptance：frontmatter `request_baseline` 对应的 `request.md#Rxx/Axx`
- 业务结果：
- 责任角色 / 所需能力：
- 当前阶段主协议：
- 明确非范围：

## 2. 最小充分上下文

只列完成当前职责所需的精确锚点；统一使用 `file@version#ID` 或 `file#heading`。ID 必须在目标文件内唯一；宽目录引用必须补文件集合或筛选条件。不默认加载完整聊天、完整 Request/Plan、专家会议、其他 Task 历史或无关项目文档。

- Source fingerprint 范围 / 排除项：
- Source fingerprint 复算命令 / 算法：

| Context ref | 必须知道的内容 | 用途 | Freshness / 缺口 |
|---|---|---|---|
| `findings.md#E01` | | | |
| `<project-file>#symbol` | | | |

## 3. 输入、输出与边界

- 明确输入：
- 必须输出：
- 允许修改：
- 只读：
- 禁止修改：
- 唯一写 owner：
- 共享资源 / 排队关系：
- 上游 / 下游 Task：
- 已授权本地动作：
- 允许的只读工具 / 命令：
- 已授权外部副作用：无 / 明确列表

## 4. 实施与验证合同

- 最小实现策略：
- DONE：
- Fresh 验证命令 / 场景：
- 预期 exit code / 可观察结果：
- 已有证据位置 / 缺口：
- 失败 / 回退点：
- 对下游必须返回的新事实：

## 5. 停止与升级条件

发现以下任一情况立即停止并返回总协调者：上游决策缺失、写域冲突、active baseline/version 与本合同不一致、source fingerprint 变化、权限不足、无法验证或范围变化。

上下文不足时只请求：`gap / target / expected_answer / why_needed`，不得自动扩张为全量上下文。

## 6. 结构化返回

- 合同：`<task-id>@<contract-version>`
- 结果：completed / blocked / needs-decision
- 实际产物 / 修改位置：
- 实际命令、exit code 与关键结果：
- 对照 DONE 的结论：
- 失败 / 已排除假设：
- 新事实及来源：
- 与计划的偏离 / 范围变化：
- 残余风险：
- 需要补充的具体上下文：无 / `gap...`
- 推荐下一路由：
