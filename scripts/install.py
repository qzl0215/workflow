#!/usr/bin/env python3
"""Install, verify, update, or recoverably uninstall workflow."""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


SOURCE = Path(__file__).resolve().parents[1]
CHECK = Path(__file__).with_name("check.py")
NAME = "workflow"
TARGET_ENV = "AGENT_SKILLS_DIR"
RUNTIME_DIRECTORIES = ("references", "templates")
IGNORED_NAMES = frozenset({".DS_Store", "Thumbs.db", "desktop.ini"})
IGNORED_PARTS = frozenset({".git", "__pycache__"})
IGNORED_SUFFIXES = frozenset({".pyc", ".pyo"})


def known_targets() -> tuple[tuple[str, Path], ...]:
    home = Path.home()
    return (
        ("Codex", home / ".codex" / "skills"),
        ("Claude Code", home / ".claude" / "skills"),
        ("OpenCode", home / ".config" / "opencode" / "skills"),
        ("通用 Agent", home / ".agents" / "skills"),
    )


def stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")


def fail(message: str) -> int:
    print(f"workflow 安装错误 / install error: {message}", file=sys.stderr)
    return 2


def ignored(path: Path) -> bool:
    relative = path.relative_to(SOURCE)
    return (
        bool(IGNORED_PARTS.intersection(relative.parts))
        or path.name in IGNORED_NAMES
        or path.suffix.casefold() in IGNORED_SUFFIXES
    )


def runtime_payload() -> list[Path]:
    files = [SOURCE / "SKILL.md"]
    for name in RUNTIME_DIRECTORIES:
        directory = SOURCE / name
        if directory.is_dir():
            files.extend(
                path
                for path in directory.rglob("*")
                if path.is_file() and path.suffix.casefold() == ".md" and not ignored(path)
            )
    return sorted(set(files))


def auto_candidates() -> list[tuple[str, Path]]:
    configured = os.environ.get(TARGET_ENV, "").strip()
    if configured:
        return [(TARGET_ENV, Path(configured).expanduser().resolve())]
    candidates: list[tuple[str, Path]] = []
    for label, path in known_targets():
        resolved = path.expanduser().resolve()
        if resolved.is_dir() and all(resolved != candidate for _, candidate in candidates):
            candidates.append((label, resolved))
    return candidates


def show_detection() -> int:
    print("workflow skills 目录探测（只读，不会安装）：")
    configured = os.environ.get(TARGET_ENV, "").strip()
    if configured:
        print(f"- [已配置] {TARGET_ENV}: {Path(configured).expanduser().resolve()}")
    for label, path in known_targets():
        status = "可用" if path.is_dir() else "未发现"
        print(f"- [{status}] {label}: {path}")
    candidates = auto_candidates()
    if len(candidates) == 1:
        print(f"\n可自动使用：{candidates[0][1]}")
    elif len(candidates) > 1:
        print("\n发现多个 skills 目录；安装时请用 --target 明确选择。")
    else:
        print(f"\n未发现可用目录；请用 --target 指定，或设置 {TARGET_ENV}。")
    return 0


def resolve_target(raw: Optional[str], action: str) -> Path:
    if raw and raw != "auto":
        return Path(raw).expanduser().resolve()
    candidates = auto_candidates()
    if action != "install":
        installed = [(label, path) for label, path in candidates if (path / NAME).is_dir()]
        if len(installed) == 1:
            candidates = installed
    if len(candidates) == 1:
        label, path = candidates[0]
        print(f"已自动识别 skills 目录：{path}（{label}）")
        return path
    if not candidates:
        raise ValueError(
            f"未发现 skills 目录；请让 Agent 确认自己的目录后使用 --target，或设置 {TARGET_ENV}"
        )
    choices = "\n".join(f"  - {label}: {path}" for label, path in candidates)
    raise ValueError(f"发现多个 skills 目录，不能替你猜；请使用 --target 明确选择：\n{choices}")


