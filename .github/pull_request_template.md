<!--
Thanks for contributing! This GitHub repository is a mirror: the maintainer carries accepted
changes over to the primary repository and credits you. See CONTRIBUTING.md.
Security fixes: please report privately first (SECURITY.md), don't open a public PR.
-->

## What and why

<!-- The problem and the change. Link the issue: Fixes #N -->

## How it was tested

<!-- Say exactly what ran where. Don't claim testing that didn't happen. -->

- [ ] CI checks from CONTRIBUTING.md (version check, `py_compile`, server import, `bash -n`)
- [ ] Ran it: desktop app / server / web app / Docker (say which, and on which OS)
- [ ] Real Wemo hardware (model and firmware: ...)
- [ ] Simulated device only
- [ ] Docs only

## Checklist

- [ ] One topic in this PR
- [ ] Desktop app, service and web app kept in step, or the feature is labelled desktop-only
- [ ] Network-supplied text (device names, SSIDs, schedule fields) is escaped before it reaches HTML or a shell
- [ ] No `VERSION` bump or `release-notes/` changes (the maintainer does those)
- [ ] Docs updated if behaviour changed (README or `wiki/`)
- [ ] AI-assisted? Say so here: <!-- yes / no, and which tool -->
