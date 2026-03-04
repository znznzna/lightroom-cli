import pytest
from lightroom_sdk.retry import RetryConfig, get_timeout


def test_exact_command_timeout():
    assert get_timeout("system.ping") == 5.0


def test_wildcard_command_timeout():
    assert get_timeout("preview.generate") == 120.0
    assert get_timeout("preview.get_info") == 120.0


def test_default_timeout():
    assert get_timeout("unknown.command") == 30.0


def test_retry_config_defaults():
    cfg = RetryConfig()
    assert cfg.max_retries == 3
    assert cfg.backoff_factor == 2.0
    assert cfg.max_delay == 30.0


def test_retry_config_custom():
    cfg = RetryConfig(max_retries=5, initial_delay=0.5)
    assert cfg.max_retries == 5
    assert cfg.initial_delay == 0.5
