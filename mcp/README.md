# WeMo MCP Server

A Model Context Protocol (MCP) server for WeMo smart home device discovery and control.

[![PyPI version](https://img.shields.io/pypi/v/wemo-mcp-server.svg)](https://pypi.org/project/wemo-mcp-server/)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![PyPI downloads](https://img.shields.io/pypi/dm/wemo-mcp-server.svg)](https://pypi.org/project/wemo-mcp-server/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![MCP](https://img.shields.io/badge/MCP-Server-blue)](https://modelcontextprotocol.io)
[![AI Integration](https://img.shields.io/badge/AI-Integration-purple)](https://modelcontextprotocol.io)

## Overview

This MCP server provides seamless integration with WeMo smart home devices, enabling discovery, monitoring, and control through the Model Context Protocol. Built on the proven [pywemo](https://github.com/pywemo/pywemo) library, it offers reliable device management with intelligent multi-phase discovery.

### Example: Controlling Devices with Claude

![Claude Desktop controlling WeMo devices](assets/claude-example.png)

*Natural language control of WeMo devices through Claude Desktop - just ask in plain English and the MCP server handles the rest.*

## Features

- **🔍 Smart Discovery**: Multi-phase device discovery combining UPnP/SSDP multicast and network scanning
- **⚡ Fast Scanning**: Parallel network probing with configurable concurrency (23-30s for full subnet)
- **🎛️ Device Control**: Turn devices on/off, toggle state, and control brightness for dimmers
- **✏️ Device Management**: Rename devices and extract HomeKit setup codes
- **📊 Status Monitoring**: Real-time device state and brightness queries
- **💾 Device Caching**: Automatic caching of discovered devices for quick access
- **🔌 MCP Integration**: Works with any MCP-compatible application (Claude Desktop, VS Code, etc.)

## Installation

### Prerequisites

- Python 3.10 or higher
- pip or uv package manager

### Install via pip (Recommended)

```bash
pip install wemo-mcp-server
```

Or using uvx (runs isolated, no global install):

```bash
uvx wemo-mcp-server
```

### Install from Source

For development or testing unreleased features:

```bash
git clone https://github.com/qrussell/wemo-ops-center.git
cd wemo-ops-center/mcp
pip install -e .
```

### Development Installation

```bash
git clone https://github.com/qrussell/wemo-ops-center.git
cd wemo-ops-center/mcp
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
uv sync --dev
```

## Usage

### Claude Desktop Integration

Add to Claude Desktop configuration (`~/Library/Application Support/Claude/claude_desktop_config.json` on macOS):

**After installing via pip/uvx:**

```json
{
  "mcpServers": {
    "wemo-mcp-server": {
      "command": "uvx",
      "args": ["wemo-mcp-server"]
    }
  }
}
```

**For development/source installation:**

```json
{
  "mcpServers": {
    "wemo-mcp-server": {
      "command": "python",
      "args": ["-m", "wemo_mcp_server"],
      "env": {
        "PYTHONPATH": "/path/to/mcp/src"
      }
    }
  }
}
```

### VS Code Integration

Add to your VS Code MCP configuration (`~/.vscode/mcp.json`):

**After installing via pip/uvx:**

```json
{
  "servers": {
    "wemo-mcp-server": {
      "type": "stdio",
      "command": "uvx",
      "args": ["wemo-mcp-server"]
    }
  }
}
```

**For development/source installation:**

```json
{
  "servers": {
    "wemo-mcp-server": {
      "type": "stdio",
      "command": "python",
      "args": ["-m", "wemo_mcp_server"],
      "env": {
        "PYTHONPATH": "/path/to/mcp/src"
      }
    }
  }
}
```

**Note:** MCP host applications automatically start and manage the server process when configured. No manual server execution is needed for normal usage.

### Manual Server Execution (Optional)

For testing or debugging, you can run the server directly:

```bash
python -m wemo_mcp_server
```

The server uses stdio transport for MCP communication.

## Available Tools

### 1. scan_network

Discover WeMo devices on your network using intelligent multi-phase scanning.

**Example Prompts:**
- "Scan for WeMo devices on my network"
- "Find all WeMo devices"
- "Discover devices on 192.168.1.0/24"

**Example Response:**
```
Found 12 WeMo devices in 23.5 seconds:

1. Office Light (Dimmer) - 192.168.1.100 - OFF
2. Living Room (Switch) - 192.168.1.101 - ON
3. Bedroom Lamp (Dimmer) - 192.168.1.102 - OFF  
...
```

### 2. list_devices

List all devices cached from previous scans.

**Example Prompts:**
- "List all my WeMo devices"
- "Show me all devices"
- "What devices do you know about?"

**Example Response:**
```
12 devices in cache:

- Office Light (Dimmer) at 192.168.1.100
- Living Room (Switch) at 192.168.1.101
- Bedroom Lamp (Dimmer) at 192.168.1.102
...
```

### 3. get_device_status

Get current state and information for a specific device.

**Example Prompts:**
- "Is the office light on?"
- "What's the status of the bedroom lamp?"
- "Check the living room switch"
- "What's the brightness of office light?"

**Example Response:**
```
Office Light (Dimmer):
- State: OFF
- Brightness: 75%
- IP: 192.168.1.100
- Model: DimmerLongPress
```

### 4. control_device

Control a WeMo device (on/off/toggle/brightness).

**Example Prompts:**
- "Turn on the office light"
- "Turn off the living room"
- "Toggle the bedroom lamp"
- "Set office light to 75%"
- "Dim the bedroom lamp to 50%"

**Example Response:**
```
✓ Office Light turned ON
  Brightness set to 75%
  Current state: ON
```

### 5. rename_device

Rename a WeMo device (change its friendly name).

**Example Prompts:**
- "Rename Office Dimmer to Office Light"
- "Change the name of the bedroom device to Bedroom Lamp"
- "Call the living room switch 'Main Light'"

**Example Response:**
```
✓ Device renamed successfully
  'Office Dimmer' → 'Office Light'
  IP: 192.168.1.100
  
The new name will appear in the WeMo app and all control interfaces.
```

### 6. get_homekit_code

Get the HomeKit setup code for a WeMo device.

**Example Prompts:**
- "Get the HomeKit code for Office Light"
- "What's the HomeKit setup code for the bedroom lamp?"
- "Show me the HomeKit code for all devices"

**Example Response:**
```
HomeKit Setup Code for 'Office Light':
  123-45-678
  
Use this code to add the device to Apple Home.
```

**Note:** Not all WeMo devices support HomeKit. If a device doesn't support HomeKit, you'll get an error message.

## How It Works

### Multi-Phase Discovery

The server uses a three-phase discovery process optimized for reliability:

1. **Phase 1 - UPnP/SSDP Discovery (Primary)**
   - Multicast discovery finds all responsive devices (~12s)
   - Most reliable method, finds devices that don't respond to port probes
   - Uses pywemo's built-in discovery mechanism

2. **Phase 2 - Network Port Scanning (Backup)**
   - Parallel probing of WeMo ports (49152-49155) across subnet
   - 60 concurrent workers for fast scanning (~10s for 254 IPs)
   - Catches devices missed by UPnP

3. **Phase 3 - Device Verification (Backup)**
   - HTTP verification of active IPs via /setup.xml
   - Parallel verification with 60 workers
   - Validates and extracts device information

This approach achieves **100% device discovery reliability** while maintaining fast scan times (23-30 seconds for complete networks).

## Feature Comparison

### MCP Server vs wemo-ops-center

Comparison of features between this MCP server and the main [wemo-ops-center](https://github.com/qrussell/wemo-ops-center) project:

| Feature | wemo-ops-center | MCP Server | Notes |
|---------|-----------------|------------|-------|
| **Device Discovery** | ✅ UPnP + Port Scan | ✅ Implemented | Multi-phase discovery with 100% reliability |
| **Device Control** | ✅ On/Off/Toggle | ✅ Implemented | Includes brightness control for dimmers |
| **Device Status** | ✅ Real-time | ✅ Implemented | Query by name or IP address |
| **Device Rename** | ✅ Friendly names | ✅ Implemented | Updates device cache automatically |
| **HomeKit Codes** | ✅ Extract codes | ✅ Implemented | For HomeKit-compatible devices |
| **Multi-subnet** | ✅ VLAN support | ❌ Planned | Currently single subnet per scan |
| **WiFi Provisioning** | ✅ Smart setup | ❌ Not planned | Requires PC WiFi connection changes |
| **Scheduling** | ✅ Time + Solar | ❌ Not planned | Requires persistent daemon (incompatible with MCP model) |
| **Maintenance Tools** | ✅ Resets | ❌ Not planned | Factory reset, clear WiFi, clear data |
| **Profile Management** | ✅ Save/Load | ❌ Not planned | WiFi credential profiles for bulk setup |
| **User Interface** | ✅ GUI + Web | ❌ N/A | MCP uses AI assistant interface |

**Legend:**
- ✅ **Implemented** - Feature is available
- ❌ **Not planned** - Feature conflicts with MCP architecture or use case
- ❌ **Planned** - Feature could be added in future

**Why some features aren't planned for MCP:**
- **Scheduling**: Requires 24/7 background daemon polling. MCP servers are typically invoked on-demand by AI assistants, not run as persistent services.
- **WiFi Provisioning**: Requires changing the host PC's WiFi connection to device setup networks, which is disruptive and platform-specific.
- **Maintenance Tools**: Destructive operations (factory reset, etc.) better suited for dedicated GUI with confirmation dialogs.

**Current MCP Coverage:** 5 of 11 core features (45%) - focused on device discovery, monitoring, and control use cases that fit the MCP model.

## Development

### Project Structure

```
mcp/
├── src/
│   └── wemo_mcp_server/
│       ├── __init__.py          # Package initialization
│       ├── __main__.py          # Module entry point
│       └── server.py            # Main MCP server implementation
├── tests/
│   ├── test_server.py           # Unit tests
│   └── test_e2e.py              # End-to-end test suite
├── pyproject.toml               # Project configuration
├── README.md                    # This file
└── LICENSE                      # MIT License
```

### Running Tests

#### E2E Test Suite (Recommended)

```bash
# Run comprehensive E2E tests (requires actual WeMo devices on network)
python -m pytest tests/test_e2e.py -v

# Or run directly
python tests/test_e2e.py
```

The E2E test suite validates all 6 MCP tools:
- ✅ Network scanning and device discovery
- ✅ Device caching and listing
- ✅ Status retrieval (by name and IP)
- ✅ Device control (optional, set `TEST_CONTROL = True`)
- ✅ Device rename
- ✅ HomeKit code extraction

#### Unit Tests

```bash
pytest tests/test_server.py -v
```

## Contributing

Contributions welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes with tests
4. Run the test suite (`python tests/test_e2e.py`)
5. Commit your changes (`git commit -m 'Add amazing feature'`)
6. Push to the branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

## License

MIT License - see [LICENSE](LICENSE) file for details.

## Acknowledgments

- Built with [Model Context Protocol SDK](https://github.com/modelcontextprotocol/python-sdk)
- Uses [pywemo](https://github.com/pywemo/pywemo) for WeMo device communication
- Part of the [wemo-ops-center](https://github.com/qrussell/wemo-ops-center) project
