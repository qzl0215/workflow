#!/usr/bin/env python3
"""从本机 Claude Code 会话记录观察 workflow 的真实加载与路由。

只读。输出的是可回到原文核对的线索，不是结论：读取以“参考路径出现在未报错的工具输入”为准，
不证明模型读完或采用；返工与失败信号靠关键词初筛，必须人工复核原文。
"""

from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import re
import sys


PACKAGE = Path(__file__).resolve().parents[1]
SKILL = "workflow"
EARLY_CALLS = 5
LATE_CALLS = 30
LONG_SESSION_CALLS = 30
STREAK = 3
SKILL_BASE = re.compile(r"Base directory for this skill: (\S+)")
REFERENCE = re.compile(r"skills/" + SKILL + r"/((?:references|templates)/[\w.-]+\.(?:md|html))")
WRAPPER = re.compile(r"<(system-reminder|local-command-caveat|local-command-stdout)>.*?</\1>", re.S)
COMMAND_ARGS = re.compile(r"<command-args>(.*?)</command-args>", re.S)
NOT_USER = ("<task-notification>", "<artifact-content-authored-by-others", "(Re-invocation")
# 宿主超时、用户拒绝、钩子拦截和并行连带取消不是一次真实的失败尝试。
HOST_NOISE = re.compile(
    r"hook did not respond|hook error|doesn't want to proceed|was rejected|"
    r"requested permissions|haven't granted|[Ii]nterrupted by user|[Cc]ancelled|sibling tool call", re.S)
FRICTION = {
    "rework": re.compile(r"过度简化|不够深|没理解|跑偏|不是我想要|不是我要的|做大了|我说的是|理解错|重新来"),
    "still_failing": re.compile(r"还是不行|还是没|还是报|又错|又失败|没生效|没有生效|怎么还|还是一样|为什么又|没解决"),
}
EXTERNAL_WRITE = re.compile(
    r"\bgit push\b|\bgh pr (?:create|merge)\b|\bgh release create\b|publish\.py|"
    r"\bsystemctl (?:restart|reload)\b|\bdocker compose up\b|\bpm2 (?:restart|reload)\b")


def text_of(content: object) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(part.get("text", "") for part in content
                         if isinstance(part, dict) and part.get("type") == "text")
    return ""


def parts_of(event: dict, kind: str) -> list[dict]:
    content = event.get("message", {}).get("content")
    if not isinstance(content, list):
        return []
    return [part for part in content if isinstance(part, dict) and part.get("type") == kind]


def user_text(event: dict) -> str:
    """用户亲手写的文字；工具回执、技能正文、宿主通知和压缩摘要返回空串。"""
    if event.get("type") != "user" or event.get("isMeta") or event.get("isCompactSummary"):
        return ""
    if parts_of(event, "tool_result"):
        return ""
    text = text_of(event.get("message", {}).get("content"))
    if SKILL_BASE.search(text[:400]):
        return ""
    command = COMMAND_ARGS.search(text)
    if command:
        return command.group(1).strip()
    text = WRAPPER.sub("", text).strip()
    return "" if text.startswith(NOT_USER) or text.startswith("<command-") else text


def read_events(path: Path, since: str = "", until: str = "") -> list[tuple[int, dict]]:
    events = []
    with path.open(encoding="utf-8", errors="replace") as handle:
        for number, line in enumerate(handle, 1):
            try:
                event = json.loads(line)
            except ValueError:
                continue
            if not isinstance(event, dict) or event.get("isSidechain"):
                continue
            stamp = event.get("timestamp", "")
            if (since and stamp < since) or (until and stamp >= until):
                continue
            events.append((number, event))
    return events


