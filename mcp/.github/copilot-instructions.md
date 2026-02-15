<!-- Use this file to provide workspace-specific custom instructions to Copilot. For more details, visit https://code.visualstudio.com/docs/copilot/copilot-customization#_use-a-githubcopilotinstructionsmd-file -->

# WeMo MCP Server Project Instructions

This project is a Model Context Protocol (MCP) server for WeMo device management with network scanning capabilities.

## Project Overview
- **Type**: MCP Server (Python-based using FastMCP)
- **Primary Function**: Network scanning and WeMo device discovery
- **Framework**: MCP Python SDK with FastMCP
- **Integration**: VS Code MCP configuration ready
- **Transport**: stdio (JSON-RPC over stdin/stdout)

## Development Guidelines
- Follow MCP server development patterns using FastMCP
- Use async/await for network operations
- Implement proper error handling for network scanning and device discovery
- Structure tools following MCP protocol specifications
- Keep network scanning non-invasive and efficient
- Log to stderr only (not stdout) to avoid corrupting MCP JSON-RPC messages

## Key Components
1. **Scan Network Tool**: Primary functionality for discovering WeMo devices on the network
2. **Device Discovery**: Identify WeMo devices by manufacturer signatures and XML parsing
3. **Network Analysis**: Scan specified IP ranges with configurable timeout and concurrency
4. **Device Information Extraction**: Parse UPnP XML descriptions for device details
5. **JSON Output**: Format results in structured device information

## Project Structure
```
mcp/
├── src/wemo_mcp_server/
│   ├── __init__.py          # Package initialization and version
│   └── server.py            # Main MCP server implementation with FastMCP
├── tests/
│   ├── __init__.py
│   └── test_server.py       # Unit tests for server functionality
├── .vscode/
│   ├── mcp.json            # MCP client configuration for VS Code
│   ├── tasks.json          # VS Code tasks (run server, run tests)
│   └── launch.json         # VS Code debug configurations
├── pyproject.toml          # Project metadata and dependencies
├── README.md               # Comprehensive project documentation
└── .github/
    └── copilot-instructions.md  # This file
```

## Available Tools
- `scan_network(subnet, timeout, max_concurrent)`: Scan network for WeMo and other devices

## Testing Approach
- Unit tests with pytest for device identification and XML parsing
- Async test support with pytest-asyncio
- Mock-based testing for network operations
- Test network scanning in isolated environments
- Validate device discovery accuracy
- Ensure proper error handling for network timeouts
- Verify VS Code MCP integration works correctly

## Development Commands
- Run server: `python -m wemo_mcp_server` (with PYTHONPATH=src)
- Run tests: `pytest tests/ -v`
- Format code: `black src/`
- Sort imports: `isort src/`
- Type check: `mypy src/`
- Lint: `ruff check src/`

## VS Code Integration
- MCP configuration: `.vscode/mcp.json`
- Tasks available: "Run WeMo MCP Server", "Test WeMo MCP Server"
- Debug configurations: "Debug WeMo MCP Server", "Debug WeMo MCP Server Tests"
- Python environment: Uses local .venv with MCP dependencies

## Key Dependencies
- mcp>=1.2.0: Model Context Protocol SDK
- httpx>=0.25.0: Async HTTP client for device communication
- Dev dependencies: pytest, black, isort, mypy, ruff