# workflow

帮助用户把目标想完整，持续完成已授权任务，用必要证据验证结果，并沿项目入口交付。

4.2 在直接执行与主动引导之上补全控制权交接：中间产物和进度更新仍是推进输入，授权内能继续就继续；真正需要用户时，明确当前处境、责任者、推荐与取舍、最小动作、完成信号和恢复路径。它不恢复固定阶段、逐步确认、强制演示或汇报格式。

## 保留的边界

- 保护用户已有工作，授权持续有效但不扩张。
- 验证实际产物与用户结果，明确证据覆盖范围；本地通过、已集成和真实可用分别成立。
- 项目负责远端、分支、环境、发布和回退方式；已有持续交付授权下连续完成。
- 失败保留现场，停止受影响的后续外部写入，继续授权内诊断。
- 长任务按恢复成本保存一个当前状态；协作时明确写入责任并核验整体结果。

[技能入口](SKILL.md) 是运行规则的唯一入口。[生成说明页](docs/workflow-visual-map.html) 直接展示入口与参考内容，不另写一套流程。

## 使用

直接说明要完成的任务、重要限制和验收要求。纯事实问答直接回答；需求讨论和只读审查可以主动补全遗漏、指出冲突，但不自动授权实施。明确且合理的小修改直接执行。方向难以判断时才做演示，多任务有依赖时才展开计划，宿主允许且有收益时才协作。

参考按缺口读取，不按阶段全量加载。项目初始化仅用于明确接入、迁移或实际结构性缺口；缺少 `.workflow/project.json` 不影响普通工作。上下文压缩后从当前事实恢复，不自动启动治理。

现有页面优先复用真实源码与已有预览；不为局部调整默认新增验收路由。汇报先说实际结果、必要缺口和下一行动；能自行推进就继续，需要用户时说明当前处境并给出有取舍的选择或带完成信号的最小动作，目标完成就结束。不能将演示可查看、包校验通过或部署成功说成用户结果已经成立。

## 项目记忆

项目保存具体业务规则、决定及实现事实；当前任务保存进度和恢复信息；workflow 提供查找、判断、更新的方法。按问题从项目已有入口定向查找，区分“应该怎样”和“实际怎样”。事实缺失补到原责任位置，旧决定被替代时说明关系；不复制第二份知识库，不把猜测写成政策。

重复错误先查目标、共享规则或既有自动检查，能由工具判断的优先修机制，不能只加提醒。没有可复用变化时不更新记忆，也不输出空复盘。具体约定见 [项目记忆与复盘](references/learn.md)。

## 从 3.x 迁移

4.0 的主版本变化是交互契约：明确请求可直接执行，取消默认的需求/方案双确认及强制演示、固定报告和空复盘。仍需要这些交互的用户可明确要求“先出方案，等我确认”。使用技能不自动授权发布、删除数据或修改技能本身。

运行时文件路径、manifest schema、`work_context.py` 的任务提取格式和项目兼容代际保持兼容。已有任务无需重建确认凭证或初始化记录；`dispatchable` 只检查任务状态，哈希只检测内容身份，二者都不证明用户授权。普通任务无需创建 `work.md`。

`safe_merge.py`、安装完整性、失败恢复和 3.9 的开发基准同步继续保留。项目明确登记 `workflow.developmentBaseline` 时，交付后安全快进同仓库开发基准；无配置跳过，脏现场与分叉保留，任务工作树不受影响。基准路径只存本机配置，不能指向生产目录。其他合并通道遵循项目自身契约。

## 维护与评测

[行为评测说明](evals/README.md) 区分结构检查、决策探针和实际任务验收。两种模型使用同一技能；没有反复出现的行为证据，不增加模型专用规则。实际样本、失败和限制见 [4.2 评测](evals/4.2.0-results.md)、[4.1 评测](evals/4.1.0-results.md) 与 [4.0 评测](evals/4.0.0-results.md)。

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

开发时运行与影响面相称的定向测试；正式候选由唯一发布入口在最终集成 SHA 上只跑一次完整门：

```bash
python3 -B -m unittest discover -s tests -p 'test_*.py'
python3 -B scripts/release_check.py
```

上面是发布入口内部持有的完整门，不在同一源码身份上手工重复。维护者实际执行：

```bash
python3 -B scripts/release_check.py --write-manifest
git add <本次文件>
git commit
python3 -B scripts/publish.py --version <版本> --yes
```

`publish.py` 复用 `safe_merge.py`、`release_check.py` 和 `install.py`，不建立第二套发布状态机。完整测试使用默认简洁输出，失败时展开具体错误。贡献方式见 [CONTRIBUTING.md](CONTRIBUTING.md)，安全边界见 [SECURITY.md](SECURITY.md)，来源与 clean-room 边界见 [NOTICE.md](NOTICE.md)。
