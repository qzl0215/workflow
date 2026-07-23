#!/usr/bin/env python3
"""Build a read-only Task context capsule from workflow truth sources.

The capsule is derived output: it is printed to stdout and never written into
the thread directory. Missing required slices fail closed with exit code 2.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Callable


HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$", re.MULTILINE)
EVIDENCE_RE = re.compile(r"\b([EJ])(\d{2,})\b")
EVIDENCE_RANGE_RE = re.compile(r"\b([EJ])(\d{2,})\s*[-–]\s*(?:[EJ])?(\d{2,})\b")
FRONTMATTER_RE = re.compile(
    r"\A---[ \t]*\r?\n(?P<body>.*?)\r?\n---[ \t]*(?:\r?\n|$)",
    re.DOTALL,
)
FRONTMATTER_STAGE_RE = re.compile(r"^[ \t]*stage[ \t]*:[ \t]*(?P<value>.+?)[ \t]*$", re.MULTILINE)
SNAPSHOT_STAGE_RE = re.compile(
    r"^(?P<prefix>[ \t]*-[ \t]*当前阶段[ \t]*[：:][ \t]*)(?P<value>.+?)[ \t]*$",
    re.MULTILINE,
)
STAGE_ORDER = (
    "需求澄清",
    "选定方案",
    "拆成任务",
    "执行任务",
    "验收交付",
    "提炼经验",
    "回灌改进",
)
CANONICAL_STAGES = frozenset(STAGE_ORDER)
STAGE_RESULT_TYPES = frozenset({"document", "visual", "collection"})
LEGACY_STAGE_ALIASES = {
    "看清目标": "需求澄清",
    "intake": "需求澄清",
    "clarify": "需求澄清",
    "readiness": "需求澄清",
    "solution": "选定方案",
    "strategic planning": "选定方案",
    "experience": "选定方案",
    "write": "拆成任务",
    "write plan": "拆成任务",
    "act": "执行任务",
    "act plan": "执行任务",
    "debug": "执行任务",
    "verify": "验收交付",
    "finish": "验收交付",
}


@dataclass(frozen=True)
class Section:
    title: str
    level: int
    text: str


def normalize_stage(raw_stage: str) -> str:
    """Normalize a stage once at this script's input boundary."""
    stage = " ".join(raw_stage.split())
    if len(stage) >= 2 and stage[0] == stage[-1] and stage[0] in {'"', "'"}:
        stage = stage[1:-1].strip()
    if stage in CANONICAL_STAGES:
        return stage
    normalized = LEGACY_STAGE_ALIASES.get(stage.casefold())
    if normalized:
        return normalized
    expected = "、".join(sorted(CANONICAL_STAGES))
    raise ValueError(f"未知阶段；只接受七个中文阶段或兼容期旧值：{expected}")


def read_optional(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="replace")


def sections(text: str) -> list[Section]:
    matches = list(HEADING_RE.finditer(text))
    result: list[Section] = []
    for index, match in enumerate(matches):
        level = len(match.group(1))
        end = len(text)
        for later in matches[index + 1 :]:
            if len(later.group(1)) <= level:
                end = later.start()
                break
        result.append(Section(match.group(2).strip(), level, text[match.start() : end].strip()))
    return result


def find_section(text: str, predicate: Callable[[str], bool]) -> Section | None:
    for section in sections(text):
        if predicate(section.title):
            return section
    return None


def find_named_section(text: str, name: str) -> Section | None:
    wanted = name.casefold()
    return find_section(text, lambda title: wanted in title.casefold())


def frontmatter_stage(text: str) -> str | None:
    frontmatter = FRONTMATTER_RE.match(text)
    if not frontmatter:
        return None
    match = FRONTMATTER_STAGE_RE.search(frontmatter.group("body"))
    return match.group("value") if match else None


def snapshot_stage(text: str) -> str | None:
    snapshot = find_named_section(text, "Current Snapshot")
    if not snapshot:
        return None
    match = SNAPSHOT_STAGE_RE.search(snapshot.text)
    return match.group("value") if match else None


def resolve_stage(task_plan: str, asserted_stage: str | None) -> str:
    """Resolve the persisted truth, treating the optional CLI value as an assertion."""
    frontmatter_raw = frontmatter_stage(task_plan)
    snapshot_raw = snapshot_stage(task_plan)
    frontmatter_value = normalize_stage(frontmatter_raw) if frontmatter_raw is not None else None
    snapshot_value = normalize_stage(snapshot_raw) if snapshot_raw is not None else None

    if frontmatter_value and snapshot_value and frontmatter_value != snapshot_value:
        raise ValueError(
            "task_plan 阶段冲突："
            f"frontmatter 为「{frontmatter_value}」，Current Snapshot 为「{snapshot_value}」"
        )

    persisted_stage = frontmatter_value or snapshot_value
    assertion = normalize_stage(asserted_stage) if asserted_stage is not None else None
    if persisted_stage and assertion and persisted_stage != assertion:
        raise ValueError(
            f"阶段冲突：task_plan 为「{persisted_stage}」，--stage 断言为「{assertion}」"
        )
    if persisted_stage:
        return persisted_stage
    if assertion:
        return assertion
    raise ValueError("缺少阶段：task_plan 未保存阶段，且没有提供 --stage 兼容断言")


