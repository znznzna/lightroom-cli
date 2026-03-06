"""incomplete フラグと部分成功レスポンスのテスト"""


def test_incomplete_flag_on_timeout():
    """タイムアウト時のレスポンスに incomplete: true と reason: "timeout" が含まれること"""
    result = {
        "photos": [{"id": 1, "filename": "a.jpg"}],
        "total": 100,
        "returned": 1,
        "offset": 0,
        "limit": 500,
        "processedCount": 1,
        "totalCount": 100,
        "incomplete": True,
        "reason": "timeout",
    }

    assert result["incomplete"] is True
    assert result["reason"] == "timeout"
    assert result["processedCount"] < result["totalCount"]


def test_incomplete_flag_on_chunk_error():
    """チャンクエラー時に incomplete: true と reason: "chunk_errors" が含まれること"""
    result = {
        "photos": [{"id": 1}, {"id": 2}],
        "total": 50,
        "returned": 2,
        "offset": 0,
        "limit": 500,
        "processedCount": 2,
        "totalCount": 50,
        "incomplete": True,
        "reason": "chunk_errors",
        "partialErrors": [
            {"chunk": "51-100", "error": "catalog access failed"}
        ],
    }

    assert result["incomplete"] is True
    assert result["reason"] == "chunk_errors"
    assert len(result["partialErrors"]) > 0


def test_incomplete_flag_with_partial_errors():
    """partialErrors フィールドにスキップされたチャンク情報が含まれること"""
    result = {
        "photos": [{"id": 1}],
        "total": 10,
        "returned": 1,
        "processedCount": 1,
        "totalCount": 10,
        "incomplete": True,
        "reason": "chunk_errors",
        "partialErrors": [
            {"chunk": "51-100", "error": "read access denied"},
            {"chunk": "metadata 1-50", "error": "timeout in metadata"},
        ],
    }

    errors = result["partialErrors"]
    assert len(errors) == 2
    assert "chunk" in errors[0]
    assert "error" in errors[0]


def test_processed_count_and_total_count():
    """processedCount / totalCount が正しいこと"""
    result = {
        "photos": [{"id": i} for i in range(1, 26)],
        "total": 100,
        "returned": 25,
        "offset": 0,
        "limit": 500,
        "processedCount": 25,
        "totalCount": 100,
        "incomplete": True,
        "reason": "timeout",
    }

    assert result["processedCount"] == 25
    assert result["totalCount"] == 100
    assert result["returned"] == len(result["photos"])


def test_complete_response_has_no_incomplete_flag():
    """正常完了時は incomplete フラグがないこと"""
    result = {
        "photos": [{"id": i} for i in range(1, 11)],
        "total": 10,
        "returned": 10,
        "offset": 0,
        "limit": 500,
        "processedCount": 10,
        "totalCount": 10,
    }

    assert "incomplete" not in result
    assert result["processedCount"] == result["totalCount"]


def test_cancelled_response():
    """キャンセル時のレスポンスに reason: "cancelled" が含まれること"""
    result = {
        "photos": [{"id": 1}],
        "total": 50,
        "returned": 1,
        "processedCount": 1,
        "totalCount": 50,
        "incomplete": True,
        "reason": "cancelled",
    }

    assert result["incomplete"] is True
    assert result["reason"] == "cancelled"
