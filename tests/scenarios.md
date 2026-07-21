# workflow 行为验收场景

本文件验证真实编排行为，不要求模型复述固定措辞。每次重大协议变更都应逐项检查一条完整轨迹：

`业务目标 → 当前阶段 → 最小上下文 → 责任角色 → 使用能力 → 权限边界 → 实际输出 → 验收结果 → 下一步`

维护本 Skill 时，由 Agent 先检查结构与引用，再逐项以“协议是否能导出 Then 行为”为准审阅受影响场景；不要求安装语言运行时，也不把关键词命中当成行为通过。

## S01｜批准计划后再隔离开工

- Given：用户在有 remote 的项目提出复杂写需求，当前工作区可能已有用户改动，并要求先看正式计划；宿主可能已经为当前任务提供独立 worktree。
- When：workflow 完成需求与方案并生成 `task_plan.md`。
- Then：先让用户一次批准需求 baseline、已选方案、范围与编排；批准后先复用已满足隔离、归属和最新基线要求的宿主工作现场，只有不足时才新建 Request branch/worktree；随后才开始首次实现写入，不覆盖、stash 或重置用户原工作区。

## S01A｜简单小改不升级为重流程

- Given：用户明确要求在一个干净、安全、没有无关用户改动的现有项目中完成局部、可逆、短生命周期小改。
- When：workflow 完成最小需求、方案与对话内编排。
- Then：`plan_mode=inline`、`approval_state=not-required`；不创建四份真源、不追加计划确认，也不机械创建第二个 worktree。开工门完成只读安全检查后直接在当前安全现场实施；如发现脏工作区、多人并行、跨会话恢复、复杂依赖或难逆风险，再升级为相称隔离或正式路径。

## S02｜同一 Request 的多 Agent

- Given：一个 Request 内有三个可执行 Task。
- When：协调者派出多个 Agent。
- Then：所有 Agent 默认共享 Request worktree，不自行创建 worktree、commit、rebase 或 push；总协调者唯一维护状态与 Git 生命周期。

## S03｜一串相关需求

- Given：用户一次提出八项要求，包含重复、依赖、共享基础和冲突。
- When：workflow 看清需求并规划。
- Then：只建立一个 Request；逐项生成稳定 Requirement ID，先查事实，再形成关系图、Plan DAG 和 Task DAG。

## S04｜高价值 Grill

- Given：多项需求仍有会改变目标、Plan 分组、顺序、验收或授权的未知。
- When：触发 Grill。
- Then：AI 先查可发现事实；只有答案会改变用户结果、范围、验收、授权或难逆风险且没有安全默认时才暂停。一轮围绕一个决策主题，通常只问 1–3 个相关问题；每题用业务语言说明推荐、2–3 个互斥选项及答案会改变什么。

## S04A｜不为低价值未知打断用户

- Given：剩余未知属于项目中可查事实、已有安全可逆默认，或只是实现偏好。
- When：需求阶段判断是否 Grill。
- Then：提问数为 0；AI 自行调查或采用已声明的安全默认，并在需求确认卡中简短说明后继续。

## S05｜多 Plan 的简明进度

- Given：P01 正在质量验收，P02 正在执行建设，P03 被外部依赖阻塞。
- When：保存和恢复 Request。
- Then：`progress.md` 只用“当前 / 工作进展 / 验收记录”三块展示 P01/P02/P03 的阶段、当前结果、下一步或等待原因；工作项状态只用 `待做 / 进行中 / 等待中 / 已完成`，`findings.md`、`task_plan.md` 和 `implementation-plan.md` 不保存第二份运行状态。

## S06｜规划期避免写冲突

- Given：两个 Task 修改同一文件、符号、schema、lockfile、生成产物或共享可变资源。
- When：计划编排串并行。
- Then：合并写 owner 或串行；不得依赖后续 rebase 来修复本可预防的同 Request 冲突。

## S07｜安全并行

- Given：两个当前可开始的 Task 无依赖路径、写域独立、验证环境独立，且并行收益为正。
- When：多 Agent 执行。
- Then：协调者从 Task 合同、`progress.md` 当前切片和精确证据引用生成独立上下文包并行实施；所有编排真源仍只由协调者更新。

## S08｜最小上下文与 Task 合同

