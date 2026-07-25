# Git/worktree 并行合并适配器

## 何时进入

授权交付过程中，同仓两个以上已验证线程需要串行落到同一目标分支，或 rebase 出现文本/语义冲突时进入。它只处理 Git/worktree 机械合并，不选择业务方案、不分派 agent、不授予外部动作权限。

## 已知输入

- 已确认的 release contract、remote、目标分支、授权范围和最新目标；
- 每个线程的独立 worktree、分支、提交、source fingerprint 与验证回执；
- MERGE_NOTE：目标、逐文件意图、关键不变量和验证命令；
- 文本冲突文件、共同祖先和受影响业务路径。

## 深度判断

同一 workspace 同时编辑同一文件必须先重新分域；独立 worktree 可并行开发，但合并队列始终串行。安全性来自最新目标、fast-forward、双边意图和双方验证，不来自悲观文件锁或整文件选边。

## 核心动作

1. fetch 最新目标并确认候选来源、共同祖先、脏改动归属和 MERGE_NOTE。
2. 后合并者基于最新目标 rebase；无冲突时可运行 `python3 scripts/safe_merge.py --target <branch> --verify "<command>" --push`，由机械件处理共享锁、验证、fast-forward 和被超车重试，绝不 force。
3. 退出码 3 时保留冲突现场。AI 比较双方意图、前提、不变量和测试，合成兼容结果后标记文件，再用 `--continue` 继续；不得整文件选边、reset、abort 或另建逃避冲突的分支。
4. rebase 后运行当前线程和受影响已合入线程的验证；文本无冲突但验证失败按语义冲突处理。
5. 目标再次前进就重新 fetch/rebase；推送前证明目标分支是候选祖先。
6. 双方意图真实互斥且事实无法判断时，释放合并队列并把最小决策缺口返回上游。

## 写入真源

MERGE_NOTE 留在既有 `findings.md`；rebase、冲突取舍、命令、exit code 和双方验证写 `progress.md`。Git common dir 中的锁只是瞬时机械状态，不进入版本化真源。

## 停止 / 通过

候选基于最新目标，冲突按双边意图消解，双方验证 fresh 通过，目标只接受 fast-forward 更新；实际推送、合并或发布状态仍由授权交付 harness 核对。

## 失败回路 / 能力缺口

退出码 3 保留现场；验证失败返回语义冲突定位；连续被超车达到上限时释放锁并重排，不 force。无可执行验证时只能报告文本合并与影响分析，不能描述为语义安全。
