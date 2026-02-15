"""Main MCP server implementation for WeMo device management."""

import asyncio
import concurrent.futures
import ipaddress
import json
import logging
import socket
import sys
import time
from typing import Any, Dict, List, Optional
from contextlib import asynccontextmanager

import pywemo
from mcp.server.fastmcp import FastMCP


# Configure logging to stderr for MCP
logging.basicConfig(
    stream=sys.stderr,
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Initialize FastMCP server
mcp = FastMCP("wemo-mcp-server")

# Global device cache to store discovered devices
_device_cache: Dict[str, Any] = {}  # key: device name or IP, value: pywemo device object


# ==============================================================================
#  WeMo Device Scanner (using pywemo)
# ==============================================================================

class WeMoScanner:
    """Scanner for discovering WeMo devices on the network using pywemo."""
    
    def __init__(self):
        self.timeout = 0.6
        self.wemo_ports = [49152, 49153, 49154, 49155]
        
    def probe_port(self, ip: str, ports: List[int] = None, timeout: float = None) -> Optional[str]:
        """
        Probe an IP address on common WeMo ports.
        
        Args:
            ip: IP address to probe
            ports: List of ports to check (default: WeMo ports)
            timeout: Connection timeout
            
        Returns:
            IP address if responsive, None otherwise
        """
        if ports is None:
            ports = self.wemo_ports
        if timeout is None:
            timeout = self.timeout
            
        for port in ports:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(timeout)
            try:
                s.connect((str(ip), port))
                s.close()
                return str(ip)
            except:
                pass
            finally:
                s.close()
        return None
    
    def scan_subnet(self, target_cidr: str, max_workers: int = 60) -> List[Any]:
        """
        Scan a subnet for WeMo devices.
        Uses UPnP/SSDP discovery FIRST (primary method), then port scanning as backup.
        This matches the proven approach from wemo-ops-center UI.
        
        Args:
            target_cidr: CIDR notation subnet (e.g., "192.168.1.0/24")
            max_workers: Maximum concurrent workers for scanning
            
        Returns:
            List of discovered pywemo device objects
        """
        found_devices = []
        
        # Phase 1: UPnP/SSDP Discovery (PRIMARY - most reliable method)
        # This is what wemo-ops-center UI uses first
        logger.info("Phase 1: Running UPnP/SSDP discovery (primary method)...")
        try:
            upnp_devices = pywemo.discover_devices()
            found_devices.extend(upnp_devices)
            logger.info(f"UPnP/SSDP found {len(upnp_devices)} WeMo devices")
            for dev in upnp_devices:
                logger.info(f"  • {dev.name} at {dev.host}:{dev.port}")
        except Exception as e:
            logger.warning(f"UPnP discovery failed: {e}")
        
        try:
            network = ipaddress.ip_network(target_cidr, strict=False)
            all_hosts = list(network.hosts())
            logger.info(f"Phase 2: Backup port scan on {len(all_hosts)} hosts in {target_cidr}")
        except Exception as e:
            logger.error(f"Invalid CIDR notation: {target_cidr} - {e}")
            return found_devices
        
        # Phase 2: Probe for active IPs (backup method for devices that don't respond to UPnP)
        active_ips = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(self.probe_port, ip): ip for ip in all_hosts}
            for future in concurrent.futures.as_completed(futures):
                result = future.result()
                if result:
                    active_ips.append(result)
                    logger.debug(f"Active IP found: {result}")
        
        # Phase 3: Verify active IPs (only check IPs not already found via UPnP)
        found_ips = {d.host for d in found_devices if hasattr(d, 'host')}
        active_ips_to_check = [ip for ip in active_ips if ip not in found_ips]
        
        if active_ips_to_check:
            logger.info(f"Found {len(active_ips_to_check)} new active IPs to verify...")
            
            # Temporarily reduce pywemo's timeout to speed up scans
            original_timeout = pywemo.discovery.REQUESTS_TIMEOUT
            pywemo.discovery.REQUESTS_TIMEOUT = 5  # Reduce from 10s to 5s (some devices are slow responders)
            
            def verify_device(ip: str) -> Optional[Any]:
                """Try to verify if an IP is a WeMo device."""
                for port in self.wemo_ports:
                    try:
                        url = f"http://{ip}:{port}/setup.xml"
                        dev = pywemo.discovery.device_from_description(url)
                        if dev:
                            logger.info(f"WeMo device found via port scan: {dev.name} at {ip}:{port}")
                            return dev
                    except Exception:
                        pass
                return None
            
            # Parallelize device verification to avoid sequential timeouts
            with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                verification_futures = {executor.submit(verify_device, ip): ip for ip in active_ips_to_check}
                for future in concurrent.futures.as_completed(verification_futures):
                    device = future.result()
                    if device:
                        found_devices.append(device)
            
            # Restore original timeout
            pywemo.discovery.REQUESTS_TIMEOUT = original_timeout
        
        logger.info(f"Scan complete. Found {len(found_devices)} WeMo devices total")
        return found_devices


