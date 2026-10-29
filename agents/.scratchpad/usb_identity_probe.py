"""Inspect D405 USB identity records to distinguish devices from their child services."""
import plistlib
import subprocess

nodes = plistlib.loads(subprocess.check_output(["ioreg", "-a", "-r", "-c", "IOUSBHostDevice"]))
while nodes:
    node = nodes.pop()
    nodes.extend(node.get("IORegistryEntryChildren", []))
    if node.get("idVendor") == 0x8086 and node.get("idProduct") == 0x0B5B:
        print({key: value for key, value in node.items()
               if key.startswith("IO") and not isinstance(value, (dict, list, bytes))
               or key in ("locationID", "USB Serial Number", "kUSBSerialNumberString")}, flush=True)
