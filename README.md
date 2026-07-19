# workflow

**一个 skill，带你的 Agent 把复杂任务真正做完。**

从“到底要做什么”开始，依次完成项目就绪检查、方案与体验设计、计划、实现、调试、验证和交付。只安装 `workflow`，不要求你再准备其他 skills，也不会为了显得完整给项目堆一套文档。

[打开中文可视化介绍](docs/workflow-visual-map.html) · [查看完整工作协议](SKILL.md)

## 30 秒了解

适合这些任务：

- 功能较复杂，需要跨多个文件或多个步骤；
- 需求还比较散，需要先收敛方案和优先级；
- 涉及 UI、视觉或动效，需要先定设计再写工程计划；
- 要跨会话推进，或需要多人 / 多 Agent 协作；
- 最终要有可复查的测试、交付或发布结果。

不适合纯问答、改一个错别字、一次性安全小操作。这些事情直接做更快。

它的主线可以简单理解为：

> 接住任务 → 澄清目标 → 检查能否开工 → 定方案 → 定体验 → 写计划 → 实施与调试 → 验证 → 收尾

## 安装

需要 Python 3.9+，运行时不需要第三方 Python 包。

### 推荐：复制给你的 Agent

不需要先知道 skills 目录。把下面整段复制给当前 Agent，它会根据自己的运行环境完成安装和验证：

> 请安装 GitHub 项目 `https://github.com/qzl0215/workflow`。先把仓库克隆到临时目录，再根据你当前 Agent 的配置确认 skills 父目录，不要猜固定路径；运行 `python3 scripts/install.py install --target "<skills父目录>"`。如果已经安装，则使用 `update`。最后运行同一脚本的 `check`，只有验证通过后才能告诉我安装完成。不要安装任何其他 skill，也不要覆盖没有备份的旧版本。

### 自己在终端安装

如果电脑上只有一个已存在的常见 Agent skills 目录，安装器会自动识别：

```bash
git clone --depth 1 https://github.com/qzl0215/workflow.git
cd workflow
python3 scripts/install.py install
```

先只读查看识别结果：

```bash
python3 scripts/install.py detect
```

如果发现多个目录或没有识别到，请明确指定你的 Agent skills 父目录：

```bash
python3 scripts/install.py install --target "/path/to/agent/skills"
```

安装结果为 `<skills父目录>/workflow`。自动识别只使用已配置的 `AGENT_SKILLS_DIR` 或本机已经存在的常见目录；有歧义时会停止，不会替你猜。

安装后检查：

```bash
python3 scripts/install.py check --target "/path/to/agent/skills"
```

## 开始使用

安装后，直接把复杂目标交给 Agent：

> 用 workflow 帮我梳理这个项目的新功能。先把需求和方案讲清楚；如果涉及界面，先完成视觉与动效选型，再写计划、实现并验证。

workflow 会按任务复杂度自动选择必要阶段。成熟项目不会被强行“补基建”；只有入口、约束、关键命令或验证路径真的缺失并阻断后续工作时，才优先补现有真源，极端情况下最多新建一份项目入口文档。

## 它如何避免把事情做重

| 原则 | 实际行为 |
|---|---|
| 一个入口 | 包内只有一个根 `SKILL.md`，所有能力都已编排在同一个包内 |
| 按需读取 | 默认一次只读取当前阶段的一份 reference，不把整套流程塞进上下文 |
| 设计先于计划 | UI 任务先完成体验、视觉、动效和完整状态选型；非 UI 明确跳过 |
| 最小项目就绪 | 项目能开工就不改；缺什么只补真正阻断的那一处 |
| 证据先于完成 | 没有刚刚跑出的验证证据，就不声称任务已经完成 |
| 副作用先授权 | 未经明确授权，不 commit、push、merge、deploy、delete 或公开发布 |

缺少 subagent、浏览器、memory 或 Git 时，workflow 会改用当前环境能提供的安全路径，并明确哪些验证没有做；不会伪造 PR、发布或完成状态。

## 更新与卸载

更新前会自动保留旧版本备份：

```bash
python3 scripts/install.py update --target "/path/to/agent/skills"
```

卸载只会把目录改名为可恢复备份，不会永久删除：

```bash
python3 scripts/install.py uninstall --target "/path/to/agent/skills" --yes
```

## 项目维护

运行完整检查：

```bash
python3 -B -m unittest discover -s tests -p 'test_*.py' -v
python3 -B scripts/workflow_doctor.py
python3 -B scripts/release_check.py
```

贡献方式见 [CONTRIBUTING.md](CONTRIBUTING.md)，安全问题见 [SECURITY.md](SECURITY.md)，来源与 clean-room 边界见 [NOTICE.md](NOTICE.md)。本项目按 [MIT License](LICENSE) 发布。

---

## English

`workflow` is a dependency-closed AI skill for complex work: discovery, minimum readiness, solution and experience design, planning, implementation, debugging, fresh verification, and delivery. Install this repository only; no other custom skill or third-party Python package is required.

Ask your agent to clone `https://github.com/qzl0215/workflow`, identify its own skills parent directory, run `python3 scripts/install.py install --target "<skills-directory>"`, and verify with the `check` action. The installer can also safely auto-detect one existing common skills directory with `python3 scripts/install.py install`; ambiguity fails closed.

See the [visual introduction](docs/workflow-visual-map.html), or run `python3 -B scripts/release_check.py` to verify a checkout.
