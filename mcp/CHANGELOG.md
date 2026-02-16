# Changelog

All notable changes to the WeMo MCP Server will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.1] - 2026-02-16

### Fixed
- 📝 **MCP Registry validation** - Added `mcp-name: io.github.qrussell/wemo` to package README for registry ownership validation
- 🔧 **Registry metadata** - Updated `server.json` to version 1.0.1

This patch release enables successful publication to the official MCP Registry at https://registry.modelcontextprotocol.io/

## [1.0.0] - 2026-02-16

### Added
- 🎉 **Initial stable release** of WeMo MCP Server
- 🔍 **Multi-phase device discovery** combining UPnP/SSDP and network scanning
- ⚡ **Fast parallel scanning** with 60 concurrent workers (~23-30s for full subnet)
- 🎛️ **Full device control** (on/off/toggle/brightness for dimmers)
- ✏️ **Device management** (rename devices, extract HomeKit codes)
- 📊 **Real-time status monitoring** of all WeMo devices
- 💾 **Automatic device caching** for quick access
- 🔌 **Universal MCP client support** (Claude Desktop, Claude Code CLI, VS Code, Cursor)
- 📚 **Comprehensive documentation** with table of contents
- 🚀 **One-click installation** badges for VS Code and Cursor
- 🔧 **Prerequisites section** explaining uvx/uv requirements
- 🖼️ **Example usage screenshots** showing Claude Desktop integration

### Documentation
- Complete README with installation guides for all MCP clients
- Table of contents for easy navigation
- Detailed tool documentation with example prompts and responses
- Multi-phase discovery explanation
- Feature comparison with wemo-ops-center project
- Development setup and contribution guidelines
- Release documentation and checklist

### Tools
- `scan_network` - Discover WeMo devices with intelligent multi-phase scanning
- `list_devices` - List all cached devices from previous scans
- `get_device_status` - Get current state and information for specific devices
- `control_device` - Control devices (on/off/toggle/brightness)
- `rename_device` - Rename devices (change friendly name)
- `get_homekit_code` - Extract HomeKit setup codes

### Infrastructure
- Automated PyPI publishing via GitHub Actions
- Trusted publishing support for secure releases
- Comprehensive test suite (unit + E2E tests)
- Type hints and linting with ruff/mypy
- Code formatting with black/isort

## [0.1.0] - 2026-02-15

### Added
- Initial beta release
- Basic device discovery and control functionality
- MCP server implementation
- PyPI packaging setup

[1.0.0]: https://github.com/qrussell/wemo-ops-center/compare/mcp-v0.1.0...mcp-v1.0.0
[0.1.0]: https://github.com/qrussell/wemo-ops-center/releases/tag/mcp-v0.1.0
