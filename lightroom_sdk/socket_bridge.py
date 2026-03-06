import asyncio
import json
import logging
import uuid
from asyncio import StreamReader, StreamWriter
from pathlib import Path
from typing import Any, Callable, Dict, Optional, Tuple

logger = logging.getLogger(__name__)


class StreamAggregator:
    """Aggregates NDJSON streaming events for a single request"""

    def __init__(self, loop: Optional[asyncio.AbstractEventLoop] = None):
        self.chunks: list[Dict[str, Any]] = []
        self.errors: list[Dict[str, Any]] = []
        self.final: Optional[Dict[str, Any]] = None
        self.future: asyncio.Future = (loop or asyncio.get_running_loop()).create_future()
        self.progress_callback: Optional[Callable] = None


class SocketBridge:
    """Manages dual socket connections to Lightroom plugin"""

    def __init__(self, host: str = "localhost", port_file: str | None = None):
        self.host = host
        if port_file is None:
            from .paths import get_port_file

            self.port_file = get_port_file()
        else:
            self.port_file = Path(port_file)
        self._send_writer: Optional[StreamWriter] = None
        self._receive_reader: Optional[StreamReader] = None
        self._receive_writer: Optional[StreamWriter] = None  # sender接続のwriter参照保持
        self._pending_requests: Dict[str, asyncio.Future] = {}
        self._pending_streams: Dict[str, StreamAggregator] = {}
        self._receive_task: Optional[asyncio.Task] = None
        self._connected = False
        self._event_handlers: Dict[str, list[Callable]] = {}

    def on_event(self, event_name: str, handler: Callable) -> None:
        """イベントハンドラを登録"""
        if event_name not in self._event_handlers:
            self._event_handlers[event_name] = []
        self._event_handlers[event_name].append(handler)

    async def connect(self, retry_attempts: int = 5, retry_delay: float = 2.0) -> None:
        """Establish connection with exponential backoff and port file monitoring"""
        port_file_notified = False

        for attempt in range(retry_attempts):
            try:
                ports = await self._read_ports()
                if not ports:
                    if not port_file_notified:
                        logger.info("Waiting for Lightroom plugin to start...")
                        logger.info(f"Port file not found at {self.port_file}")
                        logger.info("Please ensure:")
                        logger.info("  1. Lightroom Classic is running")
                        logger.info("  2. lightroom-python-bridge.lrdevplugin is installed and active")
                        logger.info("  3. Plugin has started successfully")
                        port_file_notified = True

                    # Wait for port file to appear with polling
                    await self._wait_for_port_file(timeout=retry_delay * (2**attempt))
                    ports = await self._read_ports()

                    if not ports:
                        from .exceptions import ConnectionError as LRConnectionError

                        raise LRConnectionError("Port file still not available")

                sender_port, receiver_port = ports
                logger.info(f"Found Lightroom bridge ports: {sender_port}, {receiver_port}")

                # Connect to Lightroom's receiver (where we send)
                _, self._send_writer = await asyncio.open_connection(self.host, receiver_port)

                # Connect to Lightroom's sender (where we receive)
                (
                    self._receive_reader,
                    self._receive_writer,
                ) = await asyncio.open_connection(self.host, sender_port)

                self._connected = True
                self._receive_task = asyncio.create_task(self._receive_loop())
                logger.info("✅ Connected to Lightroom bridge successfully!")
                return

            except Exception as e:
                # 部分的に開いたソケットをクリーンアップ
                for writer in [self._send_writer, self._receive_writer]:
                    if writer:
                        writer.close()
                self._send_writer = None
                self._receive_reader = None
                self._receive_writer = None
                logger.warning(f"Connection attempt {attempt + 1}/{retry_attempts} failed: {e}")
                if attempt < retry_attempts - 1:
                    delay = retry_delay * (2**attempt)
                    logger.info(f"Retrying in {delay:.1f} seconds...")
                    await asyncio.sleep(delay)
                else:
                    from .exceptions import ConnectionError as LRConnectionError

                    error_msg = (
                        f"Failed to connect to Lightroom after {retry_attempts} attempts. "
                        f"Please ensure Lightroom Classic is running with the plugin active."
                    )
                    raise LRConnectionError(error_msg)

    async def _wait_for_port_file(self, timeout: float = 10.0, poll_interval: float = 0.5) -> None:
        """Wait for port file to appear with polling"""
        start_time = asyncio.get_event_loop().time()

        while (asyncio.get_event_loop().time() - start_time) < timeout:
            if self.port_file.exists():
                logger.info(f"✅ Port file appeared at {self.port_file}")
                return
            await asyncio.sleep(poll_interval)

        logger.warning(f"Port file did not appear within {timeout:.1f} seconds")

    async def _read_ports(self) -> Optional[Tuple[int, int]]:
        """Read port numbers from Lightroom's port file"""
        if not self.port_file.exists():
            return None

        try:
            content = self.port_file.read_text().strip()
            ports = content.split(",")
            return int(ports[0]), int(ports[1])
        except Exception as e:
            logger.error(f"Failed to read port file: {e}")
            return None

    async def _receive_loop(self) -> None:
        """Background task to receive messages from Lightroom"""
        buffer = b""
        while self._connected:
            try:
                chunk = await self._receive_reader.read(8192)
                if not chunk:
                    logger.warning("Connection closed by Lightroom")
                    break

                buffer += chunk

                # Process complete messages
                while b"\n" in buffer:
                    line, buffer = buffer.split(b"\n", 1)
                    try:
                        message = json.loads(line.decode("utf-8"))
                        await self._handle_message(message)
                    except json.JSONDecodeError as e:
                        logger.error(f"Invalid JSON received: {e}")

            except Exception as e:
                logger.error(f"Receive loop error: {e}")
                break

        self._connected = False

    async def _handle_message(self, message: Dict[str, Any]) -> None:
        """Route received messages to appropriate handlers"""
        # Handle NDJSON streaming events (have "type" and "requestId" fields)
        if "type" in message and "requestId" in message:
            await self._handle_stream_event(message)
            return

        # Handle events
        if "event" in message:
            event_name = message["event"]
            logger.debug(f"Event received: {event_name}")
            for handler in self._event_handlers.get(event_name, []):
                try:
                    handler(message.get("data", {}))
                except Exception as e:
                    logger.error(f"Event handler error for {event_name}: {e}")
            return

        # Handle responses
        request_id = message.get("id")
        if request_id and request_id in self._pending_requests:
            future = self._pending_requests.pop(request_id)
            if not future.cancelled():
                future.set_result(message)

    async def _handle_stream_event(self, message: Dict[str, Any]) -> None:
        """Handle NDJSON streaming event"""
        request_id = message["requestId"]
        event_type = message["type"]
        payload = message.get("payload", {})

        stream = self._pending_streams.get(request_id)
        if not stream:
            logger.warning(f"Stream event for unknown request: {request_id}")
            return

        if event_type == "data":
            stream.chunks.append(payload)
        elif event_type == "progress":
            if stream.progress_callback:
                try:
                    stream.progress_callback(payload)
                except Exception as e:
                    logger.error(f"Progress callback error: {e}")
        elif event_type == "error":
            stream.errors.append(payload)
        elif event_type == "final":
            stream.final = payload
            # Resolve the future with aggregated result
            if not stream.future.cancelled():
                result = self._aggregate_stream(stream)
                stream.future.set_result(result)
        else:
            logger.warning(f"Unknown stream event type: {event_type}")

    def _aggregate_stream(self, stream: StreamAggregator) -> Dict[str, Any]:
        """Aggregate streaming chunks into a single response"""
        # Merge all data chunks
        all_photos: list = []
        for chunk in stream.chunks:
            if "photos" in chunk:
                all_photos.extend(chunk["photos"])

        result: Dict[str, Any] = {
            **(stream.final or {}),
            "photos": all_photos,
            "returned": len(all_photos),
        }

        if stream.errors:
            result["streamErrors"] = stream.errors

        return {"id": "stream", "success": True, "result": result}

    async def send_command(
        self,
        command: str,
        params: Optional[Dict[str, Any]] = None,
        timeout: float = 30.0,
        stream: bool = False,
        progress_callback: Optional[Callable] = None,
    ) -> Dict[str, Any]:
        """Send command and await response.

        If stream=True, registers a StreamAggregator so that NDJSON streaming
        events are collected and aggregated into the final response.
        """
        if not self._connected:
            from .exceptions import ConnectionError as LRConnectionError

            raise LRConnectionError("Not connected to Lightroom")

        request_id = str(uuid.uuid4())
        request_params = dict(params or {})
        if stream:
            request_params["_stream"] = True
        request = {"id": request_id, "command": command, "params": request_params}

        if stream:
            # Set up streaming aggregator
            aggregator = StreamAggregator()
            aggregator.progress_callback = progress_callback
            self._pending_streams[request_id] = aggregator
            wait_future = aggregator.future
        else:
            # Normal single-response path
            future = asyncio.Future()
            self._pending_requests[request_id] = future
            wait_future = future

        try:
            # Send request
            request_json = json.dumps(request) + "\n"
            self._send_writer.write(request_json.encode("utf-8"))
            await self._send_writer.drain()

            # Wait for response
            response = await asyncio.wait_for(wait_future, timeout=timeout)
            return response

        except asyncio.TimeoutError:
            self._pending_requests.pop(request_id, None)
            self._pending_streams.pop(request_id, None)
            from .exceptions import TimeoutError as LRTimeoutError

            raise LRTimeoutError(f"Command '{command}' timed out after {timeout}s")
        except Exception:
            self._pending_requests.pop(request_id, None)
            self._pending_streams.pop(request_id, None)
            raise

    async def disconnect(self) -> None:
        """Close connections gracefully"""
        self._connected = False

        if self._receive_task:
            self._receive_task.cancel()
            try:
                await self._receive_task
            except asyncio.CancelledError:
                pass

        for writer in [self._send_writer, self._receive_writer]:
            if writer:
                writer.close()
                await writer.wait_closed()

        logger.info("Disconnected from Lightroom bridge")
