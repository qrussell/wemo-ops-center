# WeMo MCP Server Migration Plan

**Migration Date:** February 21, 2026  
**From:** `qrussell/wemo-ops-center/mcp`  
**To:** `apiarya/wemo-mcp-server`

---

## Overview

This document outlines the complete migration plan for moving the WeMo MCP Server from a monorepo subdirectory to its own dedicated repository. This migration addresses MCP Registry validation requirements and follows ecosystem best practices.

## Background

The decision to migrate was made following PR #18 discussions, where it was discovered that:
1. MCP Registry only accepts base repository URLs (no path components like `/tree/main/mcp`)
2. Users clicking from the registry landing on the wemo-ops-center README creates confusion
3. Industry standard MCP servers (GitHub, Cloudflare) use dedicated repositories
4. Mixed releases between desktop app and MCP server confuse both user bases

---

## Phase 1: Prepare New Repository 🏗️ ✅ COMPLETED

**Status:** ✅ Completed on February 21, 2026  
**Execution Time:** ~5 minutes  
**Method Used:** Option A - Preserved Git History

### 1.1 Copy Core Files with Git History (Recommended) ✅

**✅ Completed - Used Option A**

Executed:
```bash
# Cloned the original repo with full history
cd /tmp && git clone https://github.com/qrussell/wemo-ops-center.git temp-wemo-ops

# Filtered to keep only MCP directory history (15 commits preserved)
cd temp-wemo-ops
git filter-branch --prune-empty --subdirectory-filter mcp -- --all

# Added new remote and pushed
git remote add new-origin https://github.com/apiarya/wemo-mcp-server.git
git push new-origin main --force
git push new-origin --tags --force
```

**Results:**
- ✅ 79 objects pushed to main branch
- ✅ 765 total objects (including history)
- ✅ 17 tags pushed (including mcp-v0.1.0, mcp-v1.0.0, mcp-v1.0.1)
- ✅ Full commit history preserved (15 commits)
- ✅ Contributors attribution maintained

### 1.2 Files to Migrate ✅

**Core Files (Required):**
- ✅ `pyproject.toml` - Package configuration (MIGRATED)
- ✅ `README.md` - Main documentation (MIGRATED)
- ✅ `LICENSE` - MIT license (MIGRATED)
- ✅ `CHANGELOG.md` - Version history (MIGRATED)
- ✅ `server.json` - MCP registry metadata (MIGRATED)
- ⚠️ `uv.lock` - Dependency lock file (NOT IN GIT - needs manual copy in Phase 2)
- ✅ `src/` - Source code directory (MIGRATED)
- ✅ `tests/` - Test suite (MIGRATED)
- ✅ `assets/` - Images and screenshots (MIGRATED)

**Development Files:**
- ✅ `.gitignore` - Git ignore rules (MIGRATED)
- ✅ `.github/workflows/pypi-publish.yml` - CI/CD pipeline (MIGRATED - needs updates in Phase 3)
- ⚠️ `.vscode/` - Editor configuration (NOT IN GIT - optional, can be added later)
- ✅ `.pytest_cache/` - Don't copy (correctly excluded)
- ✅ `.venv/` - Don't copy (correctly excluded)

**Documentation Files (Need Updates in Phase 2):**
- ✅ `MCP_REGISTRY_SUBMISSION.md` - (MIGRATED - needs updates)
- ✅ `RELEASE.md` - (MIGRATED - needs updates)
- ✅ `RELEASE_CHECKLIST.md` - (MIGRATED - needs updates)

**Summary:**
- ✅ 12/13 core files successfully migrated
- ⚠️ 1 file needs manual addition: `uv.lock` (currently in .gitignore)
- ✅ All source code and documentation transferred
- ✅ Git history fully preserved

**Action Items for Phase 2:**
1. Update .gitignore to NOT ignore uv.lock (for reproducible builds)
2. Copy uv.lock from local mcp/ directory
3. Optionally copy .vscode/ directory for editor consistency

---

## Phase 2: Update References 🔄

### 2.1 Update `pyproject.toml`

**Lines 46-48: Project URLs**
```toml
[project.urls]
Homepage = "https://github.com/apiarya/wemo-mcp-server"
Repository = "https://github.com/apiarya/wemo-mcp-server.git"
Issues = "https://github.com/apiarya/wemo-mcp-server/issues"
```

