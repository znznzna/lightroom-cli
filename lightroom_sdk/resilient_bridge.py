import asyncio
import enum
import logging
from typing import Any, Callable, Dict, Optional

from .socket_bridge import SocketBridge

logger = logging.getLogger(__name__)


def _retry_safe(command: str) -> bool:
    """Unknown commands count as unsafe: resending is opt-in per schema"""
    from .schema import COMMAND_SCHEMAS

    schema = COMMAND_SCHEMAS.get(command)
    return schema is not None and schema.retry_safe


class ConnectionState(enum.Enum):
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"
    SHUTDOWN = "shutdown"


class ResilientSocketBridge:
    """自動再接続・ハートビート付きSocketBridgeラッパー"""

    def __init__(
        self,
        host: str = "localhost",
        port_file: str | None = None,
        max_reconnect_attempts: int = 5,
        heartbeat_interval: float = 30.0,
    ):
        self._host = host
        if port_file is None:
            from .paths import get_port_file

            self._port_file = str(get_port_file())
        else:
            self._port_file = port_file
        self._max_reconnect = max_reconnect_attempts
        self._heartbeat_interval = heartbeat_interval
        self._bridge: Optional[SocketBridge] = None
        self._state = ConnectionState.DISCONNECTED
        self._heartbeat_task: Optional[asyncio.Task] = None
        self._event_handlers: Dict[str, list[Callable]] = {}

    @property
    def state(self) -> ConnectionState:
        return self._state

    def on_event(self, event_name: str, handler: Callable) -> None:
        if event_name not in self._event_handlers:
            self._event_handlers[event_name] = []
        self._event_handlers[event_name].append(handler)

    async def connect(self) -> None:
        await self._stop_heartbeat()
        self._state = ConnectionState.CONNECTING
        self._bridge = SocketBridge(self._host, self._port_file)

        # イベントハンドラを転送
        for name, handlers in self._event_handlers.items():
            for h in handlers:
                self._bridge.on_event(name, h)

        # シャットダウンイベント監視
        self._bridge.on_event("server.shutdown", self._handle_shutdown_event)

        await self._bridge.connect(retry_attempts=3, retry_delay=0.5)
        self._state = ConnectionState.CONNECTED

        if self._heartbeat_interval > 0:
            self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())

    async def send_command(self, command: str, params=None, timeout=30.0):
        if self._state == ConnectionState.SHUTDOWN:
            from .exceptions import ConnectionError as LRConnectionError

            raise LRConnectionError("Lightroom is shutting down")

        if self._state == ConnectionState.DISCONNECTED:
            await self.connect()

        from .exceptions import ConnectionError as LRConnectionError
        from .exceptions import RequestNotSentError, ResultUnknownError

        # At most two attempts. Every failure goes through the same classification, so a drop
        # during the resend is still reported as RESULT_UNKNOWN for commands that are not retry-safe.
        for attempt in range(2):
            try:
                return await self._bridge.send_command(command, params, timeout)
            except asyncio.TimeoutError:
                raise
            except (ConnectionError, OSError, EOFError, LRConnectionError) as e:
                # builtin ConnectionError is a subclass of OSError; LRConnectionError is the SDK's own
                if self._state == ConnectionState.SHUTDOWN:
                    raise
                not_sent = isinstance(e, RequestNotSentError)
                if not (not_sent or _retry_safe(command)):
                    # The request may already have been applied; sending it again could apply it twice.
                    # Drop the connection so the next command starts from a fresh one.
                    logger.warning(f"Connection error on '{command}', not resending: {e}")
                    await self._drop_bridge()
                    raise ResultUnknownError(
                        f"Connection lost while running '{command}'. It may or may not have been applied, "
                        "so it was not resent. Check the result in Lightroom before running it again.",
                        details={"command": command},
                    ) from e
                if attempt == 1:
                    # Nothing was applied (not sent) or resending is harmless; just report the failure
                    await self._drop_bridge()
                    raise
                logger.warning(f"Connection error on '{command}', reconnecting: {e}")
                await self._reconnect()
        raise AssertionError("unreachable")

    async def _drop_bridge(self) -> None:
        """Close the current bridge; the next send_command reconnects from scratch"""
        # Detach synchronously, before the first await: a concurrent send_command may reconnect
        # meanwhile, and its new bridge must not be the one closed here. Forgetting the reference
        # also keeps later cleanup (CLI finally / __aexit__) from closing the dead bridge a second time.
        self._state = ConnectionState.DISCONNECTED
        bridge, self._bridge = self._bridge, None
        await self._stop_heartbeat()
        if bridge:
            try:
                await bridge.disconnect()
            except Exception:
                pass

    async def _stop_heartbeat(self) -> None:
        task, self._heartbeat_task = self._heartbeat_task, None
        if task is None or task is asyncio.current_task():
            return
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

    async def _reconnect(self) -> None:
        self._state = ConnectionState.RECONNECTING
        # 旧bridgeをクリーンアップ（ソケットリーク防止）
        if self._bridge:
            try:
                await self._bridge.disconnect()
            except Exception:
                pass
        delay = 1.0
        for attempt in range(self._max_reconnect):
            try:
                self._bridge = SocketBridge(self._host, self._port_file)
                for name, handlers in self._event_handlers.items():
                    for h in handlers:
                        self._bridge.on_event(name, h)
                self._bridge.on_event("server.shutdown", self._handle_shutdown_event)
                await self._bridge.connect(retry_attempts=1)
                self._state = ConnectionState.CONNECTED
                return
            except Exception:
                if self._bridge:
                    try:
                        await self._bridge.disconnect()
                    except Exception:
                        pass
                await asyncio.sleep(delay)
                delay = min(delay * 2, 30.0)
        self._state = ConnectionState.DISCONNECTED
        self._bridge = None  # already closed above
        from .exceptions import ConnectionError as LRConnectionError

        raise LRConnectionError("Reconnection failed")

    def _handle_shutdown_event(self, data: Dict[str, Any]) -> None:
        logger.info(f"Shutdown event received: {data}")
        self._state = ConnectionState.SHUTDOWN

    async def disconnect(self) -> None:
        await self._stop_heartbeat()
        if self._bridge:
            await self._bridge.disconnect()
        self._state = ConnectionState.DISCONNECTED

    async def _heartbeat_loop(self) -> None:
        while self._state == ConnectionState.CONNECTED:
            try:
                await asyncio.sleep(self._heartbeat_interval)
                await self._bridge.send_command("system.ping", timeout=5.0)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.warning(f"Heartbeat failed: {e}")
