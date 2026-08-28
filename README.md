# workflow

**你说目标，workflow 帮你看清、做成，并让下一次更高效。**

它把复杂工作统一成计划、执行、复盘三段七动作；遇到跨业务、产品、设计、技术或交付的复杂决策时，组织专家圆桌看见完整森林图景，再选路线、拆任务、实施、验收并把有效经验回灌到唯一真源。只安装 `workflow` 即可，不要求你再准备其他 skills，也不会为了显得完整给项目堆一套文档。

作者：zhonglin · MIT License

当前协议版本：`2.25.0`

[打开中文可视化介绍](docs/workflow-visual-map.html) · [查看完整工作协议](SKILL.md)

## 30 秒了解它在做什么

适合这些任务：

- 有难逆决策、安全/生产风险、跨系统兼容性或重大未知；
- 需求还比较散，需要先看全局、定方案和优先级；
- 涉及 UI、视觉或动效，需要先定设计再写工程计划；
- 要跨会话推进，或需要多人 / 多 Agent 协作；
- 最终要有可复查的测试、交付或发布结果。

不适合纯问答和一次性只读操作。这些事情直接做更快。

收到需求后默认走最低充分的快刀路径。文件多、项目重要、常规发布或修改 workflow 自身不会自动升级；只有难逆决策、迁移/权限/安全/生产风险、跨系统兼容、方向不明、连续失败/证据冲突或真实恢复协作需求才进入完整项目流程：

> 计划：需求澄清 → 选定方案 → 拆成任务<br>
> 执行：执行任务 → 验收交付<br>
> 复盘：提炼经验 → 回灌改进

七个动作是证据检查点，不是七场固定仪式：证据已存在就快速通过，轻任务整体走短路径，但价值判断、完整 Plan 确认、验收证据和外部授权不会降级。

任务完成、终止或把长期阻断交回用户前都会先过一次收尾复盘门。已有返工、失败、方向变化等信号仍照常触发；即使任务顺利，只要实际执行时间严格超过 1 小时，或平台报告的任务累计 token 严格超过 200 万，也必须进入相称复盘。没有可靠遥测时不猜，没有高价值候选时可以 no-op。

需求澄清不等你先说“澄清需求”：只要表面请求与真实用户结果之间还需要关键推断，workflow 就先建立“表面请求 → 当前痛点 → 本质目标 → 成功信号”的目标链，再按“项目真源 → 已连接工具与数据 → 官方一手来源 → 最小实验”调查。**两个合理答案会形成不同的需求契约或重大风险承诺**时，该项是承重决策，由用户选择或填写，也可以明确委托 AI 在给定边界内决定。每题带当前理解或推荐、选项或填空，并说明答案会改变什么。

承重决策在需求 owner 内进入 **Grill 深度**，按有界决策树先大后小推进：每条分支先处理当前最上游节点，当前可回答且相互独立的问题一次集中展示，回答后展开相关子节点并重算下一批。局部、可逆且仍落在同一契约内的细节由 **AI 代选**，依据项目约定、当前背景和稳定历史偏好，作为 **AI 代选细节（可调整）** 随推荐需求契约展示。所有承重分支都有明确落点、剩余答案不会改变契约或重大风险时通过契约稳定门，结束追问并请求整体确认；题数和轮数由实际决策树自然收敛。

## 调研前先绑定最新真源

结论依赖可变项目现状的新需求，会先用项目定义的 freshness 机制刷新目标真源并固定 source fingerprint，再在同一现场完成调研、方案和实施；交付前只再同步一次。纯概念问答不刷新，恢复同一任务不盲目换基线，也不按落后提交数设置阈值。已经被目标版本吸收的旧工作现场只用于只读追溯，不能默认复用为新任务。

## 本地已验证 ≠ 已交付

“验收交付”先由必经的验收 owner 证明结果；只有目标包含提交、合并或发布时才加载授权交付 harness，不因此升级整项工作。它从项目部署/发布文档解析唯一真实集成发布契约，不调用外部提交 skill，也不叠加第二套提交审查链。默认事务是“聚焦验证 → 语义/安全复核 → 精确候选提交 → target-first 集成 → 一次 clean RC → fast-forward → 发布同一制品 → 安装 smoke”；相同 command-scoped 内容、命令和环境可复用回执，真实环境边界始终 fresh 烟测。

