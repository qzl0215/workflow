#!/usr/bin/env python3
"""运行可复查的模型决策探针；不将其当作端到端任务验收。"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
import time


PACKAGE = Path(__file__).resolve().parents[1]
ACTIONS = ("execute", "ask", "plan_only", "deliver", "recover", "verify", "finish")
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


def task_trial(args, model: str, variant: str, protocol: str, label: str, case: str) -> dict:
    directory = args.output / label
    directory.mkdir()
    (directory / "main.py").write_text("def total(values):\n    if not values:\n        return None\n    return sum(values)\n")
    (directory / "user-notes.txt").write_text("USER OWNED: preserve this unfinished note.\n")
    (directory / "test_main.py").write_text(
        "import unittest\nfrom main import total\n\nclass TotalTest(unittest.TestCase):\n"
        "    def test_empty(self): self.assertEqual(total([]), 0)\n"
        "    def test_values(self): self.assertEqual(total([1, 2, -1]), 2)\n"
        "\nif __name__ == '__main__': unittest.main()\n")
    if variant != "native":
        for path in (PACKAGE / "references").glob("*.md"):
            contents = path.read_text() if variant == "candidate" else subprocess.run(
                ["git", "show", f"{args.baseline}:references/{path.name}"], cwd=PACKAGE,
                capture_output=True, text=True, check=True).stdout
            destination = directory / "references" / path.name
            destination.parent.mkdir(exist_ok=True)
            destination.write_text(contents)
    before = snapshot(directory)
    user = "帮我修复 main.py 中 total 的空列表返回值，应为 0；非空列表行为不变，并验证。"
    if case == "plan_first":
        user = "针对 main.py 中 total 空列表应返回 0 的问题，先给修复方案，等我确认后再改文件。"
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
    after = snapshot(directory)
    changed = sorted(p for p in before.keys() | after.keys() if before.get(p) != after.get(p))
    verification = subprocess.run(["python3", "-B", "-m", "unittest", "test_main"], cwd=directory,
                                  capture_output=True, text=True, check=False)
    passed = changed == [] if case == "plan_first" else changed == ["main.py"] and verification.returncode == 0
    (args.output / f"{label}.verification.txt").write_text(verification.stdout + verification.stderr)
    return {"model": model, "variant": variant, "case": case, "exit_code": completed.returncode,
            "passed": passed and completed.returncode == 0, "changed": changed,
            "verification_exit": verification.returncode, "elapsed_seconds": round(time.monotonic() - start, 2),
            "semantic_review": "required"}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--codex", default="codex")
    parser.add_argument("--model", action="append", required=True)
    parser.add_argument("--baseline", default="3.9.0")
    parser.add_argument("--effort", default="medium")
    parser.add_argument("--repeat", type=int, default=2)
    parser.add_argument("--mode", choices=("probes", "tasks"), default="probes")
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
    (args.output / "schema.json").write_text(json.dumps(SCHEMA), encoding="utf-8")
    metadata = {"scope": "root-only batched decision probes" if args.mode == "probes" else "isolated local task fixtures",
                "baseline": args.baseline, "effort": args.effort,
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
                    for case in ("clear_fix", "plan_first"):
                        row = task_trial(args, model, variant, variants[variant], f"{label}-{case}", case)
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
