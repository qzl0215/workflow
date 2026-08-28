#!/usr/bin/env python3
"""从 work.md 或旧版只读真源生成有界任务胶囊。"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path


SCHEMA_VERSION = 3
MAX_CAPSULE_BYTES = 32 * 1024
MAX_CONTRACT_BYTES = 12 * 1024
HEADING = re.compile(r"^(#{1,6})\s+(.+?)\s*$", re.MULTILINE)
FRONTMATTER = re.compile(r"\A---\s*\n(?P<body>.*?)\n---\s*(?:\n|$)", re.DOTALL)
FIELD = re.compile(r"^\s*-\s*(?P<key>[^：:]+)[：:]\s*(?P<value>.*?)\s*$", re.MULTILINE)
EVIDENCE_ID = re.compile(r"\b(?:E|J|R)\d{2,}\b")
PLAN_ID = re.compile(r"P\d+", re.I)
TASK_ID = re.compile(r"P\d+-T\d+", re.I)
STATUS_VALUES = frozenset({"active", "waiting", "blocked", "done"})
LEGACY_SOURCE_NAMES = (
    "task_plan.md",
    "findings.md",
    "implementation-plan.md",
    "progress.md",
    "index.md",
)
LEGACY_ACTIONS = {
    "需求澄清": "目标框定",
    "看清目标": "目标框定",
    "intake": "目标框定",
    "clarify": "目标框定",
    "readiness": "目标框定",
    "选定方案": "结果规划",
    "拆成任务": "结果规划",
    "solution": "结果规划",
    "strategic planning": "结果规划",
    "experience": "结果规划",
    "write": "结果规划",
    "write plan": "结果规划",
    "执行任务": "任务执行",
    "act": "任务执行",
    "act plan": "任务执行",
    "debug": "任务执行",
    "验收交付": "结果验真",
    "verify": "结果验真",
    "finish": "结果验真",
    "提炼经验": "经验复盘",
    "回灌改进": "经验复盘",
}


@dataclass(frozen=True)
class Section:
    title: str
    level: int
    text: str
    start: int
    end: int


def read_text(path: Path) -> str:
    if path.is_symlink():
        raise ValueError(f"工作真源不得是符号链接：{path.name}")
    if not path.is_file():
        return ""
    return path.read_text(encoding="utf-8")


def sections(text: str) -> list[Section]:
    matches = list(HEADING.finditer(text))
    result: list[Section] = []
    for index, match in enumerate(matches):
        level = len(match.group(1))
        end = len(text)
        for later in matches[index + 1 :]:
            if len(later.group(1)) <= level:
                end = later.start()
                break
        result.append(
            Section(
                match.group(2).strip(),
                level,
                text[match.start() : end].strip(),
                match.start(),
                end,
            )
        )
    return result


def find_section(text: str, names: tuple[str, ...]) -> Section | None:
    folded = tuple(name.casefold() for name in names)
    for section in sections(text):
        title = section.title.casefold()
        if any(name in title for name in folded):
            return section
    return None


def identifier_sections(text: str, identifier: str | None) -> list[Section]:
    if not identifier:
        return []
    pattern = re.compile(rf"(?<![A-Za-z0-9-]){re.escape(identifier)}(?![A-Za-z0-9-])", re.I)
    return [section for section in sections(text) if pattern.search(section.title)]


def find_identifier_section(text: str, identifier: str | None, *, source: str) -> Section | None:
    matches = identifier_sections(text, identifier)
    if len(matches) > 1:
        raise ValueError(f"{source} 中 {identifier} 出现多个标题，任务身份不唯一")
    return matches[0] if matches else None


def normalized_ids(plan_id: str | None, task_id: str | None) -> tuple[str | None, str | None]:
    plan = plan_id.strip().upper() if plan_id else None
    task = task_id.strip().upper() if task_id else None
    if plan and not PLAN_ID.fullmatch(plan):
        raise ValueError(f"计划标识无效：{plan_id}")
    if task and not TASK_ID.fullmatch(task):
        raise ValueError(f"任务标识无效：{task_id}")
    derived = task.split("-T", 1)[0] if task else None
    if plan and derived and plan != derived:
        raise ValueError(f"任务 {task} 不属于计划 {plan}")
    return plan or derived, task


def validate_parent(plan: Section, task: Section, plan_id: str, task_id: str, *, source: str) -> None:
    nested = plan.start < task.start < plan.end and task.level > plan.level
    if not nested:
        raise ValueError(f"{source} 中任务 {task_id} 未嵌套在计划 {plan_id} 下")


def normalize_text(text: str) -> str:
    return "\n".join(line.rstrip() for line in text.replace("\r\n", "\n").splitlines()).strip()


def exact_contract(text: str, *, label: str) -> str:
    normalized = normalize_text(text)
    size = len(normalized.encode("utf-8"))
    if size > MAX_CONTRACT_BYTES:
        raise ValueError(
            f"{label} 超过安全字节上限 {MAX_CONTRACT_BYTES}；请保留承重边界并改用真源引用"
        )
    return normalized


def direct_section_text(section: Section | None) -> str:
    """Return a section's own contract without loading nested sibling tasks."""

    if section is None:
        return ""
    lines = section.text.splitlines()
    selected: list[str] = []
    for index, line in enumerate(lines):
        match = re.match(r"^(#{1,6})\s+", line)
        if index and match and len(match.group(1)) > section.level:
            break
        selected.append(line)
    return "\n".join(selected)


