# workflow

通过与用户的高效沟通和良好的执行习惯，高质量、高性能地达成真实目标，并持续自我进化。技能分三块：沟通（理解真用户真背景、找到高价值目标、摸清取舍，用好选的选择题收窄到方案）、执行（小事直接做，拿到真证据再说完成，按授权交付）、复盘（记住用户的纠正和取舍，同类失误再次出现时提出技能改进）。

AI 从精简的 [技能入口](SKILL.md) 判断当前请求、按需读取参考，以运行效率为先；用户从 [人类阅读版](docs/workflow-visual-map.html) 的工作闭环图、任务分支和能力索引理解流程，以易懂为先，点击查看完整技能正文。两种阅读方式共用一份 Markdown 真源，HTML 自动生成。[变更记录](CHANGELOG.md) 说明各版本变化。

## 使用

直接说明要完成的任务、重要限制和验收要求。新功能、改版、上线和方向不清的任务会先给出“我的理解”和全景，用选择题和你一起收窄目标、再选方案，每个选项写清用什么代价换什么收益；想跳过时说“直接做”。规则以[技能入口](SKILL.md)为准，这里不另写一套。说 `grill-me`、要求先问清楚或挑战方案时，先做深度质询再出方案。纯事实问答直接回答；需求讨论和只读审查可以主动补全遗漏、指出冲突，但不自动授权实施。明确且合理的小修改直接执行。方案的视觉或交互差异影响选择时，用同一份材料做演示，多任务有依赖时才展开计划，宿主允许且有收益时才协作。

参考按缺口读取，不按阶段全量加载。上下文压缩后从当前事实恢复，不自动启动治理。

“画一下退款流程”可以直接收到聊天里的流程图。“用这份数据做个离线趋势 HTML”会得到可打开的文件。“这两个方案怎么选”会收到推荐和代价；差别在操作上时可用同一份内容试两种做法。[汇报](references/report.md)负责组织决定与依据，[页面设计](references/visual-demo.md)负责构图、组件、配色、文案、交互和数据图怎么画。可打开[潮位观测示例](templates/explorer.html)切换站点，看主图和读数如何联动。

现有页面优先复用真实源码与已有预览；不为局部调整默认新增验收路由。汇报先说实际结果、必要缺口和下一行动；能自行推进就继续。主要方法有实质取舍时比较并推荐，授权内直接实施验证；确需用户介入时，带上具体卡点、关键证据、推荐理由和最小决定或操作，目标完成就结束。不能将演示可查看、包校验通过或部署成功说成用户结果已经成立。

## 复盘与项目记忆

项目保存具体业务规则、决定及实现事实；当前任务保存进度和恢复信息；workflow 提供查找、判断、更新的方法。按问题从项目已有入口定向查找，区分“应该怎样”和“实际怎样”。事实缺失补到原责任位置，旧决定被替代时说明关系；不复制第二份知识库，不把猜测写成政策。

重复错误先查目标、共享规则或既有自动检查，能由工具判断的优先修机制，不能只加提醒。没有可复用变化时不更新记忆，也不输出空复盘。同一类失误第二次出现、原因在技能规则时，AI 会写一条技能改进提案，你批准才改。具体约定见 [复盘](references/learn.md)。

## 6.0.1 去掉的文件

6.0.1 起随包不再带 `scripts/work_context.py`、`scripts/project_init.py`、`templates/work.md` 和 `references/linear-tracking.md`。近 30 天本机和服务器的真实会话里没有项目在用它们。仍需要的项目可从 6.0.0 的 Release 取回这几个文件自行保留；已有的 `work.md` 和 `.workflow/project.json` 不受影响，只是不再有随包脚本读它们。跨会话恢复用项目已有记录。其余运行时文件路径和 manifest schema 不变。

## 从 5.x 迁移

6.0 的主版本变化是交互契约：大事不再单独确认一轮需求契约。AI 先补全画面、请你选目标，目标收窄的结果就是契约，随后直接比方案；目标选项会带粗略代价。入口按沟通、执行、复盘三块重排，“三问”换成“真用户真背景、高价值目标、取舍”。运行时文件路径、manifest schema 和项目兼容代际不变。

## 从 4.x 迁移

5.0 的主版本变化是交互契约：新功能、改版、部署到生产和方向不清的任务不再收到请求就开工，默认先确认需求契约、再选方案。说“直接做”可跳过。已授权完成的工作、定时和无人值守任务不受影响。运行时文件路径、manifest schema 和项目兼容代际不变。

## 从 3.x 迁移

4.0 的主版本变化是交互契约：明确请求可直接执行，取消默认的需求/方案双确认及强制演示、固定报告和空复盘。仍需要这些交互的用户可明确要求“先出方案，等我确认”。使用技能不自动授权发布、删除数据或修改技能本身。