def canonicalize_snapshot_stage(snapshot_text: str, stage: str) -> str:
    return SNAPSHOT_STAGE_RE.sub(
        lambda match: f"{match.group('prefix')}{stage}",
        snapshot_text,
        count=1,
    )


def table_cells(line: str) -> list[str]:
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def normalize_stage_result_path(raw_path: str) -> str:
    value = raw_path.strip()
    if value.startswith("`") and value.endswith("`") and len(value) >= 2:
        value = value[1:-1].strip()
    if not value or "`" in value:
        raise ValueError("阶段成果路由的项目相对入口为空或格式无效")
    if (
        value.startswith(("/", "~"))
        or "\\" in value
        or re.match(r"^[A-Za-z]:", value)
        or re.match(r"^[A-Za-z][A-Za-z0-9+.-]*://", value)
    ):
        raise ValueError("阶段成果路由只接受项目相对路径，不接受绝对路径、URL 或反斜杠")
    path = PurePosixPath(value)
    if path.as_posix() == "." or ".." in path.parts:
        raise ValueError("阶段成果路由不得为空、指向当前目录或逃逸项目边界")
    return path.as_posix()


def parse_stage_results(task_plan: str) -> list[dict[str, str]]:
    section = find_named_section(task_plan, "阶段成果路由")
    if not section:
        return []
    rows = [table_cells(line) for line in section.text.splitlines() if line.lstrip().startswith("|")]
    header = ["阶段", "目标类型", "项目相对入口"]
    try:
        header_index = rows.index(header)
    except ValueError as error:
        raise ValueError("阶段成果路由缺少标准表头：阶段 / 目标类型 / 项目相对入口") from error

    results: list[dict[str, str]] = []
    seen: set[str] = set()
    for cells in rows[header_index + 1 :]:
        if all(re.fullmatch(r":?-{3,}:?", cell) for cell in cells):
            continue
        if len(cells) != 3 or not all(cells):
            raise ValueError("阶段成果路由每行必须完整填写阶段、目标类型和项目相对入口")
        try:
            stage = normalize_stage(cells[0])
        except ValueError as error:
            raise ValueError(f"阶段成果路由包含未知阶段：{cells[0]}") from error
        target_type = cells[1].strip("` ").casefold()
        if target_type not in STAGE_RESULT_TYPES:
            expected = " / ".join(sorted(STAGE_RESULT_TYPES))
            raise ValueError(f"阶段成果路由目标类型无效；只接受 {expected}")
        if stage in seen:
            raise ValueError(f"阶段成果路由重复：{stage} 每次只能有一个活动入口")
        seen.add(stage)
        results.append(
            {
                "stage": stage,
                "target_type": target_type,
                "path": normalize_stage_result_path(cells[2]),
            }
        )
    order = {stage: index for index, stage in enumerate(STAGE_ORDER)}
    return sorted(results, key=lambda result: order[result["stage"]])


def find_id_section(text: str, item_id: str, *, task: bool) -> Section | None:
    prefix = re.compile(rf"^{re.escape(item_id)}(?:\s|[｜|:：—-]|$)", re.I)
    for section in sections(text):
        title = re.sub(r"[`*_]", "", section.title).strip()
        if prefix.search(title):
            if task or "-T" not in title.upper():
                return section
    return None


def find_table_slice(text: str, item_id: str) -> str:
    lines = text.splitlines()
    row_index = next(
        (index for index, line in enumerate(lines) if re.search(rf"\|\s*{re.escape(item_id)}\s*\|", line)),
        None,
    )
    if row_index is None:
        return ""
    start = row_index
    while start > 0 and lines[start - 1].lstrip().startswith("|"):
        start -= 1
    table = lines[start : row_index + 1]
    if len(table) > 3:
        table = table[:2] + [lines[row_index]]
    return "\n".join(table).strip()


def expand_evidence_ids(text: str) -> list[str]:
    ids: set[str] = set()
    for match in EVIDENCE_RANGE_RE.finditer(text):
        prefix, start_raw, end_raw = match.groups()
        start, end = int(start_raw), int(end_raw)
        if end >= start and end - start <= 100:
            width = max(len(start_raw), len(end_raw))
            ids.update(f"{prefix}{value:0{width}d}" for value in range(start, end + 1))
    ids.update(match.group(0) for match in EVIDENCE_RE.finditer(text))
    return sorted(ids)


