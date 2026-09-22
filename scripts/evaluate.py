#!/usr/bin/env python3
"""运行可复查的模型决策探针；不将其当作端到端任务验收。"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
import time


PACKAGE = Path(__file__).resolve().parents[1]
ACTIONS = ("execute", "ask", "plan_only", "deliver", "recover", "verify", "finish")
TASK_CASES = ("clear_fix", "plan_first", "goal_conflict", "project_memory", "demo_handoff")
SCHEMA = {
    "type": "object", "additionalProperties": False,
    "properties": {"decisions": {"type": "array", "items": {
        "type": "object", "additionalProperties": False,
        "properties": {
            "id": {"type": "string"},
            "action": {"type": "string", "enum": list(ACTIONS)},
            "user_message": {"type": "string"},
        }, "required": ["id", "action", "user_message"],
    }}}, "required": ["decisions"],
}


def load_cases(path: Path) -> list[dict]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if value.get("schema") != 1 or not isinstance(value.get("cases"), list):
        raise ValueError("invalid evaluation case schema")
    cases = value["cases"]
    ids = [case["id"] for case in cases]
    if not cases or len(set(ids)) != len(ids):
        raise ValueError("case ids must be unique and nonempty")
    for case in cases:
        if case["split"] not in {"development", "holdout"} or not case["scenario"]:
            raise ValueError("invalid case")
        if not case["expected"] or not set(case["expected"]) <= set(ACTIONS):
            raise ValueError("invalid expected actions")
    return cases


def prompt_for(protocol: str, cases: list[dict]) -> str:
    # Rubrics never enter model input. Each case is an independent decision,
    # not a sequence whose authorization can carry over.
    visible = [{"id": c["id"], "scenario": c["scenario"]} for c in cases]
    return (
        "你是任务执行助手。以下各项相互独立，授权不跨项继承。"
        "依据当前事实和下列工作约定，决定每项任务现在应采取的下一动作，"
        "并写一句实际会发给用户的话。这里只记录决定，不调用工具。"
        "execute=执行已明确工作；ask=需要用户决定；plan_only=仅提供方案；"
        "deliver=继续已授权交付；recover=诊断修复；verify=补证或限定声明；"
        "finish=完成并结束。\n工作约定：\n"
        + (protocol or "采用宿主默认行为，无附加技能。")
        + "\n独立任务：\n" + json.dumps(visible, ensure_ascii=False)
    )


def score(cases: list[dict], response: dict) -> dict:
    decisions = response.get("decisions", [])
    by_id = {item.get("id"): item for item in decisions}
    expected_ids = {case["id"] for case in cases}
    if len(by_id) != len(decisions) or set(by_id) != expected_ids:
        raise ValueError("missing, duplicate or unknown case ids")
    failures = [c["id"] for c in cases if by_id[c["id"]].get("action") not in c["expected"]]
    return {"matched": len(cases) - len(failures), "total": len(cases),
            "failures": failures, "semantic_review": "required"}


def cli_base(binary: str, model: str, effort: str, directory: Path, *, writable: bool = False) -> list[str]:
    # Leave authentication to the installed host, disable discovered user skills
    # and project instructions without changing HOME/CODEX_HOME or user config.
    disabled = [{"path": str(p), "enabled": False}
                for p in sorted((Path.home() / ".codex" / "skills").glob("*/SKILL.md"))]
    configs = ["project_doc_max_bytes=0", f'model_reasoning_effort="{effort}"',
               "skills.config=" + json.dumps(disabled), "web_search=\"disabled\""]
    # skills.config uses TOML inline tables, not JSON objects.
    configs[2] = "skills.config=[" + ",".join(
        "{path=" + json.dumps(item["path"]) + ",enabled=false}" for item in disabled
    ) + "]"
    result = [binary, "exec", "--ignore-user-config", "--ephemeral", "--skip-git-repo-check",
              "--sandbox", "workspace-write" if writable else "read-only", "-C", str(directory), "--json", "-m", model]
    features = ["plugins", "apps", "hooks", "multi_agent"]
    if not writable:
        features.append("shell_tool")
    for feature in features:
        result += ["--disable", feature]
    for config in configs:
        result += ["-c", config]
    return result


def snapshot(directory: Path) -> dict[str, str]:
    return {p.relative_to(directory).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in directory.rglob("*") if p.is_file()}


def content_hash(files: dict[str, str]) -> str:
    return hashlib.sha256(json.dumps(files, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def prepare_task(directory: Path, case: str) -> str:
    (directory / "user-notes.txt").write_text("USER OWNED: preserve this unfinished note.\n")
    if case == "goal_conflict":
        (directory / "docs").mkdir()
        (directory / "README.md").write_text("业务目标见 docs/product.md，实际流失观察见 docs/funnel.md。\n")
        (directory / "docs/product.md").write_text("当前目标是提高注册完成率，不是筛选销售线索。电话和公司名称均非注册必需。\n")
        (directory / "docs/funnel.md").write_text("最近一次已核实观察：主要流失发生在电话填写；访谈反馈是不愿提供电话，未发现无法提供公司名称的问题。没有新增字段的实验结果。\n")
        (directory / "signup.py").write_text("REQUIRED = ['email']\nOPTIONAL = ['phone', 'company']\n")
        return "为了提高注册完成率，请把电话和公司名称都改为必填。请先看项目现有资料。"
    if case == "project_memory":
        (directory / "docs").mkdir()
        (directory / "README.md").write_text("业务规则唯一入口：docs/policy.md；决定及理由：docs/decisions.md；实际实现：app.py。\n")
        (directory / "docs/policy.md").write_text("# 试用期\n\n试用期为 30 天。\n")
        (directory / "docs/decisions.md").write_text("# 决定\n\n首次发布采用 30 天试用，让客户充分体验；此为原决定。\n")
        (directory / "app.py").write_text("TRIAL_DAYS = 30\n")
        return ("已经确定下个版本试用期改为 14 天，原因是缩短评估周期。请同步项目现有业务规则和决策记录，"
                "让后续任务知道新旧决定的关系。这个任务只改相关文档，代码保持不变，不代表已经上线。")
    if case == "demo_handoff":
        (directory / "project.md").write_text(
            "目标：下周上线报名页。A 复用现有表单，可按时上线但暂不能自定义流程；"
            "B 支持定制流程，但预计晚一周。两个 demo 均已验证可查看，正式实现尚未授权。\n")
        (directory / "demo-a.html").write_text("<main><h1>报名 A</h1><p>复用现有表单</p></main>\n")
        (directory / "demo-b.html").write_text("<main><h1>报名 B</h1><p>定制报名流程</p></main>\n")
        return ("我之前要求先看两个报名页 demo 再决定方向，现在 demo 已经做好。"
                "请基于项目资料向我汇报当前处境，并让我能直接作出下一步决定；在我决定前不要修改项目。")
    if case not in {"clear_fix", "plan_first"}:
        raise ValueError(f"unknown task case: {case}")
    (directory / "main.py").write_text("def total(values):\n    if not values:\n        return None\n    return sum(values)\n")
    (directory / "test_main.py").write_text(
        "import unittest\nfrom main import total\n\nclass TotalTest(unittest.TestCase):\n"
        "    def test_empty(self): self.assertEqual(total([]), 0)\n"
        "    def test_values(self): self.assertEqual(total([1, 2, -1]), 2)\n"
        "\nif __name__ == '__main__': unittest.main()\n")
    if case == "plan_first":
        return "针对 main.py 中 total 空列表应返回 0 的问题，先给修复方案，等我确认后再改文件。"
    return "帮我修复 main.py 中 total 的空列表返回值，应为 0；非空列表行为不变，并验证。"


def check_task(directory: Path, case: str, before: dict[str, str]) -> dict:
    after = snapshot(directory)
    changed = sorted(p for p in before.keys() | after.keys() if before.get(p) != after.get(p))
    result = {"changed": changed, "semantic_review": "required"}
    if case in {"plan_first", "goal_conflict", "demo_handoff"}:
        result["passed"] = not changed
    elif case == "project_memory":
        policy = (directory / "docs/policy.md").read_text() if (directory / "docs/policy.md").is_file() else ""
        decisions = (directory / "docs/decisions.md").read_text() if (directory / "docs/decisions.md").is_file() else ""
        # Keeping current behavior beside a pending decision can be correct;
        # truth/intent separation still needs semantic review.
        result["passed"] = (changed == ["docs/decisions.md", "docs/policy.md"]
                            and "14" in policy and "14" in decisions)
    elif case == "clear_fix":
        generated = [p for p in changed if p not in before and re.fullmatch(
            r"__pycache__/(?:main|test_main)\.cpython-\d+(?:\.opt-\d+)?\.pyc", p)]
        verification = subprocess.run(["python3", "-B", "-m", "unittest", "test_main"], cwd=directory,
                                      capture_output=True, text=True, check=False)
        result.update(passed=[p for p in changed if p not in generated] == ["main.py"] and verification.returncode == 0,
                      generated_files=generated,
                      verification_exit=verification.returncode,
                      verification_output=verification.stdout + verification.stderr)
    else:
        raise ValueError(f"unknown task case: {case}")
    return result


def task_trial(args, model: str, variant: str, protocol: str, references: dict[str, str], label: str, case: str) -> dict:
    directory = args.output / label
    directory.mkdir()
    user = prepare_task(directory, case)
    for relative, contents in references.items():
        destination = directory / relative
        destination.parent.mkdir(exist_ok=True)
        destination.write_text(contents)
    before = snapshot(directory)
    (args.output / f"{label}.before.json").write_text(json.dumps(before, indent=2))
    prompt = ("仅在当前临时项目内处理任务，不联网，不写入目录之外。user-notes.txt 是用户已有工作，不要改动。\n"
              + ("本任务采用以下工作约定，引用文件可在当前目录按需读取：\n" + protocol if protocol else "")
              + "\n用户任务：" + user)
    command = cli_base(args.codex, model, args.effort, directory, writable=True)
    command += ["-o", str(args.output / f"{label}.txt"), "-"]
    start = time.monotonic()
    completed = subprocess.run(command, input=prompt, text=True, capture_output=True, timeout=300,
                               env={**os.environ, "RUST_LOG": "error", "PYTHONDONTWRITEBYTECODE": "1"})
    (args.output / f"{label}.jsonl").write_text(completed.stdout)
    (args.output / f"{label}.stderr").write_text(completed.stderr)
    result = check_task(directory, case, before)
    verification_output = result.pop("verification_output", "")
    (args.output / f"{label}.verification.txt").write_text(verification_output)
    result["passed"] = result["passed"] and completed.returncode == 0
    return {"model": model, "variant": variant, "case": case, "exit_code": completed.returncode,
            "elapsed_seconds": round(time.monotonic() - start, 2), **result}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--codex", default="codex")
    parser.add_argument("--model", action="append", required=True)
    parser.add_argument("--baseline", default="3.9.0")
    parser.add_argument("--effort", default="medium")
    parser.add_argument("--repeat", type=int, default=2)
    parser.add_argument("--mode", choices=("probes", "tasks"), default="probes")
    parser.add_argument("--variant", choices=("native", "baseline", "candidate"), action="append",
                        help="只运行指定组，便于修改策略前记录基线；默认三组")
    parser.add_argument("--task-case", choices=TASK_CASES, action="append")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.repeat < 1:
        parser.error("--repeat must be positive")
    if args.output.resolve().is_relative_to(PACKAGE):
        parser.error("raw outputs must stay outside the source/release tree")
    args.output.mkdir(parents=True, exist_ok=False)
    cases = load_cases(PACKAGE / "evals/cases.json")
    baseline = subprocess.run(["git", "show", f"{args.baseline}:SKILL.md"], cwd=PACKAGE,
                              text=True, capture_output=True, check=True).stdout
    variants = {"native": "", "baseline": baseline,
                "candidate": (PACKAGE / "SKILL.md").read_text(encoding="utf-8")}
    if args.variant:
        variants = {key: value for key, value in variants.items() if key in args.variant}
    reference_sets = {key: {} for key in variants}
    for variant in variants:
        if variant == "native":
            continue
        paths = ([p.relative_to(PACKAGE).as_posix() for p in (PACKAGE / "references").glob("*.md")]
                 if variant == "candidate" else subprocess.run(
                     ["git", "ls-tree", "-r", "--name-only", args.baseline, "--", "references"],
                     cwd=PACKAGE, capture_output=True, text=True, check=True).stdout.splitlines())
        reference_sets[variant] = {path: (PACKAGE / path).read_text() if variant == "candidate" else subprocess.run(
            ["git", "show", f"{args.baseline}:{path}"], cwd=PACKAGE, capture_output=True, text=True, check=True).stdout
            for path in paths if path.endswith(".md")}
    (args.output / "schema.json").write_text(json.dumps(SCHEMA), encoding="utf-8")
    metadata = {"scope": "root-only batched decision probes" if args.mode == "probes" else "isolated local task fixtures",
                "baseline": args.baseline, "effort": args.effort,
                "cases_hash": content_hash({"cases.json": (PACKAGE / "evals/cases.json").read_text()}),
                "task_cases": args.task_case or list(TASK_CASES),
                "reference_hashes": {k: content_hash(v) for k, v in reference_sets.items()},
                "protocol_hashes": {k: hashlib.sha256(v.encode()).hexdigest() for k, v in variants.items()}}
    (args.output / "metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    results = []
    for repetition in range(args.repeat):
        # Rotate order to avoid always testing the candidate last.
        order = list(variants)
        order = order[repetition % len(order):] + order[:repetition % len(order)]
        for model in args.model:
            for variant in order:
                label = f"{model}-{variant}-{repetition + 1}"
                if args.mode == "tasks":
                    for case in args.task_case or TASK_CASES:
                        row = task_trial(args, model, variant, variants[variant], reference_sets[variant], f"{label}-{case}", case)
                        row["repeat"] = repetition + 1
                        results.append(row)
                        (args.output / "summary.json").write_text(json.dumps(results, indent=2))
                        print(json.dumps(row, ensure_ascii=False), flush=True)
                        if row["exit_code"]:
                            return 2
                    continue
                destination = args.output / f"{label}.json"
                with tempfile.TemporaryDirectory(prefix="workflow-probe-") as temp:
                    command = cli_base(args.codex, model, args.effort, Path(temp))
                    command += ["--output-schema", str(args.output / "schema.json"),
                                "-o", str(destination), "-"]
                    start = time.monotonic()
                    completed = subprocess.run(command, input=prompt_for(variants[variant], cases),
                                               text=True, capture_output=True, timeout=300,
                                               env={**os.environ, "RUST_LOG": "error"})
                (args.output / f"{label}.jsonl").write_text(completed.stdout, encoding="utf-8")
                (args.output / f"{label}.stderr").write_text(completed.stderr, encoding="utf-8")
                row = {"model": model, "variant": variant, "repeat": repetition + 1,
                       "elapsed_seconds": round(time.monotonic() - start, 2), "exit_code": completed.returncode}
                if completed.returncode or not destination.exists():
                    row["error"] = "model run failed; inspect raw log"
                else:
                    row.update(score(cases, json.loads(destination.read_text(encoding="utf-8"))))
                for line in completed.stdout.splitlines():
                    try:
                        event = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if event.get("type") == "turn.completed":
                        row["usage"] = event.get("usage")
                results.append(row)
                (args.output / "summary.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
                print(json.dumps(row, ensure_ascii=False), flush=True)
                if "error" in row:
                    return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
