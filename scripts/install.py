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
import stat
import subprocess
import sys
import tempfile
import urllib.request
import zipfile
from pathlib import Path, PurePosixPath

SOURCE = Path(__file__).resolve().parents[1]
NAME = "workflow"
TARGET_ENV = "AGENT_SKILLS_DIR"
OFFICIAL_RELEASE_API = "https://api.github.com/repos/qzl0215/workflow/releases/latest"
OFFICIAL_ASSET_PREFIX = "https://github.com/qzl0215/workflow/releases/download/"
RELEASE_ASSET_NAME = "workflow.zip"
RUNTIME_MANIFEST_NAME = "workflow-package.json"
RUNTIME_MANIFEST_SCHEMA = 1
MAX_RUNTIME_FILES = 256
MAX_RUNTIME_BYTES = 16 * 1024 * 1024
MAX_MANIFEST_BYTES = 64 * 1024
MAX_ASSET_BYTES = 64 * 1024 * 1024
MAX_ARCHIVE_FILES = 512
MAX_ARCHIVE_FILE_BYTES = 16 * 1024 * 1024
MAX_ARCHIVE_TOTAL_BYTES = 64 * 1024 * 1024
RUNTIME_REQUIRED_FILES = frozenset(
    {
        "SKILL.md",
        "scripts/install.py",
        "scripts/workflow_doctor.py",
    }
)
# This projection is intentionally frozen inside the bridge. Future runtime doctors
# may expose a different topology, while every 2.25 updater must still see these 45 paths.
PUBLIC_TARGETS = frozenset(
    {
        ".gitignore",
        "SKILL.md",
        "README.md",
        "LICENSE",
        "NOTICE.md",
        "SECURITY.md",
        "CONTRIBUTING.md",
        "CHANGELOG.md",
        "references/understand-goal.md",
        "references/decide-solution.md",
        "references/plan-tasks.md",
        "references/execute-tasks.md",
        "references/verify-results.md",
        "references/learn-review.md",
        "references/evolve-system.md",
        "references/shape-experience.md",
        "references/maintain-design.md",
        "references/coordinate-agents.md",
        "references/fix-failures.md",
        "references/handoff-context.md",
        "references/deliver-release.md",
        "adapters/merge-parallel-work.md",
        "methods/strategic-value.md",
        "methods/essence-subtraction.md",
        "methods/experiment-attack.md",
        "methods/delivery-compounding.md",
        "templates/index.md",
        "templates/findings.md",
        "templates/task_plan.md",
        "templates/implementation-plan.md",
        "templates/progress.md",
        "templates/task-owner-prompt.md",
        "scripts/workflow_doctor.py",
        "scripts/build_context_capsule.py",
        "scripts/safe_merge.py",
        "scripts/generate_visual_map.py",
        "scripts/release_check.py",
        "scripts/install.py",
        "tests/test_structure.py",
        "tests/test_behavior.py",
        "tests/test_context.py",
        "tests/test_portability.py",
        "tests/test_safe_merge.py",
        "tests/test_docs.py",
        "docs/workflow-visual-map.html",
    }
)
SCHEDULE_LABEL = "com.qzl0215.workflow.sync"
SCHEDULE_SECONDS = 24 * 60 * 60
FRONTMATTER_LINE = re.compile(r"^([A-Za-z0-9_-]+):\s*(.*?)\s*$")
WINDOWS_RESERVED_NAMES = frozenset(
    {"CON", "PRN", "AUX", "NUL"}
    | {f"COM{index}" for index in range(1, 10)}
    | {f"LPT{index}" for index in range(1, 10)}
)


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
    if raw and raw.casefold() == "codex":
        for label, path in known_targets():
            if label == "Codex":
                resolved = path.expanduser().resolve()
                print(f"已选择 Codex skills 目录：{resolved}")
                return resolved
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


def package_files(source: Path) -> frozenset[str]:
    return frozenset(
        path.relative_to(source).as_posix()
        for path in source.rglob("*")
        if path.is_file()
        and not {".git", "__pycache__"}.intersection(path.relative_to(source).parts)
        and path.name != ".DS_Store"
    )


def validate_portable_parts(parts: tuple[str, ...], raw: str, label: str) -> None:
    for part in parts:
        stem = part.split(".", 1)[0].upper()
        if (
            not part
            or part in {".", ".."}
            or part.endswith((" ", "."))
            or any(character in '<>:"|?*' for character in part)
            or stem in WINDOWS_RESERVED_NAMES
        ):
            raise ValueError(f"{label}包含不安全路径：{raw}")


