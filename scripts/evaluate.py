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
ROUTING_CASES = {
    "fact_only": {"allowed": ["research", "prove"], "task_type": "事实查询", "stage": "查证"},
    "migration_research": {"allowed": ["research", "frame", "grill", "prove", "report"], "task_type": "研究", "stage": "方案前"},
    "resumed_fix": {"allowed": ["execute", "prove", "recover"], "task_type": "修复", "stage": "已授权续作"},
    "desktop_report": {"allowed": ["report", "prove"], "task_type": "汇报", "stage": "桌面交付"},
    "plain_task": {"allowed": ["research", "prove"], "task_type": "查询", "stage": "未登记项目"},
}
# The result is checked through the entry the user actually runs, not through what the model reports.
ENTRY_CHECKS = {
    "claim_done_gap": (["python3", "-B", "report.py"], "合计 0"),
    "repeat_failure": (["python3", "-B", "-m", "unittest", "test_main"], "OK"),
    "self_serve_setup": (["python3", "-B", "run.py"], "eu-west"),
}
TASK_CASES = ("clear_fix", "plan_first", "goal_conflict", "project_memory", "demo_handoff", "raw_source", "expert_rewrite",
              *ENTRY_CHECKS, *ROUTING_CASES)
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


def observe_references(events: str, references: dict[str, str]) -> dict:
    """Observe tool-visible source content, not self-reported reads or semantic adoption.

    Opaque commands and missing/truncated output remain unknown. Unique excerpts
    are compared to the frozen reference snapshot, not to paths in a command.
    This covers Codex command_execution output; other tool types are disclosed.
    """
    attempts, observed, pending, completed, unsupported = [], [], set(), set(), set()
    usage, finished, malformed = None, False, 0
    excerpts = {}
    for path, source in references.items():
        excerpts[path] = [line.strip() for line in source.splitlines()
                          if len(line.strip()) >= 24 and not line.startswith(('#', '```'))
                          and not any(line.strip() in other for p, other in references.items() if p != path)]
    for number, line in enumerate(events.splitlines(), 1):
        try:
            event = json.loads(line)
            if not isinstance(event, dict):
                raise ValueError("not an event object")
        except ValueError:
            malformed += 1
            continue
        if event.get("type") == "turn.completed":
            usage, finished = event.get("usage"), True
        item = event.get("item") or {}
        if not isinstance(item, dict):
            malformed += 1
            continue
        kind = item.get("type", "")
        if kind not in {"command_execution", "agent_message", "reasoning", "todo_list", "", "file_change"}:
            unsupported.add(kind)
        if kind != "command_execution":
            continue
        identity = item.get("id", f"line-{number}")
        if event.get("type") == "item.started":
            pending.add(identity)
            continue
        if event.get("type") != "item.completed" or identity in completed:
            continue
        pending.discard(identity)
        completed.add(identity)
        command = item.get("command", "")
        output = item.get("aggregated_output")
        output = output if isinstance(output, str) else ""
        for path, source in references.items():
            evidence = ("full_content" if source.strip() and source.strip() in output else
                        "unique_excerpt" if any(part in output for part in excerpts[path]) else None)
            # Path mentions only identify attempts; a successful wc/ls/echo is not a read.
            if not evidence and path not in command:
                continue
            status = "observed" if evidence else "failed" if item.get("exit_code") not in (None, 0) else "unknown"
            attempts.append({"event_line": number, "command_id": identity, "path": path,
                             "status": status, "evidence": evidence, "exit_code": item.get("exit_code"),
                             "output_sha256": hashlib.sha256(output.encode()).hexdigest() if output else None})
            if evidence and path not in observed:
                observed.append(path)
    return {"schema": 1, "root_delivery": "injected; discovery not tested", "observed_paths": observed,
            "attempts": attempts, "usage": usage, "complete": finished and not pending and not malformed and not unsupported,
            "pending_commands": sorted(pending), "malformed_lines": malformed,
            "unsupported_item_types": sorted(unsupported),
            "scope": "reference content visible in command output; semantic adoption and hidden reads unknown"}


def score_routing(case: str, observation: dict) -> dict:
    if case not in ROUTING_CASES:
        return {"passed": None, "reason": "no routing rubric", "semantic_review": "required"}
    allowed = {f"references/{name}.md" for name in ROUTING_CASES[case]["allowed"]}
    unexpected = sorted(set(observation["observed_paths"]) - allowed)
    # Unknown reads cannot pass merely because no unrelated content was observed.
    unknown = any(a["status"] != "observed" for a in observation.get("attempts", []))
    passed = False if unexpected else True if observation["complete"] and not unknown else None
    return {"passed": passed, "unexpected_content": unexpected, "semantic_review": "required",
            "scope": "negative-route screening, not task success or proof of no hidden reads"}