def observe_session(path: Path, since: str = "", until: str = "") -> dict | None:
    events = read_events(path, since, until)
    session = {
        "session": path.stem, "path": str(path), "user_messages": 0, "tool_calls": 0,
        "skills": [], "reference_reads": [], "friction": [], "error_streaks": [],
        "external_writes": [], "compactions": 0, "skill_reattached_after_compaction": False,
    }
    pending: dict[str, dict] = {}
    streak: list[dict] = []
    calls_since_load: int | None = None

    def close_streak() -> None:
        if len(streak) >= STREAK:
            inputs = [item["input"] for item in streak]
            session["error_streaks"].append({
                "line": streak[0]["line"], "length": len(streak),
                "repeated_inputs": len(inputs) - len(set(inputs)),
                "tools": sorted({item["tool"] for item in streak}), "last_error": streak[-1]["error"],
            })
        streak.clear()

    for line, event in events:
        if event.get("subtype") == "compact_boundary" or event.get("isCompactSummary"):
            session["compactions"] += 1
        if (event.get("attachment") or {}).get("type") == "invoked_skills" and session["compactions"]:
            session["skill_reattached_after_compaction"] = True
        if event.get("type") == "assistant":
            for call in parts_of(event, "tool_use"):
                session["tool_calls"] += 1
                if calls_since_load is not None:
                    calls_since_load += 1
                payload = json.dumps(call.get("input", {}), ensure_ascii=False, sort_keys=True)
                command = call.get("input", {}).get("command", "") if call.get("name") == "Bash" else ""
                pending[call.get("id", "")] = {
                    "line": line, "tool": call.get("name", "?"), "input": payload,
                    "references": sorted(set(REFERENCE.findall(payload))), "calls_since_load": calls_since_load,
                    "external_write": bool(isinstance(command, str) and EXTERNAL_WRITE.search(command)),
                }
            continue
        if event.get("type") != "user":
            continue
        loaded = SKILL_BASE.search(text_of(event.get("message", {}).get("content"))[:400])
        if loaded and not parts_of(event, "tool_result"):
            name = loaded.group(1).rstrip("/").rsplit("/", 1)[-1]
            session["skills"].append({"name": name, "line": line})
            if name == SKILL:
                calls_since_load = 0
        for result in parts_of(event, "tool_result"):
            call = pending.pop(result.get("tool_use_id", ""), None)
            if call is None:
                continue
            error = text_of(result.get("content")) or str(result.get("content", ""))
            if result.get("is_error"):
                if not HOST_NOISE.search(error):
                    streak.append({**call, "error": " ".join(error.split())[:160]})
                continue
            close_streak()
            for reference in call["references"]:
                session["reference_reads"].append(
                    {"reference": reference, "line": call["line"], "calls_since_load": call["calls_since_load"]})
            if call["external_write"]:
                session["external_writes"].append({"line": call["line"]})
        text = user_text(event)
        if text:
            session["user_messages"] += 1
            for kind, pattern in FRICTION.items():
                if pattern.search(text):
                    session["friction"].append({"kind": kind, "line": line, "text": " ".join(text.split())[:160]})
    close_streak()
    if not session["user_messages"]:
        return None
    session["loaded"] = any(item["name"] == SKILL for item in session["skills"])
    return session


def package_references(package: Path = PACKAGE) -> list[str]:
    return sorted(str(path.relative_to(package)) for folder in ("references", "templates")
                  for path in (package / folder).iterdir() if path.suffix in {".md", ".html"})


