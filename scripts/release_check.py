#!/usr/bin/env python3
"""Static package or full-release gate for workflow."""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

from workflow_doctor import LEGACY_STAGE_WORD, PUBLIC_TARGETS, discover_package_files


PACKAGE = Path(__file__).resolve().parents[1]
RELEASE_ONLY = {
    "README.md",
    "LICENSE",
    "NOTICE.md",
    "SECURITY.md",
    "CONTRIBUTING.md",
    "CHANGELOG.md",
    "scripts/install.py",
}
TEXT_SUFFIXES = {".md", ".html"}
CONFLICT_MARKERS = ("<<<<<<<", "=======", ">>>>>>>")
CREDENTIAL = re.compile(
    r"(?i)(?:api[_-]?key|secret|password|access[_-]?token)\s*[:=]\s*['\"]?[^\s'\"]{8,}"
)
def command(errors: list[str], *parts: str) -> None:
    result = subprocess.run(
        [sys.executable, "-B", *parts],
        cwd=PACKAGE,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    if result.returncode:
        errors.append(f"command failed: {' '.join(parts)}\n{result.stdout.strip()}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--package",
        action="store_true",
        help="Check the P02-P06 package before release-only docs/install are added",
    )
    args = parser.parse_args()
    errors: list[str] = []

    package_files = discover_package_files(PACKAGE)
    actual = {path.relative_to(PACKAGE).as_posix() for path in package_files}
    expected = PUBLIC_TARGETS - RELEASE_ONLY if args.package else PUBLIC_TARGETS
    missing = sorted(expected - actual)
    extras = sorted(actual - expected)
    if missing:
        errors.append("missing target files: " + ", ".join(missing))
    if extras:
        errors.append("files outside public manifest: " + ", ".join(extras))

    command(errors, "scripts/workflow_doctor.py")
    command(errors, "scripts/generate_visual_map.py", "--check")

    scan_paths = [
        path
        for path in package_files
        if (path.suffix in TEXT_SUFFIXES or path.name in {"SKILL.md", "LICENSE"})
        and "tests" not in path.parts
        and "scripts" not in path.parts
    ]
    for path in scan_paths:
        text = path.read_text(encoding="utf-8", errors="replace")
        for marker in CONFLICT_MARKERS:
            if marker in text:
                errors.append(f"{path.relative_to(PACKAGE)}: conflict marker {marker}")
        if CREDENTIAL.search(text):
            errors.append(f"{path.relative_to(PACKAGE)}: sensitive-looking credential assignment")
        relative = path.relative_to(PACKAGE)
        is_formal_contract = relative.suffix in TEXT_SUFFIXES and relative.as_posix() != "CHANGELOG.md"
        if is_formal_contract:
            matches = sorted({match.group(0) for match in LEGACY_STAGE_WORD.finditer(text)})
            if matches:
                errors.append(
                    f"{relative}: legacy stage words escaped read-boundary compatibility: "
                    + ", ".join(matches)
                )

    if not args.package:
        license_text = (PACKAGE / "LICENSE").read_text(encoding="utf-8", errors="replace") if (PACKAGE / "LICENSE").exists() else ""
        notice = (PACKAGE / "NOTICE.md").read_text(encoding="utf-8", errors="replace") if (PACKAGE / "NOTICE.md").exists() else ""
        if "MIT License" not in license_text or "Permission is hereby granted" not in license_text:
            errors.append("LICENSE: incomplete MIT text")
        for token in ("Attribution", "Clean-room", "Excluded"):
            if token not in notice:
                errors.append(f"NOTICE.md: missing `{token}` section")

    if errors:
        print("RELEASE CHECK ERRORS:")
        for item in errors:
            print(f"- {item}")
        return 1
    mode = "package" if args.package else "release"
    print(f"workflow_release_check: OK ({mode}, files={len(expected)})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
