"""Lightroom connection lifecycle manager for MCP Server.

C2: LightroomClient.execute_command() 経由でコマンドを実行する。
    client._bridge 直アクセスは行わない（例外正規化を崩さないため）。
C1: mutating=True のコマンドは再接続後に再送せずエラー返却する。
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages LightroomClient lifecycle with lazy connect and asyncio.Lock."""

    def __init__(self, port_file: str | None = None):
        self._port_file = port_file
        self._client = None
        self._lock = asyncio.Lock()
        self._reconnected = False

    async def execute(
        self,
        command: str,
        params: dict[str, Any],
        timeout: float,
        mutating: bool,
    ) -> dict[str, Any]:
        """Execute a command with validation, locking, and error handling."""
        # 1. Validation
        from lightroom_sdk.validation import ValidationError, validate_params

        try:
            validated = validate_params(command, params)
        except ValidationError as e:
            return {
                "isError": True,
                "code": "VALIDATION_ERROR",
                "message": str(e),
                "suggestions": e.suggestions if hasattr(e, "suggestions") else [],
            }

        # 2. C1: mutating コマンドの再接続後チェック
        if mutating and self._reconnected:
            self._reconnected = False
            return {
                "isError": True,
                "code": "MUTATING_NOT_RETRIED",
                "message": (
                    "接続が切断されたため、mutating コマンドは安全のため再送されませんでした。"
                    "再度実行してください。"
                ),
            }

        # 3. Execute with lock
        try:
            async with asyncio.timeout(timeout):
                async with self._lock:
                    client = await self._get_client()
                    result = await client.execute_command(command, validated, timeout=timeout)
                    return {"result": result}
        except (ConnectionError, OSError) as e:
            logger.warning(f"Connection error on '{command}': {e}")
            self._client = None
            self._reconnected = True
            if mutating:
                return {
                    "isError": True,
                    "code": "MUTATING_NOT_RETRIED",
                    "message": (
                        "接続が切断されたため、mutating コマンドは安全のため再送されませんでした。"
                        "再度実行してください。"
                    ),
                }
            return {
                "isError": True,
                "code": "CONNECTION_ERROR",
                "message": (
                    "Lightroom に接続できません。Lightroom Classic が起動し、"
                    "CLI Bridge プラグインが有効であることを確認してください。"
                ),
            }
        except (asyncio.TimeoutError, TimeoutError):
            return {
                "isError": True,
                "code": "TIMEOUT_ERROR",
                "message": f"コマンドがタイムアウトしました ({timeout}秒)。",
            }
        except Exception as e:
            from lightroom_sdk.exceptions import ConnectionError as LRConnectionError
            from lightroom_sdk.exceptions import LightroomSDKError
            from lightroom_sdk.exceptions import TimeoutError as LRTimeoutError

            if isinstance(e, LRConnectionError):
                self._client = None
                self._reconnected = True
                if mutating:
                    return {
                        "isError": True,
                        "code": "MUTATING_NOT_RETRIED",
                        "message": (
                            "接続が切断されたため、mutating コマンドは安全のため再送されませんでした。"
                            "再度実行してください。"
                        ),
                    }
                return {
                    "isError": True,
                    "code": "CONNECTION_ERROR",
                    "message": (
                        "Lightroom に接続できません。Lightroom Classic が起動し、"
                        "CLI Bridge プラグインが有効であることを確認してください。"
                    ),
                }
            if isinstance(e, LRTimeoutError):
                return {
                    "isError": True,
                    "code": "TIMEOUT_ERROR",
                    "message": f"コマンドがタイムアウトしました ({timeout}秒)。",
                }
            if isinstance(e, LightroomSDKError):
                return {
                    "isError": True,
                    "code": e.code if hasattr(e, "code") else "SDK_ERROR",
                    "message": str(e),
                }
            logger.exception(f"Unexpected error on '{command}'")
            return {
                "isError": True,
                "code": "INTERNAL_ERROR",
                "message": str(e),
            }

    async def _get_client(self):
        """Get or create LightroomClient (lazy initialization)."""
        if self._client is None:
            from lightroom_sdk.client import LightroomClient

            self._client = LightroomClient(port_file=self._port_file)
            await self._client.connect()
        return self._client

    async def get_status(self) -> dict[str, Any]:
        """Get connection status for MCP resource."""
        if self._client is None:
            return {"connected": False, "state": "disconnected"}
        state = self._client._bridge.state.value
        return {"connected": state == "connected", "state": state}

    async def shutdown(self) -> None:
        """Clean shutdown."""
        if self._client:
            try:
                await self._client.disconnect()
            except Exception:
                pass
            self._client = None