def evidence_slices(findings: str, evidence_ids: list[str]) -> tuple[list[str], list[str]]:
    found: list[str] = []
    missing: list[str] = []
    seen: set[str] = set()
    for evidence_id in evidence_ids:
        section = find_id_section(findings, evidence_id, task=True)
        slice_text = section.text if section else find_table_slice(findings, evidence_id)
        if not slice_text:
            missing.append(f"findings:{evidence_id}")
            continue
        if slice_text not in seen:
            found.append(slice_text)
            seen.add(slice_text)
    return found, missing


def explicit_context_refs(task_text: str) -> list[str]:
    refs: list[str] = []
    for line in task_text.splitlines():
        if "上下文引用" not in line and "context refs" not in line.casefold():
            continue
        _, _, value = line.partition("：")
        if not value:
            _, _, value = line.partition(":")
        refs.extend(part.strip(" `") for part in re.split(r"[；;]", value) if part.strip(" `"))
    return refs


def clean_slice(text: str) -> str:
    return text.strip() if text.strip() else "_not available_"


def build_capsule(task_dir: Path, plan_id: str, task_id: str, stage: str | None = None) -> dict[str, object]:
    paths = {
        "task_plan": task_dir / "task_plan.md",
        "findings": task_dir / "findings.md",
        "implementation_plan": task_dir / "implementation-plan.md",
        "progress": task_dir / "progress.md",
    }
    texts = {name: read_optional(path) for name, path in paths.items()}
    stage = resolve_stage(texts["task_plan"], stage)
    stage_results = parse_stage_results(texts["task_plan"])
    missing: list[str] = []
    loaded: list[str] = []

    if not texts["task_plan"]:
        missing.append("task_plan.md")
    if not texts["progress"]:
        missing.append("progress.md")

    snapshot = find_named_section(texts["task_plan"], "Current Snapshot")
    stage_results_section = find_named_section(texts["task_plan"], "阶段成果路由")
    handoff = find_named_section(texts["progress"], "Handoff checkpoint")
    plan = find_id_section(texts["task_plan"], plan_id, task=False)
    task = find_id_section(texts["task_plan"], task_id, task=True)

    snapshot_text = canonicalize_snapshot_stage(snapshot.text, stage) if snapshot else ""
    handoff_text = handoff.text if handoff else ""
    plan_text = plan.text if plan else find_table_slice(texts["task_plan"], plan_id)
    task_text = task.text if task else find_table_slice(texts["task_plan"], task_id)

    for label, value in [
        ("task_plan.md#Current Snapshot", snapshot_text),
        (f"task_plan.md#{plan_id}", plan_text),
        (f"task_plan.md#{task_id}", task_text),
        ("progress.md#Handoff checkpoint", handoff_text),
    ]:
        if value:
            loaded.append(label)
        else:
            missing.append(label)

    implementation = find_id_section(texts["implementation_plan"], task_id, task=True)
    implementation_text = implementation.text if implementation else find_table_slice(texts["implementation_plan"], task_id)
    if implementation_text:
        loaded.append(f"implementation-plan.md#{task_id}")
    elif stage in {"执行任务", "验收交付"} and texts["implementation_plan"]:
        missing.append(f"implementation-plan.md#{task_id}")

    evidence_ids = expand_evidence_ids(task_text + "\n" + implementation_text)
    found_evidence, missing_evidence = evidence_slices(texts["findings"], evidence_ids)
    missing.extend(missing_evidence)
    if found_evidence:
        loaded.extend(f"findings.md#{evidence_id}" for evidence_id in evidence_ids if f"findings:{evidence_id}" not in missing)

    context_refs = explicit_context_refs(task_text)
    external_refs = [
        ref for ref in context_refs
        if not ref.casefold().startswith(("findings:", "implementation:"))
    ]

    source_total_bytes = sum(path.stat().st_size for path in paths.values() if path.exists())
    selected = "\n\n".join(
        part
        for part in [
            snapshot_text,
            stage_results_section.text if stage_results_section else "",
            handoff_text,
            plan_text,
            task_text,
            implementation_text,
            *found_evidence,
        ]
        if part
    )
    selected_bytes = len(selected.encode("utf-8"))
    ratio = round(selected_bytes / source_total_bytes, 4) if source_total_bytes else None

    return {
        "schema_version": 2,
        "task_dir": str(task_dir.resolve()),
        "stage": stage,
        "plan_id": plan_id,
        "task_id": task_id,
        "stage_results": stage_results,
        "fail_closed": bool(missing),
        "loaded": loaded,
        "external_refs": external_refs,
        "not_loaded": [
            "complete chat history",
            "complete workflow truth-source files",
            "completed Plan details",
            "unreferenced findings and artifacts",
            "unrelated project documentation",
        ],
        "missing_refs": sorted(set(missing)),
        "metrics": {
            "source_total_bytes": source_total_bytes,
            "selected_bytes": selected_bytes,
            "selected_ratio": ratio,
        },
        "slices": {
            "snapshot": snapshot_text,
            "handoff": handoff_text,
            "plan": plan_text,
            "task": task_text,
            "implementation": implementation_text,
            "evidence": found_evidence,
        },
        "upgrade_rule": "If L0-L2 is insufficient, record gap/target/expected_answer/level before loading L3 or L4.",
    }


