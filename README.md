# workflow

把一句还没想完整的需求，推进成已经做完、验明白，并让下一次更省事的结果。

你只需要说目标。workflow 会自己查项目、准备高价值问题、组织必要的专家视角、选择方案、安排多个结果计划、执行任务和 AI 协作者，持续实施、验收、处理反馈，并把值得复用的经验写回正确的位置。

它是一个完整的单 Skill：不默认你还安装了其他 skills，也不要求你先学会工程术语。

[下载或本地打开可视化 HTML](docs/index.html)

## 你会感受到什么

- **先弄清楚**：能从项目查到的事实不问你；真正需要你决定的问题集中问。
- **先想透再开工**：复杂问题先看完整森林；界面、视觉和动效在工程计划前确定。
- **一路做到并验真**：AI 自动安排先后与并行、修复失败、做代码瘦身，并用刚刚跑出的证据验收。
- **新反馈不会把项目搅乱**：验收中的缺陷、优化、新结果计划和新需求会被分别处理。

## 八个清楚的阶段

| 阶段 | 这一阶段只解决什么 |
|---|---|
| 1. 立项隔离 | 判断是不是一个新需求；Git 项目从最新代码建立独立工作区（worktree） |
| 2. 看清需求 | 逐项接住需求、查事实、集中关键追问（Grill），明确边界和验收 |
| 3. 选定设计 | 专家独立发散与交叉质询，选方案；UI 先定体验、视觉和动效 |
| 4. 计划编排 | 排清前后依赖和唯一负责人；确有阻碍时才补最小项目入口、运行/部署说明、全景导航或 DESIGN.md |
| 5. 执行建设 | 每个角色只拿当前工作单元需要的背景，按任务实施和纠错 |
| 6. 质量验收 | 先复用已有实现和做代码瘦身，再由 AI 独立重审并重新跑验收 |
| 7. 集成交付 | 按授权同步最新代码、理解并解决冲突、重验后交付 |
| 8. 复盘升级 | 找真实偏差，更新项目；有复用证据时才升级 workflow |

阶段是 AI 的责任边界，不是八次会议。没有需要你决定的事情时，workflow 会连续推进。

## 它怎样减少上下文噪音

每次实际工作都被编译成一个最小工作单元（内部称 `Workflow Cell`）：

```text
正在处理哪个对象
→ 处于什么阶段
→ 只加载哪些相关事实
→ 由什么责任角色处理
→ 使用什么阶段能力
→ 允许做什么
→ 必须产出什么证据
→ 下一步去哪里
```

一次独立交付（Request）可以包含多个结果计划（Plan），每个 Plan 可以处于不同阶段；每个执行任务（Task）只有一个写入负责人。多个 AI 协作者默认共享该 Request 的独立工作区，不各自创建分支，也不会同时修改冲突的文件域。

复杂、需要委派或跨会话的 Task 会在开工前得到一份独立执行合同。合同已经写清输入、输出、允许修改范围、完成标准和验证方法，所以执行者不需要重读完整需求和专家会议。

## 项目怎样记住上下文

项目级工作只保留四类真源，并按需增加 Task 合同：

| 文件 | 只回答一个问题 |
|---|---|
| `request.md` | 为什么做、为谁做、必须做到什么 |
| `findings.md` | 我们查到了什么，为什么得出这个判断；确有跨阶段复用价值时才建 |
| `plan.md` | 最终确认做成什么，以及多个结果和任务怎样编排 |
| `progress.md` | 现在做到哪里、哪里受阻、下一步做什么；所有运行状态只看这里 |
| `tasks/p01-t01.md` | 当前复杂 Task 的执行合同；按需生成，不按 Agent 数量复制 |

执行上下文包由这些真源即时生成，不再默认建立证据流水文档、持久化上下文包、每 Plan 进度或每角色文档。完整日志和截图留在原产物位置，`progress.md` 只保存当前快照和证据索引。

## 连续需求和验收反馈

一次说出很多要求时，workflow 会先逐项编号，查清事实和关系，再组合成可独立验收的结果计划，而不是把每句话直接变成待办。

验收中又提出一串反馈时，它会先冻结原验收基线并分类：

- 原验收没做到：重开原执行任务。
- 原目标有所遗漏：回到受影响的设计或计划。
- 同目标的小优化：加入当前结果计划或延后，不默认阻塞交付。
- 新的独立业务结果：加入当前 Request 的新 Plan。
- 不相关的新目标：建立新 Request 和新独立工作区，不污染当前交付。

## 安装与自动更新

workflow 本身和 Agent 原生安装都不需要 Python。Python 3.9+ 是可选的终端安全工具。

### 推荐：发给 Agent 的一句话

第一次发送会安装，以后再次发送同一句会自动更新：

> 请从 `https://github.com/qzl0215/workflow` 安装或更新 workflow：自动找到你当前实际使用的 skills 目录，有旧版先整体备份，再以最新 main 中的 `SKILL.md`、`references/` 和 `templates/` 完整镜像替换，校验入口与本地引用后报告版本、来源 commit 和安装位置；任何一步失败都恢复备份，不要猜固定目录。

### 可选：Python 安全安装器

需要人工终端、CI 或确定性回滚时，可以使用仓库自带的标准库脚本：

```bash
git clone --depth 1 https://github.com/qzl0215/workflow.git
cd workflow
python3 scripts/install.py install
```

有多个 skills 目录时明确指定：

```bash
python3 scripts/install.py install --target "/path/to/agent/skills"
python3 scripts/install.py check --target "/path/to/agent/skills"
```

更新和可恢复卸载：

```bash
python3 scripts/install.py update --target "/path/to/agent/skills"
python3 scripts/install.py uninstall --target "/path/to/agent/skills" --yes
```

无论 Agent 原生安装还是可选脚本，都只把 `SKILL.md`、阶段 references 和 templates 放入 Agent 的 `workflow` 目录；README、HTML、测试和仓库维护文件不会进入运行上下文。

## 开始使用

安装后直接描述目标：

> 用 workflow 推进这个需求。先查项目和现有事实；需要时一次集中关键追问，并让相关专家独立发散、交叉质询。界面工作先定体验和视觉，再计划。没有需要我决定的事情就持续推进，直到刚刚重跑的验收全部通过。

## 安全边界

- 能自行发现的事实不会重新问用户。
- Grill 单次最多 15 个问题，通常远少于这个数字。
- 未经明确授权，不 commit、push、merge、deploy、delete 或公开发布。
- 没有 fresh evidence，不声称完成。
- 没有复用证据，不把一次经验永久写进 workflow。
- 无 Git、无 subagent、无浏览器时会安全降级，不伪造能力和结果。
- 项目地基只补当前交付真正需要的部分，不默认铺治理文档。

## 维护检查

```bash
python3 -B scripts/check.py
python3 -B -m unittest discover -s tests -p 'test_*.py' -v
```

MIT licensed. <sub>Maintained by zhonglin.</sub>

## English

`workflow` turns an incomplete request into a verified delivery through staged, progressively loaded context. One independent request gets one worktree; sub-agents share it by default. Four compact sources of truth hold the problem, findings, approved plan and live progress; non-trivial Task contracts are created only when needed.
