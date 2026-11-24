# Instructions for AI coding agents

You are reading the Wemo Ops Center repository. Follow [CONTRIBUTING.md](CONTRIBUTING.md) for the full process; this file is the short version, plus the rules that matter most for agents.

## Process

1. **This GitHub repository is a mirror.** The primary repository is the maintainer's GitLab; GitHub receives `main` and tags from it. Never merge, push to `main`, push tags, edit releases or change settings on GitHub. Anything merged here is overwritten by the next mirror push.
2. **Contribute through a GitHub pull request** against `main` (or a patch in an issue). The maintainer moves accepted changes to GitLab and credits the author. Branch names: `fix/…`, `feat/…`, `docs/…`.
3. **Open an issue first** for anything beyond a small fix, and check open issues for duplicates.
4. **Security vulnerabilities never go in public issues, PRs, commits or comments.** Report them privately through GitHub's *Report a vulnerability* (Security tab), as described in [SECURITY.md](SECURITY.md). If you find one while doing other work, stop and tell your user instead of fixing it in public.
5. Don't comment on, close or label issues and PRs unless your user asked you to.

## Before you change code

- Check the current version (`grep -n '^VERSION' universal-app/wemo_ops_universal.py`), the newest file in `release-notes/` and recent `git log`.
- Read the scope in CONTRIBUTING.md: local-only, no cloud account, not a general smart-home hub. The service on port 5050 has no authentication and is for a trusted LAN; don't expose it beyond the LAN without adding auth.
- Don't edit `universal-server/` (unbuilt legacy) or untracked leftovers at the top level.
- Don't bump `VERSION` or write release notes; the maintainer does that at release time.

## Rules for the code

- Python with few dependencies; ask before adding one. Data is JSON in the app data folder; merge, don't overwrite, `settings.json`.
- Keep desktop app, service and web app in step, or label a feature as desktop-only.
- Escape any network-supplied text (device names, SSIDs, schedule fields) before it reaches HTML, a shell command or a file path. Prefer argument lists over `shell=True`.
- Device writes (resets, Wi-Fi, rules) must confirm first and keep the backups and guards in `universal-app/device_rules.py`. pywemo's `rules_db_from_device` returns an empty DB on HTTP errors, which would wipe a plug's rules if uploaded.
- Tkinter widgets only on the main thread; slow work in threads.
- LF line endings in shell scripts. No secrets or personal data in commits.

## Checks

Run the CI checks listed in CONTRIBUTING.md (version check, `py_compile`, server import, `bash -n`). There is no unit-test suite.

**Be honest about testing.** You can't test against real Wemo hardware unless your user has it and runs it. In the PR, say exactly what ran where (checks only, simulated device, or real hardware with model and firmware), and say that the change was AI-assisted.
