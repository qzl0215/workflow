# workflow

**把复杂目标推进成有证据的真实结果，同时尽量少走流程、少耗上下文、少打断用户。**

`workflow` 是一个可独立安装的中文 AI 工作协议。3.0 不再把模型固定在细密的七阶段流程里，而是守住结果、风险、授权和证据四类边界，让能力更强的模型自行选择研究方法、拆分粒度、并行方式与验证组合。

作者：zhonglin · MIT License
当前协议版本：`3.1.0`

[打开完整可视化](docs/workflow-visual-map.html) · [查看正式协议](SKILL.md)

## 一张图看懂 3.0

```text
                       ┌─ 按需：最小研究 research ─┐
                       ├─ 按需：深度质询 grill ───┤
                       └─ 按需：体验探索 experience┘
                                      ↕ 只反馈受影响结论

  目标框定 Frame  →  结果规划 Plan  →  任务执行 Execute  →  结果验真 Prove
        │                  │                   │                    │
        │                  └→ 串并联编排       └→ 失败时恢复        ├→ 无外部交付：完成或按信号复盘
        │                      子任务独立定深度                       └→ 有外部交付：Deliver → 按信号 Learn
        │
        └→ 只把会改变结果、风险、代价或授权的承重决定交给用户
```

用户可见的核心主链只有四个环节：

| 核心环节 | 必须回答的问题 | 退出依据 |
|---|---|---|
| 目标框定 | 究竟要改变谁的什么状态？ | 结果、验收、边界与承重未知足以指导行动 |
| 结果规划 | 怎样把结果拆成有责任和证据路径的工作？ | 每项验收都有实现责任、依赖和验真路径 |
| 任务执行 | 当前就绪责任怎样变成真实产物？ | 产物、候选回执和偏差都已如实返回 |
| 结果验真 | 什么新鲜证据证明用户结果成立？ | 已接受证据覆盖结果契约，而非只覆盖改动清单 |

两个条件环节不为了流程完整而出现：

- **真实交付**只在目标包含提交、合并、部署、发布或外部写入时进入。
- **经验复盘**只在本次事实能改变未来行动时进入；任何线程发生上下文压缩都会强制进入这道复盘门，检查 workflow 或项目级 `harness` 的上下文治理与无效业务动作。压缩本身不等于缺陷，检查后仍可 `no-op`。

当两者都需要时，默认顺序是 `Prove → Deliver → Learn`。等待外部平台时可以并行收集不依赖交付结果的复盘候选，但最终经验必须在真实交付状态确定后接受，不能预判发布成功。

## Frame 内不是三道固定工序

`research`、`grill`、`experience` 是目标框定中的条件反馈能力，不是默认全并行，也不是必须逐个执行。

最佳实践是：

1. **先判断事实是否足够。** 足够就不研究；不足时才由模型做最小研究，避免拿可查事实向用户提问。
2. **承重决定仍不稳，才进入 grill。** `grill-me` 兼容入口仍保留，并且是更强的挑战深度，不是简单列问题。它寻找反例、失败场景、隐藏代价和更简单的可逆方向，直到新增信息不再改变推荐。
3. **体验会改变方向，才进入 experience。** 对现有页面局部修改，直接在真实源码划分改动面与保护面，优先使用复用真实登录态的只读独立验收入口展示同一候选；结构性保真足够时不做全量人工前后对比。只有多个互斥方向形成承重方向分歧时才制作独立概念稿。
4. **只有独立且能缩短关键路径时并行。** 并行取得的只是候选输入，最后由目标责任者合成为一个结果契约。
5. **只回流受影响部分。** 新发现只有实质改变契约才重开另一条能力，不全量重跑。

这套结构保留了深度，又避免研究、质询和体验团队对同一问题重复取数、重复总结、重复询问。

## Plan 怎样拆串并联，并守住子任务深度

结果规划先从验收反推责任，再由任务编排决定串联、并联和角色，而不是先按文件或 Agent 数量切块。

```text
结果契约
  └─ P01 可独立验收的结果
       ├─ T01 建立公共边界 ─────────────┐
       ├─ T02 独立实现 A（可并行）──────┤
       ├─ T03 独立实现 B（可并行）──────┤→ 汇合 → 整体验真
       └─ T04 共享资源变更（串行）──────┘
```

只有同时满足这些条件才并行：输入和输出边界清楚、可写现场或共享资源能隔离、无需频繁互相等待、汇合成本低于节省的时间。否则串行通常更快、更稳。

每个子任务独立决定思考深度，不继承父计划的形式复杂度：

- 已知路径、局部且易回退：直接实施并做定向验证；
- 跨模块、接口或共享机制：增加消费者和相邻集成检查；
- 并发、迁移、权限、安全、生产形态或难复现行为：先建立可失败实验、回退点和更强观测；
- 目标或体验方向未定：回到上游，不在实现中靠偏好补齐。

