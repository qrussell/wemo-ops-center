# Releasing Wemo Ops Center

Releases are built by GitHub Actions from `universal-app/`. Pushing a version tag
builds every package and attaches them to a **draft** release. Nothing reaches
users until you publish the draft.

```
bump version → merge to main → push tag vX.Y.Z → CI builds packages → draft release
                                                                         │
                                          review & click "Publish release"
                                                                         │
                                       app update check sees it + Docker image is published
```

## Workflows

| Workflow | Trigger | What it does |
|---|---|---|
| `.github/workflows/release.yml` | push of a `v*` tag | Checks the version, builds all packages, creates/updates a **draft** release with the packages and `SHA256SUMS.txt` |
| `.github/workflows/release.yml` | manual (Actions → Release Build → Run workflow) | Dry run: builds all packages as downloadable workflow artifacts, no release |
| `.github/workflows/docker-publish.yml` | a release is **published** (or manual run) | Builds `ghcr.io/qrussell/wemo-ops-server:<version>`; full releases also move `:latest` (pre-releases don't) |
| `.github/workflows/pypi-publish.yml` | `mcp-v*` tag | Legacy: the MCP server moved to [apiarya/wemo-mcp-server](https://github.com/apiarya/wemo-mcp-server), which publishes it now. Its code is gone from `mcp/`, so don't push `mcp-v*` tags here |

## Packages built

| Platform | Built on | File |
|---|---|---|
| Windows | `windows-latest` + Inno Setup | `WemoOps_Setup_v<ver>.exe` |
| Debian / Ubuntu / Mint (x86-64) | Ubuntu 22.04 | `wemo-ops_<ver>-1_amd64.deb` |
| Raspberry Pi OS / Debian / Ubuntu (ARM64) | Ubuntu 22.04 ARM | `wemo-ops_<ver>-1_arm64.deb` |
| RHEL / Rocky / Alma / Fedora (x86-64) | Rocky Linux 9 container | `wemo-ops-<ver>-1.el9.x86_64.rpm` |
| RHEL / Rocky / Alma / Fedora (ARM64) | Rocky Linux 9 container (ARM) | `wemo-ops-<ver>-1.el9.aarch64.rpm` |
| macOS 15+, Apple Silicon | `macos-15` | `WemoOps_<ver>-1_macos15-apple-silicon.dmg` |
| macOS 15+, Intel | `macos-15-intel` | `WemoOps_<ver>-1_macos15-intel.dmg` |
| macOS 26 Tahoe, Apple Silicon | `macos-26` | `WemoOps_<ver>-1_macos26-apple-silicon.dmg` |
| macOS 26 Tahoe, Intel | `macos-26-intel` | `WemoOps_<ver>-1_macos26-intel.dmg` |

Linux packages are built on older distributions on purpose: a PyInstaller binary
only runs on systems with the same or newer glibc.

The Linux GUI uses the distribution's own X11 and font libraries (libX11, libXft,
fontconfig, freetype, …), declared as package dependencies, instead of bundling
the build machine's copies (`universal-app/ci/use_system_x11_libs.py`). Bundled
Rocky 9 copies crashed the GUI on Fedora 40 when a color emoji font was installed,
and produced fontconfig errors on Fedora 45. For the same reason the Linux GUI
shows plain symbols (● ▲ ↓) instead of emoji. Tested on Rocky 9, Fedora 40/45,
Ubuntu 22.04/24.04 and Debian 13.

## Release steps

1. **Bump the version** in all three places (they must match):
   - `universal-app/wemo_ops_universal.py`: `VERSION = "vX.Y.Z"`
   - `universal-app/wemo_server.py`: `VERSION = "vX.Y.Z-Server"`
   - `universal-app/Dockerfile`: `org.opencontainers.image.version="X.Y.Z"`

   The build scripts read the version from `wemo_ops_universal.py`, so they need no edits.
   Also update the version badge and tables in `README.md`.

2. **Write the release notes** in `release-notes/vX.Y.Z.md` (see
   `release-notes/v5.3.1.md` for the format). The draft release uses this file as
   its description; without it, GitHub generates notes from the commit list.

3. **Check the version:**
   ```bash
   python universal-app/ci/get_version.py --check vX.Y.Z
   ```

4. **Optional dry run:** run *Release Build* manually on your branch and download
   the artifacts to test the installers before tagging.

5. **Merge to `main`**, then **tag `main` and push the tag to GitLab** (`origin`).
   Don't push to GitHub directly: the `github` remote's push URL is disabled on
   purpose, and GitLab's push mirror copies the tag to GitHub, where it starts
   *Release Build*:
   ```bash
   git fetch origin && git switch main && git merge --ff-only origin/main
   git tag -a vX.Y.Z -m "Wemo Ops Center vX.Y.Z"
   git push origin vX.Y.Z
   ```
   Then confirm the tag reached GitHub and the build started:
   ```bash
   curl -s -o /dev/null -w "%{http_code}\n" https://api.github.com/repos/qrussell/wemo-ops-center/git/ref/tags/vX.Y.Z   # 200 = mirrored
   ```
   If it stays 404 for more than a few minutes, open GitLab → Settings → Repository →
   **Mirroring repositories**. A `403` error means the mirror's GitHub token expired or
   lacks the `workflow` permission; replace it, then click **Update now**.
   CI refuses to build if the tag doesn't match the versions in step 1.

6. **Review the draft** on the Releases page. The job summary lists each platform's
   result. If a platform failed, the draft still has the others. Fix it and re-run
   the failed jobs (or the whole workflow): packages in the existing draft are replaced.
   Edit the notes if needed.

7. **Publish.** From 5.3.1 on, the app's update button offers the newest published,
   non-draft, non-pre-release `vX.Y.Z` release that is *newer* than the running
   version (MCP `mcp-v*` releases are ignored). Publishing also starts the Docker
   image build.

   Versions up to 5.3.0 instead compare against GitHub's "latest release" and offer
   it if the tag merely differs. Until most users are on 5.3.1+, avoid publishing an
   MCP release (or mark it as a pre-release) right after an app release, or those
   users will be offered the MCP tag.

8. **apt/dnf repository: automatic.**
   [qrussell/qrussell-repo](https://github.com/qrussell/qrussell-repo) (served at
   `https://qrussell.github.io/qrussell-repo/`) rebuilds itself from the newest two
   published releases of this project. Its *Publish repository* workflow downloads
   the release's `.deb`/`.rpm` files, builds and signs the indexes, and deploys to
   GitHub Pages. Packages are never committed there, so that repository doesn't grow.
   - A new release reaches `apt`/`dnf` users **within 4 hours** (scheduled check).
     To publish right away: qrussell-repo → **Actions → Publish repository → Run workflow**.
   - Check it with `apt-cache policy wemo-ops` / `dnf list --refresh --showduplicates wemo-ops`
     on a test machine.
   - Only published, non-pre-release `vX.Y.Z` releases are picked up, so a draft or a
     pre-release never reaches Linux users.
   - Signing uses the repository key stored as `github-pages` environment secrets in
     qrussell-repo (`QRUSSELL_REPO_SIGNING_KEY`, `QRUSSELL_REPO_SIGNING_PASSPHRASE`).
     Users trust exactly that key, so don't replace it or add a subkey without a plan
     to update every user's copy of the public key.
   - How many releases are kept is `keep` in qrussell-repo's `sources.json`; the build
     fails rather than exceed GitHub Pages' 1 GB limit.
   - The apt index is built with `dpkg-scanpackages --multiversion` (otherwise the
     arm64 `.deb`, same name and version as the amd64 one, is dropped), and the RPM
     index is also published at the top level for machines set up with the older
     `baseurl=.../qrussell-repo/`.

### Re-packaging the same version

To rebuild packages without changing the app version (for example a packaging fix),
set `PKG_RELEASE` (default `1`). It becomes the `-1` suffix in deb/rpm/dmg names.

## Using your own runners (optional)

Every platform builds on GitHub-hosted runners by default (free for this public
repository). To move a platform to your own machine, e.g. an ESXi VM or a MacBook
on macOS Tahoe:

1. Register a self-hosted runner on the machine (repo Settings → Actions →
   Runners → New self-hosted runner) and give it a custom label, e.g. `wemo-tahoe`.
2. Set the matching repository **variable** (Settings → Secrets and variables →
   Actions → Variables) to that label. Delete the variable to go back to GitHub's runner.

| Variable | Builds | Default | Machine needs |
|---|---|---|---|
| `RUNNER_WINDOWS` | Windows installer | `windows-latest` | Python 3.12 (or let `setup-python` install it), Inno Setup 6 |
| `RUNNER_DEB_AMD64` | .deb amd64 | `ubuntu-22.04` | Ubuntu 22.04, passwordless `sudo` for `apt-get` |
| `RUNNER_DEB_ARM64` | .deb arm64 | `ubuntu-22.04-arm` | Same, on ARM64 |
| `RUNNER_RPM_X64` | .rpm x86_64 | `ubuntu-24.04` | Docker or Podman (build runs in a `rockylinux:9` container) |
| `RUNNER_RPM_ARM64` | .rpm aarch64 | `ubuntu-24.04-arm` | Same, on ARM64 |
| `RUNNER_MACOS_ARM` | macOS 15 Apple Silicon DMG | `macos-15` | macOS 15, Xcode command line tools |
| `RUNNER_MACOS_INTEL` | macOS 15 Intel DMG | `macos-15-intel` | macOS 15, Xcode command line tools |
| `RUNNER_MACOS26_ARM` | macOS 26 Apple Silicon DMG | `macos-26` | macOS 26 Tahoe (e.g. your MacBook), Xcode command line tools |
| `RUNNER_MACOS26_INTEL` | macOS 26 Intel DMG | `macos-26-intel` | macOS 26 Tahoe on Intel, Xcode command line tools |

Keep the build OS no newer than what you support: Linux binaries need the same
or newer glibc, and macOS builds may not run on older macOS than the build machine.
A Rocky 9 VM is fine for RPMs, but a Fedora VM would produce packages that need
Fedora's newer glibc. Point each macOS variable at a machine running that macOS
version: the DMG is named after the macOS it was built on.

**Security:** on a public repository, never let pull requests run on
self-hosted runners: a PR could run arbitrary code on your network. These
workflows only start from tag pushes and manual runs by maintainers, and no
`pull_request` trigger should be added to them. Also restrict the runners to
this repository, and treat the machines as build-only (no personal data or credentials).

## macOS signing (optional)

Without secrets, the app is **ad-hoc signed** after the service binary is added to
the bundle. That fixes the "app is damaged" error (#21); users still confirm the
first launch with right-click → **Open**.

For signed and notarized builds (no warning at all), add these repository secrets
(Settings → Secrets and variables → Actions):

| Secret | Value |
|---|---|
| `MACOS_CERT_P12_BASE64` | Developer ID Application certificate + key exported as .p12, base64-encoded |
| `MACOS_CERT_PASSWORD` | Password of that .p12 |
| `MAC_SIGN_IDENTITY` | e.g. `Developer ID Application: Your Name (TEAMID)` |
| `NOTARY_APPLE_ID` | Apple ID email used for notarization |
| `NOTARY_TEAM_ID` | Apple Developer Team ID |
| `NOTARY_PASSWORD` | App-specific password for that Apple ID |

This needs a paid Apple Developer account.

## Building locally

All scripts live in `universal-app/` and work outside CI too:

| Platform | Command | Needs |
|---|---|---|
| Windows | `build_windows.bat` | Python 3.10+, Inno Setup 6 |
| Debian/Ubuntu | `bash build_deb.sh` | `python3-venv python3-tk python3-dev dpkg-dev` |
| RHEL/Fedora | `bash build_rpm.sh` | `python3.11 python3.11-tkinter rpm-build` |
| macOS | `bash build_mac.sh` | Python with working tkinter (python.org installer recommended) |

`build_mac_tahoe.sh` (from PR #23) is an older manual Apple Silicon build; CI uses `build_mac.sh` for all four macOS DMGs, which includes the same Gatekeeper fixes.

Output goes to `universal-app/dist/`. `WEMO_VERSION=X.Y.Z` overrides the version.