def compact(text: str, limit: int = 8 * 1024) -> str:
    normalized = normalize_text(text)
    if len(normalized.encode("utf-8")) <= limit:
        return normalized
    encoded = normalized.encode("utf-8")[: limit - len("\n…已按胶囊上限截断".encode("utf-8"))]
    return encoded.decode("utf-8", errors="ignore") + "\n…已按胶囊上限截断"


def field_value(text: str, names: tuple[str, ...]) -> str | None:
    wanted = {name.casefold() for name in names}
    for match in FIELD.finditer(text):
        if match.group("key").strip().casefold() in wanted:
            return match.group("value").strip()
    return None


def normalized_status(
    text: str,
    *,
    default: str | None = None,
    names: tuple[str, ...] = ("状态", "status"),
    label: str = "work.md 状态",
    prefer_frontmatter: bool = False,
) -> str:
    field_raw = field_value(text, names)
    frontmatter = FRONTMATTER.match(text)
    frontmatter_raw = None
    if frontmatter:
        match = re.search(r"^\s*status\s*:\s*(\S+)\s*$", frontmatter.group("body"), re.M | re.I)
        frontmatter_raw = match.group(1) if match else None
    raw = frontmatter_raw if prefer_frontmatter and frontmatter_raw is not None else field_raw
    if raw is None:
        raw = frontmatter_raw
    value = raw.casefold() if raw else default
    aliases = {
        "进行中": "active",
        "等待": "waiting",
        "阻断": "blocked",
        "完成": "done",
        "completed": "done",
    }
    value = aliases.get(value or "", value)
    if value not in STATUS_VALUES:
        expected = " / ".join(sorted(STATUS_VALUES))
        raise ValueError(f"{label}无效；只接受 {expected}")
    return value


def stable_hash(value: object) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def relevant_receipts(text: str, task_id: str | None, task_text: str) -> str:
    section = find_section(text, ("已接受回执", "accepted receipts", "证据"))
    if section is None:
        return ""
    if not task_id:
        return compact(section.text)
    identifiers = set(EVIDENCE_ID.findall(task_text))
    selected = [
        line
        for line in section.text.splitlines()
        if task_id.casefold() in line.casefold()
        or bool(identifiers.intersection(EVIDENCE_ID.findall(line)))
    ]
    return compact("\n".join(selected))


def action_from_legacy(text: str) -> str:
    raw = field_value(text, ("当前阶段", "阶段"))
    if raw is None:
        frontmatter = FRONTMATTER.match(text)
        if frontmatter:
            match = re.search(r"^\s*stage\s*:\s*(.+?)\s*$", frontmatter.group("body"), re.M | re.I)
            raw = match.group(1).strip() if match else None
    if not raw:
        return ""
    return LEGACY_ACTIONS.get(raw, LEGACY_ACTIONS.get(raw.casefold(), ""))


def evidence_slice(findings: str, task_text: str) -> str:
    identifiers = set(EVIDENCE_ID.findall(task_text))
    if not identifiers:
        return ""
    lines = [line for line in findings.splitlines() if identifiers.intersection(EVIDENCE_ID.findall(line))]
    return compact("\n".join(lines))


