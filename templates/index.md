# workflow 任务索引

<!-- 仅在多个任务需要统一定位时创建；只回答“任务目录在哪里”，不复制状态。 -->

| 任务目录 | 用户结果 | task_plan |
|---|---|---|
| `260719-example` | 一句话结果 | `./260719-example/task_plan.md` |

## 规则

- 项目级索引：`<project>/plans/index.md`。
- 用户级索引：用户指定或 Agent 提供的数据目录下 `workflow/index.md`。
- 一个业务目标一个目录，默认命名 `yymmdd-summary`；不要把旧任务重新包装成新状态真源。
- 不保存生命周期、阶段、活跃 Task、阻断或更新时间；进入目录后只读 `task_plan.md` 的 Current Snapshot。
- 单任务项目不创建本索引；历史任务不复制成归档文档。
