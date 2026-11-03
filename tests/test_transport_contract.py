"""Transport contract of SocketBridge and the MCP ConnectionManager (codex-overall #12 #13 #14 #16).

The Lightroom side is a real pair of TCP servers whose answer to each request is scripted per test,
so EOF, broken bytes and plain responses to streaming requests travel over actual sockets.
"""

import asyncio
import json
import math
import time

import pytest

from lightroom_sdk.exceptions import ConnectionError as LRConnectionError
from lightroom_sdk.exceptions import TimeoutError as LRTimeoutError
from lightroom_sdk.socket_bridge import SocketBridge


class ScriptedLightroom:
    """Dual-socket server; `on_request(request) -> list[bytes] | "close" | None` decides the reply"""

    def __init__(self, port_file):
        self.port_file = port_file
        self.on_request = lambda request: [_ok(request)]
        self._senders: list[asyncio.StreamWriter] = []
        self._servers: list[asyncio.Server] = []
        self.sender_connected = asyncio.Event()

    async def start(self):
        receiver = await asyncio.start_server(self._handle_receiver, "localhost", 0)
        sender = await asyncio.start_server(self._handle_sender, "localhost", 0)
        self._servers = [receiver, sender]
        receiver_port = receiver.sockets[0].getsockname()[1]
        sender_port = sender.sockets[0].getsockname()[1]
        self.port_file.write_text(f"{sender_port},{receiver_port}")

    def close_senders(self):
        """Lightroom closes its side of the receive channel (what the client reads from)"""
        for writer in self._senders:
            writer.close()

    async def stop(self):
        for writer in self._senders:
            writer.close()
        for server in self._servers:
            server.close()
            await server.wait_closed()

    async def _handle_sender(self, reader, writer):
        self._senders.append(writer)
        self.sender_connected.set()
        try:
            await reader.read()
        except ConnectionError:
            pass
        finally:
            writer.close()  # Server.wait_closed() waits for every accepted connection to close

    async def _handle_receiver(self, reader, writer):
        try:
            async for line in reader:
                reply = self.on_request(json.loads(line))
                await self.sender_connected.wait()
                if reply == "close":
                    for sender in self._senders:
                        sender.close()
                    continue
                for chunk in reply or []:
                    for sender in self._senders:
                        sender.write(chunk)
                        await sender.drain()
        except ConnectionError:
            pass
        finally:
            writer.close()


def _line(obj) -> bytes:
    return json.dumps(obj).encode() + b"\n"


def _ok(request, result=None) -> bytes:
    return _line({"id": request["id"], "success": True, "result": result or {"echo": request["command"]}})


@pytest.fixture
async def lightroom(tmp_path):
    server = ScriptedLightroom(tmp_path / "ports.txt")
    await server.start()
    yield server
    await server.stop()


@pytest.fixture
async def bridge(lightroom):
    bridge = SocketBridge(port_file=str(lightroom.port_file))
    await bridge.connect(retry_attempts=1)
    await lightroom.sender_connected.wait()
    yield bridge
    await bridge.disconnect()


def _replace_send_writer(bridge, fake):
    """Swap in a fake send socket; the real one is closed so the server's wait_closed() can finish"""
    bridge._send_writer.close()
    bridge._send_writer = fake


def _assert_nothing_pending(bridge):
    assert bridge._pending_requests == {}
    assert bridge._pending_streams == {}


