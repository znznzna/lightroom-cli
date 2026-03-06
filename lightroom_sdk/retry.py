import fnmatch
from dataclasses import dataclass, field

COMMAND_TIMEOUTS: dict[str, float] = {
    "system.ping": 5.0,
    "system.status": 5.0,
    "system.reconnect": 10.0,
    "preview.*": 120.0,
    "develop.set_parameter": 10.0,
    "develop.set_parameters": 15.0,
    "develop.get_current_settings": 10.0,
    "catalog.search_photos": 60.0,
    "catalog.findPhotos": 90.0,
    "catalog.get_all_photos": 60.0,
    "catalog.getAllPhotos": 90.0,
    "catalog.getCollections": 60.0,
    "catalog.getCollectionPhotos": 60.0,
    # AI Mask commands
    "develop.createAIMaskWithAdjustments": 60.0,
    "develop.batchAIMask": 300.0,
    "develop.probeAIPartSupport": 30.0,
    # Batch develop commands (fallback fixed values; use calculate_batch_timeout for dynamic)
    "develop.batchApplySettings": 120.0,
    "develop.batchSetValue": 120.0,
}

DEFAULT_TIMEOUT = 30.0


def calculate_batch_timeout(photo_count: int) -> float:
    """枚数に応じた動的タイムアウトを計算"""
    BASE_TIMEOUT = 10.0
    PER_PHOTO_TIMEOUT = 2.0
    MIN_TIMEOUT = 30.0
    MAX_TIMEOUT = 120.0
    return min(MAX_TIMEOUT, max(MIN_TIMEOUT, BASE_TIMEOUT + PER_PHOTO_TIMEOUT * photo_count))


def get_timeout(command: str) -> float:
    """コマンド名に対応するタイムアウト値を返す（ワイルドカード対応）"""
    if command in COMMAND_TIMEOUTS:
        return COMMAND_TIMEOUTS[command]
    for pattern, timeout in COMMAND_TIMEOUTS.items():
        if fnmatch.fnmatch(command, pattern):
            return timeout
    return DEFAULT_TIMEOUT


@dataclass
class RetryConfig:
    max_retries: int = 3
    initial_delay: float = 1.0
    backoff_factor: float = 2.0
    max_delay: float = 30.0
    retryable_exceptions: tuple = field(default_factory=lambda: (ConnectionError, TimeoutError))