- Given：Task Agent 开始实施。
- When：协调者交接上下文。
- Then：复杂、委派或跨会话 Task 在派发前有一份版本化执行合同；Agent 只收到该合同、当前状态切片和精确证据引用，不默认收到完整 Portfolio、专家会议和无关 Task 历史。

## S09｜方案选型只在真实取舍时暂停

- Given：需求已经清楚，可能只有一条明显优势路线，也可能存在 2–3 条在体验、成本、风险或难逆方向上不同的真实路线。
- When：进入方案选型。
- Then：单一路线明显占优且可逆时，AI 给出推荐并继续；存在人类必须承担的业务取舍时，用选择题、短表、线框或 HTML demo 中最合适的一种呈现，并暂停等待选择。用户选过的方向不得在正式 Plan 中重复询问。

## S10｜失败时才加载 Debug

- Given：Build 出现测试失败、异常或非预期结果。
- When：进入失败回路。
- Then：先复现、定位根因、验证假设并最小修复；没有真实失败时不加载 Debug reference。

## S11｜有信号才展开专项 Simplify

- Given：实际 diff 出现重复实现、不必要复杂度、维护性或明显效率风险，或用户明确要求专项 simplify。
- When：进入质量验收。
- Then：由当前验证 owner 在同一次 review 中检查复用、删除、合并、效率和不必要抽象，修复确认问题后只 fresh 验证受影响路径；没有具体风险信号时不展开独立 simplify 流程，也不为此默认派 Agent。

## S12｜验收反馈的 Delta Intake

- Given：验收时用户连续提出缺陷、遗漏、小优化、新业务结果和无关需求。
- When：收到反馈。
- Then：先在 `progress.md` 捕获并冻结原验收基线，分类完成前不改代码；需要时先升级 `findings.md` 的需求 baseline 或 `task_plan.md` 的正式计划版本，再失效受影响 Task 合同并重新判断哪些工作项可以开始，未受影响工作继续。

## S13｜无关新 Request

- Given：验收反馈中出现可独立交付、独立验收且与当前目标弱相关的新需求。
- When：用户要求推进该需求。
- Then：当前 Request 保持原交付基线；新需求不继承未合入功能分支，重新走自己的 01–03 与开工门。需要正式或相称隔离时，才从最新可信目标建立自己的 Request worktree。

## S14｜交付前 Rebase 与 AI 冲突解决

- Given：目标分支在 Request 执行期间前进。
- When：进入集成交付并已有相应授权。
- Then：总协调者 fetch/rebase；AI根据双方业务意图、diff、约束和测试解决文本与语义冲突；source fingerprint 改变后只失效受影响证据，并 fresh 重验相关 Plan、跨 Plan 集成和 Request 关键路径。

## S15｜AI Review 与受控进化

- Given：实现已完成，且可能产生可复用经验。
- When：质量验收与复盘。
- Then：不默认等待人类 Reviewer；只有高风险、职责冲突或独立证据的净收益明确为正时才增加一个独立 Agent，否则由当前 owner 完成一次整合式 fresh review。项目事实可安全回灌；workflow 只有两次独立复现或一次严重、系统且可复现问题才晋升。

## S16｜能力缺失时安全降级

- Given：当前环境没有 Git remote、独立 Agent、浏览器或持久 memory 中的一项或多项。
- When：workflow 推进当前工作。
- Then：只改变实现手段，不降低业务验收要求；宿主有对应原生能力时不执行、不叠加同类 fallback，且同一关注点的条件 fallback 读取数为 0；宿主缺失时每个触发关注点最多加载一个最小 fallback；明确未覆盖项，不把计划、模拟或未验证结果写成完成。

## S17｜运行包 Clean-room 安装

- Given：用户已有能操作本地文件的 Agent，可能已安装旧 workflow，但没有 Python 或不知道 skills 目录。
- When：用户发送同一句 Agent 安装/更新提示词。
- Then：Agent 必须唯一定位真实 skills 目录，先把最新目标解析成一个不可变 commit SHA，再从同一 SHA 将根协议、阶段 references、templates 和 `tests/scenarios.md` 下载到临时目录并校验，最后原子替换；更新失败恢复备份，首次安装失败删除未完成目录；报告版本/commit/位置，全程不要求 Python。

## S18｜Plan 验收与 Request 交付分开

