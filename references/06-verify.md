---
kind: stage
stage: 06
---

# 06｜质量验收

从实际 diff 和业务验收重新判断结果是否简单、正确、完整；不把 Task 自报、历史绿灯或即将交付当成证据。

## 最小上下文

- 当前 Plan 的业务 DONE、Task/Plan/整体验收和非范围；
- 实际 diff、产物、source fingerprint、运行环境和影响面；
- 相关设计不变量、验证入口、`progress.md` Evidence Index 指向的原始证据和未覆盖风险；
- Reviewer 的文件权限和允许执行的本地验证。

不默认加载实现对话、完整专家过程、其他 Plan 流水或 Git 发布细节。

## 责任角色

**Reviewer**从验收和 fresh diff 开始独立复核，先看需求符合性，再看实现质量、复用、安全和维护性；**Plan owner**对集成业务结果负责。没有 fresh Agent 时同一 AI 切换职责重审并如实标注，不要求人类 Reviewer。

## 阶段能力

1. 从实际变更和验收生成验证矩阵，覆盖定向、相邻、集成、构建、真实使用和必要的 clean-room 路径；按影响选择最小充分范围。
2. 有非平凡代码 diff 时加载 `references/06-simplify.md`，检查复用、删除、合并、清晰度和效率，修复确认问题后重新验证。
3. Reviewer 检查越界文件、遗漏状态、错误抽象、隐性第二真源、安全/性能风险和失败回退；不因实现者解释而跳过实际代码。
4. fresh 运行关键命令，检查 exit code、完整关键输出、产物 freshness、source fingerprint 和环境。
5. 依次证明 Task → 当前 Plan 的独立业务结果；低层测试不能替代 Plan 的用户结果，部分日志不能替代未覆盖场景。Request 整体结果由 07 在所有纳入 Plan 汇合后证明。
6. 总协调者把 fresh 结论和原始证据位置写入 `progress.md` Evidence Index，不粘贴完整日志。验收过程中出现新要求时冻结原 baseline/version，进入 02 的 Delta Intake；未分类前不改代码。

## 输出

- simplify 与 AI review 结论；
- fresh 验证矩阵、命令、关键输出、fingerprint 和业务证据；
- 发现的问题、残余风险、未覆盖项及其路由；
- 可进入交付的候选 digest 和交付前必须重验的项目。

## 退出与路由

当前 Plan 的纳入范围已有 fresh 证据并达到业务 DONE 后标记为可汇合；其他 Plan 未完成时等待 Request 编排，不提前操作共享分支。所有纳入 Plan 通过后，由总协调者创建 Request 级 **07 集成交付** Cell。实现缺陷返回 05；需求、设计或计划基线错误分别返回 02、03、04。新增反馈按 Delta Intake 分流，未受影响 Plan 保持当前阶段。