def render_markdown(capsule: dict[str, object]) -> str:
    slices = capsule["slices"]
    assert isinstance(slices, dict)
    metrics = capsule["metrics"]
    assert isinstance(metrics, dict)
    evidence = slices["evidence"]
    assert isinstance(evidence, list)
    loaded = capsule["loaded"]
    external_refs = capsule["external_refs"]
    missing = capsule["missing_refs"]
    not_loaded = capsule["not_loaded"]
    stage_results = capsule["stage_results"]
    assert isinstance(stage_results, list)
    rendered_stage_results = [
        f"- `{result['stage']}` → `{result['target_type']}` → `{result['path']}`"
        for result in stage_results
        if isinstance(result, dict)
    ]
    lines = [
        "# Task Context Capsule",
        "",
        f"- Task directory: `{capsule['task_dir']}`",
        f"- Stage / Plan / Task: `{capsule['stage']}` / `{capsule['plan_id']}` / `{capsule['task_id']}`",
        f"- Fail closed: `{'yes' if capsule['fail_closed'] else 'no'}`",
        f"- Selected context: `{metrics['selected_bytes']}` / `{metrics['source_total_bytes']}` bytes (`{metrics['selected_ratio']}`)",
        "",
        "## L0｜Location",
        "",
        f"`{capsule['task_dir']}` → `{capsule['plan_id']}` → `{capsule['task_id']}`",
        "",
        "## L1｜Current Snapshot",
        "",
        clean_slice(str(slices["snapshot"])),
        "",
        "## L1｜Active stage results",
        "",
        *(rendered_stage_results or ["_none registered_"]),
        "",
        "## L1｜Handoff checkpoint",
        "",
        clean_slice(str(slices["handoff"])),
        "",
        "## L2｜Current Plan",
        "",
        clean_slice(str(slices["plan"])),
        "",
        "## L2｜Current Task",
        "",
        clean_slice(str(slices["task"])),
        "",
        "## L2｜Implementation slice",
        "",
        clean_slice(str(slices["implementation"])),
        "",
        "## L2｜Referenced evidence",
        "",
        *(evidence or ["_none referenced_"]),
        "",
        "## L3/L4｜Context accounting",
        "",
        "- Loaded: " + (", ".join(f"`{item}`" for item in loaded) if loaded else "none"),
        "- External refs for project adapter: " + (", ".join(f"`{item}`" for item in external_refs) if external_refs else "none"),
        "- Not loaded: " + ", ".join(str(item) for item in not_loaded),
        "- Missing refs: " + (", ".join(f"`{item}`" for item in missing) if missing else "none"),
        f"- Upgrade: {capsule['upgrade_rule']}",
    ]
    return "\n".join(lines).rstrip() + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    task_dir = parser.add_mutually_exclusive_group(required=True)
    task_dir.add_argument("--task-dir", dest="task_dir", type=Path)
    task_dir.add_argument("--thread-dir", dest="task_dir", type=Path, help=argparse.SUPPRESS)
    parser.add_argument("--plan", required=True, dest="plan_id")
    parser.add_argument("--task", required=True, dest="task_id")
    parser.add_argument("--stage", help="可选阶段断言；task_plan 没有阶段时作为旧计划兼容输入")
    parser.add_argument("--format", choices=("markdown", "json"), default="markdown")
    parser.add_argument("--allow-missing", action="store_true", help="Return zero even when the capsule fails closed")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    plan_id = args.plan_id.upper()
    task_id = args.task_id.upper()
    if not re.fullmatch(r"P\d{2,}", plan_id):
        print("invalid --plan; expected P01", file=sys.stderr)
        return 2
    if not re.fullmatch(r"P\d{2,}-T\d{2,}", task_id) or not task_id.startswith(plan_id + "-"):
        print("invalid --task or task does not belong to plan", file=sys.stderr)
        return 2

    try:
        capsule = build_capsule(args.task_dir, plan_id, task_id, args.stage)
    except ValueError as error:
        print(str(error), file=sys.stderr)
        return 2
    if args.format == "json":
        print(json.dumps(capsule, ensure_ascii=False, indent=2))
    else:
        print(render_markdown(capsule), end="")
    return 0 if args.allow_missing or not capsule["fail_closed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
