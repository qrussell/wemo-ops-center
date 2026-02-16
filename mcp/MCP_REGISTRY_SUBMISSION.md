# MCP Registry Submission Instructions

## Status: Ready for qrussell to publish ✅

The WeMo MCP Server v1.0.0 is ready for submission to the official MCP Registry. Since the package is published from the `qrussell/wemo-ops-center` repository, **@qrussell needs to complete the registry submission**.

## Why qrussell needs to do this

The MCP Registry validates namespace ownership:
- Server name: `io.github.qrussell/wemo`
- Only GitHub user `qrussell` can publish under `io.github.qrussell/*`
- The PyPI package `wemo-mcp-server` is published from qrussell's GitHub Actions

## Steps for @qrussell

### 1. Install mcp-publisher CLI

```bash
# Option 1: Homebrew (recommended)
brew install mcp-publisher

# Option 2: Direct download
curl -L "https://github.com/modelcontextprotocol/registry/releases/latest/download/mcp-publisher_$(uname -s | tr '[:upper:]' '[:lower:]')_$(uname -m | sed 's/x86_64/amd64/;s/aarch64/arm64/').tar.gz" | tar xz mcp-publisher
mkdir -p ~/.local/bin
mv mcp-publisher ~/.local/bin/
export PATH="$HOME/.local/bin:$PATH"
```

### 2. Verify installation

```bash
mcp-publisher --version
# Should show version info
```

### 3. Authenticate with GitHub

```bash
mcp-publisher login github
```

This will:
1. Display a URL: https://github.com/login/device
2. Show a code (e.g., ABCD-1234)
3. You visit the URL, enter the code, and authorize
4. Returns to terminal with "Successfully logged in"

### 4. Navigate to the repo

```bash
cd /path/to/wemo-ops-center
git pull origin main
cd mcp
```

### 5. Publish to MCP Registry

```bash
mcp-publisher publish
```

Expected output:
```
Publishing to https://registry.modelcontextprotocol.io...
✓ Successfully published
✓ Server io.github.qrussell/wemo version 1.0.0
```

### 6. Verify publication

```bash
# Search for the server
curl "https://registry.modelcontextprotocol.io/v0.1/servers?search=wemo"

# Or visit the registry
open https://registry.modelcontextprotocol.io/
```

## What's already configured

✅ **server.json** - Registry metadata file ready in `mcp/server.json`
✅ **PyPI package** - v1.0.0 published at https://pypi.org/project/wemo-mcp-server/
✅ **GitHub release** - v1.0.0 tagged and released
✅ **Documentation** - README and release docs updated

## Troubleshooting

### "You do not have permission to publish this server"
- Make sure you're logged in as the correct GitHub user
- Run `mcp-publisher logout` then `mcp-publisher login github` again

### "Validation failed"
- Check that PyPI package v1.0.0 exists: https://pypi.org/project/wemo-mcp-server/
- Verify server.json matches the schema

### "Registry validation failed"
- The package on PyPI must match the version in server.json (1.0.0)
- The repository URL must be accessible

## After publishing

Once published, the server will be:
- 🔍 Searchable at https://registry.modelcontextprotocol.io/
- 📦 Installable via Claude Desktop, VS Code, Cursor
- 🌐 Discoverable by the MCP community

## Questions?

- MCP Registry docs: https://github.com/modelcontextprotocol/registry
- Registry API: https://registry.modelcontextprotocol.io/docs
- Discord: https://modelcontextprotocol.io/community/communication
