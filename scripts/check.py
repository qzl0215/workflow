#!/usr/bin/env python3
"""Check only the mechanical integrity of a workflow runtime package."""

from __future__ import annotations

import html
import os
import re
import sys
from pathlib import Path
from typing import Optional, Tuple
from urllib.parse import unquote, urlsplit


RUNTIME_DIRECTORIES = ("references", "templates")
IGNORED_NAMES = frozenset({".DS_Store", "Thumbs.db", "desktop.ini"})
IGNORED_PARTS = frozenset({".git", "__pycache__"})
IGNORED_SUFFIXES = frozenset({".pyc", ".pyo"})
MARKDOWN_LINK = re.compile(r"!?\[[^\]]*\]\((?P<target><[^>]+>|[^)]+)\)")
RUNTIME_PATH = re.compile(
    r"(?<![A-Za-z0-9_./-])(?P<target>(?:references|templates)/[A-Za-z0-9._/-]+\.md)"
)
FRONTMATTER_KEY = re.compile(r"^[A-Za-z][A-Za-z0-9_-]*\s*:\s*(.*?)\s*$")
MACHINE_PATH = re.compile(
    r"(?:/(?:Users|home|opt)/[A-Za-z0-9._-]+|[A-Za-z]:\\Users\\[^\\\s`]+|~/\.(?:codex|claude)/)"
)
SENSITIVE_ASSIGNMENT = re.compile(
    r"(?i)(?:api[_-]?key|secret|password|access[_-]?token)\s*[:=]\s*['\"]?[^\s'\"]{8,}"
)
CONFLICT_MARKER = re.compile(r"^(?:<<<<<<<(?: .*)?|=======$|>>>>>>>(?: .*)?)$", re.MULTILINE)


def ignored(path: Path, package: Path) -> bool:
    relative = path.relative_to(package)
    return (
        bool(IGNORED_PARTS.intersection(relative.parts))
        or path.name in IGNORED_NAMES
        or path.suffix.casefold() in IGNORED_SUFFIXES
    )


def runtime_files(package: Path) -> Tuple[list[Path], list[str]]:
    errors: list[str] = []
    files: list[Path] = []
    skill = package / "SKILL.md"
    if skill.is_file() and not skill.is_symlink():
        files.append(skill)
    elif skill.is_symlink():
        errors.append("SKILL.md: symlinks are not allowed")
    else:
        errors.append("SKILL.md: missing runtime entrypoint")

    for name in RUNTIME_DIRECTORIES:
        directory = package / name
        if not directory.is_dir():
            errors.append(f"{name}/: missing runtime directory")
            continue
        if directory.is_symlink():
            errors.append(f"{name}/: symlinks are not allowed")
            continue
        for root, directories, filenames in os.walk(directory, followlinks=False):
            root_path = Path(root)
            kept_directories: list[str] = []
            for child_name in directories:
                child = root_path / child_name
                if ignored(child, package):
                    continue
                if child.is_symlink():
                    errors.append(f"{child.relative_to(package)}: symlinks are not allowed")
                    continue
                kept_directories.append(child_name)
            directories[:] = kept_directories
            for child_name in filenames:
                child = root_path / child_name
                if ignored(child, package):
                    continue
                if child.is_symlink():
                    errors.append(f"{child.relative_to(package)}: symlinks are not allowed")
                elif child.is_file() and child.suffix.casefold() == ".md":
                    files.append(child)
                elif child.is_file():
                    errors.append(f"{child.relative_to(package)}: unsupported non-Markdown runtime file")
    return sorted(set(files)), errors


