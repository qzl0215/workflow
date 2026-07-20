---
kind: stage
stage: 01
---

# 01｜立项隔离

只建立安全、最新、可恢复的 Request 工作现场；不在本阶段讨论详细方案或提前实现。

## 最小上下文

- 用户本次交付意图和当前目录；
- 项目入口、仓库规则、现有未提交改动和可用工具；
- Git remote、默认目标分支、upstream 与权限；
- 当前请求是否为已有 Request 的连续反馈。

纯问答、只读诊断和一次性轻操作可以记录“不需要隔离”后快速通过，不为形式创建目录或文档。

## 责任角色

**总协调者**唯一判断 Request 边界、目标分支和工作目录。它不得覆盖、stash、reset、清理或搬运用户现有修改；子 Agent 不创建 worktree，不执行 Git 副作用。

## 阶段能力

1. 区分 Requirement 与独立 Request：同一用户触发中服务同一交付意图的一串要求属于一个 Request；可独立交付、验收和排期的无关目标另建 Request。
2. 先读项目规则和真实入口，再只读检查 Git 状态、remote 与目标分支；不猜 GitHub/GitLab 命名。
3. 有 Git remote 的新写入 Request，执行 fetch 获取最新远端跟踪引用，再从该引用创建一个 Request branch + worktree；不从可能过期的本地目标分支或其他功能分支开始。
4. 用户当前目录有修改时保持原样，在独立 worktree 工作；只有事实无法判断哪些修改属于当前 Request 时才请求一个具体决策。
5. 记录 source fingerprint、branch、worktree、base ref、项目命令入口与外部副作用授权；不在此阶段 commit、rebase 或 push。

## 输出

- Request ID、目标的一句话摘要和与既有 Request 的关系；
- 项目入口、项目规则和验证入口；
- 工作目录、branch、worktree、remote/base ref 与 source fingerprint，或不需要隔离的证据；
- 已发现 blocker、权限边界和交给 02 阶段的最小上下文引用。

## 退出与路由

工作现场不会覆盖现有改动，基线来自当前可信事实，下一角色知道在哪里工作和不能做什么后路由到 **02 看清需求**。缺权限、remote 或目标分支无法安全判定时保持 blocked；若证实只是纯问答或只读操作，完成相称验证后直接结束。
