#!/usr/bin/env python3
"""Lightroom接続チェックスクリプト"""
import asyncio
import sys

from lightroom_sdk.paths import get_port_file

PORT_FILE = get_port_file()


def main():
    if not PORT_FILE.exists():
        print("[ ] Port file not found. Is Lightroom running with the plugin?")
        sys.exit(1)

    try:
        from lightroom_sdk.resilient_bridge import ResilientSocketBridge

        bridge = ResilientSocketBridge()
        loop = asyncio.new_event_loop()
        try:
            result = loop.run_until_complete(
                bridge.send_command("system.ping", timeout=5.0)
            )
            loop.run_until_complete(bridge.disconnect())
        finally:
            loop.close()
        print("[OK] Lightroom connection successful")
        sys.exit(0)
    except Exception as e:
        print(f"[ ] Connection failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
