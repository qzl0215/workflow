#!/usr/bin/env python3
"""生成 Workflow 3.x manifest、执行发布门禁并构建精简运行时。"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import stat
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

import install
import workflow_doctor


PACKAGE = Path(__file__).resolve().parents[1]
RUNTIME_FILES = workflow_doctor.EXPECTED_RUNTIME_FILES
SOURCE_ONLY_FILES = frozenset(
    {
        ".gitignore",
        "AGENTS.md",
        "README.md",
        "SECURITY.md",
        "CONTRIBUTING.md",
        "CHANGELOG.md",
        "docs/workflow-visual-map.html",
        "scripts/generate_visual_map.py",
        "scripts/release_check.py",
        "tests/test_portability.py",
        "tests/test_protocol_v3.py",
        "tests/test_release_v3.py",
        "tests/test_safe_merge.py",
        "tests/test_work_context.py",
    }
)
EXPECTED_SOURCE_FILES = RUNTIME_FILES | SOURCE_ONLY_FILES | {install.RUNTIME_MANIFEST_NAME}
IMMUTABLE_COMMIT = re.compile(r"(?:[0-9a-f]{40}|[0-9a-f]{64})\Z")


class ReleaseError(ValueError):
    """可直接向发布者展示的失败关闭错误。"""


def sha256_bytes(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def current_version(package: Path) -> str:
    version = install.skill_metadata(package / "SKILL.md").get("version", "").strip()
    if not re.fullmatch(r"3\.\d+\.\d+(?:[-+][0-9A-Za-z.-]+)?", version):
        raise ReleaseError("SKILL.md: Workflow 3.x version 无效")
    return version


def source_inventory_errors(package: Path, *, allow_missing_manifest: bool = False) -> list[str]:
    actual = install.package_files(package)
    expected = EXPECTED_SOURCE_FILES
    missing = expected - actual
    if allow_missing_manifest:
        missing -= {install.RUNTIME_MANIFEST_NAME}
    extras = actual - expected
    errors: list[str] = []
    if missing:
        errors.append("源码缺少声明文件：" + ", ".join(sorted(missing)))
    if extras:
        errors.append("源码包含未声明文件：" + ", ".join(sorted(extras)))
    for relative in sorted(actual & expected):
        path = package / relative
        if path.is_symlink() or not path.is_file():
            errors.append(f"源码声明目标不是普通文件：{relative}")
    return errors


def manifest_document(package: Path) -> dict[str, object]:
    errors = source_inventory_errors(package, allow_missing_manifest=True)
    if errors:
        raise ReleaseError("；".join(errors))
    files: dict[str, str] = {}
    for relative in sorted(RUNTIME_FILES):
        path = package / relative
        if path.is_symlink() or not path.is_file():
            raise ReleaseError(f"无法生成 manifest；runtime 目标不是普通文件：{relative}")
        files[relative] = sha256_bytes(path.read_bytes())
    return {
        "schema": install.RUNTIME_MANIFEST_SCHEMA,
        "name": install.NAME,
        "version": current_version(package),
        "entrypoint": "SKILL.md",
        "runtime": {"files": files},
        "source_only": sorted(SOURCE_ONLY_FILES),
    }


def write_manifest(package: Path = PACKAGE) -> Path:
    document = manifest_document(package)
    destination = package / install.RUNTIME_MANIFEST_NAME
    rendered = json.dumps(document, ensure_ascii=False, indent=2) + "\n"
    handle, raw_temp = tempfile.mkstemp(prefix=".workflow-package-", suffix=".json", dir=package)
    temp = Path(raw_temp)
    try:
        with os.fdopen(handle, "w", encoding="utf-8", newline="\n") as output:
            output.write(rendered)
            output.flush()
            os.fsync(output.fileno())
        os.replace(temp, destination)
    except Exception:
        temp.unlink(missing_ok=True)
        raise
    return destination


def manifest_policy_errors(package: Path) -> list[str]:
    errors = source_inventory_errors(package)
    try:
        targets, source_only = install.payload_spec(package)
    except (OSError, UnicodeError, ValueError) as exc:
        errors.append(str(exc))
        return errors
    runtime = targets - {install.RUNTIME_MANIFEST_NAME}
    if runtime != RUNTIME_FILES:
        missing = sorted(RUNTIME_FILES - runtime)
        extras = sorted(runtime - RUNTIME_FILES)
        if missing:
            errors.append("manifest 缺少 runtime：" + ", ".join(missing))
        if extras:
            errors.append("manifest 多出 runtime：" + ", ".join(extras))
    if source_only != SOURCE_ONLY_FILES:
        missing = sorted(SOURCE_ONLY_FILES - source_only)
        extras = sorted(source_only - SOURCE_ONLY_FILES)
        if missing:
            errors.append("manifest 缺少 source_only：" + ", ".join(missing))
        if extras:
            errors.append("manifest 多出 source_only：" + ", ".join(extras))
    return errors


def run_python(package: Path, relative: str, *arguments: str) -> tuple[int, str]:
    result = subprocess.run(
        [sys.executable, "-B", str(package / relative), *arguments],
        cwd=package,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    return result.returncode, result.stdout.strip()


def legal_errors(package: Path) -> list[str]:
    errors: list[str] = []
    try:
        license_text = (package / "LICENSE").read_text(encoding="utf-8")
    except OSError as exc:
        errors.append(f"LICENSE: 无法读取：{exc}")
        license_text = ""
    if "MIT License" not in license_text or "Permission is hereby granted" not in license_text:
        errors.append("LICENSE: MIT 授权正文不完整")
    try:
        notice = (package / "NOTICE.md").read_text(encoding="utf-8")
    except OSError as exc:
        errors.append(f"NOTICE.md: 无法读取：{exc}")
        notice = ""
    for token in ("Attribution", "Clean-room", "Excluded"):
        if token not in notice:
            errors.append(f"NOTICE.md: 缺少 {token} 段落")
    return errors


def release_gate(package: Path = PACKAGE) -> list[str]:
    """组合门只编排一次 doctor 和一次生成物校验。"""

    errors = manifest_policy_errors(package)
    errors.extend(legal_errors(package))
    doctor_code, doctor_output = run_python(package, "scripts/workflow_doctor.py")
    if doctor_code:
        errors.append("workflow doctor 失败：\n" + doctor_output)
    visual_code, visual_output = run_python(package, "scripts/generate_visual_map.py", "--check")
    if visual_code:
        errors.append("视觉地图校验失败：\n" + visual_output)
    return errors


def git_output(repo: Path, *arguments: str, text: bool = False) -> bytes | str:
    result = subprocess.run(
        ["git", *arguments],
        cwd=repo,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=text,
        check=False,
    )
    if result.returncode:
        stderr = result.stderr.strip() if text else result.stderr.decode("utf-8", errors="replace").strip()
        raise ReleaseError(f"git {' '.join(arguments)} 失败：{stderr}")
    return result.stdout


def resolve_immutable_commit(repo: Path, raw: str) -> str:
    value = raw.strip()
    if not IMMUTABLE_COMMIT.fullmatch(value):
        raise ReleaseError("--git-ref 必须是完整小写 commit SHA，不能使用可移动分支或 tag")
    resolved = str(git_output(repo, "rev-parse", "--verify", f"{value}^{{commit}}", text=True)).strip()
    if resolved != value:
        raise ReleaseError("--git-ref 未精确解析到所给 commit SHA")
    return resolved


def git_tree(repo: Path, commit: str) -> dict[str, tuple[str, str, str]]:
    payload = bytes(git_output(repo, "ls-tree", "-r", "-z", commit))
    tree: dict[str, tuple[str, str, str]] = {}
    for record in payload.split(b"\0"):
        if not record:
            continue
        try:
            metadata, raw_path = record.split(b"\t", 1)
            mode, kind, object_id = metadata.decode("ascii").split(" ", 2)
            path = raw_path.decode("utf-8")
        except (UnicodeError, ValueError) as exc:
            raise ReleaseError(f"commit 树包含无法解析的路径：{exc}") from exc
        normalized = install.normalize_manifest_path(path)
        if normalized != path or path in tree:
            raise ReleaseError(f"commit 树包含重复或非规范路径：{path}")
        tree[path] = (mode, kind, object_id)
    return tree


def git_blob(repo: Path, object_id: str) -> bytes:
    return bytes(git_output(repo, "cat-file", "blob", object_id))


def ref_manifest(repo: Path, tree: dict[str, tuple[str, str, str]]) -> tuple[dict[str, object], bytes]:
    entry = tree.get(install.RUNTIME_MANIFEST_NAME)
    if entry is None:
        raise ReleaseError("commit 缺少 workflow-package.json")
    mode, kind, object_id = entry
    if kind != "blob" or mode not in {"100644", "100755"}:
        raise ReleaseError("commit 中 workflow-package.json 不是普通文件")
    payload = git_blob(repo, object_id)
    try:
        document = json.loads(payload.decode("utf-8"), object_pairs_hook=install.unique_json_object)
    except (UnicodeError, json.JSONDecodeError, ValueError) as exc:
        raise ReleaseError(f"commit 中 workflow-package.json 无效：{exc}") from exc
    if not isinstance(document, dict):
        raise ReleaseError("commit 中 workflow-package.json 必须是对象")
    runtime = document.get("runtime")
    raw_files = runtime.get("files") if isinstance(runtime, dict) else None
    raw_source = document.get("source_only")
    if not isinstance(raw_files, dict) or not isinstance(raw_source, list):
        raise ReleaseError("commit manifest 缺少 runtime.files 或 source_only")
    try:
        runtime_files = frozenset(install.normalize_manifest_path(path) for path in raw_files)
        source_only = frozenset(install.normalize_manifest_path(path) for path in raw_source)
    except ValueError as exc:
        raise ReleaseError(str(exc)) from exc
    if runtime_files != RUNTIME_FILES or source_only != SOURCE_ONLY_FILES:
        raise ReleaseError("commit manifest 与 Workflow 3.0 发布拓扑不一致")
    if set(tree) != EXPECTED_SOURCE_FILES:
        missing = sorted(EXPECTED_SOURCE_FILES - set(tree))
        extras = sorted(set(tree) - EXPECTED_SOURCE_FILES)
        details: list[str] = []
        if missing:
            details.append("缺少 " + ", ".join(missing))
        if extras:
            details.append("多出 " + ", ".join(extras))
        raise ReleaseError("commit 源码清单不精确：" + "；".join(details))
    for relative, (item_mode, item_kind, _) in tree.items():
        if item_kind != "blob" or item_mode not in {"100644", "100755"}:
            raise ReleaseError(f"commit 中源码目标不是普通文件：{relative}")
    return document, payload


def validate_ref_files(
    repo: Path,
    tree: dict[str, tuple[str, str, str]],
    document: dict[str, object],
) -> dict[str, bytes]:
    raw_files = document["runtime"]["files"]  # type: ignore[index]
    selected: dict[str, bytes] = {}
    for relative in sorted(RUNTIME_FILES):
        mode, kind, object_id = tree[relative]
        if kind != "blob" or mode not in {"100644", "100755"}:
            raise ReleaseError(f"commit 中声明目标不是普通文件：{relative}")
        payload = git_blob(repo, object_id)
        digest = raw_files.get(relative) if isinstance(raw_files, dict) else None
        if digest != sha256_bytes(payload):
            raise ReleaseError(f"commit manifest SHA-256 不匹配：{relative}")
        selected[relative] = payload
    return selected


def deterministic_zip(destination: Path, files: dict[str, bytes]) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        raise ReleaseError(f"拒绝覆盖已有 runtime asset：{destination}")
    handle, raw_temp = tempfile.mkstemp(prefix=f".{destination.name}.", suffix=".tmp", dir=destination.parent)
    os.close(handle)
    temp = Path(raw_temp)
    try:
        with zipfile.ZipFile(temp, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
            for relative in sorted(files):
                info = zipfile.ZipInfo(relative, date_time=(1980, 1, 1, 0, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED
                info.create_system = 3
                info.external_attr = (stat.S_IFREG | 0o644) << 16
                archive.writestr(info, files[relative], compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
        os.replace(temp, destination)
    except Exception:
        temp.unlink(missing_ok=True)
        raise


def build_runtime_archive(repo: Path, destination: Path, git_ref: str) -> tuple[str, str]:
    commit = resolve_immutable_commit(repo, git_ref)
    tree = git_tree(repo, commit)
    document, manifest_payload = ref_manifest(repo, tree)
    runtime_payload = validate_ref_files(repo, tree, document)
    runtime_payload[install.RUNTIME_MANIFEST_NAME] = manifest_payload

    with tempfile.TemporaryDirectory(prefix="workflow-runtime-check-") as raw_stage:
        stage = Path(raw_stage)
        for relative, payload in runtime_payload.items():
            path = stage / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(payload)
        try:
            install.payload_spec(stage)
        except (OSError, UnicodeError, ValueError) as exc:
            raise ReleaseError(f"精简 runtime 自校验失败：{exc}") from exc
        errors, _ = workflow_doctor.inspect_package(stage)
        if errors:
            raise ReleaseError("精简 runtime doctor 失败：" + "；".join(errors))

    deterministic_zip(destination, runtime_payload)
    digest = sha256_bytes(destination.read_bytes())
    return commit, digest


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--write-manifest", action="store_true", help="按正式拓扑刷新 version 与逐文件 SHA-256")
    result.add_argument("--build-runtime", metavar="OUTPUT", type=Path, help="从不可变 commit 构建 runtime-only ZIP")
    result.add_argument("--git-ref", metavar="COMMIT_SHA", help="完整、不可移动的 commit SHA")
    return result


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    if args.write_manifest and (args.build_runtime or args.git_ref):
        print("release_check: --write-manifest 不能与构建参数并用", file=sys.stderr)
        return 2
    if bool(args.build_runtime) != bool(args.git_ref):
        print("release_check: --build-runtime 与 --git-ref 必须同时提供", file=sys.stderr)
        return 2
    try:
        if args.write_manifest:
            path = write_manifest(PACKAGE)
            print(f"workflow_manifest: WRITTEN {path}")
            return 0
        if args.build_runtime:
            commit, digest = build_runtime_archive(PACKAGE, args.build_runtime.resolve(), args.git_ref)
            print(f"workflow_runtime: BUILT commit={commit} digest={digest} path={args.build_runtime.resolve()}")
            return 0
        errors = release_gate(PACKAGE)
    except (OSError, UnicodeError, ReleaseError, ValueError, zipfile.BadZipFile) as exc:
        print(f"workflow_release_check: ERROR\n- {exc}")
        return 1
    if errors:
        print("WORKFLOW RELEASE CHECK ERRORS:")
        for item in errors:
            print(f"- {item}")
        return 1
    print(f"workflow_release_check: OK (runtime={len(RUNTIME_FILES) + 1}, source={len(EXPECTED_SOURCE_FILES)})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