运行时文件路径、manifest schema、`work_context.py` 的任务提取格式和项目兼容代际保持兼容。已有任务无需重建确认凭证或初始化记录；`dispatchable` 只检查任务状态，哈希只检测内容身份，二者都不证明用户授权。普通任务无需创建 `work.md`。

`safe_merge.py`、安装完整性、失败恢复和 3.9 的开发基准同步继续保留。项目明确登记 `workflow.developmentBaseline` 时，交付后安全快进同仓库开发基准；无配置跳过，脏现场与分叉保留，任务工作树不受影响。基准路径只存本机配置，不能指向生产目录。其他合并通道遵循项目自身契约。

## 维护与评测

日常使用只需交代任务。实际加载观测、路由负例与版本审阅用于维护者验证技能，普通任务不需要维护这些记录。

下载 [最新正式 Release](https://github.com/qzl0215/workflow/releases/latest) 的 `workflow-review.html`，离线查看图文总览、按情况找参考，或搜索全文。版本说明直接取自 CHANGELOG；高亮差异默认显示技能规则与参考，可切换到维护源码。

手动比较两个已提交版本（输出到仓库外）：

```bash
python3 -B dev/generate_visual_map.py --base 5.2.0 --target 5.2.1 --review-output /tmp/workflow-review.html
```

省略 `--base` 和 `--target` 时，比较当前提交与 CHANGELOG 里上一个已发布版本，用于发布前评审。目标版本须包含 5.2 起的可视化资源；历史版本可作为基线。正式发布自动生成审阅页。文本差异不能代替行为评测；验证方法见 [评测说明](evals/README.md)，实际加载观测的样本与限制见 [5.2 评测](evals/5.2.0-results.md)。日常会话里的真实加载用 `dev/observe.py` 观察，口径与限制见评测说明的 5.4 记录。

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

## 升级到 4.x 的迁移边界

3.x 起的安装包只包含 manifest 声明的精简运行时，不再携带测试、维护脚本和对外文档。2.26.0 是专门为这种格式准备的兼容桥。

| 当前活动版本 | 更新到 4.x | 原因与动作 |
|---|---|---|
| `3.x` | 可直接 `sync` | manifest schema 与运行时路径兼容；默认交互策略改变，升级后按 4.0 规则工作 |
| `2.26.x` | 可直接 `sync` | 2.26 已理解 `workflow-package.json`、逐文件散列和精简运行时，会在同文件系统暂存验证后事务替换 |
| `2.25.x` 或更早 | 旧更新器应失败关闭 | 旧版不应猜测 3.x 文件清单；它会保留原安装。请从已验证的 4.x tag 或正式 Release 重新取得源码，使用其中的新安装器执行 `update`，再运行 `check` |
| 无安装 | 从 4.x 源码安装 | 新安装器只复制 manifest 中的运行时文件，并验证唯一性与完整性 |

错过 2.26 时，不要手工删除旧文件再把 ZIP 覆盖进去。建议使用临时克隆：

```bash
git clone --depth 1 --branch 4.2.0 https://github.com/qzl0215/workflow.git workflow-4
cd workflow-4
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

在 Codex 本机可以使用稳定名称，不需要写入个人绝对路径：

```bash
python3 scripts/install.py sync --target codex
```

同步更新的是 Codex 在磁盘上的活动 workflow。新任务会使用新版本；已经打开的任务可能继续使用启动时载入的上下文，需要立即核对新规则时，新建任务即可，宿主仍未重新发现时再重启 Codex。

永久卸载会删除唯一活动副本，需要显式确认：

```bash
python3 scripts/install.py uninstall --target "/path/to/agent/skills" --yes
```

## 安全与降级

- 未经明确授权，不扩大外部副作用；范围已清楚的持续交付授权不重复询问。
- 任一验证、集成、部署或发布后检查失败时，停止后续外部写入，保留可恢复现场并报告真实状态。
- 宿主实际拒绝外部写入时不绕过；只有拒绝信息明确允许用户授权解锁，才展示不变的载荷、目标和后续动作并请求精确授权。宿主策略不可解锁时如实阻断。
- 没有子 Agent 就由同一模型顺序承担职责；没有持久存储就留在上下文；没有 Git 就交付文件和证据。工具降级不能把未覆盖写成通过。
- 纯事实问答和一次性查询不启动执行流程；讨论、解释与只读审查不扩大为未授权实施。

## 项目维护

实施、验证与正式发布统一遵循 [CONTRIBUTING.md](CONTRIBUTING.md)。每次迭代从已有内容的删除、合并和修复开始，说明收益是否值得新增的长期维护负担。安全边界见 [SECURITY.md](SECURITY.md)，来源与 clean-room 边界见 [NOTICE.md](NOTICE.md)。
