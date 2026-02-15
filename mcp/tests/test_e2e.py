#!/usr/bin/env python3
"""
E2E Test Suite for WeMo MCP Server
Tests all 6 MCP tools: scan_network, list_devices, get_device_status, control_device,
rename_device, get_homekit_code
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from wemo_mcp_server.server import (
    scan_network,
    list_devices,
    get_device_status,
    control_device,
    rename_device,
    get_homekit_code
)


# Test configuration
TEST_CONTROL = False  # Set to True to test actual device control (will toggle devices!)
EXPECTED_DEVICE_COUNT = 12  # Expected number of devices


class TestResults:
    """Track test results."""
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.skipped = 0
        self.tests = []
    
    def add(self, name: str, status: str, message: str = ""):
        """Add test result."""
        self.tests.append((name, status, message))
        if status == "PASS":
            self.passed += 1
        elif status == "FAIL":
            self.failed += 1
        elif status == "SKIP":
            self.skipped += 1
    
    def print_summary(self):
        """Print test summary."""
        print("\n" + "=" * 70)
        print("📊 TEST SUMMARY")
        print("=" * 70)
        
        for name, status, message in self.tests:
            icon = "✅" if status == "PASS" else "❌" if status == "FAIL" else "⚠️"
            msg = f" - {message}" if message else ""
            print(f"{icon} {name}: {status}{msg}")
        
        print(f"\n📈 Results: {self.passed} passed, {self.failed} failed, {self.skipped} skipped")
        
        if self.failed == 0:
            print("🎉 ALL TESTS PASSED!")
        else:
            print(f"⚠️  {self.failed} test(s) failed")


async def test_scan_network(results: TestResults):
    """Test 1: Network scanning."""
    print("\n" + "=" * 70)
    print("TEST 1: scan_network()")
    print("=" * 70)
    
    try:
        print("📡 Scanning network for WeMo devices...")
        scan_result = await scan_network(
            subnet="192.168.1.0/24",
            timeout=0.6,
            max_workers=60
        )
        
        device_count = len(scan_result["devices"])
        scan_time = scan_result["results"]["scan_duration_seconds"]
        
        print(f"Found {device_count} devices in {scan_time:.2f}s")
        
        # Show some devices
        for i, device in enumerate(scan_result["devices"][:5], 1):
            state_icon = "🟢" if device['state'] == "on" else "⚫"
            print(f"  {i}. {state_icon} {device['name']} @ {device['ip_address']}")
        
        if device_count > 5:
            print(f"  ... and {device_count - 5} more")
        
        # Assertions
        if device_count == 0:
            results.add("scan_network", "FAIL", "No devices found")
            return None
        elif device_count < EXPECTED_DEVICE_COUNT:
            results.add("scan_network", "PASS", f"Found {device_count}/{EXPECTED_DEVICE_COUNT} devices (some missing)")
        else:
            results.add("scan_network", "PASS", f"Found all {device_count} devices")
        
        return scan_result
    
    except Exception as e:
        print(f"❌ Error: {e}")
        results.add("scan_network", "FAIL", str(e))
        return None


async def test_list_devices(results: TestResults):
    """Test 2: List cached devices."""
    print("\n" + "=" * 70)
    print("TEST 2: list_devices()")
    print("=" * 70)
    
    try:
        print("📋 Listing cached devices...")
        list_result = await list_devices()
        
        device_count = list_result['device_count']
        print(f"Cache contains {device_count} devices")
        
        if device_count > 0:
            results.add("list_devices", "PASS", f"{device_count} devices in cache")
        else:
            results.add("list_devices", "FAIL", "Cache is empty")
        
        return list_result
    
    except Exception as e:
        print(f"❌ Error: {e}")
        results.add("list_devices", "FAIL", str(e))
        return None


async def test_get_device_status(results: TestResults, scan_result):
    """Test 3: Get device status (test by name and by IP)."""
    print("\n" + "=" * 70)
    print("TEST 3: get_device_status()")
    print("=" * 70)
    
    if not scan_result or not scan_result["devices"]:
        results.add("get_device_status (by name)", "SKIP", "No devices available")
        results.add("get_device_status (by IP)", "SKIP", "No devices available")
        return
    
    device = scan_result["devices"][0]
    device_name = device["name"]
    device_ip = device["ip_address"]
    is_dimmer = device["device_type"] in ["Dimmer", "DimmerLongPress"]
    
    # Test 3a: Get status by name
    try:
        print(f"📊 Getting status by name: '{device_name}'")
        status_result = await get_device_status(device_name)
        
        if "error" in status_result:
            print(f"❌ Error: {status_result['error']}")
            results.add("get_device_status (by name)", "FAIL", status_result['error'])
        else:
            state = status_result["state"]
            state_icon = "🟢" if state == "on" else "⚫"
            print(f"  State: {state_icon} {state.upper()}")
            
            if is_dimmer and 'brightness' in status_result:
                print(f"  Brightness: {status_result['brightness']}%")
                results.add("get_device_status (by name)", "PASS", f"State: {state}, Brightness: {status_result['brightness']}%")
            else:
                results.add("get_device_status (by name)", "PASS", f"State: {state}")
    
    except Exception as e:
        print(f"❌ Error: {e}")
        results.add("get_device_status (by name)", "FAIL", str(e))
    
    # Test 3b: Get status by IP
    try:
        print(f"📊 Getting status by IP: {device_ip}")
        status_result = await get_device_status(device_ip)
        
        if "error" in status_result:
            print(f"❌ Error: {status_result['error']}")
            results.add("get_device_status (by IP)", "FAIL", status_result['error'])
        else:
            state = status_result["state"]
            state_icon = "🟢" if state == "on" else "⚫"
            print(f"  State: {state_icon} {state.upper()}")
            results.add("get_device_status (by IP)", "PASS", f"State: {state}")
    
    except Exception as e:
        print(f"❌ Error: {e}")
        results.add("get_device_status (by IP)", "FAIL", str(e))


async def test_control_device(results: TestResults, scan_result):
    """Test 4: Control device (toggle, optional)."""
    print("\n" + "=" * 70)
    print("TEST 4: control_device()")
    print("=" * 70)
    
    if not TEST_CONTROL:
        print("⚠️  Skipping control tests (TEST_CONTROL = False)")
        print("   Set TEST_CONTROL = True at top of file to test actual device control")
        results.add("control_device (toggle)", "SKIP", "TEST_CONTROL disabled")
        results.add("control_device (brightness)", "SKIP", "TEST_CONTROL disabled")
        return
    
    if not scan_result or not scan_result["devices"]:
        results.add("control_device (toggle)", "SKIP", "No devices available")
        results.add("control_device (brightness)", "SKIP", "No devices available")
        return
    
    device = scan_result["devices"][0]
    device_name = device["name"]
    is_dimmer = device["device_type"] in ["Dimmer", "DimmerLongPress"]
    
    # Test 4a: Toggle test
    try:
        print(f"🎛️  Testing toggle on '{device_name}'...")
        
        # Get original state
        original_status = await get_device_status(device_name)
        original_state = original_status["state"]
        print(f"  Original state: {original_state.upper()}")
        
        # Toggle
        control_result = await control_device(device_name, "toggle")
        
        if control_result["success"]:
            new_state = control_result['new_state']
            print(f"  ✅ Toggled to: {new_state.upper()}")
            
            # Toggle back
            await asyncio.sleep(1)
            control_result2 = await control_device(device_name, "toggle")
            restored_state = control_result2['new_state']
            print(f"  ✅ Restored to: {restored_state.upper()}")
            
            if restored_state == original_state:
                results.add("control_device (toggle)", "PASS", "Toggle and restore successful")
            else:
                results.add("control_device (toggle)", "FAIL", f"State mismatch: expected {original_state}, got {restored_state}")
        else:
            print(f"  ❌ Control failed: {control_result.get('error')}")
            results.add("control_device (toggle)", "FAIL", control_result.get('error'))
    
    except Exception as e:
        print(f"❌ Error: {e}")
        results.add("control_device (toggle)", "FAIL", str(e))
    
    # Test 4b: Brightness test (only for dimmers)
    if is_dimmer:
        try:
            print(f"🔆 Testing brightness control on '{device_name}'...")
            
            # Get original brightness
            original_status = await get_device_status(device_name)
            original_brightness = original_status.get("brightness", 50)
            print(f"  Original brightness: {original_brightness}%")
            
            # Set to 50%
            control_result = await control_device(device_name, "brightness", brightness=50)
            
            if control_result["success"]:
                print(f"  ✅ Set brightness to 50%")
                
                # Restore original
                await asyncio.sleep(1)
                control_result2 = await control_device(device_name, "brightness", brightness=original_brightness)
                print(f"  ✅ Restored brightness to {original_brightness}%")
                
                results.add("control_device (brightness)", "PASS", "Brightness control successful")
            else:
                print(f"  ❌ Brightness control failed: {control_result.get('error')}")
                results.add("control_device (brightness)", "FAIL", control_result.get('error'))
        
        except Exception as e:
            print(f"❌ Error: {e}")
            results.add("control_device (brightness)", "FAIL", str(e))
    else:
        results.add("control_device (brightness)", "SKIP", "Not a dimmer")


async def test_rename_device(results: TestResults, scan_result: dict):
    """Test 5: Device renaming."""
    print("\n" + "=" * 70)
    print("TEST 5: rename_device()")
    print("=" * 70)
    
    if not TEST_CONTROL:
        results.add("rename_device", "SKIP", "Control tests disabled")
        return
    
    if not scan_result or not scan_result["devices"]:
        results.add("rename_device", "SKIP", "No devices available")
        return
    
    # Find a device to test with
    device = None
    for d in scan_result["devices"]:
        # Skip devices we don't want to mess with (optional filter)
        device = d
        break
    
    if not device:
        results.add("rename_device", "SKIP", "No suitable device found")
        return
    
    original_name = device["name"]
    test_name = f"{original_name}_TEST"
    
    try:
        print(f"✏️  Testing rename on '{original_name}'...")
        
        # Rename to test name
        print(f"  Step 1: Renaming to '{test_name}'...")
        rename_result = await rename_device(original_name, test_name)
        
        if not rename_result["success"]:
            print(f"  ❌ Rename failed: {rename_result.get('error')}")
            results.add("rename_device", "FAIL", rename_result.get('error'))
            return
        
        print(f"  ✅ Renamed to '{test_name}'")
        
        # Wait a moment
        await asyncio.sleep(1)
        
        # Verify we can access it by new name
        print(f"  Step 2: Verifying with get_device_status...")
        status = await get_device_status(test_name)
        
        if "error" in status:
            print(f"  ❌ Can't access device by new name: {status.get('error')}")
            results.add("rename_device", "FAIL", "Device not accessible by new name")
        else:
            print(f"  ✅ Device accessible as '{test_name}'")
        
        # Restore original name
        print(f"  Step 3: Restoring original name '{original_name}'...")
        restore_result = await rename_device(test_name, original_name)
        
        if restore_result["success"]:
            print(f"  ✅ Restored to '{original_name}'")
            results.add("rename_device", "PASS", "Rename and restore successful")
        else:
            print(f"  ⚠️  Restore failed: {restore_result.get('error')}")
            results.add("rename_device", "FAIL", f"Restore failed: {restore_result.get('error')}")
    
    except Exception as e:
        print(f"❌ Error: {e}")
        results.add("rename_device", "FAIL", str(e))
        
        # Try to restore name on error
        try:
            print(f"  Attempting to restore original name...")
            await rename_device(test_name, original_name)
            print(f"  ✅ Original name restored")
        except:
            print(f"  ⚠️  Could not restore original name automatically")


async def test_get_homekit_code(results: TestResults, scan_result: dict):
    """Test 6: HomeKit code retrieval."""
    print("\n" + "=" * 70)
    print("TEST 6: get_homekit_code()")
    print("=" * 70)
    
    if not scan_result or not scan_result["devices"]:
        results.add("get_homekit_code", "SKIP", "No devices available")
        return
    
    # Try to get HomeKit code from first device
    device = scan_result["devices"][0]
    device_name = device["name"]
    
    try:
        print(f"🏠 Testing HomeKit code retrieval from '{device_name}'...")
        
        hk_result = await get_homekit_code(device_name)
        
        if hk_result["success"]:
            code = hk_result["homekit_code"]
            print(f"  ✅ HomeKit code: {code}")
            results.add("get_homekit_code", "PASS", f"Code retrieved: {code}")
        else:
            error = hk_result.get("error", "Unknown error")
            # HomeKit not being available is expected for some devices
            if "does not support HomeKit" in error or "no basicevent" in error.lower():
                print(f"  ⚠️  Device doesn't support HomeKit (expected for some devices)")
                results.add("get_homekit_code", "SKIP", "Device doesn't support HomeKit")
            else:
                print(f"  ❌ Unexpected error: {error}")
                results.add("get_homekit_code", "FAIL", error)
    
    except Exception as e:
        print(f"❌ Error: {e}")
        results.add("get_homekit_code", "FAIL", str(e))


async def main():
    """Run all E2E tests."""
    
    print("🧪 WEMO MCP SERVER - E2E TEST SUITE")
    print("=" * 70)
    print(f"Expected devices: {EXPECTED_DEVICE_COUNT}")
    print(f"Control tests: {'ENABLED' if TEST_CONTROL else 'DISABLED'}")
    print("=" * 70)
    
    results = TestResults()
    
    # Run tests
    scan_result = await test_scan_network(results)
    await test_list_devices(results)
    await test_get_device_status(results, scan_result)
    await test_control_device(results, scan_result)
    await test_rename_device(results, scan_result)
    await test_get_homekit_code(results, scan_result)
    
    # Print summary
    results.print_summary()
    
    print("\n📚 MCP Tools Reference:")
    print("  1. scan_network(subnet, timeout, max_workers) - Discover WeMo devices")
    print("  2. list_devices() - List cached devices from previous scans")
    print("  3. get_device_status(device_identifier) - Get current device state")
    print("  4. control_device(device_identifier, action, brightness) - Control devices")
    print("  5. rename_device(device_identifier, new_name) - Rename devices")
    print("  6. get_homekit_code(device_identifier) - Get HomeKit setup code")
    print()
    
    # Exit with appropriate code
    sys.exit(0 if results.failed == 0 else 1)


if __name__ == "__main__":
    asyncio.run(main())
