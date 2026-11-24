# Contributing to Wemo Ops Center

Thanks for helping! Wemo Ops Center is a free (MIT), fully local, cloud-free tool for people who still own Belkin Wemo plugs, switches and dimmers. It's maintained by one person, so small, focused changes with a clear reason are the easiest to accept.

This guide is for people and for AI coding agents. Agents should also read [AGENTS.md](AGENTS.md).

## How changes flow

```
GitHub issue or PR  →  maintainer applies it on GitLab (primary)  →  merge request + CI  →  main
                                                                                          │
                                         GitLab push-mirrors main and tags to GitHub  ←───┘
                                         GitHub Actions builds the release packages
```

- **The primary repository is on the maintainer's GitLab.** This GitHub repository is a read-only **mirror** of its `main` branch and tags. Anything merged directly on GitHub is overwritten by the next mirror push.
- **You contribute on GitHub as usual:** open an issue, or a pull request against `main`. The maintainer reviews it here, then carries the change to GitLab as a merge request with you credited as the author (`Co-authored-by`). Your PR is closed with a link to the release that ships it.
- **Bugs and feature requests:** [GitHub issues](https://github.com/qrussell/wemo-ops-center/issues). Include the app version, edition (desktop app, background service, Docker, HOOBS helper), operating system, and for device problems the Wemo model and firmware version.
- **Security problems: don't open an issue or PR.** Report privately as described in [SECURITY.md](SECURITY.md).

## Before you start

- For anything bigger than a bug fix, open an issue first so we can agree on the approach.
- Read the scope: Wemo Ops Center is a provisioning and automation tool for Wemo devices, not a general smart-home hub. It must keep working **without any cloud account**.
- The background service (port 5050) has no login and is designed for a trusted LAN. Don't add features that expose it to the internet without adding authentication first (see SECURITY.md).

## Where things are

| Path | What |
|---|---|
| `universal-app/wemo_ops_universal.py` | Desktop app (CustomTkinter). Holds `VERSION`, the single source of the version number |
| `universal-app/wemo_server.py` | Background service / server (Flask + waitress, port 5050) and the mobile web app's API |
| `universal-app/templates/`, `static/` | Mobile web app |
| `universal-app/device_rules.py` | Schedules stored on the plug (experimental) |
| `universal-app/hoobs_installer.py` | Homebridge/HOOBS helper |
| `universal-app/build_*.sh`, `build_windows.bat`, `wemo_windows.spec`, `Dockerfile` | Packaging |
| `.github/workflows/` | Release builds (see [RELEASING.md](RELEASING.md)) |
| `docs/` | Website (GitHub Pages) |
| `release-notes/` | One file per release |
| `universal-server/` | Old standalone server, not built. Please don't change it |

## Coding conventions

- **Python, few dependencies.** Ask before adding a new dependency. No database: settings and data are JSON files in the app data folder. `settings.json` is shared by the desktop app, the service and the web app: reload and merge before saving, never overwrite another component's keys.
- **Keep the editions in step.** If you change behaviour in the desktop app, change the service and web app too, or say clearly in the UI and release notes that the feature is desktop-only.
- **Tkinter:** do slow work in a thread and only touch widgets on the main thread (`after()`).
- **Web app:** device names and other data come from the network. Escape them before putting them into HTML (use `escapeHtml` or `textContent`, never raw `innerHTML` with data).
- **Destructive device actions** (resets, clearing Wi-Fi, writing rules) must ask for confirmation, and rules writes must keep the backup and guards in `device_rules.py`.
- **Shell scripts use LF line endings** (CI fails on CRLF).
- Label experimental features in the UI with their limitation.
- Don't commit secrets, Wi-Fi passwords, real device serials or personal data. Secret scanning push protection is on.

## Checks to run

There's no unit-test suite yet. Run what CI runs, then test at the level your change touches:

```bash
python universal-app/ci/get_version.py --check "v$(python universal-app/ci/get_version.py)"
python -m py_compile universal-app/*.py universal-app/ci/*.py
pip install flask waitress requests "pywemo>=2.1.1"
cd universal-app && python -c "import wemo_server"
for f in universal-app/*.sh; do bash -n "$f"; done
```

- Server or web app changes: run `python universal-app/wemo_server.py` and open `http://localhost:5050`.
- Desktop app changes: run `python universal-app/wemo_ops_universal.py`.
- In your PR, say **what you tested and where**: real Wemo hardware (model and firmware), a simulated device, or only the checks above. Don't claim hardware testing you didn't do.

## Pull requests

- One topic per PR, with a short description of the problem, the fix and how you tested it. Link the issue (`Fixes #N`).
- Don't bump `VERSION` or edit `release-notes/`. The maintainer does that when releasing.
- Changes to build scripts or workflows need a dry-run release build, which the maintainer runs.

## AI-assisted contributions

AI-assisted contributions are welcome under the same rules. Please say in the PR that an AI tool helped, review the code yourself before opening it, and make sure the testing you describe actually happened. Agents: see [AGENTS.md](AGENTS.md).

## License

By contributing, you agree that your contribution is licensed under the project's MIT license (see the README).