def normalize_manifest_path(raw: object) -> str:
    if not isinstance(raw, str) or not raw.strip():
        raise ValueError("runtime manifest 文件路径必须是非空字符串")
    value = raw.strip()
    if (
        raw != value
        or not value.isascii()
        or any(ord(character) < 32 or ord(character) == 127 for character in value)
        or value.startswith(("/", "~"))
        or "\\" in value
        or re.match(r"^[A-Za-z]:", value)
    ):
        raise ValueError(f"runtime manifest 包含不安全路径：{raw}")
    path = PurePosixPath(value)
    if (
        path.as_posix() != value
        or path.as_posix() == "."
        or ".." in path.parts
        or any(not part for part in path.parts)
    ):
        raise ValueError(f"runtime manifest 包含不安全路径：{raw}")
    validate_portable_parts(path.parts, value, "runtime manifest ")
    return path.as_posix()


def runtime_tree_errors(
    root: Path,
    targets: frozenset[str],
    *,
    allowed_optional: frozenset[str] = frozenset(),
    allow_checkout_metadata: bool = False,
) -> list[str]:
    allowed_directories: set[str] = set()
    for relative in targets | allowed_optional:
        parts = PurePosixPath(relative).parts[:-1]
        for index in range(1, len(parts) + 1):
            allowed_directories.add("/".join(parts[:index]))
    found: set[str] = set()
    errors: list[str] = []
    scanned_entries = 0

    def visit_generated(directory: Path, prefix: tuple[str, ...]) -> None:
        nonlocal scanned_entries
        try:
            with os.scandir(directory) as entries:
                current = list(entries)
        except OSError as exc:
            errors.append(f"无法扫描 runtime 缓存：{directory}: {exc}")
            return
        for entry in current:
            scanned_entries += 1
            relative = "/".join(prefix + (entry.name,))
            if scanned_entries > MAX_ARCHIVE_FILES:
                errors.append(f"runtime 条目数超过安全上限：{MAX_ARCHIVE_FILES}")
                return
            try:
                if entry.is_symlink():
                    errors.append(f"runtime 包含符号链接：{relative}")
                    continue
                mode = entry.stat(follow_symlinks=False).st_mode
            except OSError as exc:
                errors.append(f"无法检查 runtime 条目：{relative}: {exc}")
                continue
            if stat.S_ISDIR(mode):
                visit_generated(Path(entry.path), prefix + (entry.name,))
            elif not stat.S_ISREG(mode):
                errors.append(f"runtime 包含非普通条目：{relative}")

    def visit(directory: Path, prefix: tuple[str, ...] = ()) -> None:
        nonlocal scanned_entries
        try:
            with os.scandir(directory) as entries:
                current = list(entries)
        except OSError as exc:
            errors.append(f"无法扫描 runtime：{directory}: {exc}")
            return
        for entry in current:
            scanned_entries += 1
            parts = prefix + (entry.name,)
            relative = "/".join(parts)
            if scanned_entries > MAX_ARCHIVE_FILES:
                errors.append(f"runtime 条目数超过安全上限：{MAX_ARCHIVE_FILES}")
                return
            try:
                if entry.is_symlink():
                    errors.append(f"runtime 包含符号链接：{relative}")
                    continue
                mode = entry.stat(follow_symlinks=False).st_mode
            except OSError as exc:
                errors.append(f"无法检查 runtime 条目：{relative}: {exc}")
                continue
            if entry.name == ".DS_Store" and stat.S_ISREG(mode):
                continue
            if entry.name == "__pycache__" and stat.S_ISDIR(mode):
                visit_generated(Path(entry.path), parts)
                continue
            if relative == ".git" and allow_checkout_metadata:
                continue
            if stat.S_ISDIR(mode):
                if relative not in allowed_directories:
                    errors.append(f"runtime 包含未声明目录：{relative}")
                    continue
                visit(Path(entry.path), parts)
            elif stat.S_ISREG(mode):
                if relative in targets:
                    found.add(relative)
                elif relative not in allowed_optional:
                    errors.append(f"runtime 包含未声明文件：{relative}")
            else:
                errors.append(f"runtime 包含非普通条目：{relative}")

    visit(root)
    missing = sorted(targets - found)
    if missing:
        errors.append("runtime 缺少声明文件：" + ", ".join(missing))
    return errors


