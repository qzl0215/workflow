# Fresh Verification

## 原则

完成声明是证据结论，不是实现者感受。验证必须在声明前 fresh 运行，覆盖用户验收和实际变更面。

## 证据层级

- **Quick**：单文件或低风险 Task 的语法、定向测试和 diff 检查。
- **Standard**：功能测试、相邻回归、静态检查、构建或可视验证。
- **Full**：Plan/整体验收、clean-room、发布/安全/迁移或多环境矩阵。

## 门禁

1. 从当前 Task/Plan 验收和实际 diff 建验证清单，不照抄旧命令。
2. 实现类 Task 优先保留 RED → GREEN → REFACTOR 证据；不适用时说明原因。
3. 运行命令并检查 exit code、完整关键输出、产物 freshness 和覆盖范围；任一命令非零都必须解释并重新验证，不能只展示成功片段。
4. Reviewer 对关键命令 fresh 重跑；执行者自报、历史绿灯、部分日志和“应该通过”都不是证据。
5. 依次通过 Task、Plan、整体业务门；任一失败就回 Act/Debug 或上游缺口阶段。
6. 在 `progress.md` 记录时间、source fingerprint、命令、输出摘要、结论和未覆盖风险。

## 出口

只有所有纳入范围的验收都有 fresh evidence，且无未授权副作用，才能更新为 completed 或进入 Finish。
