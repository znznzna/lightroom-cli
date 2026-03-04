import asyncio
import enum
import logging
from typing import Optional, Dict, Any, Callable

from .socket_bridge import SocketBridge

logger = logging.getLogger(__name__)


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
        port_file: str = "/tmp/lightroom_ports.txt",
        max_reconnect_attempts: int = 5,
        heartbeat_interval: float = 30.0,
    ):
        self._host = host
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
        self._state = ConnectionState.CONNECTING
        self._bridge = SocketBridge(self._host, self._port_file)

        # イベントハンドラを転送
        for name, handlers in self._event_handlers.items():
            for h in handlers:
                self._bridge.on_event(name, h)

        # シャットダウンイベント監視
        self._bridge.on_event("server.shutdown", self._handle_shutdown_event)

        await self._bridge.connect(retry_attempts=1)
        self._state = ConnectionState.CONNECTED

        if self._heartbeat_interval > 0:
            self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())

    async def send_command(self, command: str, params=None, timeout=30.0):
        if self._state == ConnectionState.SHUTDOWN:
            from .exceptions import ConnectionError as LRConnectionError
            raise LRConnectionError("Lightroom is shutting down")

        try:
            return await self._bridge.send_command(command, params, timeout)
        except (ConnectionError, OSError, EOFError) as e:
            if self._state == ConnectionState.SHUTDOWN:
                raise
            logger.warning(f"Connection error on '{command}', reconnecting: {e}")
            await self._reconnect()
            return await self._bridge.send_command(command, params, timeout)
        except asyncio.TimeoutError:
            raise
        except Exception as e:
            # Import here to avoid circular dependency
            from .exceptions import ConnectionError as LRConnectionError
            # Only retry on connection-related exceptions, not application errors
            if self._state == ConnectionState.SHUTDOWN:
                raise
            if isinstance(e, LRConnectionError):
                logger.warning(f"LR connection error on '{command}', reconnecting: {e}")
                await self._reconnect()
                return await self._bridge.send_command(command, params, timeout)
            raise

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
        from .exceptions import ConnectionError as LRConnectionError
        raise LRConnectionError("Reconnection failed")

    def _handle_shutdown_event(self, data: Dict[str, Any]) -> None:
        logger.info(f"Shutdown event received: {data}")
        self._state = ConnectionState.SHUTDOWN

    async def disconnect(self) -> None:
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:
                pass
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
