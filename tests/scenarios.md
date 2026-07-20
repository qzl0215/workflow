# workflow 行为验收场景

本文件验证真实编排行为，不要求模型复述固定措辞。每次重大协议变更都应逐项检查一条完整轨迹：

`工作对象 → 当前阶段 → 最小上下文 → 责任角色 → 使用能力 → 权限边界 → 实际输出 → fresh evidence → 下一路由`

## S01｜Git 项目中的新 Request

- Given：用户在有 remote 的项目提出一个独立写需求，当前工作区可能已有用户改动。
- When：workflow 立项。
- Then：先只读检查并 fetch 最新目标分支，为整个 Request 建一个 branch + worktree；不覆盖、stash 或重置用户原工作区。

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
- Then：可查事实不问；独立问题集中在一个决策包，依赖问题按先后排列，总数不超过 15；每题说明推荐默认与影响。

## S05｜多 Plan 处于不同阶段

- Given：P01 正在质量验收，P02 正在执行建设，P03 被外部依赖阻塞。
- When：保存和恢复 Request。
- Then：`progress.md` 是所有运行状态的唯一控制台，分别记录 P01/P02/P03 的阶段、当前结果和 blocker；`request.md` 与 `plan.md` 不保存第二份运行状态。

## S06｜规划期避免写冲突

- Given：两个 Task 修改同一文件、符号、schema、lockfile、生成产物或共享可变资源。
- When：计划编排串并行。
- Then：合并写 owner 或串行；不得依赖后续 rebase 来修复本可预防的同 Request 冲突。

## S07｜安全并行

- Given：两个 Ready Task 无依赖路径、写域独立、验证环境独立，且并行收益为正。
- When：多 Agent 执行。
- Then：协调者从 Task 合同、`progress.md` 当前切片和精确证据引用生成独立上下文包并行实施；所有编排真源仍只由协调者更新。

## S08｜最小上下文与 Task 合同

- Given：Task Agent 开始实施。
- When：协调者交接上下文。
- Then：复杂、委派或跨会话 Task 在派发前有一份版本化执行合同；Agent 只收到该合同、当前状态切片和精确证据引用，不默认收到完整 Portfolio、专家会议和无关 Task 历史。

## S09｜UI 在计划前收敛

- Given：Request 涉及用户旅程、界面、视觉或动效。
- When：进入选定设计。
- Then：按需要先完成结构、状态、视觉和动效方向，再进入工程计划；非 UI 不加载体验 reference。

## S10｜失败时才加载 Debug

- Given：Build 出现测试失败、异常或非预期结果。
- When：进入失败回路。
- Then：先复现、定位根因、验证假设并最小修复；没有真实失败时不加载 Debug reference。

## S11｜代码完成后的 Simplify

- Given：存在非平凡代码 diff。
- When：进入质量验收。
- Then：先检查复用、删除、合并、效率和不必要抽象，修复确认问题后再 fresh 验证；不依赖外部 simplify skill。

## S12｜验收反馈的 Delta Intake

- Given：验收时用户连续提出缺陷、遗漏、小优化、新业务结果和无关需求。
- When：收到反馈。
- Then：先在 `progress.md` 捕获并冻结原验收基线，分类完成前不改代码；需要时先升级 Request baseline 或 Plan version，再失效受影响 Task 合同并重算 Ready，未受影响工作继续。

## S13｜无关新 Request

- Given：验收反馈中出现可独立交付、独立验收且与当前目标弱相关的新需求。
- When：用户要求推进该需求。
- Then：当前 Request 保持原交付基线；新需求从最新目标分支建立自己的 Request worktree，不继承未合入功能分支。

## S14｜交付前 Rebase 与 AI 冲突解决

- Given：目标分支在 Request 执行期间前进。
- When：进入集成交付并已有相应授权。
- Then：总协调者 fetch/rebase；AI根据双方业务意图、diff、约束和测试解决文本与语义冲突；source fingerprint 改变后旧证据失效并 fresh 重跑。

## S15｜AI Review 与受控进化

- Given：实现已完成，且可能产生可复用经验。
- When：质量验收与复盘。
- Then：不默认等待人类 Reviewer；独立 Agent 可 fresh review，无独立 Agent 时同一模型切换职责并如实标注。项目事实可安全回灌；workflow 只有两次独立复现或一次严重、系统且可复现问题才晋升。

## S16｜能力缺失时安全降级

- Given：当前环境没有 Git remote、独立 Agent、浏览器或持久 memory 中的一项或多项。
- When：workflow 推进当前 Cell。
- Then：只改变实现手段，不降低业务验收和证据要求；明确未覆盖项，不把计划、模拟或未验证结果写成完成。

## S17｜运行包 Clean-room 安装

- Given：用户已有能操作本地文件的 Agent，可能已安装旧 workflow，但没有 Python 或不知道 skills 目录。
- When：用户发送同一句 Agent 安装/更新提示词。
- Then：Agent 自动识别真实 skills 目录，整体备份旧版，以最新 GitHub main 的根协议、阶段 references 和 templates 完整镜像替换，校验入口与本地引用并报告版本/commit/位置；失败时恢复备份，不要求 Python。

## S18｜Plan 验收与 Request 交付分开

- Given：P01 已通过质量验收，P02 仍在执行，二者共享一个 Request worktree。
- When：协调者判断下一步。
- Then：P01 只标记为可汇合，不提前 rebase 或交付共享分支；所有纳入 Plan 通过后才创建 Request 级集成交付 Cell，并重验跨 Plan 与整体结果。

## S19｜只补最小项目地基

- Given：当前 Request 无法可靠找到项目入口、运行/验证/部署路径、关键模块边界或 UI 设计契约中的一项。
- When：计划编排检查可执行性。
- Then：先复用现有 owner，只把真实缺口变成前置 Task；最多按需补 AI 入口、运行与交付入口、项目全景导航、设计契约，不默认创建 ADR、术语表或治理文档，并用下一位 AI 的 clean-room 路径验收。

## S20｜唯一真源与文档预算

- Given：项目级 Request 需要跨会话推进，并包含事实调查、完整方案、多 Task 执行和验收反馈。
- When：workflow 建立持久化文档。
- Then：`request.md` 只拥有问题与验收基线，`findings.md` 只拥有证据与判断依据，`plan.md` 只拥有批准方案与顶层编排，`progress.md` 独占运行状态；Task 合同仅在复杂、委派或跨会话时按需生成，不默认建立 Evidence、Capsule、每 Plan 进度或每 Agent 文档。

## S21｜Task 合同晋升而不是复制

- Given：Plan 中一个 inline Task 变成需要委派、跨会话或高冲突风险的 Task。
- When：协调者生成 `tasks/<task-id>.md`。
- Then：Plan 删除结果、owner、写域、DONE、验证和权限细节，只保留 Task ID、所属 Plan、依赖、波次与合同链接；Task 文件成为完整定义唯一 owner。

## S22｜Progress 保持为当前快照

- Given：Request 已执行多轮 Task、验证和反馈路由。
- When：协调者更新 `progress.md`。
- Then：已完成 Task 折叠进 Plan 结果，过期 Evidence、已路由 Feedback、已关闭 Blocker 和已闭合事务从当前快照移除；历史交给 Git 或原始产物，不形成 Markdown 日记。