class TestReceiveLoopEnds:
    async def test_eof_fails_waiting_request_immediately(self, lightroom, bridge):
        lightroom.on_request = lambda request: "close"
        started = time.monotonic()
        with pytest.raises(LRConnectionError, match="lost"):
            await bridge.send_command("catalog.getSelectedPhotos", timeout=10)
        assert time.monotonic() - started < 2, "must not wait for the command timeout"
        _assert_nothing_pending(bridge)
        assert bridge._connected is False

    async def test_eof_fails_waiting_stream(self, lightroom, bridge):
        lightroom.on_request = lambda request: "close"
        with pytest.raises(LRConnectionError):
            await bridge.send_command("catalog.searchPhotos", timeout=10, stream=True)
        _assert_nothing_pending(bridge)

    async def test_eof_closes_the_sockets(self, lightroom, bridge):
        lightroom.on_request = lambda request: "close"
        with pytest.raises(LRConnectionError):
            await bridge.send_command("system.ping", timeout=10)
        assert bridge._send_writer is None and bridge._receive_writer is None

    async def test_send_after_eof_is_reported_as_not_sent(self, lightroom, bridge):
        from lightroom_sdk.exceptions import RequestNotSentError

        lightroom.on_request = lambda request: "close"
        with pytest.raises(LRConnectionError):
            await bridge.send_command("system.ping", timeout=10)
        with pytest.raises(RequestNotSentError):
            await bridge.send_command("system.ping", timeout=10)

    async def test_eof_while_drain_is_blocked_fails_immediately(self, lightroom, bridge):
        _replace_send_writer(bridge, _StuckWriter())
        pending = asyncio.create_task(bridge.send_command("develop.setValue", timeout=10))
        await asyncio.sleep(0.1)
        started = time.monotonic()
        lightroom.close_senders()
        with pytest.raises(LRConnectionError, match="lost"):
            await pending
        assert time.monotonic() - started < 2, "must not wait for the command timeout"
        _assert_nothing_pending(bridge)

    async def test_eof_between_check_and_write_is_not_sent(self, bridge):
        """The receive loop dropped the sockets after send_command() checked the connection"""
        from lightroom_sdk.exceptions import RequestNotSentError

        _replace_send_writer(bridge, None)
        with pytest.raises(RequestNotSentError):
            await bridge.send_command("develop.setValue", timeout=5)
        _assert_nothing_pending(bridge)

    async def test_disconnect_fails_waiting_request(self, lightroom, bridge):
        lightroom.on_request = lambda request: None  # never answers
        pending = asyncio.create_task(bridge.send_command("system.ping", timeout=10))
        await asyncio.sleep(0.1)
        await bridge.disconnect()
        with pytest.raises(LRConnectionError):
            await pending
        _assert_nothing_pending(bridge)


class TestBadLinesDoNotStopTheLoop:
    @pytest.mark.parametrize(
        "bad",
        [
            b"\xff\xfe not utf-8\n",
            b"{not json\n",
            b"[1, 2, 3]\n",
            b'"just a string"\n',
            b"\n",
            b"\r\n",
        ],
        ids=["invalid-utf8", "invalid-json", "array", "string", "empty", "crlf"],
    )
    async def test_response_after_bad_line_is_delivered(self, lightroom, bridge, bad):
        lightroom.on_request = lambda request: [bad, _ok(request)]
        response = await bridge.send_command("system.ping", timeout=5)
        assert response["result"] == {"echo": "system.ping"}
        assert bridge._connected is True

    async def test_handler_exception_does_not_stop_the_loop(self, lightroom, bridge):
        def boom(data):
            raise RuntimeError("handler bug")

        bridge.on_event("photo.selected", boom)
        lightroom.on_request = lambda request: [_line({"event": "photo.selected", "data": {}}), _ok(request)]
        response = await bridge.send_command("system.ping", timeout=5)
        assert response["success"] is True

    async def test_message_with_unhashable_id_is_skipped(self, lightroom, bridge):
        lightroom.on_request = lambda request: [_line({"id": ["x"], "success": True}), _ok(request)]
        response = await bridge.send_command("system.ping", timeout=5)
        assert response["success"] is True


class TestStreamingRequestGetsPlainResponse:
    async def test_plain_success_completes_the_stream(self, lightroom, bridge):
        lightroom.on_request = lambda request: [_ok(request, {"photos": [], "total": 0})]
        response = await bridge.send_command("catalog.searchPhotos", timeout=5, stream=True)
        assert response["success"] is True
        assert response["result"] == {"photos": [], "total": 0}
        _assert_nothing_pending(bridge)

    async def test_plain_error_completes_the_stream(self, lightroom, bridge):
        error = {"code": "INVALID_PARAM", "message": "bad query"}
        lightroom.on_request = lambda request: [_line({"id": request["id"], "success": False, "error": error})]
        response = await bridge.send_command("catalog.searchPhotos", timeout=5, stream=True)
        assert response["success"] is False
        assert response["error"] == error

    async def test_ndjson_stream_still_aggregates(self, lightroom, bridge):
        def reply(request):
            rid = request["id"]
            return [
                _line({"requestId": rid, "type": "data", "payload": {"photos": [{"id": 1}]}}),
                _line({"requestId": rid, "type": "data", "payload": {"photos": [{"id": 2}]}}),
                _line({"requestId": rid, "type": "final", "payload": {"total": 2}}),
            ]

        lightroom.on_request = reply
        response = await bridge.send_command("catalog.searchPhotos", timeout=5, stream=True)
        assert response["result"]["photos"] == [{"id": 1}, {"id": 2}]
        assert response["result"]["total"] == 2


class _StuckWriter:
    """A send socket whose peer stopped reading: drain() never returns"""

    def __init__(self):
        self.written = []

    def write(self, data):
        self.written.append(data)

    async def drain(self):
        await asyncio.Event().wait()

    def close(self):
        pass

    async def wait_closed(self):
        pass


