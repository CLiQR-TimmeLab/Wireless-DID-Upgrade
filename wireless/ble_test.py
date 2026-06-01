import asyncio
import sys
from bleak import BleakScanner, BleakClient
from bleak.exc import BleakError


# ── Windows asyncio fix ───────────────────────────────────────────────────────
# On Windows, the default asyncio event loop policy can cause issues with BLE.
# This line switches to a compatible one. Always include this on Windows.
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


# ── Part 1: Scan for BLE devices ─────────────────────────────────────────────
async def scan_devices(timeout: float = 5.0) -> list:
    """
    Scan for nearby BLE devices and print their address and name.

    Args:
        timeout: How many seconds to scan. 5s is enough for most devices.

    Returns:
        List of discovered BleakScanner device objects.
    """
    print(f"\n[SCAN] Scanning for BLE devices ({timeout}s)...")
    print("[SCAN] Make sure Bluetooth is enabled on this PC.\n")

    devices = await BleakScanner.discover(timeout=timeout)

    if not devices:
        print("[SCAN] No devices found.")
        print("       Tips: Is Bluetooth on? Is your test device advertising?")
        return []

    print(f"[SCAN] Found {len(devices)} device(s):")
    for i, d in enumerate(devices):
        name = d.name if d.name else "(unnamed)"
        print(f"  [{i}] Address: {d.address}   Name: {name}")

    return devices


# ── Part 2: Connect and explore GATT table ───────────────────────────────────
async def connect_and_explore(address: str) -> None:
    """
    Connect to a BLE device and print its full GATT table:
    Services → Characteristics → Properties → Values (if readable).

    This teaches you what real BLE devices look like before you design
    your own GATT layout in Task 0.4.

    Args:
        address: BLE MAC address string, e.g. "AA:BB:CC:DD:EE:FF"
    """
    print(f"\n[CONNECT] Connecting to {address} ...")

    try:
        # 'async with' automatically disconnects when the block exits
        # This is the correct pattern — always clean up BLE connections
        async with BleakClient(address, timeout=10.0) as client:

            if not client.is_connected:
                print("[CONNECT] Failed to connect.")
                return

            print(f"[CONNECT] Connected successfully!\n")
            print("[GATT] Exploring services and characteristics:")
            print("-" * 60)

            # Walk every service on the device
            for service in client.services:
                print(f"\n  SERVICE: {service.uuid}")
                if service.description:
                    print(f"           ({service.description})")

                # Walk every characteristic in this service
                for char in service.characteristics:
                    props = ", ".join(char.properties)
                    print(f"\n    CHARACTERISTIC: {char.uuid}")
                    print(f"    Properties    : {props}")

                    # If readable, try to read the current value
                    if "read" in char.properties:
                        try:
                            value = await client.read_gatt_char(char.uuid)
                            print(f"    Value (hex)   : {value.hex()}")
                            # Also try to decode as text if it looks like ASCII
                            try:
                                print(f"    Value (text)  : {value.decode('utf-8')}")
                            except UnicodeDecodeError:
                                pass  # Not text data, that's fine
                        except BleakError as e:
                            print(f"    Read error    : {e}")

            print("\n" + "-" * 60)
            print("[GATT] Exploration complete.")

    except BleakError as e:
        print(f"[CONNECT] BleakError: {e}")
        print("          Try: Is the device still advertising? Is it paired?")
    except asyncio.TimeoutError:
        print("[CONNECT] Connection timed out. Device may be out of range.")


# ── Part 3: Test simultaneous connections ────────────────────────────────────
async def test_simultaneous_connections(addresses: list[str]) -> None:
    """
    Attempt to connect to multiple BLE devices at the same time.

    Windows BLE stack has a documented limit of ~7 concurrent connections.
    This function tests how many we can actually hold open at once.
    Document your results in your written summary for Task 0.3.

    Args:
        addresses: List of BLE MAC address strings to connect to simultaneously.
    """
    print(f"\n[MULTI] Testing {len(addresses)} simultaneous connections...")

    results = {}  # address → success/fail

    async def connect_one(addr: str) -> None:
        """Connect to one device, hold for 5s, then disconnect."""
        try:
            async with BleakClient(addr, timeout=10.0) as client:
                status = "CONNECTED" if client.is_connected else "FAILED"
                results[addr] = status
                print(f"  [{status}] {addr}")
                await asyncio.sleep(5)  # Hold connection open
        except BleakError as e:
            results[addr] = f"ERROR: {e}"
            print(f"  [ERROR] {addr} → {e}")

    # asyncio.gather runs all coroutines CONCURRENTLY
    # This is the same pattern used in Task 2.5 (batch download of 24 devices)
    await asyncio.gather(*[connect_one(addr) for addr in addresses])

    # Summary
    print(f"\n[MULTI] Results ({len(addresses)} attempted):")
    for addr, result in results.items():
        print(f"  {addr}: {result}")

    successful = sum(1 for r in results.values() if r == "CONNECTED")
    print(f"\n[MULTI] Successfully held {successful}/{len(addresses)} connections.")
    print("        Document this number in your Task 0.3 written summary.")


# ── Main entry point ──────────────────────────────────────────────────────────
async def main():
    print("=" * 60)
    print("  CLiQR Project — Task 0.3: BLE Research (bleak on Windows)")
    print("=" * 60)

    # ── Step 1: Scan ──────────────────────────────────────────────────────
    devices = await scan_devices(timeout=5.0)

    if not devices:
        print("\nNo devices found. Exiting.")
        print("Tip: Use 'BLE Peripheral Simulator' app on a phone to create")
        print("     a test BLE device if you have no other hardware available.")
        return

    # ── Step 2: Connect and explore the first device ──────────────────────
    # Pick the first discovered device. You can change this index or
    # hardcode a specific address: address = "AA:BB:CC:DD:EE:FF"
    target = devices[0]
    print(f"\n[INFO] Targeting device: {target.name or '(unnamed)'} @ {target.address}")
    await connect_and_explore(target.address)

    # ── Step 3: Multi-connection test ─────────────────────────────────────
    # If you have more than one BLE device, add their addresses here.
    # Even testing with 2-3 devices is valuable to document.
    #
    # To run this test, uncomment the lines below and add real addresses:
    #
    # test_addresses = [
    #     "AA:BB:CC:DD:EE:FF",   # device 1
    #     "11:22:33:44:55:66",   # device 2
    # ]
    # await test_simultaneous_connections(test_addresses)
    #
    print("\n[INFO] Multi-connection test is commented out by default.")
    print("       Add device addresses above and uncomment to test.")

    print("\n[DONE] Task 0.3 complete!")


if __name__ == "__main__":
    asyncio.run(main())
