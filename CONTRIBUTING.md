# Contributing

Contributions are welcome when they improve an observable workflow result without adding a second truth source or a new external skill dependency.

## Before changing the package

1. Open or link an issue that states the user-visible problem, evidence, and smallest useful outcome.
2. Identify the existing owner. Prefer improving one reference/template/script over adding a file.
3. Add a failing test or explain why RED/GREEN does not apply.
4. Keep `SKILL.md` as a router, references under 250 lines, and Foundation limited to the single Minimum Readiness Gate.

## Required checks

```bash
python3 -B -m unittest discover -s tests -p 'test_*.py' -v
python3 -B scripts/workflow_doctor.py
python3 -B scripts/generate_visual_map.py --check
python3 -B scripts/release_check.py
```

If the root route or state table changes, regenerate the visual map. If templates change, update every reader/writer test. Never commit credentials, private paths, production reports, generated caches, or organization-specific release implementations.

## Pull requests

Describe the user outcome, removed or merged complexity, tests and actual results, compatibility impact, and residual risks. Keep unrelated cleanup separate. A green check does not authorize maintainers to deploy or publish external systems.