子 Agent 的交接也不靠自由发挥猜上下文：协调者发送最小任务胶囊，包含目标、父计划和任务契约的身份摘要；执行者在授权范围内工作并把同一身份随候选回执返回。协调者核对契约漂移、真实产物、证据身份和语义冲突后，才把它接受为整体结果。子任务绿灯不能代替整体验真。

## 为什么只保留一个 `work.md`

3.0 不是把 `findings.md`、`progress.md`、`implementation-plan.md`、`index.md` 和 `task-owner-prompt.md` 的全文机械拼成一个巨型文件，而是删除它们对“当前状态”的重复描述，只保留一个稀疏控制面。

| 信息 | 默认位置 | 何时物化 |
|---|---|---|
| 结果契约、当前计划、依赖、状态、已接受证据、阻断 | 协调者独占的 `work.md` | 仅在跨会话、多人协作、昂贵证据或恢复成本真实存在时建立 |
| 子任务胶囊 | 委派消息内联 | 需要跨上下文恢复时物化，并由协调者登记入口 |
| 执行回执 | 子 Agent 返回内联 | 昂贵或不可复现证据才物化 |
| 过程探索与被拒候选 | 当前上下文 | 默认不进入持久真源 |

这对高复杂度多 Agent 项目更稳的关键不是“文件更少”，而是写入权更清楚：

- `work.md` 只有协调者写，避免多个 Agent 并发覆盖当前状态；
- 执行者回执永远先是候选，不能自称已被整体接受；
- 当前投影替代流水账，恢复时只读有效结论；
- 胶囊和证据仍可独立保存，不会为了单文件而丢掉必要深度。

简单任务不创建 `work.md`，计划、胶囊和回执留在当前上下文即可。长项目会把完成分支压缩成结果级证据入口；整体完成后退役当前 `work.md`，避免单文件最终长成永久日志。

## reference 是渐进路由，不是统一表格

四大核心环节不需要再各自复制一棵同形目录树。3.0 当前的十一份 reference 都只在问题需要时读取，并共同守住：**先取最小充分结果，真实信号出现才加深，达到停止条件就返回**。它们不必拥有同一章节、长度或推理形式。

| 当前问题 | 按需读取 |
|---|---|
| 框定真实结果 | [`frame.md`](references/frame.md) |
| 缺少会改变决定的事实 | [`research.md`](references/research.md) |
| 承重假设、矛盾或高代价取舍 | [`grill.md`](references/grill.md) |
| 体验或交互可能改变方向 | [`experience.md`](references/experience.md) |
| 从结果形成计划和任务契约 | [`plan.md`](references/plan.md) |
| 决定串并联、责任与上下文边界 | [`orchestrate.md`](references/orchestrate.md) |
| 实施当前就绪任务 | [`execute.md`](references/execute.md) |
| 失败、证据冲突或尝试无进展 | [`recover.md`](references/recover.md) |
| 声明结果完成 | [`prove.md`](references/prove.md) |
| 执行真实外部交付 | [`deliver.md`](references/deliver.md) |
| 判断是否沉淀经验 | [`learn.md`](references/learn.md) |

因此，模型可以在简单任务上快速通过，也能在高风险子任务上继续加深；协议规定的是责任和硬门，不是固定题数、轮数、Agent 数量、重试次数或唯一工具链。

## 关键出口强制四行画面，内容先让业务人员读懂

workflow 启动后的首次进展、环节实质变化、真实阻断、最终交付和交回控制权必须展示“结论 + 四行画面”；状态没变不重复。同一轮完成的轻量任务只在最终出口展示一次：

> 结论｜新版工作流已安全启用，后续任务会按新规则执行<br>
> 进度｜■■■■｜■— · 核心结果完成 · 已完成真实更新 · 本次无需复盘<br>
> 技能｜[任务执行](references/execute.md) · [结果验真](references/prove.md) · [真实交付](references/deliver.md)<br>
> 成果｜✓ 旧版已安全替换 · ✓ 新版已确认可正常使用 · ✓ 没有产生重复安装<br>
> 路径｜确认更新目标 → 安全替换旧版 → 验证实际可用

- `结论` 和 `成果` 先表达用户状态、实际影响与是否可用，不用技术检查名代替意义。
- `进度` 的前四格对应核心主链；条件环节实际进入后才追加。`■ / ◆ / □ / —` 表示完成、当前、未完成、不适用。
- `技能` 只列本轮真正使用的中文能力名。
- `路径` 使用业务结果或用户动作；内部 Plan/Task 编号只在确有定位价值时补充。

