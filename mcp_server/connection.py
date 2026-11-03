"""Lightroom connection lifecycle manager for MCP Server.

C2: LightroomClient.execute_command() 経由でコマンドを実行する。
    client._bridge 直アクセスは行わない（例外正規化を崩さないため）。
C1: mutating=True のコマンドは再接続後に再送せずエラー返却する。

NOTE: ResilientSocketBridge が再送するのは、送信前に切れていたときと、スキーマで
      retry_safe（読み取り専用かつ二度送っても効果が重ならない）なコマンドだけ。
      それ以外は ResultUnknownError になり、ここで RESULT_UNKNOWN として返す。
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
        confirmed: bool = False,
    ) -> dict[str, Any]:
        """Execute a command with validation, locking, and error handling."""
        # 0. 確認が要る破壊的操作は confirm なしでは送らない
        from lightroom_sdk.validation import ConfirmationRequiredError, check_confirmation

        try:
            check_confirmation(command, confirmed)
        except ConfirmationRequiredError as e:
            return {
                "isError": True,
                "code": e.code,
                "message": str(e),
                "suggestions": ["Call the tool again with confirm=true", "Use dry_run=true first to preview"],
            }

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
                    "接続が切断されたため、mutating コマンドは安全のため再送されませんでした。再度実行してください。"
                ),
            }

        # 3. Execute with lock (asyncio.wait_for for Python 3.10 compatibility)
        try:

            async def _execute():
                async with self._lock:
                    client = await self._get_client()
                    return await client.execute_command(command, validated, timeout=timeout)

            result = await asyncio.wait_for(_execute(), timeout=timeout)
            return {"result": result}
        except (asyncio.TimeoutError, TimeoutError):
            # Checked before OSError: the builtin TimeoutError is an OSError subclass.
            # The connection itself is fine, so it is kept; the bridge already forgot the request.
            return {
                "isError": True,
                "code": "TIMEOUT_ERROR",
                "message": f"コマンドがタイムアウトしました ({timeout}秒)。",
            }
        except (ConnectionError, OSError) as e:
            logger.warning(f"Connection error on '{command}': {e}")
            await self._discard_client()
            if mutating:
                # mutating コマンドは再送しない。_reconnected はセットしない（次回は新規接続扱い）
                return {
                    "isError": True,
                    "code": "MUTATING_NOT_RETRIED",
                    "message": (
                        "接続が切断されたため、mutating コマンドは安全のため再送されませんでした。"
                        "再度実行してください。"
                    ),
                }
            self._reconnected = True
            return {
                "isError": True,
                "code": "CONNECTION_ERROR",
                "message": (
                    "Lightroom に接続できません。Lightroom Classic が起動し、"
                    "CLI Bridge プラグインが有効であることを確認してください。"
                ),
            }
        except Exception as e:
            from lightroom_sdk.exceptions import ConnectionError as LRConnectionError
            from lightroom_sdk.exceptions import LightroomSDKError, ResultUnknownError
            from lightroom_sdk.exceptions import TimeoutError as LRTimeoutError

            if isinstance(e, ResultUnknownError):
                await self._discard_client()
                return {
                    "isError": True,
                    "code": "RESULT_UNKNOWN",
                    "message": (
                        "実行中に接続が切れたため、コマンドが反映されたかどうか分かりません。"
                        "二重に実行しないよう再送はしていません。Lightroom で結果を確かめてから実行し直してください。"
                    ),
                }
            if isinstance(e, LRConnectionError):
                await self._discard_client()
                if mutating:
                    return {
                        "isError": True,
                        "code": "MUTATING_NOT_RETRIED",
                        "message": (
                            "接続が切断されたため、mutating コマンドは安全のため再送されませんでした。"
                            "再度実行してください。"
                        ),
                    }
                self._reconnected = True
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

            client = LightroomClient(port_file=self._port_file)
            try:
                await client.connect()
            except BaseException:
                # Failed or cancelled (e.g. by the timeout) halfway: close what was opened
                await self._close(client)
                raise
            self._client = client
        return self._client

    async def _discard_client(self) -> None:
        """Forget the current client and close its sockets, so the next command connects afresh"""
        client, self._client = self._client, None
        if client:
            await self._close(client)

    @staticmethod
    async def _close(client) -> None:
        try:
            await client.disconnect()
        except Exception:
            logger.debug("Error while closing a discarded Lightroom client", exc_info=True)

    async def get_status(self) -> str:
        """Get connection status for MCP resource (JSON string).

        fastmcp >=3.0 のリソースは str / bytes を返す必要がある。
        """
        import json

        if self._client is None:
            return json.dumps({"connected": False, "state": "disconnected"})
        state = self._client._bridge.state.value
        return json.dumps({"connected": state == "connected", "state": state})

    async def shutdown(self) -> None:
        """Clean shutdown."""
        await self._discard_client()
