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
   # Edit these files to set version (e.g., 1.0.0)
   mcp/pyproject.toml  # Line 7: version = "1.0.0"
   mcp/src/wemo_mcp_server/__init__.py  # Line 3: __version__ = "1.0.0"
   ```

2. **Update CHANGELOG.md**:
   ```bash
   # Add release notes to mcp/CHANGELOG.md
   # Document all new features, fixes, and breaking changes
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
   git add mcp/pyproject.toml mcp/src/wemo_mcp_server/__init__.py mcp/CHANGELOG.md
   git commit -m "Release v1.0.0"
   git push origin main
   ```

### Step 2: Create GitHub Release

1. **Create and push a tag**:
   ```bash
   # Tag must start with 'mcp-v' to trigger PyPI workflow
   git tag mcp-v1.0.0
   git push origin mcp-v1.0.0
   ```

2. **Create GitHub Release**:
   - Go to: https://github.com/qrussell/wemo-ops-center/releases/new
   - Select tag: `mcp-v1.0.0`
   - Release title: `MCP Server v1.0.0`
   - Description:
     ```markdown
     ## WeMo MCP Server v1.0.0

     🎉 **First stable release** of the WeMo MCP Server for AI assistant integration!

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
   - Verify version shows as 1.0.0
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

### Step 4: Publish to MCP Registry

Once published and tested on PyPI, submit to the official MCP Registry:

1. **Install mcp-publisher CLI**:
   ```bash
   # macOS/Linux
   curl -L "https://github.com/modelcontextprotocol/registry/releases/latest/download/mcp-publisher_$(uname -s | tr '[:upper:]' '[:lower:]')_$(uname -m | sed 's/x86_64/amd64/;s/aarch64/arm64/').tar.gz" | tar xz mcp-publisher && sudo mv mcp-publisher /usr/local/bin/
   
   # Or via Homebrew
   brew install mcp-publisher
   
   # Verify installation
   mcp-publisher --help
   ```

2. **Authenticate with GitHub**:
   ```bash
   mcp-publisher login github
   ```
   
   Follow the prompts to authenticate via GitHub device flow.

3. **Publish to registry**:
   ```bash
   cd mcp
   mcp-publisher publish
   ```
   
   This uses the `server.json` file in the mcp directory.

4. **Verify registration**:
   ```bash
   # Search for your server
   curl "https://registry.modelcontextprotocol.io/v0.1/servers?search=wemo"
   ```
   
   Or visit: https://registry.modelcontextprotocol.io/

**Note:** The `server.json` file is already configured with:
- Name: `io.github.qrussell/wemo`
- PyPI package: `wemo-mcp-server`
- Repository: `https://github.com/qrussell/wemo-ops-center`

The registry validates that the PyPI package exists and matches the specified version before accepting the submission.


## Subsequent Releases

For version 1.0.1, 1.1.0, 2.0.0, etc:

1. Update version in `pyproject.toml` and `__init__.py`
2. Update CHANGELOG.md with release notes
3. Commit: `git commit -m "Release vX.X.X"`
4. Tag: `git tag mcp-vX.X.X && git push origin mcp-vX.X.X`
5. Create GitHub release with changelog
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
pip install dist/wemo_mcp_server-1.0.0-py3-none-any.whl
```

### Workflow doesn't trigger

The workflow only triggers for tags starting with `mcp-v`. Make sure your tag follows this pattern:
```bash
git tag mcp-v1.0.0  # ✅ Correct
git tag v1.0.0      # ❌ Won't trigger
```

## Resources

- [PyPI Trusted Publishing Guide](https://docs.pypi.org/trusted-publishers/)
- [Python Packaging Guide](https://packaging.python.org/)
- [MCP Registry](https://registry.modelcontextprotocol.io/)
- [MCP Registry Documentation](https://github.com/modelcontextprotocol/registry)
- [MCP Registry Quickstart](https://github.com/modelcontextprotocol/registry/blob/main/docs/modelcontextprotocol-io/quickstart.mdx)
- [GitHub Actions - PyPI Publish Action](https://github.com/pypa/gh-action-pypi-publish)