def extract_device_info(device: Any) -> Dict[str, Any]:
    """
    Extract device information from a pywemo device object.
    
    Args:
        device: pywemo device object
        
    Returns:
        Dictionary containing device information
    """
    try:
        return {
            "name": device.name,
            "model": device.model_name if hasattr(device, 'model_name') else device.model,
            "serial_number": getattr(device, 'serial_number', "N/A"),
            "ip_address": device.host if hasattr(device, 'host') else "unknown",
            "port": device.port if hasattr(device, 'port') else 49153,
            "mac_address": device.mac if hasattr(device, 'mac') else "N/A",
            "firmware_version": device.firmware_version if hasattr(device, 'firmware_version') else "N/A",
            "state": "on" if device.get_state() else "off" if hasattr(device, 'get_state') else "unknown",
            "device_type": type(device).__name__,
            "manufacturer": "Belkin",
        }
    except Exception as e:
        logger.warning(f"Error extracting device info: {e}")
        return {
            "name": getattr(device, 'name', 'Unknown'),
            "model": getattr(device, 'model', 'Unknown'),
            "error": str(e)
        }


@mcp.tool()
async def scan_network(
    subnet: str = "192.168.1.0/24",
    timeout: float = 0.6,
    max_workers: int = 60
) -> Dict[str, Any]:
    """
    Scan network for WeMo devices using pywemo discovery.
    
    This tool scans the specified subnet for WeMo devices by:
    1. Probing all IPs in the subnet on common WeMo ports (49152-49155)
    2. Verifying responsive IPs by attempting to read device descriptions
    3. Using pywemo library to properly identify and parse WeMo devices
    
    Args:
        subnet: Network subnet in CIDR notation (e.g., "192.168.1.0/24")
        timeout: Connection timeout in seconds for port probing
        max_workers: Maximum concurrent workers for network scanning
    
    Returns:
        Dictionary containing:
        - scan_parameters: The parameters used for scanning
        - results: Summary with device counts
        - devices: List of discovered WeMo devices with full details
    """
    start_time = time.time()
    
    try:
        logger.info(f"Starting WeMo network scan for subnet: {subnet}")
        
        # Create scanner instance
        scanner = WeMoScanner()
        scanner.timeout = timeout
        
        # Run the synchronous scan in a thread pool to keep async interface
        loop = asyncio.get_event_loop()
        devices = await loop.run_in_executor(
            None,
            scanner.scan_subnet,
            subnet,
            max_workers
        )
        
        # Extract device information
        device_list = []
        for device in devices:
            device_info = extract_device_info(device)
            device_list.append(device_info)
            
            # Cache the device object for later control operations
            _device_cache[device.name] = device
            if hasattr(device, 'host'):
                _device_cache[device.host] = device
        
        elapsed_time = time.time() - start_time
        
        scan_result = {
            "scan_parameters": {
                "subnet": subnet,
                "timeout": timeout,
                "max_workers": max_workers
            },
            "results": {
                "total_devices_found": len(device_list),
                "wemo_devices": len(device_list),
                "scan_duration_seconds": round(elapsed_time, 2)
            },
            "devices": device_list,
            "scan_completed": True,
            "timestamp": time.time()
        }
        
        logger.info(f"Scan completed in {elapsed_time:.2f}s. Found {len(device_list)} WeMo devices")
        return scan_result
        
    except Exception as e:
        error_result = {
            "error": f"Network scan failed: {str(e)}",
            "scan_parameters": {
                "subnet": subnet,
                "timeout": timeout,
                "max_workers": max_workers
            },
            "scan_completed": False,
            "timestamp": time.time()
        }
        logger.error(f"Network scan error: {str(e)}", exc_info=True)
        return error_result


