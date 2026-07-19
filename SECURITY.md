# Security policy

## Supported versions

Security fixes are prepared for the latest published beta or stable release. Development snapshots are supported on a best-effort basis.

## Reporting a vulnerability

Do not open a public issue for credentials, sensitive paths, command injection, unsafe destructive actions, or another privately exploitable finding. Use GitHub's private vulnerability reporting for this repository. If it is unavailable, contact the repository owner through their GitHub profile and request a private channel without including exploit details in the first message.

Include the affected version, environment, minimal reproduction, impact, and any safe mitigation. Do not access data or systems beyond what is necessary to demonstrate the issue.

## Security boundaries

- workflow does not require secrets and must not store credentials in plans, logs, templates, or examples.
- commit, push, merge, deploy, delete, public release, and other external writes require explicit authorization.
- install/update keeps a recoverable backup; uninstall renames the installation instead of permanently deleting it.
- reports about third-party agents, Git providers, or runtimes may need to be filed with those maintainers as well.