def run_check(package: Path, *, quiet: bool = False) -> int:
    result = subprocess.run(
        [sys.executable, "-B", str(CHECK), str(package)],
        cwd=SOURCE,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    if not quiet or result.returncode:
        print(result.stdout, end="")
    return result.returncode


def copy_payload(stage: Path) -> None:
    for source in runtime_payload():
        relative = source.relative_to(SOURCE)
        destination = stage / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)


def package_name(package: Path) -> Optional[str]:
    skill = package / "SKILL.md"
    if not skill.is_file() or skill.is_symlink():
        return None
    lines = skill.read_text(encoding="utf-8", errors="replace").splitlines()
    if not lines or lines[0].strip() != "---":
        return None
    for line in lines[1:]:
        if line.strip() == "---":
            break
        if line.startswith("name:"):
            return line.split(":", 1)[1].strip().strip("'\"")
    return None


def install(parent: Path, *, update: bool) -> int:
    if run_check(SOURCE, quiet=True):
        return fail("当前源码未通过运行包检查")
    destination = parent / NAME
    if update and package_name(destination) != NAME:
        return fail(f"目标不是可识别的 workflow 安装，拒绝更新：{destination}")
    if not update and destination.exists():
        return fail(f"目标已存在：{destination}；请改用 update 以保留备份")

    parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix=".workflow-stage-", dir=parent))
    backup: Optional[Path] = None
    try:
        copy_payload(stage)
        if update:
            backup = parent / f"{NAME}.backup-{stamp()}"
            destination.rename(backup)
        try:
            stage.rename(destination)
        except Exception:
            if backup and backup.exists() and not destination.exists():
                backup.rename(destination)
            raise
    finally:
        if stage.exists():
            shutil.rmtree(stage)

    if run_check(destination):
        print("安装文件未通过验证 / verification failed", file=sys.stderr)
        failed = parent / f"{NAME}.failed-{stamp()}"
        destination.rename(failed)
        if backup and backup.exists():
            backup.rename(destination)
            print(f"已恢复旧版本；失败候选保留在 {failed}", file=sys.stderr)
        return 1
    print(f"workflow 已{'更新' if update else '安装'}：{destination}")
    if backup:
        print(f"旧版本备份：{backup}")
    return 0


def uninstall(parent: Path, confirmed: bool) -> int:
    destination = parent / NAME
    if not confirmed:
        return fail("卸载需要 --yes；操作只会重命名目录，不会永久删除")
    if package_name(destination) != NAME:
        return fail(f"目标不是可识别的 workflow 安装，拒绝卸载：{destination}")
    recovered = parent / f"{NAME}.removed-{stamp()}"
    destination.rename(recovered)
    print(f"workflow 已卸载；可恢复目录：{recovered}")
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="安装、检查、更新或可恢复卸载 workflow")
    parser.add_argument("action", choices=("detect", "install", "check", "update", "uninstall"))
    parser.add_argument(
        "--target",
        help=f"skills 父目录；省略或填 auto 时安全探测，也可设置 {TARGET_ENV}",
    )
    parser.add_argument("--yes", action="store_true", help="确认执行可恢复卸载")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.action == "detect":
        return show_detection()
    try:
        parent = resolve_target(args.target, args.action)
    except ValueError as exc:
        return fail(str(exc))
    if parent == Path(parent.anchor):
        return fail("target 不能是文件系统根目录")
    destination = parent / NAME
    if destination == SOURCE or destination in SOURCE.parents or SOURCE in destination.parents:
        return fail("target 解析后的安装目录不能与源码包相同或重叠")
    if args.action == "install":
        return install(parent, update=False)
    if args.action == "update":
        return install(parent, update=True)
    if args.action == "uninstall":
        return uninstall(parent, args.yes)
    if not destination.is_dir():
        return fail(f"未找到安装：{destination}")
    return run_check(destination)


if __name__ == "__main__":
    raise SystemExit(main())