def unique_json_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"runtime manifest 包含重复字段：{key}")
        result[key] = value
    return result


def read_runtime_manifest(path: Path) -> dict[str, object]:
    try:
        if path.is_symlink():
            raise ValueError("runtime manifest 必须是普通文件")
        metadata = path.stat()
        if not stat.S_ISREG(metadata.st_mode):
            raise ValueError("runtime manifest 必须是普通文件")
        if metadata.st_size > MAX_MANIFEST_BYTES:
            raise ValueError(f"runtime manifest 超过安全字节上限：{MAX_MANIFEST_BYTES}")
        manifest = json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=unique_json_object,
        )
    except OSError as exc:
        raise ValueError(f"runtime manifest 无法读取：{exc}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"runtime manifest 不是有效 JSON：{exc}") from exc
    if not isinstance(manifest, dict):
        raise ValueError("runtime manifest 必须是对象")
    return manifest


def payload_spec(source: Path = SOURCE) -> tuple[frozenset[str], frozenset[str]]:
    manifest_path = source / RUNTIME_MANIFEST_NAME
    if not manifest_path.is_file():
        version = skill_metadata(source / "SKILL.md").get("version", "")
        major = re.match(r"^(\d+)\.", version)
        if major and int(major.group(1)) >= 3:
            raise ValueError("workflow 3.x+ 必须包含普通 workflow-package.json")
        return PUBLIC_TARGETS, frozenset()
    manifest = read_runtime_manifest(manifest_path)
    expected_keys = {"schema", "name", "version", "entrypoint", "runtime", "source_only"}
    if set(manifest) != expected_keys:
        raise ValueError(
            "runtime manifest 字段必须且只能是 "
            "schema/name/version/entrypoint/runtime/source_only"
        )
    schema = manifest.get("schema")
    if type(schema) is not int or schema != RUNTIME_MANIFEST_SCHEMA:
        raise ValueError(f"runtime manifest schema 必须是 {RUNTIME_MANIFEST_SCHEMA}")
    if manifest.get("name") != NAME:
        raise ValueError("runtime manifest name 必须是 workflow")
    if manifest.get("entrypoint") != "SKILL.md":
        raise ValueError("runtime manifest entrypoint 必须是 SKILL.md")
    runtime = manifest.get("runtime")
    if not isinstance(runtime, dict) or set(runtime) != {"files"}:
        raise ValueError("runtime manifest runtime 必须且只能包含 files")
    raw_files = runtime.get("files")
    if not isinstance(raw_files, dict) or not raw_files:
        raise ValueError("runtime manifest runtime.files 必须是非空对象")
    normalized = [normalize_manifest_path(value) for value in raw_files]
    if len(normalized) != len(set(normalized)):
        raise ValueError("runtime manifest 包含重复文件路径")
    folded: dict[str, str] = {}
    for relative in normalized:
        key = relative.casefold()
        if key in folded and folded[key] != relative:
            raise ValueError(
                f"runtime manifest 包含大小写冲突路径：{folded[key]} / {relative}"
            )
        folded[key] = relative
    runtime_targets = frozenset(normalized)
    if len(runtime_targets) > MAX_RUNTIME_FILES:
        raise ValueError(f"runtime manifest 文件数超过安全上限：{MAX_RUNTIME_FILES}")
    missing_required = sorted(RUNTIME_REQUIRED_FILES - runtime_targets)
    if missing_required:
        raise ValueError("runtime manifest 缺少运行时文件：" + ", ".join(missing_required))
    metadata = skill_metadata(source / "SKILL.md")
    version = manifest.get("version")
    if not isinstance(version, str) or not version.strip() or metadata.get("version") != version.strip():
        raise ValueError("runtime manifest version 必须与 SKILL.md 一致")
    source_only = manifest.get("source_only")
    if not isinstance(source_only, list):
        raise ValueError("runtime manifest source_only 必须是数组")
    normalized_source_only = [normalize_manifest_path(value) for value in source_only]
    if len(normalized_source_only) != len(set(normalized_source_only)):
        raise ValueError("runtime manifest source_only 包含重复路径")
    all_declared = normalized + normalized_source_only + [RUNTIME_MANIFEST_NAME]
    if len({value.casefold() for value in all_declared}) != len(all_declared):
        raise ValueError("runtime manifest 的 runtime/source_only 包含大小写冲突")

    targets = runtime_targets | {RUNTIME_MANIFEST_NAME}
    allowed_source_files = targets | frozenset(normalized_source_only)
    actual = package_files(source)
    missing = sorted(targets - actual)
    extras = sorted(actual - allowed_source_files)
    if missing:
        raise ValueError("runtime manifest 声明的文件不存在：" + ", ".join(missing))
    if extras:
        raise ValueError("runtime package 包含未声明文件：" + ", ".join(extras))
    total_bytes = 0
    for relative in runtime_targets:
        path = source / relative
        if path.is_symlink() or not path.is_file():
            raise ValueError(f"runtime manifest 目标不是普通文件：{relative}")
        size = path.stat().st_size
        if size > MAX_RUNTIME_BYTES or total_bytes + size > MAX_RUNTIME_BYTES:
            raise ValueError(f"runtime package 超过安全字节上限：{MAX_RUNTIME_BYTES}")
        digest = raw_files.get(relative)
        if not isinstance(digest, str) or not re.fullmatch(r"sha256:[0-9a-fA-F]{64}", digest):
            raise ValueError(f"runtime manifest 缺少有效 SHA-256：{relative}")
        actual_digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual_digest != digest.split(":", 1)[1].lower():
            raise ValueError(f"runtime manifest SHA-256 不匹配：{relative}")
        total_bytes += size
    return targets, frozenset(normalized_source_only)


def payload_targets(source: Path = SOURCE) -> frozenset[str]:
    return payload_spec(source)[0]


def validate_source(source: Path = SOURCE) -> list[str]:
    targets = payload_targets(source)
    return sorted(targets - package_files(source))


def copy_payload(source_root: Path, stage: Path, targets: frozenset[str]) -> None:
    for relative in sorted(targets):
        source = source_root / relative
        destination = stage / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)