- Given：P01 已通过质量验收，P02 仍在执行，二者共享一个 Request worktree。
- When：协调者判断下一步。
- Then：P01 只标记为可汇合，不提前 rebase 或交付共享分支；所有纳入 Plan 通过后才进入 Request 级集成交付，并重验跨 Plan 与整体结果。

## S19｜只补最小项目地基

- Given：当前 Request 无法可靠找到项目入口、运行/验证/部署路径、关键模块边界或 UI 设计契约中的一项。
- When：计划编排检查可执行性。
- Then：先复用现有 owner，只把真实缺口变成前置 Task；最多按需补 AI 入口、运行与交付入口、项目全景导航、设计契约，不默认创建 ADR、术语表或治理文档，并用下一位 AI 的 clean-room 路径验收。

## S20｜四份唯一真源与文档预算

- Given：项目级 Request 需要跨会话推进，并包含事实调查、完整方案、多 Task 执行和验收反馈。
- When：workflow 建立持久化文档。
- Then：`findings.md` 拥有完整需求 baseline、背景调查和判断依据，`task_plan.md` 拥有批准方案、PRD 与 Plan/Task 顶层编排，`implementation-plan.md` 只在复杂实施时拥有 Task 执行合同，`progress.md` 独占运行状态与验收记录；不建立 `request.md / plan.md / task.md` 兼容副本，也不默认建立 Evidence、Capsule、每 Plan 进度或每 Agent 文档。

## S21｜复杂 Task 才展开实施合同

- Given：`task_plan.md` 中一个 Task 变成需要委派、跨会话或高冲突风险的复杂 Task。
- When：协调者展开实施合同。
- Then：`task_plan.md` 只保留 Task ID、业务摘要、所属 Plan、依赖与波次；完整输入、写域、DONE、验证和停止条件只写在 `implementation-plan.md` 的同 ID 小节。简单 Task 保持 inline，不为每个 Task 或 Agent 机械建文件。

## S22｜Progress 保持为当前快照

- Given：Request 已执行多轮 Task、验证和反馈路由。
- When：协调者更新 `progress.md`。
- Then：已完成 Task 折叠进当前业务结果；已处理反馈、已解除等待和过期验收记录从当前快照移除，重要判断回写 `findings.md` 或计划真源；历史交给 Git 或原始产物，不形成 Queue、事件表或 Markdown 日记。

## S23｜默认走最短但足够的路径

- Given：同一个 workflow 既可能接到本地可逆的小改动，也可能接到跨域、难逆或高影响公开发布的复杂目标。
- When：总协调者决定调查、专家、文档、Agent 和验证投入。
- Then：不持久化或向用户展示 H0–H3；默认不建文档、不派 Agent、不召集专家。只有额外方法能改变关键决策、降低主要风险、带来安全并行或补足必要验收时才启用，证据足够立即收敛。

## S24｜相同证据不机械重跑

- Given：同一 Request 已有一条通过证据，其被验对象/产物、输入/依赖 fingerprint、环境、命令/场景、验收 baseline、观测时间和有效条件都可复核。
- When：后续阶段需要引用相同结论。
- Then：只有确定性检查、被验对象/产物与全部实质输入已指纹化、环境/命令/验收一致、有效条件仍成立且原始结果可用时才复用；任一项变化只失效受影响证据。外部可变状态在决策点重新观测；Rebase、冲突修复、依赖或产物变化后重验相关路径。

## S25｜零 Python 的维护验收

- Given：维护者电脑只有能读写仓库和执行基础 Git/文本检查的 Agent，没有 Python。
- When：安装、更新或修改 workflow。
- Then：运行包镜像 `SKILL.md`、`references/`、`templates/` 和按需维护契约 `tests/scenarios.md`；Agent 检查 frontmatter、相对引用、文件可达性、版本、安装提示词同步、敏感信息、冲突标记、行为场景与变更 diff，并给出可追溯结论，不要求任何 `.py` 文件或 Python 环境。

## S26｜计划确认与连续执行的交互预算

- Given：用户已经明确授权实施，但任务难度和未决取舍不同。
- When：workflow 准备从计划进入建设。
- Then：只有选择正式计划路径才出现通用批准门；无论草案暂存在对话、安全计划区还是最终 `task_plan.md`，都必须保持 `plan_mode=formal`，并在 `approval_state=approved` 后才可开工。用户一次批准需求 baseline、已选方案、范围和编排；开工后默认持续到 AI 验收与授权内交付，只有新的业务契约变化或未授权难逆决策才中断；同一决定重复确认次数为 0。

