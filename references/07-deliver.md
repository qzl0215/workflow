---
kind: stage
stage: 07
---

# 07｜集成交付

把所有已验收 Plan 汇合成 Request 候选，安全落到最新目标基线，并准确报告本地、Git 或线上真实状态；本阶段不重新发明产品范围。

## 最小上下文

- 候选 digest、Request branch/worktree、目标 remote/ref 和项目交付规则；
- 逐文件/模块变更意图、关键不变量、验证矩阵和回滚方式；
- 06 阶段证据、source fingerprint、敏感信息检查和残余风险；
- 当前请求、项目规则或 active Plan 已明确授权的副作用。

不加载完整 Grill、专家发言、Task 对话和无关 Plan 证据。

## 责任角色

**Integrator**唯一执行 Request 级 Git 集成、冲突修复和交付；**总协调者**守住授权和最终状态。Task Agent 不 commit、rebase、push 或 merge。没有独立 Integrator 时同一 AI 顺序承担，但必须从变更意图和目标分支重新检查。

## 阶段能力

1. 只读确认所有纳入 Plan 已通过、工作区、候选 diff、目标 remote/branch、授权、敏感信息和项目 CI/MR/发布契约，不混入无关改动。
2. 需要 Git commit、fetch/rebase、冲突解决、push 或 merge 时加载 `references/07-git-integrate.md`；Git start 规则仍属于 01，不在此重新创建子 worktree。
3. Rebase、冲突修复或目标分支前进会改变 source fingerprint；只失效证据身份受影响的验证，fresh 运行相关 Plan、跨 Plan 集成和 Request 关键路径，不机械重跑无关检查。
4. 外部动作逐目标应用已有授权；未覆盖的 remote、branch、环境、公开发布、delete 或破坏性例外停在授权门。
5. 交付失败立即停止后续写操作，保留可恢复现场和证据；不得用 force、reset、整文件选边或新建逃避分支掩盖冲突。
6. 面向用户先说明业务结果、是否可放心使用、验证、真实交付层级和下一步；技术细节只保留复核所需。

## 输出

- 最终 commit/diff/digest、目标基线和 post-rebase fresh evidence；
- 文本/语义冲突的双方意图、解决方式和验证；
- 本地已验证、已提交、已推送、已合并、已部署或 blocked 的准确状态；
- 回滚方式、残余风险和进入 08 阶段所需的 `progress.md` 当前结果切片。

## 退出与路由

候选基于最新目标，授权内动作完成，交付后证据 fresh 且状态报告真实后在 `progress.md` 创建 Request 级 **08 复盘升级** Cell。验证失败时为 Request 建立 07 Blocker，定位并重开受影响 Plan 到 06，或重开具体 Task 到 05；业务意图互斥且事实无法判断时创建/重开对应 Requirement Cell 到 02 或 Plan 到 03，不强行合并；缺授权保持可恢复 blocker。
