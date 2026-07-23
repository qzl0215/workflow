# workflow

**你说目标，workflow 帮你看清、做成，并让下一次更高效。**

它把复杂工作统一成计划、执行、复盘三段七动作；遇到跨业务、产品、设计、技术或交付的复杂决策时，组织专家圆桌看见完整森林图景，再选路线、拆任务、实施、验收并把有效经验回灌到唯一真源。只安装 `workflow` 即可，不要求你再准备其他 skills，也不会为了显得完整给项目堆一套文档。

作者：zhonglin · MIT License

当前协议版本：`2.4.0`

[打开中文可视化介绍](docs/workflow-visual-map.html) · [查看完整工作协议](SKILL.md)

## 30 秒了解它在做什么

适合这些任务：

- 功能较复杂，需要跨多个文件或多个步骤；
- 需求还比较散，需要先看全局、定方案和优先级；
- 涉及 UI、视觉或动效，需要先定设计再写工程计划；
- 要跨会话推进，或需要多人 / 多 Agent 协作；
- 最终要有可复查的测试、交付或发布结果。

不适合纯问答、改一个错别字、一次性安全小操作。这些事情直接做更快。

收到需求后，它先判断是否值得进入完整流程。纯问答、改一个错别字、一次性安全小操作会直接做；复杂任务进入三段七动作：

> 计划：需求澄清 → 选定方案 → 拆成任务<br>
> 执行：执行任务 → 验收交付<br>
> 复盘：提炼经验 → 回灌改进

七个动作是证据检查点，不是七场固定仪式：证据已存在就快速通过，轻任务整体走短路径，但价值判断、完整 Plan 确认、验收证据和外部授权不会降级。

需求澄清不会先替用户编一张完整需求卡。workflow 先查项目和已有事实，再把真正需要人判断的目标、范围、成功标准、优先级与授权整理成编号问题批次；独立问题可一次询问，用户按 `1B 2A 3C` 回答，有依赖或回答含糊的分支继续追问。只有关键判断已回答、验证、明确延期或成为阻断后，才生成完成态需求卡并进入方案选择。

## 开工前先证明工作现场仍有效

workflow 不会因为目录还在、分支干净或历史测试通过，就默认旧工作现场可以继续修改。新任务必须从项目认可的最新基线和隔离现场开始；恢复同一任务时，目标版本前进不等于必须立即重做，而是先核对任务归属、变化范围和同步要求。已经被目标版本吸收的旧工作现场只用于只读追溯或等待授权清理，不能默认复用为下一项工作。

## 本地已验证 ≠ 已交付

当目标包含提交、合并或发布时，“验收交付”会固有地完成集成发布，不把本地测试绿色当作终点。workflow 先读取项目部署/发布文档以及项目规则、CI/脚本和仓库配置，确定真实 remote、目标分支、集成方式、版本、回滚与发布后检查；然后只在授权范围内连续完成：提交 → 合并 → 发布 → 发布后 smoke。

项目要求 PR/MR、CI、直接 fast-forward、特定部署命令或 GitHub Release 时，以项目真源为准，workflow 不硬编码平台流程。用户已经明确要求“提交合并发布”且目标可由项目文档唯一确定时，不会在每一步重复索取同一授权；目标不明、未授权或存在破坏性例外时，才停在一个具体决策点。

用户不承担代码审阅。AI 自己检查 diff、范围和测试，只把业务结果、风险与外部授权交给用户决定。PR/MR 仅在分支保护、必需 CI、项目规则或真实 reviewer 要求时使用；tag、Release、部署等节点也必须有独立价值，能由一个平台动作安全完成的步骤会合并，不为 Git 术语增加人工停顿。

## 状态变化会播报，需要你接棒才停下

进度、实际使用的 reference、有效成果或当前 Plan/Task 发生变化时，workflow 会在下一条可见消息顶部给出一次最新快照，然后继续工作；状态没变就不重复。快照固定使用普通文本与 Markdown 链接，不探测宿主、不生成 DAG 视觉，也不展示 Ready 队列。有正式计划时只补一行最短活动路径，例如 `✓ P01 → ● P02 / T03 → ○ P03`。

