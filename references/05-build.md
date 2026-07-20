---
kind: stage
stage: 05
---

# 05｜执行建设

一次推进一个 Ready Task 或一组已证明互不冲突的 Ready Task；不在实现中偷做需求、方案或范围决定。

## 最小上下文

- 当前 Plan/Task ID、目标、输入、输出、验收、依赖和 source fingerprint；
- 允许修改、只读和禁止的文件/符号/共享资源；
- 被引用的项目事实、相关代码、测试入口、已排除假设和回退点；
- 当前 Request worktree 与已授权副作用。

Task owner 从版本化 Task 合同、`progress.md` 当前切片和精确 facts/code refs 获得一次性上下文包；不默认获得完整 Request、专家讨论、其他 Plan 历史或交付协议，缺什么只请求具体切片。

## 责任角色

**Task owner**只在 Task 合同和上下文包授权范围内建设并返回证据；**总协调者**唯一更新 `progress.md` 的 Plan/Task 状态、Evidence Index 和 Ready Queue。多个 Agent 共享 Request worktree，禁止自行创建 worktree、commit、rebase、push 或修改编排文档。

## 阶段能力

1. 开始前重验 active request baseline、plan version、Task contract version、Ready、依赖、写域占用、source fingerprint 和验证路径；失效就返回协调者升级合同或重编上下文包。
2. 先获得最小失败/缺口证据，再做满足验收的最小实现；适用时保留红→绿→整理证据。
3. 只改 Task 写域；发现上游缺口、范围变化、共享资源冲突或需要外部副作用时停止并返回，不顺手扩大范围。
4. 执行最小相关验证，再检查受影响的相邻路径；记录被验对象/产物、输入/依赖 fingerprint、环境、命令/场景、验收 baseline、观测时间/有效条件、exit code、关键输出和原始位置。只有确定性检查、实质输入已指纹化且有效条件仍成立时复用。
5. 出现 bug、失败、flaky、空结果或连续失败时加载 `references/05-debug.md`，基于可证伪假设换观察点，不机械重试。
6. Worker 结构化返回产物、实际 diff、证据、失败、排除假设、新事实、偏差、上下文 gap 和推荐路由；不能自行宣布 Plan 完成。
7. 用户已授权持续推进时，每个 Task 验明后自动重算 Ready Queue，直到纳入 Plan 完成、真实 blocker、需要新业务决策或用户暂停。

## 输出

- Task 产物、实际修改文件/符号和 diff；
- fresh 定向验证、失败与排除假设、残余风险；
- 新发现、范围偏差、上下文请求和下一 Task 建议；
- 由总协调者更新到 `progress.md` 的 Task 状态、Evidence Index 与进入 06 阶段的 Plan 候选。

## 退出与路由

Task 满足验收，且证据身份与有效条件仍覆盖当前判断后完成；Plan 的纳入 Task 全部具备可复核产物后路由到 **06 质量验收**。实现失败加载本阶段 Debug；目标/验收缺口返回 02，方案/体验缺口返回 03，编排或写域缺口返回 04。新反馈先进入 02 的 Delta Intake，不直接塞入 Build。
