# Git/worktree 并行合并适配器

## 何时进入

同仓两个以上线程需要独立写入、已验证候选需要串行落到同一目标分支、merge 出现文本或语义冲突，或 workflow 自建 worktree 需要安全回收时进入。它只处理 Git/worktree 机械现场，不选择业务方案、不分派 agent、不授予外部动作权限或删除权限。

## 已知输入

- 已确认的 release contract、remote、目标分支、授权范围和最新目标；
- 每个线程的 Task ID、独立 worktree、分支、提交、source fingerprint 与验证回执；
- MERGE_NOTE：目标、逐文件意图、关键不变量和验证命令；
- 文本冲突文件、共同祖先、受影响业务路径与 worktree cleanup authorization。

## 深度判断

同一 workspace/worktree 同时只能有一个可写 owner，只读线程可以共享；任何并行写线程必须使用独立 worktree。不同 worktree 可以修改同一原始文件，但合并队列始终串行。安全性来自 matching owner lock、最新目标、target-first merge、fast-forward、双边意图和有效验证回执，不来自悲观文件锁、整文件选边或重复跑相同检查。

## 核心动作

1. 并行写 Task 从 fresh 目标运行 `git worktree add --lock --reason "workflow:<Task ID>"`，或使用 `python3 scripts/safe_merge.py --create-worktree <path> --branch <branch> --task-id <id> --target <branch>`；主 workspace 留给协调或集成。
2. fetch 最新目标并确认候选来源、共同祖先、脏改动归属、matching `workflow:<Task ID>` lock 和 MERGE_NOTE。
3. 后合并者运行 `python3 scripts/safe_merge.py --target <branch> --verify "<command>" --push`。机械件从最新目标创建临时集成分支，以目标为第一父提交、完整候选为第二父提交执行 target-first merge；候选分支和提交身份不改写，目标只接受 fast-forward 更新，绝不 force。
4. 退出码 3 时保留冲突现场并释放本次命令的合并 lease，避免人工处理期间阻塞其他已就绪交付。AI 比较双方意图、前提、不变量和测试，合成兼容结果后标记文件，再用 `--continue` 重新排队；不得整文件选边、reset、abort 或另建逃避冲突的分支。
5. merge 后先比较 command-scoped 内容、命令和环境：内容等价时复用双方有效回执；无关变化只做影响分析，冲突消解或相关输入变化才运行当前线程和受影响已合入线程的验证。文本无冲突但相关验证失败按语义冲突处理。
6. 目标再次前进就删除脚本创建的临时集成分支，从最新目标重建并重试；推送前证明目标仍是集成候选的第一父基线。项目明确要求线性历史时退出本地默认路径并遵循 release contract 的平台 squash merge。
7. 交付核对后，只有 workflow 自建的非主 worktree 同时满足 matching Task lock、clean、无进行中的 Git 操作、HEAD 已被 fresh 目标吸收并已有精确或 standing cleanup authorization，才运行 `python3 scripts/safe_merge.py --cleanup-worktree <path> --task-id <id> --target <branch> --yes`；脚本解锁并执行 `git worktree remove`，禁止 `--force`，保留本地分支。
8. 脏改动、未被目标吸收、活动 Git 操作、活跃或不匹配的 lock 一律保持锁定。缺失路径只用 `git worktree prune` 清元数据；旧 worktree 缺可信 owner 标记时只报告候选。双方意图真实互斥且事实无法判断时释放合并队列并把最小决策缺口返回上游。

## 写入真源

MERGE_NOTE 留在既有 `findings.md`；worktree/Task 绑定、merge、冲突取舍、内容等价检查、回执复用、目标核对和实际现场处置写 `progress.md`。Git common dir 中的 owner lock、合并 lease 和临时 integration state 只是可重建机械状态，不进入版本化真源。

## 停止 / 通过

每个并行写线程有独立且锁定的 worktree；候选以最新目标为第一父基线完成 merge，冲突按双边意图消解，内容等价时复用有效证据、相关输入变化时 fresh 验证，目标只接受 fast-forward 更新。已完成 worktree 按授权安全回收，未满足条件的现场保持可恢复；实际推送、合并、发布与线上状态仍由授权交付 harness 核对。

## 失败回路 / 能力缺口

退出码 3 保留现场并释放 command-scoped lease；验证失败返回语义冲突定位；连续被超车达到上限时释放 lease 并重排，不 force。无法建立独立 worktree 就串行写入；无可执行验证时只能报告文本合并与影响分析，不能描述为语义安全；无法证明 owner、吸收状态或清理授权时不得删除。