`safe_merge.py` 把正式验证绑定到不可变集成 SHA 和验证命令。push 或网络传输失败但目标仍停在已复核基线时，只重试同一 SHA，不重复跑 RC；目标或源码变化才重建集成证据。成功输出只保留紧凑摘要、阶段耗时与回执位置，失败才展开有界尾部和完整日志路径。

项目要求 PR/MR、CI、直接 fast-forward、特定部署命令或 GitHub Release 时，以项目真源为准，workflow 不硬编码平台流程。用户已经明确要求“提交合并发布”且目标可由项目文档唯一确定时，不会在每一步重复索取同一授权；目标不明、未授权或存在破坏性例外时，才停在一个具体决策点。

用户不承担代码审阅。AI 自己检查 diff、范围和测试，只把业务结果、风险与外部授权交给用户决定。PR/MR 仅在分支保护、必需 CI、项目规则或真实 reviewer 要求时使用；tag、Release、部署等节点也必须有独立价值，能由一个平台动作安全完成的步骤会合并，不为 Git 术语增加人工停顿。

## 并行线程各用自己的 worktree

同一 workspace/worktree 同时只允许一个可写 owner；只读线程可以共享，任何并行写线程都使用带 `workflow:<Task ID>` lock reason 的独立 worktree。不同 worktree 可以同时修改同一原始文件，但交付时排队做 target-first merge：最新目标是第一父提交，整个需求分支是第二父提交，冲突集中解决一次且不改写候选提交。项目明确要求线性历史时才遵循平台 squash merge；workflow 不为默认并行链路维护第二套提交重放流程。

workflow 自建 worktree 具有完整生命周期：创建时锁定，阻断或未合入时保持锁定；交付核对后，仅在 matching Task lock、clean、无进行中的 Git 操作、HEAD 已被目标吸收且已有精确或 standing cleanup authorization 时解锁并执行 `git worktree remove`。清理禁止 `--force`，默认保留本地分支；`git worktree prune` 只处理路径已经消失的残留元数据，不会冒充 worktree 回收。

## 状态变化会播报，需要你接棒才停下

所有用户可见内容先过一次决策价值过滤：优先说明用户能得到什么、实际效果、真实代价、关键风险和必要行动。执行过程与技术细节只有在会改变决定、行动、风险认知或结论可信度时才进入主回复；否则删除或等你需要时再展开。它不会为了显得“业务化”制造取舍或虚构价值，也不会借精简隐藏失败、授权边界和必要证据。

除等待你回复外，H0/H1 只在开始、真实 blocker、完成时简短播报；H2/H3、跨上下文时，进度、实际使用的 reference、有效成果或当前 Plan/Task 发生变化会在下一条可见消息顶部给出一次最新快照，然后继续工作。状态没变就不重复。每次 workflow 停下等待你作出决定或提供输入前，都会在同一条消息顶部更新并展示完整快照，不受深度或状态是否刚变化影响。快照固定使用普通文本与 Markdown 链接，不探测宿主、不生成 DAG 视觉，也不展示 Ready 队列。有正式计划时只补一行最短活动路径，例如 `✓ P01 → ● P02 / T03 → ○ P03`。

只有真正需要你纠正理解、选择方向、确认完整计划、提供外部输入、授权副作用、解除阻断或验收时，workflow 才交回控制权。此时结论之后始终保留独立的“建议下一步”和“回复建议”，不会因精简 AI 调度信息而消失。提交、合并和发布都已核验，且没有风险、待决策或必要行动时，最终完成改用一句带线上链接的状态，不再重复整套快照。下面演示两种交接和一种成功完成；真实任务会链接实际 reference、成果或线上入口。

### 场景一：方向决策

> 进度｜■◆□□□□□ 2/7 · 选定方案<br>
> 技能｜[选定方案](references/decide-solution.md) · [试验攻防](methods/experiment-attack.md)<br>
> 成果｜✓ [需求](references/understand-goal.md) · ● 方案 · ○ 计划 · ○ 交付 · ○ 进化<br>
> 结论｜推荐先验证单一路径，它覆盖核心价值且最容易回退。<br>
> 关键动作｜先只接通并验证核心路径，暂不扩展次要分支。<br>
> 正面效果｜能以最低成本验证核心价值，失败时也最容易回退。<br>
> 负面后果｜首版不会覆盖全部场景；若采用覆盖更全的备选方案，则会提前引入维护负担。<br>
> 待决策｜是否接受首版覆盖较窄，以换取更快验证和更低回退成本。<br>
> 建议下一步｜采用推荐方案并保留回滚点。<br>
> 回复建议｜回复“采用推荐方案”，或指出必须保留的备选能力。

