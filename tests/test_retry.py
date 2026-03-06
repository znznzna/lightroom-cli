from lightroom_sdk.retry import COMMAND_TIMEOUTS, RetryConfig, calculate_batch_timeout, get_timeout


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


def test_ai_mask_timeout():
    assert get_timeout("develop.createAIMaskWithAdjustments") == 60.0


def test_batch_ai_mask_timeout():
    assert get_timeout("develop.batchAIMask") == 300.0


def test_probe_ai_part_timeout():
    assert get_timeout("develop.probeAIPartSupport") == 30.0


def test_calculate_batch_timeout_10_photos():
    assert calculate_batch_timeout(10) == 30.0


def test_calculate_batch_timeout_50_photos():
    assert calculate_batch_timeout(50) == 110.0


def test_calculate_batch_timeout_1_photo():
    assert calculate_batch_timeout(1) == 30.0


def test_calculate_batch_timeout_exceeds_max():
    assert calculate_batch_timeout(100) == 120.0


def test_batch_command_timeouts_registered():
    assert "develop.batchApplySettings" in COMMAND_TIMEOUTS
    assert "develop.batchSetValue" in COMMAND_TIMEOUTS
    assert COMMAND_TIMEOUTS["develop.batchApplySettings"] == 120.0
    assert COMMAND_TIMEOUTS["develop.batchSetValue"] == 120.0
