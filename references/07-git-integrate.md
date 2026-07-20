---
kind: conditional
stage: 07
---

# 07 条件｜Git 集成与冲突修复

## 触发

当前 Request 已在需求级 worktree 完成候选，需要 commit、同步最新目标、rebase、解决冲突、push、创建 PR/MR 或 merge。建 worktree 属于 01，本协议不为子 Agent 新建线程。

## 最小上下文与角色

Integrator 只接收 Request branch/worktree、目标 remote/ref、候选 diff、逐文件意图、双方不变量、验证矩阵、项目规则和已授权动作；不凭提交标题猜业务意图。

## 做法

1. 只读检查候选 diff、未跟踪/敏感文件和项目提交规则；只纳入当前 Request，commit 等副作用必须已有明确授权。
2. Fetch 最新目标 remote tracking ref；如目标前进，将 Request 分支 rebase 到最新目标，不从旧本地分支推定最新。
3. 文本冲突时读取共同祖先、目标版本、Request 版本、相邻代码、双方意图和测试；合成同时保护不变量的实现，不整文件选 ours/theirs。
4. 文本无冲突但验证失败按语义冲突处理。修复后继续 rebase，并重新运行本 Request 和受影响目标路径验证。
5. Rebase 或冲突修复改变 fingerprint，06 的旧绿灯失效；post-rebase 验证通过后才能 push/merge。
6. 目标再次前进则重新 fetch/rebase；不得 force push 目标分支。只有已授权的私有 Request 分支在项目允许时才考虑 `--force-with-lease`。
7. 双方业务意图真实互斥、无法从事实判断时列冲突、已排除方案、推荐与备选并请求决策；不通过 abort/reset/逃避分支伪装解决。

## 输出与返回

输出最终 commit/digest、最新 base、冲突及语义合成、post-rebase 命令与 fresh 结果、实际 push/PR/MR/merge 状态。证据齐全后返回 Request 的 07 主协议并更新 `progress.md`；失败时为 Request 建立 07 Blocker，并重开受影响 Plan 到 06、具体 Task 到 05，或建立 Requirement Cell 到 02 交给业务决策 owner。