@mcp.tool()
async def list_devices() -> Dict[str, Any]:
    """
    List all discovered WeMo devices from the cache.
    
    Returns a list of devices that were found in previous network scans.
    Run scan_network first to populate the device cache.
    
    Returns:
        Dictionary containing:
        - device_count: Number of cached devices
        - devices: List of device names and IPs
    """
    try:
        # Get unique devices (device cache may have duplicates by name and IP)
        unique_devices = {}
        for key, device in _device_cache.items():
            device_name = device.name
            if device_name not in unique_devices:
                unique_devices[device_name] = {
                    "name": device_name,
                    "ip_address": getattr(device, 'host', 'unknown'),
                    "model": getattr(device, 'model', 'Unknown'),
                    "type": type(device).__name__
                }
        
        return {
            "device_count": len(unique_devices),
            "devices": list(unique_devices.values()),
            "cache_keys": len(_device_cache)
        }
    except Exception as e:
        logger.error(f"Error listing devices: {e}", exc_info=True)
        return {
            "error": str(e),
            "device_count": 0,
            "devices": []
        }


@mcp.tool()
async def get_device_status(device_identifier: str) -> Dict[str, Any]:
    """
    Get the current status of a WeMo device.
    
    Retrieves the current state and information for a device by name or IP address.
    The device must have been discovered via scan_network first.
    
    Args:
        device_identifier: Device name (e.g., "Office Light") or IP address (e.g., "192.168.1.100")
    
    Returns:
        Dictionary containing:
        - device_name: Name of the device
        - state: Current state ("on" or "off")
        - Additional device information
    """
    try:
        # Try to find device in cache
        device = _device_cache.get(device_identifier)
        
        if not device:
            return {
                "error": f"Device '{device_identifier}' not found in cache",
                "suggestion": "Run scan_network first to discover devices",
                "available_devices": [k for k in _device_cache.keys() if isinstance(k, str) and not k.replace('.', '').isdigit()]
            }
        
        # Get device state
        loop = asyncio.get_event_loop()
        state = await loop.run_in_executor(None, device.get_state, True)  # force_update=True
        
        # Extract full device info
        device_info = extract_device_info(device)
        device_info["state"] = "on" if state else "off"
        device_info["status_retrieved_at"] = time.time()
        
        # Add brightness for dimmer devices
        if hasattr(device, 'get_brightness'):
            brightness = await loop.run_in_executor(None, device.get_brightness, True)
            device_info["brightness"] = brightness
            device_info["is_dimmer"] = True
        else:
            device_info["is_dimmer"] = False
        
        logger.info(f"Status retrieved for {device.name}: {device_info['state']}" + 
                   (f" Brightness: {device_info.get('brightness')}" if device_info.get('is_dimmer') else ""))
        return device_info
        
    except Exception as e:
        logger.error(f"Error getting device status: {e}", exc_info=True)
        return {
            "error": f"Failed to get device status: {str(e)}",
            "device_identifier": device_identifier
        }


