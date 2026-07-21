---
kind: gate
stage: start-gate
method_role: business-boundary
---

# ◆开工门

在首次产品实现写入前建立安全、最新、可恢复的 Request 现场。它不是编号阶段，不重新做需求、方案或计划。

## 入口授权

- `plan_mode=formal`：不看草案是否已经落盘，当前版本必须为 `approval_state=approved`；`draft / rejected / modified` 时不得隔离开工，返回 03。
- `plan_mode=inline`：`approval_state=not-required`，用户原始明确执行请求即授权本地、可逆、范围内实施；不增加确认。
- 用户只要求调查、诊断或计划时不进入本门，也不把这些请求扩成实现授权。
- 计划批准不覆盖 commit、push、merge、deploy、delete、公开发布、生产写入或其他外部副作用。

## 安全现场

1. 先读项目规则和真实入口，只读检查当前目录、未提交改动、Git remote、目标分支、upstream 与权限；不猜平台或分支名。
2. 不覆盖、stash、reset、清理或搬运用户现有修改。事实无法判断某项修改是否属于当前 Request 时，只询问这一个具体边界。
3. 先判断 Codex thread、用户或兼容 harness 是否已提供归属当前 Request、干净独立、基于可信目标且不会影响用户改动的现场；满足则直接复用，不创建第二个 branch/worktree，也不迁移已经位于该现场的唯一计划文件。
4. 只有正式计划、脏工作区、多人/并行、跨会话恢复、复杂依赖或较高风险工作且现有现场不足时，才在授权成立后 fetch 最新远端跟踪目标，并从可信引用创建一个 Request branch + worktree；不从过期本地目标或未合入功能分支开始。局部、可逆、短生命周期小改可直接使用现有安全工作区。无 Git/remote 时使用环境可提供的最安全隔离，并记录未覆盖风险。
5. 需要 worktree 时，同一 Request 的 Agent 共享该 worktree。子 Agent 不建分支/worktree，不 commit、rebase、push；工作区和 Git 动作由总协调者唯一管理。

## 基线复核

建立现场后重新观测 source fingerprint，并与 03 的规划基线比较。若变化影响用户结果、范围、验收、关键体验、难逆风险、成本/时间承诺或交付目标，当前批准失效：保持现场可恢复，返回 01、02 或 03 形成受影响的新版本与必要决定。若只改变 Task 依赖/波次、真实 owner、写域、schema/共享资源、验证入口或其他可逆实现细节，总协调者先更新 planning baseline、`task_plan.md` / `implementation-plan.md` 和受影响验证，再以同一业务批准继续；不重复询问用户。

正式计划批准前只可在对话展示；确需文件时，唯一草案保存在一个既有安全计划区，不写产品源文件。开工门成功通过后，把完全相同的批准内容原子迁移到 Request 工作现场，并删除临时草案；不得保留两份可编辑副本。未通过或基线变化时可重新进入本门，每次只复核受影响项。

## 输出与退出

输出 Request ID、`plan_mode / approval_state`、目标 ref、实际隔离方式、source fingerprint、项目与验证入口、写域、授权引用和未覆盖风险。授权成立、现场不影响用户改动、最新基线仍支持当前计划后进入 **04 执行建设**；否则返回对应阶段或保持等待，绝不绕门写入。
