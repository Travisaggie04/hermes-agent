import pytest

from mission_control.jenny_bridge_relay import append_response, pending_requests, relay_packet, relay_status, run_once
from mission_control.records import (
    JennyBridgeMessageRequestRecord,
    JennyBridgeMessageResponseRecord,
    JennyBridgePollerStatusRecord,
    JsonlRecordStore,
)


def test_pending_requests_exclude_answered_bridge_messages(tmp_path):
    path = tmp_path / "records.jsonl"
    store = JsonlRecordStore(path)
    store.append(
        JennyBridgeMessageRequestRecord(
            request_id="bridge-request-1",
            project_id="project-hermes",
            sender="codex",
            target_agent="jenny",
            message="Review whether the bridge can relay messages.",
            status="queued",
        )
    )

    pending = pending_requests(path)
    assert len(pending) == 1
    assert pending[0].record.request_id == "bridge-request-1"
    packet = relay_packet(pending)
    assert "Mission Control Jenny bridge relay packet" in packet
    assert "bridge-request-1" in packet
    assert "python -m mission_control.jenny_bridge_relay respond" in packet

    index, response, status = append_response(
        path=path,
        request_id="bridge-request-1",
        project_id="project-hermes",
        message="Bridge request received; remaining work is a bounded poller lane.",
    )
    assert index == 2
    assert response is not None
    assert response.record_type == "JennyBridgeMessageResponseRecord"
    assert response.metadata["trusted_for_execution"] is False
    assert response.metadata["inert_context_only"] is True
    assert response.metadata["would_execute"] is False
    assert response.metadata["dispatch_enabled"] is False
    assert response.metadata["session_send_enabled"] is False
    assert response.metadata["worker_dispatch_enabled"] is False
    assert response.metadata["send_to_jenny_enabled"] is False
    assert status.status == "response_appended"
    assert status.metadata["trusted_for_execution"] is False
    assert status.metadata["inert_context_only"] is True
    assert status.metadata["would_execute"] is False
    assert status.metadata["worker_dispatch_enabled"] is False
    assert status.metadata["worker_enabled"] is False
    assert status.metadata["timer_enabled"] is False

    assert pending_requests(path) == []
    responses = JsonlRecordStore(path).read_all(JennyBridgeMessageResponseRecord)
    assert len(responses) == 1
    assert responses[0].request_id == "bridge-request-1"
    statuses = JsonlRecordStore(path).read_all(JennyBridgePollerStatusRecord)
    assert len(statuses) == 1
    assert statuses[0].handled_response_id == response.response_id


def test_pending_requests_use_latest_request_status(tmp_path):
    path = tmp_path / "records.jsonl"
    store = JsonlRecordStore(path)
    store.append(
        JennyBridgeMessageRequestRecord(
            request_id="bridge-request-1",
            project_id="project-hermes",
            message="Old queued message.",
            status="queued",
        )
    )
    store.append(
        JennyBridgeMessageRequestRecord(
            request_id="bridge-request-1",
            project_id="project-hermes",
            message="Superseded by newer status.",
            status="cancelled",
        )
    )

    assert pending_requests(path) == []


def test_run_once_appends_started_and_completed_status_without_response(tmp_path):
    path = tmp_path / "records.jsonl"
    JsonlRecordStore(path).append(
        JennyBridgeMessageRequestRecord(
            request_id="bridge-request-1",
            project_id="project-hermes",
            message="Check bridge status.",
            status="queued",
        )
    )

    payload = run_once(path, operator="jenny")

    assert payload["count"] == 1
    assert "bridge-request-1" in payload["relay_packet"]
    store = JsonlRecordStore(path)
    assert len(store.read_all(JennyBridgeMessageResponseRecord)) == 0
    statuses = store.read_all(JennyBridgePollerStatusRecord)
    assert [record.status for record in statuses] == ["poll_started", "poll_completed"]
    assert statuses[-1].pending_count == 1
    assert statuses[-1].operator == "jenny"


def test_append_response_skips_duplicate_without_second_response(tmp_path):
    path = tmp_path / "records.jsonl"
    store = JsonlRecordStore(path)
    store.append(
        JennyBridgeMessageRequestRecord(
            request_id="bridge-request-1",
            project_id="project-hermes",
            message="Check bridge status.",
            status="queued",
        )
    )

    _index, first_response, _status = append_response(
        path=path,
        request_id="bridge-request-1",
        project_id="project-hermes",
        message="First answer.",
    )
    duplicate_index, duplicate_response, duplicate_status = append_response(
        path=path,
        request_id="bridge-request-1",
        project_id="project-hermes",
        message="Second answer.",
    )

    assert first_response is not None
    assert duplicate_response is None
    assert duplicate_status.status == "skipped_duplicate"
    assert duplicate_index == 4
    responses = JsonlRecordStore(path).read_all(JennyBridgeMessageResponseRecord)
    assert len(responses) == 1
    assert responses[0].message == "First answer."


def test_append_response_rejects_missing_or_non_pending_request_with_error_status(tmp_path):
    path = tmp_path / "records.jsonl"
    store = JsonlRecordStore(path)
    store.append(
        JennyBridgeMessageRequestRecord(
            request_id="bridge-request-1",
            project_id="project-hermes",
            message="Cancelled.",
            status="cancelled",
        )
    )

    with pytest.raises(ValueError, match="request status is cancelled"):
        append_response(
            path=path,
            request_id="bridge-request-1",
            project_id="project-hermes",
            message="Should not append.",
        )
    with pytest.raises(ValueError, match="request_id not found"):
        append_response(
            path=path,
            request_id="bridge-request-missing",
            project_id="project-hermes",
            message="Should not append.",
        )

    assert len(JsonlRecordStore(path).read_all(JennyBridgeMessageResponseRecord)) == 0
    statuses = JsonlRecordStore(path).read_all(JennyBridgePollerStatusRecord)
    assert [record.status for record in statuses] == ["error", "error"]
    assert statuses[0].last_error == "request status is cancelled"
    assert statuses[1].last_error == "request_id not found"


def test_relay_status_reports_manual_flags_and_last_response(tmp_path):
    path = tmp_path / "records.jsonl"
    JsonlRecordStore(path).append(
        JennyBridgeMessageRequestRecord(
            request_id="bridge-request-1",
            project_id="project-hermes",
            message="Check bridge status.",
            status="queued",
        )
    )
    append_response(
        path=path,
        request_id="bridge-request-1",
        project_id="project-hermes",
        message="Answered.",
    )

    status = relay_status(path)

    assert status["manual_start_only"] is True
    assert status["trusted_for_execution"] is False
    assert status["inert_context_only"] is True
    assert status["would_execute"] is False
    assert status["dispatch_enabled"] is False
    assert status["session_send_enabled"] is False
    assert status["worker_dispatch_enabled"] is False
    assert status["worker_enabled"] is False
    assert status["timer_enabled"] is False
    assert status["pending_count"] == 0
    assert status["last_status"] == "response_appended"
    assert status["last_response_request_id"] == "bridge-request-1"
