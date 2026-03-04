import asyncio
import json
from pathlib import Path
from typing import Dict, Any, Optional


class MockLightroomServer:
    """デュアルTCPソケットのLightroomプラグインモック"""

    def __init__(self, port_file: str = "/tmp/lightroom_ports_test.txt"):
        self.port_file = Path(port_file)
        self._responses: Dict[str, Any] = {}
        self._sender_server: Optional[asyncio.Server] = None  # LR→Python
        self._receiver_server: Optional[asyncio.Server] = None  # Python→LR
        self._sender_writers: list[asyncio.StreamWriter] = []
        self._sender_port = 0
        self._receiver_port = 0

    def register_response(self, command: str, result: Any) -> None:
        self._responses[command] = result

    async def _handle_receiver(self, reader, writer):
        """Python→LRチャネル: コマンド受信→レスポンス送信（sender経由）"""
        buffer = b""
        while True:
            chunk = await reader.read(8192)
            if not chunk:
                break
            buffer += chunk
            while b"\n" in buffer:
                line, buffer = buffer.split(b"\n", 1)
                msg = json.loads(line)
                result = self._responses.get(msg["command"], {})
                resp = {"id": msg["id"], "success": True, "result": result}
                for w in self._sender_writers:
                    w.write(json.dumps(resp).encode() + b"\n")
                    await w.drain()

    async def _handle_sender(self, reader, writer):
        """LR→Pythonチャネル: senderクライアント登録"""
        self._sender_writers.append(writer)
        try:
            await reader.read()  # 接続維持
        finally:
            self._sender_writers.remove(writer)

    async def send_event(self, event_name: str, data: Dict[str, Any]) -> None:
        event = {"event": event_name, "data": data}
        payload = json.dumps(event).encode() + b"\n"
        for w in self._sender_writers:
            w.write(payload)
            await w.drain()

    async def start(self) -> None:
        self._sender_server = await asyncio.start_server(
            self._handle_sender, "localhost", 0
        )
        self._receiver_server = await asyncio.start_server(
            self._handle_receiver, "localhost", 0
        )
        self._sender_port = self._sender_server.sockets[0].getsockname()[1]
        self._receiver_port = self._receiver_server.sockets[0].getsockname()[1]
        self.port_file.write_text(f"{self._sender_port},{self._receiver_port}")

    async def stop(self) -> None:
        # 既存接続をクローズ
        for w in list(self._sender_writers):
            w.close()
        self._sender_writers.clear()
        for s in [self._sender_server, self._receiver_server]:
            if s:
                s.close()
                await s.wait_closed()
        if self.port_file.exists():
            self.port_file.unlink()
