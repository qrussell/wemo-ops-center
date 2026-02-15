# Release Guide - WeMo MCP Server

This guide explains how to publish the MCP server to PyPI and the official MCP registry.

## Prerequisites

### 1. PyPI Account Setup

1. Create an account at [pypi.org](https://pypi.org/account/register/)
2. Verify your email address
3. Set up Two-Factor Authentication (required for publishing)

### 2. Configure Trusted Publishing (Recommended)

Trusted publishing uses GitHub OIDC tokens instead of API keys - more secure and easier to manage.

1. Go to https://pypi.org/manage/account/publishing/
2. Add a new pending publisher with these details:
   - **PyPI Project Name:** `wemo-mcp-server`
   - **Owner:** `qrussell` (or your GitHub username)
   - **Repository name:** `wemo-ops-center`
   - **Workflow name:** `pypi-publish.yml`
   - **Environment name:** *(leave blank)*

**Alternative:** If you prefer API tokens instead:
1. Go to https://pypi.org/manage/account/token/
2. Create a token named "wemo-ops-center-github-actions"
3. Set scope to "Entire account" (until first publish) or "Project: wemo-mcp-server" (after first publish)
4. Copy the token (starts with `pypi-`)
5. Add it to GitHub repo secrets as `PYPI_API_TOKEN`
6. Uncomment the `password:` line in `.github/workflows/pypi-publish.yml`

## Release Process

### Step 1: Prepare the Release

1. **Update version** in both files:
   ```bash
   # Edit these files to set version (e.g., 0.1.0)
   mcp/pyproject.toml  # Line 7: version = "0.1.0"
   mcp/src/wemo_mcp_server/__init__.py  # Line 3: __version__ = "0.1.0"
   ```

2. **Update CHANGELOG** (create if needed):
   ```bash
   # Create mcp/CHANGELOG.md with release notes
   ```

3. **Run tests locally**:
   ```bash
   cd mcp
   python -m pytest tests/test_server.py -v
   python tests/test_e2e.py  # If you have WeMo devices
   ```

4. **Test build locally**:
   ```bash
   cd mcp
   pip install build twine
   python -m build
   twine check dist/*
   ```

5. **Commit and push**:
   ```bash
   git add mcp/pyproject.toml mcp/src/wemo_mcp_server/__init__.py
   git commit -m "Bump version to 0.1.0"
   git push origin main
   ```

### Step 2: Create GitHub Release

1. **Create and push a tag**:
   ```bash
   # Tag must start with 'mcp-v' to trigger PyPI workflow
   git tag mcp-v0.1.0
   git push origin mcp-v0.1.0
   ```

2. **Create GitHub Release**:
   - Go to: https://github.com/qrussell/wemo-ops-center/releases/new
   - Select tag: `mcp-v0.1.0`
   - Release title: `MCP Server v0.1.0`
   - Description:
     ```markdown
     ## WeMo MCP Server v0.1.0

     First release of the WeMo MCP Server for AI assistant integration!

     ### Installation
     ```bash
     pip install wemo-mcp-server
     # or
     uvx wemo-mcp-server
     ```

     ### Features
     - 🔍 Smart device discovery with multi-phase scanning
     - ⚡ Device control (on/off/toggle/brightness)
     - ✏️ Device management (rename, HomeKit codes)
     - 📊 Real-time status monitoring
     - 🔌 Works with Claude Desktop, VS Code, and any MCP host

     ### Documentation
     See [mcp/README.md](https://github.com/qrussell/wemo-ops-center/tree/main/mcp) for setup instructions.
     ```
   - Click **Publish release**

3. **Monitor the workflow**:
   - Go to: https://github.com/qrussell/wemo-ops-center/actions
   - Watch the "Publish MCP Server to PyPI" workflow
   - If it fails, check the logs and fix issues

### Step 3: Verify Publication

1. **Check PyPI**:
   - Visit: https://pypi.org/project/wemo-mcp-server/
   - Verify version shows as 0.1.0
   - Check that README renders correctly

2. **Test installation**:
   ```bash
   # Create a fresh venv and test
   python -m venv test-env
   source test-env/bin/activate
   pip install wemo-mcp-server
   python -m wemo_mcp_server --help  # Should show help
   deactivate
   rm -rf test-env
   ```

3. **Test with uvx**:
   ```bash
   uvx wemo-mcp-server
   ```

### Step 4: Submit to MCP Registry

Once published and tested on PyPI:

1. **Fork the MCP servers repository**:
   - Go to: https://github.com/modelcontextprotocol/servers
   - Click "Fork"

2. **Add your server entry**:
   ```bash
   git clone https://github.com/YOUR_USERNAME/servers.git
   cd servers
   ```
   
   Add entry to the appropriate file (check their contribution guide):
   ```json
   {
     "name": "wemo-mcp-server",
     "displayName": "WeMo Smart Home Control",
     "description": "Control WeMo smart home devices through natural language. Discover devices, toggle switches, adjust brightness, and manage HomeKit codes.",
     "repository": "https://github.com/qrussell/wemo-ops-center/tree/main/mcp",
     "homepage": "https://github.com/qrussell/wemo-ops-center",
     "language": "python",
     "categories": ["smart-home", "iot", "home-automation"],
     "install": {
       "pip": "wemo-mcp-server",
       "uvx": "wemo-mcp-server"
     },
     "configuration": {
       "claude_desktop": {
         "mcpServers": {
           "wemo-mcp-server": {
             "command": "uvx",
             "args": ["wemo-mcp-server"]
           }
         }
       }
     },
     "license": "MIT",
     "version": "0.1.0"
   }
   ```

3. **Create Pull Request**:
   ```bash
   git checkout -b add-wemo-mcp-server
   git add .
   git commit -m "Add WeMo MCP Server"
   git push origin add-wemo-mcp-server
   ```
   - Go to your fork on GitHub
   - Click "Contribute" → "Open pull request"
   - Follow their PR template
   - Link to PyPI package: https://pypi.org/project/wemo-mcp-server/

## Subsequent Releases

For version 0.1.1, 0.2.0, etc:

1. Update version in `pyproject.toml` and `__init__.py`
2. Update CHANGELOG.md
3. Commit: `git commit -m "Bump version to 0.x.x"`
4. Tag: `git tag mcp-v0.x.x && git push origin mcp-v0.x.x`
5. Create GitHub release
6. Workflow auto-publishes to PyPI
7. Update MCP registry entry if needed

## Troubleshooting

### PyPI publish fails with "403 Forbidden"

**Trusted publishing:** Make sure the pending publisher is correctly configured with the exact repository and workflow name.

**API token:** Verify the token has appropriate scope and hasn't expired.

### Version conflict error

The workflow checks that the tag matches `pyproject.toml`. Make sure both are in sync:
```bash
# Check version
grep '^version = ' mcp/pyproject.toml
```

### Package doesn't install correctly

Test the built package locally before releasing:
```bash
cd mcp
python -m build
pip install dist/wemo_mcp_server-0.1.0-py3-none-any.whl
```

### Workflow doesn't trigger

The workflow only triggers for tags starting with `mcp-v`. Make sure your tag follows this pattern:
```bash
git tag mcp-v0.1.0  # ✅ Correct
git tag v0.1.0      # ❌ Won't trigger
```

## Resources

- [PyPI Trusted Publishing Guide](https://docs.pypi.org/trusted-publishers/)
- [Python Packaging Guide](https://packaging.python.org/)
- [MCP Servers Registry](https://github.com/modelcontextprotocol/servers)
- [GitHub Actions - PyPI Publish Action](https://github.com/pypa/gh-action-pypi-publish)
