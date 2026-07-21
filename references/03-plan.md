---
kind: stage
stage: 03
method_role: business-boundary
---

# 03｜计划编排

把选定路线编译为低冲突、可验收的 Plan/Task 工作图，并决定走对话内简单路径还是正式计划路径；本阶段不创建实现 branch/worktree，也不写产品代码。

## 最小上下文

- `findings.md` 或对话中的需求 baseline、已选路线、体验契约、非范围、不变量和整体验收；
- Requirement 到业务结果的映射；
- 只读获得的真实目录、文件/符号 owner、生成物、共享资源、运行与验证入口；
- 规划时的 source fingerprint、授权边界和待建立的隔离规格。

不读取无关历史、全部方案过程或其他 Request 的执行流水。

## 方法 owner

Workflow 只拥有正式计划边界、文件职责、批准门和开工路由。具体拆解与排程先使用一个用户指定或兼容的宿主原生 planning 能力，并要求其回写本协议真源；命中后不执行或叠加其他 planning 方法。下方只规定必须产出的业务结构与安全边界，不与原生 planning 方法竞争。

## 两条计划路径

- **简单路径**：目标单一、局部可逆、可在当前对话完成且不需要跨会话恢复、复杂委派或高冲突控制时，记录 `plan_mode=inline`、`approval_state=not-required`；用对话内短计划，不创建四份文件、不增加批准仪式。用户原始明确执行请求作为本地可逆实施授权。
- **正式路径**：用户要求正式计划，或工作需要跨会话恢复/长期持久化、包含多个业务 Plan、复杂 Task、委派、明显冲突或难逆风险时，记录 `plan_mode=formal` 和当前 `approval_state`，并形成唯一 `task_plan.md`。逻辑路线不因草案暂存在对话或安全计划区而改变；只有 `approval_state=approved` 才可开工。

## 必须产出的规划结构

1. 按可独立产生用户价值和独立验收的业务结果划分 Plan，不按技术层或用户句子机械分组。
2. `task_plan.md` 是 Task 拓扑唯一 owner：先用 Plan DAG 和业务摘要表示业务结果依赖与汇合，再为每个 Task 保留 ID、摘要、所属 Plan、依赖与波次。任何依赖或波次变化都先改这里。
3. 简单 Task 保持 inline，可在 `task_plan.md` 直接补足目标、写域、DONE 和验证。复杂、委派、跨会话或高冲突 Task 晋升后，`task_plan.md` 只保留 ID、业务摘要、所属 Plan、依赖、波次和合同链接；完整输入、允许/禁止写域、DONE、验证、停止条件与返回格式只写 `implementation-plan.md` 的同 ID 小节。后者展示的 Plan DAG，以及按 Plan 分组的 Task DAG、并行波次和跨 Plan 边，都只是从 `task_plan.md` 拓扑派生的只读视图，不得单独修改；所有图中 ID 必须能直接定位同 ID 摘要或合同。
4. 文件、符号、API/schema、lockfile、生成物、构建产物、端口、数据库或发布资源共享写入时，合并为一个写 owner 或串行；不得把可预防冲突推给后续 rebase。
5. 只有依赖已满足、写域独立、验证环境独立且并行收益为正的工作才并行。需要多 Plan 或多个 Agent 且宿主没有协作方法时，读取 `references/03-coordinate.md`。
6. 当前 Request 缺少会直接阻碍安全实施、验证、部署、恢复或交接的最小项目地基时，读取 `references/03-foundation.md`，把真实缺口变成前置 Task；不为未来可能性铺治理文档。
7. 正式计划写清开工门所需的 planning target ref、planning source fingerprint、建议隔离策略、共享现场、写域，以及 06 需要哪些集成/外部动作；当前授权事实只引用 `findings.md@baseline#authorization`，本阶段不重复定义授权，也不执行 Git 副作用。

## 正式计划批准

批准前，`plan_mode=formal` 且 `approval_state=draft`；计划内容只在对话展示，若需要持久化，只允许在一个既有安全计划区保存唯一草案，不写产品源文件。一次批准同时覆盖需求 baseline、已选方案、范围和编排；已在 02 选择的方向不得重复提问。

批准使当前版本从 `draft` 变为 `approved`，但不授权 commit、push、merge、deploy、delete、公开发布或其他外部副作用。用户要求修改或拒绝时分别标记 `modified / rejected` 并留在 03。只有用户结果、范围、验收、关键体验、难逆风险、成本/时间承诺或交付目标变化才需要新版本和重新批准；Task 拆合、依赖/波次、写域、owner、验证方式和不影响用户结果的实现变化，由总协调者同步定义后继续。

## 输出与路由

- 对话内短计划，或唯一的正式 `task_plan.md` 草案/批准版本；
- 按需 `implementation-plan.md` 的复杂 Task 合同、派生只读 Plan DAG 与按 Plan 分组的 Task DAG；
- 写冲突处理、串并行波次、验证矩阵、等待原因和隔离规格；
- `progress.md` 的当前工作切片（仅正式、跨会话或执行确需持久化时）。

用户只要计划时交付计划并结束。实施请求在简单路径编排完成，或正式计划批准后，进入 **◆开工门**；不能直接进入 04。目标/验收改变返回 01，方向/体验缺口返回 02，仓库事实不足继续只读调查。
