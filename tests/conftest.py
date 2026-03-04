import pytest_asyncio
from tests.mocks.lightroom_mock import MockLightroomServer


@pytest_asyncio.fixture
async def mock_lr_server():
    server = MockLightroomServer()
    await server.start()
    yield server
    await server.stop()
