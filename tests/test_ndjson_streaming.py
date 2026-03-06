"""NDJSON ストリーミング受信・集約のテスト"""

import asyncio

import pytest

from lightroom_sdk.socket_bridge import SocketBridge, StreamAggregator


def _make_bridge():
    """テスト用の最小限 SocketBridge を作成"""
    bridge = SocketBridge.__new__(SocketBridge)
    bridge._pending_streams = {}
    bridge._pending_requests = {}
    bridge._event_handlers = {}
    bridge._connected = True
    return bridge


@pytest.mark.asyncio
async def test_stream_aggregator_initial_state():
    """StreamAggregator の初期状態"""
    agg = StreamAggregator()
    assert agg.chunks == []
    assert agg.errors == []
    assert agg.final is None
    assert not agg.future.done()


@pytest.mark.asyncio
async def test_ndjson_data_events_aggregated():
    """複数の data イベントが集約されて単一レスポンスになること"""
    bridge = _make_bridge()
    agg = StreamAggregator()
    bridge._pending_streams["req-1"] = agg

    await bridge._handle_stream_event({
        "requestId": "req-1", "type": "data",
        "payload": {"photos": [{"id": 1}, {"id": 2}]}
    })
    await bridge._handle_stream_event({
        "requestId": "req-1", "type": "data",
        "payload": {"photos": [{"id": 3}]}
    })

    assert len(agg.chunks) == 2
    assert not agg.future.done()

    await bridge._handle_stream_event({
        "requestId": "req-1", "type": "final",
        "payload": {"total": 3}
    })

    assert agg.future.done()
    result = agg.future.result()
    assert result["success"] is True
    assert len(result["result"]["photos"]) == 3
    assert result["result"]["total"] == 3


@pytest.mark.asyncio
async def test_ndjson_progress_events_received():
    """progress イベントがコールバックで受信されること"""
    bridge = _make_bridge()
    progress_reports = []
    agg = StreamAggregator()
    agg.progress_callback = lambda p: progress_reports.append(p)
    bridge._pending_streams["req-2"] = agg

    await bridge._handle_stream_event({
        "requestId": "req-2", "type": "progress",
        "payload": {"processed": 50, "total": 200}
    })
    await bridge._handle_stream_event({
        "requestId": "req-2", "type": "progress",
        "payload": {"processed": 100, "total": 200}
    })

    assert len(progress_reports) == 2
    assert progress_reports[0]["processed"] == 50
    assert progress_reports[1]["processed"] == 100


@pytest.mark.asyncio
async def test_ndjson_final_event_triggers_response():
    """final イベント受信後にレスポンスが返ること"""
    bridge = _make_bridge()
    agg = StreamAggregator()
    bridge._pending_streams["req-3"] = agg

    await bridge._handle_stream_event({
        "requestId": "req-3", "type": "final",
        "payload": {"total": 0, "complete": True}
    })

    assert agg.future.done()
    result = agg.future.result()
    assert result["success"] is True
    assert result["result"]["complete"] is True


@pytest.mark.asyncio
async def test_ndjson_error_event_recorded():
    """error イベントが記録され、final 後にレスポンスに含まれること"""
    bridge = _make_bridge()
    agg = StreamAggregator()
    bridge._pending_streams["req-4"] = agg

    await bridge._handle_stream_event({
        "requestId": "req-4", "type": "data",
        "payload": {"photos": [{"id": 1}]}
    })
    await bridge._handle_stream_event({
        "requestId": "req-4", "type": "error",
        "payload": {"chunk": "51-100", "error": "read access failed"}
    })
    await bridge._handle_stream_event({
        "requestId": "req-4", "type": "final",
        "payload": {"total": 1, "incomplete": True}
    })

    result = agg.future.result()
    assert result["result"]["incomplete"] is True
    assert len(result["result"]["streamErrors"]) == 1
    assert result["result"]["streamErrors"][0]["chunk"] == "51-100"


@pytest.mark.asyncio
async def test_ndjson_request_id_filtering():
    """異なる requestId のイベントが混在しても正しくフィルタリングされること"""
    bridge = _make_bridge()
    agg1 = StreamAggregator()
    agg2 = StreamAggregator()
    bridge._pending_streams["req-a"] = agg1
    bridge._pending_streams["req-b"] = agg2

    await bridge._handle_stream_event({
        "requestId": "req-a", "type": "data",
        "payload": {"photos": [{"id": 1}]}
    })
    await bridge._handle_stream_event({
        "requestId": "req-b", "type": "data",
        "payload": {"photos": [{"id": 10}, {"id": 11}]}
    })
    await bridge._handle_stream_event({
        "requestId": "req-a", "type": "final",
        "payload": {"total": 1}
    })
    await bridge._handle_stream_event({
        "requestId": "req-b", "type": "final",
        "payload": {"total": 2}
    })

    result_a = agg1.future.result()
    result_b = agg2.future.result()

    assert len(result_a["result"]["photos"]) == 1
    assert len(result_b["result"]["photos"]) == 2
    assert result_a["result"]["total"] == 1
    assert result_b["result"]["total"] == 2
