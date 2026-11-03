from lightroom_sdk.retry import calculate_batch_timeout


def test_calculate_batch_timeout_10_photos():
    assert calculate_batch_timeout(10) == 30.0


def test_calculate_batch_timeout_50_photos():
    assert calculate_batch_timeout(50) == 110.0


def test_calculate_batch_timeout_1_photo():
    assert calculate_batch_timeout(1) == 30.0


def test_calculate_batch_timeout_exceeds_max():
    assert calculate_batch_timeout(100) == 120.0