class TestTimeoutCoversTheRoundTrip:
    async def test_stuck_drain_times_out(self, bridge):
        _replace_send_writer(bridge, _StuckWriter())
        started = time.monotonic()
        with pytest.raises(LRTimeoutError):
            await bridge.send_command("system.ping", timeout=0.2)
        assert time.monotonic() - started < 1
        _assert_nothing_pending(bridge)

    async def test_no_answer_times_out_and_forgets_request(self, lightroom, bridge):
        lightroom.on_request = lambda request: None
        with pytest.raises(LRTimeoutError):
            await bridge.send_command("system.ping", timeout=0.2)
        _assert_nothing_pending(bridge)

    async def test_late_answer_after_timeout_is_ignored(self, lightroom, bridge):
        delayed = []
        lightroom.on_request = lambda request: delayed.append(request) or None
        with pytest.raises(LRTimeoutError):
            await bridge.send_command("system.ping", timeout=0.2)
        # The answer to the abandoned request arrives late, then a fresh request works
        lightroom.on_request = lambda request: [_ok(delayed[0]), _ok(request)]
        response = await bridge.send_command("system.status", timeout=5)
        assert response["result"] == {"echo": "system.status"}

    async def test_cancelled_request_is_forgotten(self, lightroom, bridge):
        lightroom.on_request = lambda request: None
        task = asyncio.create_task(bridge.send_command("system.ping", timeout=10, stream=True))
        await asyncio.sleep(0.1)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        _assert_nothing_pending(bridge)

    async def test_send_socket_error_is_a_connection_error(self, bridge):
        class BrokenWriter(_StuckWriter):
            async def drain(self):
                raise TimeoutError(60, "Operation timed out")  # ETIMEDOUT, an OSError

        _replace_send_writer(bridge, BrokenWriter())
        with pytest.raises(LRConnectionError):
            await bridge.send_command("system.ping", timeout=5)

    @pytest.mark.parametrize("timeout", [0, -1, math.nan, math.inf, None, True, "5"])
    async def test_timeout_must_be_positive_and_finite(self, bridge, timeout):
        with pytest.raises(ValueError, match="timeout"):
            await bridge.send_command("system.ping", timeout=timeout)
        _assert_nothing_pending(bridge)

    async def test_disconnect_does_not_hang_on_wait_closed(self, bridge):
        class NeverClosed(_StuckWriter):
            async def wait_closed(self):
                await asyncio.Event().wait()

        _replace_send_writer(bridge, NeverClosed())
        started = time.monotonic()
        await bridge.disconnect()
        assert time.monotonic() - started < 5


class TestMcpConnectionManager:
    async def test_timeout_is_classified_as_timeout_and_keeps_client(self, lightroom):
        from mcp_server.connection import ConnectionManager

        lightroom.on_request = lambda request: None if request["command"] == "system.status" else [_ok(request)]
        manager = ConnectionManager(port_file=str(lightroom.port_file))
        try:
            result = await manager.execute("system.status", {}, timeout=0.3, mutating=False)
            assert result["code"] == "TIMEOUT_ERROR"
            client = manager._client
            assert client is not None
            assert manager._reconnected is False
            # The same connection still works and nothing from the timed-out request is left behind
            assert (await manager.execute("system.ping", {}, timeout=5, mutating=False)) == {
                "result": {"echo": "system.ping"}
            }
            assert manager._client is client
            _assert_nothing_pending(client._bridge._bridge)
        finally:
            await manager.shutdown()

    async def test_dropped_client_is_disconnected(self, lightroom):
        from mcp_server.connection import ConnectionManager

        manager = ConnectionManager(port_file=str(lightroom.port_file))
        try:
            await manager.execute("system.ping", {}, timeout=5, mutating=False)
            old_bridge = manager._client._bridge._bridge
            lightroom.on_request = lambda request: "close"
            result = await manager.execute("develop.setValue", {"param": "Exposure", "value": 0.5}, 5, True)
            assert result["code"] == "RESULT_UNKNOWN"
            assert manager._client is None
            assert old_bridge._connected is False
            assert old_bridge._send_writer is None
        finally:
            await manager.shutdown()

    async def test_connect_cut_by_timeout_leaves_no_client(self, tmp_path):
        from mcp_server.connection import ConnectionManager

        manager = ConnectionManager(port_file=str(tmp_path / "missing-ports.txt"))
        result = await manager.execute("system.ping", {}, timeout=0.3, mutating=False)
        assert result["code"] == "TIMEOUT_ERROR"
        assert manager._client is None
