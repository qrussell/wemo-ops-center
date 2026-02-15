"""Unit tests for WeMo MCP server components."""

import pytest
from unittest.mock import Mock, patch
from wemo_mcp_server.server import WeMoScanner, extract_device_info


class TestWeMoScanner:
    """Tests for WeMoScanner class."""
    
    def test_scanner_initialization(self):
        """Test scanner initializes with correct defaults."""
        scanner = WeMoScanner()
        
        assert scanner.timeout == 0.6
        assert scanner.wemo_ports == [49152, 49153, 49154, 49155]
    
    def test_probe_port_with_custom_timeout(self):
        """Test probe_port accepts custom timeout."""
        scanner = WeMoScanner()
        
        # This will fail to connect but should respect timeout
        result = scanner.probe_port("192.168.1.255", timeout=0.1)
        
        assert result is None  # No device at this IP
    
    def test_probe_port_with_custom_ports(self):
        """Test probe_port accepts custom port list."""
        scanner = WeMoScanner()
        
        result = scanner.probe_port("192.168.1.255", ports=[8080], timeout=0.1)
        
        assert result is None


class TestExtractDeviceInfo:
    """Tests for extract_device_info function."""
    
    def test_extract_device_info_complete(self):
        """Test extracting complete device information."""
        # Create mock device with all attributes
        mock_device = Mock()
        mock_device.name = "Test Device"
        mock_device.model_name = "Dimmer"
        mock_device.serial_number = "TEST123456"
        mock_device.host = "192.168.1.100"
        mock_device.port = 49153
        mock_device.mac = "AA:BB:CC:DD:EE:FF"
        mock_device.firmware_version = "WeMo_WW_2.00.11573"
        mock_device.get_state = Mock(return_value=1)  # On state
        
        result = extract_device_info(mock_device)
        
        assert result["name"] == "Test Device"
        assert result["model"] == "Dimmer"
        assert result["serial_number"] == "TEST123456"
        assert result["ip_address"] == "192.168.1.100"
        assert result["port"] == 49153
        assert result["mac_address"] == "AA:BB:CC:DD:EE:FF"
        assert result["firmware_version"] == "WeMo_WW_2.00.11573"
        assert result["state"] == "on"
        assert result["manufacturer"] == "Belkin"
    
    def test_extract_device_info_minimal(self):
        """Test extracting info from device with minimal attributes."""
        mock_device = Mock()
        mock_device.name = "Minimal Device"
        mock_device.model = "Socket"
        
        # Remove optional attributes
        del mock_device.model_name
        del mock_device.serial_number
        del mock_device.host
        del mock_device.port
        del mock_device.mac
        del mock_device.firmware_version
        
        mock_device.get_state = Mock(return_value=0)  # Off state
        
        result = extract_device_info(mock_device)
        
        assert result["name"] == "Minimal Device"
        assert result["model"] == "Socket"
        assert result["serial_number"] == "N/A"
        assert result["ip_address"] == "unknown"
        assert result["port"] == 49153  # Default
        assert result["mac_address"] == "N/A"
        assert result["firmware_version"] == "N/A"
        assert result["state"] == "off"
    
    def test_extract_device_info_with_exception(self):
        """Test handling of exceptions during extraction."""
        mock_device = Mock()
        mock_device.name = "Error Device"
        mock_device.model = "Unknown"
        mock_device.get_state = Mock(side_effect=Exception("Connection error"))
        
        # Should not raise exception, but return partial info
        result = extract_device_info(mock_device)
        
        assert "name" in result
        assert "error" in result


class TestDeviceCache:
    """Tests for device caching functionality."""
    
    @pytest.mark.asyncio
    async def test_device_cache_structure(self):
        """Test that device cache has correct structure."""
        from wemo_mcp_server.server import _device_cache
        
        # Verify cache is a dictionary
        assert isinstance(_device_cache, dict)


@pytest.mark.asyncio
class TestAsyncFunctions:
    """Tests for async MCP tool functions."""
    
    async def test_scan_network_returns_dict(self):
        """Test scan_network returns properly structured dictionary."""
        from wemo_mcp_server.server import scan_network
        
        with patch('wemo_mcp_server.server.WeMoScanner') as MockScanner:
            # Mock scanner to return empty list
            mock_instance = MockScanner.return_value
            mock_instance.scan_subnet = Mock(return_value=[])
            
            result = await scan_network("192.168.1.0/24", timeout=0.1, max_workers=1)
            
            assert "scan_parameters" in result
            assert "results" in result
            assert "devices" in result
            assert "scan_completed" in result
            assert result["scan_parameters"]["subnet"] == "192.168.1.0/24"
    
    async def test_list_devices_returns_dict(self):
        """Test list_devices returns properly structured dictionary."""
        from wemo_mcp_server.server import list_devices, _device_cache
        
        # Clear and setup cache
        _device_cache.clear()
        
        result = await list_devices()
        
        assert "device_count" in result
        assert "devices" in result
        assert isinstance(result["devices"], list)
        assert result["device_count"] == 0  # Empty cache
    
    async def test_get_device_status_not_found(self):
        """Test get_device_status with non-existent device."""
        from wemo_mcp_server.server import get_device_status, _device_cache
        
        _device_cache.clear()
        
        result = await get_device_status("NonExistentDevice")
        
        assert "error" in result
        assert "not found" in result["error"].lower()
    
    async def test_control_device_invalid_action(self):
        """Test control_device with invalid action."""
        from wemo_mcp_server.server import control_device
        
        result = await control_device("TestDevice", "invalid_action")
        
        assert "error" in result
        assert "Invalid action" in result["error"]
        assert result["success"] is False
    
    async def test_control_device_invalid_brightness(self):
        """Test control_device with invalid brightness value."""
        from wemo_mcp_server.server import control_device
        
        result = await control_device("TestDevice", "brightness", brightness=150)
        
        assert "error" in result
        assert "Invalid brightness" in result["error"]
        assert result["success"] is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
