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

from workflow_doctor import PUBLIC_TARGETS


SOURCE = Path(__file__).resolve().parents[1]
NAME = "workflow"
TARGET_ENV = "AGENT_SKILLS_DIR"


def known_targets() -> tuple[tuple[str, Path], ...]:
    home = Path.home()
    return (
        ("Codex", home / ".codex" / "skills"),
        ("Claude Code", home / ".claude" / "skills"),
        ("OpenCode", home / ".config" / "opencode" / "skills"),
        ("通用 Agent", home / ".agents" / "skills"),
    )


def stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def fail(message: str) -> int:
    print(f"workflow 安装错误 / install error: {message}", file=sys.stderr)
    return 2


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


def resolve_target(raw: str | None, action: str) -> Path:
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


def validate_source() -> list[str]:
    actual = {path.relative_to(SOURCE).as_posix() for path in SOURCE.rglob("*") if path.is_file()}
    return sorted(PUBLIC_TARGETS - actual)


def copy_payload(stage: Path) -> None:
    for relative in sorted(PUBLIC_TARGETS):
        source = SOURCE / relative
        destination = stage / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)


def payload_matches(destination: Path) -> bool:
    for relative in PUBLIC_TARGETS:
        source = SOURCE / relative
        installed = destination / relative
        if not installed.is_file() or installed.read_bytes() != source.read_bytes():
            return False
    return True


def run_check(destination: Path) -> int:
    for script in ("workflow_doctor.py", "release_check.py"):
        result = subprocess.run(
            [sys.executable, "-B", str(destination / "scripts" / script)],
            cwd=destination,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
        )
        print(result.stdout, end="")
        if result.returncode:
            return result.returncode
    return 0


def install(parent: Path, *, update: bool) -> int:
    missing = validate_source()
    if missing:
        return fail("当前源码不是完整发布候选：" + ", ".join(missing))
    destination = parent / NAME
    if update and destination.is_symlink():
        if not destination.is_dir() or not (destination / "SKILL.md").is_file():
            return fail(f"符号链接安装已损坏：{destination}")
        if not payload_matches(destination):
            return fail(
                f"符号链接安装与当前源码不同：{destination}；"
                "请先更新链接指向的唯一真源，安装器不会把软链替换成实体副本"
            )
        result = run_check(destination)
        if result:
            return result
        print(f"workflow 由符号链接管理且已是当前版本，保留原链接：{destination}")
        return 0
    if update and not destination.is_dir():
        return fail(f"没有可更新的安装：{destination}")
    if not update and destination.exists():
        return fail(f"目标已存在：{destination}；请改用 update 以保留备份")

    parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix=".workflow-stage-", dir=parent))
    backup: Path | None = None
    try:
        copy_payload(stage)
        if update:
            backup = parent / f"{NAME}.backup-{stamp()}"
            if backup.exists():
                return fail(f"备份路径已存在：{backup}")
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
        if backup and backup.exists():
            failed = parent / f"{NAME}.failed-{stamp()}"
            destination.rename(failed)
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
    if not destination.is_dir():
        return fail(f"未找到安装：{destination}")
    recovered = parent / f"{NAME}.removed-{stamp()}"
    if recovered.exists():
        return fail(f"恢复目录已存在：{recovered}")
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
    if parent == SOURCE or SOURCE in parent.parents:
        return fail("target 不能是源码包或其子目录")
    destination = parent / NAME
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
