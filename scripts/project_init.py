#!/usr/bin/env python3
"""为项目初始化提供低成本兼容代际门与有界机器清单。"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tempfile
from pathlib import Path


PACKAGE = Path(__file__).resolve().parents[1]
STATE_RELATIVE = Path(".workflow/project.json")
STATE_SCHEMA = 1
COMPATIBILITY_GENERATION = 1
MAX_ENTRIES = 20_000
MAX_RESULTS_PER_GROUP = 40
IGNORED_DIRECTORIES = frozenset(
    {
        ".git",
        ".hg",
        ".next",
        ".next-dev",
        ".svn",
        ".claude/worktrees",
        ".codex/worktrees",
        ".worktrees",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
        ".tox",
        ".venv",
        "__pycache__",
        "build",
        "coverage",
        "data",
        "dist",
        "node_modules",
        "out",
        "plans/archive",
        "reports",
        "target",
        "tmp",
        "vendor",
    }
)
INSTRUCTION_NAMES = frozenset(
    {"AGENTS.md", "CLAUDE.md", "GEMINI.md", ".cursorrules", "copilot-instructions.md"}
)
TRUTH_NAMES = frozenset(
    {
        "TRUTH.md",
        "PRODUCT.md",
        "README.md",
        "CONTRIBUTING.md",
        "DESIGN.md",
        "SECURITY.md",
        "architecture.md",
        "deployment_environment.md",
        "module.md",
    }
)
BUILD_NAMES = frozenset(
    {
        "package.json",
        "pyproject.toml",
        "requirements.txt",
        "requirements-dev.txt",
        "go.mod",
        "Cargo.toml",
        "Gemfile",
        "pom.xml",
        "build.gradle",
        "Makefile",
        "Taskfile.yml",
        "justfile",
        "Dockerfile",
        "docker-compose.yml",
    }
)
SENSITIVE_NAMES = frozenset({".env", ".npmrc", ".pypirc", "credentials.json", "service-account.json"})
VERSION_PATTERN = re.compile(r"(?m)^version:\s*(\S+)\s*$")


class ProjectStateError(ValueError):
    """项目兼容状态不可信。"""


def workflow_version() -> str:
    text = (PACKAGE / "SKILL.md").read_text(encoding="utf-8")
    match = VERSION_PATTERN.search(text)
    if match is None:
        raise ProjectStateError("SKILL.md 缺少 workflow 版本")
    return match.group(1)


def project_root(raw: str) -> Path:
    root = Path(raw).expanduser().resolve()
    if not root.is_dir():
        raise ProjectStateError(f"项目目录不存在：{raw}")
    return root


def safe_relative_file(root: Path, raw: str, label: str) -> tuple[str, Path]:
    relative = Path(raw)
    if relative.is_absolute() or not relative.parts or ".." in relative.parts:
        raise ProjectStateError(f"{label} 必须是项目内相对路径")
    candidate = root / relative
    try:
        candidate.resolve().relative_to(root)
    except ValueError as exc:
        raise ProjectStateError(f"{label} 越出项目边界") from exc
    if not candidate.is_file() or candidate.is_symlink():
        raise ProjectStateError(f"{label} 不是项目内普通文件：{relative.as_posix()}")
    return relative.as_posix(), candidate


def emit(payload: dict[str, object]) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))


def read_state(root: Path) -> dict[str, object] | None:
    path = root / STATE_RELATIVE
    state_directory = path.parent
    if state_directory.is_symlink():
        raise ProjectStateError(f"{state_directory.relative_to(root).as_posix()} 不得是符号链接")
    if path.is_symlink():
        raise ProjectStateError(f"{STATE_RELATIVE.as_posix()} 不得是符号链接")
    if not path.exists():
        return None
    if not path.is_file():
        raise ProjectStateError(f"{STATE_RELATIVE.as_posix()} 必须是普通文件")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ProjectStateError(f"{STATE_RELATIVE.as_posix()} 无法解析：{exc}") from exc
    if not isinstance(value, dict):
        raise ProjectStateError(f"{STATE_RELATIVE.as_posix()} 必须是 JSON object")
    expected = {"schema", "compatibility_generation", "reviewed_with", "entrypoint", "evidence"}
    if set(value) != expected:
        raise ProjectStateError(
            f"{STATE_RELATIVE.as_posix()} 字段必须精确为：" + ", ".join(sorted(expected))
        )
    if value["schema"] != STATE_SCHEMA:
        raise ProjectStateError(f"不支持的项目状态 schema：{value['schema']}")
    generation = value["compatibility_generation"]
    if not isinstance(generation, int) or isinstance(generation, bool) or generation < 0:
        raise ProjectStateError("compatibility_generation 必须是非负整数")
    for field in ("reviewed_with", "entrypoint", "evidence"):
        if not isinstance(value[field], str) or not value[field].strip():
            raise ProjectStateError(f"{field} 必须是非空字符串")
    return value


def check(root: Path) -> int:
    read_scope = [STATE_RELATIVE.as_posix()]
    state = read_state(root)
    if state is None:
        emit(
            {
                "status": "needs-initialization",
                "compatibility_generation": COMPATIBILITY_GENERATION,
                "read_scope": read_scope,
            }
        )
        return 10

    generation = int(state["compatibility_generation"])
    if generation > COMPATIBILITY_GENERATION:
        raise ProjectStateError(
            "项目兼容代际高于当前 workflow；请先更新 workflow，禁止降级判断"
        )
    if generation < COMPATIBILITY_GENERATION:
        emit(
            {
                "status": "needs-upgrade",
                "compatibility_generation": generation,
                "required_generation": COMPATIBILITY_GENERATION,
                "read_scope": read_scope,
            }
        )
        return 10

    missing: list[str] = []
    for field in ("entrypoint", "evidence"):
        relative = str(state[field])
        read_scope.append(relative)
        try:
            safe_relative_file(root, relative, field)
        except ProjectStateError:
            missing.append(relative)
    if missing:
        emit(
            {
                "status": "needs-review",
                "reason": "兼容凭据指向的项目 owner 不再存在",
                "missing": missing,
                "read_scope": read_scope,
            }
        )
        return 10

    emit(
        {
            "status": "current",
            "compatibility_generation": generation,
            "reviewed_with": state["reviewed_with"],
            "entrypoint": state["entrypoint"],
            "evidence": state["evidence"],
            "read_scope": read_scope,
        }
    )
    return 0


def record(root: Path, entrypoint: str, evidence: str) -> int:
    entrypoint_relative, _ = safe_relative_file(root, entrypoint, "entrypoint")
    evidence_relative, _ = safe_relative_file(root, evidence, "evidence")
    document = {
        "schema": STATE_SCHEMA,
        "compatibility_generation": COMPATIBILITY_GENERATION,
        "reviewed_with": workflow_version(),
        "entrypoint": entrypoint_relative,
        "evidence": evidence_relative,
    }
    destination = root / STATE_RELATIVE
    if destination.parent.is_symlink():
        raise ProjectStateError(
            f"{destination.parent.relative_to(root).as_posix()} 不得是符号链接"
        )
    destination.parent.mkdir(parents=True, exist_ok=True)
    handle, raw_temp = tempfile.mkstemp(prefix=".project-", suffix=".json", dir=destination.parent)
    temp = Path(raw_temp)
    try:
        with os.fdopen(handle, "w", encoding="utf-8", newline="\n") as output:
            json.dump(document, output, ensure_ascii=False, indent=2)
            output.write("\n")
            output.flush()
            os.fsync(output.fileno())
        os.replace(temp, destination)
    except Exception:
        temp.unlink(missing_ok=True)
        raise
    emit({"status": "recorded", "state": STATE_RELATIVE.as_posix(), **document})
    return 0


def ignored_directory(relative: str, name: str) -> bool:
    return name in IGNORED_DIRECTORIES or relative in IGNORED_DIRECTORIES


def project_files(root: Path) -> list[str]:
    found: list[str] = []
    stack = [root]
    visited = 0
    while stack:
        directory = stack.pop()
        try:
            entries = sorted(os.scandir(directory), key=lambda item: item.name, reverse=True)
        except OSError:
            continue
        for entry in entries:
            visited += 1
            if visited > MAX_ENTRIES:
                raise ProjectStateError(
                    f"项目清单超过安全上限 {MAX_ENTRIES} 个条目；请先指定更小项目根"
                )
            path = Path(entry.path)
            relative = path.relative_to(root).as_posix()
            try:
                if entry.is_symlink():
                    continue
                if entry.is_dir(follow_symlinks=False):
                    if not ignored_directory(relative, entry.name):
                        stack.append(path)
                elif entry.is_file(follow_symlinks=False):
                    found.append(relative)
            except OSError:
                continue
    return sorted(found)


def limited(values: list[str]) -> list[str]:
    return sorted(set(values))[:MAX_RESULTS_PER_GROUP]


def inventory(root: Path) -> int:
    files = project_files(root)
    instructions: list[str] = []
    truths: list[str] = []
    builds: list[str] = []
    controls: list[str] = []
    validations: list[str] = []
    deliveries: list[str] = []
    ai_assets: list[str] = []
    sensitive: list[str] = []
    for relative in files:
        path = Path(relative)
        name = path.name
        lower = relative.lower()
        parts = {part.lower() for part in path.parts}
        if name in INSTRUCTION_NAMES or lower == ".github/copilot-instructions.md":
            instructions.append(relative)
        if name in TRUTH_NAMES or lower.startswith("docs/truth/"):
            truths.append(relative)
        if name in BUILD_NAMES:
            builds.append(relative)
        if relative in {"work.md", "plans/index.md"} or lower.endswith("/work.md"):
            controls.append(relative)
        if (
            "tests" in parts
            or "test" in parts
            or lower.startswith(".github/workflows/")
            or name in {"pytest.ini", "tox.ini", "vitest.config.ts", "vitest.config.js"}
        ):
            validations.append(relative)
        if (
            "deploy" in parts
            or "release" in lower
            or lower.startswith(".github/workflows/")
            or name in {"Dockerfile", "docker-compose.yml"}
        ):
            deliveries.append(relative)
        if parts.intersection({"ai", "agents", "evals", "evaluations", "prompts", "models"}) or re.search(
            r"(?i)(?:^|[_.-])(assistant|eval|llm|model|prompt)(?:[_.-]|$)", lower
        ):
            ai_assets.append(relative)
        if name in SENSITIVE_NAMES or re.search(r"(?i)(credential|service.?account|secret).+\.json$", name):
            sensitive.append(relative)
    emit(
        {
            "status": "inventory",
            "project": root.name,
            "file_count": len(files),
            "instructions": limited(instructions),
            "truth_candidates": limited(truths),
            "build_candidates": limited(builds),
            "control_candidates": limited(controls),
            "validation_candidates": limited(validations),
            "delivery_candidates": limited(deliveries),
            "ai_candidates": limited(ai_assets),
            "sensitive_path_candidates": limited(sensitive),
            "candidate_counts": {
                "instructions": len(set(instructions)),
                "truth": len(set(truths)),
                "build": len(set(builds)),
                "control": len(set(controls)),
                "validation": len(set(validations)),
                "delivery": len(set(deliveries)),
                "ai": len(set(ai_assets)),
                "sensitive": len(set(sensitive)),
            },
            "excluded_directories": sorted(IGNORED_DIRECTORIES),
            "truncated_groups": any(
                len(set(group)) > MAX_RESULTS_PER_GROUP
                for group in (
                    instructions,
                    truths,
                    builds,
                    controls,
                    validations,
                    deliveries,
                    ai_assets,
                    sensitive,
                )
            ),
        }
    )
    return 0


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description=__doc__)
    commands = root.add_subparsers(dest="command", required=True)
    for name in ("check", "inventory"):
        command = commands.add_parser(name)
        command.add_argument("--project", default=".")
    record_command = commands.add_parser("record")
    record_command.add_argument("--project", default=".")
    record_command.add_argument("--entrypoint", required=True)
    record_command.add_argument("--evidence", required=True)
    return root


def main(argv: list[str] | None = None) -> int:
    arguments = parser().parse_args(argv)
    try:
        root = project_root(arguments.project)
        if arguments.command == "check":
            return check(root)
        if arguments.command == "inventory":
            return inventory(root)
        return record(root, arguments.entrypoint, arguments.evidence)
    except ProjectStateError as exc:
        emit({"status": "invalid", "error": str(exc)})
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

