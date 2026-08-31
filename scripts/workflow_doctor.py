#!/usr/bin/env python3
"""对 Workflow 3.x 源码树或精简运行时做失败关闭检查。"""

from __future__ import annotations

import os
import re
import stat
import sys
from pathlib import Path
from urllib.parse import unquote, urlsplit

import install


REQUIRED_REFERENCES = (
    "frame.md",
    "research.md",
    "experience.md",
    "grill.md",
    "plan.md",
    "orchestrate.md",
    "execute.md",
    "recover.md",
    "prove.md",
    "deliver.md",
    "learn.md",
    "initialize.md",
)
REQUIRED_TEMPLATES = ("work.md",)
REQUIRED_RUNTIME_SCRIPTS = (
    "install.py",
    "safe_merge.py",
    "work_context.py",
    "workflow_doctor.py",
    "project_init.py",
)
EXPECTED_RUNTIME_FILES = frozenset(
    {
        "SKILL.md",
        "LICENSE",
        "NOTICE.md",
        *(f"references/{name}" for name in REQUIRED_REFERENCES),
        *(f"templates/{name}" for name in REQUIRED_TEMPLATES),
        *(f"scripts/{name}" for name in REQUIRED_RUNTIME_SCRIPTS),
    }
)

MAX_ENTRYPOINT_LINES = 150
MAX_ENTRYPOINT_CHARS = 10_000
MAX_REFERENCE_LINES = 1_200
MAX_REFERENCE_FILE_LINES = 250
MAX_SOURCE_BYTES = 8 * 1024 * 1024
MAX_TEXT_FILE_BYTES = 2 * 1024 * 1024
CONFLICT_MARKERS = ("<<<<<<<", "=======", ">>>>>>>")
MARKDOWN_LINK = re.compile(r"\[[^\]]*\]\((?P<target>[^)]+)\)")
HTML_LINK = re.compile(r"(?:href|src)\s*=\s*['\"](?P<target>[^'\"]+)['\"]", re.I)
SECRET_ASSIGNMENT = re.compile(
    r"(?i)(?:api[_-]?key|client[_-]?secret|password|access[_-]?token)"
    r"\s*[:=]\s*['\"]?(?!<|\{|\[|\$)[^\s'\"]{8,}"
)
MACHINE_PATH = re.compile(
    r"(?:/(?:Users|home)/[^\s`]+|[A-Za-z]:\\Users\\[^\\\s`]+)"
)
TEXT_NAMES = frozenset({"SKILL.md", "LICENSE"})
TEXT_SUFFIXES = frozenset({".md", ".html", ".json", ".py"})
IGNORED_CONTROL_NAMES = frozenset({".git"})
GENERATED_NAMES = frozenset({".DS_Store", "Thumbs.db", "desktop.ini", ".pytest_cache", "__pycache__"})


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def relative(path: Path, package: Path) -> str:
    return path.relative_to(package).as_posix()


def all_entries(package: Path) -> list[Path]:
    """列出控制目录之外的条目，不跟随符号链接。"""

    found: list[Path] = []

    def visit(directory: Path) -> None:
        try:
            entries = sorted(os.scandir(directory), key=lambda entry: entry.name)
        except OSError:
            return
        for entry in entries:
            if entry.name in IGNORED_CONTROL_NAMES and directory == package:
                continue
            path = Path(entry.path)
            found.append(path)
            try:
                mode = entry.stat(follow_symlinks=False).st_mode
            except OSError:
                continue
            if stat.S_ISDIR(mode) and not entry.is_symlink():
                visit(path)

    visit(package)
    return found


def local_link_target(raw: str) -> str | None:
    value = raw.strip()
    if value.startswith("<") and ">" in value:
        value = value[1 : value.index(">")]
    elif " " in value:
        value = value.split(" ", 1)[0]
    parsed = urlsplit(value)
    if parsed.scheme or parsed.netloc or not parsed.path:
        return None
    return unquote(parsed.path)