def summarize(sessions: list[dict], references: list[str]) -> dict:
    loaded = [item for item in sessions if item["loaded"]]
    rows = {name: {"sessions": 0, "reads": 0, "early": 0, "late": 0} for name in references}
    for item in loaded:
        seen = set()
        for read in item["reference_reads"]:
            row = rows.setdefault(read["reference"], {"sessions": 0, "reads": 0, "early": 0, "late": 0})
            row["reads"] += 1
            calls = read["calls_since_load"]
            row["early"] += calls is not None and calls <= EARLY_CALLS
            row["late"] += calls is not None and calls > LATE_CALLS
            if read["reference"] not in seen:
                seen.add(read["reference"])
                row["sessions"] += 1
    skills = Counter(name for item in sessions for name in {skill["name"] for skill in item["skills"]})
    compacted = [item for item in loaded if item["compactions"]]
    tool_counts = sorted(item["tool_calls"] for item in loaded)
    return {
        "sessions": len(sessions), "user_messages": sum(item["user_messages"] for item in sessions),
        "loaded_sessions": len(loaded),
        "loaded_median_tool_calls": tool_counts[len(tool_counts) // 2] if tool_counts else 0,
        "loaded_sessions_without_reference": sum(not item["reference_reads"] for item in loaded),
        "unloaded_long_sessions": sum(not item["loaded"] and item["tool_calls"] >= LONG_SESSION_CALLS for item in sessions),
        "references": rows,
        "silent_references": sorted(name for name in references if not rows[name]["reads"]),
        "skills_by_sessions": dict(skills.most_common()),
        "friction_sessions": {kind: sum(any(hit["kind"] == kind for hit in item["friction"]) for item in loaded)
                              for kind in FRICTION},
        "error_streak_sessions": sum(bool(item["error_streaks"]) for item in loaded),
        "external_write_sessions": sum(bool(item["external_writes"]) for item in loaded),
        "compacted_sessions": len(compacted),
        "compacted_with_skill_reattached": sum(item["skill_reattached_after_compaction"] for item in compacted),
    }


def excerpt(path: Path, line: int, radius: int) -> str:
    """把指定行前后的对话压成短记录，供人工复核线索。"""
    rows = []
    for number, event in read_events(path):
        if abs(number - line) > radius:
            continue
        stamp = event.get("timestamp", "")[:16]
        if event.get("type") == "assistant":
            for part in event.get("message", {}).get("content", []) or []:
                if not isinstance(part, dict):
                    continue
                if part.get("type") == "text" and part.get("text", "").strip():
                    rows.append(f"{number} {stamp} 助手: {' '.join(part['text'].split())[:400]}")
                elif part.get("type") == "tool_use":
                    payload = json.dumps(part.get("input", {}), ensure_ascii=False)
                    rows.append(f"{number} {stamp} 工具 {part.get('name')}: {payload[:200]}")
        elif event.get("type") == "user":
            for result in parts_of(event, "tool_result"):
                body = " ".join((text_of(result.get("content")) or str(result.get("content", ""))).split())
                rows.append(f"{number} {stamp} {'报错' if result.get('is_error') else '回执'}: {body[:200]}")
            text = user_text(event)
            if text:
                rows.append(f"{number} {stamp} 用户: {' '.join(text.split())[:600]}")
    return "\n".join(rows)


def render(summary: dict) -> str:
    lines = [
        f"会话 {summary['sessions']}，用户消息 {summary['user_messages']}；加载 {SKILL} 的会话 {summary['loaded_sessions']}"
        f"（工具调用中位数 {summary['loaded_median_tool_calls']}，零参考 {summary['loaded_sessions_without_reference']}）",
        f"未加载但不短（≥{LONG_SESSION_CALLS} 次工具调用）的会话 {summary['unloaded_long_sessions']}",
        f"参考读取：会话数 / 次数 / 加载后≤{EARLY_CALLS}步 / >{LATE_CALLS}步",
    ]
    for name, row in sorted(summary["references"].items(), key=lambda pair: (-pair[1]["reads"], pair[0])):
        if row["reads"]:
            lines.append(f"  {name:32s} {row['sessions']:4d} / {row['reads']:4d} / {row['early']:4d} / {row['late']:4d}")
    lines.append("零读取参考：" + ("、".join(summary["silent_references"]) or "无"))
    lines.append("各技能出现的会话数：" + "，".join(f"{name} {count}" for name, count in list(summary["skills_by_sessions"].items())[:15]))
    lines.append(
        f"待人工复核的线索（仅 {SKILL} 会话）：返工措辞 {summary['friction_sessions']['rework']}，"
        f"仍失败措辞 {summary['friction_sessions']['still_failing']}，连续 {STREAK}+ 次真实报错 {summary['error_streak_sessions']}，"
        f"外部写入命令 {summary['external_write_sessions']}")
    lines.append(f"压缩过的会话 {summary['compacted_sessions']}，其中宿主重新附带技能 {summary['compacted_with_skill_reattached']}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--projects", type=Path, default=Path.home() / ".claude/projects", help="Claude Code 会话记录目录")
    parser.add_argument("--since", default="", help="起始时间（ISO，含）")
    parser.add_argument("--until", default="", help="结束时间（ISO，不含）")
    parser.add_argument("--output", type=Path, help="逐会话明细 JSON；含会话原文片段，必须在仓库外")
    parser.add_argument("--excerpt", type=Path, help="改为打印该会话文件指定行附近的短记录")
    parser.add_argument("--line", type=int, default=1)
    parser.add_argument("--radius", type=int, default=15)
    args = parser.parse_args(argv)
    if args.excerpt:
        print(excerpt(args.excerpt, args.line, args.radius))
        return 0
    if args.output and args.output.resolve().is_relative_to(PACKAGE):
        parser.error("明细含会话原文，必须写在仓库外")
    sessions = [item for path in sorted(args.projects.glob("*/*.jsonl"))
                if (item := observe_session(path, args.since, args.until))]
    summary = summarize(sessions, package_references())
    if args.output:
        args.output.write_text(json.dumps({"since": args.since, "until": args.until, "summary": summary,
                                           "sessions": sessions}, ensure_ascii=False, indent=1), encoding="utf-8")
    print(render(summary))
    return 0


if __name__ == "__main__":
    sys.exit(main())