### 场景二：阻断或授权

> 进度｜■■■■◆□□ 5/7 · 验收交付<br>
> 技能｜[验收结果](references/verify-results.md) · [授权交付](references/deliver-release.md)<br>
> 成果｜✓ [需求](references/understand-goal.md) · ✓ [视觉方案](docs/workflow-visual-map.html) · ✓ [计划](templates/task_plan.md) · ● 交付 · ○ 进化<br>
> ✓ P01 → ● P02 / T03 → ○ P03<br>
> 结论｜成果已在本地验明，但发布会产生外部影响，尚未执行。<br>
> 风险｜继续发布会改变外部环境；保持本地不会产生副作用。<br>
> 建议下一步｜决定是否把本地已验证成果发布到目标环境。<br>
> 回复建议｜回复“授权发布”或“保持本地已验证”。

### 场景三：最终完成

> 已提交 GitHub，已合并，已发布：[线上入口](https://example.com)。

## 发现小改进时，先提案再动手

workflow 不会再按“出现几次”机械决定是否回灌。AI 会结合事实证据、实际影响、改动大小和长期收益做判断；一次发现也可能很有价值，重复出现的低价值噪音也可以不改。

提交前先做减法，只留下“小改动、大价值”的完整回灌提案：痛点问题、AI 推断的补充需求、最小改造、预期业务价值、唯一 owner、范围、可失败验收、验证和副作用边界，以及接受、调整或暂不做。确认前不写入；用户一次明确确认后直接实施，不再重复索取 Plan 确认。外部动作授权和最终验收仍然独立。

获批后的改造在正确归属地完成：当前项目原范围内的知识整合作为原 Plan 的退休事务完成，不另开 Plan；只有新的用户结果或需要独立交付、回滚的跨 owner 变更才追加 Plan。其他项目或 skill 使用最小 handoff capsule，把已确认需求、方案、验收和授权带过去，不重复访谈；没有稳定真源时先停下确认。生成一段 handoff 提示词不算完成，目标位置必须返回实际改动和 fresh 验证。

## 不知道下一步时：四路未知

workflow 不会把所有不确定都变成对用户的追问：

| 未知 | 怎么处理 |
|---|---|
| 事实可查 | AI 查项目、数据、工具、配置和可信来源 |
| 取舍待定 | 承重取舍给推荐、选项和答案影响，由用户决定或明确委托；契约内细节由 AI 代选并展示 |
| 假设待验 | 做最小实验、原型、小样或可失败验收 |
| 外部待解 | 写清 blocker、外部 owner、解锁条件与授权边界 |

四路未知处理完都会回到当前业务动作，不再制造第二套阶段名称。

## 专家圆桌如何看见整片森林

H0/H1 默认单视角，不加载专家、subagent、独立 Reviewer 或方法包。当问题跨多个领域、角色目标冲突、证据互相冲突或重大路线难以取舍时，workflow 才列出会改变最终推荐的关键决策，再选择 `lead + 必要补位 + challenger`。H2 默认最多 3 个视角，H3 默认最多 5 个。

会议不是轮流发表套话，而是三段式：

1. **独立发散**：所有专家看同一份事实，各自指出机会、依赖、盲区和会改变判断的新证据。
2. **交叉质询**：互相挑战未经证明的假设、只顾局部的方案和遗漏的角色或生命周期。
3. **主持收敛**：把信息合成完整森林图景，再给出推荐方案；最终方案必须通过奥卡姆硬门，列出删除项、最简充分版和额外复杂度的证据，实质修改后重跑。

PUA/P10 方法只分成四个懒加载包：战略价值、本质减法、试验攻防、交付复利。一次只加载一个主包和一个挑战包，每包只运行 1–2 个与当前决策有关的原语。简单、低风险、容易回退的任务不会为了“专家感”强行开会；没有多个 Agent 时可顺序模拟，但不会冒充独立审查。

## 安装

需要 Python 3.9+，运行时不需要第三方 Python 包。

### 推荐：复制给你的 Agent

不需要先知道 skills 目录。把下面整段复制给当前 Agent，它会根据自己的运行环境完成安装和验证：

> 请安装 GitHub 项目 `https://github.com/qzl0215/workflow`。先把仓库克隆到临时目录，再根据你当前 Agent 的配置确认 skills 父目录，不要猜固定路径；运行 `python3 scripts/install.py install --target "<skills父目录>"`。如果已经安装，则使用 `update` 整体替换。随后运行 `enable-auto-update`，为 workflow 显式启用登录时加每日一次的用户级自动同步；不得创建管理员级服务。最后运行同一脚本的 `check`，只有唯一性和完整验证通过后才能告诉我安装完成。只安装 workflow，不保留可被宿主发现的旧版本副本。

### 自己在终端安装

如果电脑上只有一个已存在的常见 Agent skills 目录，安装器会自动识别：

```bash
git clone --depth 1 https://github.com/qzl0215/workflow.git
cd workflow
python3 scripts/install.py install
python3 scripts/install.py enable-auto-update
```

先只读查看识别结果：

```bash
python3 scripts/install.py detect
```

如果发现多个目录或没有识别到，请明确指定你的 Agent skills 父目录：

```bash
python3 scripts/install.py install --target "/path/to/agent/skills"
```

安装结果为 `<skills父目录>/workflow`。自动识别只使用已配置的 `AGENT_SKILLS_DIR` 或本机已经存在的常见目录；有歧义时会停止，不会替你猜。

安装后检查：

```bash
python3 scripts/install.py check --target "/path/to/agent/skills"
```

`check` 不只检查包内容，也要求这个 skills 根目录中只能发现一个 `name: workflow`，且位置必须是 `<skills父目录>/workflow`。

## 开始使用

安装后，直接把复杂目标交给 Agent：

> 用 workflow 帮我推进这个项目的新功能。先把目标说清楚；需要时组织专家圆桌，给我完整森林图景和推荐路线。如果是现有页面的小改，直接给我真实页面实装预览；只有方向探索才做独立 demo，再写计划、实现并按真实使用验收。

workflow 会按任务复杂度自动选择必要阶段。成熟项目不会被强行“补基建”；只有入口、约束、关键命令或验证路径真的缺失并阻断后续工作时，才优先补现有真源，极端情况下最多新建一份项目入口文档。

## 18 项按需模块如何保持思考深度

七个 owner 守住七个业务动作；六个 harness 只在体验塑形、设计治理、Agent 协调、失败修复、上下文交接或授权交付有价值时叠加；并行 Git/worktree 合并是一个窄 adapter，四个 PUA/P10 方法包独立懒加载。文件数量不是规则，只有独立问题、不同退出条件、唯一触发和单独加载收益同时成立才拆文件。

UI 先分**现有页面增强**与**方向探索**。未明确要求重构时，默认复用实际路由、代码 owner、组件和 tokens，做可回退的**真实页面实装预览**；确认后让同一补丁进入 Plan，不再照着 demo 重写。只有方向探索才做独立 demo：**方向粗选**同批给三个静态线框视觉方向，用户选定后在**方案精修**中只做一个模拟数据 HTML，最后将候选与完整 Plan 一起交给用户**确认开动**。任务按 Plan/Task DAG 拆串并联，只并行文件域独立且收益高于协调成本的工作。估算聚焦 AI 执行路径、等待外部决策和风险缓冲，不把人的工作天数直接当成 AI 耗时。

可见文案同时通过内容设计硬门：先用信息层级、布局、状态、图形和交互让页面一眼可懂，不用标题、副标题或说明文案重复解释；删掉不影响理解、行动或安全的文字，五秒扫读仍能看清目的、状态和首要操作。必要标签、无障碍文本和完整风险语义继续保留，长内容使用渐进披露。

## 它如何避免把事情做重

长期项目优先复用 `AGENTS.md`、README、TRUTH、代码、配置和测试作为一个短小的项目知识导航，不把代码事实复制成另一份百科，也不建立人类与 AI 分离的知识真源。长期知识只过一个最小消费价值与可发现性门：未来什么场景会用、会改变什么核心结论或行动、怎样从问题找到唯一真源。答不清就不沉淀，不为每条知识增加 owner、失效条件或维护表单；可变事实优先由代码、配置或 fresh 探测给出当前答案。

`findings.md` 只保留每个决策主题当前有效的唯一结论，不把来回修改过程写成两套现行决定。用户后续表达可明确判断为最新目标时直接覆盖旧结论；覆盖意图不清或错误覆盖会带来实质风险时才请用户确认，确认后仍只留最终决定。

临时证据在验收和退休后及时删除，避免成为未来注意力噪音。只有不可重现且审计、回滚或事故恢复明确要求的证据，才复用 Git、发布记录或既有审计系统保留，不新建证据管理流程。完成 Plan 立即退出日常上下文，但不等于立刻物理删除；长期知识已整合、临时证据已清理、未解决项不影响恢复且获得精确删除授权后才物理删除。

| 原则 | 实际行为 |
|---|---|
| 一个入口 | 包内只有一个根 `SKILL.md`，所有能力都已编排在同一个包内 |
| 按需读取 | 默认读取当前 owner；方案只加主包和挑战包，交付与 adapter 仅在真实触发时加载 |
| 专家按需会诊 | 复杂决策才发散和质询；简单任务不走形式 |
| 推荐契约先行 | 承重决策逐层集中确认，AI 代选细节随完整契约展示 |
| 真实页面优先 | 现有页面增强直接做实装预览并复用同一补丁；只有方向探索才生成独立视觉候选 |
| 最小项目就绪 | 项目能开工就不改；缺什么只补真正阻断的那一处 |
| 证据先于完成 | 同一内容、命令和环境复用回执；输入变化或跨真实环境才 fresh |
| 文档服从恢复 | 简单任务零文档；复杂项目也只按真实恢复需求启用热真源 |
| 决策只留现行结论 | 最新目标高置信覆盖旧决定；有实质误判风险时先确认 |
| 知识导航而非堆积 | 复用一个项目入口定位代码、运行态、规范、理由和活动任务 |
| 知识必须可消费 | 说清使用场景、核心决策价值和唯一真源入口才进入长期层 |
| 完成 Plan 退出热区 | 先退出默认上下文，再经退休检查决定保留 Plan 或授权删除 |
| 副作用先授权 | 未经明确授权，不 commit、push、merge、deploy、delete 或公开发布 |

缺少 subagent、浏览器、memory 或 Git 时，workflow 会改用当前环境能提供的安全路径，并明确哪些验证没有做；不会伪造 PR、发布或完成状态。

## 自动更新与卸载

workflow 直接把 GitHub 最新正式、immutable Release 作为发布真源。自动同步不进入 workflow 调用路径；系统在登录时运行一次，之后每 24 小时运行一次。启用前可以只读预览将要创建的用户级任务：

从新克隆的官方源码整体替换旧安装：

```bash
python3 scripts/install.py update --target "/path/to/agent/skills"
```

```bash
python3 scripts/install.py enable-auto-update --target "/path/to/agent/skills" --dry-run
python3 scripts/install.py enable-auto-update --target "/path/to/agent/skills"
```

立即同步一次：

```bash
python3 scripts/install.py sync --target "/path/to/agent/skills"
```

同步只接受最新正式 Release 中唯一的 `workflow.zip`，并核对 GitHub 返回的 SHA-256、Release tag、包内版本、doctor 和 release check。所有检查先在临时目录完成；失败不会修改当前 workflow。成功后整体替换 `<skills父目录>/workflow`，不保留 backup、failed 或 removed 副本，也不支持本地一键回滚。

停用自动同步后永久卸载：

```bash
python3 scripts/install.py disable-auto-update
python3 scripts/install.py uninstall --target "/path/to/agent/skills" --yes
```

维护者发布自动更新版本时，先创建 draft、上传 `workflow.zip`，再发布为最新正式 immutable Release；draft 和 prerelease 不进入普通用户自动同步。

## 项目维护

运行完整检查：

```bash
python3 -B -m unittest discover -s tests -p 'test_*.py' -v
python3 -B scripts/release_check.py
```

贡献方式见 [CONTRIBUTING.md](CONTRIBUTING.md)，安全问题见 [SECURITY.md](SECURITY.md)，来源与 clean-room 边界见 [NOTICE.md](NOTICE.md)。本项目按 [MIT License](LICENSE) 发布。

---

## English

`workflow` is a dependency-closed AI skill that turns an incomplete goal into a verified delivery. It defaults to the minimum sufficient process, proposes a complete requirement contract after focused research, and escalates only for material uncertainty, risk, compatibility, or recovery needs. Install this repository only; no other custom skill or third-party Python package is required.

Ask your agent to clone `https://github.com/qzl0215/workflow`, identify its own skills parent directory, run `python3 scripts/install.py install --target "<skills-directory>"`, enable the explicit user-level daily updater with `enable-auto-update`, and verify with `check`. The single active package lives at `<skills-directory>/workflow`; verified updates replace it without retaining discoverable backups. Ambiguous targets and duplicate workflow skills fail closed.

See the [visual introduction](docs/workflow-visual-map.html), or run `python3 -B scripts/release_check.py` to verify a checkout.
