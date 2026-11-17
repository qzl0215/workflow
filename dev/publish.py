#!/usr/bin/env python3
"""Publish this Workflow repository through its existing release owners."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import install  # noqa: E402


PACKAGE = Path(__file__).resolve().parents[1]
REMOTE = "origin"
TARGET = "main"
REPOSITORY = "qzl0215/workflow"
ASSET_NAME = "workflow.zip"
REVIEW_NAME = "workflow-review.html"
VERSION = re.compile(r"(?:[3-9]|[1-9][0-9]+)\.(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\Z")
FULL_GATE = (
    f"{sys.executable} -B -m unittest discover -s tests -p 'test_*.py' && "
    f"{sys.executable} -B dev/release_check.py"
)


class PublishError(RuntimeError):
    """A fail-closed release precondition or delivery failure."""


def command(*parts: str, capture: bool = False) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        parts,
        cwd=PACKAGE,
        text=True,
        stdout=subprocess.PIPE if capture else None,
        stderr=subprocess.STDOUT if capture else None,
        check=False,
    )
    if capture and result.stdout:
        print(result.stdout, end="" if result.stdout.endswith("\n") else "\n")
    return result


def checked(*parts: str, capture: bool = False) -> subprocess.CompletedProcess[str]:
    result = command(*parts, capture=capture)
    if result.returncode:
        output = (result.stdout or "").strip()
        raise PublishError(output or f"command failed: {' '.join(parts)}")
    return result


def output(*parts: str) -> str:
    result = checked(*parts, capture=True)
    return (result.stdout or "").strip()


def package_version() -> str:
    return install.skill_metadata(PACKAGE / "SKILL.md").get("version", "").strip()


def release_commands(version: str, integration_sha: str, asset: Path) -> list[list[str]]:
    """Return the small owner-composition used by the real publisher."""

    return [
        [
            sys.executable,
            "-B",
            str(PACKAGE / "scripts/safe_merge.py"),
            "--remote",
            REMOTE,
            "--target",
            TARGET,
            "--verify",
            FULL_GATE,
            "--push",
            "--tag",
            version,
        ],
        [
            sys.executable,
            "-B",
            str(PACKAGE / "dev/release_check.py"),
            "--build-runtime",
            str(asset),
            "--git-ref",
            integration_sha,
        ],
        [
            "gh",
            "release",
            "create",
            version,
            "--repo",
            REPOSITORY,
            "--verify-tag",
            "--title",
            version,
            "--generate-notes",
            str(asset),
            str(asset.with_name(REVIEW_NAME)),
        ],
        [
            sys.executable,
            "-B",
            str(PACKAGE / "scripts/install.py"),
            "sync",
            "--target",
            "codex",
        ],
    ]


def remote_ref(ref: str) -> str | None:
    result = checked("git", "ls-remote", "--refs", REMOTE, ref, capture=True)
    records = [line.split() for line in (result.stdout or "").splitlines() if line.strip()]
    if not records:
        return None
    if len(records) != 1 or len(records[0]) != 2 or records[0][1] != ref:
        raise PublishError(f"ambiguous remote ref: {ref}")
    return records[0][0]


def validate_source_version(version: str) -> None:
    if not VERSION.fullmatch(version):
        raise PublishError("--version must be a stable Workflow semantic version (major >= 3)")
    actual = package_version()
    if actual != version:
        raise PublishError(f"requested version {version} does not match package version {actual or 'missing'}")
    manifest = json.loads((PACKAGE / "workflow-package.json").read_text(encoding="utf-8"))
    if manifest.get("version") != version:
        raise PublishError("workflow-package.json version does not match --version")
    changelog = (PACKAGE / "CHANGELOG.md").read_text(encoding="utf-8")
    if f"## [{version}]" not in changelog:
        raise PublishError(f"CHANGELOG.md has no {version} release entry")


def validate_candidate() -> tuple[str, str]:
    if output("git", "status", "--porcelain"):
        raise PublishError("worktree must be clean before publishing")
    branch = output("git", "branch", "--show-current")
    if not branch or branch == TARGET:
        raise PublishError(f"publish from a committed feature branch, not {TARGET}")
    return branch, output("git", "rev-parse", "HEAD")


def integration_for(version: str, candidate_sha: str, merge_command: list[str]) -> str:
    tag_ref = f"refs/tags/{version}"
    existing = remote_ref(tag_ref)
    resumed = existing is not None
    if existing is None:
        checked(*merge_command)
        existing = remote_ref(tag_ref)
        if existing is None:
            raise PublishError("atomic integration completed without the requested remote tag")
    ancestry = command("git", "merge-base", "--is-ancestor", candidate_sha, existing)
    if ancestry.returncode:
        raise PublishError(f"remote tag {version} does not contain this candidate")
    target_sha = remote_ref(f"refs/heads/{TARGET}")
    if target_sha is None or command("git", "merge-base", "--is-ancestor", existing, target_sha).returncode:
        raise PublishError(f"remote target {TARGET} does not contain tag {version}")
    if resumed:
        checked(
            sys.executable, "-B", str(PACKAGE / "scripts/safe_merge.py"),
            "--remote", REMOTE, "--target", TARGET,
            "--sync-baseline", "--confirmed-target", target_sha,
        )
    return existing


def release_state(version: str) -> dict[str, object] | None:
    result = command(
        "gh",
        "release",
        "view",
        version,
        "--repo",
        REPOSITORY,
        "--json",
        "tagName,isDraft,isPrerelease,isImmutable,assets,url",
        capture=True,
    )
    if result.returncode == 0:
        try:
            payload = json.loads(result.stdout or "")
        except json.JSONDecodeError as exc:
            raise PublishError(f"GitHub Release response was not JSON: {exc}") from exc
        if not isinstance(payload, dict):
            raise PublishError("GitHub Release response was not an object")
        return payload
    missing = (result.stdout or "").lower()
    if "release not found" in missing or "http 404" in missing or "not found" in missing:
        return None
    raise PublishError((result.stdout or "").strip() or "could not inspect GitHub Release")


def verify_release(version: str, expected_asset: Path, directory: Path) -> str:
    state = release_state(version)
    if state is None:
        raise PublishError("GitHub Release was not created")
    if state.get("tagName") != version or state.get("isDraft") or state.get("isPrerelease") or state.get('isImmutable') is not True:
        raise PublishError("GitHub Release identity or immutability state is incorrect")
    assets = state.get("assets")
    names = {item.get("name") for item in assets if isinstance(item, dict)} if isinstance(assets, list) else set()
    expected_names = {ASSET_NAME, REVIEW_NAME}
    if names != expected_names or len(assets) != len(expected_names):
        raise PublishError(f"GitHub Release assets are not exactly {sorted(expected_names)}")
    for name in sorted(expected_names):
        checked('gh', 'release', 'download', version, '--repo', REPOSITORY,
                '--pattern', name, '--dir', str(directory))
        downloaded = directory / name
        if not downloaded.is_file():
            raise PublishError(f'downloaded GitHub Release asset is missing: {name}')
        expected = hashlib.sha256(expected_asset.with_name(name).read_bytes()).hexdigest()
        actual = hashlib.sha256(downloaded.read_bytes()).hexdigest()
        if actual != expected:
            raise PublishError(f'GitHub Release asset SHA-256 does not match: {name}')
    url = state.get("url")
    return str(url) if isinstance(url, str) else ""


def comparison_base(version: str, candidate_sha: str) -> str:
    result = subprocess.run(['git', 'show', f'{candidate_sha}:CHANGELOG.md'], cwd=PACKAGE,
                            capture_output=True, text=True, check=False)
    if result.returncode:
        raise PublishError('could not read candidate CHANGELOG')
    versions = re.findall(r'^## \[(\d+\.\d+\.\d+)\]', result.stdout, re.M)
    if len(versions) < 2 or versions[0] != version:
        raise PublishError('CHANGELOG must identify this and the preceding release')
    base = output('git', 'rev-parse', '--verify', f'refs/tags/{versions[1]}^{{commit}}')
    checked('git', 'merge-base', '--is-ancestor', base, candidate_sha)
    return base


def publish(version: str) -> None:
    validate_source_version(version)
    branch, candidate_sha = validate_candidate()
    base = comparison_base(version, candidate_sha)
    checked("git", "push", "--set-upstream", REMOTE, f"HEAD:refs/heads/{branch}")
    with tempfile.TemporaryDirectory(prefix=f"workflow-{version}-release-") as raw_temp:
        temp = Path(raw_temp)
        asset = temp / ASSET_NAME
        commands = release_commands(version, "0" * 40, asset)
        integration_sha = integration_for(version, candidate_sha, commands[0])
        build = release_commands(version, integration_sha, asset)[1]
        checked(*build)
        # The prior changelog version pins the comparison on retries; never use
        # a moving latest tag or dirty worktree to rebuild immutable assets.
        if comparison_base(version, integration_sha) != base:
            raise PublishError('integration changed the release comparison baseline')
        checked('git', 'merge-base', '--is-ancestor', base, integration_sha)
        checked(sys.executable, '-B', str(PACKAGE/'dev/generate_visual_map.py'),
                '--base', base, '--target', integration_sha, '--review-output', str(temp/REVIEW_NAME))
        if release_state(version) is None:
            create = release_commands(version, integration_sha, asset)[2]
            checked(*create)
        verify_dir = temp / "downloaded"
        verify_dir.mkdir()
        release_url = verify_release(version, asset, verify_dir)
        sync = release_commands(version, integration_sha, asset)[3]
        checked(*sync)
        installed = install.skill_metadata(
            install.resolve_target("codex", "check") / install.NAME / "SKILL.md"
        ).get("version", "")
        if installed != version:
            raise PublishError(f"local Codex version {installed or 'missing'} does not match {version}")
    print(f"workflow_publish: COMPLETE version={version} commit={integration_sha} release={release_url}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", required=True)
    parser.add_argument("--yes", action="store_true", help="confirm the formal public release")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.yes:
        print("workflow_publish: --yes is required for a formal public release", file=sys.stderr)
        return 2
    try:
        publish(args.version)
    except (OSError, ValueError, PublishError) as exc:
        print(f"workflow_publish: ERROR: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