def parse_frontmatter(path: Path, text: str) -> Tuple[dict[str, str], Optional[str]]:
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}, "missing frontmatter"
    try:
        closing = next(index for index, line in enumerate(lines[1:], 1) if line.strip() == "---")
    except StopIteration:
        return {}, "unclosed frontmatter"
    values: dict[str, str] = {}
    for line in lines[1:closing]:
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        match = FRONTMATTER_KEY.match(line)
        if not match:
            return {}, f"invalid frontmatter line `{line.strip()}`"
        key = line.split(":", 1)[0].strip()
        if key in values:
            return {}, f"duplicate frontmatter key `{key}`"
        values[key] = match.group(1).strip().strip("'\"")
    if not values:
        return {}, "empty frontmatter"
    if path.name == "SKILL.md":
        for key in ("name", "description"):
            if not values.get(key):
                return {}, f"frontmatter missing `{key}`"
    return values, None


def destinations(text: str) -> list[str]:
    found: list[str] = []
    for match in MARKDOWN_LINK.finditer(text):
        raw = match.group("target").strip()
        if raw.startswith("<") and raw.endswith(">"):
            raw = raw[1:-1]
        else:
            # Drop an optional Markdown link title without treating spaces in
            # angle-bracket destinations as separators.
            raw = re.split(r"\s+[\"']", raw, maxsplit=1)[0]
        found.append(raw)
    found.extend(match.group("target") for match in RUNTIME_PATH.finditer(text))
    return list(dict.fromkeys(found))


def resolve_local(package: Path, source: Path, raw: str) -> Optional[Path]:
    target = html.unescape(raw.strip())
    parsed = urlsplit(target)
    if parsed.scheme or parsed.netloc:
        return None
    path_text = unquote(parsed.path)
    if not path_text:
        return None
    relative = Path(path_text)
    if path_text.startswith(("references/", "templates/")):
        candidate = package / relative
    else:
        candidate = source.parent / relative
    return candidate.resolve(strict=False)


def validate(package: Path) -> list[str]:
    package = package.resolve()
    files, errors = runtime_files(package)
    runtime_set = {path.resolve() for path in files}
    markdown = [path for path in files if path.suffix.casefold() == ".md"]
    graph: dict[Path, set[Path]] = {path.resolve(): set() for path in markdown}

    for path in markdown:
        relative = path.relative_to(package)
        text = path.read_text(encoding="utf-8", errors="replace")
        _, frontmatter_error = parse_frontmatter(path, text)
        if frontmatter_error:
            errors.append(f"{relative}: {frontmatter_error}")
        if MACHINE_PATH.search(text):
            errors.append(f"{relative}: machine-specific absolute path")
        if SENSITIVE_ASSIGNMENT.search(text):
            errors.append(f"{relative}: sensitive-looking credential assignment")
        if CONFLICT_MARKER.search(text):
            errors.append(f"{relative}: unresolved conflict marker")

        for raw in destinations(text):
            target = resolve_local(package, path, raw)
            if target is None:
                continue
            try:
                target.relative_to(package)
            except ValueError:
                errors.append(f"{relative}: local link escapes runtime package: {raw}")
                continue
            if target not in runtime_set:
                errors.append(f"{relative}: broken or non-runtime local link: {raw}")
                continue
            if target.suffix.casefold() == ".md":
                graph[path.resolve()].add(target)

    skill = (package / "SKILL.md").resolve()
    reachable: set[Path] = set()
    pending = [skill]
    while pending:
        current = pending.pop()
        if current in reachable:
            continue
        reachable.add(current)
        pending.extend(graph.get(current, ()))
    for orphan in sorted(set(graph) - reachable):
        errors.append(f"{orphan.relative_to(package)}: runtime Markdown is unreachable from SKILL.md")

    return sorted(set(errors))


def main() -> int:
    package = Path(sys.argv[1] if len(sys.argv) > 1 else Path(__file__).resolve().parents[1])
    errors = validate(package)
    if errors:
        print("workflow runtime check failed:")
        for item in errors:
            print(f"- {item}")
        return 1
    files, _ = runtime_files(package.resolve())
    print(f"workflow runtime check: OK ({len(files)} files)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