文件数量、`runtime`、`Manifest`、`doctor`、测试命令和哈希属于按需技术证据。只有它们会改变决定、风险或可信度时才展开，并且先说明业务含义。需要用户接棒时，再按需补充风险、下一步和最短回复建议；没有用户行动就不制造栏目。

## 安装

需要 Python 3.9+，运行时不需要第三方 Python 包。

### 推荐：复制给当前 Agent

> 请安装 GitHub 项目 `https://github.com/qzl0215/workflow`。先克隆到临时目录，再根据当前 Agent 配置确认 skills 父目录，不要猜固定路径；运行 `python3 scripts/install.py install --target "<skills父目录>"`。若已有安装，使用 `update` 整体替换。随后运行 `enable-auto-update`，最后运行 `check`；只有唯一性与完整性验证通过后才报告完成。只保留一个活动 workflow，不保留可被宿主发现的旧副本。

### 终端安装

```bash
git clone --depth 1 https://github.com/qzl0215/workflow.git
cd workflow
python3 scripts/install.py detect
python3 scripts/install.py install --target "/path/to/agent/skills"
python3 scripts/install.py check --target "/path/to/agent/skills"
python3 scripts/install.py enable-auto-update --target "/path/to/agent/skills"
```

已存在安装时，把 `install` 改为 `update`。安装结果是 `<skills父目录>/workflow`；目标不唯一或发现多个 workflow 时会停止，不替用户猜测。

## 2.x 到 3.x 的迁移边界

3.0 的安装包只包含 manifest 声明的精简运行时，不再携带测试、维护脚本和对外文档。2.26.0 是专门为这种格式准备的兼容桥。

| 当前活动版本 | 更新到 3.x | 原因与动作 |
|---|---|---|
| `2.26.x` | 可直接 `sync` | 2.26 已理解 `workflow-package.json`、逐文件散列和精简运行时，会在同文件系统暂存验证后事务替换 |
| `2.25.x` 或更早 | 旧更新器应失败关闭 | 旧版不应猜测 3.x 文件清单；它会保留原安装。请从已验证的 3.x tag 或正式 Release 重新取得源码，使用其中的新安装器执行 `update`，再运行 `check` |
| 无安装 | 从 3.x 源码安装 | 新安装器只复制 manifest 中的运行时文件，并验证唯一性与完整性 |

错过 2.26 时，不要手工删除旧文件再把 ZIP 覆盖进去。建议使用临时克隆：

```bash
git clone --depth 1 --branch 3.1.0 https://github.com/qzl0215/workflow.git workflow-3
cd workflow-3
python3 scripts/install.py update --target "/path/to/agent/skills"
python3 scripts/install.py check --target "/path/to/agent/skills"
```

正式自动同步以 **GitHub 最新正式、immutable Release** 为唯一远程真源：只接受非 draft、非 prerelease 的唯一 `workflow.zip`，核对 Release tag、资产 SHA-256、包内版本和 `workflow-package.json` 中每个运行文件的 SHA-256，然后运行一次 manifest 指定的 doctor。自动更新登录时运行一次，之后最多每 24 小时一次。

候选在目标 skills 目录同一文件系统的隐藏 stage 中先完整验证，再用 rename 事务激活。可捕获的激活后失败会恢复旧安装；成功后不保留 backup、failed 或 removed 副本。强制终止或主机掉电跨越两次 rename 的极窄窗口不承诺崩溃原子性，异常现场应从指定的已验证 Release 重新安装。

立即同步或停用自动更新：

```bash
python3 scripts/install.py sync --target "/path/to/agent/skills"
python3 scripts/install.py disable-auto-update
```

永久卸载会删除唯一活动副本，需要显式确认：

```bash
python3 scripts/install.py uninstall --target "/path/to/agent/skills" --yes
```

## 安全与降级

- 未经明确授权，不扩大外部副作用；范围已清楚的持续交付授权不重复询问。
- 任一验证、集成、部署或发布后检查失败时，停止后续外部写入，保留可恢复现场并报告真实状态。
- 没有子 Agent 就由同一模型顺序承担职责；没有持久存储就留在上下文；没有 Git 就交付文件和证据。工具降级不能把未覆盖写成通过。
- 纯问答、解释、只读审查和一次性查询不启动 workflow。

## 项目维护

完整候选只跑一次正式门：

```bash
python3 -B -m unittest discover -s tests -p 'test_*.py' -v
python3 -B scripts/release_check.py
```

`release_check.py` 负责调用 runtime doctor、校验 manifest 与生成页面，不需要把相同检查拆成多次仪式。贡献方式见 [CONTRIBUTING.md](CONTRIBUTING.md)，安全边界见 [SECURITY.md](SECURITY.md)，来源与 clean-room 边界见 [NOTICE.md](NOTICE.md)。
