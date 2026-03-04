import asyncio
from typing import Optional, Dict, Any
from contextlib import asynccontextmanager
import logging

from .socket_bridge import SocketBridge
from .protocol import LightroomResponse
from .exceptions import LightroomSDKError, ERROR_CODE_MAP

logger = logging.getLogger(__name__)

class LightroomClient:
    """Main client for interacting with Lightroom"""

    def __init__(self, host: str = 'localhost'):
        self.host = host
        self._bridge = SocketBridge(host)

    async def connect(self, retry_attempts: int = 5) -> None:
        """Connect to Lightroom bridge"""
        logger.debug(f"[LR_CLIENT:{id(self)}] connect() called")
        await self._bridge.connect(retry_attempts=retry_attempts)
        logger.debug(f"[LR_CLIENT:{id(self)}] connect() completed")

    async def disconnect(self) -> None:
        """Disconnect from Lightroom bridge"""
        await self._bridge.disconnect()

    async def __aenter__(self):
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.disconnect()

    async def execute_command(
        self,
        command: str,
        params: Optional[Dict[str, Any]] = None,
        timeout: float = 30.0
    ) -> Dict[str, Any]:
        """Execute a command and handle response"""
        response = await self._bridge.send_command(command, params, timeout)

        # Parse response
        lr_response = LightroomResponse(**response)

        if not lr_response.success:
            error = lr_response.error or {}
            error_code = error.get('code', 'UNKNOWN')
            error_message = error.get('message', 'Unknown error')

            # Map to specific exception type
            exception_class = ERROR_CODE_MAP.get(error_code, LightroomSDKError)
            raise exception_class(error_message, code=error_code, details=error)

        return lr_response.result or {}

    # Convenience methods for common operations
    async def ping(self) -> Dict[str, Any]:
        """Test connection to Lightroom"""
        return await self.execute_command("system.ping")

    async def get_status(self) -> Dict[str, Any]:
        """Get bridge status"""
        return await self.execute_command("system.status")

    async def wait_for_lightroom(self, timeout: float = 60.0) -> bool:
        """
        Wait for Lightroom to become available with helpful progress messages

        Args:
            timeout: Maximum time to wait in seconds

        Returns:
            True if Lightroom becomes available, False if timeout
        """
        logger.info("Checking for Lightroom Classic...")

        try:
            await asyncio.wait_for(self.connect(), timeout=timeout)
            logger.info("Lightroom is ready!")
            return True
        except asyncio.TimeoutError:
            logger.warning(f"Lightroom not available within {timeout}s")
            return False
        except Exception as e:
            logger.warning(f"Lightroom not ready: {e}")
            return False