def link_errors(package: Path, text_files: list[Path]) -> list[str]:
    errors: list[str] = []
    root = package.resolve()
    for path in text_files:
        if path.suffix.lower() not in {".md", ".html"} and path.name != "SKILL.md":
            continue
        try:
            text = read_text(path)
        except (OSError, UnicodeError):
            continue
        patterns = [MARKDOWN_LINK]
        if path.suffix.lower() == ".html":
            patterns.append(HTML_LINK)
        for pattern in patterns:
            for match in pattern.finditer(text):
                target = local_link_target(match.group("target"))
                if target is None:
                    continue
                candidate = (path.parent / target).resolve()
                try:
                    candidate.relative_to(root)
                except ValueError:
                    errors.append(f"{relative(path, package)}: 本地链接越出包边界：{target}")
                    continue
                if not candidate.exists():
                    errors.append(f"{relative(path, package)}: 本地链接不存在：{target}")
    return errors


def inspect_package(package: Path) -> tuple[list[str], list[str]]:
    package = package.resolve()
    errors: list[str] = []
    warnings: list[str] = []

    if not package.is_dir():
        return [f"{package}: 包目录不存在"], warnings

    entries = all_entries(package)
    for path in entries:
        rel = relative(path, package)
        name_parts = set(path.relative_to(package).parts)
        try:
            mode = path.lstat().st_mode
        except OSError as exc:
            errors.append(f"{rel}: 无法检查文件类型：{exc}")
            continue
        if path.name in GENERATED_NAMES or name_parts.intersection(GENERATED_NAMES):
            errors.append(f"{rel}: 生成缓存或系统杂项不得进入包")
        if stat.S_ISLNK(mode):
            errors.append(f"{rel}: 符号链接不得进入可移植包")
        elif not (stat.S_ISREG(mode) or stat.S_ISDIR(mode)):
            errors.append(f"{rel}: 只允许普通文件和目录")

    try:
        targets, source_only = install.payload_spec(package)
    except (OSError, UnicodeError, ValueError) as exc:
        errors.append(str(exc))
        return sorted(set(errors)), warnings

    runtime_files = targets - {install.RUNTIME_MANIFEST_NAME}
    if runtime_files != EXPECTED_RUNTIME_FILES:
        missing = sorted(EXPECTED_RUNTIME_FILES - runtime_files)
        extras = sorted(runtime_files - EXPECTED_RUNTIME_FILES)
        if missing:
            errors.append("runtime manifest 缺少 3.0 文件：" + ", ".join(missing))
        if extras:
            errors.append("runtime manifest 声明了非 3.0 文件：" + ", ".join(extras))

    actual_files = install.package_files(package)
    present_source = source_only & actual_files
    if present_source and present_source != source_only:
        errors.append(
            "源码树的 source_only 不完整；缺少："
            + ", ".join(sorted(source_only - present_source))
        )
    full_source = bool(source_only) and present_source == source_only
    errors.extend(
        install.runtime_tree_errors(
            package,
            targets,
            allowed_optional=source_only if full_source else frozenset(),
            allow_checkout_metadata=True,
        )
    )

    skill_files = sorted(
        path
        for path in package.rglob("SKILL.md")
        if ".git" not in path.relative_to(package).parts
    )
    expected_skill = package / "SKILL.md"
    if skill_files != [expected_skill]:
        rendered = ", ".join(relative(path, package) for path in skill_files) or "无"
        errors.append(f"必须且只能有根 SKILL.md；当前：{rendered}")

    reference_dir = package / "references"
    actual_references = {
        path.name for path in reference_dir.glob("*.md") if path.is_file() and not path.is_symlink()
    }
    if actual_references != set(REQUIRED_REFERENCES):
        missing = sorted(set(REQUIRED_REFERENCES) - actual_references)
        extras = sorted(actual_references - set(REQUIRED_REFERENCES))
        if missing:
            errors.append("缺少 3.0 reference：" + ", ".join(missing))
        if extras:
            errors.append("存在未归属 reference：" + ", ".join(extras))

    template_dir = package / "templates"
    actual_templates = {
        path.name for path in template_dir.glob("*.md") if path.is_file() and not path.is_symlink()
    }
    if actual_templates != set(REQUIRED_TEMPLATES):
        missing = sorted(set(REQUIRED_TEMPLATES) - actual_templates)
        extras = sorted(actual_templates - set(REQUIRED_TEMPLATES))
        if missing:
            errors.append("缺少 3.0 模板：" + ", ".join(missing))
        if extras:
            errors.append("存在重复状态模板：" + ", ".join(extras))

    declared = targets | (source_only if full_source else frozenset())
    text_files: list[Path] = []
    source_bytes = 0
    for rel in sorted(declared):
        path = package / rel
        if not path.is_file() or path.is_symlink():
            continue
        size = path.stat().st_size
        source_bytes += size
        if size > MAX_TEXT_FILE_BYTES:
            errors.append(f"{rel}: 单文件超过安全上限 {MAX_TEXT_FILE_BYTES} bytes")
        if path.name not in TEXT_NAMES and path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        try:
            text = read_text(path)
        except UnicodeError:
            errors.append(f"{rel}: 文本文件不是有效 UTF-8")
            continue
        except OSError as exc:
            errors.append(f"{rel}: 无法读取文本：{exc}")
            continue
        text_files.append(path)
        if "\x00" in text:
            errors.append(f"{rel}: 文本文件包含 NUL 字节")
        human_readable = path.suffix.lower() in {".md", ".html"} or path.name in TEXT_NAMES
        if human_readable:
            for marker in CONFLICT_MARKERS:
                if marker in text:
                    errors.append(f"{rel}: 残留冲突标记 {marker}")
            if SECRET_ASSIGNMENT.search(text):
                errors.append(f"{rel}: 疑似包含凭据赋值")
            if MACHINE_PATH.search(text):
                errors.append(f"{rel}: 包含机器专属绝对路径")

    if full_source and source_bytes > MAX_SOURCE_BYTES:
        warnings.append(f"完整源码共 {source_bytes} bytes，超过观察线 {MAX_SOURCE_BYTES}")

    skill = package / "SKILL.md"
    if skill.is_file():
        try:
            skill_text = read_text(skill)
        except (OSError, UnicodeError):
            skill_text = ""
        if len(skill_text.splitlines()) > MAX_ENTRYPOINT_LINES:
            errors.append(f"SKILL.md: 超过 {MAX_ENTRYPOINT_LINES} 行")
        if len(skill_text) > MAX_ENTRYPOINT_CHARS:
            errors.append(f"SKILL.md: 超过 {MAX_ENTRYPOINT_CHARS} 字符")
        metadata = install.skill_metadata(skill)
        if metadata.get("name") != "workflow":
            errors.append("SKILL.md: frontmatter name 必须是 workflow")
        for name in REQUIRED_REFERENCES:
            if f"references/{name}" not in skill_text:
                errors.append(f"SKILL.md: 未路由 references/{name}")

    reference_lines = 0
    for name in REQUIRED_REFERENCES:
        path = reference_dir / name
        if not path.is_file():
            continue
        try:
            lines = len(read_text(path).splitlines())
        except (OSError, UnicodeError):
            continue
        reference_lines += lines
        if lines > MAX_REFERENCE_FILE_LINES:
            errors.append(f"references/{name}: 超过 {MAX_REFERENCE_FILE_LINES} 行")
    if reference_lines > MAX_REFERENCE_LINES:
        errors.append(f"references: 总计 {reference_lines} 行，超过 {MAX_REFERENCE_LINES} 行")

    errors.extend(link_errors(package, text_files))
    return sorted(set(errors)), sorted(set(warnings))


def report(errors: list[str], warnings: list[str]) -> None:
    if errors:
        print("WORKFLOW DOCTOR ERRORS:")
        for item in errors:
            print(f"- {item}")
    if warnings:
        print("WORKFLOW DOCTOR WARNINGS:")
        for item in warnings:
            print(f"- {item}")
    if not errors:
        suffix = "（有警告）" if warnings else ""
        print(f"workflow_doctor: OK{suffix}")


def main(argv: list[str] | None = None) -> int:
    arguments = list(sys.argv[1:] if argv is None else argv)
    if len(arguments) > 1:
        print("usage: workflow_doctor.py [PACKAGE]", file=sys.stderr)
        return 2
    package = Path(arguments[0]) if arguments else Path(__file__).resolve().parents[1]
    errors, warnings = inspect_package(package)
    report(errors, warnings)
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