def payload_matches(
    destination: Path,
    source_root: Path = SOURCE,
    targets: frozenset[str] | None = None,
) -> bool:
    selected = targets or payload_targets(source_root)
    for relative in selected:
        source = source_root / relative
        installed = destination / relative
        if not installed.is_file() or installed.read_bytes() != source.read_bytes():
            return False
    return True


def installed_payload_matches(
    destination: Path,
    source_root: Path,
    targets: frozenset[str] | None = None,
) -> bool:
    selected = targets or payload_targets(source_root)
    return not runtime_tree_errors(destination, selected) and payload_matches(
        destination, source_root, selected
    )


def run_check(destination: Path) -> int:
    try:
        runtime = (destination / RUNTIME_MANIFEST_NAME).is_file()
        targets, source_only = payload_spec(destination)
    except ValueError as exc:
        return fail(str(exc))
    tree_errors = runtime_tree_errors(
        destination,
        targets,
        allowed_optional=source_only if destination.is_symlink() else frozenset(),
        allow_checkout_metadata=destination.is_symlink(),
    )
    if tree_errors:
        return fail("；".join(tree_errors))
    scripts = ("workflow_doctor.py",) if runtime else ("release_check.py",)
    for script in scripts:
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
    tree_errors = runtime_tree_errors(
        destination,
        targets,
        allowed_optional=source_only if destination.is_symlink() else frozenset(),
        allow_checkout_metadata=destination.is_symlink(),
    )
    if tree_errors:
        return fail("runtime gate 后完整性失败：" + "；".join(tree_errors))
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


def prepare_activation_stage(
    parent: Path,
    source_root: Path,
    targets: frozenset[str],
) -> tuple[Path | None, int]:
    stage = Path(tempfile.mkdtemp(prefix=".workflow-stage-", dir=parent))
    try:
        copy_payload(source_root, stage, targets)
        result = run_check(stage)
        if result:
            shutil.rmtree(stage)
            return None, result
        return stage, 0
    except Exception:
        if stage.exists():
            shutil.rmtree(stage)
        raise


def verify_activated_install(
    parent: Path,
    destination: Path,
    source_root: Path,
    targets: frozenset[str],
) -> int:
    if not installed_payload_matches(destination, source_root, targets):
        return fail("激活后的 payload 与已验证候选不一致")
    metadata = skill_metadata(destination / "SKILL.md")
    if metadata.get("name") != NAME or not metadata.get("version"):
        return fail("激活后的 SKILL.md 缺少 workflow 名称或版本")
    return ensure_unique_install(parent)


