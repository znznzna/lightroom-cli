import asyncio
import logging
from typing import Any, Dict, Optional

from .exceptions import ERROR_CODE_MAP, LightroomSDKError
from .protocol import LightroomResponse
from .socket_bridge import SocketBridge

logger = logging.getLogger(__name__)


class LightroomClient:
    """Main client for interacting with Lightroom"""

    def __init__(self, host: str = "localhost"):
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
        timeout: float = 30.0,
    ) -> Dict[str, Any]:
        """Execute a command and handle response"""
        response = await self._bridge.send_command(command, params, timeout)

        # Parse response
        lr_response = LightroomResponse(**response)

        if not lr_response.success:
            error = lr_response.error or {}
            error_code = error.get("code", "UNKNOWN")
            error_message = error.get("message", "Unknown error")

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

    async def create_ai_mask(
        self,
        selection_type: str,
        part: Optional[str] = None,
        adjustments: Optional[Dict[str, float]] = None,
        timeout: float = 60.0,
    ) -> Dict[str, Any]:
        """Create an AI mask and optionally apply adjustments.

        Args:
            selection_type: One of subject, sky, background, objects, people, landscape
            part: Optional body/landscape part for people/landscape types
            adjustments: Optional dict of develop parameter adjustments
            timeout: Command timeout in seconds
        """
        params: Dict[str, Any] = {"selectionType": selection_type}
        if part:
            params["part"] = part
        if adjustments:
            params["adjustments"] = adjustments
        return await self.execute_command("develop.createAIMaskWithAdjustments", params, timeout=timeout)

    async def batch_ai_mask(
        self,
        selection_type: str,
        photo_ids: Optional[list[str]] = None,
        all_selected: bool = False,
        part: Optional[str] = None,
        adjustments: Optional[Dict[str, float]] = None,
        continue_on_error: bool = True,
        timeout: float = 300.0,
    ) -> Dict[str, Any]:
        """Apply AI mask to multiple photos.

        Args:
            selection_type: One of subject, sky, background, objects, people, landscape
            photo_ids: List of photo IDs to process
            all_selected: If True, apply to all currently selected photos
            part: Optional body/landscape part
            adjustments: Optional dict of develop parameter adjustments
            continue_on_error: If True, continue processing on individual failures
            timeout: Command timeout in seconds
        """
        params: Dict[str, Any] = {
            "selectionType": selection_type,
            "allSelected": all_selected,
            "continueOnError": continue_on_error,
        }
        if photo_ids:
            params["photoIds"] = photo_ids
        if part:
            params["part"] = part
        if adjustments:
            params["adjustments"] = adjustments
        return await self.execute_command("develop.batchAIMask", params, timeout=timeout)