def work_payload(task_dir: Path, plan_id: str | None, task_id: str | None) -> dict[str, object]:
    work_path = task_dir / "work.md"
    text = read_text(work_path)
    plan_id, task_id = normalized_ids(plan_id, task_id)
    status_section = find_section(text, ("当前状态", "当前工作"))
    if FRONTMATTER.match(text):
        status = normalized_status(text, prefer_frontmatter=True)
        if status_section and field_value(status_section.text, ("工作状态", "状态", "status")):
            projected_status = normalized_status(
                status_section.text,
                names=("工作状态", "状态", "status"),
            )
            if projected_status != status:
                raise ValueError("work.md 全局状态存在冲突投影")
    elif status_section:
        status = normalized_status(status_section.text)
    else:
        raise ValueError("work.md 缺少全局工作状态")
    contract = find_section(text, ("目标契约", "结果契约"))
    if contract is None:
        raise ValueError("work.md 缺少目标契约")
    plan = find_identifier_section(text, plan_id, source="work.md")
    if plan_id and plan is None:
        raise ValueError(f"work.md 找不到计划：{plan_id}")
    task = find_identifier_section(text, task_id, source="work.md")
    if task_id and task is None:
        raise ValueError(f"work.md 找不到任务：{task_id}")
    if plan_id and task_id and plan and task:
        validate_parent(plan, task, plan_id, task_id, source="work.md")
    current = find_section(text, ("当前结果", "有效成果"))
    next_action = find_section(text, ("下一就绪责任", "下一动作", "下一步"))
    blockers = find_section(text, ("阻断与交付", "阻断", "blocker"))
    delivery = find_section(text, ("交付状态", "真实交付", "delivery"))
    learn = find_section(text, ("经验候选", "经验复盘", "learn"))
    contract_text = exact_contract(contract.text, label="目标契约")
    plan_text = exact_contract(direct_section_text(plan), label="计划结果")
    task_text = exact_contract(task.text if task else plan.text if plan else "", label="任务契约")
    task_status = ""
    if task:
        task_status_raw = field_value(task.text, ("任务状态", "状态", "status"))
        if task_status_raw is None:
            raise ValueError(f"任务 {task_id} 缺少任务状态；禁止派发")
        task_status = normalized_status(
            task.text,
            names=("任务状态", "状态", "status"),
            label=f"任务 {task_id} 状态",
        )
    payload: dict[str, object] = {
        "schema_version": SCHEMA_VERSION,
        "source": "work.md",
        "source_paths": ["work.md"],
        "status": status,
        "work_status": status,
        "task_status": task_status,
        "dispatchable": bool(task_id and status == "active" and task_status == "active"),
        "action_hint": field_value(status_section.text if status_section else text, ("当前动作", "动作")) or "",
        "plan_id": plan_id or "",
        "task_id": task_id or "",
        "contract": contract_text,
        "plan_result": plan_text,
        "task_contract": task_text,
        "current_result": compact(current.text if current else ""),
        "accepted_receipts": relevant_receipts(text, task_id, task_text),
        "next_action": compact(next_action.text if next_action else ""),
        "blocker": compact(blockers.text if blockers else ""),
        "delivery": compact(delivery.text if delivery else ""),
        "learn": compact(learn.text if learn else ""),
        "contract_hash": stable_hash(contract_text),
        "plan_contract_hash": stable_hash(plan_text),
        "task_contract_hash": stable_hash(task_text),
    }
    return payload


def legacy_payload(task_dir: Path, plan_id: str | None, task_id: str | None) -> dict[str, object]:
    plan_id, task_id = normalized_ids(plan_id, task_id)
    sources = {name: read_text(task_dir / name) for name in LEGACY_SOURCE_NAMES}
    present = [name for name, text in sources.items() if text]
    if not present:
        raise ValueError("找不到 work.md 或可读取的 v2 工作文件")
    task_plan = sources["task_plan.md"]
    plan = find_identifier_section(task_plan, plan_id, source="旧版 task_plan.md")
    if plan_id and plan is None:
        raise ValueError(f"旧版工作文件找不到计划：{plan_id}")
    task = find_identifier_section(task_plan, task_id, source="旧版 task_plan.md")
    implementation = find_identifier_section(
        sources["implementation-plan.md"], task_id, source="旧版 implementation-plan.md"
    )
    if task_id and task is None and implementation is None:
        raise ValueError(f"旧版工作文件找不到任务：{task_id}")
    if plan_id and task_id and plan and task:
        validate_parent(plan, task, plan_id, task_id, source="旧版 task_plan.md")
    contract_sections = [
        section.text
        for section in sections(task_plan)
        if any(token in section.title for token in ("需求", "目标", "范围", "验收"))
    ][:3]
    contract_text = exact_contract(
        "\n\n".join(contract_sections) or task_plan,
        label="旧版目标契约",
    )
    plan_text = exact_contract(direct_section_text(plan), label="旧版计划结果")
    task_text = exact_contract(
        "\n\n".join(section.text for section in (task, implementation) if section),
        label="旧版任务契约",
    )
    progress = find_section(sources["progress.md"], ("Handoff", "Current", "当前", "下一步"))
    action_hint = action_from_legacy(task_plan)
    status = normalized_status(
        task_plan + "\n" + sources["progress.md"],
        default="active",
        prefer_frontmatter=True,
    )
    task_status = (
        normalized_status(
            task.text if task else implementation.text,
            default=status,
            names=("任务状态", "状态", "status"),
            label=f"旧版任务 {task_id} 状态",
        )
        if task or implementation
        else ""
    )
    payload: dict[str, object] = {
        "schema_version": SCHEMA_VERSION,
        "source": "legacy-v2-read-only",
        "source_paths": present,
        "status": status,
        "work_status": status,
        "task_status": task_status,
        "dispatchable": bool(task_id and status == "active" and task_status == "active"),
        "action_hint": action_hint,
        "plan_id": plan_id or "",
        "task_id": task_id or "",
        "contract": contract_text,
        "plan_result": plan_text,
        "task_contract": task_text,
        "current_result": compact(progress.text if progress else ""),
        "accepted_receipts": evidence_slice(sources["findings.md"], task_text),
        "next_action": compact(progress.text if progress else ""),
        "blocker": "",
        "delivery": "unknown",
        "learn": "",
        "contract_hash": stable_hash(contract_text),
        "plan_contract_hash": stable_hash(plan_text),
        "task_contract_hash": stable_hash(task_text),
        "legacy_note": (
            "旧版“验收交付”只映射为结果验真提示，不证明已经提交、发布或线上生效。"
            if action_hint == "结果验真"
            else "旧文件只读；首次规范写入 work.md 后，以 work.md 为唯一真源。"
        ),
    }
    return payload


