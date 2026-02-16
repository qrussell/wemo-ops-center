# Quick Release Checklist

## One-Time Setup (Do once)

- [ ] Create PyPI account at https://pypi.org/account/register/
- [ ] Enable 2FA on PyPI
- [ ] Configure trusted publishing at https://pypi.org/manage/account/publishing/
  - Project: `wemo-mcp-server`
  - Repo: `qrussell/wemo-ops-center`
  - Workflow: `pypi-publish.yml`

## For Each Release

### Preparation
- [ ] Update version in `mcp/pyproject.toml` (line 7)
- [ ] Update version in `mcp/src/wemo_mcp_server/__init__.py` (line 3)
- [ ] Update `mcp/CHANGELOG.md` with release notes
- [ ] Run tests: `cd mcp && pytest tests/ -v`
- [ ] Test build: `cd mcp && python -m build && twine check dist/*`

### Release
- [ ] Commit: `git commit -m "Release vX.X.X"`
- [ ] Push: `git push origin main`
- [ ] Tag: `git tag mcp-vX.X.X`
- [ ] Push tag: `git push origin mcp-vX.X.X`
- [ ] Create GitHub release at https://github.com/qrussell/wemo-ops-center/releases/new
- [ ] Wait for workflow to complete

### Verification
- [ ] Verify on PyPI: https://pypi.org/project/wemo-mcp-server/
- [ ] Test install: `pip install wemo-mcp-server==X.X.X`
- [ ] Test with uvx: `uvx wemo-mcp-server`

## After First Stable Release (v1.0.0)

- [ ] Submit to MCP registry: https://github.com/modelcontextprotocol/servers
- [ ] Share on social media / community forums
- [ ] Monitor issues and user feedback
- [ ] Update documentation if needed

## Quick Commands

```bash
# Check current version
grep '^version = ' mcp/pyproject.toml

# Update both version files (replace 1.0.0 with your version)
sed -i '' 's/version = ".*"/version = "1.0.0"/' mcp/pyproject.toml
sed -i '' 's/__version__ = ".*"/__version__ = "1.0.0"/' mcp/src/wemo_mcp_server/__init__.py

# Test build
cd mcp && python -m build && twine check dist/*

# Create and push tag
git tag mcp-v1.0.0 && git push origin mcp-v1.0.0

# Clean up old builds
rm -rf mcp/dist mcp/build mcp/src/*.egg-info
```