### 2.2 Update `server.json`

**Lines 5-7: Repository URL**
```json
{
  "repository": {
    "url": "https://github.com/apiarya/wemo-mcp-server",
    "source": "github"
  }
}
```

### 2.3 Update `README.md`

**References to Update:**
- **Line 40:** Image URL: `apiarya/wemo-mcp-server/main/assets/claude-example.png`
- **Line 370:** Update wemo-ops-center reference (keep as external link to qrussell's repo)
- **Line 403:** Clone command: `git clone https://github.com/apiarya/wemo-mcp-server.git`
- **Line 453:** Update "Part of" section to reference qrussell's project as related/parent project

### 2.4 Update Documentation Files

**CHANGELOG.md (Lines 64-65):**
```markdown
[1.0.1]: https://github.com/apiarya/wemo-mcp-server/compare/v1.0.0...v1.0.1
[1.0.0]: https://github.com/apiarya/wemo-mcp-server/compare/v0.1.0...v1.0.0
[0.1.0]: https://github.com/apiarya/wemo-mcp-server/releases/tag/v0.1.0
```

**RELEASE.md:**
- Update all GitHub URLs
- Change repo references from `qrussell/wemo-ops-center` to `apiarya/wemo-mcp-server`
- Remove references to `/mcp` subdirectory paths

**RELEASE_CHECKLIST.md:**
- Line 9: Update repo name
- Line 26: Update release URL

**MCP_REGISTRY_SUBMISSION.md:**
- Update instructions for new repo owner
- Update namespace references

---

## Phase 2: Update References 🔄 ✅ COMPLETED

**Status:** ✅ Completed on February 21, 2026  
**Execution Time:**~20 minutes  
**Files Updated:** 9 files modified, 1 file added (uv.lock)

### 2.1 Update `pyproject.toml` ✅

**Lines 46-48: Project URLs**
```toml
[project.urls]
Homepage = "https://github.com/apiarya/wemo-mcp-server"
Repository = "https://github.com/apiarya/wemo-mcp-server.git"
Issues = "https://github.com/apiarya/wemo-mcp-server/issues"
```
✅ **Completed** - All project URLs updated

### 2.2 Update `server.json` ✅

**Lines 5-7: Repository URL**
```json
{
  "repository": {
    "url": "https://github.com/apiarya/wemo-mcp-server",
    "source": "github"
  }
}
```
✅ **Completed** - Repository URL updated (removed /tree/main/mcp path)

### 2.3 Update `README.md` ✅

**References Updated:**
- **Line 40:** Image URL → `apiarya/wemo-mcp-server/main/assets/claude-example.png` ✅
- **Line 370:** Kept as external link to qrussell's repo (parent project reference) ✅
- **Line 403:** Clone command → `git clone https://github.com/apiarya/wemo-mcp-server.git` ✅
- **Line 453:** Changed from "Part of" to "Related to" wemo-ops-center project ✅

### 2.4 Update Documentation Files ✅

**CHANGELOG.md:**
```markdown
[1.0.1]: https://github.com/apiarya/wemo-mcp-server/compare/v1.0.0...v1.0.1
[1.0.0]: https://github.com/apiarya/wemo-mcp-server/compare/v0.1.0...v1.0.0
[0.1.0]: https://github.com/apiarya/wemo-mcp-server/releases/tag/v0.1.0
```
✅ **Completed** - Version tags simplified from `mcp-v*` to `v*` format

**RELEASE.md:**
✅ Updated all 4 GitHub URL references  
✅ Removed `/mcp` subdirectory paths  
✅ Changed tag format from `mcp-v*` to `v*`  
✅ Updated workflow monitoring URLs

**RELEASE_CHECKLIST.md:**
✅ Updated repo name to `apiarya/wemo-mcp-server`  
✅ Updated release URL  
✅ Removed all `mcp/` path prefixes from commands  
✅ Simplified tag format from `mcp-vX.X.X` to `vX.X.X`

**MCP_REGISTRY_SUBMISSION.md:**
✅ Updated instructions for new repo owner  
✅ Added namespace considerations section  
✅ Documented options for registry namespace (qrussell vs apiarya)  
✅ Removed `/mcp` subdirectory references

### 2.5 Additional Changes ✅

**.gitignore:**
✅ Updated to allow `uv.lock` in version control  
✅ Added comment: "Keep in version control for reproducible builds"

**uv.lock:**
✅ Copied from original mcp/ directory (285KB)  
✅ Added to version control for dependency pinning

### Results Summary

**Files Modified:** 8
- `pyproject.toml`
- `server.json`
- `README.md`
- `CHANGELOG.md`
- `RELEASE.md`
- `RELEASE_CHECKLIST.md`
- `MCP_REGISTRY_SUBMISSION.md`
- `.gitignore`

**Files Added:** 1
- `uv.lock`

**Commit:** `5ed36f9`  
**Lines Changed:** +1484 insertions, -44 deletions  
**Pushed to:** https://github.com/apiarya/wemo-mcp-server (main branch)

**View Changes:** https://github.com/apiarya/wemo-mcp-server/commit/5ed36f9

---

## Phase 3: Setup CI/CD & Automation ⚙️

### 3.1 Update GitHub Actions Workflow

**`.github/workflows/pypi-publish.yml` Changes:**

```yaml
name: Publish to PyPI

on:
  release:
    types: [published]
  workflow_dispatch:

jobs:
  publish:
    # Changed from mcp-v* to v*
    if: startsWith(github.ref, 'refs/tags/v')
    runs-on: ubuntu-latest
    permissions:
      contents: read
      id-token: write

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.10"

      - name: Install build dependencies
        run: |
          python -m pip install --upgrade pip
          pip install build twine

      - name: Extract version from tag
        id: version
        run: |
          # Extract version from tag (e.g., v1.1.0 -> 1.1.0)
          VERSION=${GITHUB_REF#refs/tags/v}
          echo "version=$VERSION" >> "$GITHUB_OUTPUT"
          echo "Publishing version: $VERSION"

      - name: Verify version matches pyproject.toml
        run: |
          # Removed 'cd mcp' - now at root level
          PYPROJECT_VERSION=$(grep '^version = ' pyproject.toml | sed 's/version = "\(.*\)"/\1/')
          TAG_VERSION="${{ steps.version.outputs.version }}"
          if [ "$PYPROJECT_VERSION" != "$TAG_VERSION" ]; then
            echo "❌ Version mismatch!"
            echo "   pyproject.toml: $PYPROJECT_VERSION"
            echo "   Git tag: $TAG_VERSION"
            exit 1
          fi
          echo "✅ Version verified: $PYPROJECT_VERSION"

      - name: Build package
        run: |
          # Removed 'cd mcp' - now at root level
          python -m build
          echo "📦 Built package:"
          ls -lh dist/

      - name: Check package
        run: |
          # Removed 'cd mcp'
          twine check dist/*

      - name: Publish to PyPI
        uses: pypa/gh-action-pypi-publish@release/v1
        with:
          packages-dir: dist/  # Changed from mcp/dist/
          print-hash: true

      - name: Create release summary
        run: |
          echo "## 🎉 Published to PyPI" >> $GITHUB_STEP_SUMMARY
          echo "" >> $GITHUB_STEP_SUMMARY
          echo "**Version:** ${{ steps.version.outputs.version }}" >> $GITHUB_STEP_SUMMARY
          echo "" >> $GITHUB_STEP_SUMMARY
          echo "**Install command:**" >> $GITHUB_STEP_SUMMARY
          echo '```bash' >> $GITHUB_STEP_SUMMARY
          echo "pip install wemo-mcp-server==${{ steps.version.outputs.version }}" >> $GITHUB_STEP_SUMMARY
          echo "# or" >> $GITHUB_STEP_SUMMARY
          echo "uvx wemo-mcp-server@${{ steps.version.outputs.version }}" >> $GITHUB_STEP_SUMMARY
          echo '```' >> $GITHUB_STEP_SUMMARY
          echo "" >> $GITHUB_STEP_SUMMARY
          echo "**PyPI page:** https://pypi.org/project/wemo-mcp-server/${{ steps.version.outputs.version }}/" >> $GITHUB_STEP_SUMMARY
```

**Key Changes:**
- Tag format: `mcp-v*` → `v*`
- Removed all `cd mcp` commands
- Updated `packages-dir: dist/` (was `mcp/dist/`)

### 3.2 Setup PyPI Trusted Publishing

**Steps:**
1. Go to https://pypi.org/manage/project/wemo-mcp-server/settings/publishing/
2. Add new GitHub publisher:
   - **Owner:** `apiarya`
   - **Repository:** `wemo-mcp-server`
   - **Workflow name:** `pypi-publish.yml`
   - **Environment name:** (leave blank or use `release`)

### 3.3 Setup Repository Secrets (Alternative)

If using token-based publishing instead of trusted publishing:
- Add `PYPI_API_TOKEN` in repository secrets at:
  `https://github.com/apiarya/wemo-mcp-server/settings/secrets/actions`

---

## Phase 4: Update MCP Registry 📦

### 4.1 Prepare for Registry Update

**Version Strategy:**
- Option A: Bump to `v1.1.0` (recommended - indicates "new home" milestone)
- Option B: Bump to `v1.0.2` (patch - if minimal changes)

**Update Checklist:**
- [ ] Update `version` in `pyproject.toml`
- [ ] Update `version` in `src/wemo_mcp_server/__init__.py`
- [ ] Update `version` in `server.json`
- [ ] Add migration note to `CHANGELOG.md`
- [ ] Update all repository URLs to point to new repo

### 4.2 Publish to Registry

```bash
cd wemo-mcp-server
mcp-publisher publish
```

### 4.3 Registry Namespace Considerations

**Current Registration:** `io.github.qrussell/wemo`

**Options:**
- **Option A:** Have qrussell transfer ownership in registry (recommended for continuity)
- **Option B:** Register as new name `io.github.apiarya/wemo` (requires coordination)
- **Option C:** Collaborate with qrussell to republish under his namespace from new repo

**Recommendation:** Discuss with qrussell about the best approach for namespace management.

---

## Phase 5: Update Original Repository 🔗

### 5.1 Update `wemo-ops-center/README.md`

**Update MCP Server Section (around line 30):**
```markdown
| Feature | 🖥️ Desktop App (GUI) | ⚙️ Server App (Headless) | 🤖 MCP Server (AI) |
| :--- | :--- | :--- | :--- |
| **Repository** | This repo | This repo | [apiarya/wemo-mcp-server](https://github.com/apiarya/wemo-mcp-server) |
| **Installation** | Download from Releases | `dnf/apt install` or Docker | `pip install wemo-mcp-server` |
```

Add note after table:
```markdown
> **Note:** The MCP Server has been moved to its own dedicated repository at [apiarya/wemo-mcp-server](https://github.com/apiarya/wemo-mcp-server) for better discoverability and to follow MCP ecosystem best practices.
```

### 5.2 Add Deprecation Notice in `wemo-ops-center/mcp/`

**Create `wemo-ops-center/mcp/README.md`:**
```markdown
# ⚠️ Repository Moved

The WeMo MCP Server has been migrated to its own dedicated repository for better discoverability and to comply with MCP Registry requirements.

## 🔗 New Location

**Repository:** https://github.com/apiarya/wemo-mcp-server

**Installation:**
```bash
pip install wemo-mcp-server
# or
uvx wemo-mcp-server
```

## Why the Move?

1. **MCP Registry Compliance:** Registry requires base repository URLs
2. **Better Discoverability:** Users from registry land directly on MCP documentation
3. **Ecosystem Standards:** Major MCP servers (GitHub, Cloudflare) use dedicated repos
4. **Clearer Separation:** Reduces confusion between desktop app and MCP server releases

## For Users

No action needed! Installation commands remain the same. The PyPI package `wemo-mcp-server` now publishes from the new repository.

## For Contributors

Please submit issues and pull requests to the new repository:
- **Issues:** https://github.com/apiarya/wemo-mcp-server/issues
- **Contributing:** See the new repo's documentation

## Historical Context

This directory is preserved for historical reference and contains the original development history. For current code and documentation, please visit the new repository.

---

**Related Project:** This MCP Server works with devices managed by [WeMo Ops Center](https://github.com/qrussell/wemo-ops-center) desktop and server applications.
```

### 5.3 Archive or Remove `mcp/` Directory

**Option A: Keep with Deprecation Notice (Recommended)**
- Preserves git history
- Provides clear migration path for existing users
- Maintains references in old documentation

**Option B: Remove Entirely**
- Cleaner repository structure
- Prevents confusion
- Update `.gitignore` if needed

**Recommendation:** Keep with deprecation notice for at least 6 months, then consider archival.

---

## Phase 6: Testing & Validation ✅

### 6.1 Pre-Release Checklist

**Files & Configuration:**
- [ ] All source files migrated to new repo
- [ ] All URLs updated to point to `apiarya/wemo-mcp-server`
- [ ] GitHub Actions workflow updated and tested
- [ ] PyPI trusted publishing configured
- [ ] Version bumped appropriately (1.1.0 or 1.0.2)
- [ ] CHANGELOG updated with migration note

**Documentation:**
- [ ] README.md updated with new URLs
- [ ] All documentation files reviewed and updated
- [ ] Image URLs working (test in GitHub preview)
- [ ] Installation instructions verified

**Original Repo:**
- [ ] Deprecation notice added to old location
- [ ] Main README updated with new repo link
- [ ] No broken links in documentation

### 6.2 Release Testing

```bash
# Navigate to new repo
cd wemo-mcp-server

# Tag new version
git tag v1.1.0
git push origin v1.1.0

# Create GitHub release
# This triggers automatic PyPI publish via GitHub Actions

# Wait for workflow to complete (~2-3 minutes)

# Verify PyPI publish
pip install --upgrade wemo-mcp-server
pip show wemo-mcp-server

# Test installation via uvx
uvx wemo-mcp-server

# Verify version
python -c "import wemo_mcp_server; print(wemo_mcp_server.__version__)"
```

### 6.3 MCP Registry Testing

```bash
# Ensure mcp-publisher is installed
brew install mcp-publisher  # or pip install mcp-publisher

# Authenticate
mcp-publisher login github

# Publish to registry
cd wemo-mcp-server
mcp-publisher publish

# Verify in registry
# Visit: https://registry.modelcontextprotocol.io/?q=wemo
# Check that clicking through lands on correct README
```

### 6.4 Integration Testing

**Test with MCP Clients:**
- [ ] Claude Desktop
- [ ] VS Code MCP extension
- [ ] Cursor
- [ ] Cline (VS Code extension)

**Test Commands:**
```json
// Add to MCP client config
{
  "mcpServers": {
    "wemo": {
      "command": "uvx",
      "args": ["wemo-mcp-server"]
    }
  }
}
```

---

## Phase 7: Communication & Documentation 📢

### 7.1 Create Pull Request to `qrussell/wemo-ops-center`

**PR Title:** "MCP Server Migration - Update References to New Repository"

**PR Description:**
```markdown
# MCP Server Repository Migration

As discussed in PR #18, the WeMo MCP Server has been migrated to its own dedicated repository to comply with MCP Registry requirements and follow ecosystem best practices.

## Changes in This PR

1. ✅ Updated README.md to reference new repository location
2. ✅ Added deprecation notice in `/mcp/` directory
3. ✅ Updated comparison table with new repository link
4. ✅ Added migration explanation note

## New Repository

**Location:** https://github.com/apiarya/wemo-mcp-server

## Why This Move?

- **Registry Compliance:** MCP Registry only accepts base repository URLs
- **Better UX:** Users from registry land directly on MCP documentation
- **Industry Standard:** Follows patterns used by GitHub and Cloudflare MCP servers
- **Clearer Separation:** Reduces confusion between desktop app and MCP releases

## For Users

No action needed! Installation remains the same:
```bash
pip install wemo-mcp-server
```

## Related

- Closes: #[issue number if any]
- Related to: PR #18
- Migration Tracking: apiarya/wemo-mcp-server#[PR number]
```

### 7.2 GitHub Release Notes Template

**Release Title:** `v1.1.0 - New Repository Home`

**Release Description:**
```markdown
# v1.1.0 - Repository Migration 🏠

## 🎉 New Home for WeMo MCP Server

The WeMo MCP Server now has its own dedicated repository!

**New Repository:** https://github.com/apiarya/wemo-mcp-server

This move follows MCP ecosystem best practices and significantly improves discoverability for users finding the server through the official MCP Registry.

## What Changed

### Repository & Infrastructure
- ✅ Migrated from `qrussell/wemo-ops-center/mcp` monorepo
- ✅ All documentation and URLs updated to new repository
- ✅ CI/CD pipeline configured for standalone repo
- ✅ MCP Registry metadata updated with new location
- ✅ Simplified versioning (no more `mcp-v*` tags, just `v*`)

### Documentation
- ✅ All image URLs and links updated
- ✅ Installation instructions verified
- ✅ Contributing guidelines updated
- ✅ Issue tracking moved to new repository

### No Breaking Changes
- ✅ Package name remains: `wemo-mcp-server`
- ✅ Installation command unchanged: `pip install wemo-mcp-server`
- ✅ All MCP tools function identically
- ✅ Configuration compatibility maintained

## For Users

**No action needed!** Just install or upgrade as usual:

```bash
# Via pip
pip install --upgrade wemo-mcp-server

# Via uvx (recommended)
uvx wemo-mcp-server@latest
```

## For Contributors

Please submit issues and PRs to the new repository:
- **Issues:** https://github.com/apiarya/wemo-mcp-server/issues
- **Pull Requests:** https://github.com/apiarya/wemo-mcp-server/pulls

## Why This Matters

### MCP Registry Compliance
The MCP Registry requires base repository URLs without path components. The previous URL (`/tree/main/mcp`) caused validation failures.

### Better User Experience
Users discovering the server through the [MCP Registry](https://registry.modelcontextprotocol.io/?q=wemo) now land directly on MCP documentation instead of the desktop app README.

### Industry Standard
This aligns with patterns used by major MCP servers:
- [github/github-mcp-server](https://github.com/github/github-mcp-server)
- [cloudflare/mcp-server-cloudflare](https://github.com/cloudflare/mcp-server-cloudflare)

## Related Projects

The WeMo MCP Server complements the [WeMo Ops Center](https://github.com/qrussell/wemo-ops-center) desktop and server applications for managing WeMo devices.

## Installation

```bash
# PyPI
pip install wemo-mcp-server

# uvx (recommended for MCP)
uvx wemo-mcp-server
```

## Quick Start

Add to your MCP client configuration:
```json
{
  "mcpServers": {
    "wemo": {
      "command": "uvx",
      "args": ["wemo-mcp-server"]
    }
  }
}
```

## Full Changelog

See [CHANGELOG.md](https://github.com/apiarya/wemo-mcp-server/blob/main/CHANGELOG.md) for complete version history.

---

**Thanks to @qrussell for the collaboration and support in making this migration happen!** 🙏
```

### 7.3 Communication Channels

**Announce Migration On:**
- [ ] GitHub release (both repos)
- [ ] README badges/notices (both repos)
- [ ] PyPI project description (new repo)
- [ ] MCP Registry listing (updated URL)
- [ ] Related issues/PRs with stakeholders

**Key Messages:**
1. **Users:** Nothing changes for you - same installation command
2. **Contributors:** New location for issues and PRs
3. **Registry Users:** Better landing experience now
4. **Maintainers:** Cleaner separation of concerns

---

## Timeline & Milestones

### Estimated Timeline

**Week 1 (Current):**
- [x] ✅ Create migration plan document
- [x] ✅ Execute Phase 1: File migration (COMPLETED Feb 21, 2026 - 5 mins)
- [x] ✅ Execute Phase 2: Update references (COMPLETED Feb 21, 2026 - 20 mins)
- [ ] Execute Phase 3: Setup CI/CD

**Week 2:**
- [ ] Execute Phase 4: Test and publish first release
- [ ] Execute Phase 5: Update original repository
- [ ] Execute Phase 6: Comprehensive testing

**Week 3:**
- [ ] Execute Phase 7: Communication and documentation
- [ ] Monitor for issues and user feedback
- [ ] Address any migration-related bugs

**Total Estimated Time:** 3-4 hours of focused work spread over 1-2 weeks

### Key Milestones

1. ✅ **Migration Plan Approved** - This document (Feb 21, 2026)
2. ✅ **Files Migrated** - All code in new repo with preserved history (Feb 21, 2026)
3. ✅ **References Updated** - All URLs point to new repository (Feb 21, 2026)
4. ⏳ **First Release Published** - v1.1.0 on PyPI
5. ⏳ **Registry Updated** - New URL validated
6. ⏳ **Original Repo Updated** - Deprecation notices in place
7. ⏳ **Communication Complete** - All stakeholders notified

---

## Critical Considerations

### 1. PyPI Ownership
**Status:** Verify maintainer/owner access to `wemo-mcp-server` on PyPI  
**Action Required:** Ensure @apiarya has publish rights or setup trusted publishing

### 2. Registry Namespace
**Current:** `io.github.qrussell/wemo`  
**Options:**
- Transfer to `io.github.apiarya/wemo`
- Keep as `io.github.qrussell/wemo` with qrussell republishing from new repo
- Discuss with qrussell for preferred approach

**Recommendation:** Coordinate with @qrussell before registry publish

### 3. Version Strategy
**Recommended:** Use `v1.1.0` to indicate "new home" milestone  
**Rationale:**
- Clear indication of significant change
- Not a breaking change (minor version bump appropriate)
- Users can track pre/post migration versions

### 4. Git History Preservation
**Method:** Use `git filter-branch` or `git subtree` to preserve commit history  
**Value:**
- Maintains contributor attribution
- Preserves development history
- Useful for understanding codebase evolution

### 5. Backward Compatibility
**Guarantee:** All existing integrations must continue working  
**Testing:** Verify with multiple MCP clients before announcing

### 6. Documentation Sync
**Challenge:** Keep both repos' documentation in sync during transition  
**Solution:** Clear deprecation timeline and automatic redirects where possible

---

## Rollback Plan

In case of critical issues during migration:

### Immediate Rollback
1. Revert registry update to old URL (if possible)
2. Continue publishing from old location temporarily
3. Keep new repo as draft/WIP

### Gradual Rollback
1. Maintain both locations for 30 days
2. Publish to PyPI from old location as backup
3. Investigate issues before re-attempting migration

### Communication
- Immediate notice on GitHub
- Update installation docs with temporary instructions
- Post-mortem to understand failure points

---

## Success Criteria

Migration is considered successful when:

- [ ] New repository is fully operational and documented
- [ ] At least one successful release published from new repo
- [ ] PyPI package published and installable from new repo
- [ ] MCP Registry updated and validation passing
- [ ] No broken links in either repository
- [ ] User installations work without modification
- [ ] CI/CD pipeline passing all tests
- [ ] Zero critical bugs reported in first week
- [ ] Original repository properly updated with migration notices
- [ ] Community awareness and acceptance of new location

---

## Contacts & Resources

### Key People
- **@apiarya** - Migration lead, new repo maintainer
- **@qrussell** - Original repo owner, PyPI access coordination

### Resources
- **New Repo:** https://github.com/apiarya/wemo-mcp-server
- **Original Repo:** https://github.com/qrussell/wemo-ops-center
- **PyPI Package:** https://pypi.org/project/wemo-mcp-server/
- **MCP Registry:** https://registry.modelcontextprotocol.io/?q=wemo
- **Registry Docs:** https://github.com/modelcontextprotocol/registry

### Support Channels
- **GitHub Issues:** For technical problems
- **Pull Requests:** For contributions
- **Discussions:** For questions and community support

---

## Notes & Updates

### February 21, 2026 - 4:30 PM
- ✅ **Phase 2 COMPLETED**
- Updated all repository references (9 files)
- Changed 17 URLs from qrussell/wemo-ops-center to apiarya/wemo-mcp-server
- Simplified versioning: mcp-v* → v*
- Added uv.lock (285KB) for reproducible builds
- Removed all /mcp subdirectory references
- Preserved appropriate external links to parent project
- Commit 5ed36f9 pushed to apiarya/wemo-mcp-server
- Ready to proceed with Phase 3: Setup CI/CD

### February 21, 2026 - 3:30 PM
- ✅ **Phase 1 COMPLETED**
- Successfully cloned and filtered git history (15 commits preserved)
- Pushed all files to apiarya/wemo-mcp-server with full history
- 17 tags migrated including mcp-v0.1.0, mcp-v1.0.0, mcp-v1.0.1
- Verified all core files present in new repository
- **Note:** uv.lock needs to be added (currently in .gitignore)
- Ready to proceed with Phase 2: Update References

### February 21, 2026 - Initial
- Migration plan created and documented
- Branch `mcp-migration` created in wemo-ops-center
- Awaiting approval to proceed with Phase 1

---

**Document Version:** 1.2  
**Last Updated:** February 21, 2026 - 4:30 PM  
**Status:** Phase 2 Complete - Ready for Phase 3