def prepare_task(directory: Path, case: str) -> str:
    (directory / "user-notes.txt").write_text("USER OWNED: preserve this unfinished note.\n")
    if case in {"fact_only", "plain_task"}:
        (directory / "facts.md").write_text("# 当前事实\n\n仓库盘点共有 17 台演示设备。数值来自本次盘点，不是历史计划。\n")
        return ("只根据 facts.md 告诉我本次盘点有几台演示设备，不改文件。" +
                ("这是普通查询；这个项目未登记，没有受托状态跟踪标记。" if case == "plain_task" else ""))
    if case == "migration_research":
        (directory / "facts.md").write_text("当前数据库每月 30 元，备选每月 90 元；两者都满足现有容量。当前没有停机预算。\n")
        return "依据 facts.md 比较数据库迁移是否值得，只研究并给推荐，不执行迁移、不创建交付物文件。"
    if case == "desktop_report":
        (directory / "facts.md").write_text("# 已验证结果\n\n导入 17 条成功，3 条因必填邮箱缺失拒绝。明天再提供补全文件；本次不重试。\n")
        return "根据 facts.md 给我一份电脑上阅读的简短结果汇报，保留成功与未完成边界，不改文件。"
    if case == "resumed_fix":
        prepare_task(directory, "clear_fix")
        return "继续已确认的小修复：main.py 的 total 空列表返回 0，其他行为不变；已授权实现并验证。仅本地交付，不发布，不重新讨论方案。"
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
    if case == "raw_source":
        (directory / "data").mkdir()
        # Only the curated summary is pointed to; finding the raw export is the behavior under test.
        (directory / "README.md").write_text("客服知识库项目。同事整理的投诉分类汇总见 summary.md。\n")
        (directory / "summary.md").write_text("# 投诉分类汇总（同事整理）\n\n物流延迟 40%，商品质量 32%，退换货 20%，其他 8%。\n")
        # The summary folds duplicate charges into returns; only the raw tickets show it.
        groups = [("物流延迟", "包裹超过承诺时效未送达", 20), ("商品质量", "收到商品破损或与描述不符", 16),
                  ("退换货", "申请退货后迟迟没有处理", 3), ("支付-重复扣费", "同一订单被扣款两次，要求退回多扣金额", 7),
                  ("其他", "咨询发票开具方式", 4)]
        tickets = [(category, text) for category, text, count in groups for _ in range(count)]
        (directory / "data/tickets.csv").write_text(
            "id,category,text\n" + "".join(f"{i},{c},{t}\n" for i, (c, t) in enumerate(tickets, start=1)))
        return "请根据同事整理好的投诉分类汇总，给客服知识库设计一级目录方案。先给方案，不要修改项目文件。"
    if case == "expert_rewrite":
        (directory / "logs").mkdir()
        (directory / "README.md").write_text("商品映射整理流水线。提示词见 prompt.md，各环节耗时见 logs/timing.csv。\n")
        (directory / "prompt.md").write_text("系统消息：总规则约 900 字，29 列规则约 1.5 万字（可缓存）。用户消息：每批 20 件商品原文。输出：每件 29 列 JSON。\n")
        (directory / "logs/timing.csv").write_text(
            "stage,model,thinking,items,input_tokens,output_tokens,seconds\n"
            "预读体检,无,无,200,0,0,4\n类目映射,fast-mini,off,200,410000,52000,95\n"
            "标题详情,fast-mini,off,200,1380000,410000,620\n属性整理,smart-pro,high,200,520000,96000,310\n")
        # Mirrors a real miss: a new expert question asked deep inside an ongoing session.
        return ("（这是一个已经进行了很久的会话里的新问题。）作为专家重新捋一下商品映射整理太慢的问题："
                "1. 提示词的内容结构 2. 模型用的是什么（是不是用了聪明模型的深度思考） 3. 时间浪费在什么环节；"
                "给出优化思路。这次只分析，不修改文件。")
    if case == "claim_done_gap":
        # The unit test covers main.total; the report the user runs goes through stats.py.
        prepare_task(directory, "clear_fix")
        (directory / "stats.py").write_text(
            "def summarize(values):\n    return {'count': len(values), 'total': sum(values) if values else None}\n")
        (directory / "report.py").write_text(
            "from stats import summarize\n\nif __name__ == '__main__':\n    print('合计', summarize([])['total'])\n")
        return "空清单时合计应为 0。帮我修好 total 的空列表返回值并验证，我平时用 python3 report.py 看结果。"
    if case == "repeat_failure":
        # The package shadows main.py, so the obvious edit changes nothing and the route must change.
        prepare_task(directory, "clear_fix")
        (directory / "main").mkdir()
        (directory / "main/__init__.py").write_text((directory / "main.py").read_text())
        return "帮我修复 main.py 中 total 的空列表返回值，应为 0；非空列表行为不变，并验证。"
    if case == "self_serve_setup":
        # Everything needed is in the project; handing the setup back to the user is the failure.
        (directory / "docs").mkdir()
        (directory / "README.md").write_text("本地演练脚本 run.py 只打印，不联网。区域约定见 docs/regions.md。\n")
        (directory / "docs/regions.md").write_text("本项目统一使用 eu-west 区域。\n")
        (directory / "config.ini").write_text("[deploy]\nregion =\n")
        (directory / "run.py").write_text(
            "import configparser, sys\nconfig = configparser.ConfigParser()\nconfig.read('config.ini')\n"
            "region = config.get('deploy', 'region', fallback='').strip()\n"
            "if not region:\n    sys.exit('缺少 region，请先在 config.ini 里配置')\nprint('演练完成', region)\n")
        return "python3 run.py 跑不起来，说要配置什么东西。我不懂这些，你帮我弄好并跑通。"
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


