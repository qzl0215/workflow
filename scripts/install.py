#!/usr/bin/env python3
"""Install, verify, replace, or sync the single active workflow package."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import plistlib
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.request
import zipfile
from pathlib import Path, PurePosixPath

from workflow_doctor import PUBLIC_TARGETS


SOURCE = Path(__file__).resolve().parents[1]
NAME = "workflow"
TARGET_ENV = "AGENT_SKILLS_DIR"
OFFICIAL_RELEASE_API = "https://api.github.com/repos/qzl0215/workflow/releases/latest"
OFFICIAL_ASSET_PREFIX = "https://github.com/qzl0215/workflow/releases/download/"
RELEASE_ASSET_NAME = "workflow.zip"
PENDING_ENTRY = "SKILL.pending"
SCHEDULE_LABEL = "com.qzl0215.workflow.sync"
SCHEDULE_SECONDS = 24 * 60 * 60
FRONTMATTER_LINE = re.compile(r"^([A-Za-z0-9_-]+):\s*(.*?)\s*$")


def known_targets() -> tuple[tuple[str, Path], ...]:
    home = Path.home()
    return (
        ("Codex", home / ".codex" / "skills"),
        ("Claude Code", home / ".claude" / "skills"),
        ("OpenCode", home / ".config" / "opencode" / "skills"),
        ("通用 Agent", home / ".agents" / "skills"),
    )


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


def validate_source(source: Path = SOURCE) -> list[str]:
    actual = {path.relative_to(source).as_posix() for path in source.rglob("*") if path.is_file()}
    return sorted(PUBLIC_TARGETS - actual)


def copy_payload(source_root: Path, stage: Path, *, pending_entry: bool = False) -> None:
    for relative in sorted(PUBLIC_TARGETS):
        source = source_root / relative
        destination_relative = PENDING_ENTRY if pending_entry and relative == "SKILL.md" else relative
        destination = stage / destination_relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)


def payload_matches(destination: Path, source_root: Path = SOURCE) -> bool:
    for relative in PUBLIC_TARGETS:
        source = source_root / relative
        installed = destination / relative
        if not installed.is_file() or installed.read_bytes() != source.read_bytes():
            return False
    return True


def installed_payload_matches(destination: Path, source_root: Path) -> bool:
    actual = {
        path.relative_to(destination).as_posix()
        for path in destination.rglob("*")
        if path.is_file()
    }
    return actual == PUBLIC_TARGETS and payload_matches(destination, source_root)


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


def skill_metadata(path: Path) -> dict[str, str]:
    if not path.is_file():
        return {}
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    if not lines or lines[0] != "---":
        return {}
    metadata: dict[str, str] = {}
    for line in lines[1:]:
        if line == "---":
            return metadata
        match = FRONTMATTER_LINE.match(line)
        if match:
            metadata[match.group(1)] = match.group(2)
    return {}


def discover_workflow_entries(parent: Path) -> list[Path]:
    if not parent.is_dir():
        return []
    entries: list[Path] = []
    for candidate in sorted(parent.iterdir()):
        if candidate.name.startswith("."):
            continue
        if skill_metadata(candidate / "SKILL.md").get("name") == NAME:
            entries.append(candidate)
    return entries


def ensure_unique_install(parent: Path) -> int:
    destination = parent / NAME
    entries = discover_workflow_entries(parent)
    if entries == [destination]:
        return 0
    rendered = ", ".join(str(path) for path in entries) or "none"
    return fail(
        f"skills 目录必须且只能有一个 workflow，且位置必须是 {destination}；"
        f"当前发现多个 workflow 或位置不正确：{rendered}"
    )


def prepare_activation_stage(parent: Path, source_root: Path) -> tuple[Path | None, int]:
    with tempfile.TemporaryDirectory(prefix="workflow-validate-") as temp:
        validation = Path(temp) / NAME
        validation.mkdir()
        copy_payload(source_root, validation)
        result = run_check(validation)
        if result:
            return None, result
        stage = Path(tempfile.mkdtemp(prefix=".workflow-stage-", dir=parent))
        copy_payload(validation, stage, pending_entry=True)
        return stage, 0


def activate_stage(parent: Path, stage: Path, *, update: bool) -> int:
    destination = parent / NAME
    if update:
        shutil.rmtree(destination)
    stage.rename(destination)
    (destination / PENDING_ENTRY).rename(destination / "SKILL.md")
    result = run_check(destination)
    if result:
        return result
    return ensure_unique_install(parent)


def install(parent: Path, *, update: bool, source_root: Path = SOURCE) -> int:
    missing = validate_source(source_root)
    if missing:
        return fail("当前源码不是完整发布候选：" + ", ".join(missing))
    destination = parent / NAME
    if update and destination.is_symlink():
        if not destination.is_dir() or not (destination / "SKILL.md").is_file():
            return fail(f"符号链接安装已损坏：{destination}")
        if source_root != SOURCE or not payload_matches(destination, source_root):
            return fail(
                f"符号链接安装与当前源码不同：{destination}；"
                "请先更新链接指向的唯一真源，安装器不会把软链替换成实体副本"
            )
        result = run_check(destination)
        if result:
            return result
        print(f"workflow 由符号链接管理且已是当前版本，保留原链接：{destination}")
        return ensure_unique_install(parent)
    if update and not destination.is_dir():
        return fail(f"没有可更新的安装：{destination}")
    if not update and destination.exists():
        return fail(f"目标已存在：{destination}；请改用 update 整体替换")

    parent.mkdir(parents=True, exist_ok=True)
    other_entries = [path for path in discover_workflow_entries(parent) if path != destination]
    if other_entries:
        return fail("发现多个 workflow，拒绝猜测唯一真源：" + ", ".join(map(str, other_entries)))
    stage, result = prepare_activation_stage(parent, source_root)
    if result or stage is None:
        return result or 1
    try:
        result = activate_stage(parent, stage, update=update)
    finally:
        if stage.exists():
            shutil.rmtree(stage)
    if result:
        return result
    print(f"workflow 已{'更新' if update else '安装'}：{destination}")
    return 0


def uninstall(parent: Path, confirmed: bool) -> int:
    destination = parent / NAME
    if not confirmed:
        return fail("卸载需要 --yes；操作会永久删除活动 workflow")
    if destination.is_symlink():
        destination.unlink()
    elif destination.is_dir():
        shutil.rmtree(destination)
    else:
        return fail(f"未找到安装：{destination}")
    print(f"workflow 已卸载：{destination}")
    return 0


def fetch_release(url: str) -> dict[str, object]:
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "workflow-updater",
        },
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        payload = json.load(response)
    if not isinstance(payload, dict):
        raise ValueError("Latest Release 响应不是对象")
    return payload


def latest_asset(release: dict[str, object], *, official: bool) -> tuple[str, str, str]:
    if release.get("draft") or release.get("prerelease"):
        raise ValueError("Latest Release 必须是正式版本，不能是 draft 或 prerelease")
    if release.get("immutable") is not True:
        raise ValueError("Latest Release 必须启用 immutable")
    tag = release.get("tag_name")
    if not isinstance(tag, str) or not tag.strip():
        raise ValueError("Latest Release 缺少 tag_name")
    version = tag.strip().removeprefix("v")
    assets = release.get("assets")
    if not isinstance(assets, list):
        raise ValueError("Latest Release 缺少 assets")
    matches = [
        asset
        for asset in assets
        if isinstance(asset, dict) and asset.get("name") == RELEASE_ASSET_NAME
    ]
    if len(matches) != 1:
        raise ValueError(f"Latest Release 必须且只能包含一个 {RELEASE_ASSET_NAME}")
    asset = matches[0]
    url = asset.get("browser_download_url")
    digest = asset.get("digest")
    if not isinstance(url, str) or not url:
        raise ValueError("Release asset 缺少下载地址")
    if official and not url.startswith(OFFICIAL_ASSET_PREFIX):
        raise ValueError("Release asset 不是 workflow 官方下载地址")
    if not isinstance(digest, str) or not re.fullmatch(r"sha256:[0-9a-fA-F]{64}", digest):
        raise ValueError("Release asset 缺少有效 SHA-256")
    return version, url, digest.split(":", 1)[1].lower()


def download_asset(url: str, destination: Path, expected_sha256: str) -> None:
    digest = hashlib.sha256()
    request = urllib.request.Request(url, headers={"User-Agent": "workflow-updater"})
    with urllib.request.urlopen(request, timeout=30) as response, destination.open("wb") as output:
        while chunk := response.read(1024 * 1024):
            output.write(chunk)
            digest.update(chunk)
    actual = digest.hexdigest()
    if actual != expected_sha256:
        destination.unlink(missing_ok=True)
        raise ValueError(f"Release asset SHA-256 不匹配：expected={expected_sha256}, actual={actual}")


def extract_release(asset: Path, destination: Path) -> Path:
    with zipfile.ZipFile(asset) as archive:
        for info in archive.infolist():
            relative = PurePosixPath(info.filename)
            if relative.is_absolute() or ".." in relative.parts or "\\" in info.filename:
                raise ValueError(f"Release asset 包含不安全路径：{info.filename}")
        archive.extractall(destination)
    if (destination / "SKILL.md").is_file():
        return destination
    candidates = sorted(destination.glob("*/SKILL.md"))
    if len(candidates) != 1:
        raise ValueError("Release asset 必须包含唯一的根 SKILL.md")
    return candidates[0].parent


def sync_latest(parent: Path, release_api: str) -> int:
    destination = parent / NAME
    if destination.is_symlink():
        return fail("符号链接安装由其唯一源码管理，sync 不会覆盖")
    if not destination.is_dir():
        return fail(f"未找到可同步安装：{destination}")
    if ensure_unique_install(parent):
        return 2
    try:
        release = fetch_release(release_api)
        version, asset_url, expected_sha256 = latest_asset(
            release,
            official=release_api == OFFICIAL_RELEASE_API,
        )
        with tempfile.TemporaryDirectory(prefix="workflow-release-") as temp:
            release_root = Path(temp)
            asset = release_root / RELEASE_ASSET_NAME
            download_asset(asset_url, asset, expected_sha256)
            extracted = release_root / "extracted"
            extracted.mkdir()
            package = extract_release(asset, extracted)
            package_version = skill_metadata(package / "SKILL.md").get("version")
            if package_version != version:
                raise ValueError(
                    f"Release tag 与包版本不一致：tag={version}, package={package_version or 'missing'}"
                )
            current = skill_metadata(destination / "SKILL.md").get("version")
            if current == version and installed_payload_matches(destination, package):
                result = run_check(destination)
                if result:
                    return result
                print(f"workflow 已是 GitHub Latest Release：{version}")
                return 0
            result = install(parent, update=True, source_root=package)
            if result:
                return result
        print(f"workflow 已同步到 GitHub Latest Release：{version}")
        return 0
    except (OSError, ValueError, json.JSONDecodeError, zipfile.BadZipFile) as exc:
        return fail(str(exc))


def sync_command(parent: Path) -> list[str]:
    return [
        sys.executable,
        "-B",
        str(parent / NAME / "scripts" / "install.py"),
        "sync",
        "--target",
        str(parent),
    ]


def scheduler_platform(value: str | None = None) -> str:
    current = value or sys.platform
    if current == "darwin":
        return "darwin"
    if current.startswith("linux"):
        return "linux"
    if current in {"win32", "cygwin"}:
        return "win32"
    raise ValueError(f"不支持的自动更新平台：{current}")


def systemd_quote(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def schedule_preview(parent: Path, platform_name: str) -> str:
    command = sync_command(parent)
    if platform_name == "darwin":
        payload = {
            "Label": SCHEDULE_LABEL,
            "ProgramArguments": command,
            "RunAtLoad": True,
            "StartInterval": SCHEDULE_SECONDS,
        }
        return plistlib.dumps(payload, sort_keys=True).decode("utf-8")
    if platform_name == "linux":
        rendered = " ".join(systemd_quote(part) for part in command)
        return (
            "[Unit]\nDescription=Sync workflow to GitHub Latest Release\n\n"
            "[Service]\nType=oneshot\n"
            f"ExecStart={rendered}\n\n"
            "--- workflow-sync.timer ---\n"
            "[Unit]\nDescription=Run workflow sync daily\n\n"
            "[Timer]\nOnBootSec=2min\nOnUnitActiveSec=1d\nPersistent=true\n\n"
            "[Install]\nWantedBy=timers.target\n"
        )
    rendered = subprocess.list2cmdline(command)
    return (
        f'schtasks /Create /TN "Workflow Sync Daily" /TR "{rendered}" /SC DAILY /F\n'
        f'schtasks /Create /TN "Workflow Sync Logon" /TR "{rendered}" /SC ONLOGON /F\n'
    )


def enable_auto_update(parent: Path, *, dry_run: bool, platform_override: str | None) -> int:
    if ensure_unique_install(parent):
        return 2
    try:
        platform_name = scheduler_platform(platform_override)
        preview = schedule_preview(parent, platform_name)
        if dry_run:
            print(preview, end="" if preview.endswith("\n") else "\n")
            return 0
        if platform_override and platform_name != scheduler_platform():
            return fail("--scheduler-platform 只能与 --dry-run 一起使用")
        command = sync_command(parent)
        if platform_name == "darwin":
            path = Path.home() / "Library/LaunchAgents" / f"{SCHEDULE_LABEL}.plist"
            path.parent.mkdir(parents=True, exist_ok=True)
            if path.exists():
                subprocess.run(
                    ["launchctl", "bootout", f"gui/{os.getuid()}", str(path)],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    check=False,
                )
            path.write_bytes(
                plistlib.dumps(
                    {
                        "Label": SCHEDULE_LABEL,
                        "ProgramArguments": command,
                        "RunAtLoad": True,
                        "StartInterval": SCHEDULE_SECONDS,
                    },
                    sort_keys=True,
                )
            )
            subprocess.run(
                ["launchctl", "bootstrap", f"gui/{os.getuid()}", str(path)],
                check=True,
            )
        elif platform_name == "linux":
            unit_dir = Path.home() / ".config/systemd/user"
            unit_dir.mkdir(parents=True, exist_ok=True)
            rendered = " ".join(systemd_quote(part) for part in command)
            (unit_dir / "workflow-sync.service").write_text(
                "[Unit]\nDescription=Sync workflow to GitHub Latest Release\n\n"
                "[Service]\nType=oneshot\n"
                f"ExecStart={rendered}\n",
                encoding="utf-8",
            )
            (unit_dir / "workflow-sync.timer").write_text(
                "[Unit]\nDescription=Run workflow sync daily\n\n"
                "[Timer]\nOnBootSec=2min\nOnUnitActiveSec=1d\nPersistent=true\n\n"
                "[Install]\nWantedBy=timers.target\n",
                encoding="utf-8",
            )
            subprocess.run(["systemctl", "--user", "daemon-reload"], check=True)
            subprocess.run(
                ["systemctl", "--user", "enable", "--now", "workflow-sync.timer"],
                check=True,
            )
        else:
            rendered = subprocess.list2cmdline(command)
            for task_name, schedule in (
                ("Workflow Sync Daily", "DAILY"),
                ("Workflow Sync Logon", "ONLOGON"),
            ):
                subprocess.run(
                    [
                        "schtasks",
                        "/Create",
                        "/TN",
                        task_name,
                        "/TR",
                        rendered,
                        "/SC",
                        schedule,
                        "/F",
                    ],
                    check=True,
                )
        print("workflow 自动更新已启用：登录时运行，并每 24 小时同步 GitHub Latest Release")
        return 0
    except (OSError, ValueError, subprocess.CalledProcessError) as exc:
        return fail(str(exc))


def disable_auto_update(*, dry_run: bool, platform_override: str | None) -> int:
    try:
        platform_name = scheduler_platform(platform_override)
        if dry_run:
            print(f"disable workflow auto update on {platform_name}")
            return 0
        if platform_override and platform_name != scheduler_platform():
            return fail("--scheduler-platform 只能与 --dry-run 一起使用")
        if platform_name == "darwin":
            path = Path.home() / "Library/LaunchAgents" / f"{SCHEDULE_LABEL}.plist"
            if path.exists():
                subprocess.run(
                    ["launchctl", "bootout", f"gui/{os.getuid()}", str(path)],
                    check=False,
                )
                path.unlink()
        elif platform_name == "linux":
            unit_dir = Path.home() / ".config/systemd/user"
            subprocess.run(
                ["systemctl", "--user", "disable", "--now", "workflow-sync.timer"],
                check=False,
            )
            for name in ("workflow-sync.service", "workflow-sync.timer"):
                (unit_dir / name).unlink(missing_ok=True)
            subprocess.run(["systemctl", "--user", "daemon-reload"], check=False)
        else:
            for task_name in ("Workflow Sync Daily", "Workflow Sync Logon"):
                subprocess.run(
                    ["schtasks", "/Delete", "/TN", task_name, "/F"],
                    check=False,
                )
        print("workflow 自动更新已停用")
        return 0
    except (OSError, ValueError) as exc:
        return fail(str(exc))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="安装、检查、替换或同步唯一 workflow")
    parser.add_argument(
        "action",
        choices=(
            "detect",
            "install",
            "check",
            "update",
            "sync",
            "enable-auto-update",
            "disable-auto-update",
            "uninstall",
        ),
    )
    parser.add_argument(
        "--target",
        help=f"skills 父目录；省略或填 auto 时安全探测，也可设置 {TARGET_ENV}",
    )
    parser.add_argument("--yes", action="store_true", help="确认永久卸载")
    parser.add_argument("--dry-run", action="store_true", help="只展示自动更新配置，不写系统")
    parser.add_argument(
        "--release-api",
        default=OFFICIAL_RELEASE_API,
        help=argparse.SUPPRESS,
    )
    parser.add_argument(
        "--scheduler-platform",
        choices=("darwin", "linux", "win32"),
        help=argparse.SUPPRESS,
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.action == "detect":
        return show_detection()
    if args.action == "disable-auto-update":
        return disable_auto_update(
            dry_run=args.dry_run,
            platform_override=args.scheduler_platform,
        )
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
    if args.action == "sync":
        return sync_latest(parent, args.release_api)
    if args.action == "enable-auto-update":
        return enable_auto_update(
            parent,
            dry_run=args.dry_run,
            platform_override=args.scheduler_platform,
        )
    if args.action == "uninstall":
        return uninstall(parent, args.yes)
    if not destination.is_dir():
        return fail(f"未找到安装：{destination}")
    result = run_check(destination)
    if result:
        return result
    return ensure_unique_install(parent)


if __name__ == "__main__":
    raise SystemExit(main())
