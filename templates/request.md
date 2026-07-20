---
scope: problem-contract
owner: 总协调者
persistence: project-request-lifetime
request_id: <RQxx>
baseline: B01
updated_at: <YYYY-MM-DD>
---

# 需求与验收基线：<business-outcome>

<!--
本文件只回答“为什么做、为谁做、必须做到什么”。它是问题定义与验收基线的唯一真源，不保存调查证据、最终方案、Task、stage、status、执行流水或反馈队列。
只有项目级、跨会话或多人协作 Request 才创建；短任务留在对话。已接受的反馈会升级 baseline 并更新当前真源，旧版本由 Git 历史或项目现有版本机制保留。
-->

## 1. 真正要解决的问题

- 真实用户 / 使用场景：
- 当前处境：
- 需求产生的原因 / 根因：
- 为什么现在做：
- 期望的业务结果：
- 如果不做的损失：
- 明确非范围：

## 2. Requirement Ledger

每项 Requirement 使用稳定 ID。能从项目查明的事实不写成用户待回答问题；事实来源放 `findings.md`。

| Requirement | 用户原话 / 归一后的需求 | 服务对象与价值 | 可观察验收 | 约束 / 未知 | 与其他需求的关系 | 范围决定 |
|---|---|---|---|---|---|---|
| R01 | | | A01 | | | 纳入 / 暂缓 / 不做 / 待决策 |

## 3. 整体验收基线

- Baseline：与 frontmatter `baseline` 一致。
- 整体用户结果：
- 关键使用场景：
- 不变量 / 边界条件：
- 非范围：
- Fresh 证据要求：

| Acceptance | 验收行为 / 结果 | 覆盖 Requirement | 证据形式 |
|---|---|---|---|
| A01 | | R01 | |

## 4. 约束与授权

- 项目 / 平台 / 合规约束：
- 时间、成本、兼容或可逆性要求：
- 已授权本地动作：
- 已授权外部副作用：无 / commit / push / merge / deploy / delete / 公开发布的明确目标
- 必须再次由用户决定的事项：

## 5. 基线变更规则

- 原验收未满足不是新范围，不升级 baseline。
- 需求含义、服务对象、业务结果、约束或验收改变时，先在 `progress.md` 分类反馈，再升级 baseline。
- baseline 升级后，`plan.md` 必须重新判断影响并升级 `plan_version`；受影响的 Task 合同失效，未受影响工作继续。
- 不在本文件保存 raw feedback、运行状态或变更流水；Git 历史或项目已有版本机制负责历史。
