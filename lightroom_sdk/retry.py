def calculate_batch_timeout(photo_count: int) -> float:
    """枚数に応じた動的タイムアウトを計算"""
    BASE_TIMEOUT = 10.0
    PER_PHOTO_TIMEOUT = 2.0
    MIN_TIMEOUT = 30.0
    MAX_TIMEOUT = 120.0
    return min(MAX_TIMEOUT, max(MIN_TIMEOUT, BASE_TIMEOUT + PER_PHOTO_TIMEOUT * photo_count))