@mcp.tool()
async def control_device(
    device_identifier: str,
    action: str,
    brightness: int = None
) -> Dict[str, Any]:
    """
    Control a WeMo device (turn on, off, toggle, or set brightness).
    
    Controls a device by sending turn on, turn off, or toggle commands.
    For dimmer devices, you can also set the brightness level (1-100).
    The device must have been discovered via scan_network first.
    
    Args:
        device_identifier: Device name (e.g., "Office Light") or IP address (e.g., "192.168.1.100")
        action: Action to perform - must be one of: "on", "off", "toggle", "brightness"
        brightness: Brightness level (1-100) - only used when action is "brightness" or "on" for dimmer devices
    
    Returns:
        Dictionary containing:
        - success: Boolean indicating if the action succeeded
        - device_name: Name of the device
        - action_performed: The action that was executed
        - new_state: The state after the action
        - brightness: Current brightness level (for dimmers)
    """
    try:
        # Validate action
        action = action.lower()
        if action not in ["on", "off", "toggle", "brightness"]:
            return {
                "error": f"Invalid action '{action}'. Must be 'on', 'off', 'toggle', or 'brightness'",
                "success": False
            }
        
        # Validate brightness if provided
        if brightness is not None and (brightness < 1 or brightness > 100):
            return {
                "error": f"Invalid brightness '{brightness}'. Must be between 1 and 100",
                "success": False
            }
        
        # Try to find device in cache
        device = _device_cache.get(device_identifier)
        
        if not device:
            return {
                "error": f"Device '{device_identifier}' not found in cache",
                "suggestion": "Run scan_network first to discover devices",
                "available_devices": [k for k in _device_cache.keys() if isinstance(k, str) and not k.replace('.', '').isdigit()],
                "success": False
            }
        
        # Perform the action in a thread pool
        loop = asyncio.get_event_loop()
        
        # Check if device is a dimmer (has brightness methods)
        is_dimmer = hasattr(device, 'set_brightness') and hasattr(device, 'get_brightness')
        
        if action == "brightness":
            if not is_dimmer:
                return {
                    "error": f"Device '{device.name}' is not a dimmer and does not support brightness control",
                    "device_type": type(device).__name__,
                    "success": False
                }
            if brightness is None:
                return {
                    "error": "Brightness value is required when action is 'brightness'",
                    "success": False
                }
            await loop.run_in_executor(None, device.set_brightness, brightness)
            
        elif action == "on":
            if is_dimmer and brightness is not None:
                # For dimmers, turn on and set brightness in one operation
                await loop.run_in_executor(None, device.set_brightness, brightness)
            else:
                await loop.run_in_executor(None, device.on)
                
        elif action == "off":
            await loop.run_in_executor(None, device.off)
            
        elif action == "toggle":
            await loop.run_in_executor(None, device.toggle)
        
        # Wait a moment for the device to respond
        await asyncio.sleep(0.5)
        
        # Get the new state
        new_state = await loop.run_in_executor(None, device.get_state, True)
        
        result = {
            "success": True,
            "device_name": device.name,
            "action_performed": action,
            "new_state": "on" if new_state else "off",
            "device_type": type(device).__name__,
            "timestamp": time.time()
        }
        
        # Add brightness for dimmers
        if is_dimmer:
            current_brightness = await loop.run_in_executor(None, device.get_brightness, True)
            result["brightness"] = current_brightness
            result["is_dimmer"] = True
        else:
            result["is_dimmer"] = False
        
        logger.info(f"Device '{device.name}' {action} successful. New state: {result['new_state']}" + 
                   (f" Brightness: {result.get('brightness')}" if is_dimmer else ""))
        return result
        
    except Exception as e:
        logger.error(f"Error controlling device: {e}", exc_info=True)
        return {
            "error": f"Failed to control device: {str(e)}",
            "device_identifier": device_identifier,
            "action": action,
            "success": False
        }


@mcp.tool()
async def rename_device(
    device_identifier: str,
    new_name: str
) -> Dict[str, Any]:
    """
    Rename a WeMo device (change its friendly name).
    
    Changes the friendly name of a WeMo device. This is the name that appears
    in the WeMo app and is used to identify the device. The device must have
    been discovered via scan_network first.
    
    After renaming, the device cache will be updated with the new name. You may
    want to run scan_network again to refresh the device list.
    
    Args:
        device_identifier: Current device name (e.g., "Office Dimmer") or IP address (e.g., "192.168.1.100")
        new_name: New friendly name for the device (e.g., "Office Light")
    
    Returns:
        Dictionary containing:
        - success: Boolean indicating if the rename succeeded
        - old_name: The previous name of the device
        - new_name: The new name of the device
        - device_ip: IP address of the device
    """
    try:
        # Validate new name
        if not new_name or not new_name.strip():
            return {
                "error": "New name cannot be empty",
                "success": False
            }
        
        new_name = new_name.strip()
        
        # Try to find device in cache
        device = _device_cache.get(device_identifier)
        
        if not device:
            return {
                "error": f"Device '{device_identifier}' not found in cache",
                "suggestion": "Run scan_network first to discover devices",
                "available_devices": [k for k in _device_cache.keys() if isinstance(k, str) and not k.replace('.', '').isdigit()],
                "success": False
            }
        
        old_name = device.name
        device_ip = getattr(device, 'host', 'unknown')
        
        # Perform the rename operation in a thread pool
        loop = asyncio.get_event_loop()
        
        # Try both methods for compatibility with different pywemo versions
        def rename_operation():
            if hasattr(device, 'change_friendly_name'):
                device.change_friendly_name(new_name)
            elif hasattr(device, 'basicevent'):
                device.basicevent.ChangeFriendlyName(FriendlyName=new_name)
            else:
                raise AttributeError("Device does not support renaming")
        
        await loop.run_in_executor(None, rename_operation)
        
        # Wait a moment for the device to respond
        await asyncio.sleep(0.5)
        
        # Update the cache with the new name
        # Remove old name entry and add new one
        if old_name in _device_cache:
            del _device_cache[old_name]
        _device_cache[new_name] = device
        
        # Also update IP-based cache entry if it exists
        if device_ip in _device_cache:
            _device_cache[device_ip] = device
        
        result = {
            "success": True,
            "old_name": old_name,
            "new_name": new_name,
            "device_ip": device_ip,
            "message": f"Device renamed from '{old_name}' to '{new_name}'",
            "timestamp": time.time()
        }
        
        logger.info(f"Device renamed: '{old_name}' -> '{new_name}' at {device_ip}")
        return result
        
    except Exception as e:
        logger.error(f"Error renaming device: {e}", exc_info=True)
        return {
            "error": f"Failed to rename device: {str(e)}",
            "device_identifier": device_identifier,
            "new_name": new_name,
            "success": False
        }


