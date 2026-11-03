import asyncio
import json
import logging
import math
import uuid
from asyncio import StreamReader, StreamWriter
from pathlib import Path
from typing import Any, Callable, Dict, Optional, Tuple

logger = logging.getLogger(__name__)

# Upper bounds for the parts of a round trip that are not covered by a command's own timeout
CONNECT_TIMEOUT = 5.0
CLOSE_TIMEOUT = 2.0


def _check_timeout(timeout: Any) -> None:
    if isinstance(timeout, bool) or not isinstance(timeout, (int, float)) or not math.isfinite(timeout) or timeout <= 0:
        raise ValueError(f"timeout must be a positive finite number of seconds, got {timeout!r}")


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
                _, self._send_writer = await asyncio.wait_for(
                    asyncio.open_connection(self.host, receiver_port), timeout=CONNECT_TIMEOUT
                )

                # Connect to Lightroom's sender (where we receive)
                (
                    self._receive_reader,
                    self._receive_writer,
                ) = await asyncio.wait_for(asyncio.open_connection(self.host, sender_port), timeout=CONNECT_TIMEOUT)

                self._connected = True
                self._receive_task = asyncio.create_task(self._receive_loop())
                logger.info("✅ Connected to Lightroom bridge successfully!")
                return

            except asyncio.CancelledError:
                self._abort_writers()
                raise
            except Exception as e:
                # 部分的に開いたソケットをクリーンアップ
                self._abort_writers()
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

    def _abort_writers(self) -> None:
        """Drop both sockets at once, discarding unsent data (the connection is being abandoned).

        close() would keep the socket open until its send buffer drains, which never happens
        when Lightroom has stopped reading.
        """
        for writer in [self._send_writer, self._receive_writer]:
            if writer:
                writer.transport.abort()
        self._send_writer = None
        self._receive_reader = None
        self._receive_writer = None

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
        """Background task to receive messages from Lightroom.

        However the loop ends (EOF, read error, disconnect), every request still waiting for an
        answer fails right away with a connection error instead of sitting until its timeout.
        """
        buffer = b""
        reason = "connection closed by Lightroom"
        try:
            while self._connected:
                chunk = await self._receive_reader.read(8192)
                if not chunk:
                    logger.warning("Connection closed by Lightroom")
                    break

                buffer += chunk

                # Process complete messages
                while b"\n" in buffer:
                    line, buffer = buffer.split(b"\n", 1)
                    await self._dispatch_line(line)
        except asyncio.CancelledError:
            reason = "disconnected"
            raise
        except Exception as e:
            reason = f"receive error: {e}"
            logger.error(f"Receive loop error: {e}")
        finally:
            self._connected = False
            self._fail_pending(reason)
            if reason != "disconnected":
                # disconnect() closes the sockets itself; here nobody else will
                self._abort_writers()

    async def _dispatch_line(self, line: bytes) -> None:
        """Decode and route one NDJSON line. A bad line is logged and skipped, never fatal."""
        if not line.strip():
            return
        try:
            message = json.loads(line.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as e:
            logger.error(f"Undecodable message from Lightroom ({len(line)} bytes), skipped: {e}")
            return
        if not isinstance(message, dict):
            logger.error(f"Message from Lightroom is not a JSON object, skipped: {type(message).__name__}")
            return
        try:
            await self._handle_message(message)
        except Exception:
            logger.exception("Failed to handle message from Lightroom")

    def _fail_pending(self, reason: str) -> None:
        """Fail every request and stream still waiting for an answer"""
        from .exceptions import ConnectionError as LRConnectionError

        requests, self._pending_requests = self._pending_requests, {}
        streams, self._pending_streams = self._pending_streams, {}
        futures = [*requests.values(), *(stream.future for stream in streams.values())]
        for future in futures:
            if not future.done():
                future.set_exception(LRConnectionError(f"Connection to Lightroom lost ({reason})"))

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

        # Handle responses. A streaming request can also end with a plain response: Lua answers
        # that way for an empty result, a parameter error or a handler error.
        request_id = message.get("id")
        if request_id in self._pending_requests:
            future = self._pending_requests.pop(request_id)
        elif request_id in self._pending_streams:
            future = self._pending_streams.pop(request_id).future
        else:
            return
        if not future.done():
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
            if not stream.future.done():
                result = self._aggregate_stream(stream)
                stream.future.set_result(result)
            # Cleanup completed stream
            self._pending_streams.pop(request_id, None)
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

        `timeout` covers the whole round trip: writing the request, draining it and the answer.
        """
        _check_timeout(timeout)
        if not self._connected:
            from .exceptions import RequestNotSentError

            raise RequestNotSentError("Not connected to Lightroom")

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
            return await asyncio.wait_for(self._write_and_wait(request, wait_future), timeout=timeout)
        except asyncio.TimeoutError:
            from .exceptions import TimeoutError as LRTimeoutError

            raise LRTimeoutError(f"Command '{command}' timed out after {timeout}s") from None
        finally:
            # Also runs on cancellation, so an abandoned request never stays registered
            self._pending_requests.pop(request_id, None)
            self._pending_streams.pop(request_id, None)
            if wait_future.done() and not wait_future.cancelled():
                wait_future.exception()  # failed by _fail_pending while nobody awaited it: mark as seen

    async def _write_and_wait(self, request: Dict[str, Any], wait_future: asyncio.Future) -> Dict[str, Any]:
        from .exceptions import ConnectionError as LRConnectionError
        from .exceptions import RequestNotSentError

        # Checked again here: on Python 3.10 wait_for() runs this as a separate task, so the
        # receive loop may have seen EOF and dropped the sockets since send_command() checked.
        writer = self._send_writer
        if not self._connected or writer is None:
            raise RequestNotSentError(f"Connection to Lightroom closed before '{request['command']}' was sent")

        try:
            writer.write((json.dumps(request) + "\n").encode("utf-8"))
        except OSError as e:
            raise LRConnectionError(f"Failed to send '{request['command']}' to Lightroom: {e}") from e

        # Wait for the drain and the answer together: if the receive side closes while the send
        # buffer is still full, the request fails right away instead of waiting for the timeout.
        drain = asyncio.ensure_future(writer.drain())
        try:
            await asyncio.wait({drain, wait_future}, return_when=asyncio.FIRST_COMPLETED)
        finally:
            if not drain.done():
                drain.cancel()
        if not wait_future.done():
            try:
                drain.result()
            except OSError as e:
                # Wrapped so that a socket-level ETIMEDOUT is not mistaken for the command timeout
                raise LRConnectionError(f"Failed to send '{request['command']}' to Lightroom: {e}") from e
        elif not drain.cancelled() and drain.done():
            drain.exception()  # the answer already decides the outcome; a late drain error is moot
        return await wait_future

    async def disconnect(self) -> None:
        """Close connections gracefully"""
        self._connected = False

        if self._receive_task:
            self._receive_task.cancel()
            try:
                await self._receive_task
            except asyncio.CancelledError:
                pass

        self._fail_pending("disconnected")

        writers = [self._send_writer, self._receive_writer]
        self._send_writer = None
        self._receive_reader = None
        self._receive_writer = None
        for writer in writers:
            if writer:
                writer.close()
                try:
                    await asyncio.wait_for(writer.wait_closed(), timeout=CLOSE_TIMEOUT)
                except (asyncio.TimeoutError, OSError):
                    # close() waits for unsent data to go out; if Lightroom is not reading, force it
                    logger.warning("Socket did not close cleanly, aborting it")
                    writer.transport.abort()

        logger.info("Disconnected from Lightroom bridge")
