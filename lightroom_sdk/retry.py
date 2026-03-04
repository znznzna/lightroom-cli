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
    "catalog.get_all_photos": 60.0,
}

DEFAULT_TIMEOUT = 30.0


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