## S27｜需求确认卡自动续行

- Given：一个标准或正式任务的需求阶段已查清关键事实，剩余假设都有安全可逆默认，不再存在会改变方向的红项。
- When：看清需求阶段结束。
- Then：向用户展示一张简短的“需求确认卡｜我将按此继续”，只含为谁解决什么、最终得到什么、本次做/不做、怎样算完成和安全默认；它从 `findings.md` 渲染，不新增文档、不询问“是否确认”，随后自动进入方案选型。

## S28｜同一关注点只有一个方法 owner

- Given：Codex 已提供设计、Agent 协作、调试、验证或 Git 中的某项原生能力，而 workflow 包内也有同类 fallback。
- When：workflow 选择当前阶段的执行方法。
- Then：只使用用户指定或宿主原生且与四真源兼容的一项能力，不执行、不叠加同类 fallback；该关注点的条件 fallback 读取数为 0。业务阶段协议仍可读取，但只规定边界和输出，不包含与原生能力竞争的方法。结果回写四真源，不创建第二份计划、状态或确认。原生能力缺失时才读取一个对应 fallback。

## S29｜旧命名直接兼容现有技能

- Given：`write-plan`、`act-plan`、`strategic-planning`、`verification-before-completion` 或 `design-chief` 与 workflow 一起使用。
- When：它们读取或写入项目计划。
- Then：统一使用 `findings.md / task_plan.md / implementation-plan.md / progress.md`；`task_plan.md` 不存运行状态，`implementation-plan.md` 按复杂度创建，`progress.md` 是当前进展唯一 owner，不生成新命名的兼容副本。

## S30｜P / T 双 DAG 一眼可读

- Given：正式 Plan 包含多个业务 Plan，每个 Plan 下又有串行、并行和跨 Plan 汇合的 Task。
- When：用户或 fresh Agent 打开计划。
- Then：`task_plan.md` 先用 Plan DAG 展示业务结果的依赖和汇合；`implementation-plan.md` 再用按 Plan 分组的 Task DAG 展示 Task 依赖、并行波次和跨 Plan 边。两张图都配业务摘要表，图中 ID 能直接定位同 ID 合同。

## S31｜讲座只讲最终协议

- Given：Workflow 根协议、references、templates 和伴生技能已经通过验收。
- When：更新讲座 HTML。
- Then：保留黑黄白主题、高质量翻页、全局步骤导航、富文本 Markdown 阅读、字号和阶段成果高亮；内容只展示七阶段、四真源、必要用户触点、人/AI 分工和清楚的 P/T DAG，不再出现旧阶段、旧文件、H0–H3、Cell、Queue 或 Evidence Index。

## S32｜对话里的正式草案不能绕过批准

- Given：03 已选择 `plan_mode=formal`，正式草案仍只存在对话或安全计划区，尚未落为产品工作区中的 `task_plan.md`。
- When：workflow 尝试进入开工门。
- Then：只按逻辑状态判断；`approval_state=draft / rejected / modified` 一律停留在 03，不因文件尚未落盘而降级为 inline 或开始写入。只有用户批准当前版本，状态变为 `approved` 后才可继续。

## S33｜规划后基线漂移分流

- Given：正式计划获批后、首次实现写入前，最新目标与计划记录的 source fingerprint 不同。
- When：开工门复核影响。
- Then：若变化只影响可逆实现细节，AI 更新规划基线、Task 合同和受影响验证，不重复请求批准；若变化改变用户结果、范围、验收、关键体验、难逆风险、成本/时间承诺或交付目标，则返回对应阶段、升级版本并只请用户决定受影响部分。

## S34｜计划批准不扩大外部授权

- Given：用户已经批准正式计划，但 `findings.md#authorization` 未授权 commit、push、merge、deploy、delete、公开发布或生产写入。
- When：执行进入可能产生外部副作用的动作。
- Then：计划内本地可逆实施继续，外部动作保持等待并提出一个具体授权决定；不得把 `approval_state=approved` 当作外部授权。

## S35｜正式计划的 P / T 双 DAG 可直接导航

