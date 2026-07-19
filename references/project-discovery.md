# Project Discovery 与 Minimum Readiness

## 何时读取

项目级请求刚进入，或下一阶段可能因找不到入口、约束、必需命令或验证路径而猜测时读取。成熟项目通常只读不写。

## 发现顺序

1. 确认项目根、用户请求涉及的模块和现有项目规则。
2. 读取与当前请求直接相关的 README、AGENTS、配置、入口代码、测试和部署说明；不做全仓资料考古。
3. 记录事实、未知和来源，把证据写入 `findings.md`；不要把发现复制成第二份项目说明。

## Minimum Readiness Gate

只问一句：**如果现在进入下一阶段，是否必须猜关键事实，或无法验证结果？**

只检查当前任务需要的三类信息：

- 入口与约束在哪里；
- 必需的运行、构建或部署命令是什么；
- 用什么证据验证下一阶段的结果。

| 场景 | 确实阻断下一阶段 | 已有 owner | 动作 | 新文件预算 | 通过证据 |
|---|---|---|---|---:|---|
| mature | 否 | 任意 | no-op | 0 | fresh reader 能定位三类信息 |
| incomplete | 是 | 是 | patch existing | 0 | 现有真源链接真实命令/配置，fresh command 成功 |
| empty | 是 | 否 | create one entry | 1 | 新入口只做导航，下一阶段可执行并验证 |
| non-blocking gap | 否 | 否 | record in findings | 0 | 不妨碍当前结果，不扩大本次范围 |

处理顺序：

1. 信息足够：no-op，记录证据位置后继续。
2. 信息存在但分散或过期：优先 patch 现有 README、AGENTS 或已有真源，并把命令接到真实脚本/配置。
3. 没有 owner 且缺口确实阻断：最多新建一份短入口文档，链接现有真源；不生成治理文档树。
4. 修补后由 fresh reader/command 证明下一阶段无需猜测；写出实际定位和命令结果，否则门仍未通过。

若 README、AGENTS 或项目规则已经是 owner，就地补它；不得为了显得完整再创建同义入口。新入口也不能复制部署、安全、设计等细节，只链接这些内容的真实 owner。

Readiness 不扩展设计、部署、安全、数据、运维或评估体系；这些内容只在真实任务触发时由对应阶段处理。

## 出口

输出项目/用户级判断、关键证据路径、readiness 结果（no-op / patched existing / one entry created）和仍会改变方案的未知，然后进入 Clarify 或 Solution。