只有真正需要你纠正理解、选择方向、确认完整计划、提供外部输入、授权副作用、解除阻断、验收或接收完成时，workflow 才交回控制权。此时结论之后始终保留独立的“建议下一步”和“回复建议”，不会因精简 AI 调度信息而消失。下面用本包现有文件演示三种交接；真实任务会链接实际 reference 与成果。

### 场景一：方向决策

> 进度｜■◆□□□□□ 2/7 · 选定方案<br>
> 技能｜[选定方案](references/decide-solution.md) · [决策挑战](references/challenge-decisions.md)<br>
> 成果｜✓ [需求](references/understand-goal.md) · ● 方案 · ○ 计划 · ○ 交付 · ○ 进化<br>
> 结论｜推荐先验证单一路径，它覆盖核心价值且最容易回退。<br>
> 待决策｜推荐方案成本最低；备选方案覆盖更全，但会提前引入维护负担。<br>
> 建议下一步｜采用推荐方案并保留回滚点。<br>
> 回复建议｜回复“采用推荐方案”，或指出必须保留的备选能力。

### 场景二：阻断或授权

> 进度｜■■■■◆□□ 5/7 · 验收交付<br>
> 技能｜[验收交付](references/verify-deliver.md)<br>
> 成果｜✓ [需求](references/understand-goal.md) · ✓ [视觉方案](docs/workflow-visual-map.html) · ✓ [计划](templates/task_plan.md) · ● 交付 · ○ 进化<br>
> ✓ P01 → ● P02 / T03 → ○ P03<br>
> 结论｜成果已在本地验明，但发布会产生外部影响，尚未执行。<br>
> 风险｜继续发布会改变外部环境；保持本地不会产生副作用。<br>
> 建议下一步｜决定是否把本地已验证成果发布到目标环境。<br>
> 回复建议｜回复“授权发布”或“保持本地已验证”。

### 场景三：最终完成

> 进度｜■■■■■■◆ 7/7 · 回灌改进<br>
> 技能｜[验收交付](references/verify-deliver.md) · [提炼经验](references/learn-review.md) · [回灌改进](references/evolve-system.md)<br>
> 成果｜✓ [需求](references/understand-goal.md) · ✓ [视觉方案](docs/workflow-visual-map.html) · ✓ [计划](templates/task_plan.md) · ✓ [交付](CHANGELOG.md) · ✓ 进化<br>
> 结论｜纳入范围已完成并通过验收，未执行任何未授权外部动作。<br>
> 状态｜已完成<br>
> 代码完成｜已完成<br>
> 合并完成｜已合入主版本<br>
> 线上生效｜已生效<br>
> 建议下一步｜开始下一项最高价值目标。<br>
> 回复建议｜回复“继续下一目标”或直接提出新任务。

## 发现小改进时，先提案再动手

workflow 不会再按“出现几次”机械决定是否回灌。AI 会结合事实证据、实际影响、改动大小和长期收益做判断；一次发现也可能很有价值，重复出现的低价值噪音也可以不改。

提交前先做减法，只留下“小改动、大价值”的提案：痛点问题、AI 推断的补充需求、最小改造、预期业务价值，以及接受、调整或暂不做。用户接受提案只代表同意进入计划，完整 Plan 确认、外部动作授权和最终验收仍然独立。

获批后的改造在正确归属地完成：当前项目就沿原计划追加新的 Plan/Task；其他项目或 skill 使用最小 handoff capsule，把已确认需求、方案、验收和授权带过去，不重复访谈；没有稳定真源时先停下确认。生成一段 handoff 提示词不算完成，目标位置必须返回实际改动和 fresh 验证。

## 不知道下一步时：四路未知

workflow 不会把所有不确定都变成对用户的追问：

| 未知 | 怎么处理 |
|---|---|
| 事实可查 | AI 查项目、数据、工具、配置和可信来源 |
| 取舍待定 | 给推荐、代价和默认假设，必要时集中 Grill 决策者 |
| 假设待验 | 做最小实验、原型、小样或可失败验收 |
| 外部待解 | 写清 blocker、外部 owner、解锁条件与授权边界 |

四路未知处理完都会回到当前业务动作，不再制造第二套阶段名称。

## 专家圆桌如何看见整片森林

