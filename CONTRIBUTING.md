# Contributing

Contributions are welcome when they improve an observable workflow result without adding a second truth source or a new external skill dependency.

## Before changing the package

1. Open or link an issue that states the user-visible problem, evidence, and smallest useful outcome.
2. Identify the existing owner. Prefer improving one reference/template/script over adding a file.
3. Add a failing test or explain why RED/GREEN does not apply.
4. Keep `SKILL.md` as a router, references under 250 lines, and the seven-action model limited to one evidence-based 开工检查.

## Required checks

```bash
python3 -B -m unittest discover -s tests -p 'test_*.py' -v
python3 -B scripts/workflow_doctor.py
python3 -B scripts/generate_visual_map.py --check
python3 -B scripts/release_check.py
```

If the root route or state table changes, regenerate the visual map. If templates change, update every reader/writer test. Never commit credentials, private paths, production reports, generated caches, or organization-specific release implementations.

## Pull requests

Describe the user outcome, removed or merged complexity, tests and actual results, compatibility impact, and residual risks. Keep unrelated cleanup separate.

## 持续发布授权

项目 owner `qzl0215` 于 2026-07-24 为公开仓库 `qzl0215/workflow` 的维护授予持续授权：当变更范围仅限本仓库，并且上面的 Required checks 已在最终候选上 fresh 通过时，Agent 可以连续完成 commit、push、合并到主版本和发布，不再重复请求授权。该授权同时覆盖为兼容最新主版本所必需的语义合并与集成后重验。

持续授权不降低安全和范围边界：

- 只纳入 workflow 当前目标所需文件，不提交凭据、生产数据、私有环境信息或无关改动；
- P0 安全、供应链或发布覆盖风险仍然硬阻断；新的业务目标冲突、发布目标变化或权限缺失仍需用户决定；
- 禁止 force、绕过分支保护、无证据覆盖、删除临时版本或省略发布后核验；
- 任一 Required check 失败时停止发布，修复并 fresh 重验后才可继续。

超出这些边界时，单纯测试绿色不构成授权。
