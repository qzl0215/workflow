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
from pathlib import Path
from typing import Callable


HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$", re.MULTILINE)
EVIDENCE_RE = re.compile(r"\b([EJ])(\d{2,})\b")
EVIDENCE_RANGE_RE = re.compile(r"\b([EJ])(\d{2,})\s*[-–]\s*(?:[EJ])?(\d{2,})\b")


@dataclass(frozen=True)
class Section:
    title: str
    level: int
    text: str


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


def build_capsule(task_dir: Path, plan_id: str, task_id: str, stage: str) -> dict[str, object]:
    paths = {
        "task_plan": task_dir / "task_plan.md",
        "findings": task_dir / "findings.md",
        "implementation_plan": task_dir / "implementation-plan.md",
        "progress": task_dir / "progress.md",
    }
    texts = {name: read_optional(path) for name, path in paths.items()}
    missing: list[str] = []
    loaded: list[str] = []

    if not texts["task_plan"]:
        missing.append("task_plan.md")
    if not texts["progress"]:
        missing.append("progress.md")

    snapshot = find_named_section(texts["task_plan"], "Current Snapshot")
    handoff = find_named_section(texts["progress"], "Handoff checkpoint")
    plan = find_id_section(texts["task_plan"], plan_id, task=False)
    task = find_id_section(texts["task_plan"], task_id, task=True)

    snapshot_text = snapshot.text if snapshot else ""
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
    elif stage.casefold() in {"act", "act plan", "verify"} and texts["implementation_plan"]:
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
        part for part in [snapshot_text, handoff_text, plan_text, task_text, implementation_text, *found_evidence]
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
    parser.add_argument("--stage", default="Act Plan")
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

    capsule = build_capsule(args.task_dir, plan_id, task_id, args.stage)
    if args.format == "json":
        print(json.dumps(capsule, ensure_ascii=False, indent=2))
    else:
        print(render_markdown(capsule), end="")
    return 0 if args.allow_missing or not capsule["fail_closed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