def build_payload(
    task_dir: Path,
    plan_id: str | None,
    task_id: str | None,
    *,
    allow_missing: bool,
) -> dict[str, object]:
    work_exists = (task_dir / "work.md").is_file()
    legacy_exists = any((task_dir / name).is_file() for name in LEGACY_SOURCE_NAMES)
    if work_exists:
        payload = work_payload(task_dir, plan_id, task_id)
    elif legacy_exists:
        payload = legacy_payload(task_dir, plan_id, task_id)
    elif allow_missing:
        plan_id, task_id = normalized_ids(plan_id, task_id)
        payload = {
            "schema_version": SCHEMA_VERSION,
            "source": "missing",
            "source_paths": [],
            "status": "blocked",
            "work_status": "blocked",
            "task_status": "blocked",
            "dispatchable": False,
            "action_hint": "",
            "plan_id": plan_id or "",
            "task_id": task_id or "",
            "contract": "",
            "plan_result": "",
            "task_contract": "",
            "current_result": "",
            "accepted_receipts": "",
            "next_action": "",
            "blocker": "缺少 work.md 或可读取的旧版工作真源；禁止派发。",
            "delivery": "unknown",
            "learn": "",
            "contract_hash": stable_hash(""),
            "plan_contract_hash": stable_hash(""),
            "task_contract_hash": stable_hash(""),
        }
    else:
        raise ValueError("找不到 work.md 或可读取的 v2 工作文件")
    payload["capsule_hash"] = stable_hash(payload)
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
    if len(raw) > MAX_CAPSULE_BYTES:
        raise ValueError(f"capsule 超过安全字节上限：{MAX_CAPSULE_BYTES}")
    return payload


def render_markdown(payload: dict[str, object]) -> str:
    return "\n".join(
        (
            "# 任务胶囊",
            f"- 工作 / 任务状态：{payload['work_status']} / {payload['task_status'] or '-'}",
            f"- 可派发：{'是' if payload['dispatchable'] else '否'}",
            f"- 当前动作提示：{payload['action_hint'] or '未指定'}",
            f"- 计划 / 任务：{payload['plan_id'] or '-'} / {payload['task_id'] or '-'}",
            f"- 来源：{payload['source']}",
            f"- contract_hash：`{payload['contract_hash']}`",
            f"- plan_contract_hash：`{payload['plan_contract_hash']}`",
            f"- task_contract_hash：`{payload['task_contract_hash']}`",
            f"- capsule_hash：`{payload['capsule_hash']}`",
            "",
            "## 目标契约",
            str(payload["contract"]),
            "",
            "## 计划结果",
            str(payload["plan_result"]),
            "",
            "## 任务契约",
            str(payload["task_contract"]),
            "",
            "## 已接受回执",
            str(payload["accepted_receipts"]),
            "",
            "## 下一就绪责任 / 阻断",
            str(payload["next_action"]),
            str(payload["blocker"]),
        )
    ).rstrip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--task-dir", required=True)
    parser.add_argument("--plan")
    parser.add_argument("--task")
    parser.add_argument("--format", choices=("json", "markdown"), default="json")
    parser.add_argument("--allow-missing", action="store_true")
    args = parser.parse_args()
    try:
        payload = build_payload(
            Path(args.task_dir).expanduser().resolve(),
            args.plan,
            args.task,
            allow_missing=args.allow_missing,
        )
    except (OSError, ValueError) as exc:
        print(f"work_context 错误：{exc}", file=sys.stderr)
        return 2
    if args.format == "markdown":
        print(render_markdown(payload), end="")
    else:
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