def activate_stage(
    parent: Path,
    stage: Path,
    *,
    update: bool,
    source_root: Path,
    targets: frozenset[str],
) -> int:
    destination = parent / NAME
    rollback_root: Path | None = None
    backup: Path | None = None

    def restore_previous() -> bool:
        if backup is None or not backup.exists():
            return False
        failed = rollback_root / "failed"
        if destination.exists() or destination.is_symlink():
            destination.rename(failed)
        backup.rename(destination)
        return True

    try:
        if update:
            rollback_root = Path(tempfile.mkdtemp(prefix=".workflow-rollback-", dir=parent))
            backup = rollback_root / NAME
            destination.rename(backup)
        stage.rename(destination)
        result = verify_activated_install(parent, destination, source_root, targets)
    except OSError as exc:
        restored = False
        cleanup_error: OSError | None = None
        untouched = bool(
            update
            and backup is not None
            and not backup.exists()
            and (destination.exists() or destination.is_symlink())
        )
        if backup is not None and backup.exists():
            try:
                restored = restore_previous()
            except OSError:
                restored = False
        elif not update and (destination.exists() or destination.is_symlink()):
            try:
                if destination.is_symlink():
                    destination.unlink()
                else:
                    shutil.rmtree(destination)
            except OSError:
                pass
        if (restored or untouched) and rollback_root and rollback_root.exists():
            try:
                shutil.rmtree(rollback_root)
            except OSError as cleanup_exc:
                cleanup_error = cleanup_exc
        if restored:
            suffix = "；旧安装已恢复"
        elif untouched:
            suffix = "；旧安装保持不变"
        else:
            suffix = "；请保留现场并人工恢复"
        if cleanup_error is not None:
            suffix += f"；隐藏事务目录清理失败：{cleanup_error}；请人工清理 {rollback_root}"
        return fail(f"原子激活失败：{exc}{suffix}")

    if result:
        restored = False
        try:
            if backup is not None:
                restored = restore_previous()
            elif destination.exists() or destination.is_symlink():
                if destination.is_symlink():
                    destination.unlink()
                else:
                    shutil.rmtree(destination)
        except OSError as exc:
            return fail(f"候选激活后验证失败，自动恢复旧安装也失败：{exc}；请保留现场并人工恢复")
        if rollback_root and rollback_root.exists():
            try:
                shutil.rmtree(rollback_root)
            except OSError as exc:
                suffix = "旧安装已恢复" if restored else "失败候选已移除"
                return fail(f"候选激活后验证失败，{suffix}，但隐藏事务目录清理失败：{exc}")
        return result

    if rollback_root and rollback_root.exists():
        try:
            shutil.rmtree(rollback_root)
        except OSError as exc:
            return fail(
                "新安装已激活并通过完整性检查，但旧隐藏副本清理失败："
                f"{exc}；当前 workflow 保持新版本，请人工清理 {rollback_root}"
            )
    return 0


def install(parent: Path, *, update: bool, source_root: Path = SOURCE) -> int:
    try:
        targets = payload_targets(source_root)
        missing = validate_source(source_root)
    except ValueError as exc:
        return fail(str(exc))
    if missing:
        return fail("当前源码不是完整发布候选：" + ", ".join(missing))
    destination = parent / NAME
    if update and destination.is_symlink():
        if not destination.is_dir() or not (destination / "SKILL.md").is_file():
            return fail(f"符号链接安装已损坏：{destination}")
        if source_root != SOURCE or not payload_matches(destination, source_root, targets):
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
    stage, result = prepare_activation_stage(parent, source_root, targets)
    if result or stage is None:
        return result or 1
    try:
        result = activate_stage(
            parent,
            stage,
            update=update,
            source_root=source_root,
            targets=targets,
        )
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
    downloaded = 0
    try:
        with urllib.request.urlopen(request, timeout=30) as response, destination.open("wb") as output:
            while chunk := response.read(1024 * 1024):
                downloaded += len(chunk)
                if downloaded > MAX_ASSET_BYTES:
                    raise ValueError(f"Release asset 超过安全字节上限：{MAX_ASSET_BYTES}")
                output.write(chunk)
                digest.update(chunk)
    except Exception:
        destination.unlink(missing_ok=True)
        raise
    actual = digest.hexdigest()
    if actual != expected_sha256:
        destination.unlink(missing_ok=True)
        raise ValueError(f"Release asset SHA-256 不匹配：expected={expected_sha256}, actual={actual}")


