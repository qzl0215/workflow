---
kind: stage
stage: 04
---

# 04｜计划编排

把选定方案编译为多 Plan、多 Task、可串并行执行且尽量无写冲突的工作图；这是 Build 前最后一道深度门。

## 最小上下文

- 已选方案、体验契约、非范围、不变量、回滚点和整体验收；
- Requirement 到业务结果的映射与 Plan 依赖；
- 真实目录、文件/符号 owner、生成物、共享资源、运行和验证入口；
- Request worktree、active request baseline、source fingerprint 和授权边界；只有触发多 Agent 编排时才补 Agent 槽位。

不读取专家完整会议、无关项目历史和其他 Request 的执行日志。

## 责任角色

**Plan owner**对一个可独立验收的业务结果、Task DAG 和集成验收负责；**总协调者**维护一个 Request 的完整 `plan.md` 与唯一运行状态 `progress.md`。每个 Task 只有一个写 owner。

## 阶段能力

1. Plan 按可独立产生用户价值和独立验收的业务结果分组，不按技术层或用户句子机械分组。
2. 在一份 `plan.md` 中建立 Plan Portfolio/DAG 和各 Plan 的 Task DAG，明确分叉、汇合、关键路径、blocker 和回滚点；不为每个 Plan 默认建文档。
3. 计划期先为每个 Task 写足以判断目标、依赖、写域、DONE 和验证的 stub；复杂、委派、跨会话或存在写冲突风险的 Task 到达 Ready 候选时，才从 `templates/task.md` 冻结完整合同。一个 Task 不按 Agent 数量复制文件。
4. 建冲突矩阵：文件、符号、API/schema、lockfile、生成物、build output、端口、数据库和 release candidate 任一共享写入，都合并为同一 owner 或串行。
5. 只有依赖已满足、写域隔离、验证独立且并行收益高于协调成本的 Task 才并行；需要多 Agent 时加载 `references/04-coordinate.md`。
6. 若缺少会直接阻碍当前 Request 安全实施、验证、部署或交接的项目地基，加载 `references/04-foundation.md`，把最小补齐项作为前置 Task；不为未来可能性铺文档体系。
7. 用户用业务语言确认完整方案和 Plan 编排后，才能进入 Build；不逐 Task 索取无意义批准。派工时从 Task 合同、`progress.md` 当前切片和精确事实引用生成一次性上下文包。
8. Git 项目才把最终 rebase、post-rebase 验证和交付路径纳入计划；本阶段不执行 Git 副作用。

## 输出

- 一份用户确认的完整 `plan.md`：方案、Plan Portfolio/DAG、Task DAG、冲突矩阵和串并行顺序；
- 每个 Ready 候选 Task 的 owner、写域、验证、权限，以及按需冻结的 Task 合同；
- `progress.md` 中的多对象当前阶段、派生 Ready Queue 和 blocker；
- 集成/交付验证矩阵、blocker 和进入 05 阶段的执行入口。

## 退出与路由

用户已确认 `plan.md`，每个 Ready Task 无需重新设计即可独立执行，写冲突已消除，Plan 级验收和集成路径清楚后路由到 **05 执行建设**。目标/验收改变返回 02；方案/体验缺口返回 03；仓库事实不足只读补证据。无并行收益时按 Ready Queue solo，不降低验收。