- Given：正式计划包含 P01、P02 并行后汇合到 P03，每个 Plan 下有串行与并行 Task。
- When：人或 AI 打开 `task_plan.md` 与按需的 `implementation-plan.md`。
- Then：先看到 P-DAG 的业务全景，再看到按 Plan 分组的 T-DAG；跨 Plan 边位于分组外，波次与并行关系无需阅读合同即可理解。图节点和摘要表中的每个 ID 都是可点击链接，直接到同 ID 计划摘要、inline Task 或复杂 Task 合同。

## S36｜轻任务运行预算

- Given：用户明确要求一个答案已知、局部、可逆、当前工作区安全的小改，并显式调用 workflow。
- When：workflow 从需求推进到完成。
- Then：除必读根 `SKILL.md` 外，不为“经过阶段”机械读取阶段 reference；持久化文档数、子 Agent 数、独立需求卡、额外计划确认数和新增 worktree 数均为 0。AI 把需求理解并入最终一句，完成一次相称实施与 fresh 验证后结束。

## S37｜标准任务默认 solo

- Given：一个单会话可完成的普通多文件功能，没有独立写域并行收益，也没有高风险独立复核需求。
- When：workflow 选择执行与验收方式。
- Then：默认由当前 AI 连续完成，不因 UI、多文件、多个阶段或“角色分工”自动派 Agent。阶段是内部检查点，不逐阶段向用户报到；只有当前判断需要细则时才读取对应 reference，状态只在实质变化或交接前更新。

## S38｜子 Agent 必须有净收益

- Given：当前目标可能从并行执行或独立复核获益。
- When：workflow 考虑派出子 Agent。
- Then：每个 Agent 必须对应独立决策、独立写域或能显著降低高风险误判的 fresh 证据，并且预期收益高于派发、等待、整合和复核成本；仅为“多一个视角”、模拟角色层级或满足固定人数不得派发。收益不再成立时立即回到 solo。

## S39｜一次验证关注点只跑一套

- Given：一个标准变更已完成实现，需要代码整理、review 和 fresh 验证。
- When：进入质量验收。
- Then：优先由同一个验证 owner 在一次影响面驱动的检查中完成简化审视、diff review 与 fresh 验证；一项检查可同时覆盖 Task、Plan 或 Request，多层共享且输入未变时直接复用，没有影响信号的层不运行。不默认再派独立 Reviewer；只有高风险、职责冲突或独立证据会明显提高置信度时才增加复核。

## S40｜禁止重叠审计扇出

- Given：一个实现结果需要最终复核，但 spec、质量、效率和兼容性检查读取同一 diff、共享大部分验收，结论也由同一总协调者整合。
- When：workflow 编排 Reviewer。
- Then：默认合并为一个正交终审，由同一 reviewer 按验收覆盖这些维度；不得仅按审查标题拆成多个重叠 Agent。只有各自拥有不同证据源、风险域或可并行验证环境，且每个结论都可能独立改变决定时才拆分。

## S41｜复用宿主已经隔离的工作现场

- Given：Codex thread、用户或其他兼容 harness 已经为当前 Request 提供干净、独立、归属明确且基于可信目标的 worktree。
- When：正式计划批准并进入开工门。
- Then：workflow 或直接调用的 `act-plan` 都只做只读复核并直接复用，不创建第二个 branch/worktree、不迁移已在该现场的唯一计划文件。只有现有现场不满足隔离、归属、基线或用户改动保护时，才最小升级为一个 Request 工作现场。

## S42｜无复盘信号直接结束

- Given：交付已通过，且没有未完成结果、反复返工、可删除步骤或达到复用门槛的经验。
- When：06 做交付收尾判断。
- Then：直接在最终汇报中记录 no-op 并结束；不读取 `references/07-review.md`、不派复盘 Agent、不创建复盘文档。只有至少一个判断为“是”才进入 07。

## S43｜模板不制造虚构拓扑

- Given：正式计划实际只有 P01 和两个真实 Task，其中一个 inline、一个需要复杂合同。
- When：根据四模板生成计划文件。
- Then：`task_plan.md` 和 `implementation-plan.md` 只保留 P01 与这两个 Task；删除模板语法占位、空节、空表和不存在的 P02/P03。单 Plan 可省略 P-DAG，T-DAG 仍按真实波次与合同链接清楚呈现，不为展示图而制造节点。