def normalized_archive_parts(info: zipfile.ZipInfo) -> tuple[str, ...]:
    raw = info.filename
    if (
        not raw
        or "\\" in raw
        or "\x00" in raw
        or not raw.isascii()
        or any(ord(character) < 32 or ord(character) == 127 for character in raw)
        or raw.startswith(("/", "~"))
        or re.match(r"^[A-Za-z]:", raw)
    ):
        raise ValueError(f"Release asset 包含不安全路径：{raw}")
    value = raw[:-1] if info.is_dir() and raw.endswith("/") else raw
    parts = tuple(value.split("/"))
    if not parts or any(part in {"", ".", ".."} for part in parts):
        raise ValueError(f"Release asset 包含不安全路径：{raw}")
    validate_portable_parts(parts, raw, "Release asset ")
    return parts


def extract_release(asset: Path, destination: Path) -> Path:
    with zipfile.ZipFile(asset) as archive:
        infos = archive.infolist()
        if not infos or len(infos) > MAX_ARCHIVE_FILES:
            raise ValueError(f"Release asset 文件数无效或超过安全上限：{MAX_ARCHIVE_FILES}")
        seen: set[str] = set()
        folded: set[str] = set()
        files: list[tuple[zipfile.ZipInfo, tuple[str, ...]]] = []
        total_size = 0
        for info in infos:
            parts = normalized_archive_parts(info)
            rendered = "/".join(parts)
            if rendered in seen:
                raise ValueError(f"Release asset 包含重复路径：{rendered}")
            if rendered.casefold() in folded:
                raise ValueError(f"Release asset 包含大小写冲突路径：{rendered}")
            seen.add(rendered)
            folded.add(rendered.casefold())
            if info.flag_bits & 0x1:
                raise ValueError(f"Release asset 不接受加密成员：{rendered}")
            mode = (info.external_attr >> 16) & 0xFFFF
            file_type = stat.S_IFMT(mode)
            if info.is_dir():
                if file_type not in {0, stat.S_IFDIR}:
                    raise ValueError(f"Release asset 成员不是普通文件或目录：{rendered}")
                continue
            if file_type not in {0, stat.S_IFREG}:
                raise ValueError(f"Release asset 成员不是普通文件：{rendered}")
            if info.file_size > MAX_ARCHIVE_FILE_BYTES:
                raise ValueError(f"Release asset 单文件超过安全上限：{rendered}")
            total_size += info.file_size
            if total_size > MAX_ARCHIVE_TOTAL_BYTES:
                raise ValueError(
                    f"Release asset 解压总字节超过安全上限：{MAX_ARCHIVE_TOTAL_BYTES}"
                )
            files.append((info, parts))

        skill_members = [parts for _, parts in files if parts[-1] == "SKILL.md"]
        if len(skill_members) != 1 or len(skill_members[0]) not in {1, 2}:
            raise ValueError("Release asset 必须包含唯一的根 SKILL.md")
        package_prefix = skill_members[0][0] if len(skill_members[0]) == 2 else None
        relative_files: list[tuple[zipfile.ZipInfo, tuple[str, ...]]] = []
        relative_names: set[str] = set()
        relative_folded: set[str] = set()
        for info, parts in files:
            if package_prefix is not None:
                if len(parts) < 2 or parts[0] != package_prefix:
                    raise ValueError("Release asset 包含 package 根之外的文件")
                relative_parts = parts[1:]
            else:
                relative_parts = parts
            rendered = "/".join(relative_parts)
            if rendered in relative_names or rendered.casefold() in relative_folded:
                raise ValueError(f"Release asset 包含重复或大小写冲突路径：{rendered}")
            relative_names.add(rendered)
            relative_folded.add(rendered.casefold())
            relative_files.append((info, relative_parts))
        for rendered in relative_names:
            parts = rendered.split("/")
            for index in range(1, len(parts)):
                if "/".join(parts[:index]) in relative_names:
                    raise ValueError(f"Release asset 包含文件/目录前缀冲突：{rendered}")

        destination.mkdir(parents=True, exist_ok=True)
        if any(destination.iterdir()):
            raise ValueError("Release asset 解压目标必须为空")
        for info, parts in relative_files:
            target = destination.joinpath(*parts)
            target.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(info) as source, target.open("wb") as output:
                shutil.copyfileobj(source, output, length=1024 * 1024)
    return destination


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
            targets = payload_targets(package)
            if current == version and installed_payload_matches(destination, package, targets):
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
        help=(
            "skills 父目录；Codex 本机可填 codex；"
            f"省略或填 auto 时安全探测，也可设置 {TARGET_ENV}"
        ),
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
