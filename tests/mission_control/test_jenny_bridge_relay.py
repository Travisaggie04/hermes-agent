from mission_control.jenny_bridge_relay import append_response, pending_requests, relay_packet
from mission_control.records import (
    JennyBridgeMessageRequestRecord,
    JennyBridgeMessageResponseRecord,
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

    index, response = append_response(
        path=path,
        request_id="bridge-request-1",
        project_id="project-hermes",
        message="Bridge request received; remaining work is a bounded poller lane.",
    )
    assert index == 2
    assert response.record_type == "JennyBridgeMessageResponseRecord"
    assert response.metadata["dispatch_enabled"] is False
    assert response.metadata["send_to_jenny_enabled"] is False

    assert pending_requests(path) == []
    responses = JsonlRecordStore(path).read_all(JennyBridgeMessageResponseRecord)
    assert len(responses) == 1
    assert responses[0].request_id == "bridge-request-1"


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