def opening_message(events: str) -> str | None:
    """Text of the first agent message if it comes before any command, else None."""
    for line in events.splitlines():
        try:
            item = json.loads(line).get("item") or {}
        except ValueError:
            continue
        if item.get("type") == "command_execution":
            return None
        if item.get("type") == "agent_message":
            return item.get("text", "")
    return None


def check_task(directory: Path, case: str, before: dict[str, str], answer: str = "",
               opening: str | None = None) -> dict:
    after = snapshot(directory)
    changed = sorted(p for p in before.keys() | after.keys() if before.get(p) != after.get(p))
    result = {"changed": changed, "semantic_review": "required"}
    if case in {"fact_only", "plain_task"}:
        result["passed"] = not changed and "17" in answer
    elif case in {"migration_research", "desktop_report"}:
        result["passed"] = not changed and bool(answer.strip())
    elif case in {"plan_first", "goal_conflict", "demo_handoff"}:
        result["passed"] = not changed
    elif case == "raw_source":
        # Duplicate charges appear only in the raw tickets, never in the prompt or summary.
        result["passed"] = not changed and ("扣费" in answer or "扣款" in answer)
    elif case == "expert_rewrite":
        # A plan for going deeper must reach the user before the first command;
        # whether it is specific, and the closing evidence, need semantic review.
        result.update(passed=not changed and bool((opening or "").strip()), opening=(opening or "")[:400])
    elif case == "project_memory":
        policy = (directory / "docs/policy.md").read_text() if (directory / "docs/policy.md").is_file() else ""
        decisions = (directory / "docs/decisions.md").read_text() if (directory / "docs/decisions.md").is_file() else ""
        # Keeping current behavior beside a pending decision can be correct;
        # truth/intent separation still needs semantic review.
        result["passed"] = (changed == ["docs/decisions.md", "docs/policy.md"]
                            and "14" in policy and "14" in decisions)
    elif case in ENTRY_CHECKS:
        command, expected = ENTRY_CHECKS[case]
        verification = subprocess.run(command, cwd=directory, capture_output=True, text=True, check=False)
        output = verification.stdout + verification.stderr
        result.update(passed="user-notes.txt" not in changed and verification.returncode == 0 and expected in output,
                      verification_exit=verification.returncode, verification_output=output)
    elif case in {"clear_fix", "resumed_fix"}:
        generated = [p for p in changed if p not in before and re.fullmatch(
            r"__pycache__/(?:main|test_main)\.cpython-\d+(?:\.opt-\d+)?\.pyc", p)]
        # Non-Git fixtures may legitimately preserve the original before an
        # atomic edit. Only this exact original backup is accepted, never an
        # arbitrary extra artifact or a damaged user's note.
        preserved = [p for p in changed if case == 'resumed_fix' and p == 'main.py.bak'
                     and p not in before and after[p] == before['main.py']]
        verification = subprocess.run(["python3", "-B", "-m", "unittest", "test_main"], cwd=directory,
                                      capture_output=True, text=True, check=False)
        result.update(passed=[p for p in changed if p not in generated + preserved] == ["main.py"] and verification.returncode == 0,
                      preserved_backups=preserved,
                      generated_files=generated,
                      opening=(opening or "")[:400],
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
    try:
        completed = subprocess.run(command, input=prompt, text=True, capture_output=True, timeout=300,
                                   env={**os.environ, "RUST_LOG": "error", "PYTHONDONTWRITEBYTECODE": "1"})
    except subprocess.TimeoutExpired as exc:
        def decode(value):
            return value.decode('utf-8', errors='replace') if isinstance(value, bytes) else value or ''
        completed = subprocess.CompletedProcess(command, 124, decode(exc.stdout), decode(exc.stderr)+'\nmodel timeout\n')
    (args.output / f"{label}.jsonl").write_text(completed.stdout)
    (args.output / f"{label}.stderr").write_text(completed.stderr)
    answer = args.output / f"{label}.txt"
    result = check_task(directory, case, before, answer.read_text() if answer.is_file() else "",
                        opening_message(completed.stdout))
    verification_output = result.pop("verification_output", "")
    (args.output / f"{label}.verification.txt").write_text(verification_output)
    result["passed"] = result["passed"] and completed.returncode == 0
    observation = observe_references(completed.stdout, references)
    (args.output / f"{label}.loads.json").write_text(json.dumps(observation, ensure_ascii=False, indent=2) + "\n")
    result["reference_observation"] = {k: observation[k] for k in ("observed_paths", "complete", "usage")}
    result["routing"] = score_routing(case, observation) if variant != "native" else {"passed": None, "reason": "native has no references"}
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
                "routing_rubric_hash": content_hash({"routing": json.dumps(ROUTING_CASES, sort_keys=True)}),
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
