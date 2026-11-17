# 项目记忆

用户要求复盘、记住或接入项目，或同一问题再次出现时使用。没有新内容就结束，不做空复盘。

- 只存会改变以后行动的稳定事实、决定，或难以便宜重查的证据。
- 写到原有的责任位置：业务规则和决定归项目的产品或决策资料，实际行为和发布入口归代码、配置和操作说明，进度归当前任务。内容有但难找就补入口，不复制正文。本技能不存具体项目的知识。
- 已确认的决定、实际观察、未验证的假设分开写；不把模型的建议写成用户的政策，不把计划写成已上线。
- 旧决定被替代时，注明被什么替代和原因。
- 同一问题再次出现：先查是不是目标、规则或共享实现错了；工具能稳定判断的，修自动检查，不只加提醒。
- 改业务政策或改本技能要有对应授权。

## 接入项目

仅在用户要求接入、迁移或复查时做，普通任务不因缺少记录而触发。目标是让新来的模型找得到业务约定、关键决定、实现、验证、交付和恢复入口；已有的够用就不动，不给项目套统一目录。

```bash
python3 -B <workflow根>/scripts/project_init.py check --project <项目根>
python3 -B <workflow根>/scripts/project_init.py inventory --project <项目根>
python3 -B <workflow根>/scripts/project_init.py record --project <项目根> --entrypoint <项目内入口> --evidence <项目内证据>
```

`check` 返回 `current` 只表示记录有效，不证明项目质量；`needs-initialization` 只表示还没有记录，不授权改造。`inventory` 列出入口清单供定向阅读。`record` 在验收后保存；`.workflow/project.json` 只存代际和入口。
