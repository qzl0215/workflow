#!/usr/bin/env python3
"""Fail-closed structural checks for the public workflow package."""

from __future__ import annotations

import re
import sys
from pathlib import Path


REQUIRED_REFERENCES = (
    "understand-goal.md",
    "decide-solution.md",
    "plan-tasks.md",
    "execute-tasks.md",
    "verify-deliver.md",
    "learn-review.md",
    "evolve-system.md",
    "challenge-decisions.md",
    "shape-experience.md",
    "maintain-design.md",
    "coordinate-agents.md",
    "merge-parallel-work.md",
    "fix-failures.md",
    "handoff-context.md",
)

REQUIRED_TEMPLATES = (
    "index.md",
    "findings.md",
    "task_plan.md",
    "implementation-plan.md",
    "progress.md",
    "task-owner-prompt.md",
    "pre-plan-contract.md",
)
LEGACY_REFERENCES = (
    "project-discovery.md",
    "context-discovery.md",
    "clarify-prioritize.md",
    "solution-design.md",
    "experience-design.md",
    "design-system.md",
    "write-plan.md",
    "act-plan.md",
    "delegation.md",
    "debugging-recovery.md",
    "verification.md",
    "finish-release.md",
    "context-handoff.md",
    "evolution-loop.md",
    "context-reset-handoff.md",
    "delegation-orchestration.md",
    "failure-recovery.md",
    "finish-git-release.md",
    "owner-execution.md",
    "parallel-merge-governance.md",
    "partner-clarify.md",
    "priority-discovery.md",
    "skill-routing.md",
    "strategic-review.md",
)
FORBIDDEN_FOUNDATION_NAMES = (
    "project_foundation.py",
    "foundation-catalog.md",
    "foundation-manifest.md",
    "foundation-profile.md",
)
LEGACY_SCRIPTS = ("acceptance_test.py", "test_context_capsule.py", "safe-push.sh")
ROOT_TOKENS = (
    "dependency-closed",
    "需求澄清 → 选定方案 → 拆成任务 → 执行任务 → 验收交付 → 提炼经验 → 回灌改进",
    "事实可查",
    "取舍待定",
    "假设待验",
    "外部待解",
    "H0",
    "H3",
    "未经明确授权",
    "不声称完成",
    "无 subagent",
    "无 memory",
    "无 Git",
)
PROTOCOL_OWNERS = {
    "## 状态接口与硬门": "SKILL.md",
    "## 需求澄清中的四路未知": "SKILL.md",
    "## harness 深度": "SKILL.md",
    "## 角色、权限与降级": "SKILL.md",
    "# 需求澄清\n": "references/understand-goal.md",
    "# 选定方案\n": "references/decide-solution.md",
    "# 拆成任务\n": "references/plan-tasks.md",
    "# 执行任务\n": "references/execute-tasks.md",
    "# 验收交付\n": "references/verify-deliver.md",
    "# 提炼经验\n": "references/learn-review.md",
    "# 回灌改进\n": "references/evolve-system.md",
    "# 关键追问与反向挑战\n": "references/challenge-decisions.md",
    "# 体验塑形\n": "references/shape-experience.md",
    "# 维护设计真源\n": "references/maintain-design.md",
    "# 协调 Agent\n": "references/coordinate-agents.md",
    "# 并行成果合并\n": "references/merge-parallel-work.md",
    "# 修复失败\n": "references/fix-failures.md",
    "# 有界上下文交接\n": "references/handoff-context.md",
}
PUBLIC_TARGETS = {
    ".gitignore",
    "SKILL.md",
    "README.md",
    "LICENSE",
    "NOTICE.md",
    "SECURITY.md",
    "CONTRIBUTING.md",
    "CHANGELOG.md",
    *(f"references/{name}" for name in REQUIRED_REFERENCES),
    *(f"templates/{name}" for name in REQUIRED_TEMPLATES),
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
MAX_PACKAGE_FILES = 45
MAX_PACKAGE_BYTES = 400_000
MAX_REFERENCE_LINES = 1_200
CONFLICT_MARKERS = ("<<<<<<<", "=======", ">>>>>>>")
REFERENCE_LINK = re.compile(r"references/([A-Za-z0-9_-]+\.md)")
SECRET_ASSIGNMENT = re.compile(
    r"(?i)(?:api[_-]?key|secret|password|access[_-]?token)\s*[:=]\s*['\"]?[^\s'\"]{8,}"
)
EXTERNAL_SKILL_CALL = re.compile(
    r"(?:\$[A-Za-z][A-Za-z0-9_-]*|(?:call|invoke|调用|启用)\s+[`$]?[A-Za-z][A-Za-z0-9_-]*(?:`|\s+skill|\s+技能))",
    re.IGNORECASE,
)
MACHINE_PATH = re.compile(
    r"(?:/(?:Users|home|opt)/[A-Za-z0-9._-]+|[A-Za-z]:\\Users\\[^\\\s`]+|\.(?:codex|claude)/skills/)"
)
LEGACY_STAGE_NAMES = (
    "看清目标",
    "Intake",
    "Clarify",
    "Readiness",
    "Solution",
    "Strategic Planning",
    "Experience",
    "Write",
    "Write Plan",
    "Act",
    "Act Plan",
    "Debug",
    "Verify",
    "Finish",
)
LEGACY_STAGE_WORD = re.compile(
    r"(?<![A-Za-z0-9_])(?:"
    + "|".join(re.escape(value) for value in sorted(LEGACY_STAGE_NAMES, key=len, reverse=True))
    + r")(?![A-Za-z0-9_])"
)
IGNORED_PACKAGE_PARTS = frozenset({".git"})


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def discover_package_files(package: Path) -> list[Path]:
    """Return public working-tree files while excluding VCS metadata."""
    return sorted(
        path
        for path in package.rglob("*")
        if path.is_file()
        and not IGNORED_PACKAGE_PARTS.intersection(path.relative_to(package).parts)
    )


def error(errors: list[str], path: Path, message: str) -> None:
    errors.append(f"{path}: {message}")


def main() -> int:
    package = Path(sys.argv[1] if len(sys.argv) > 1 else Path(__file__).resolve().parents[1]).resolve()
    skill = package / "SKILL.md"
    refs = package / "references"
    templates = package / "templates"
    errors: list[str] = []
    warnings: list[str] = []

    skill_files = sorted(package.rglob("SKILL.md"))
    if skill_files != [skill]:
        rendered = ", ".join(str(path.relative_to(package)) for path in skill_files) or "none"
        error(errors, package, f"expected exactly one root SKILL.md; found {rendered}")
    if not skill.exists():
        report(errors, warnings)
        return 1

    skill_text = read(skill)
    markdown = [skill]

    package_files = discover_package_files(package)
    relative_files = {path.relative_to(package).as_posix() for path in package_files}
    if len(package_files) > MAX_PACKAGE_FILES:
        error(errors, package, f"package has {len(package_files)} files; budget is {MAX_PACKAGE_FILES}")
    package_bytes = sum(path.stat().st_size for path in package_files)
    if package_bytes > MAX_PACKAGE_BYTES:
        error(errors, package, f"package is {package_bytes} bytes; budget is {MAX_PACKAGE_BYTES}")
    for extra in sorted(relative_files - PUBLIC_TARGETS):
        error(errors, package / extra, "file is not owned by the public target manifest")
    for link in package.rglob("*"):
        if IGNORED_PACKAGE_PARTS.intersection(link.relative_to(package).parts):
            continue
        if link.is_symlink():
            error(errors, link, "symlinks must not ship in the portable package")

    if not skill_text.startswith("---\n") or "name: workflow" not in skill_text.split("---", 2)[1]:
        error(errors, skill, "missing workflow frontmatter")
    if len(skill_text.splitlines()) > 150:
        error(errors, skill, "entrypoint exceeds 150 lines")
    if len(skill_text) > 10000:
        error(errors, skill, "entrypoint exceeds 10,000 characters")
    for token in ROOT_TOKENS:
        if token not in skill_text:
            error(errors, skill, f"missing root contract `{token}`")

    actual_refs = sorted(refs.glob("*.md")) if refs.exists() else []
    actual_names = {path.name for path in actual_refs}
    expected_names = set(REQUIRED_REFERENCES)
    for name in sorted(expected_names - actual_names):
        error(errors, refs / name, "missing required reference")
    for name in sorted(actual_names - expected_names):
        error(errors, refs / name, "orphan or unowned reference")
    for name in REQUIRED_REFERENCES:
        if skill_text.count(f"`references/{name}`") != 1:
            error(errors, skill, f"must route exactly once to references/{name}")
    markdown.extend(actual_refs)
    reference_lines = sum(len(read(path).splitlines()) for path in actual_refs)
    if reference_lines > MAX_REFERENCE_LINES:
        error(errors, refs, f"references total {reference_lines} lines; budget is {MAX_REFERENCE_LINES}")

    actual_templates = {path.name for path in templates.glob("*.md")} if templates.exists() else set()
    expected_templates = set(REQUIRED_TEMPLATES)
    for name in sorted(expected_templates - actual_templates):
        if not (templates / name).is_file():
            error(errors, templates / name, "missing runtime truth-source template")
    for name in sorted(actual_templates - expected_templates):
        error(errors, templates / name, "orphan or duplicate template")
    status_registry = "pending / in_progress / completed / blocked"
    for path in sorted(templates.glob("*.md")):
        if path.name != "task_plan.md" and status_registry in read(path):
            error(errors, path, "duplicates the Plan/Task status registry owned by task_plan.md")
    for name in LEGACY_REFERENCES:
        if (refs / name).exists():
            error(errors, refs / name, "legacy reference remains")
    for name in LEGACY_SCRIPTS:
        if (package / "scripts" / name).exists():
            error(errors, package / "scripts" / name, "legacy or duplicate tool owner remains")

    for path in markdown:
        text = read(path)
        if len(text.splitlines()) > 250:
            error(errors, path, "reference exceeds 250 lines")
        for marker in CONFLICT_MARKERS:
            if marker in text:
                error(errors, path, f"conflict marker remains: {marker}")
        if SECRET_ASSIGNMENT.search(text):
            error(errors, path, "sensitive-looking credential assignment")
        if MACHINE_PATH.search(text):
            error(errors, path, "machine-specific absolute or skills path remains")
        if EXTERNAL_SKILL_CALL.search(text) or re.search(r"(?:^|[/.])skills/[A-Za-z0-9_-]+", text):
            error(errors, path, "external skill invocation remains")
        for target in set(REFERENCE_LINK.findall(text)):
            if not (refs / target).is_file():
                error(errors, path, f"broken reference link: references/{target}")
            elif path.parent == refs:
                error(errors, path, f"reference-to-reference deep link is not allowed: references/{target}")

    protocol_files = [skill, *actual_refs, *sorted(templates.glob("*.md"))]
    for path in protocol_files:
        matches = sorted({match.group(0) for match in LEGACY_STAGE_WORD.finditer(read(path))})
        if matches:
            error(errors, path, "legacy stage words escaped read-boundary compatibility: " + ", ".join(matches))
    for heading, owner in PROTOCOL_OWNERS.items():
        hits = [path.relative_to(package).as_posix() for path in protocol_files if heading in read(path)]
        if hits != [owner]:
            error(errors, package / owner, f"protocol `{heading}` owner mismatch; found {hits or 'none'}")

    for forbidden in FORBIDDEN_FOUNDATION_NAMES:
        if any(
            path.name == forbidden
            and not IGNORED_PACKAGE_PARTS.intersection(path.relative_to(package).parts)
            for path in package.rglob("*")
        ):
            error(errors, package, f"overbuilt Foundation artifact remains: {forbidden}")

    for cache in list(package.rglob("__pycache__")) + list(package.rglob("*.pyc")):
        if IGNORED_PACKAGE_PARTS.intersection(cache.relative_to(package).parts):
            continue
        error(errors, cache, "compiled cache must not ship")
    report(errors, warnings)
    return 1 if errors else 0


def report(errors: list[str], warnings: list[str]) -> None:
    if errors:
        print("ERRORS:")
        for item in errors:
            print(f"- {item}")
    if warnings:
        print("WARNINGS:")
        for item in warnings:
            print(f"- {item}")
    if not errors:
        print("workflow_doctor: OK" + (" with warnings" if warnings else ""))


if __name__ == "__main__":
    raise SystemExit(main())