当问题跨多个领域、角色目标冲突或重大路线难以取舍时，workflow 会先判断“把这件事做到 90 分，最重要的专家角色是谁”，再邀请最相关的 3–5 个视角参与。角色不写死；每个专家都要勾勒最终画面、关键依赖、最大盲区以及会改变判断的新证据。

会议不是轮流发表套话，而是三段式：

1. **独立发散**：所有专家看同一份事实，各自指出机会、依赖、盲区和会改变判断的新证据。
2. **交叉质询**：互相挑战未经证明的假设、只顾局部的方案和遗漏的角色或生命周期。
3. **主持收敛**：把信息合成完整森林图景——目标、业务主线、能力、基础依赖、约束、风险和 2–3 条可走路线；再给出推荐方案、必要备选和删除理由。

简单、低风险、容易回退的任务不会为了“专家感”强行开会。没有多个 Agent 时也能顺序模拟多视角，但会明确说明这不是独立专家审查。

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

> 用 workflow 帮我推进这个项目的新功能。先把目标说清楚；需要时组织专家圆桌，给我完整森林图景和推荐路线。如果涉及界面，先完成体验、视觉与动效选型，再写计划、实现并按真实使用验收。

workflow 会按任务复杂度自动选择必要阶段。成熟项目不会被强行“补基建”；只有入口、约束、关键命令或验证路径真的缺失并阻断后续工作时，才优先补现有真源，极端情况下最多新建一份项目入口文档。

## 14 项按需能力如何保持思考深度

七个主 owner 分别守住七个业务动作；七个 harness 在关键追问与反向挑战、体验塑形、设计真源、Agent 协调、并行成果合并、失败修复和上下文交接有价值时叠加。AI 自动选择 H0–H3 中最低但足够的深度；H2/H3 会说明为什么需要加深，硬门不能降级。

UI 范围先用线框图确认旅程、信息架构和关键状态；用户认可方向后再投入高保真 demo。任务按 Plan/Task DAG 拆串并联，只并行文件域独立且收益高于协调成本的工作。估算聚焦 AI 执行路径、等待外部决策和风险缓冲，不把人的工作天数直接当成 AI 耗时。

## 它如何避免把事情做重

| 原则 | 实际行为 |
|---|---|
| 一个入口 | 包内只有一个根 `SKILL.md`，所有能力都已编排在同一个包内 |
| 按需读取 | 默认一次只读取当前阶段的一份 reference，不把整套流程塞进上下文 |
| 专家按需会诊 | 复杂决策才发散和质询；简单任务不走形式 |
| 关键问题集中问 | Grill 一次尽量问完相互独立的高价值问题，不用无限对话消耗用户 |
| 设计先于计划 | UI 任务先完成体验、视觉、动效和完整状态选型；非 UI 明确跳过 |
| 最小项目就绪 | 项目能开工就不改；缺什么只补真正阻断的那一处 |
| 证据先于完成 | 没有刚刚跑出的验证证据，就不声称任务已经完成 |
| 文档服从决策 | 只补有明确读者问题和唯一 owner 的真源；失去价值就合并或删除 |
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
python3 -B scripts/workflow_doctor.py
python3 -B scripts/release_check.py
```

贡献方式见 [CONTRIBUTING.md](CONTRIBUTING.md)，安全问题见 [SECURITY.md](SECURITY.md)，来源与 clean-room 边界见 [NOTICE.md](NOTICE.md)。本项目按 [MIT License](LICENSE) 发布。

---

## English

`workflow` is a dependency-closed AI skill that turns an incomplete goal into a verified delivery. For complex decisions it runs an expert roundtable, maps the full problem landscape, and converges on a recommended route before experience design, planning, implementation, debugging, verification, and delivery. Install this repository only; no other custom skill or third-party Python package is required.

Ask your agent to clone `https://github.com/qzl0215/workflow`, identify its own skills parent directory, run `python3 scripts/install.py install --target "<skills-directory>"`, enable the explicit user-level daily updater with `enable-auto-update`, and verify with `check`. The single active package lives at `<skills-directory>/workflow`; verified updates replace it without retaining discoverable backups. Ambiguous targets and duplicate workflow skills fail closed.

See the [visual introduction](docs/workflow-visual-map.html), or run `python3 -B scripts/release_check.py` to verify a checkout.
