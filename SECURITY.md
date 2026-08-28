# Security policy

## Supported versions

Security fixes are prepared for the latest published beta or stable release. Development snapshots are supported on a best-effort basis.

## Reporting a vulnerability

Do not open a public issue for credentials, sensitive paths, command injection, unsafe destructive actions, or another privately exploitable finding. Use GitHub's private vulnerability reporting for this repository. If it is unavailable, contact the repository owner through their GitHub profile and request a private channel without including exploit details in the first message.

Include the affected version, environment, minimal reproduction, impact, and any safe mitigation. Do not access data or systems beyond what is necessary to demonstrate the issue.

## Security boundaries

- workflow does not require secrets and must not store credentials in plans, logs, templates, or examples.
- commit, push, merge, deploy, delete, public release, and other external writes require explicit authorization.
- install/update validates a complete candidate in a same-filesystem hidden stage before replacing the single active package. Caught activation failures restore the old install; no discoverable backup, failed, or removed copy is retained after success. The two-rename transaction is not claimed to be crash-atomic across forced process termination or host power loss.
- remote sync accepts only the official latest non-draft, non-prerelease, immutable GitHub Release, verifies the asset SHA-256 and package version, and runs exactly one candidate gate before replacement. Legacy 2.x packages use the installer's frozen public target set; 3.x+ packages require a regular manifest and install an exact runtime file set with per-file SHA-256. Declared `source_only` entries are an optional checkout allowlist and are never installed.
- release archives are extracted member by member and reject unsafe, duplicate, case-colliding, encrypted, linked, special, oversized, or ambiguous-root entries before package validation.
- uninstall permanently removes the active package after explicit `--yes`; users who need rollback must reinstall a specific verified Release.
- reports about third-party agents, Git providers, or runtimes may need to be filed with those maintainers as well.