@mcp.tool()
async def get_homekit_code(device_identifier: str) -> Dict[str, Any]:
    """
    Get the HomeKit setup code for a WeMo device.
    
    Retrieves the HomeKit setup code (HKSetupCode) for devices that support
    HomeKit integration. This code can be used to add the device to Apple Home.
    The device must have been discovered via scan_network first.
    
    Note: Not all WeMo devices support HomeKit. If a device doesn't support
    HomeKit or doesn't have a setup code, an error will be returned.
    
    Args:
        device_identifier: Device name (e.g., "Office Light") or IP address (e.g., "192.168.1.100")
    
    Returns:
        Dictionary containing:
        - success: Boolean indicating if the code was retrieved
        - device_name: Name of the device
        - homekit_code: The HomeKit setup code (format: XXX-XX-XXX)
        - device_ip: IP address of the device
    """
    try:
        # Try to find device in cache
        device = _device_cache.get(device_identifier)
        
        if not device:
            return {
                "error": f"Device '{device_identifier}' not found in cache",
                "suggestion": "Run scan_network first to discover devices",
                "available_devices": [k for k in _device_cache.keys() if isinstance(k, str) and not k.replace('.', '').isdigit()],
                "success": False
            }
        
        device_name = device.name
        device_ip = getattr(device, 'host', 'unknown')
        
        # Check if device has basicevent (required for HomeKit info)
        if not hasattr(device, 'basicevent'):
            return {
                "error": f"Device '{device_name}' does not support HomeKit (no basicevent service)",
                "device_name": device_name,
                "device_type": type(device).__name__,
                "success": False
            }
        
        # Get HomeKit setup info in a thread pool
        loop = asyncio.get_event_loop()
        
        def get_hk_info():
            return device.basicevent.GetHKSetupInfo()
        
        hk_info = await loop.run_in_executor(None, get_hk_info)
        
        # Extract the HomeKit code
        hk_code = hk_info.get('HKSetupCode')
        
        if not hk_code:
            return {
                "error": f"Device '{device_name}' does not have a HomeKit setup code",
                "device_name": device_name,
                "device_ip": device_ip,
                "device_type": type(device).__name__,
                "homekit_info_available": hk_info,
                "success": False
            }
        
        result = {
            "success": True,
            "device_name": device_name,
            "homekit_code": hk_code,
            "device_ip": device_ip,
            "device_type": type(device).__name__,
            "message": f"HomeKit setup code for '{device_name}': {hk_code}",
            "timestamp": time.time()
        }
        
        logger.info(f"HomeKit code retrieved for '{device_name}': {hk_code}")
        return result
        
    except Exception as e:
        logger.error(f"Error getting HomeKit code: {e}", exc_info=True)
        
        # Provide helpful error messages for common issues
        error_msg = str(e)
        if "UPnPError" in error_msg or "Action" in error_msg:
            error_msg = f"Device does not support HomeKit or the HomeKit feature is not available: {error_msg}"
        
        return {
            "error": f"Failed to get HomeKit code: {error_msg}",
            "device_identifier": device_identifier,
            "success": False
        }


def main() -> None:
    """Main entry point for the MCP server."""
    logger.info("Starting WeMo MCP Server...")
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()