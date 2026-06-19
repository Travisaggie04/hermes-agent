"""Read-only Mission Control governance dashboard plugin tests."""

from __future__ import annotations

import inspect
import importlib.util
import re
import sys
from pathlib import Path

import pytest
import yaml
from fastapi import FastAPI
from fastapi.testclient import TestClient

from mission_control.records import (
    AcceptedBaselineRecord,
    ApprovalRecord,
    ApprovalSlice,
    ArtifactRef,
    ChallengeReviewRecord,
    ChildRunRecord,
    EvidenceCard,
    GoalContract,
    GitHubBridgeMailboxStatusRecord,
    GitHubBridgeMessageRecord,
    JsonlRecordStore,
    JennyBridgeMessageRequestRecord,
    JennyBridgeMessageResponseRecord,
    JennyBridgePollerStatusRecord,
    JennyReplyReviewRecord,
    JennyReportRecord,
    LaneRequestRecord,
    MissionBrief,
    OperatingWorkspaceHandoffRecord,
    OperatorAction,
    ProjectBriefRecord,
    ProjectRecord,
    ReportRecord,
    RunRecord,
    SessionProjectLinkRecord,
    StartGateCheck,
    TaskControlEnvelope,
    VerifierWorkflowEvidenceRecord,
    WorkerNodeRunRecord,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
PLUGIN_DIR = REPO_ROOT / "plugins" / "mission-control-governance"
API_PATH = PLUGIN_DIR / "api.py"


def _load_api_module():
    spec = importlib.util.spec_from_file_location(
        "mission_control_governance_plugin_api_test",
        API_PATH,
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def plugin_api(tmp_path, monkeypatch):
    module = _load_api_module()
    records_path = tmp_path / "mission-control" / "records.jsonl"
    monkeypatch.setattr(module, "record_store_path", lambda: records_path)
    return module


@pytest.fixture
def client(plugin_api):
    app = FastAPI()
    app.include_router(plugin_api.router, prefix="/api/plugins/mission-control-governance")
    return TestClient(app)


def test_workspace_project_api_creates_and_lists_append_only_records(plugin_api, client):
    response = client.post(
        "/api/plugins/mission-control-governance/workspace/projects/create",
        json={
            "name": "Hermes / Mission Control",
            "status": "live",
            "current_goal": "Make Mission Control the workspace.",
            "next_recommended_lane": "Create a durable lane request.",
            "mistakes_guards": "No dispatch without approval.",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["trusted_for_execution"] is False
    assert payload["execution_enabled"] is False
    assert payload["manual_copy_only"] is True
    assert payload["send_to_jenny_enabled"] is False
    assert payload["dispatch_enabled"] is False
    assert payload["stored"] is True
    assert payload["record_type"] == "ProjectRecord"
    assert payload["project"]["name"] == "Hermes / Mission Control"

    records = JsonlRecordStore(plugin_api.record_store_path()).read_all(ProjectRecord)
    assert len(records) == 1
    assert records[0].name == "Hermes / Mission Control"

    listed = client.get("/api/plugins/mission-control-governance/workspace/projects")
    assert listed.status_code == 200
    assert listed.json()["count"] == 1
    assert listed.json()["projects"][0]["record_type"] == "ProjectRecord"


def test_workspace_project_template_seed_creates_defaults_and_skips_duplicates(plugin_api, client):
    templates = client.get("/api/plugins/mission-control-governance/workspace/project-templates")
    assert templates.status_code == 200
    template_payload = templates.json()
    assert template_payload["stored"] is False
    assert template_payload["send_to_jenny_enabled"] is False
    assert template_payload["dispatch_enabled"] is False
    assert template_payload["count"] == 5
    assert {item["name"] for item in template_payload["templates"]} == {
        "Hermes / Mission Control",
        "Long-form Video",
        "Shorts Video",
        "Tool & Tally",
        "Waha Work",
    }
    assert all(item["exists"] is False for item in template_payload["templates"])
    assert all(item["default_guards"] for item in template_payload["templates"])

    seeded = client.post("/api/plugins/mission-control-governance/workspace/projects/seed-defaults", json={})
    assert seeded.status_code == 200
    payload = seeded.json()
    assert payload["trusted_for_execution"] is False
    assert payload["execution_enabled"] is False
    assert payload["manual_copy_only"] is True
    assert payload["send_to_jenny_enabled"] is False
    assert payload["dispatch_enabled"] is False
    assert payload["stored"] is True
    assert payload["created_count"] == 5
    assert payload["skipped_count"] == 0

    projects = JsonlRecordStore(plugin_api.record_store_path()).read_all(ProjectRecord)
    assert len(projects) == 5
    assert {project.project_id for project in projects} == {
        "project-hermes-mission-control",
        "project-long-form-video",
        "project-shorts-video",
        "project-tool-tally",
        "project-waha-work",
    }
    assert all(project.source_of_truth for project in projects)
    assert all(project.current_goal for project in projects)
    assert all(project.mistakes_guards for project in projects)
    assert all(project.metadata.get("default_guards") for project in projects)
    assert all(project.metadata.get("send_to_jenny_enabled") is False for project in projects)
    assert all(project.metadata.get("dispatch_enabled") is False for project in projects)
    hermes_project = next(project for project in projects if project.project_id == "project-hermes-mission-control")
    assert "Jenny OS native chat" in hermes_project.current_goal
    assert "Make Mission Control the obvious operating surface" not in hermes_project.current_goal

    reseed = client.post("/api/plugins/mission-control-governance/workspace/projects/seed-defaults", json={})
    assert reseed.status_code == 200
    reseed_payload = reseed.json()
    assert reseed_payload["stored"] is False
    assert reseed_payload["created_count"] == 0
    assert reseed_payload["skipped_count"] == 5
    assert len(JsonlRecordStore(plugin_api.record_store_path()).read_all(ProjectRecord)) == 5

    after_templates = client.get("/api/plugins/mission-control-governance/workspace/project-templates")
    assert after_templates.status_code == 200
    assert all(item["exists"] is True for item in after_templates.json()["templates"])

    state = client.get("/api/plugins/mission-control-governance/workspace/project-state")
    assert state.status_code == 200
    state_payload = state.json()
    assert state_payload["stored"] is False
    assert state_payload["count"] == 5


def test_workspace_project_brief_api_creates_lists_and_stays_inert(plugin_api, client):
    response = client.post(
        "/api/plugins/mission-control-governance/workspace/project-briefs/create",
        json={
            "project_id": "project-hermes-mission-control",
            "name": "Hermes / Mission Control",
            "outcome": "Make Jenny reliable before increasing autonomy.",
            "audience": "Travis",
            "source_of_truth": "Mission Control records",
            "success_criteria": ["workspace-status agrees", "challenge gate exists"],
            "constraints": ["manual-copy only until send path is reviewed"],
            "forbidden_actions": ["dispatch", "session-send", "runtime switch"],
            "approval_rules": ["deploy requires explicit approval"],
            "context_pack_path": "context-packs/mission-control-current.md",
            "status": "active",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["trusted_for_execution"] is False
    assert payload["execution_enabled"] is False
    assert payload["manual_copy_only"] is True
    assert payload["send_to_jenny_enabled"] is False
    assert payload["dispatch_enabled"] is False
    assert payload["stored"] is True
    assert payload["record_type"] == "ProjectBriefRecord"
    assert payload["project_brief"]["project_id"] == "project-hermes-mission-control"

    records = JsonlRecordStore(plugin_api.record_store_path()).read_all(ProjectBriefRecord)
    assert len(records) == 1
    assert records[0].status == "active"
    assert records[0].forbidden_actions == ("dispatch", "session-send", "runtime switch")

    listed = client.get(
        "/api/plugins/mission-control-governance/workspace/project-briefs?project_id=project-hermes-mission-control"
    )
    assert listed.status_code == 200
    listed_payload = listed.json()
    assert listed_payload["count"] == 1
    assert listed_payload["project_briefs"][0]["record_type"] == "ProjectBriefRecord"


def test_workspace_challenge_review_api_creates_lists_and_challenges_bad_direction(plugin_api, client):
    response = client.post(
        "/api/plugins/mission-control-governance/workspace/challenge-reviews/create",
        json={
            "project_id": "project-shorts-video",
            "request_summary": "Make Jenny post automatically every day.",
            "decision_state": "wrong_approach_likely",
            "challenge_categories": ["wrong_approach", "protected_surface"],
            "blocking_verdicts": ["blocks_lane_draft", "requires_travis_approval"],
            "recommended_path": "Start with scheduled drafts, then approval-gated posting.",
            "concerns": ["automation before observability", "public posting needs approval"],
            "questions": ["Which platform is highest priority?"],
            "required_spec_updates": ["add platform failure policy"],
            "required_approvals": ["public posting approval"],
            "suggested_lane_title": "Read-only scheduler readiness audit",
            "reviewed_by": "jenny",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["trusted_for_execution"] is False
    assert payload["execution_enabled"] is False
    assert payload["manual_copy_only"] is True
    assert payload["send_to_jenny_enabled"] is False
    assert payload["dispatch_enabled"] is False
    assert payload["stored"] is True
    assert payload["record_type"] == "ChallengeReviewRecord"
    assert payload["challenge_review"]["decision_state"] == "wrong_approach_likely"
    assert payload["challenge_review"]["challenge_categories"] == ["wrong_approach", "protected_surface"]
    assert payload["challenge_review"]["blocking_verdicts"] == ["blocks_lane_draft", "requires_travis_approval"]
    assert payload["challenge_review"]["recommended_path"] == "Start with scheduled drafts, then approval-gated posting."

    records = JsonlRecordStore(plugin_api.record_store_path()).read_all(ChallengeReviewRecord)
    assert len(records) == 1
    assert records[0].concerns == ("automation before observability", "public posting needs approval")
    assert records[0].challenge_categories == ("wrong_approach", "protected_surface")
    assert records[0].blocking_verdicts == ("blocks_lane_draft", "requires_travis_approval")

    listed = client.get(
        "/api/plugins/mission-control-governance/workspace/challenge-reviews?project_id=project-shorts-video"
    )
    assert listed.status_code == 200
    listed_payload = listed.json()
    assert listed_payload["count"] == 1
    assert listed_payload["challenge_reviews"][0]["record"]["decision_state"] == "wrong_approach_likely"
    assert listed_payload["challenge_reviews"][0]["record"]["challenge_categories"] == ["wrong_approach", "protected_surface"]


def test_workspace_challenge_review_rejects_invalid_challenge_category(client):
    response = client.post(
        "/api/plugins/mission-control-governance/workspace/challenge-reviews/create",
        json={
            "project_id": "project-hermes-mission-control",
            "request_summary": "Do a vague unsafe thing.",
            "decision_state": "needs_spec_first",
            "challenge_categories": ["vibes_only"],
        },
    )

    assert response.status_code == 422
    assert "challenge_categories must contain only" in response.json()["detail"]


def test_workspace_project_intake_rejects_invalid_challenge_state(client):
    response = client.post(
        "/api/plugins/mission-control-governance/workspace/challenge-reviews/create",
        json={
            "project_id": "project-hermes-mission-control",
            "request_summary": "Do a vague unsafe thing.",
            "decision_state": "just_do_it",
        },
    )

    assert response.status_code == 422
    assert "status must be one of" in response.json()["detail"]


def test_workspace_lane_request_api_creates_lists_and_stays_inert(plugin_api, client):
    store = JsonlRecordStore(plugin_api.record_store_path())
    store.append(ProjectRecord(project_id="project-hermes", name="Hermes / Mission Control"))

    response = client.post(
        "/api/plugins/mission-control-governance/workspace/lane-requests/create",
        json={
            "project_id": "project-hermes",
            "title": "Read-only status refresh",
            "objective": "Inspect current status and recommend next lane.",
            "allowed_actions": ["read approved context", "report status"],
            "forbidden_actions": ["dispatch", "execute", "queue mutation"],
            "stop_conditions": ["workspace-status preflight fails"],
            "expected_report_format": ["preflight", "no-mutation confirmation"],
            "draft_prompt": "Manual transport only — paste into Discord.",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["trusted_for_execution"] is False
    assert payload["execution_enabled"] is False
    assert payload["manual_copy_only"] is True
    assert payload["send_to_jenny_enabled"] is False
    assert payload["dispatch_enabled"] is False
    assert payload["stored"] is True
    assert payload["record_type"] == "LaneRequestRecord"
    assert payload["lane_request"]["status"] == "draft"
    assert payload["lane_request"]["metadata"]["dispatch_enabled"] is False

    records = JsonlRecordStore(plugin_api.record_store_path()).read_all(LaneRequestRecord)
    assert len(records) == 1
    assert records[0].title == "Read-only status refresh"
    assert records[0].forbidden_actions == ("dispatch", "execute", "queue mutation")

    listed = client.get("/api/plugins/mission-control-governance/workspace/lane-requests?project_id=project-hermes")
    assert listed.status_code == 200
    assert listed.json()["count"] == 1
    assert listed.json()["lane_requests"][0]["record"]["project_id"] == "project-hermes"


def test_workspace_jenny_report_api_creates_lists_and_stays_inert(plugin_api, client):
    store = JsonlRecordStore(plugin_api.record_store_path())
    store.append(ProjectRecord(project_id="project-hermes", name="Hermes / Mission Control"))
    store.append(LaneRequestRecord(lane_request_id="lane-request-1", project_id="project-hermes", title="Read-only status refresh"))

    response = client.post(
        "/api/plugins/mission-control-governance/workspace/reports/create",
        json={
            "project_id": "project-hermes",
            "lane_request_id": "lane-request-1",
            "summary": "Jenny completed the read-only status refresh.",
            "result": "No runtime mutation occurred.",
            "changed_files": ["mission_control/records/models.py"],
            "artifact_links": ["reports/hermes/status.md"],
            "tests": ["pytest -q"],
            "risks": ["none"],
            "next_recommended_lane": "Review next report inbox slice.",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["trusted_for_execution"] is False
    assert payload["execution_enabled"] is False
    assert payload["manual_copy_only"] is True
    assert payload["send_to_jenny_enabled"] is False
    assert payload["dispatch_enabled"] is False
    assert payload["stored"] is True
    assert payload["record_type"] == "JennyReportRecord"
    assert payload["report"]["project_id"] == "project-hermes"
    assert payload["report"]["lane_request_id"] == "lane-request-1"
    assert payload["report"]["metadata"]["dispatch_enabled"] is False
    assert payload["report"]["metadata"]["artifact_links"] == ["reports/hermes/status.md"]

    reports = JsonlRecordStore(plugin_api.record_store_path()).read_all(JennyReportRecord)
    assert len(reports) == 1
    assert reports[0].summary == "Jenny completed the read-only status refresh."
    assert reports[0].changed_files == ("mission_control/records/models.py",)

    listed = client.get("/api/plugins/mission-control-governance/workspace/reports?project_id=project-hermes&lane_request_id=lane-request-1")
    assert listed.status_code == 200
    assert listed.json()["count"] == 1
    assert listed.json()["reports"][0]["record"]["summary"] == "Jenny completed the read-only status refresh."


def test_workspace_jenny_bridge_api_creates_lists_and_stays_inert(plugin_api, client):
    response = client.post(
        "/api/plugins/mission-control-governance/workspace/jenny-bridge/outbox/create",
        json={
            "request_id": "bridge-request-1",
            "project_id": "project-hermes",
            "lane_request_id": "lane-request-1",
            "sender": "codex",
            "target_agent": "jenny",
            "message": "Please review PR #75 and report whether it is safe to mark ready.",
            "user_message": "Review PR #75.",
            "ack_key": "pr75-review",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["trusted_for_execution"] is False
    assert payload["execution_enabled"] is False
    assert payload["manual_copy_only"] is False
    assert payload["send_to_jenny_enabled"] is False
    assert payload["dispatch_enabled"] is False
    assert payload["stored"] is True
    assert payload["record_type"] == "JennyBridgeMessageRequestRecord"
    assert payload["request"]["project_id"] == "project-hermes"
    assert payload["request"]["status"] == "queued"
    assert payload["request"]["metadata"]["requires_external_jenny_poller"] is True
    assert payload["request"]["metadata"]["user_message"] == "Review PR #75."

    requests = JsonlRecordStore(plugin_api.record_store_path()).read_all(JennyBridgeMessageRequestRecord)
    assert len(requests) == 1
    assert requests[0].message == "Please review PR #75 and report whether it is safe to mark ready."
    assert requests[0].metadata["user_message"] == "Review PR #75."

    listed = client.get(
        "/api/plugins/mission-control-governance/workspace/jenny-bridge/outbox?project_id=project-hermes&status=queued"
    )
    assert listed.status_code == 200
    assert listed.json()["manual_copy_only"] is False
    assert listed.json()["send_to_jenny_enabled"] is False
    assert listed.json()["dispatch_enabled"] is False
    assert listed.json()["count"] == 1
    assert listed.json()["requests"][0]["record"]["request_id"] == "bridge-request-1"
    assert listed.json()["requests"][0]["record"]["bridge_state"] == "queued"
    assert listed.json()["requests"][0]["has_response"] is False

    pending = client.get("/api/plugins/mission-control-governance/workspace/jenny-bridge/pending?project_id=project-hermes")
    assert pending.status_code == 200
    pending_payload = pending.json()
    assert pending_payload["manual_copy_only"] is False
    assert pending_payload["send_to_jenny_enabled"] is False
    assert pending_payload["dispatch_enabled"] is False
    assert pending_payload["relay_ready"] is True
    assert pending_payload["poller_required"] is True
    assert pending_payload["count"] == 1
    assert pending_payload["requests"][0]["record"]["request_id"] == "bridge-request-1"
    assert "Mission Control Jenny bridge relay packet" in pending_payload["relay_packet"]
    assert "bridge-request-1" in pending_payload["relay_packet"]
    assert "POST /workspace/jenny-bridge/inbox/create" in pending_payload["relay_packet"]

    inbound = client.post(
        "/api/plugins/mission-control-governance/workspace/jenny-bridge/inbox/create",
        json={
            "response_id": "bridge-response-1",
            "request_id": "bridge-request-1",
            "project_id": "project-hermes",
            "lane_request_id": "lane-request-1",
            "responder": "jenny",
            "message": "Safe to mark ready. No runtime behavior changed.",
        },
    )

    assert inbound.status_code == 200
    inbound_payload = inbound.json()
    assert inbound_payload["trusted_for_execution"] is False
    assert inbound_payload["execution_enabled"] is False
    assert inbound_payload["manual_copy_only"] is False
    assert inbound_payload["send_to_jenny_enabled"] is False
    assert inbound_payload["dispatch_enabled"] is False
    assert inbound_payload["stored"] is True
    assert inbound_payload["record_type"] == "JennyBridgeMessageResponseRecord"
    assert inbound_payload["response"]["request_id"] == "bridge-request-1"
    assert inbound_payload["response"]["metadata"]["external_jenny_response"] is True

    responses = JsonlRecordStore(plugin_api.record_store_path()).read_all(JennyBridgeMessageResponseRecord)
    assert len(responses) == 1
    assert responses[0].message == "Safe to mark ready. No runtime behavior changed."

    inbox = client.get(
        "/api/plugins/mission-control-governance/workspace/jenny-bridge/inbox?project_id=project-hermes&request_id=bridge-request-1"
    )
    assert inbox.status_code == 200
    assert inbox.json()["manual_copy_only"] is False
    assert inbox.json()["send_to_jenny_enabled"] is False
    assert inbox.json()["dispatch_enabled"] is False
    assert inbox.json()["count"] == 1
    assert inbox.json()["responses"][0]["record"]["response_id"] == "bridge-response-1"

    answered_outbox = client.get(
        "/api/plugins/mission-control-governance/workspace/jenny-bridge/outbox?project_id=project-hermes"
    )
    assert answered_outbox.status_code == 200
    assert answered_outbox.json()["requests"][0]["record"]["bridge_state"] == "replied"
    assert answered_outbox.json()["requests"][0]["has_response"] is True

    queued_after_response = client.get(
        "/api/plugins/mission-control-governance/workspace/jenny-bridge/outbox?project_id=project-hermes&status=queued"
    )
    assert queued_after_response.status_code == 200
    assert queued_after_response.json()["count"] == 0

    pending_after_response = client.get(
        "/api/plugins/mission-control-governance/workspace/jenny-bridge/pending?project_id=project-hermes"
    )
    assert pending_after_response.status_code == 200
    assert pending_after_response.json()["count"] == 0
    assert "No pending bridge requests." in pending_after_response.json()["relay_packet"]


def test_workspace_jenny_reply_reviews_append_operator_decisions_and_stay_inert(plugin_api, client):
    created = client.post(
        "/api/plugins/mission-control-governance/workspace/jenny-reply-reviews/create",
        json={
            "project_id": "project-hermes",
            "response_id": "bridge-response-1",
            "request_id": "bridge-request-1",
            "decision": "needs_evidence",
            "reviewer": "travis",
            "note": "Ask Jenny for exact files, checks, risks, and next safe lane.",
        },
    )

    assert created.status_code == 200
    payload = created.json()
    assert payload["stored"] is True
    assert payload["display_only"] is True
    assert payload["manual_start_only"] is True
    assert payload["send_to_jenny_enabled"] is False
    assert payload["dispatch_enabled"] is False
    assert payload["execution_enabled"] is False
    assert payload["worker_enabled"] is False
    assert payload["timer_enabled"] is False
    assert payload["record_type"] == "JennyReplyReviewRecord"
    assert payload["reply_review"]["response_id"] == "bridge-response-1"
    assert payload["reply_review"]["decision"] == "needs_evidence"
    assert payload["reply_review"]["metadata"]["trusted_for_execution"] is False

    reviews = JsonlRecordStore(plugin_api.record_store_path()).read_all(JennyReplyReviewRecord)
    assert len(reviews) == 1
    assert reviews[0].note == "Ask Jenny for exact files, checks, risks, and next safe lane."

    listed = client.get(
        "/api/plugins/mission-control-governance/workspace/jenny-reply-reviews?project_id=project-hermes&response_id=bridge-response-1"
    )
    assert listed.status_code == 200
    list_payload = listed.json()
    assert list_payload["stored"] is False
    assert list_payload["send_to_jenny_enabled"] is False
    assert list_payload["dispatch_enabled"] is False
    assert list_payload["worker_enabled"] is False
    assert list_payload["timer_enabled"] is False
    assert list_payload["count"] == 1
    assert list_payload["reply_reviews"][0]["record"]["decision"] == "needs_evidence"

    invalid = client.post(
        "/api/plugins/mission-control-governance/workspace/jenny-reply-reviews/create",
        json={
            "project_id": "project-hermes",
            "response_id": "bridge-response-1",
            "decision": "deploy_now",
        },
    )
    assert invalid.status_code == 422


def test_workspace_jenny_bridge_poller_status_is_read_only(plugin_api, client):
    store = JsonlRecordStore(plugin_api.record_store_path())
    store.append(
        JennyBridgeMessageRequestRecord(
            request_id="bridge-request-1",
            project_id="project-hermes",
            message="Pending bridge request.",
            status="queued",
        )
    )
    store.append(
        JennyBridgePollerStatusRecord(
            status_id="bridge-status-1",
            poller_id="manual-jenny-bridge-relay",
            mode="manual",
            status="error",
            pending_count=1,
            handled_request_id="bridge-request-1",
            last_error="operator stopped before responding",
            created_at="2026-06-12T15:22:00Z",
            metadata={
                "manual_start_only": True,
                "dispatch_enabled": False,
                "session_send_enabled": False,
                "worker_enabled": False,
                "timer_enabled": False,
            },
        )
    )

    before = len(store.read_all())
    response = client.get("/api/plugins/mission-control-governance/workspace/jenny-bridge/poller-status")

    assert response.status_code == 200
    payload = response.json()
    assert payload["stored"] is False
    assert payload["display_only"] is True
    assert payload["manual_start_only"] is True
    assert payload["dispatch_enabled"] is False
    assert payload["send_to_jenny_enabled"] is False
    assert payload["session_send_enabled"] is False
    assert payload["worker_enabled"] is False
    assert payload["timer_enabled"] is False
    assert payload["pending_count"] == 1
    assert payload["last_status"] == "error"
    assert payload["last_error"] == "operator stopped before responding"
    assert payload["status_records"][0]["record"]["status_id"] == "bridge-status-1"
    assert len(store.read_all()) == before


def test_workspace_github_bridge_status_is_read_only_and_manual_only(plugin_api, client):
    store = JsonlRecordStore(plugin_api.record_store_path())
    store.append(
        GitHubBridgeMessageRecord(
            request_id="github-req-open",
            project_id="project-hermes",
            from_agent="codex",
            to_agent="jenny",
            status="queued",
            message="Please review from Codex.",
            created_at="2026-06-13T00:00:00Z",
            github_repo="Travisaggie04/hermes-agent",
            github_issue_number=79,
            github_comment_id="101",
        )
    )
    store.append(
        GitHubBridgeMessageRecord(
            request_id="github-req-done",
            project_id="project-hermes",
            from_agent="jenny",
            to_agent="travis",
            status="replied",
            message="Reviewed from Jenny.",
            created_at="2026-06-13T00:00:30Z",
            github_repo="Travisaggie04/hermes-agent",
            github_issue_number=79,
            github_comment_id="102",
        )
    )
    store.append(
        GitHubBridgeMessageRecord(
            request_id="github-req-travis-open",
            project_id="project-hermes",
            from_agent="travis",
            to_agent="jenny",
            status="queued",
            message="Please answer Travis from Mission Control.",
            created_at="2026-06-13T00:00:45Z",
            github_repo="Travisaggie04/hermes-agent",
            github_issue_number=79,
            github_comment_id="103",
        )
    )
    store.append(
        GitHubBridgeMailboxStatusRecord(
            status_id="github-status-1",
            repo="Travisaggie04/hermes-agent",
            issue_number=79,
            mode="watch_foreground",
            status="watch_poll_completed",
            pending_count=1,
            new_message_count=1,
            created_at="2026-06-13T00:01:00Z",
            metadata={"manual_start_only": True, "worker_enabled": False, "timer_enabled": False},
        )
    )

    before = len(store.read_all())
    response = client.get("/api/plugins/mission-control-governance/workspace/github-bridge/status")

    assert response.status_code == 200
    payload = response.json()
    assert payload["stored"] is False
    assert payload["display_only"] is True
    assert payload["manual_start_only"] is True
    assert payload["dispatch_enabled"] is False
    assert payload["session_send_enabled"] is False
    assert payload["worker_enabled"] is False
    assert payload["timer_enabled"] is False
    assert payload["daemon_enabled"] is False
    assert payload["discord_automation_enabled"] is False
    assert payload["model_routing_enabled"] is False
    assert payload["pending_count"] == 2
    assert payload["visible_pending_count"] == 1
    assert payload["background_pending_count"] == 1
    assert payload["mode"] == "watch_foreground"
    assert payload["foreground_watch_supported"] is True
    assert payload["foreground_watch_running"] is False
    assert payload["last_status"] == "watch_poll_completed"
    assert payload["pending_messages"][0]["record"]["request_id"] == "github-req-open"
    assert payload["visible_pending_messages"][0]["record"]["request_id"] == "github-req-travis-open"
    assert payload["recent_messages"][-1]["record"]["request_id"] == "github-req-travis-open"
    assert payload["response_messages"][0]["record"]["message"] == "Reviewed from Jenny."
    assert len(store.read_all()) == before


def test_workspace_github_bridge_status_collapses_superseded_codex_deploy_requests(plugin_api, client):
    store = JsonlRecordStore(plugin_api.record_store_path())
    store.append(
        GitHubBridgeMessageRecord(
            request_id="codex-deploy-chat-old",
            project_id="project-hermes",
            from_agent="codex",
            to_agent="jenny",
            status="queued",
            message="Dashboard-only deploy request. accepted-live head old.",
            created_at="2026-06-13T00:00:00Z",
            github_repo="Travisaggie04/hermes-agent",
            github_issue_number=79,
            github_comment_id="201",
        )
    )
    store.append(
        GitHubBridgeMessageRecord(
            request_id="codex-deploy-chat-new",
            project_id="project-hermes",
            from_agent="codex",
            to_agent="jenny",
            status="queued",
            message="Dashboard-only deploy request. accepted-live head new.",
            created_at="2026-06-13T00:01:00Z",
            github_repo="Travisaggie04/hermes-agent",
            github_issue_number=79,
            github_comment_id="202",
        )
    )
    store.append(
        GitHubBridgeMessageRecord(
            request_id="github-req-travis-open",
            project_id="project-hermes",
            from_agent="travis",
            to_agent="jenny",
            status="queued",
            message="Please answer Travis from Mission Control.",
            created_at="2026-06-13T00:02:00Z",
            github_repo="Travisaggie04/hermes-agent",
            github_issue_number=79,
            github_comment_id="203",
        )
    )

    response = client.get("/api/plugins/mission-control-governance/workspace/github-bridge/status")

    assert response.status_code == 200
    payload = response.json()
    assert payload["pending_count"] == 2
    assert payload["visible_pending_count"] == 1
    assert payload["background_pending_count"] == 1
    assert payload["superseded_background_pending_count"] == 1
    pending_ids = [item["record"]["request_id"] for item in payload["pending_messages"]]
    assert pending_ids == ["codex-deploy-chat-new", "github-req-travis-open"]
    assert payload["visible_pending_messages"][0]["record"]["request_id"] == "github-req-travis-open"


def test_workspace_github_bridge_status_can_filter_by_project(plugin_api, client):
    store = JsonlRecordStore(plugin_api.record_store_path())
    store.append(
        GitHubBridgeMessageRecord(
            request_id="hermes-req",
            project_id="project-hermes",
            from_agent="travis",
            to_agent="jenny",
            status="queued",
            message="Hermes project request.",
            created_at="2026-06-13T00:00:00Z",
            github_repo="Travisaggie04/hermes-agent",
            github_issue_number=79,
            github_comment_id="301",
        )
    )
    store.append(
        GitHubBridgeMessageRecord(
            request_id="tool-req",
            project_id="project-tool-tally",
            from_agent="travis",
            to_agent="jenny",
            status="queued",
            message="Tool project request.",
            created_at="2026-06-13T00:01:00Z",
            github_repo="Travisaggie04/hermes-agent",
            github_issue_number=79,
            github_comment_id="302",
        )
    )
    store.append(
        GitHubBridgeMailboxStatusRecord(
            status_id="hermes-status",
            repo="Travisaggie04/hermes-agent",
            issue_number=79,
            mode="manual_hermes_answer",
            status="manual_hermes_answer_started",
            pending_count=1,
            handled_request_id="hermes-req",
            created_at="2026-06-13T00:01:30Z",
            metadata={"manual_start_only": True, "worker_enabled": False, "timer_enabled": False},
        )
    )
    store.append(
        GitHubBridgeMailboxStatusRecord(
            status_id="tool-error",
            repo="Travisaggie04/hermes-agent",
            issue_number=79,
            mode="manual_hermes_answer",
            status="error",
            pending_count=1,
            handled_request_id="tool-req",
            last_error="tool request failed",
            created_at="2026-06-13T00:02:00Z",
            metadata={"manual_start_only": True, "worker_enabled": False, "timer_enabled": False},
        )
    )

    response = client.get(
        "/api/plugins/mission-control-governance/workspace/github-bridge/status?project_id=project-hermes"
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["project_id"] == "project-hermes"
    assert payload["pending_count"] == 1
    assert payload["visible_pending_count"] == 1
    assert payload["background_pending_count"] == 0
    assert payload["last_status"] == "manual_hermes_answer_started"
    assert payload["last_error"] == ""
    assert payload["pending_messages"][0]["record"]["request_id"] == "hermes-req"
    assert payload["visible_pending_messages"][0]["record"]["request_id"] == "hermes-req"
    assert [item["record"]["request_id"] for item in payload["recent_messages"]] == ["hermes-req"]


def test_workspace_async_agent_status_is_read_only_and_status_only(plugin_api, client):
    store = JsonlRecordStore(plugin_api.record_store_path())
    before = len(store.read_all())

    response = client.get("/api/plugins/mission-control-governance/workspace/async-agent-status")

    assert response.status_code == 200
    payload = response.json()
    _assert_inert_workspace_payload(payload)
    assert payload["stored"] is False
    assert payload["manual_start_only"] is True
    assert payload["session_send_enabled"] is False
    assert payload["worker_enabled"] is False
    assert payload["timer_enabled"] is False
    assert payload["daemon_enabled"] is False
    assert payload["model_routing_enabled"] is False
    assert payload["sync_delegate_task_available"] is True
    assert payload["sync_delegate_task_durable"] is False
    assert payload["async_agent_controls_enabled"] is False
    assert payload["async_agent_controls_expected"] == ["spawn", "check", "steer", "collect", "cancel", "list"]
    assert payload["current_mode"] in {
        "sync_delegate_task_only",
        "native_async_agents_available",
    }
    assert "approval-gated" in payload["policy_summary"]
    assert len(store.read_all()) == before


def test_workspace_github_bridge_outbox_create_posts_one_mailbox_message(plugin_api, client, monkeypatch):
    def fake_post_github_message(**kwargs):
        record = GitHubBridgeMessageRecord(
            request_id=kwargs["request_id"],
            project_id=kwargs["project_id"],
            from_agent=kwargs["from_agent"],
            to_agent=kwargs["to_agent"],
            status=kwargs["status"],
            message=kwargs["message"],
            created_at="2026-06-13T00:02:00Z",
            github_repo="Travisaggie04/hermes-agent",
            github_issue_number=79,
            github_comment_id="103",
            metadata={"user_message": kwargs.get("user_message", "")},
        )
        index = JsonlRecordStore(kwargs["path"]).append(record)
        return {
            "record_index": index,
            "record_type": record.record_type,
            "message": record.to_dict(),
            "status": {"status": "message_posted", "manual_start_only": True},
        }

    monkeypatch.setattr(plugin_api, "post_github_message", fake_post_github_message)

    response = client.post(
        "/api/plugins/mission-control-governance/workspace/github-bridge/outbox/create",
        json={
            "request_id": "github-req-ui",
            "project_id": "project-hermes",
            "from_agent": "travis",
            "to_agent": "jenny",
            "message": "Please review Mission Control chat bridge.",
            "user_message": "Please review the room without showing the hidden guardrail packet.",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["stored"] is True
    assert payload["send_to_jenny_enabled"] is True
    assert payload["dispatch_enabled"] is False
    assert payload["session_send_enabled"] is False
    assert payload["execution_enabled"] is False
    assert payload["worker_enabled"] is False
    assert payload["timer_enabled"] is False
    assert payload["daemon_enabled"] is False
    assert payload["github_bridge_enabled"] is True
    assert payload["record_type"] == "GitHubBridgeMessageRecord"
    assert payload["message"]["request_id"] == "github-req-ui"
    assert payload["message"]["from_agent"] == "travis"
    assert payload["message"]["to_agent"] == "jenny"
    assert payload["message"]["metadata"]["user_message"] == "Please review the room without showing the hidden guardrail packet."
    records = JsonlRecordStore(plugin_api.record_store_path()).read_all(GitHubBridgeMessageRecord)
    assert [record.request_id for record in records] == ["github-req-ui"]
    assert records[0].metadata["user_message"] == "Please review the room without showing the hidden guardrail packet."


def test_workspace_github_bridge_answer_once_requires_explicit_request(plugin_api, client):
    response = client.post(
        "/api/plugins/mission-control-governance/workspace/github-bridge/answer-once",
        json={"project_id": "project-hermes"},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "request_id is required"


def test_workspace_github_bridge_answer_once_requires_manual_confirmation(plugin_api, client, monkeypatch):
    monkeypatch.setattr(
        plugin_api,
        "answer_pending_with_hermes",
        lambda **_kwargs: pytest.fail("answer-once must not run without explicit confirmation"),
    )

    response = client.post(
        "/api/plugins/mission-control-governance/workspace/github-bridge/answer-once",
        json={"project_id": "project-hermes", "request_id": "github-req-ui"},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "confirm_manual_hermes_answer is required"


def test_workspace_github_bridge_answer_once_runs_single_manual_answer(plugin_api, client, monkeypatch):
    def fake_answer_pending_with_hermes(**kwargs):
        assert kwargs["project_id"] == "project-hermes"
        assert kwargs["request_id"] == "github-req-ui"
        assert kwargs["path"] == plugin_api.record_store_path()
        assert kwargs["operator"] == "mission-control-ui"
        return {
            "manual_start_only": True,
            "dispatch_enabled": False,
            "session_send_enabled": False,
            "execution_enabled": False,
            "worker_enabled": False,
            "timer_enabled": False,
            "answered": True,
            "request": {
                "request_id": "github-req-ui",
                "project_id": "project-hermes",
                "from_agent": "travis",
                "to_agent": "jenny",
                "status": "queued",
                "message": "Please answer one request.",
            },
            "response": {
                "request_id": "github-req-ui",
                "project_id": "project-hermes",
                "from_agent": "jenny",
                "to_agent": "travis",
                "status": "replied",
                "message": "Answered once.",
            },
            "status": {"status": "hermes_answer_completed"},
        }

    monkeypatch.setattr(plugin_api, "answer_pending_with_hermes", fake_answer_pending_with_hermes)

    response = client.post(
        "/api/plugins/mission-control-governance/workspace/github-bridge/answer-once",
        json={
            "confirm_manual_hermes_answer": True,
            "project_id": "project-hermes",
            "request_id": "github-req-ui",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["stored"] is True
    assert payload["manual_start_only"] is True
    assert payload["manual_hermes_answer_enabled"] is True
    assert payload["requires_explicit_manual_confirmation"] is True
    assert payload["send_to_jenny_enabled"] is True
    assert payload["dispatch_enabled"] is False
    assert payload["session_send_enabled"] is False
    assert payload["execution_enabled"] is False
    assert payload["worker_enabled"] is False
    assert payload["timer_enabled"] is False
    assert payload["daemon_enabled"] is False
    assert payload["github_bridge_enabled"] is True
    assert payload["answered"] is True
    assert payload["request"]["request_id"] == "github-req-ui"
    assert payload["response"]["message"] == "Answered once."


def _assert_inert_workspace_payload(payload):
    assert payload["display_only"] is True
    assert payload["manual_copy_only"] is True
    assert payload["send_to_jenny_enabled"] is False
    assert payload["dispatch_enabled"] is False
    assert payload["execution_enabled"] is False
    assert payload["trusted_for_execution"] is False
    assert payload["inert_context_only"] is True


def test_control_plane_records_round_trip_and_register():
    approval = ApprovalRecord(
        approval_id="approval-1",
        project_id="project-hermes",
        lane_request_id="lane-request-1",
        run_id="run-1",
        action_class="read_only_lane",
        approval_scope="project-hermes read-only status refresh",
        approved_actions=("inspect", "report"),
        forbidden_actions=("dispatch", "session-send"),
        status="approved",
        approved_by="Travis",
        approval_source="desktop",
        approval_text="Approved read-only inspection only.",
        created_at="2026-06-12T00:00:00Z",
        approved_at="2026-06-12T00:01:00Z",
        baseline_head="d7d1e0d758a64783f4de435f06450be218e8a2bf",
        metadata={"manual_copy_only": True},
    )
    assert ApprovalRecord.from_dict(approval.to_dict()) == approval

    run = RunRecord(
        run_id="run-1",
        project_id="project-hermes",
        lane_request_id="lane-request-1",
        approval_id="approval-1",
        lane_type="read_only_inspection",
        title="Inspect Mission Control state",
        objective="Read-only validation only.",
        status="requested",
        allowed_actions=("read files",),
        forbidden_actions=("write files", "dispatch"),
        baseline_head="d7d1e0d758a64783f4de435f06450be218e8a2bf",
        runtime_guard_state="pass",
        dispatch_state=False,
        safety_gate_status="pass",
        safety_gate_reasons=("dispatch false",),
        report_ids=("report-1",),
        metadata={"manual_copy_only": True},
    )
    assert RunRecord.from_dict(run.to_dict()) == run
    assert run.execution_mode == "manual_copy"

    report = ReportRecord(
        report_id="report-1",
        run_id="run-1",
        approval_id="approval-1",
        project_id="project-hermes",
        lane_request_id="lane-request-1",
        status="received",
        report_kind="jenny_result",
        summary="Preflight passed.",
        result="No mutation occurred.",
        risks=("none",),
        blockers=(),
        changed_files=("mission_control/records/models.py",),
        tests=("pytest tests/plugins/test_mission_control_governance_plugin.py",),
        next_recommended_lane="Review report inbox UI.",
        evidence_refs=("reports/control-plane/preflight.md",),
        artifact_refs=("reports/control-plane/output.md",),
        submitted_by="Jenny",
        submitted_from="desktop_manual_paste",
        created_at="2026-06-12T00:02:00Z",
    )
    assert ReportRecord.from_dict(report.to_dict()) == report

    from mission_control.records.models import RECORD_TYPES

    assert RECORD_TYPES["ApprovalRecord"] is ApprovalRecord
    assert RECORD_TYPES["RunRecord"] is RunRecord
    assert RECORD_TYPES["ReportRecord"] is ReportRecord
    assert RECORD_TYPES["ProjectBriefRecord"] is ProjectBriefRecord
    assert RECORD_TYPES["ChallengeReviewRecord"] is ChallengeReviewRecord


def test_control_plane_get_endpoints_empty_are_inert(client):
    for path, collection in (
        ("/api/plugins/mission-control-governance/workspace/approvals", "approvals"),
        ("/api/plugins/mission-control-governance/workspace/runs", "runs"),
        ("/api/plugins/mission-control-governance/workspace/report-inbox", "reports"),
    ):
        response = client.get(path)
        assert response.status_code == 200
        payload = response.json()
        _assert_inert_workspace_payload(payload)
        assert payload["stored"] is False
        assert payload["count"] == 0
        assert payload[collection] == []


def test_control_plane_append_endpoints_store_temp_records_and_stay_inert(plugin_api, client):
    approval = client.post(
        "/api/plugins/mission-control-governance/workspace/approvals/create",
        json={
            "project_id": "project-hermes",
            "lane_request_id": "lane-request-1",
            "run_id": "run-1",
            "action_class": "read_only_lane",
            "approval_scope": "project-hermes read-only inspection only",
            "approved_actions": ["inspect", "report"],
            "forbidden_actions": ["dispatch", "session-send", "queue mutation"],
            "status": "approved",
            "approved_by": "Travis",
            "approval_source": "desktop",
            "approval_text": "Approved only for read-only inspection.",
            "baseline_head": "d7d1e0d758a64783f4de435f06450be218e8a2bf",
        },
    )
    assert approval.status_code == 200
    approval_payload = approval.json()
    _assert_inert_workspace_payload(approval_payload)
    assert approval_payload["stored"] is True
    assert approval_payload["record_type"] == "ApprovalRecord"
    assert approval_payload["approval"]["approval_mode"] == "one_time"

    run = client.post(
        "/api/plugins/mission-control-governance/workspace/runs/create",
        json={
            "run_id": "run-1",
            "project_id": "project-hermes",
            "lane_request_id": "lane-request-1",
            "approval_id": approval_payload["approval"]["approval_id"],
            "lane_type": "read_only_inspection",
            "title": "Inspect control plane",
            "objective": "Read-only inspection.",
            "status": "requested",
            "allowed_actions": ["read source"],
            "forbidden_actions": ["write files", "dispatch"],
            "baseline_head": "d7d1e0d758a64783f4de435f06450be218e8a2bf",
            "runtime_guard_state": "pass",
            "dispatch_state": False,
            "active_lane_count_at_start": 0,
            "agent_identity": "Jenny",
            "source": "desktop",
            "safety_gate_status": "pass",
            "safety_gate_reasons": ["dispatch false"],
        },
    )
    assert run.status_code == 200
    run_payload = run.json()
    _assert_inert_workspace_payload(run_payload)
    assert run_payload["stored"] is True
    assert run_payload["record_type"] == "RunRecord"
    assert run_payload["run"]["execution_mode"] == "manual_copy"

    report = client.post(
        "/api/plugins/mission-control-governance/workspace/reports/ingest",
        json={
            "run_id": "run-1",
            "approval_id": approval_payload["approval"]["approval_id"],
            "project_id": "project-hermes",
            "lane_request_id": "lane-request-1",
            "summary": "Jenny returned a read-only report.",
            "result": "No mutation occurred.",
            "risks": ["none"],
            "blockers": [],
            "changed_files": [],
            "tests": ["pytest"],
            "next_recommended_lane": "Review UI inbox.",
            "evidence_refs": ["reports/control-plane/report.md"],
            "artifact_refs": ["reports/control-plane/artifact.md"],
            "submitted_by": "Jenny",
            "submitted_from": "desktop_manual_paste",
        },
    )
    assert report.status_code == 200
    report_payload = report.json()
    _assert_inert_workspace_payload(report_payload)
    assert report_payload["stored"] is True
    assert report_payload["record_type"] == "ReportRecord"

    assert len(JsonlRecordStore(plugin_api.record_store_path()).read_all(ApprovalRecord)) == 1
    assert len(JsonlRecordStore(plugin_api.record_store_path()).read_all(RunRecord)) == 1
    assert len(JsonlRecordStore(plugin_api.record_store_path()).read_all(ReportRecord)) == 1


def test_control_plane_validation_rejects_broad_or_executable_approvals(client):
    broad = client.post(
        "/api/plugins/mission-control-governance/workspace/approvals/create",
        json={
            "action_class": "read_only_lane",
            "approval_scope": "*",
            "approved_actions": ["all"],
            "status": "approved",
        },
    )
    assert broad.status_code == 422

    dangerous = client.post(
        "/api/plugins/mission-control-governance/workspace/approvals/create",
        json={
            "action_class": "deploy",
            "approval_scope": "deploy production runtime",
            "approved_actions": ["deploy"],
            "status": "approved",
        },
    )
    assert dangerous.status_code == 422

    proposed = client.post(
        "/api/plugins/mission-control-governance/workspace/approvals/create",
        json={
            "action_class": "deploy",
            "approval_scope": "project-hermes deploy proposal display only",
            "approved_actions": ["deploy"],
            "forbidden_actions": ["execute deploy", "runtime switch"],
            "status": "proposed",
        },
    )
    assert proposed.status_code == 200
    payload = proposed.json()
    _assert_inert_workspace_payload(payload)
    assert payload["approval"]["status"] == "proposed"


def test_control_plane_validation_rejects_invalid_statuses_and_execution_modes(client):
    invalid_approval = client.post(
        "/api/plugins/mission-control-governance/workspace/approvals/create",
        json={
            "action_class": "read_only_lane",
            "approval_scope": "project-hermes read-only inspection",
            "status": "running",
        },
    )
    assert invalid_approval.status_code == 422

    invalid_run = client.post(
        "/api/plugins/mission-control-governance/workspace/runs/create",
        json={
            "project_id": "project-hermes",
            "lane_type": "read_only_inspection",
            "title": "Unsafe run",
            "status": "running",
            "execution_mode": "send_to_jenny_read_only",
        },
    )
    assert invalid_run.status_code == 422

    invalid_report = client.post(
        "/api/plugins/mission-control-governance/workspace/reports/ingest",
        json={
            "project_id": "project-hermes",
            "summary": "bad status",
            "status": "running",
        },
    )
    assert invalid_report.status_code == 422


def test_control_plane_backend_does_not_wire_session_send_or_dispatch():
    source = API_PATH.read_text(encoding="utf-8")
    control_plane_source = source[source.index('@router.get("/workspace/approvals")') : source.index('@router.get("/records")')]
    forbidden = ["session_send", "session-send", "dispatch_task", "send_to_jenny_enabled\": True", "dispatch_enabled\": True"]
    assert not any(fragment in control_plane_source for fragment in forbidden)


def test_session_project_link_record_serializes_deserializes():
    record = SessionProjectLinkRecord(
        link_id="link-1",
        project_id="project-hermes",
        session_id="session-tip",
        lineage_root_id="session-root",
        profile="default",
        source="discord",
        title_snapshot="Mission Control status",
        cwd_snapshot="/tmp/hermes",
        linked_at="2026-06-12T00:00:00Z",
        linked_by="Travis",
        link_method="manual",
        confidence="manual",
        status="active",
        metadata={"manual_copy_only": True},
    )

    payload = record.to_dict()
    assert payload["session_id"] == "session-tip"
    assert payload["lineage_root_id"] == "session-root"
    assert record.durable_session_id == "session-root"

    decoded = SessionProjectLinkRecord.from_dict(payload)
    assert decoded == record
    assert decoded.durable_session_id == "session-root"


def test_workspace_session_project_link_api_and_projection_rules(plugin_api, client, monkeypatch):
    store = JsonlRecordStore(plugin_api.record_store_path())
    store.append(ProjectRecord(project_id="project-hermes", name="Hermes / Mission Control"))
    store.append(ProjectRecord(project_id="project-tool-tally", name="Tool & Tally"))
    monkeypatch.setattr(
        plugin_api,
        "_read_profile_sessions_for_project_links",
        lambda limit: (
            [
                {
                    "id": "session-tip",
                    "_lineage_root_id": "session-root",
                    "profile": "default",
                    "source": "discord",
                    "title": "Mission Control lane",
                    "preview": "Hermes Mission Control work",
                    "cwd": "/home/jenny/.hermes/runtime",
                    "started_at": 1,
                    "last_active": 10,
                    "message_count": 5,
                },
                {
                    "id": "session-tool",
                    "profile": "no-call-estimateready",
                    "source": "discord",
                    "title": "Tool & Tally safety",
                    "preview": "read-only status",
                    "cwd": "",
                    "started_at": 2,
                    "last_active": 9,
                    "message_count": 3,
                },
            ],
            [{"profile": "old-profile", "error": "no such column: s.archived"}],
        ),
    )

    create = client.post(
        "/api/plugins/mission-control-governance/workspace/session-project-links/create",
        json={
            "project_id": "project-hermes",
            "session_id": "session-tip",
            "lineage_root_id": "session-root",
            "profile": "default",
            "source": "discord",
            "title": "Mission Control lane",
        },
    )

    assert create.status_code == 200
    payload = create.json()
    assert payload["trusted_for_execution"] is False
    assert payload["execution_enabled"] is False
    assert payload["manual_copy_only"] is True
    assert payload["send_to_jenny_enabled"] is False
    assert payload["dispatch_enabled"] is False
    assert payload["stored"] is True
    assert payload["record_type"] == "SessionProjectLinkRecord"
    assert payload["session_project_link"]["durable_session_id"] == "session-root"
    assert payload["session_project_link"]["metadata"]["auto_inferred"] is False

    links = client.get("/api/plugins/mission-control-governance/workspace/session-project-links")
    assert links.status_code == 200
    assert links.json()["count"] == 1

    grouped = client.get("/api/plugins/mission-control-governance/workspace/project-sessions")
    assert grouped.status_code == 200
    grouped_payload = grouped.json()
    assert grouped_payload["stored"] is False
    assert grouped_payload["send_to_jenny_enabled"] is False
    assert grouped_payload["dispatch_enabled"] is False
    assert grouped_payload["errors"] == [{"profile": "old-profile", "error": "no such column: s.archived"}]
    groups = {item["project_id"]: item for item in grouped_payload["groups"]}
    assert groups["project-hermes"]["linked_session_count"] == 1
    linked = groups["project-hermes"]["sessions"][0]
    assert linked["session_id"] == "session-tip"
    assert linked["durable_session_id"] == "session-root"
    assert linked["linked_project_id"] == "project-hermes"

    unassigned = groups["unassigned-general"]
    assert len(unassigned["sessions"]) == 1
    assert unassigned["sessions"][0]["session_id"] == "session-tool"
    assert unassigned["sessions"][0]["suggested_project_id"] == "project-tool-tally"
    assert unassigned["sessions"][0]["linked_project_id"] == ""
    assert unassigned["unassigned_suggestion_count"] == 1

    state = client.get("/api/plugins/mission-control-governance/workspace/project-state")
    assert state.status_code == 200
    states = {item["project_id"]: item for item in state.json()["project_states"]}
    assert states["project-hermes"]["linked_session_count"] == 1
    assert states["project-hermes"]["recent_sessions"][0]["session_id"] == "session-tip"
    assert states["project-tool-tally"]["linked_session_count"] == 0


def test_session_project_link_accepts_legacy_desktop_native_method_but_rejects_unknown(client):
    create = client.post(
        "/api/plugins/mission-control-governance/workspace/session-project-links/create",
        json={
            "project_id": "project-hermes",
            "session_id": "session-tip",
            "link_method": "desktop-native-chat",
            "source": "desktop-native-chat",
            "title": "Native project chat",
        },
    )

    assert create.status_code == 200
    record = create.json()["session_project_link"]
    assert record["link_method"] == "manual"
    assert record["metadata"]["normalized_link_method_from"] == "desktop-native-chat"
    assert record["metadata"]["dispatch_enabled"] is False

    invalid = client.post(
        "/api/plugins/mission-control-governance/workspace/session-project-links/create",
        json={
            "project_id": "project-hermes",
            "session_id": "session-tip-2",
            "link_method": "auto-dispatch",
        },
    )

    assert invalid.status_code == 422
    assert invalid.json()["detail"] == "link_method must be manual, suggested, or seeded"


def test_session_project_link_latest_status_wins_and_removed_excluded(plugin_api, client, monkeypatch):
    store = JsonlRecordStore(plugin_api.record_store_path())
    store.append(ProjectRecord(project_id="project-hermes", name="Hermes / Mission Control"))
    store.append(ProjectRecord(project_id="project-tool-tally", name="Tool & Tally"))
    store.append(
        SessionProjectLinkRecord(
            link_id="old-link",
            project_id="project-hermes",
            session_id="session-tip",
            lineage_root_id="session-root",
            status="active",
            linked_at="2026-06-12T00:00:00Z",
        )
    )
    store.append(
        SessionProjectLinkRecord(
            link_id="new-link",
            project_id="project-tool-tally",
            session_id="session-tip",
            lineage_root_id="session-root",
            status="removed",
            linked_at="2026-06-12T00:01:00Z",
        )
    )
    monkeypatch.setattr(
        plugin_api,
        "_read_profile_sessions_for_project_links",
        lambda limit: ([{"id": "session-tip", "_lineage_root_id": "session-root", "title": "Hermes", "started_at": 1, "last_active": 2}], []),
    )

    grouped = client.get("/api/plugins/mission-control-governance/workspace/project-sessions")
    assert grouped.status_code == 200
    groups = {item["project_id"]: item for item in grouped.json()["groups"]}
    assert groups["project-hermes"]["linked_session_count"] == 0
    assert groups["project-tool-tally"]["linked_session_count"] == 0
    assert groups["unassigned-general"]["sessions"][0]["durable_session_id"] == "session-root"

    store.append(
        SessionProjectLinkRecord(
            link_id="latest-link",
            project_id="project-tool-tally",
            session_id="session-tip",
            lineage_root_id="session-root",
            status="active",
            linked_at="2026-06-12T00:02:00Z",
        )
    )
    grouped = client.get("/api/plugins/mission-control-governance/workspace/project-sessions")
    groups = {item["project_id"]: item for item in grouped.json()["groups"]}
    assert groups["project-tool-tally"]["linked_session_count"] == 1
    assert groups["project-tool-tally"]["sessions"][0]["link_record"]["link_id"] == "latest-link"


def test_project_session_projection_counts_links_outside_recent_session_window(plugin_api, client, monkeypatch):
    store = JsonlRecordStore(plugin_api.record_store_path())
    store.append(ProjectRecord(project_id="project-hermes", name="Hermes / Mission Control"))
    store.append(
        SessionProjectLinkRecord(
            link_id="recent-link",
            project_id="project-hermes",
            session_id="session-recent",
            lineage_root_id="root-recent",
            status="active",
            linked_at="2026-06-12T00:01:00Z",
        )
    )
    store.append(
        SessionProjectLinkRecord(
            link_id="older-link",
            project_id="project-hermes",
            session_id="session-older",
            lineage_root_id="root-older",
            status="active",
            linked_at="2026-06-12T00:02:00Z",
        )
    )
    monkeypatch.setattr(
        plugin_api,
        "_read_profile_sessions_for_project_links",
        lambda limit: (
            [
                {
                    "id": "session-recent",
                    "_lineage_root_id": "root-recent",
                    "title": "Recent Hermes work",
                    "started_at": 2,
                    "last_active": 3,
                }
            ],
            [],
        ),
    )

    grouped = client.get("/api/plugins/mission-control-governance/workspace/project-sessions")
    assert grouped.status_code == 200
    grouped_payload = grouped.json()
    groups = {item["project_id"]: item for item in grouped_payload["groups"]}
    assert grouped_payload["active_link_count"] == 2
    assert groups["project-hermes"]["linked_session_count"] == 2
    assert set(groups["project-hermes"]["linked_session_ids"]) == {"root-recent", "root-older"}
    assert [session["session_id"] for session in groups["project-hermes"]["sessions"]] == ["session-recent"]

    state = client.get("/api/plugins/mission-control-governance/workspace/project-state")
    assert state.status_code == 200
    states = {item["project_id"]: item for item in state.json()["project_states"]}
    assert states["project-hermes"]["linked_session_count"] == 2
    assert [session["session_id"] for session in states["project-hermes"]["recent_sessions"]] == ["session-recent"]


def test_project_session_projection_limit_controls_visible_rows(plugin_api, client, monkeypatch):
    store = JsonlRecordStore(plugin_api.record_store_path())
    store.append(ProjectRecord(project_id="project-hermes", name="Hermes / Mission Control"))
    for idx in range(6):
        store.append(
            SessionProjectLinkRecord(
                link_id=f"linked-{idx}",
                project_id="project-hermes",
                session_id=f"session-linked-{idx}",
                lineage_root_id=f"root-linked-{idx}",
                status="active",
                linked_at=f"2026-06-12T00:0{idx}:00Z",
            )
        )

    linked_sessions = [
        {
            "id": f"session-linked-{idx}",
            "_lineage_root_id": f"root-linked-{idx}",
            "title": f"Linked Hermes work {idx}",
            "started_at": idx + 1,
            "last_active": idx + 1,
        }
        for idx in range(6)
    ]
    unassigned_sessions = [
        {
            "id": f"session-general-{idx}",
            "_lineage_root_id": f"root-general-{idx}",
            "title": f"General work {idx}",
            "started_at": idx + 20,
            "last_active": idx + 20,
        }
        for idx in range(12)
    ]
    monkeypatch.setattr(
        plugin_api,
        "_read_profile_sessions_for_project_links",
        lambda limit: (linked_sessions + unassigned_sessions, []),
    )

    grouped = client.get("/api/plugins/mission-control-governance/workspace/project-sessions?limit=6")
    assert grouped.status_code == 200
    groups = {item["project_id"]: item for item in grouped.json()["groups"]}

    assert [session["session_id"] for session in groups["project-hermes"]["sessions"]] == [
        f"session-linked-{idx}" for idx in range(6)
    ]
    assert [session["session_id"] for session in groups["unassigned-general"]["sessions"]] == [
        f"session-general-{idx}" for idx in range(6)
    ]


def test_workspace_project_state_projection_is_read_only_and_derived(plugin_api, client):
    store = JsonlRecordStore(plugin_api.record_store_path())
    store.append(
        ProjectRecord(
            project_id="project-hermes",
            name="Hermes / Mission Control",
            current_goal="Make Mission Control the workspace.",
            next_recommended_lane="Initial lane",
            updated_at="2026-06-10T10:00:00Z",
        )
    )
    store.append(
        ProjectRecord(
            project_id="project-empty",
            name="Empty Project",
            current_goal="Awaiting first lane.",
            next_recommended_lane="Create first lane",
            updated_at="2026-06-10T10:05:00Z",
        )
    )
    store.append(
        LaneRequestRecord(
            lane_request_id="lane-old",
            project_id="project-hermes",
            title="Old lane",
            objective="Older request",
            updated_at="2026-06-10T10:10:00Z",
        )
    )
    store.append(
        LaneRequestRecord(
            lane_request_id="lane-new",
            project_id="project-hermes",
            title="Latest lane",
            objective="Newest request",
            updated_at="2026-06-10T10:20:00Z",
        )
    )
    store.append(
        JennyReportRecord(
            report_id="report-old",
            project_id="project-hermes",
            lane_request_id="lane-old",
            summary="Old report",
            result="Old result",
            risks=("old risk",),
            next_recommended_lane="Old next lane",
            created_at="2026-06-10T10:30:00Z",
        )
    )
    store.append(
        JennyReportRecord(
            report_id="report-new",
            project_id="project-hermes",
            lane_request_id="lane-new",
            summary="Latest report",
            result="Latest result",
            risks=("risk one", "risk two"),
            changed_files=("reports/hermes/status.md",),
            next_recommended_lane="Derived next lane",
            created_at="2026-06-10T10:40:00Z",
        )
    )
    before = len(store.read_all())

    response = client.get("/api/plugins/mission-control-governance/workspace/project-state")

    assert response.status_code == 200
    payload = response.json()
    assert payload["trusted_for_execution"] is False
    assert payload["execution_enabled"] is False
    assert payload["manual_copy_only"] is True
    assert payload["send_to_jenny_enabled"] is False
    assert payload["dispatch_enabled"] is False
    assert payload["stored"] is False
    assert len(store.read_all()) == before

    states = {item["project_id"]: item for item in payload["project_states"]}
    hermes_state = states["project-hermes"]
    assert hermes_state["current_goal"] == "Make Mission Control the workspace."
    assert hermes_state["latest_lane_title"] == "Latest lane"
    assert hermes_state["latest_report_summary"] == "Latest report"
    assert hermes_state["latest_result"] == "Latest result"
    assert hermes_state["risks_blockers"] == ["risk one", "risk two"]
    assert hermes_state["next_recommended_lane"] == "Derived next lane"
    assert hermes_state["last_updated"] == "2026-06-10T10:40:00Z"
    assert hermes_state["latest_activity_at"] == "2026-06-10T10:40:00Z"
    assert hermes_state["latest_activity_source"] == "report"
    assert hermes_state["has_real_report"] is True
    assert hermes_state["report_contract"] == {
        "state": "incomplete",
        "complete": False,
        "missing_fields": ["tests"],
        "required_fields": ["summary", "result", "risks/blockers", "evidence", "tests", "next lane"],
        "display_only": True,
        "trusted_for_execution": False,
    }
    assert hermes_state["missing_state_fields"] == ["report_contract"]
    assert hermes_state["artifact_links"] == ["reports/hermes/status.md"]

    empty_state = states["project-empty"]
    assert empty_state["latest_lane_request"] == {}
    assert empty_state["latest_jenny_report"] == {}
    assert empty_state["next_recommended_lane"] == "Create first lane"
    assert empty_state["has_real_report"] is False
    assert empty_state["latest_activity_source"] == "project"
    assert empty_state["missing_state_fields"] == [
        "latest_lane",
        "latest_jenny_report",
        "latest_result",
        "risks_blockers",
        "artifact_links",
        "report_contract",
    ]
    assert empty_state["report_contract"]["state"] == "missing_report"
    assert empty_state["report_contract"]["missing_fields"] == ["report"]


def test_workspace_record_api_rejects_unsafe_oversized_and_malformed_payloads(client):
    assert client.post(
        "/api/plugins/mission-control-governance/workspace/projects/create",
        data="not-json",
        headers={"content-type": "application/json"},
    ).status_code == 400
    assert client.post(
        "/api/plugins/mission-control-governance/workspace/projects/create",
        json={"name": "x" * 1300},
    ).status_code == 422
    assert client.post(
        "/api/plugins/mission-control-governance/workspace/lane-requests/create",
        json={"project_id": "project-hermes"},
    ).status_code == 422
    assert client.post(
        "/api/plugins/mission-control-governance/workspace/reports/create",
        json={"project_id": "project-hermes"},
    ).status_code == 422
    assert client.post(
        "/api/plugins/mission-control-governance/workspace/reports/create",
        json={"project_id": "project-hermes", "summary": "x" * 5000},
    ).status_code == 422


def _seed_records(path: Path) -> None:
    store = JsonlRecordStore(path)
    goal = GoalContract(
        goal_id="goal-1",
        statement="Keep governance records inert.",
        success_criteria=("read-only summary renders",),
        constraints=("no execution",),
    )
    control = TaskControlEnvelope(
        active_lane="PR-B Mission Control governance plugin MVP",
        mode="code/test only",
        allowed_actions=("read records",),
        forbidden_actions=("execute tools", "load transcripts"),
        current_repo="/tmp/hermes",
        stop_condition="Stop before commit.",
    )
    store.append(goal)
    store.append(control)
    store.append(
        ApprovalSlice(
            approval_id="approval-1",
            lane=control.active_lane,
            mode=control.mode,
            approved_actions=("create read-only plugin",),
            forbidden_actions=("execute approval",),
            approver="Travis",
            approved_at="2026-06-04T00:00:00Z",
        )
    )
    store.append(
        MissionBrief(
            mission_id="mission-1",
            title="Governance plugin MVP",
            created_at="2026-06-04T00:01:00Z",
            goal=goal,
            control=control,
        )
    )


def _seed_goal_records(path: Path, count: int) -> None:
    store = JsonlRecordStore(path)
    for index in range(count):
        store.append(
            GoalContract(
                goal_id=f"goal-{index}",
                statement=f"Keep governance record {index} inert.",
                metadata={
                    "raw_context": "secret raw governance context",
                    "transcript": "secret governance transcript",
                },
            )
        )



def test_verifier_workflow_evaluate_only_does_not_store_evidence(plugin_api, client):
    response = client.post(
        "/api/plugins/mission-control-governance/verifier-workflow/evaluate",
        json={
            "pr_merge_requested": True,
            "independent_verification_present": False,
            "verification_approved": False,
            "source": "unit-test",
            "lane_id": "lane-no-store",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["stored"] is False
    assert payload["record"] is None
    assert payload["would_block"] is True
    assert JsonlRecordStore(plugin_api.record_store_path()).read_all(VerifierWorkflowEvidenceRecord) == ()


def test_verifier_workflow_evaluate_and_record_appends_one_sanitized_record(plugin_api, client):
    body = {
        "evaluate_and_record": True,
        "pr_merge_requested": True,
        "independent_verification_present": False,
        "verification_approved": False,
        "source": "operator token=secret-value",
        "lane_id": "/home/jenny/.hermes/private/very/long/path/to/worktree",
        "task_id": "task-1 sk-test-secretvalue",
        "domain_id": "mission-control",
        "action_class": "pr_merge",
        "observed_state_raw": {"secret": "must not be stored"},
    }

    response = client.post(
        "/api/plugins/mission-control-governance/verifier-workflow/evaluate",
        json=body,
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["stored"] is True
    assert payload["dry_run_only"] is True
    assert payload["enforces_runtime"] is False
    record = payload["record"]
    assert record["guard_type"] == "verifier_workflow"
    assert record["decision_state"] == "would_block"
    assert record["would_block"] is True
    assert record["dry_run_only"] is True
    assert record["enforces_runtime"] is False
    assert record["action_class"] == "pr_merge"
    assert "merge PR" in record["blocked_actions"]
    assert "approved independent verification" in record["required_approvals"]
    lowered = str(record).lower()
    assert "secret-value" not in lowered
    assert "sk-test-secretvalue" not in lowered
    assert "/home/jenny" not in lowered
    assert "observed_state_raw" not in lowered
    assert "must not be stored" not in lowered

    records = JsonlRecordStore(plugin_api.record_store_path()).read_all(VerifierWorkflowEvidenceRecord)
    assert len(records) == 1
    assert records[0].record_id == record["record_id"]


def test_verifier_workflow_recent_evidence_endpoint_is_bounded_and_safe(plugin_api, client):
    store = JsonlRecordStore(plugin_api.record_store_path())
    for index in range(12):
        store.append(
            VerifierWorkflowEvidenceRecord(
                record_id=f"record-{index}",
                created_at=f"2026-06-08T00:{index:02d}:00Z",
                lane_id=f"lane-{index}",
                action_class="pr_merge",
                decision_state="would_block",
                would_block=True,
                reasons=("safe compact reason",),
                blocked_actions=("merge PR",),
                required_approvals=("approved independent verification",),
            )
        )

    response = client.get("/api/plugins/mission-control-governance/verifier-workflow/evidence?limit=20")

    assert response.status_code == 200
    payload = response.json()
    assert payload["trusted_for_execution"] is False
    assert payload["inert_context_only"] is True
    assert payload["execution_enabled"] is False
    assert payload["dry_run_only"] is True
    assert payload["enforcement_enabled"] is False
    assert payload["count"] == 10
    assert [item["record_id"] for item in payload["records"]] == [f"record-{index}" for index in range(2, 12)]
    assert all("observed_state" not in item for item in payload["records"])


def test_pr_merge_verifier_gate_policy_endpoint_is_inert(client):
    response = client.get("/api/plugins/mission-control-governance/pr-merge-verifier-gate")

    assert response.status_code == 200
    payload = response.json()
    assert payload["trusted_for_execution"] is False
    assert payload["inert_context_only"] is True
    assert payload["execution_enabled"] is False
    assert payload["enforcement_enabled"] is False
    assert payload["dry_run_only"] is True
    assert payload["display_only"] is True
    assert payload["gate"]["gate_id"] == "pr_merge_verifier_gate_v1"
    assert payload["gate"]["future_enforcement_boundary"]["does_not_call_github"] is True


def test_pr_merge_verifier_gate_evaluate_valid_state_stores_nothing(client):
    body = {
        "repo": "Travisaggie04/hermes-agent",
        "pr_number": "36",
        "base_branch": "pr-base/v2026.5.29.2-mission-control-records",
        "head_commit": "abc123",
        "packet_hash": "sha256:packet",
        "implementer_id": "jenny-implementer",
        "verifier_id": "jenny-verifier",
        "verifier_evidence_record_id": "evidence-1",
        "verifier_evidence": {
            "record_id": "evidence-1",
            "guard_type": "verifier_workflow",
            "action_class": "pr_merge",
            "repo": "Travisaggie04/hermes-agent",
            "pr_number": "36",
            "base_branch": "pr-base/v2026.5.29.2-mission-control-records",
            "head_commit": "abc123",
            "packet_hash": "sha256:packet",
            "implementer_id": "jenny-implementer",
            "verifier_id": "jenny-verifier",
            "would_block": False,
            "blocked_actions": [],
            "dry_run_only": True,
            "enforces_runtime": False,
            "observed_state_raw": {"secret": "must not be exposed"},
        },
    }

    response = client.post("/api/plugins/mission-control-governance/pr-merge-verifier-gate/evaluate", json=body)

    assert response.status_code == 200
    payload = response.json()
    assert payload["stored"] is False
    assert payload["decision_state"] == "warn"
    assert payload["would_block"] is False
    assert payload["dry_run_only"] is True
    assert payload["enforces_runtime"] is False
    assert "observed_state_raw" not in str(payload)
    assert "must not be exposed" not in str(payload)


def test_pr_merge_verifier_gate_evaluate_hash_mismatch_blocks(client):
    body = {
        "repo": "Travisaggie04/hermes-agent",
        "pr_number": "36",
        "base_branch": "pr-base/v2026.5.29.2-mission-control-records",
        "head_commit": "abc123",
        "packet_hash": "sha256:packet",
        "implementer_id": "jenny-implementer",
        "verifier_id": "jenny-verifier",
        "verifier_evidence_record_id": "evidence-1",
        "verifier_evidence": {
            "record_id": "evidence-1",
            "guard_type": "verifier_workflow",
            "action_class": "pr_merge",
            "repo": "Travisaggie04/hermes-agent",
            "pr_number": "36",
            "base_branch": "pr-base/v2026.5.29.2-mission-control-records",
            "head_commit": "abc123",
            "packet_hash": "sha256:different",
            "implementer_id": "jenny-implementer",
            "verifier_id": "jenny-verifier",
            "would_block": False,
            "blocked_actions": [],
            "dry_run_only": True,
            "enforces_runtime": False,
        },
    }

    response = client.post("/api/plugins/mission-control-governance/pr-merge-verifier-gate/evaluate", json=body)

    assert response.status_code == 200
    payload = response.json()
    assert payload["stored"] is False
    assert payload["would_block"] is True
    assert "verifier evidence packet_hash mismatch" in payload["reasons"]
    assert payload["dry_run_only"] is True
    assert payload["enforces_runtime"] is False





def _valid_pr_merge_visibility_body() -> dict[str, object]:
    return {
        "config": {
            "mission_control": {
                "enforcement": {"pr_merge_verifier_gate_enabled": True},
            },
        },
        "merge_packet": {
            "repo": "Travisaggie04/hermes-agent",
            "pr_number": "38",
            "base_branch": "pr-base/v2026.5.29.2-mission-control-records",
            "head_commit": "abc123",
            "packet_hash": "sha256:packet",
            "implementer_id": "jenny-implementer",
            "verifier_id": "jenny-verifier",
            "verifier_evidence_record_id": "evidence-38",
            "verifier_evidence": {
                "record_id": "evidence-38",
                "guard_type": "verifier_workflow",
                "action_class": "pr_merge",
                "repo": "Travisaggie04/hermes-agent",
                "pr_number": "38",
                "base_branch": "pr-base/v2026.5.29.2-mission-control-records",
                "head_commit": "abc123",
                "packet_hash": "sha256:packet",
                "implementer_id": "jenny-implementer",
                "verifier_id": "jenny-verifier",
                "would_block": False,
                "blocked_actions": [],
                "dry_run_only": True,
                "enforces_runtime": False,
            },
        },
    }


def test_pr_merge_gate_visibility_missing_packet_is_inert_advisory(client):
    response = client.post(
        "/api/plugins/mission-control-governance/pr-merge-verifier-gate/visibility",
        json={},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["trusted_for_execution"] is False
    assert payload["inert_context_only"] is True
    assert payload["execution_enabled"] is False
    assert payload["enforcement_enabled"] is False
    assert payload["visibility_only"] is True
    assert payload["label"] == "Visibility only. No approval, merge, deploy, or enforcement."
    assert payload["enabled"] is False
    assert payload["advisory_only"] is True
    assert payload["stop_merge_lane"] is False
    assert payload["would_block"] is False
    assert payload["decision_state"] == "unknown"
    assert "caller-supplied PR merge packet state is incomplete" in payload["reasons"]
    assert payload["missing_requirements"]
    assert payload["stored"] is False


def test_pr_merge_gate_visibility_valid_packet_shows_fields_and_allows(client):
    response = client.post(
        "/api/plugins/mission-control-governance/pr-merge-verifier-gate/visibility",
        json=_valid_pr_merge_visibility_body(),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["visibility_only"] is True
    assert payload["enabled"] is True
    assert payload["advisory_only"] is False
    assert payload["would_block"] is False
    assert payload["stop_merge_lane"] is False
    assert payload["repo"] == "Travisaggie04/hermes-agent"
    assert payload["pr_number"] == "38"
    assert payload["base_branch"] == "pr-base/v2026.5.29.2-mission-control-records"
    assert payload["head_commit"] == "abc123"
    assert payload["packet_hash"] == "sha256:packet"
    assert payload["evidence_record_id"] == "evidence-38"
    assert payload["blocked_actions"] == []
    assert payload["dry_run_only"] is True
    assert payload["enforces_runtime"] is False


def test_pr_merge_gate_visibility_default_false_never_stops_even_when_would_block(client):
    body = _valid_pr_merge_visibility_body()
    body["config"] = {}
    body["merge_packet"].pop("verifier_evidence")

    response = client.post(
        "/api/plugins/mission-control-governance/pr-merge-verifier-gate/visibility",
        json=body,
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["enabled"] is False
    assert payload["advisory_only"] is True
    assert payload["would_block"] is True
    assert payload["stop_merge_lane"] is False
    assert "missing verifier evidence" in payload["reasons"]
    assert "missing verifier evidence" in payload["missing_requirements"]


def test_pr_merge_gate_visibility_hash_mismatch_is_visible(client):
    body = _valid_pr_merge_visibility_body()
    body["merge_packet"]["verifier_evidence"]["packet_hash"] = "sha256:different"

    response = client.post(
        "/api/plugins/mission-control-governance/pr-merge-verifier-gate/visibility",
        json=body,
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["would_block"] is True
    assert payload["stop_merge_lane"] is True
    assert "verifier evidence packet_hash mismatch" in payload["reasons"]
    assert payload["packet_hash"] == "sha256:packet"
    assert payload["evidence_record_id"] == "evidence-38"


def test_pr_merge_gate_visibility_has_no_live_inspection_or_execution(plugin_api, client):
    response = client.post(
        "/api/plugins/mission-control-governance/pr-merge-verifier-gate/visibility",
        json=_valid_pr_merge_visibility_body(),
    )
    source = "\n".join(
        inspect.getsource(item)
        for item in (
            plugin_api.pr_merge_verifier_gate_visibility,
            plugin_api._read_json_object_body,
            plugin_api._compact_pr_merge_gate_config,
            plugin_api._compact_pr_merge_gate_state,
            plugin_api._pr_merge_visibility_payload,
        )
    )

    assert response.status_code == 200
    for forbidden in (
        "subprocess",
        "Popen",
        "os.system",
        "systemctl",
        "requests",
        "httpx",
        "urllib",
        "github",
        "gh pr",
        "JsonlRecordStore",
        "record_store_path",
        ".append(",
        ".write(",
        "open(",
        "worker",
        "model_router",
        "queue",
    ):
        assert forbidden not in source


def test_plugin_manifest_loads():
    manifest = yaml.safe_load((PLUGIN_DIR / "plugin.yaml").read_text())
    assert manifest["name"] == "mission-control-governance"
    assert manifest["version"]
    assert manifest.get("hooks") in (None, [])
    assert manifest.get("provides_tools") in (None, [])

    dashboard = yaml.safe_load((PLUGIN_DIR / "dashboard" / "manifest.json").read_text())
    assert dashboard["name"] == "mission-control-governance"
    assert dashboard["label"] == "Mission Control"
    assert dashboard["tab"]["path"] == "/mission-control-governance"
    assert dashboard["entry"] == "dist/index.js"
    assert dashboard["api"] == "plugin_api.py"


def test_app_routes_mission_control_alias_to_governance_tab():
    app_source = (REPO_ROOT / "web" / "src" / "App.tsx").read_text()

    assert "function MissionControlRedirect()" in app_source
    assert 'return <Navigate to="/mission-control-governance" replace />;' in app_source
    assert '"/mission-control": MissionControlRedirect' in app_source
    assert '"/mission-control-governance":' not in app_source


def test_lane_handoff_draft_builder_bundle_is_inert_and_copy_only():
    bundle = (PLUGIN_DIR / "dashboard" / "dist" / "index.js").read_text()
    styles = (PLUGIN_DIR / "dashboard" / "dist" / "style.css").read_text()

    for required in (
        "Start New Lane / Draft Handoff",
        "Lane Handoff Draft Builder",
        "/api/plugins/mission-control-governance/workspace-status",
        "Manual transport only",
        "paste into Discord. This does not start work.",
        "Draft packet only. This is not an active lane.",
        "STOP: Mission Control stale-context warnings are present",
        "Do not proceed until this is resolved.",
        "Lane name",
        "Mode",
        "Objective",
        "Allowed actions",
        "Forbidden actions",
        "Stop conditions",
        "Expected report format",
        "Target repo/path/branch optional",
        "Notes optional",
        "Active lane:",
        "Accepted baseline:",
        "Rollback baseline:",
        "max_active_lane=",
        "dispatch_in_gateway=false",
        "display_only=true",
        "dry_run_only=true",
        "execution_enabled=false",
        "model_routing=false",
        "queue_mutation=false",
        "waha_mutation=false",
        "enforcement_enabled=false",
        "record_write_enabled=false",
        "navigator.clipboard.writeText(prompt)",
        'h("textarea"',
        "mcg-handoff-textarea",
        "mcg-handoff-field-wide",
        "Copy prompt",
        'role: "link"',
    ):
        assert required in bundle

    assert bundle.count('h("input"') >= 2
    assert bundle.count('h("textarea"') >= 2
    assert bundle.count("multiline: true") >= 6

    for required_style in (
        ".mcg-handoff-grid",
        ".mcg-handoff-input",
        ".mcg-handoff-textarea",
        "min-height: 96px",
        "resize: vertical",
        ".mcg-handoff-output",
        ".mcg-handoff-prompt",
        ".mcg-copy-control",
        "@media (max-width: 860px)",
    ):
        assert required_style in styles

    for forbidden in (
        "/dispatch",
        "/execute",
        "/restart",
        "/deploy",
        "/merge",
        "/api/plugins/kanban/tasks",
        "OperatingWorkspaceHandoffRecord",
        "JsonlRecordStore",
        "record_store_path",
        ".append(",
        ".write(",
        "fetch('/",
        'fetch("/',
        "setInterval",
        "setTimeout",
        "localStorage",
        "sessionStorage",
    ):
        assert forbidden not in bundle


def test_project_workspace_records_pr_a_bundle_is_manual_copy_only():
    bundle = (PLUGIN_DIR / "dashboard" / "dist" / "index.js").read_text()
    styles = (PLUGIN_DIR / "dashboard" / "dist" / "style.css").read_text()

    for required in (
        "Project Workspace",
        "Hermes / Mission Control",
        "Long-form Video",
        "Shorts Video",
        "Tool & Tally",
        "Waha Work",
        "status",
        "current goal",
        "last report summary",
        "next recommended lane",
        "mistakes/guards",
        "Copy prompt",
        "Save lane request draft",
        "Saved lane request drafts",
        "Send to Jenny",
        "disabled. No dispatch, queue, Waha, model routing, enforcement, automatic session send, storage, timers, or hidden workers.",
        "WORKSPACE_PROJECTS_URL",
        "WORKSPACE_PROJECT_BRIEFS_URL",
        "WORKSPACE_PROJECT_BRIEF_CREATE_URL",
        "WORKSPACE_CHALLENGE_REVIEWS_URL",
        "WORKSPACE_CHALLENGE_REVIEW_CREATE_URL",
        "WORKSPACE_LANE_REQUESTS_URL",
        "WORKSPACE_REPORTS_URL",
        "WORKSPACE_REPORT_CREATE_URL",
        "WORKSPACE_PROJECT_STATE_URL",
        "Phone Decision Queue",
        "Project Brief Intake",
        "Jenny Challenge Gate",
        "Save project brief",
        "Save challenge review",
        "Create a Jenny challenge review before saving a lane request draft.",
        "Latest challenge review is ",
        "clear_and_safe",
        "wrong_approach_likely",
        "needs_spec_first",
        "Challenge blocked",
        "Needs approval",
        "Lane draft ok",
        "Use this from laptop or phone",
        "Use this before a lane draft when your request may be vague, too broad, unsafe, or the wrong approach.",
        "Project State Projection",
        "Derived read-only view from ProjectRecord, LaneRequestRecord, and JennyReportRecord",
        "latest lane request",
        "latest Jenny report summary",
        "latest result",
        "risks/blockers",
        "last updated",
        "Manual Jenny Report Inbox",
        "Save Jenny report manually",
        "Saved Jenny reports",
        "Paste Jenny",
        "Manual transport only",
        "This does not start work.",
        "Draft packet only. This is not an active lane.",
        "Read-only/manual-copy Mission Control project workspace lane.",
        "Use this project card as context",
        "No dispatch, queue, Waha, model routing, enforcement, automatic session send, storage, timers, or hidden workers.",
        "PROJECT_WORKSPACE_CARDS",
        "ProjectWorkspacePanel",
        "ProjectWorkspaceCard",
        "Project Rooms",
        "Project Room: ",
        "Project Records: ",
        "Project-only workspace for requests, drafts, sessions, and reports.",
        "Ask Jenny / Propose Work",
        "Project-room composer. First version creates safe records and phone-safe packets only; no direct send path.",
        "Copy phone-safe packet",
        "Save challenge draft",
        "Save read-only lane draft",
        "Phone-safe packet",
        "1900",
        "makePhoneSafeProjectPrompt",
        "Project room request:",
        "Project Sessions",
        "No linked sessions for this project yet.",
    ):
        assert required in bundle

    assert bundle.count('name: "Hermes / Mission Control"') == 1
    assert bundle.count('name: "Long-form Video"') == 1
    assert bundle.count('name: "Shorts Video"') == 1
    assert bundle.count('name: "Tool & Tally"') == 1
    assert bundle.count('name: "Waha Work"') == 1
    assert bundle.count("name: ") == 5

    for required_style in (
        ".mcg-project-workspace-card",
        ".mcg-project-workspace-body",
        ".mcg-project-grid",
        ".mcg-project-card",
        ".mcg-project-card-head",
        ".mcg-project-prompt-preview",
        ".mcg-decision-queue",
        ".mcg-decision-row",
        ".mcg-project-intake-grid",
        ".mcg-project-intake-form",
        ".mcg-challenge-gate-form",
        ".mcg-project-room-layout",
        ".mcg-project-room-rail",
        ".mcg-project-room-shell",
        ".mcg-project-room-composer",
        ".mcg-project-room-packet",
        ".mcg-project-room-tab",
        ".mcg-manual-report-inbox",
        ".mcg-project-report-list",
        "grid-template-columns: repeat(2, minmax(0, 1fr))",
        "@media (max-width: 760px)",
    ):
        assert required_style in styles

    for forbidden in (
        "/dispatch",
        "/execute",
        "/restart",
        "/deploy",
        "/merge",
        "/api/plugins/kanban/tasks",
        "OperatingWorkspaceHandoffRecord",
        "JsonlRecordStore",
        "record_store_path",
        ".append(",
        ".write(",
        "localStorage",
        "sessionStorage",
        "setInterval",
        "setTimeout",
    ):
        assert forbidden not in bundle


def test_project_workspace_latest_brief_and_challenge_review_use_newest_record():
    bundle = (PLUGIN_DIR / "dashboard" / "dist" / "index.js").read_text()

    assert "return filtered.length ? filtered[filtered.length - 1] : null;" in bundle
    assert "const latestReview = latestForProject(records.challengeReviews.map(challengeReviewFromRecord).filter(Boolean), selectedId);" in bundle
    assert 'if (latestReview.decision_state !== "clear_and_safe")' in bundle
    assert "Latest challenge review is " in bundle
    assert "Create a Jenny challenge review before saving a lane request draft." in bundle

    old_clear_new_unsafe = [
        {"project_id": "project-hermes", "decision_state": "clear_and_safe"},
        {"project_id": "project-hermes", "decision_state": "unsafe"},
    ]
    old_unsafe_new_clear = [
        {"project_id": "project-hermes", "decision_state": "unsafe"},
        {"project_id": "project-hermes", "decision_state": "clear_and_safe"},
    ]

    assert old_clear_new_unsafe[-1]["decision_state"] == "unsafe"
    assert old_unsafe_new_clear[-1]["decision_state"] == "clear_and_safe"


def test_autonomy_readiness_ledger_bundle_is_static_display_only():
    bundle = (PLUGIN_DIR / "dashboard" / "dist" / "index.js").read_text()

    for required in (
        "Autonomy Readiness Ledger",
        "Display-only ledger. This is not an enforcement surface.",
        "mistake / near miss",
        "root cause",
        "caught by Jenny",
        "guardrail",
        "remaining manual dependency",
        "autonomy impact",
        "fixed",
        "open",
        "accepted risk",
        "dashboard import-binding verifier false rollback",
        "unapproved skill/reference update during live repair",
        "stale dashboard session token printed during final verification",
        "token rotation remediation",
        "PR #48 / lane-handoff builder safely deployed",
        "display_only=true",
        "dry_run_only=true",
        "execution_enabled=false",
        "dispatch_in_gateway=false",
        "model_routing=false",
        "queue_mutation=false",
        "waha_mutation=false",
        "enforcement_enabled=false",
        "record_write_enabled=false",
        "runtime worktree used as PR checkout",
        "runtime/worktree guard",
    ):
        assert required in bundle

    for forbidden in (
        "/autonomy-readiness-ledger",
        "/dispatch",
        "/execute",
        "/restart",
        "/deploy",
        "/merge",
        "/api/plugins/kanban/tasks",
        "JsonlRecordStore",
        "OperatingWorkspaceHandoffRecord",
        "AutonomyReadinessLedgerRecord",
        "record_store_path",
        ".append(",
        ".write(",
        "fetch('",
        'fetch("',
        "setInterval",
        "setTimeout",
        "localStorage",
        "sessionStorage",
    ):
        assert forbidden not in bundle


def test_dashboard_bundle_shows_runtime_worktree_guard_blocker_labels():
    bundle = (PLUGIN_DIR / "dashboard" / "dist" / "index.js").read_text()
    styles = (PLUGIN_DIR / "dashboard" / "dist" / "style.css").read_text()

    for required in (
        "Runtime Worktree Guard",
        "dev_worktree_is_live_runtime",
        "dev_worktree_is_rollback_runtime",
        "runtime_disk_head_mismatch",
        "runtime_on_feature_branch",
        "rollback_disk_head_mismatch",
        "requested_dev_worktree_missing",
        "mcg-runtime-guard-blockers",
    ):
        assert required in bundle

    assert ".mcg-runtime-guard-blockers" in styles


def test_api_routes_are_get_only(plugin_api, client):
    methods_by_path = {
        route.path: route.methods
        for route in plugin_api.router.routes
        if getattr(route, "path", "").startswith("/")
    }
    assert methods_by_path == {
        "/health": {"GET"},
        "/summary": {"GET"},
        "/start-gate": {"GET"},
        "/start-gate/evaluate": {"POST"},
        "/lane-preflight/evaluate": {"POST"},
        "/action-policy": {"GET"},
        "/action-policy/evaluate": {"POST"},
        "/global-resource-guard": {"GET"},
        "/global-resource-guard/evaluate": {"POST"},
        "/storage-guard": {"GET"},
        "/storage-guard/evaluate": {"POST"},
        "/storage-guard/cleanup-manifest": {"POST"},
        "/verifier-workflow": {"GET"},
        "/pr-merge-verifier-gate": {"GET"},
        "/workspace-status": {"GET"},
        "/workspace-status/preview": {"POST"},
        "/workspace/runtime-provenance/preview": {"POST"},
        "/workspace/autonomy-eligibility/preview": {"POST"},
        "/workspace/scoped-pr-eligibility/preview": {"POST"},
        "/workspace/tool-permissions/preview": {"POST"},
        "/workspace/execution-packet/preview": {"POST"},
        "/pr-merge-verifier-gate/evaluate": {"POST"},
        "/pr-merge-verifier-gate/visibility": {"POST"},
        "/verifier-workflow/evidence": {"GET"},
        "/verifier-workflow/evaluate": {"POST"},
        "/model-registry": {"GET"},
        "/domain-governance": {"GET"},
        "/task-control-envelopes": {"GET"},
        "/start-gate-checks": {"GET"},
        "/approval-slices": {"GET"},
        "/evidence-cards": {"GET"},
        "/operator-actions": {"GET"},
        "/workspace/projects": {"GET"},
        "/workspace/projects/create": {"POST"},
        "/workspace/project-briefs": {"GET"},
        "/workspace/project-briefs/create": {"POST"},
        "/workspace/project-templates": {"GET"},
        "/workspace/projects/seed-defaults": {"POST"},
        "/workspace/challenge-reviews": {"GET"},
        "/workspace/challenge-reviews/create": {"POST"},
        "/workspace/lane-requests": {"GET"},
        "/workspace/lane-requests/create": {"POST"},
        "/workspace/reports": {"GET"},
        "/workspace/reports/create": {"POST"},
        "/workspace/jenny-bridge/outbox": {"GET"},
        "/workspace/jenny-bridge/pending": {"GET"},
        "/workspace/jenny-bridge/poller-status": {"GET"},
        "/workspace/jenny-reply-reviews": {"GET"},
        "/workspace/jenny-reply-reviews/create": {"POST"},
        "/workspace/github-bridge/status": {"GET"},
        "/workspace/async-agent-status": {"GET"},
        "/workspace/github-bridge/outbox/create": {"POST"},
        "/workspace/github-bridge/answer-once": {"POST"},
        "/workspace/profile-memory-storage": {"GET"},
        "/workspace/jenny-bridge/outbox/create": {"POST"},
        "/workspace/jenny-bridge/inbox": {"GET"},
        "/workspace/jenny-bridge/inbox/create": {"POST"},
        "/workspace/approvals": {"GET"},
        "/workspace/approvals/create": {"POST"},
        "/workspace/runs": {"GET"},
        "/workspace/runs/create": {"POST"},
        "/workspace/report-inbox": {"GET"},
        "/workspace/reports/ingest": {"POST"},
        "/workspace/child-runs": {"GET"},
        "/workspace/child-runs/create": {"POST"},
        "/workspace/worker-node-runs": {"GET"},
        "/workspace/worker-node-runs/create": {"POST"},
        "/workspace/session-project-links": {"GET"},
        "/workspace/session-project-links/create": {"POST"},
        "/workspace/project-sessions": {"GET"},
        "/workspace/project-state": {"GET"},
        "/records": {"GET"},
        "/schema": {"GET"},
        "/records/{record_index}": {"GET"},
    }

    for path in (
        "/health",
        "/summary",
        "/start-gate",
        "/action-policy",
        "/global-resource-guard",
        "/storage-guard",
        "/verifier-workflow",
        "/pr-merge-verifier-gate",
        "/workspace-status",
        "/verifier-workflow/evidence",
        "/model-registry",
        "/domain-governance",
        "/task-control-envelopes",
        "/start-gate-checks",
        "/approval-slices",
        "/evidence-cards",
        "/operator-actions",
        "/workspace/projects",
        "/workspace/project-briefs",
        "/workspace/project-templates",
        "/workspace/challenge-reviews",
        "/workspace/lane-requests",
        "/workspace/reports",
        "/workspace/profile-memory-storage",
        "/workspace/approvals",
        "/workspace/runs",
        "/workspace/report-inbox",
        "/workspace/child-runs",
        "/workspace/worker-node-runs",
        "/workspace/session-project-links",
        "/workspace/project-sessions",
        "/workspace/project-state",
        "/records",
        "/schema",
        "/records/0",
    ):
        for method in ("post", "put", "patch", "delete"):
            response = getattr(client, method)(
                f"/api/plugins/mission-control-governance{path}"
            )
            assert response.status_code == 405

    for method in ("get", "put", "patch", "delete"):
        response = getattr(client, method)(
            "/api/plugins/mission-control-governance/start-gate/evaluate"
        )
        assert response.status_code == 405
        response = getattr(client, method)(
            "/api/plugins/mission-control-governance/lane-preflight/evaluate"
        )
        assert response.status_code == 405
        response = getattr(client, method)(
            "/api/plugins/mission-control-governance/action-policy/evaluate"
        )
        assert response.status_code == 405
        response = getattr(client, method)(
            "/api/plugins/mission-control-governance/global-resource-guard/evaluate"
        )
        assert response.status_code == 405
        response = getattr(client, method)(
            "/api/plugins/mission-control-governance/storage-guard/evaluate"
        )
        assert response.status_code == 405
        response = getattr(client, method)(
            "/api/plugins/mission-control-governance/storage-guard/cleanup-manifest"
        )
        assert response.status_code == 405
        response = getattr(client, method)(
            "/api/plugins/mission-control-governance/verifier-workflow/evaluate"
        )
        assert response.status_code == 405
        response = getattr(client, method)(
            "/api/plugins/mission-control-governance/pr-merge-verifier-gate/evaluate"
        )
        assert response.status_code == 405
        response = getattr(client, method)(
            "/api/plugins/mission-control-governance/pr-merge-verifier-gate/visibility"
        )
        assert response.status_code == 405
        response = getattr(client, method)(
            "/api/plugins/mission-control-governance/workspace-status/preview"
        )
        assert response.status_code == 405


def test_health_is_read_only_and_inert(client):
    response = client.get("/api/plugins/mission-control-governance/health")

    assert response.status_code == 200
    assert response.json() == {
        "ok": True,
        "plugin": "mission-control-governance",
        "trusted_for_execution": False,
        "inert_context_only": True,
        "execution_enabled": False,
    }


def test_summary_and_records_return_inert_fields(plugin_api, client):
    _seed_records(plugin_api.record_store_path())

    summary = client.get("/api/plugins/mission-control-governance/summary").json()
    assert summary["trusted_for_execution"] is False
    assert summary["inert_context_only"] is True
    assert summary["execution_enabled"] is False
    assert summary["record_count"] == 4
    assert summary["record_types"] == {
        "ApprovalSlice": 1,
        "GoalContract": 1,
        "MissionBrief": 1,
        "TaskControlEnvelope": 1,
    }
    assert summary["latest_mission_title"] == "Governance plugin MVP"

    records = client.get("/api/plugins/mission-control-governance/records").json()
    assert records["trusted_for_execution"] is False
    assert records["inert_context_only"] is True
    assert records["execution_enabled"] is False
    assert records["count"] == 4
    assert records["store_status"] == "ok"
    assert records["error"] is None
    assert [item["record_type"] for item in records["records"]] == [
        "GoalContract",
        "TaskControlEnvelope",
        "ApprovalSlice",
        "MissionBrief",
    ]
    assert records["records"][0]["record"]["statement"] == "Keep governance records inert."


def test_records_defaults_to_latest_bounded_response(plugin_api, client):
    _seed_goal_records(plugin_api.record_store_path(), 30)

    response = client.get("/api/plugins/mission-control-governance/records")

    assert response.status_code == 200
    payload = response.json()
    assert payload["count"] == 25
    assert payload["limit"] == 25
    assert [item["record_index"] for item in payload["records"]] == list(range(5, 30))
    assert payload["records"][0]["record"]["statement"] == "Keep governance record 5 inert."
    assert payload["records"][-1]["record"]["statement"] == "Keep governance record 29 inert."


def test_records_caps_oversized_limit(plugin_api, client):
    _seed_goal_records(plugin_api.record_store_path(), 60)

    response = client.get("/api/plugins/mission-control-governance/records?limit=999")

    assert response.status_code == 200
    payload = response.json()
    assert payload["count"] == 50
    assert payload["limit"] == 50
    assert [item["record_index"] for item in payload["records"]] == list(range(10, 60))


@pytest.mark.parametrize("limit", ["bogus", "0", "-10"])
def test_records_invalid_or_non_positive_limit_uses_safe_default(plugin_api, client, limit):
    _seed_goal_records(plugin_api.record_store_path(), 30)

    response = client.get(f"/api/plugins/mission-control-governance/records?limit={limit}")

    assert response.status_code == 200
    payload = response.json()
    assert payload["count"] == 25
    assert payload["limit"] == 25
    assert [item["record_index"] for item in payload["records"]] == list(range(5, 30))


def test_records_limit_keeps_raw_metadata_stripped(plugin_api, client):
    _seed_goal_records(plugin_api.record_store_path(), 30)

    response = client.get("/api/plugins/mission-control-governance/records?limit=2")

    assert response.status_code == 200
    payload = response.json()
    assert payload["count"] == 2
    assert [item["record_index"] for item in payload["records"]] == [28, 29]
    lowered = f"{payload}".lower()
    assert "metadata" not in lowered
    assert "secret raw governance context" not in lowered
    assert "secret governance transcript" not in lowered


def test_bounded_records_detail_index_remains_available_and_sanitized(plugin_api, client):
    _seed_goal_records(plugin_api.record_store_path(), 30)

    records_payload = client.get("/api/plugins/mission-control-governance/records?limit=2").json()
    record_index = records_payload["records"][0]["record_index"]
    response = client.get(f"/api/plugins/mission-control-governance/records/{record_index}")

    assert response.status_code == 200
    payload = response.json()
    assert payload["record_index"] == 28
    assert payload["record"]["statement"] == "Keep governance record 28 inert."
    lowered = f"{payload}".lower()
    assert "metadata" not in lowered
    assert "secret raw governance context" not in lowered
    assert "secret governance transcript" not in lowered


def test_start_gate_returns_no_active_envelope_for_missing_store(client):
    response = client.get("/api/plugins/mission-control-governance/start-gate")

    assert response.status_code == 200
    assert response.json() == {
        "trusted_for_execution": False,
        "inert_context_only": True,
        "execution_enabled": False,
        "store_status": "missing",
        "error": None,
        "has_active_envelope": False,
        "source": "none",
        "record_index": None,
        "mission_id": None,
        "mission_title": None,
        "mission_created_at": None,
        "envelope": None,
    }


def test_start_gate_prefers_latest_mission_brief_control(plugin_api, client):
    store = JsonlRecordStore(plugin_api.record_store_path())
    old_control = TaskControlEnvelope(
        active_lane="Older standalone lane",
        mode="inventory only",
        allowed_actions=("read records",),
        forbidden_actions=("change records",),
        current_repo="/tmp/old",
        stop_condition="Stop before edits.",
    )
    latest_control = TaskControlEnvelope(
        active_lane="Latest mission lane",
        mode="focused tests only",
        allowed_actions=("add GET endpoint", "update dashboard panel"),
        forbidden_actions=("run broad tests", "load transcripts"),
        current_repo="/tmp/latest",
        expected_systems_files=("plugins/mission-control-governance/api.py",),
        stop_condition="Stop after focused tests.",
        other_threads_excluded=("unrelated PR",),
    )
    goal = GoalContract(goal_id="goal-latest", statement="Expose inert start gate summary.")
    store.append(old_control)
    store.append(
        MissionBrief(
            mission_id="mission-latest",
            title="Start Gate UI",
            created_at="2026-06-05T00:00:00Z",
            goal=goal,
            control=latest_control,
        )
    )

    response = client.get("/api/plugins/mission-control-governance/start-gate")

    assert response.status_code == 200
    payload = response.json()
    assert payload["trusted_for_execution"] is False
    assert payload["inert_context_only"] is True
    assert payload["execution_enabled"] is False
    assert payload["has_active_envelope"] is True
    assert payload["source"] == "MissionBrief.control"
    assert payload["record_index"] == 1
    assert payload["mission_id"] == "mission-latest"
    assert payload["mission_title"] == "Start Gate UI"
    assert payload["mission_created_at"] == "2026-06-05T00:00:00Z"
    assert payload["envelope"] == {
        "envelope_id": "",
        "active_lane": "Latest mission lane",
        "mode": "focused tests only",
        "allowed_actions": ["add GET endpoint", "update dashboard panel"],
        "forbidden_actions": ["run broad tests", "load transcripts"],
        "current_repo": "/tmp/latest",
        "expected_systems_files": ["plugins/mission-control-governance/api.py"],
        "stop_condition": "Stop after focused tests.",
        "other_threads_excluded": ["unrelated PR"],
        "report_requirements": [],
        "risk_level": "",
        "approval_required": False,
        "approval_slice_ids": [],
        "evidence_ids": [],
        "token_context_policy": "",
        "created_at": "",
        "status": "",
    }


def test_start_gate_uses_standalone_envelope_fallback(plugin_api, client):
    store = JsonlRecordStore(plugin_api.record_store_path())
    control = TaskControlEnvelope(
        active_lane="Standalone lane",
        mode="read-only summary",
        allowed_actions=("read envelope",),
        forbidden_actions=("write records",),
        current_repo="/tmp/standalone",
        stop_condition="Stop after response.",
    )
    store.append(control)

    response = client.get("/api/plugins/mission-control-governance/start-gate")

    assert response.status_code == 200
    payload = response.json()
    assert payload["has_active_envelope"] is True
    assert payload["source"] == "TaskControlEnvelope"
    assert payload["record_index"] == 0
    assert payload["mission_id"] is None
    assert payload["mission_title"] is None
    assert payload["mission_created_at"] is None
    assert payload["envelope"]["active_lane"] == "Standalone lane"
    assert payload["envelope"]["mode"] == "read-only summary"
    assert "metadata" not in payload["envelope"]


def _valid_start_gate_evaluation_payload(**overrides):
    payload = {
        "envelope_id": "envelope-pr-l",
        "active_lane": "PR-L read-only/default-off Start Gate evaluator API exposure",
        "mode": "bounded implementation in a new clean worktree only",
        "allowed_actions": ["add read-only evaluator endpoint", "run targeted tests"],
        "forbidden_actions": ["no live enforcement", "no tool execution", "no secrets"],
        "current_repo": "Travisaggie04/hermes-agent",
        "expected_systems_files": ["plugins/mission-control-governance/api.py"],
        "stop_condition": "Stop after draft PR.",
        "other_threads_excluded": ["Signal Room", "Instagram"],
        "report_requirements": ["files changed", "tests run", "safety confirmation"],
        "token_context_policy": "bounded compact input only",
        "metadata": {
            "target_remote": "Travisaggie04/hermes-agent",
            "worktree_state": "clean",
            "raw_context": "secret raw context must not leak",
        },
    }
    payload.update(overrides)
    return payload


def test_start_gate_evaluate_returns_pass_for_valid_bounded_envelope(plugin_api, client):
    response = client.post(
        "/api/plugins/mission-control-governance/start-gate/evaluate",
        json=_valid_start_gate_evaluation_payload(),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["trusted_for_execution"] is False
    assert payload["inert_context_only"] is True
    assert payload["execution_enabled"] is False
    assert payload["default_off"] is True
    assert payload["inert"] is True
    assert payload["enforces_runtime"] is False
    assert payload["source"] == "proposed_envelope"
    assert payload["stored"] is False
    assert payload["decision"]["decision_state"] == "pass"
    assert payload["decision"]["envelope_id"] == "envelope-pr-l"
    assert payload["decision"]["blocked_actions"] == []
    assert payload["decision"]["required_approvals"] == []
    assert plugin_api.record_store_path().exists() is False


@pytest.mark.parametrize(
    ("field_name", "replacement", "reason_fragment"),
    (
        ("active_lane", "", "missing active lane"),
        ("mode", "", "missing mode"),
        ("allowed_actions", [], "missing allowed actions"),
        ("forbidden_actions", [], "missing forbidden actions"),
        ("stop_condition", "", "missing stop condition"),
        ("report_requirements", [], "missing report requirements"),
    ),
)
def test_start_gate_evaluate_blocks_missing_required_lane_control_fields(
    client,
    field_name,
    replacement,
    reason_fragment,
):
    response = client.post(
        "/api/plugins/mission-control-governance/start-gate/evaluate",
        json=_valid_start_gate_evaluation_payload(**{field_name: replacement}),
    )

    assert response.status_code == 200
    decision = response.json()["decision"]
    assert decision["decision_state"] == "blocked"
    assert any(reason_fragment in reason for reason in decision["reasons"])


def test_start_gate_evaluate_flags_dangerous_actions_as_needing_approval(client):
    response = client.post(
        "/api/plugins/mission-control-governance/start-gate/evaluate",
        json=_valid_start_gate_evaluation_payload(
            allowed_actions=["deploy Mission Control"],
        ),
    )

    assert response.status_code == 200
    decision = response.json()["decision"]
    assert decision["decision_state"] == "needs_approval"
    assert decision["blocked_actions"] == ["deploy Mission Control"]
    assert decision["required_approvals"] == ["explicit approval for privileged action"]


def test_start_gate_evaluate_handles_malformed_json_and_oversized_body_safely(client):
    malformed = client.post(
        "/api/plugins/mission-control-governance/start-gate/evaluate",
        content="{not valid json",
        headers={"content-type": "application/json"},
    )
    oversized = client.post(
        "/api/plugins/mission-control-governance/start-gate/evaluate",
        json={"active_lane": "x" * 9000},
    )

    assert malformed.status_code == 400
    assert malformed.json()["detail"] == "malformed JSON body"
    assert oversized.status_code == 413
    assert oversized.json()["detail"] == "evaluation payload is too large"


def test_start_gate_evaluate_does_not_write_records_or_mutate_store(plugin_api, client):
    records_path = plugin_api.record_store_path()
    before_exists = records_path.exists()

    response = client.post(
        "/api/plugins/mission-control-governance/start-gate/evaluate",
        json=_valid_start_gate_evaluation_payload(),
    )

    assert response.status_code == 200
    assert response.json()["stored"] is False
    assert records_path.exists() is before_exists


def test_start_gate_evaluate_does_not_expose_raw_metadata(client):
    response = client.post(
        "/api/plugins/mission-control-governance/start-gate/evaluate",
        json=_valid_start_gate_evaluation_payload(
            metadata={
                "target_remote": "Travisaggie04/hermes-agent",
                "worktree_state": "clean",
                "transcript": "secret transcript value",
                "raw_context": "secret raw context value",
            },
        ),
    )

    assert response.status_code == 200
    lowered = str(response.json()).lower()
    assert "metadata" not in lowered
    assert "secret transcript value" not in lowered
    assert "secret raw context value" not in lowered


def test_start_gate_evaluate_does_not_call_tools_subprocess_network_or_git(
    plugin_api,
    client,
):
    response = client.post(
        "/api/plugins/mission-control-governance/start-gate/evaluate",
        json=_valid_start_gate_evaluation_payload(),
    )
    source = "\n".join(
        inspect.getsource(item)
        for item in (
            plugin_api.start_gate_evaluate,
            plugin_api._read_compact_json_body,
            plugin_api._compact_evaluation_payload,
            plugin_api._start_gate_decision_payload,
        )
    )

    assert response.status_code == 200
    for forbidden in (
        "subprocess",
        "Popen",
        "os.system",
        "socket",
        "requests",
        "httpx",
        "urllib",
        "git",
        "JsonlRecordStore",
        "record_store_path",
        ".append(",
        ".write(",
        "open(",
    ):
        assert forbidden not in source


def test_lane_preflight_evaluate_returns_compact_dry_run_result(plugin_api, client):
    response = client.post(
        "/api/plugins/mission-control-governance/lane-preflight/evaluate",
        json={},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["trusted_for_execution"] is False
    assert payload["inert_context_only"] is True
    assert payload["execution_enabled"] is False
    assert payload["default_off"] is True
    assert payload["dry_run_only"] is True
    assert payload["enforces_runtime"] is False
    assert payload["source"] == "fixed_lane_start_sample"
    assert payload["stored"] is False
    assert payload["input_mode"] == "bounded_fixed_sample"
    assert payload["linked_kanban_task"] == {
        "link_state": "missing_link",
        "board_id": "",
        "board_name": "",
        "task_id": "",
        "task_title": "",
        "task_status": "",
        "task_workspace": "",
        "task_branch": "",
        "linked_goal_contract_id": "",
        "linked_task_control_envelope_id": "",
        "reasons": [],
    }
    assert payload["decision_state"] == "pass"
    assert payload["would_block"] is False
    assert payload["would_require_approval"] is False
    assert isinstance(payload["reasons"], list)
    assert payload["blocked_actions"] == []
    assert payload["required_approvals"] == []
    assert "supported_input_fields" not in payload
    assert "start_gate_check" not in payload
    assert plugin_api.record_store_path().exists() is False


def test_lane_preflight_evaluate_includes_safe_linked_kanban_identity_when_available(
    plugin_api,
    client,
    monkeypatch,
):
    from mission_control.kanban_linkage import ObservedKanbanTaskState

    monkeypatch.setattr(
        plugin_api,
        "_sample_lane_preflight_envelope",
        lambda: TaskControlEnvelope(
            envelope_id="tce-lane-preflight-linked",
            active_lane="Lane preflight linked identity",
            mode="display only",
            current_repo="/work/hermes-agent",
            metadata={
                "kanban_board_id": "mission-control",
                "kanban_task_id": "task-linked",
                "goal_contract_id": "goal-linked",
                "expected_branch": "pr-p-lane-preflight-result-visibility",
                "raw_context": "secret raw request metadata",
            },
        ),
    )
    monkeypatch.setattr(
        "mission_control.kanban_linkage.read_observed_kanban_task",
        lambda link: (
            ObservedKanbanTaskState(
                board_id=link.board_id,
                task_id=link.task_id,
                title="Linked lane preflight task",
                status="ready",
                workspace_path="/work/hermes-agent",
                branch_name="pr-p-lane-preflight-result-visibility",
            ),
            "",
        ),
    )
    monkeypatch.setattr(
        "mission_control.kanban_linkage.read_kanban_board_name",
        lambda board_id: "Mission Control",
    )

    response = client.post(
        "/api/plugins/mission-control-governance/lane-preflight/evaluate",
        json={},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["dry_run_only"] is True
    assert payload["default_off"] is True
    assert payload["enforces_runtime"] is False
    assert payload["stored"] is False
    assert payload["linked_kanban_task"] == {
        "link_state": "linked",
        "board_id": "mission-control",
        "board_name": "Mission Control",
        "task_id": "task-linked",
        "task_title": "Linked lane preflight task",
        "task_status": "ready",
        "task_workspace": "hermes-agent",
        "task_branch": "pr-p-lane-preflight-result-visibility",
        "linked_goal_contract_id": "goal-linked",
        "linked_task_control_envelope_id": "tce-lane-preflight-linked",
        "reasons": [],
    }
    flattened = str(payload)
    assert "metadata" not in flattened.lower()
    assert "secret raw request metadata" not in flattened


def test_lane_preflight_linked_kanban_identity_uses_shared_display_safety(
    plugin_api,
    client,
    monkeypatch,
):
    from mission_control.kanban_linkage import ObservedKanbanTaskState

    unsafe = "\x1b[31mSECRET_TOKEN=sk-test-fake\n" + ("x" * 500)
    monkeypatch.setattr(
        plugin_api,
        "_sample_lane_preflight_envelope",
        lambda: TaskControlEnvelope(
            envelope_id="tce-" + unsafe,
            active_lane="Lane preflight linked identity",
            mode="display only",
            current_repo="/different/workspace",
            metadata={
                "kanban_board_id": "mission-control",
                "kanban_task_id": "task-linked",
                "goal_contract_id": "goal-" + unsafe,
                "expected_branch": "main",
                "raw_context": "secret raw request metadata",
            },
        ),
    )
    monkeypatch.setattr(
        "mission_control.kanban_linkage.read_observed_kanban_task",
        lambda link: (
            ObservedKanbanTaskState(
                board_id=link.board_id,
                task_id=link.task_id,
                title="Task " + unsafe,
                status="ready\nqueued",
                workspace_path="/home/jenny/.secrets/project",
                branch_name="feature/" + unsafe,
            ),
            "",
        ),
    )
    monkeypatch.setattr(
        "mission_control.kanban_linkage.read_kanban_board_name",
        lambda board_id: "Mission Control " + unsafe,
    )

    response = client.post(
        "/api/plugins/mission-control-governance/lane-preflight/evaluate",
        json={
            "metadata": {
                "kanban_task_id": "raw-body-task-id",
                "token": "SECRET_TOKEN=sk-body-fake",
            },
            "current_repo": "/home/jenny/.hidden/raw-body",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    linked = payload["linked_kanban_task"]
    flattened = str(linked)
    assert linked["link_state"] == "scope_mismatch"
    assert linked["task_workspace"] == "[workspace path hidden]"
    assert "\x1b" not in flattened
    assert "\n" not in flattened
    assert "sk-test-fake" not in flattened
    assert "SECRET_TOKEN" not in flattened
    assert "/home/jenny/.secrets/project" not in flattened
    assert "raw-body-task-id" not in str(payload)
    assert "sk-body-fake" not in str(payload)
    assert "/home/jenny/.hidden/raw-body" not in str(payload)
    assert all(len(reason) <= 120 for reason in linked["reasons"])


def test_lane_preflight_evaluate_does_not_expose_raw_metadata(client):
    response = client.post(
        "/api/plugins/mission-control-governance/lane-preflight/evaluate",
        json={
            "metadata": {
                "transcript": "secret transcript value",
                "raw_context": "secret raw context value",
            },
            "requested_actions": ["deploy Mission Control"],
        },
    )

    assert response.status_code == 200
    lowered = str(response.json()).lower()
    assert "metadata" not in lowered
    assert "secret transcript value" not in lowered
    assert "secret raw context value" not in lowered
    assert "deploy mission control" not in lowered


def test_lane_preflight_evaluate_does_not_write_records_or_mutate_runtime_surfaces(
    plugin_api,
    client,
):
    records_path = plugin_api.record_store_path()
    before_exists = records_path.exists()

    response = client.post(
        "/api/plugins/mission-control-governance/lane-preflight/evaluate",
        json={},
    )
    source = "\n".join(
        inspect.getsource(item)
        for item in (
            plugin_api.lane_preflight_evaluate,
            plugin_api._lane_preflight_visibility_payload,
            plugin_api._sample_lane_preflight_request,
        )
    )

    assert response.status_code == 200
    assert response.json()["stored"] is False
    assert records_path.exists() is before_exists
    for forbidden in (
        "subprocess",
        "Popen",
        "os.system",
        "socket",
        "requests",
        "httpx",
        "urllib",
        "git",
        "JsonlRecordStore",
        "record_store_path",
        ".append(",
        ".write(",
        "open(",
    ):
        assert forbidden not in source


def test_schema_lists_record_types_without_loading_records(client):
    response = client.get("/api/plugins/mission-control-governance/schema")

    assert response.status_code == 200
    payload = response.json()
    assert payload["trusted_for_execution"] is False
    assert payload["inert_context_only"] is True
    assert payload["execution_enabled"] is False
    assert payload["record_store"]["status"] == "missing"
    assert "GoalContract" in payload["record_types"]
    assert payload["record_types"]["GoalContract"]["fields"] == [
        "goal_id",
        "statement",
        "success_criteria",
        "constraints",
        "metadata",
    ]
    assert "ArtifactRef" in payload["record_types"]


def test_record_detail_returns_zero_based_record_index(plugin_api, client):
    _seed_records(plugin_api.record_store_path())

    response = client.get("/api/plugins/mission-control-governance/records/1")

    assert response.status_code == 200
    payload = response.json()
    assert payload["trusted_for_execution"] is False
    assert payload["inert_context_only"] is True
    assert payload["execution_enabled"] is False
    assert payload["record_index"] == 1
    assert payload["record_type"] == "TaskControlEnvelope"
    assert payload["record"]["active_lane"] == "PR-B Mission Control governance plugin MVP"


def test_operator_action_metadata_is_not_exposed_by_record_apis(plugin_api, client):
    store = JsonlRecordStore(plugin_api.record_store_path())
    store.append(
        OperatorAction(
            action_id="action-sensitive-metadata",
            title="Review safe summary only",
            lane="PR-G",
            mode="read-only",
            requested_action="Review bounded queue summary.",
            metadata={
                "source": "planning",
                "transcript": "secret transcript value",
                "artifact_blob": "secret artifact value",
                "arbitrary_key": "arbitrary secret value",
            },
        )
    )

    records_payload = client.get("/api/plugins/mission-control-governance/records").json()
    detail_payload = client.get("/api/plugins/mission-control-governance/records/0").json()

    for record in (
        records_payload["records"][0]["record"],
        detail_payload["record"],
    ):
        assert record["action_id"] == "action-sensitive-metadata"
        assert record["source"] == "planning"
        assert "metadata" not in record
        assert "transcript" not in record
        assert "artifact_blob" not in record
        assert "arbitrary_key" not in record

    lowered = f"{records_payload} {detail_payload}".lower()
    assert "secret transcript value" not in lowered
    assert "secret artifact value" not in lowered
    assert "arbitrary secret value" not in lowered


def test_approval_and_evidence_metadata_is_not_exposed_by_record_apis(plugin_api, client):
    store = JsonlRecordStore(plugin_api.record_store_path())
    store.append(
        ApprovalSlice(
            approval_slice_id="approval-sensitive-metadata",
            related_action_id="action-sensitive",
            approval_type="operator",
            decision_state="pending",
            required_by="Travis",
            reason="Needs focused verification.",
            safety_conditions=("no deploy",),
            evidence_ids=("evidence-sensitive-metadata",),
            created_at="2026-06-06T00:00:00Z",
            metadata={
                "transcript": "secret approval transcript",
                "raw_decision": "secret approval metadata",
            },
        )
    )
    store.append(
        EvidenceCard(
            evidence_id="evidence-sensitive-metadata",
            related_lane="PR-H",
            related_action_id="action-sensitive",
            related_record_type="OperatorAction",
            summary="Safe compact evidence summary.",
            evidence_type="test",
            source_label="pytest",
            created_at="2026-06-06T00:01:00Z",
            risk_notes=("metadata must stay private",),
            metadata={
                "raw_log": "secret evidence log",
                "transcript": "secret evidence transcript",
            },
        )
    )

    records_payload = client.get("/api/plugins/mission-control-governance/records").json()
    approval_detail = client.get("/api/plugins/mission-control-governance/records/0").json()
    evidence_detail = client.get("/api/plugins/mission-control-governance/records/1").json()

    assert "metadata" not in records_payload["records"][0]["record"]
    assert "metadata" not in records_payload["records"][1]["record"]
    assert "metadata" not in approval_detail["record"]
    assert "metadata" not in evidence_detail["record"]
    lowered = f"{records_payload} {approval_detail} {evidence_detail}".lower()
    assert "secret approval transcript" not in lowered
    assert "secret approval metadata" not in lowered
    assert "secret evidence log" not in lowered
    assert "secret evidence transcript" not in lowered


def test_task_control_envelopes_endpoint_is_bounded_and_metadata_safe(plugin_api, client):
    store = JsonlRecordStore(plugin_api.record_store_path())
    for index in range(12):
        store.append(
            TaskControlEnvelope(
                envelope_id=f"envelope-{index}",
                active_lane=f"lane-{index}",
                mode="read-only",
                allowed_actions=("read records",),
                forbidden_actions=("execute tools",),
                stop_condition="Stop after report.",
                report_requirements=("files changed",),
                risk_level="low",
                approval_required=index % 2 == 0,
                approval_slice_ids=(f"approval-{index}",),
                evidence_ids=(f"evidence-{index}",),
                token_context_policy="summary-first latest-10 only",
                created_at=f"2026-06-06T00:{index:02d}:00Z",
                status="active",
                metadata={
                    "raw_context": "secret envelope context",
                    "transcript": "secret envelope transcript",
                },
            )
        )

    response = client.get("/api/plugins/mission-control-governance/task-control-envelopes")

    assert response.status_code == 200
    payload = response.json()
    assert payload["trusted_for_execution"] is False
    assert payload["inert_context_only"] is True
    assert payload["execution_enabled"] is False
    assert payload["source"] == "TaskControlEnvelope"
    assert payload["count"] == 10
    assert [item["envelope_id"] for item in payload["task_control_envelopes"]] == [
        f"envelope-{index}" for index in range(2, 12)
    ]
    first = payload["task_control_envelopes"][0]
    assert first["record_index"] == 2
    assert first["active_lane"] == "lane-2"
    assert first["allowed_action_count"] == 1
    assert first["forbidden_action_count"] == 1
    assert first["approval_required"] is True
    assert first["approval_slice_count"] == 1
    assert first["evidence_count"] == 1
    lowered = str(payload).lower()
    assert "metadata" not in lowered
    assert "secret envelope context" not in lowered
    assert "secret envelope transcript" not in lowered


def test_task_control_envelopes_endpoint_returns_linked_kanban_task_state(
    plugin_api,
    client,
    tmp_path,
    monkeypatch,
):
    monkeypatch.setenv("HERMES_KANBAN_HOME", str(tmp_path / "kanban-home"))
    from hermes_cli import kanban_db

    kanban_db.init_db(board="mission-control")
    with kanban_db.connect(board="mission-control") as conn:
        task_id = kanban_db.create_task(
            conn,
            title="Implement linkage",
            body="Visible task state only.",
            created_by="test",
            workspace_kind="worktree",
            workspace_path="/work/hermes-agent",
            branch_name="mc-kanban-linkage-v1",
            board="mission-control",
        )

    store = JsonlRecordStore(plugin_api.record_store_path())
    store.append(
        TaskControlEnvelope(
            envelope_id="tce-linked",
            active_lane="Mission Control / Kanban task-linkage v1",
            mode="bounded implementation",
            current_repo="/work/hermes-agent",
            metadata={
                "kanban_board_id": "mission-control",
                "kanban_task_id": task_id,
                "goal_contract_id": "goal-linked",
                "expected_branch": "mc-kanban-linkage-v1",
                "transcript": "secret envelope transcript",
            },
        )
    )

    response = client.get("/api/plugins/mission-control-governance/task-control-envelopes")

    assert response.status_code == 200
    item = response.json()["task_control_envelopes"][0]
    assert item["linked_kanban_task"] == {
        "link_state": "linked",
        "board_id": "mission-control",
        "board_name": "Mission Control",
        "task_id": task_id,
        "task_title": "Implement linkage",
        "task_status": "ready",
        "task_workspace": "hermes-agent",
        "task_branch": "mc-kanban-linkage-v1",
        "linked_goal_contract_id": "goal-linked",
        "linked_task_control_envelope_id": "tce-linked",
        "reasons": [],
    }
    assert "metadata" not in str(item).lower()
    assert "secret envelope transcript" not in str(item)


def test_records_endpoint_returns_goal_contract_linked_kanban_task_state(
    plugin_api,
    client,
    tmp_path,
    monkeypatch,
):
    monkeypatch.setenv("HERMES_KANBAN_HOME", str(tmp_path / "kanban-home"))
    from hermes_cli import kanban_db

    kanban_db.init_db(board="mission-control")
    with kanban_db.connect(board="mission-control") as conn:
        task_id = kanban_db.create_task(
            conn,
            title="Goal task",
            body="Visible goal-linked task state only.",
            created_by="test",
            board="mission-control",
        )

    store = JsonlRecordStore(plugin_api.record_store_path())
    store.append(
        GoalContract(
            goal_id="goal-linked",
            statement="Display the linked Kanban identity.",
            metadata={
                "kanban_board_id": "mission-control",
                "kanban_task_id": task_id,
                "raw_context": "secret goal context",
            },
        )
    )

    response = client.get("/api/plugins/mission-control-governance/records")

    assert response.status_code == 200
    record = response.json()["records"][0]["record"]
    assert record["linked_kanban_task"]["link_state"] == "linked"
    assert record["linked_kanban_task"]["board_id"] == "mission-control"
    assert record["linked_kanban_task"]["task_id"] == task_id
    assert record["linked_kanban_task"]["task_title"] == "Goal task"
    assert record["linked_kanban_task"]["linked_goal_contract_id"] == "goal-linked"
    assert "metadata" not in str(record).lower()
    assert "secret goal context" not in str(record)


def test_api_linked_kanban_payload_is_display_safe_for_dashboard(
    plugin_api,
    client,
    tmp_path,
    monkeypatch,
):
    monkeypatch.setenv("HERMES_KANBAN_HOME", str(tmp_path / "kanban-home"))
    from hermes_cli import kanban_db

    kanban_db.init_db(board="mission-control")
    with kanban_db.connect(board="mission-control") as conn:
        task_id = kanban_db.create_task(
            conn,
            title="Task \x1b[31mSECRET_TOKEN=sk-test-fake\n" + ("x" * 500),
            body="Visible task state only.",
            created_by="test",
            workspace_kind="worktree",
            workspace_path="/home/jenny/.secrets/project",
            branch_name="feature/SECRET_TOKEN=sk-test-fake\n" + ("x" * 500),
            board="mission-control",
        )

    store = JsonlRecordStore(plugin_api.record_store_path())
    store.append(
        TaskControlEnvelope(
            envelope_id="tce-dashboard-safe",
            active_lane="Mission Control / Kanban display-only linkage",
            mode="read-only display",
            current_repo="/different/project",
            metadata={
                "kanban_board_id": "mission-control",
                "kanban_task_id": task_id,
                "goal_contract_id": "goal-dashboard-safe",
                "expected_branch": "main",
                "raw_context": "secret raw metadata",
            },
        )
    )

    response = client.get("/api/plugins/mission-control-governance/start-gate")

    assert response.status_code == 200
    linked = response.json()["envelope"]["linked_kanban_task"]
    flattened = str(linked)
    assert linked["link_state"] == "scope_mismatch"
    assert linked["task_workspace"] == "[workspace path hidden]"
    assert "\x1b" not in flattened
    assert "\n" not in flattened
    assert "sk-test-fake" not in flattened
    assert "SECRET_TOKEN" not in flattened
    assert "/home/jenny/.secrets/project" not in flattened
    assert "metadata" not in flattened.lower()
    assert "secret raw metadata" not in flattened
    assert all(len(reason) <= 120 for reason in linked["reasons"])


def test_dashboard_model_picker_panel_is_display_only_and_non_executing():
    js = (PLUGIN_DIR / "dashboard" / "dist" / "index.js").read_text()

    assert 'MODEL_REGISTRY_URL = "/api/plugins/mission-control-governance/model-registry"' in js
    assert "Model Picker" in js
    assert "Display-only / routing disabled" in js
    assert "Waha requires explicit approved models" in js
    assert "Free-cloud and unknown models are blocked for Waha until approved." in js
    assert "Verifier roles stay blocked until explicitly qualified." in js
    assert "routing_enabled=false" in js
    assert "No execution controls, provider calls, or credential checks are available here." in js
    forbidden_actions = (
        "Select model",
        "Use model",
        "Route task",
        "Test model",
        "Call provider",
    )
    assert all(action not in js for action in forbidden_actions)


def test_dashboard_model_picker_styles_are_present():
    css = (PLUGIN_DIR / "dashboard" / "dist" / "style.css").read_text()

    assert ".mcg-model-picker-card" in css
    assert ".mcg-model-grid" in css
    assert ".mcg-model-row" in css
    assert ".mcg-model-pill" in css


def test_action_policy_endpoint_exposes_inert_allow_ask_deny_policy(client):
    response = client.get("/api/plugins/mission-control-governance/action-policy")

    assert response.status_code == 200
    payload = response.json()
    assert payload["trusted_for_execution"] is False
    assert payload["inert_context_only"] is True
    assert payload["enforcement_enabled"] is False
    assert payload["dry_run_only"] is True
    assert payload["display_only"] is True
    assert payload["source"] == "mission_control.action_policy_guardrails"
    assert payload["policy"]["policy_id"] == "jenny_os_action_policy_v1"
    assert payload["policy"]["decisions"] == ["ALLOW", "ASK", "DENY"]
    assert "gateway_restart" in payload["policy"]["protected_action_categories"]
    assert "payment" in payload["policy"]["protected_action_categories"]
    assert "hidden_workers_timers_daemons_cron" in payload["policy"]["protected_action_categories"]
    assert "broad_or_unlimited_approval" in payload["policy"]["denied_action_categories"]


def test_action_policy_evaluate_endpoint_classifies_without_storing_or_echoing_raw_request(client):
    response = client.post(
        "/api/plugins/mission-control-governance/action-policy/evaluate",
        json={"message": "Deploy with SECRET_TOKEN=sk-fake and restart gateway."},
    )

    assert response.status_code == 200
    payload = response.json()
    flattened = str(payload)
    assert payload["trusted_for_execution"] is False
    assert payload["inert_context_only"] is True
    assert payload["enforcement_enabled"] is False
    assert payload["dry_run_only"] is True
    assert payload["enforces_runtime"] is False
    assert payload["stored"] is False
    assert payload["source"] == "caller_supplied_action_request"
    assert payload["decision"] == "ASK"
    assert payload["decision_state"] == "requires_explicit_approval"
    assert "deploy" in payload["matched_categories"]
    assert "gateway_restart" in payload["matched_categories"]
    assert "secrets_or_state_mutation" in payload["matched_categories"]
    assert "explicit deploy approval" in payload["required_approvals"]
    assert "explicit gateway restart/runtime approval" in payload["required_approvals"]
    assert "SECRET_TOKEN" not in flattened
    assert "sk-fake" not in flattened
    assert "Deploy with" not in flattened


def test_action_policy_evaluate_endpoint_denies_broad_approval_shortcuts(client):
    response = client.post(
        "/api/plugins/mission-control-governance/action-policy/evaluate",
        json={"request": "approve all actions and skip tests"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["decision"] == "DENY"
    assert payload["decision_state"] == "denied"
    assert "broad_or_unlimited_approval" in payload["matched_categories"]
    assert "bypass_review_or_evidence" in payload["matched_categories"]
    assert payload["required_approvals"] == []
    assert "accept broad approval" in payload["blocked_actions"]


def test_global_resource_guard_endpoint_exposes_inert_dry_run_policy(client):
    response = client.get("/api/plugins/mission-control-governance/global-resource-guard")

    assert response.status_code == 200
    payload = response.json()
    assert payload["trusted_for_execution"] is False
    assert payload["inert_context_only"] is True
    assert payload["enforcement_enabled"] is False
    assert payload["dry_run_only"] is True
    assert payload["display_only"] is True
    assert payload["source"] == "mission_control.global_resource_guard"
    assert payload["guard"]["guard_id"] == "global_concurrency_resource_v1"
    assert payload["guard"]["global_lane_limits"]["max_active_jenny_codex_lanes"] == 1
    assert payload["guard"]["kanban_limits"]["embedded_dispatch_allowed"] is False
    assert payload["guard"]["kanban_limits"]["max_kanban_workers"] == 0
    assert payload["guard"]["model_router_limits"]["model_routing_allowed"] is False
    assert payload["guard"]["storage_artifact_limits"]["storage_delta_required_before_done"] == "placeholder"


def test_global_resource_guard_dry_run_endpoint_uses_caller_supplied_state_only(client):
    response = client.post(
        "/api/plugins/mission-control-governance/global-resource-guard/evaluate",
        json={
            "active_jenny_codex_lanes": 2,
            "embedded_dispatch_enabled": True,
            "model_routing_requested": True,
            "waha_execution_requested": True,
            "waha_hard_wall_ready": False,
            "waha_approved_model_policy_ready": False,
            "waha_technical_verifier_ready": False,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["trusted_for_execution"] is False
    assert payload["inert_context_only"] is True
    assert payload["enforcement_enabled"] is False
    assert payload["dry_run_only"] is True
    assert payload["enforces_runtime"] is False
    assert payload["stored"] is False
    assert payload["source"] == "caller_supplied_observed_state"
    assert payload["decision_state"] == "would_block"
    assert payload["would_block"] is True
    assert "parallel Jenny/Codex lanes exceed max_active_jenny_codex_lanes=1" in payload["reasons"]
    assert "embedded Kanban dispatch is not approved" in payload["reasons"]
    assert "model routing is not approved" in payload["reasons"]
    assert "Waha hard-wall policy is unresolved" in payload["reasons"]
    assert "start additional Jenny/Codex lane" in payload["blocked_actions"]
    assert "route tasks to models" in payload["blocked_actions"]
    assert "explicit dispatch lane approval" in payload["required_approvals"]
    assert "storage_delta_required_before_done" in payload["unresolved_policy_fields"]


def test_storage_guard_endpoint_exposes_inert_dry_run_policy(client):
    response = client.get("/api/plugins/mission-control-governance/storage-guard")

    assert response.status_code == 200
    payload = response.json()
    assert payload["trusted_for_execution"] is False
    assert payload["inert_context_only"] is True
    assert payload["enforcement_enabled"] is False
    assert payload["dry_run_only"] is True
    assert payload["display_only"] is True
    assert payload["source"] == "mission_control.storage_guard"
    assert payload["guard"]["guard_id"] == "storage_guard_v1"
    assert payload["guard"]["artifact_manifest_rules"]["artifact_manifest_required_before_done"] is True
    assert payload["guard"]["storage_delta_rules"]["storage_delta_required_before_done"] is True
    assert payload["guard"]["archive_delete_rules"]["delete_forbidden_without_manifest"] is True
    assert payload["guard"]["cloud_archive_policy"]["no_cloud_upload_in_dry_run"] is True
    assert payload["guard"]["project_specific_posture"]["signal_room_video_requires_artifact_manifest_and_archive_plan"] is True


def test_storage_guard_dry_run_endpoint_uses_caller_supplied_state_only(client):
    response = client.post(
        "/api/plugins/mission-control-governance/storage-guard/evaluate",
        json={
            "task_marked_done": True,
            "artifact_manifest_required": True,
            "artifact_manifest_present": False,
            "cloud_upload_requested": True,
            "delete_requested": True,
            "archive_verification_present": False,
            "explicit_delete_lane": False,
            "large_artifact_created": True,
            "storage_delta_present": False,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["trusted_for_execution"] is False
    assert payload["inert_context_only"] is True
    assert payload["enforcement_enabled"] is False
    assert payload["dry_run_only"] is True
    assert payload["enforces_runtime"] is False
    assert payload["stored"] is False
    assert payload["source"] == "caller_supplied_storage_state"
    assert payload["decision_state"] == "would_block"
    assert payload["would_block"] is True
    assert "task marked done without required artifact manifest" in payload["reasons"]
    assert "cloud upload requested during dry-run" in payload["reasons"]
    assert "delete requested without archive verification" in payload["reasons"]
    assert "large artifact created without storage delta" in payload["reasons"]
    assert "mark task done" in payload["blocked_actions"]
    assert "upload artifacts to cloud" in payload["blocked_actions"]
    assert "delete artifacts" in payload["blocked_actions"]
    assert "explicit cloud upload approval" in payload["required_approvals"]
    assert "future_enforcement_wiring" in payload["unresolved_policy_fields"]
    assert "approved_archive_targets" in payload["unresolved_policy_fields"]


def test_storage_guard_cleanup_manifest_endpoint_is_dry_run_only(client):
    response = client.post(
        "/api/plugins/mission-control-governance/storage-guard/cleanup-manifest",
        json={
            "current_live_runtime": "/home/jenny/.hermes/hermes-runtime-live",
            "accepted_live_repo": "/home/jenny/.hermes/hermes-agent",
            "rollback_runtimes": ["/home/jenny/.hermes/hermes-runtime-rollback"],
            "candidates": [
                {
                    "path": "/home/jenny/.hermes/hermes-runtime-live",
                    "kind": "dashboard_runtime",
                    "clean": True,
                    "size_gib": 10,
                },
                {
                    "path": "/home/jenny/.hermes/hermes-runtime-old",
                    "kind": "stale_runtime",
                    "clean": True,
                    "merged": True,
                    "size_gib": 14,
                },
                {
                    "path": "/home/jenny/.hermes/worktrees/dirty-pr",
                    "kind": "review_worktree",
                    "clean": False,
                    "dirty": True,
                    "size_gib": 3,
                },
            ],
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["trusted_for_execution"] is False
    assert payload["inert_context_only"] is True
    assert payload["enforcement_enabled"] is False
    assert payload["dry_run_only"] is True
    assert payload["display_only"] is True
    assert payload["stored"] is False
    assert payload["delete_enabled"] is False
    assert payload["upload_enabled"] is False
    assert payload["source"] == "caller_supplied_cleanup_inventory"
    assert payload["current_live_runtime_protected"] is True
    assert payload["rollback_runtimes_protected"] is True
    assert payload["accepted_live_repo_protected"] is True
    assert payload["records_state_db_secrets_protected"] is True
    assert payload["summary"]["protected_count"] == 1
    assert payload["summary"]["eligible_count"] == 1
    assert payload["summary"]["blocked_count"] == 1
    assert payload["eligible"][0]["path"] == "/home/jenny/.hermes/hermes-runtime-old"
    assert "dirty worktrees are never cleanup candidates" in {
        item["reason"] for item in payload["blocked"]
    }


def test_verifier_workflow_endpoint_exposes_inert_dry_run_policy(client):
    response = client.get("/api/plugins/mission-control-governance/verifier-workflow")

    assert response.status_code == 200
    payload = response.json()
    assert payload["trusted_for_execution"] is False
    assert payload["inert_context_only"] is True
    assert payload["enforcement_enabled"] is False
    assert payload["dry_run_only"] is True
    assert payload["display_only"] is True
    assert payload["source"] == "mission_control.verifier_workflow"
    workflow = payload["workflow"]
    assert workflow["workflow_id"] == "verifier_workflow_v1"
    assert workflow["trusted_for_execution"] is False
    assert workflow["enforcement_enabled"] is False
    assert workflow["required_workflow"]["independent_verification_required"] is True
    assert workflow["required_workflow"]["implementer_cannot_self_verify"] is True
    assert workflow["pr_workflow"]["pr_merge_requires_approved_verification"] is True
    assert workflow["deployment_workflow"]["rollback_plan_required"] is True
    assert workflow["waha_workflow"]["waha_technical_verifier_required"] is True
    assert workflow["model_workflow"]["verifier_model_must_be_qualified_before_verifier_role"] is True
    assert workflow["storage_workflow"]["archive_verification_required_before_delete"] is True
    assert "verifier_verdict" in workflow["evidence_requirements"]


def test_verifier_workflow_dry_run_endpoint_uses_caller_supplied_state_only(client):
    response = client.post(
        "/api/plugins/mission-control-governance/verifier-workflow/evaluate",
        json={
            "pr_merge_requested": True,
            "independent_verification_present": False,
            "verification_approved": False,
            "implementer_id": "jenny",
            "verifier_id": "jenny",
            "deployment_requested": True,
            "deployment_readiness_packet_present": False,
            "rollback_plan_present": False,
            "waha_work_requested": True,
            "waha_technical_verifier_present": False,
            "verifier_model_role_requested": True,
            "verifier_model_qualified": False,
            "storage_cleanup_requested": True,
            "artifact_manifest_verified": False,
            "storage_delta_verified": False,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["trusted_for_execution"] is False
    assert payload["inert_context_only"] is True
    assert payload["enforcement_enabled"] is False
    assert payload["dry_run_only"] is True
    assert payload["enforces_runtime"] is False
    assert payload["stored"] is False
    assert payload["source"] == "caller_supplied_workflow_state"
    assert payload["decision_state"] == "would_block"
    assert payload["would_block"] is True
    assert "PR merge requested without independent verification" in payload["reasons"]
    assert "implementer cannot self-verify" in payload["reasons"]
    assert "deployment requested without deployment-readiness packet" in payload["reasons"]
    assert "deployment requested without rollback plan" in payload["reasons"]
    assert "Waha work requested without technical verifier" in payload["reasons"]
    assert "verifier model role requested with unqualified model" in payload["reasons"]
    assert "storage cleanup/delete requested without artifact manifest verification" in payload["reasons"]
    assert "merge PR" in payload["blocked_actions"]
    assert "deploy runtime" in payload["blocked_actions"]
    assert "mark Waha work ready" in payload["blocked_actions"]
    assert "assign model verifier role" in payload["blocked_actions"]
    assert "cleanup/delete storage artifacts" in payload["blocked_actions"]
    assert "qualified verifier model approval" in payload["required_approvals"]
    assert "future_runtime_enforcement_wiring" in payload["unresolved_policy_fields"]


def test_model_registry_endpoint_exposes_inert_display_only_policy(client):
    response = client.get("/api/plugins/mission-control-governance/model-registry")

    assert response.status_code == 200
    payload = response.json()
    assert payload["trusted_for_execution"] is False
    assert payload["inert_context_only"] is True
    assert payload["routing_enabled"] is False
    assert payload["display_only"] is True
    assert payload["count"] >= 3
    records = payload["model_registry"]
    assert all(record["trusted_for_execution"] is False for record in records)
    assert all(record["routing_enabled"] is False for record in records)
    unknown = next(record for record in records if record["provider_type"] == "unknown")
    assert unknown["allowed_for_waha"] is False
    assert unknown["verifier_allowed"] is False
    assert "deployment_review" in unknown["forbidden_lanes"]
    free_cloud = next(record for record in records if record["provider_type"] == "free_cloud")
    assert free_cloud["allowed_for_waha"] is False
    assert "explicit_waha_model_approval" in free_cloud["unresolved_before_routing"]


def test_domain_governance_endpoint_exposes_waha_hard_wall_policy_as_display_only(client):
    response = client.get("/api/plugins/mission-control-governance/domain-governance")

    assert response.status_code == 200
    payload = response.json()
    assert payload["trusted_for_execution"] is False
    assert payload["inert_context_only"] is True
    assert payload["execution_enabled"] is False
    assert payload["enforcement_enabled"] is False
    assert payload["display_only"] is True
    assert payload["count"] == 1
    policy = payload["domain_policies"][0]
    assert policy["domain_id"] == "waha"
    assert policy["domain_type"] == "professional_engineering"
    assert policy["isolation_level"] == "hard_wall_required"
    assert policy["board_policy"]["required_board"] == "waha"
    assert policy["workspace_policy"]["deny_cross_project_reads"] is True
    assert policy["workspace_policy"]["deny_cross_project_writes"] is True
    assert policy["profile_policy"]["allowed_profiles"] == ["wahainspection"]
    assert policy["memory_policy"]["required_namespace"] == "waha"
    assert policy["model_policy_placeholder"]["approved_models_required"] is True
    assert policy["verifier_policy"]["waha_technical_verifier_required"] is True
    assert policy["enforcement"] == {
        "trusted_for_execution": False,
        "inert_context_only": True,
        "enforcement_enabled": False,
        "display_only": True,
    }
    assert "allowed_roots" in policy["unresolved_required_before_enforcement"]


def test_start_gate_checks_endpoint_is_descriptive_bounded_and_metadata_safe(plugin_api, client):
    store = JsonlRecordStore(plugin_api.record_store_path())
    for index in range(12):
        store.append(
            StartGateCheck(
                start_gate_id=f"start-gate-{index}",
                envelope_id=f"envelope-{index}",
                decision_state="blocked" if index == 11 else "informational",
                reasons=(f"reason {index}",),
                blocked_actions=("deploy", "merge"),
                required_approvals=(f"approval-{index}",),
                dirty_worktree_state="clean",
                branch_safety_state="exact base",
                secret_safety_state="not touched",
                token_context_state="bounded",
                created_at=f"2026-06-06T01:{index:02d}:00Z",
                metadata={
                    "raw_scan": "secret start gate scan",
                    "transcript": "secret start gate transcript",
                },
            )
        )

    response = client.get("/api/plugins/mission-control-governance/start-gate-checks")

    assert response.status_code == 200
    payload = response.json()
    assert payload["trusted_for_execution"] is False
    assert payload["inert_context_only"] is True
    assert payload["execution_enabled"] is False
    assert payload["source"] == "StartGateCheck"
    assert payload["count"] == 10
    assert [item["start_gate_id"] for item in payload["start_gate_checks"]] == [
        f"start-gate-{index}" for index in range(2, 12)
    ]
    latest = payload["start_gate_checks"][-1]
    assert latest["record_index"] == 11
    assert latest["decision_state"] == "blocked"
    assert latest["reason_count"] == 1
    assert latest["blocked_action_count"] == 2
    assert latest["required_approval_count"] == 1
    lowered = str(payload).lower()
    assert "metadata" not in lowered
    assert "secret start gate scan" not in lowered
    assert "secret start gate transcript" not in lowered


def test_record_detail_returns_404_for_missing_index(plugin_api, client):
    _seed_records(plugin_api.record_store_path())

    response = client.get("/api/plugins/mission-control-governance/records/99")

    assert response.status_code == 404
    assert response.json()["detail"] == "record index not found"


def test_empty_store_returns_empty_inert_payload(client):
    summary = client.get("/api/plugins/mission-control-governance/summary").json()
    records = client.get("/api/plugins/mission-control-governance/records").json()

    assert summary["record_count"] == 0
    assert summary["record_types"] == {}
    assert records["count"] == 0
    assert records["records"] == []
    assert summary["store_status"] == "missing"
    assert summary["error"] is None
    assert records["store_status"] == "missing"
    assert records["error"] is None
    assert summary["trusted_for_execution"] is False
    assert records["execution_enabled"] is False


def test_empty_store_returns_empty_approval_and_evidence_payloads(client):
    approvals = client.get("/api/plugins/mission-control-governance/approval-slices")
    evidence = client.get("/api/plugins/mission-control-governance/evidence-cards")
    actions = client.get("/api/plugins/mission-control-governance/operator-actions")

    assert approvals.status_code == 200
    assert evidence.status_code == 200
    assert actions.status_code == 200
    assert approvals.json() == {
        "trusted_for_execution": False,
        "inert_context_only": True,
        "execution_enabled": False,
        "store_status": "missing",
        "error": None,
        "source": "none",
        "count": 0,
        "approval_slices": [],
    }
    assert evidence.json() == {
        "trusted_for_execution": False,
        "inert_context_only": True,
        "execution_enabled": False,
        "store_status": "missing",
        "error": None,
        "source": "none",
        "count": 0,
        "evidence_cards": [],
    }
    assert actions.json() == {
        "trusted_for_execution": False,
        "inert_context_only": True,
        "execution_enabled": False,
        "store_status": "missing",
        "error": None,
        "source": "none",
        "count": 0,
        "operator_actions": [],
    }


def test_approval_and_evidence_routes_are_get_only(client):
    for path in (
        "/approval-slices",
        "/evidence-cards",
        "/operator-actions",
        "/task-control-envelopes",
        "/start-gate-checks",
    ):
        for method in ("post", "put", "patch", "delete"):
            response = getattr(client, method)(
                f"/api/plugins/mission-control-governance{path}"
            )
            assert response.status_code == 405


def test_approval_slices_prefers_latest_mission_brief_approvals(plugin_api, client):
    store = JsonlRecordStore(plugin_api.record_store_path())
    old = ApprovalSlice(
        approval_id="standalone-old",
        lane="old lane",
        mode="old mode",
        approved_actions=("old action",),
    )
    latest = ApprovalSlice(
        approval_id="mission-latest",
        lane="latest lane",
        mode="focused tests only",
        approved_actions=("add GET endpoint", "add compact panel"),
        forbidden_actions=("push", "deploy"),
        approver="Travis",
        approved_at="2026-06-05T01:00:00Z",
        expires_at="2026-06-06T01:00:00Z",
        metadata={
            "status": "active",
            "reason": "bounded implementation",
            "risk_class": "low",
            "required_approver": "Travis",
            "internal_note": "do not expose this",
        },
    )
    goal = GoalContract(goal_id="goal-approval", statement="Summarize approvals.")
    control = TaskControlEnvelope(active_lane="latest lane", mode="focused tests only")
    store.append(old)
    store.append(
        MissionBrief(
            mission_id="mission-approval",
            title="Approval summaries",
            created_at="2026-06-05T01:01:00Z",
            goal=goal,
            control=control,
            approvals=(latest,),
            evidence=(EvidenceCard(evidence_id="ev-linked", summary="Supports approval"),),
        )
    )

    response = client.get("/api/plugins/mission-control-governance/approval-slices")

    assert response.status_code == 200
    payload = response.json()
    assert payload["trusted_for_execution"] is False
    assert payload["inert_context_only"] is True
    assert payload["execution_enabled"] is False
    assert payload["source"] == "MissionBrief.approvals"
    assert payload["count"] == 1
    assert payload["approval_slices"] == [
        {
            "approval_id": "mission-latest",
            "lane": "latest lane",
            "mode": "focused tests only",
            "approver": "Travis",
            "approved_at": "2026-06-05T01:00:00Z",
            "expires_at": "2026-06-06T01:00:00Z",
            "approved_action_count": 2,
            "forbidden_action_count": 2,
            "evidence_count": 1,
            "status": "active",
            "reason": "bounded implementation",
            "risk_class": "low",
            "required_approver": "Travis",
        }
    ]
    assert "metadata" not in payload["approval_slices"][0]
    assert "internal_note" not in str(payload)


def test_approval_slices_uses_standalone_fallback(plugin_api, client):
    store = JsonlRecordStore(plugin_api.record_store_path())
    store.append(
        ApprovalSlice(
            approval_slice_id="standalone-approval",
            related_action_id="action-1",
            approval_type="operator",
            decision_state="pending",
            required_by="Travis",
            reason="Bounded read-only inspection.",
            safety_conditions=("write records",),
            evidence_ids=("evidence-1",),
            created_at="2026-06-05T02:00:00Z",
        )
    )

    payload = client.get("/api/plugins/mission-control-governance/approval-slices").json()

    assert payload["source"] == "ApprovalSlice"
    assert payload["count"] == 1
    assert payload["approval_slices"][0] == {
        "record_index": 0,
        "approval_slice_id": "standalone-approval",
        "related_action_id": "action-1",
        "approval_type": "operator",
        "decision_state": "pending",
        "required_by": "Travis",
        "reason": "Bounded read-only inspection.",
        "safety_condition_count": 1,
        "evidence_count": 1,
        "created_at": "2026-06-05T02:00:00Z",
        "expires_at": None,
    }


def test_evidence_cards_prefers_latest_mission_brief_evidence(plugin_api, client):
    store = JsonlRecordStore(plugin_api.record_store_path())
    old = EvidenceCard(evidence_id="standalone-old", summary="Old evidence")
    latest = EvidenceCard(
        evidence_id="mission-evidence",
        summary="Focused tests demonstrate inert summaries.",
        artifact_refs=(
            ArtifactRef(
                ref_id="artifact-1",
                kind="test-log",
                location="tests/plugins/test_mission_control_governance_plugin.py",
                description="focused test",
                metadata={"blob": "do not dump"},
            ),
        ),
        metadata={
            "title": "Focused test log",
            "type": "test",
            "source": "pytest",
            "transcript": "do not include transcript",
            "artifact_blob": "do not include blob",
        },
    )
    goal = GoalContract(goal_id="goal-evidence", statement="Summarize evidence.")
    control = TaskControlEnvelope(active_lane="evidence lane", mode="focused tests only")
    store.append(old)
    store.append(
        MissionBrief(
            mission_id="mission-evidence",
            title="Evidence summaries",
            created_at="2026-06-05T03:00:00Z",
            goal=goal,
            control=control,
            evidence=(latest,),
        )
    )

    response = client.get("/api/plugins/mission-control-governance/evidence-cards")

    assert response.status_code == 200
    payload = response.json()
    assert payload["trusted_for_execution"] is False
    assert payload["inert_context_only"] is True
    assert payload["execution_enabled"] is False
    assert payload["source"] == "MissionBrief.evidence"
    assert payload["count"] == 1
    assert payload["evidence_cards"] == [
        {
            "evidence_id": "mission-evidence",
            "summary": "Focused tests demonstrate inert summaries.",
            "artifact_count": 1,
            "artifact_refs_count": 1,
            "title": "Focused test log",
            "type": "test",
            "source": "pytest",
        }
    ]
    assert "metadata" not in payload["evidence_cards"][0]
    assert "artifact_refs" not in payload["evidence_cards"][0]
    assert "transcript" not in str(payload).lower()
    assert "blob" not in str(payload).lower()


def test_evidence_cards_uses_standalone_fallback(plugin_api, client):
    store = JsonlRecordStore(plugin_api.record_store_path())
    store.append(
        EvidenceCard(
            evidence_id="standalone-evidence",
            related_lane="PR-H",
            related_action_id="action-1",
            related_record_type="OperatorAction",
            summary="Fallback evidence summary.",
            evidence_type="test",
            source_label="pytest",
            created_at="2026-06-05T03:00:00Z",
            risk_notes=("No raw metadata exposed.",),
            artifact_refs=(ArtifactRef(ref_id="artifact-1", kind="log", location="focused.log"),),
        )
    )

    payload = client.get("/api/plugins/mission-control-governance/evidence-cards").json()

    assert payload["source"] == "EvidenceCard"
    assert payload["count"] == 1
    assert payload["evidence_cards"][0] == {
        "record_index": 0,
        "evidence_id": "standalone-evidence",
        "related_lane": "PR-H",
        "related_action_id": "action-1",
        "related_record_type": "OperatorAction",
        "summary": "Fallback evidence summary.",
        "evidence_type": "test",
        "source_label": "pytest",
        "created_at": "2026-06-05T03:00:00Z",
        "risk_note_count": 1,
        "artifact_count": 1,
        "artifact_refs_count": 1,
    }



def test_summary_style_routes_do_not_call_read_all(plugin_api, client, monkeypatch):
    store = JsonlRecordStore(plugin_api.record_store_path())
    goal = GoalContract(goal_id="goal-bounded", statement="Bounded summaries only.")
    control = TaskControlEnvelope(active_lane="bounded lane", mode="focused tests only")
    store.append(TaskControlEnvelope(active_lane="fallback lane", mode="read-only"))
    store.append(
        ApprovalSlice(
            approval_id="standalone-approval",
            lane="bounded lane",
            mode="focused tests only",
        )
    )
    store.append(EvidenceCard(evidence_id="standalone-evidence", summary="Standalone evidence"))
    store.append(StartGateCheck(start_gate_id="gate-bounded", envelope_id="envelope-bounded"))
    store.append(
        MissionBrief(
            mission_id="mission-bounded",
            title="Bounded summaries",
            created_at="2026-06-05T04:00:00Z",
            goal=goal,
            control=control,
            approvals=(
                ApprovalSlice(
                    approval_id="mission-approval",
                    lane="bounded lane",
                    mode="focused tests only",
                ),
            ),
            evidence=(EvidenceCard(evidence_id="mission-evidence", summary="Mission evidence"),),
        )
    )

    def fail_read_all(self, record_class=None):
        raise AssertionError("summary route unexpectedly called read_all")

    monkeypatch.setattr(JsonlRecordStore, "read_all", fail_read_all)

    summary = client.get("/api/plugins/mission-control-governance/summary")
    start_gate = client.get("/api/plugins/mission-control-governance/start-gate")
    approvals = client.get("/api/plugins/mission-control-governance/approval-slices")
    evidence = client.get("/api/plugins/mission-control-governance/evidence-cards")
    actions = client.get("/api/plugins/mission-control-governance/operator-actions")
    envelopes = client.get("/api/plugins/mission-control-governance/task-control-envelopes")
    checks = client.get("/api/plugins/mission-control-governance/start-gate-checks")

    assert summary.status_code == 200
    assert start_gate.status_code == 200
    assert approvals.status_code == 200
    assert evidence.status_code == 200
    assert actions.status_code == 200
    assert envelopes.status_code == 200
    assert checks.status_code == 200
    assert summary.json()["record_count"] == 5
    assert start_gate.json()["source"] == "MissionBrief.control"
    assert approvals.json()["source"] == "MissionBrief.approvals"
    assert evidence.json()["source"] == "MissionBrief.evidence"
    assert envelopes.json()["source"] == "TaskControlEnvelope"
    assert checks.json()["source"] == "StartGateCheck"


def test_latest_standalone_fallback_preserves_original_record_index(plugin_api, client):
    store = JsonlRecordStore(plugin_api.record_store_path())
    store.append(GoalContract(goal_id="goal-index", statement="Unrelated record"))
    store.append(TaskControlEnvelope(active_lane="fallback lane", mode="read-only"))

    payload = client.get("/api/plugins/mission-control-governance/start-gate").json()

    assert payload["source"] == "TaskControlEnvelope"
    assert payload["record_index"] == 1


def test_approval_and_evidence_summaries_are_bounded_to_latest_10(plugin_api, client):
    store = JsonlRecordStore(plugin_api.record_store_path())
    for index in range(12):
        store.append(
            ApprovalSlice(
                approval_id=f"approval-{index}",
                lane="bounded lane",
                mode="read-only",
            )
        )
        store.append(
            EvidenceCard(
                evidence_id=f"evidence-{index}",
                summary=f"Evidence {index}",
            )
        )

    approvals = client.get("/api/plugins/mission-control-governance/approval-slices").json()
    evidence = client.get("/api/plugins/mission-control-governance/evidence-cards").json()

    assert approvals["source"] == "ApprovalSlice"
    assert approvals["count"] == 10
    assert [item["approval_id"] for item in approvals["approval_slices"]] == [
        f"approval-{index}" for index in range(2, 12)
    ]
    assert evidence["source"] == "EvidenceCard"
    assert evidence["count"] == 10
    assert [item["evidence_id"] for item in evidence["evidence_cards"]] == [
        f"evidence-{index}" for index in range(2, 12)
    ]

def test_malformed_store_returns_inert_error_payload(plugin_api, client):
    path = plugin_api.record_store_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("{not json}\n", encoding="utf-8")

    summary = client.get("/api/plugins/mission-control-governance/summary")
    records = client.get("/api/plugins/mission-control-governance/records")
    detail = client.get("/api/plugins/mission-control-governance/records/0")

    assert summary.status_code == 200
    assert records.status_code == 200
    assert detail.status_code == 409

    summary_payload = summary.json()
    records_payload = records.json()
    assert summary_payload["record_count"] == 0
    assert summary_payload["record_types"] == {}
    assert summary_payload["store_status"] == "malformed"
    assert "line 1" in summary_payload["error"]
    assert records_payload["count"] == 0
    assert records_payload["records"] == []
    assert records_payload["store_status"] == "malformed"
    assert "line 1" in records_payload["error"]
    assert detail.json()["detail"] == "record store is malformed"


def test_plugin_has_no_runtime_tool_gateway_or_subprocess_imports():
    forbidden = (
        "subprocess",
        "tools.",
        "tools import",
        "gateway.",
        "gateway import",
        "run_agent",
        "resolve_gateway_approval",
        "tools.approval",
        "transcript",
    )
    for path in (
        PLUGIN_DIR / "__init__.py",
        PLUGIN_DIR / "api.py",
        PLUGIN_DIR / "dashboard" / "plugin_api.py",
    ):
        text = path.read_text()
        lowered = text.lower()
        assert not any(token in lowered for token in forbidden), path


def test_dashboard_bundle_registers_read_only_tab_only():
    bundle = (PLUGIN_DIR / "dashboard" / "dist" / "index.js").read_text()
    lowered = bundle.lower()

    assert '__HERMES_PLUGINS__.register("mission-control-governance"' in bundle
    assert "/api/plugins/mission-control-governance/summary" in bundle
    assert "/api/plugins/mission-control-governance/start-gate" in bundle
    assert "/api/plugins/mission-control-governance/start-gate/evaluate" in bundle
    assert "/api/plugins/mission-control-governance/lane-preflight/evaluate" in bundle
    assert "/api/plugins/mission-control-governance/task-control-envelopes" in bundle
    assert "/api/plugins/mission-control-governance/start-gate-checks" in bundle
    assert "/api/plugins/mission-control-governance/approval-slices" in bundle
    assert "/api/plugins/mission-control-governance/evidence-cards" in bundle
    assert "/api/plugins/mission-control-governance/operator-actions" in bundle
    assert "Operator Action Queue" in bundle
    assert "Task Control Envelopes" in bundle
    assert "Start Gate Checks" in bundle
    assert "formatLinkedKanbanTask" in bundle
    assert "linked_kanban_task" in bundle
    assert "Kanban:" in bundle
    assert "/api/plugins/mission-control-governance/records?limit=25" in bundle
    assert "/api/plugins/mission-control-governance/schema" in bundle
    assert "RECORD_DETAIL_URL" in bundle
    for token in (
        "put(",
        "patch(",
        "delete(",
        "execute",
        "approve(",
        "deny(",
        "transcript",
        "resolve_gateway_approval",
        "tools.approval",
    ):
        assert token not in lowered


def test_dashboard_start_gate_evaluator_panel_is_bounded_display_only():
    bundle = (PLUGIN_DIR / "dashboard" / "dist" / "index.js").read_text()
    lowered = bundle.lower()

    assert "Start Gate Evaluator" in bundle
    assert "default-off" in lowered
    assert "inert" in lowered
    assert "no runtime enforcement" in lowered
    assert "SAMPLE_EVALUATOR_ENVELOPE" in bundle
    assert "START_GATE_EVALUATE_URL" in bundle
    assert "postJSON(START_GATE_EVALUATE_URL, SAMPLE_EVALUATOR_ENVELOPE)" in bundle
    assert bundle.count("/api/plugins/mission-control-governance/start-gate/evaluate") == 1
    assert re.findall(r'method:\s*"([A-Z]+)"', bundle) == ["POST"]

    for token in (
        "contenteditable",
        "conversation_history",
        "conversationhistory",
        "transcript",
        "full-text",
        "fulltext",
        "localstorage",
        "sessionstorage",
    ):
        assert token not in lowered
    for control in ("approve", "reject", "execute", "deny"):
        assert not re.search(r"<button[^>]*>[^<]*" + control, lowered)
        assert control + "(" not in lowered


def test_dashboard_lane_preflight_panel_is_bounded_display_only():
    bundle = (PLUGIN_DIR / "dashboard" / "dist" / "index.js").read_text()
    lowered = bundle.lower()

    assert "Lane Preflight" in bundle
    assert "LANE_PREFLIGHT_EVALUATE_URL" in bundle
    assert "postJSON(LANE_PREFLIGHT_EVALUATE_URL, {})" in bundle
    assert "default-off" in lowered
    assert "dry-run" in lowered
    assert "no runtime enforcement" in lowered
    assert "would_block" in bundle
    assert "would_require_approval" in bundle
    assert "Linked Kanban task" in bundle
    assert "formatLinkedKanbanTask(lanePreflight.linked_kanban_task)" in bundle
    assert bundle.count("/api/plugins/mission-control-governance/lane-preflight/evaluate") == 1
    assert re.findall(r'method:\s*"([A-Z]+)"', bundle) == ["POST"]

    for token in (
        "contenteditable",
        "conversation_history",
        "conversationhistory",
        "transcript",
        "full-text",
        "fulltext",
        "localstorage",
        "sessionstorage",
    ):
        assert token not in lowered
    for control in ("approve", "reject", "execute", "deny"):
        assert not re.search(r"<button[^>]*>[^<]*" + control, lowered)
        assert control + "(" not in lowered


def test_dashboard_operating_workspace_panel_is_bounded_display_only():
    bundle = (PLUGIN_DIR / "dashboard" / "dist" / "index.js").read_text()
    lowered = bundle.lower()

    assert "WORKSPACE_STATUS_URL" in bundle
    assert "/api/plugins/mission-control-governance/workspace-status" in bundle
    assert "getJSON(WORKSPACE_STATUS_URL)" in bundle
    assert "Operating Workspace" in bundle
    assert "Execution disabled" in bundle
    assert "use approved lane." in bundle
    assert "Accepted Baseline" in bundle
    assert "Rollback Baseline" in bundle
    assert "Active Lane" in bundle
    assert "Safety Locks" in bundle
    assert "Activity Counts" in bundle
    assert "PR Packet / Evidence / Approval Status" in bundle
    assert "Deployment Status" in bundle
    assert "Stale Context Warnings" in bundle
    assert "display_only" in bundle
    assert "dry_run_only" in bundle
    assert "enforcement_enabled" in bundle
    assert "dispatch_in_gateway" in bundle
    assert "workers_enabled" in bundle
    assert "queue_mutation_enabled" in bundle
    assert "model_routing_enabled" in bundle
    assert "packet_hash" in bundle
    assert "verifier_evidence_record_id" in bundle
    assert "approval_record_id" in bundle
    assert "guard_advisory_only" in bundle
    assert "rollback_used" in bundle
    assert "stale_context" in bundle

    assert bundle.count("/api/plugins/mission-control-governance/workspace-status") == 1
    assert "/api/plugins/mission-control-governance/workspace-status/preview" not in bundle
    assert "postJSON(WORKSPACE_STATUS_URL" not in bundle
    assert "setInterval" not in bundle
    assert "setTimeout" not in bundle
    assert "localStorage" not in bundle
    assert "sessionStorage" not in bundle
    assert "discord_history" not in bundle
    assert "discord_messages" not in bundle
    assert "github_response" not in bundle
    assert "api_response" not in bundle

    assert "button" not in lowered
    assert "onClick: function () { selectRecord" in bundle
    for control in ("approve", "reject", "execute", "deny", "route_model"):
        assert not re.search(r"<button[^>]*>[^<]*" + control, lowered)
        assert control + "(" not in lowered


def test_operator_actions_empty_missing_store_returns_bounded_empty_payload(client):
    response = client.get("/api/plugins/mission-control-governance/operator-actions")

    assert response.status_code == 200
    assert response.json() == {
        "trusted_for_execution": False,
        "inert_context_only": True,
        "execution_enabled": False,
        "store_status": "missing",
        "error": None,
        "source": "none",
        "count": 0,
        "operator_actions": [],
    }


def test_operator_actions_uses_latest_standalone_fallback(plugin_api, client):
    store = JsonlRecordStore(plugin_api.record_store_path())
    store.append(GoalContract(goal_id="goal-action", statement="Unrelated record"))
    store.append(
        OperatorAction(
            action_id="action-standalone",
            title="Review bounded queue",
            lane="PR-G",
            mode="focused tests only",
            requested_action="Review requested action summary.",
            risk_level="low",
            status="requested",
            required_approval="manual approval",
            approval_id="approval-1",
            evidence_ids=("evidence-1", "evidence-2"),
            stop_condition="Stop after tests.",
            created_at="2026-06-05T12:00:00Z",
            expires_at="2026-06-06T12:00:00Z",
            metadata={
                "source": "planning",
                "transcript": "do not expose",
                "artifact_blob": "do not expose",
                "broad_context": "do not expose",
            },
        )
    )

    payload = client.get("/api/plugins/mission-control-governance/operator-actions").json()

    assert payload["trusted_for_execution"] is False
    assert payload["inert_context_only"] is True
    assert payload["execution_enabled"] is False
    assert payload["source"] == "OperatorAction"
    assert payload["count"] == 1
    assert payload["operator_actions"] == [
        {
            "record_index": 1,
            "action_id": "action-standalone",
            "title": "Review bounded queue",
            "lane": "PR-G",
            "mode": "focused tests only",
            "requested_action": "Review requested action summary.",
            "risk_level": "low",
            "status": "requested",
            "required_approval": "manual approval",
            "approval_id": "approval-1",
            "evidence_count": 2,
            "stop_condition": "Stop after tests.",
            "created_at": "2026-06-05T12:00:00Z",
            "expires_at": "2026-06-06T12:00:00Z",
            "source": "planning",
        }
    ]
    assert "metadata" not in payload["operator_actions"][0]
    assert "evidence_ids" not in payload["operator_actions"][0]
    lowered = str(payload).lower()
    assert "transcript" not in lowered
    assert "artifact_blob" not in lowered
    assert "broad_context" not in lowered


def test_operator_actions_are_bounded_to_latest_10(plugin_api, client):
    store = JsonlRecordStore(plugin_api.record_store_path())
    for index in range(12):
        store.append(
            OperatorAction(
                action_id=f"action-{index}",
                title=f"Action {index}",
                lane="bounded lane",
                mode="read-only",
                requested_action=f"Review action {index}.",
            )
        )

    payload = client.get("/api/plugins/mission-control-governance/operator-actions").json()

    assert payload["source"] == "OperatorAction"
    assert payload["count"] == 10
    assert [item["action_id"] for item in payload["operator_actions"]] == [
        f"action-{index}" for index in range(2, 12)
    ]


def test_operator_actions_are_descriptive_context_only(plugin_api, client):
    store = JsonlRecordStore(plugin_api.record_store_path())
    store.append(
        OperatorAction(
            action_id="action-inert",
            title="Request manual review",
            lane="governance lane",
            mode="read-only",
            requested_action="Review this summary manually.",
            metadata={"can_run": True, "command": "ignored"},
        )
    )

    payload = client.get("/api/plugins/mission-control-governance/operator-actions").json()

    assert payload["trusted_for_execution"] is False
    assert payload["inert_context_only"] is True
    assert payload["execution_enabled"] is False
    assert payload["operator_actions"][0]["status"] == "requested"
    assert "can_run" not in str(payload)
    assert "command" not in str(payload)


def test_operator_actions_do_not_read_mission_brief_metadata(plugin_api, client):
    store = JsonlRecordStore(plugin_api.record_store_path())
    store.append(
        MissionBrief(
            mission_id="mission-action-metadata",
            title="Metadata requested action",
            created_at="2026-06-05T13:00:00Z",
            goal=GoalContract(goal_id="goal-action-metadata", statement="Do not infer actions."),
            control=TaskControlEnvelope(active_lane="metadata lane", mode="read-only"),
            metadata={
                "operator_actions": [
                    {
                        "action_id": "metadata-action",
                        "title": "Do not expose",
                        "requested_action": "Do not infer from mission metadata.",
                    }
                ]
            },
        )
    )

    payload = client.get("/api/plugins/mission-control-governance/operator-actions").json()

    assert payload["source"] == "none"
    assert payload["count"] == 0
    assert payload["operator_actions"] == []


def test_summary_style_routes_include_operator_actions_without_read_all(plugin_api, client, monkeypatch):
    store = JsonlRecordStore(plugin_api.record_store_path())
    store.append(
        OperatorAction(
            action_id="action-bounded",
            title="Bounded action",
            lane="bounded lane",
            mode="read-only",
            requested_action="Read compact summary.",
        )
    )

    def fail_read_all(self, record_class=None):
        raise AssertionError("summary route unexpectedly called read_all")

    monkeypatch.setattr(JsonlRecordStore, "read_all", fail_read_all)

    response = client.get("/api/plugins/mission-control-governance/operator-actions")

    assert response.status_code == 200
    assert response.json()["source"] == "OperatorAction"


def test_workspace_status_endpoint_returns_display_only_status(client):
    response = client.get("/api/plugins/mission-control-governance/workspace-status")

    assert response.status_code == 200
    payload = response.json()
    assert payload["display_only"] is True
    assert payload["trusted_for_execution"] is False
    assert payload["execution_enabled"] is False
    assert payload["enforcement_enabled"] is False
    assert payload["dry_run_only"] is True
    assert payload["enforces_runtime"] is False
    assert "accepted_baseline" in payload
    assert "rollback_baseline" in payload
    assert "stale_context" in payload


def test_workspace_status_preview_is_caller_supplied_and_stores_nothing(plugin_api, client):
    response = client.post(
        "/api/plugins/mission-control-governance/workspace-status/preview",
        json={
            "accepted_baseline": {"head": "775f49352189fdec3169f59e3378b6744da2bdda"},
            "lane": {
                "active_lane": "PR #43 verify",
                "declared_baseline_head": "cb42bbc1ed372576079ce8162e6c66fe11872fa4",
                "max_active_lane": 1,
                "active_lane_count": 2,
            },
            "safety": {"dispatch_in_gateway": True},
            "raw_log": "must not be stored or exposed",
            "token": "secret-token-value",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["stored"] is False
    assert payload["source"] == "caller_supplied_workspace_status_preview"
    warnings = set(payload["stale_context"]["warnings"])
    assert "baseline_mismatch" in warnings
    assert "active_lane_count_exceeds_max" in warnings
    assert "dispatch_not_false" in warnings
    rendered = str(payload).lower()
    assert "must not be stored or exposed" not in rendered
    assert "secret-token-value" not in rendered
    assert plugin_api.record_store_path().exists() is False


def test_workspace_status_preview_flags_accepted_live_ahead_of_deployed_dashboard(plugin_api, client):
    response = client.post(
        "/api/plugins/mission-control-governance/workspace-status/preview",
        json={
            "accepted_baseline": {
                "head": "1111111111111111111111111111111111111111",
                "runtime_path": "/home/jenny/.hermes/hermes-runtime-old",
            },
            "source_control": {
                "branch": "accepted-live/approval-safety-5ad8906",
                "accepted_live_head": "2222222222222222222222222222222222222222",
                "latest_merged_pr": "108",
            },
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["stored"] is False
    assert payload["deployment_gap"]["state"] == "merged_not_deployed"
    assert payload["deployment_gap"]["dashboard_deploy_needed"] is True
    assert payload["deployment_gap"]["accepted_live_head"] == "2222222222222222222222222222222222222222"
    assert payload["deployment_gap"]["deployed_head"] == "1111111111111111111111111111111111111111"
    assert payload["deployment_gap"]["latest_merged_pr"] == "108"
    assert "accepted_live_head_not_deployed" in payload["stale_context"]["warnings"]
    assert plugin_api.record_store_path().exists() is False


def test_runtime_provenance_preview_is_inert_and_stores_nothing(plugin_api, client):
    head = "8ef64e370a51bc19e97fec1526f5bb3d42025a09"
    runtime = {
        "path": "/home/jenny/.hermes/hermes-runtime-current",
        "exists": True,
        "git_healthy": True,
        "head": head,
        "dirty_files": [],
        "untracked_files": [],
        "error": "",
    }

    response = client.post(
        "/api/plugins/mission-control-governance/workspace/runtime-provenance/preview",
        json={
            "source": {"head": head},
            "accepted_baseline": runtime,
            "dashboard_runtime": runtime,
            "gateway_runtime": runtime,
            "rollback_runtime": runtime,
            "dispatch_in_gateway": False,
            "active_lane_count": 0,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["source"] == "caller_supplied_runtime_provenance_preview"
    assert payload["stored"] is False
    assert payload["display_only"] is True
    assert payload["dry_run_only"] is True
    assert payload["execution_enabled"] is False
    assert payload["dispatch_enabled"] is False
    assert payload["session_send_enabled"] is False
    assert payload["primary_status"] == "CLEAN_AND_ALIGNED"
    assert payload["autonomy_blocked"] is False
    assert plugin_api.record_store_path().exists() is False


def test_read_only_autonomy_preview_is_inert_and_stores_nothing(plugin_api, client):
    forbidden_actions = [
        "file write",
        "commit",
        "PR creation",
        "merge",
        "deploy",
        "restart",
        "runtime switch",
        "Waha",
        "social",
        "payment",
        "model routing",
        "queue mutation",
        "worker",
        "timer",
        "daemon",
        "dispatch",
        "session-send",
    ]

    response = client.post(
        "/api/plugins/mission-control-governance/workspace/autonomy-eligibility/preview",
        json={
            "runtime_provenance": {
                "primary_status": "CLEAN_AND_ALIGNED",
                "autonomy_blocked": False,
                "autonomy_blocked_reasons": [],
            },
            "approval": {
                "approval_id": "approval-read-only-1",
                "status": "approved",
                "approval_mode": "one_time",
                "approval_scope": "project-hermes-mission-control:read-only-inspection",
                "action_class": "read_only_inspection",
                "expires_at": "2099-01-01T00:00:00Z",
                "consumed_at": "",
            },
            "run": {
                "run_id": "run-read-only-1",
                "project_id": "project-hermes-mission-control",
                "approval_id": "approval-read-only-1",
                "lane_type": "read_only_inspection",
                "status": "requested",
                "dispatch_state": False,
                "forbidden_actions": forbidden_actions,
            },
            "lane": {
                "lane_type": "read_only_inspection",
                "forbidden_actions": forbidden_actions,
            },
            "bridge": {"manual_start_only": True},
            "report_inbox_ready": True,
            "active_mutation_lane_count": 0,
            "capabilities": {},
            "now": "2026-06-19T00:00:00Z",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["source"] == "caller_supplied_read_only_autonomy_preview"
    assert payload["stored"] is False
    assert payload["eligible"] is True
    assert payload["would_execute"] is False
    assert payload["dry_run_only"] is True
    assert payload["execution_enabled"] is False
    assert payload["dispatch_enabled"] is False
    assert payload["session_send_enabled"] is False
    assert plugin_api.record_store_path().exists() is False


def test_scoped_pr_and_execution_packet_previews_are_inert_and_store_nothing(plugin_api, client):
    forbidden_actions = [
        "merge",
        "deploy",
        "restart",
        "runtime switch",
        "Waha",
        "social",
        "payment",
        "model routing",
        "queue mutation",
        "worker",
        "timer",
        "daemon",
        "dispatch",
        "session-send",
    ]
    payload = {
        "mode": "scoped_pr",
        "runtime_provenance": {
            "primary_status": "CLEAN_AND_ALIGNED",
            "autonomy_blocked": False,
            "autonomy_blocked_reasons": [],
        },
        "approval": {
            "approval_id": "approval-pr-1",
            "status": "approved",
            "approval_mode": "one_time",
            "approval_scope": "project-hermes-mission-control:scoped-pr:mission_control/",
            "action_class": "pr_creation",
            "approved_files": ["mission_control/autonomy_eligibility.py"],
            "expires_at": "2099-01-01T00:00:00Z",
        },
        "run": {
            "run_id": "run-pr-1",
            "project_id": "project-hermes-mission-control",
            "approval_id": "approval-pr-1",
            "lane_type": "pr_creation",
            "status": "requested",
            "dispatch_state": False,
            "forbidden_actions": forbidden_actions,
        },
        "lane": {
            "lane_type": "pr_creation",
            "allowed_files": ["mission_control/autonomy_eligibility.py"],
            "forbidden_actions": forbidden_actions,
            "tests_required": True,
            "review_required": True,
        },
        "report_contract": {"required": True, "tests_required": True, "review_required": True},
        "active_mutation_lane_count": 1,
        "bridge": {"manual_start_only": True},
        "capabilities": {},
        "now": "2026-06-19T00:00:00Z",
    }

    scoped = client.post(
        "/api/plugins/mission-control-governance/workspace/scoped-pr-eligibility/preview",
        json=payload,
    )
    packet = client.post(
        "/api/plugins/mission-control-governance/workspace/execution-packet/preview",
        json=payload,
    )
    worker_packet = client.post(
        "/api/plugins/mission-control-governance/workspace/execution-packet/preview",
        json={
            **payload,
            "mode": "worker_node",
            "run": {
                **payload["run"],
                "objective": "Prepare a bounded scoped PR packet.",
            },
            "worker_node": {
                "parent_run_id": "run-pr-1",
                "worker_identity": "codex",
                "worker_host_label": "laptop-codex",
                "worker_kind": "laptop_codex",
                "presence_status": "online",
            },
        },
    )

    assert scoped.status_code == 200
    scoped_payload = scoped.json()
    assert scoped_payload["source"] == "caller_supplied_scoped_pr_lane_preview"
    assert scoped_payload["stored"] is False
    assert scoped_payload["eligible"] is True
    assert scoped_payload["would_execute"] is False
    assert scoped_payload["would_create_pr"] is False
    assert scoped_payload["dispatch_enabled"] is False
    assert scoped_payload["session_send_enabled"] is False
    assert scoped_payload["worker_dispatch_enabled"] is False

    assert packet.status_code == 200
    packet_payload = packet.json()
    assert packet_payload["source"] == "caller_supplied_execution_packet_preview"
    assert packet_payload["stored"] is False
    assert packet_payload["packet"]["mode"] == "scoped_pr"
    assert packet_payload["would_execute"] is False
    assert packet_payload["would_dispatch"] is False
    assert packet_payload["would_session_send"] is False
    assert packet_payload["worker_dispatch_enabled"] is False

    assert worker_packet.status_code == 200
    worker_packet_payload = worker_packet.json()
    assert worker_packet_payload["stored"] is False
    assert worker_packet_payload["eligible"] is True
    assert worker_packet_payload["packet"]["mode"] == "worker_node"
    assert worker_packet_payload["packet"]["worker_node_contract"]["worker_host_label"] == "laptop-codex"
    assert worker_packet_payload["packet"]["worker_node_contract"]["manual_handoff_only"] is True
    assert worker_packet_payload["would_execute"] is False
    assert worker_packet_payload["would_dispatch"] is False
    assert worker_packet_payload["would_session_send"] is False
    assert worker_packet_payload["worker_dispatch_enabled"] is False
    assert plugin_api.record_store_path().exists() is False


def test_tool_permission_preview_classifies_write_paths_and_stores_nothing(plugin_api, client):
    response = client.post(
        "/api/plugins/mission-control-governance/workspace/tool-permissions/preview",
        json={
            "paths": [
                {"path_id": "audit_read", "read_only_safe": True, "tools": ["read_file"]},
                {"path_id": "manual_relay", "manual_start_only": True, "append_records": True},
                {"path_id": "laptop_codex", "worker_node_path": True, "write_capable_tools": True},
            ]
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["source"] == "mission_control_control_path_permission_preview_v1"
    assert payload["stored"] is False
    assert payload["permission_classification"] == "write_capable_not_safe_for_autonomy"
    assert payload["execution_enabled"] is False
    assert payload["dispatch_enabled"] is False
    assert payload["session_send_enabled"] is False
    assert payload["worker_dispatch_enabled"] is False
    assert "laptop_codex" in payload["write_capable_path_ids"]
    classifications = {path["path_id"]: path["permission_classification"] for path in payload["paths"]}
    assert classifications["audit_read"] == "read_only_safe"
    assert classifications["manual_relay"] == "manual_only"
    assert classifications["laptop_codex"] == "write_capable_not_safe_for_autonomy"
    assert plugin_api.record_store_path().exists() is False


def test_child_and_worker_node_run_records_stay_inert(plugin_api, client):
    child_response = client.post(
        "/api/plugins/mission-control-governance/workspace/child-runs/create",
        json={
            "child_run_id": "child-run-1",
            "parent_run_id": "run-parent-1",
            "project_id": "project-hermes-mission-control",
            "agent_identity": "jenny-child",
            "delegation_source": "mission-control-preview",
            "objective": "Inspect bounded context.",
            "allowed_actions": ["read files"],
            "forbidden_actions": ["dispatch", "deploy"],
            "status": "running",
            "dispatch_enabled": True,
            "worker_dispatch_enabled": True,
        },
    )
    worker_response = client.post(
        "/api/plugins/mission-control-governance/workspace/worker-node-runs/create",
        json={
            "worker_run_id": "worker-run-1",
            "parent_run_id": "run-parent-1",
            "project_id": "project-hermes-mission-control",
            "worker_identity": "codex",
            "worker_host_label": "laptop-codex",
            "objective": "Prepare a scoped PR.",
            "blocked_reasons": ["worker node offline"],
            "status": "blocked",
            "worker_dispatch_enabled": True,
        },
    )

    assert child_response.status_code == 200
    child_payload = child_response.json()
    assert child_payload["stored"] is True
    assert child_payload["dispatch_enabled"] is False
    assert child_payload["session_send_enabled"] is False
    assert child_payload["worker_dispatch_enabled"] is False
    assert child_payload["child_run"]["metadata"]["dispatch_enabled"] is False
    assert child_payload["child_run"]["metadata"]["worker_dispatch_enabled"] is False

    assert worker_response.status_code == 200
    worker_payload = worker_response.json()
    assert worker_payload["stored"] is True
    assert worker_payload["dispatch_enabled"] is False
    assert worker_payload["session_send_enabled"] is False
    assert worker_payload["worker_dispatch_enabled"] is False
    assert worker_payload["worker_node_run"]["worker_host_label"] == "laptop-codex"
    assert worker_payload["worker_node_run"]["worker_dispatch_enabled"] is False
    assert worker_payload["worker_node_run"]["metadata"]["worker_dispatch_enabled"] is False

    child_runs = client.get("/api/plugins/mission-control-governance/workspace/child-runs")
    worker_runs = client.get("/api/plugins/mission-control-governance/workspace/worker-node-runs")
    assert child_runs.status_code == 200
    assert child_runs.json()["count"] == 1
    assert child_runs.json()["child_runs"][0]["record_type"] == "ChildRunRecord"
    assert worker_runs.status_code == 200
    assert worker_runs.json()["count"] == 1
    assert worker_runs.json()["worker_node_runs"][0]["record_type"] == "WorkerNodeRunRecord"

    records = JsonlRecordStore(plugin_api.record_store_path())
    assert len(records.read_all(ChildRunRecord)) == 1
    assert len(records.read_all(WorkerNodeRunRecord)) == 1


def test_workspace_status_has_no_action_routes(client):
    for path in (
        "/api/plugins/mission-control-governance/workspace-status/execute",
        "/api/plugins/mission-control-governance/workspace-status/approve",
        "/api/plugins/mission-control-governance/workspace-status/deploy",
    ):
        response = client.post(path, json={})
        assert response.status_code == 404


def test_workspace_status_get_includes_latest_handoff_record_without_mutation(plugin_api, client):
    JsonlRecordStore(plugin_api.record_store_path()).append(
        OperatingWorkspaceHandoffRecord(
            handoff_id="handoff-001",
            created_at="2026-06-09T00:00:00Z",
            source="operator_supplied_handoff",
            active_lane="PR #45 Operating Workspace handoff records",
            lane_mode="bounded display-only PR",
            accepted_head="775f49352189fdec3169f59e3378b6744da2bdda",
            rollback_head="cb42bbc1ed372576079ce8162e6c66fe11872fa4",
            dispatch_in_gateway=False,
            max_active_lane=1,
            active_lane_count=1,
            target_type="pr",
            target_id="45",
            target_head="775f49352189fdec3169f59e3378b6744da2bdda",
            status="active",
            last_result="PR #44 accepted",
            next_action="Review PR #45",
        )
    )

    response = client.get("/api/plugins/mission-control-governance/workspace-status")

    assert response.status_code == 200
    payload = response.json()
    assert payload["display_only"] is True
    assert payload["dry_run_only"] is True
    assert payload["enforces_runtime"] is False
    assert payload["latest_handoff"]["present"] is True
    assert payload["latest_handoff"]["handoff_id"] == "handoff-001"
    assert payload["latest_handoff"]["target_id"] == "45"
    assert payload["latest_handoff"]["display_only"] is True
    assert payload["stored"] is False


def test_workspace_status_preview_remains_unstored_with_caller_supplied_handoff(client):
    response = client.post(
        "/api/plugins/mission-control-governance/workspace-status/preview",
        json={
            "latest_handoff": {
                "handoff_id": "preview-001",
                "accepted_head": "775f49352189fdec3169f59e3378b6744da2bdda",
                "target_type": "pr",
                "target_id": "45",
                "target_head": "775f49352189fdec3169f59e3378b6744da2bdda",
                "dry_run_only": False,
                "enforces_runtime": True,
                "display_only": False,
                "raw_log": "forbidden",
                "token": "secret-token",
            }
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["stored"] is False
    assert payload["latest_handoff"]["present"] is True
    assert payload["latest_handoff"]["handoff_id"] == "preview-001"
    assert payload["latest_handoff"]["dry_run_only"] is True
    assert payload["latest_handoff"]["enforces_runtime"] is False
    assert payload["latest_handoff"]["display_only"] is True
    rendered = str(payload).lower()
    assert "secret-token" not in rendered
    assert "raw_log" not in rendered


def test_dashboard_operating_workspace_latest_handoff_panel_is_display_only():
    bundle = (PLUGIN_DIR / "dashboard" / "dist" / "index.js").read_text(encoding="utf-8")

    assert "Latest Lane Handoff" in bundle
    assert "No lane handoff record found." in bundle
    assert "display_only" in bundle
    assert "enforces_runtime" in bundle
    assert "workspace-status/preview" not in bundle
    assert "setInterval" not in bundle
    assert "setTimeout" not in bundle
    assert "localStorage" not in bundle
    assert "sessionStorage" not in bundle
    assert not re.search(r'"(?:Approve|Reject|Execute|Run|Merge)"', bundle)
    assert "button" not in bundle.lower()


def test_workspace_status_get_uses_latest_accepted_baseline_record_without_mutation(plugin_api, client):
    JsonlRecordStore(plugin_api.record_store_path()).append(
        AcceptedBaselineRecord(
            baseline_id="baseline-001",
            recorded_at="2026-06-09T00:00:00Z",
            source="operator_accepted_baseline",
            runtime_path="/home/jenny/.hermes/hermes-runtime-handoff-8c560c7",
            head="8c560c739606564aeeb4db464fe1989cb67a40b6",
            rollback_runtime_path="/home/jenny/.hermes/hermes-runtime-workspaceui-d11681f",
            rollback_head="d11681f81c7cd16a99c53649f157040b2d10a89f",
            dispatch_in_gateway=False,
            active_kanban=0,
            max_active_lane=1,
            issue="none",
        )
    )

    response = client.get("/api/plugins/mission-control-governance/workspace-status")

    assert response.status_code == 200
    payload = response.json()
    assert payload["stored"] is False
    assert payload["accepted_baseline_source"] == "record"
    assert payload["accepted_baseline"]["runtime_path"] == "/home/jenny/.hermes/hermes-runtime-handoff-8c560c7"
    assert payload["accepted_baseline"]["head"] == "8c560c739606564aeeb4db464fe1989cb67a40b6"
    assert payload["rollback_baseline"]["runtime_path"] == "/home/jenny/.hermes/hermes-runtime-workspaceui-d11681f"
    assert payload["rollback_baseline"]["head"] == "d11681f81c7cd16a99c53649f157040b2d10a89f"
    assert payload["display_only"] is True
    assert payload["dry_run_only"] is True
    assert payload["enforces_runtime"] is False
    assert payload["record_store"]["status"] == "ok"
    assert payload["control_plane_records"]["active_run_count"] == 0


def test_workspace_status_get_uses_record_sourced_active_runs_not_static_lane(plugin_api, client):
    store = JsonlRecordStore(plugin_api.record_store_path())
    store.append(
        AcceptedBaselineRecord(
            baseline_id="accepted-pr69-control-plane-af1eafe",
            runtime_path="/home/jenny/.hermes/hermes-runtime-control-plane-af1eafe",
            head="af1eafe23eb25eabd92496e0ea04db39e099acdf",
            rollback_runtime_path="/home/jenny/.hermes/hermes-runtime-manual-session-link-ui-d7d1e0d",
            rollback_head="d7d1e0d758a64783f4de435f06450be218e8a2bf",
            dispatch_in_gateway=False,
            active_kanban=0,
            max_active_lane=1,
        )
    )
    store.append(
        RunRecord(
            run_id="run-1",
            project_id="project-hermes-mission-control",
            lane_type="read_only_inspection",
            title="Read-only status reconciliation",
            status="running",
            execution_mode="manual_copy",
            baseline_head="af1eafe23eb25eabd92496e0ea04db39e099acdf",
        )
    )

    response = client.get("/api/plugins/mission-control-governance/workspace-status")

    assert response.status_code == 200
    payload = response.json()
    assert payload["accepted_baseline_source"] == "record"
    assert payload["accepted_baseline"]["head"] == "af1eafe23eb25eabd92496e0ea04db39e099acdf"
    assert payload["lane"]["active_lane"] == "Read-only status reconciliation"
    assert payload["lane"]["active_lane_count"] == 1
    assert payload["activity"]["active_runs"] == 1
    assert payload["control_plane_records"]["latest_active_run_id"] == "run-1"


def test_workspace_profile_memory_storage_is_read_only(plugin_api, client, monkeypatch):
    monkeypatch.setattr(
        plugin_api,
        "_profile_memory_storage_projection",
        lambda: {
            "profile_count": 2,
            "profiles": [
                {
                    "profile": "default",
                    "home": "/home/jenny/.hermes",
                    "data": {
                        "path": "/home/jenny/.hermes",
                        "scope": "default_profile_state_sessions_memories",
                        "exists": True,
                        "bytes": 6_442_450_944,
                        "components": {
                            "state": {"path": "/home/jenny/.hermes/state.db", "exists": True, "bytes": 3_652_108_288},
                            "sessions": {"path": "/home/jenny/.hermes/sessions", "exists": True, "bytes": 2_790_309_888},
                            "memories": {"path": "/home/jenny/.hermes/memories", "exists": True, "bytes": 32_768},
                        },
                    },
                    "memory": {"bytes": 1100, "chars": 1100, "exists": True, "limit_chars": 2200, "percent_used": 50},
                    "mount": {
                        "path": "/",
                        "total_bytes": 17_179_869_184,
                        "used_bytes": 12_884_901_888,
                        "free_bytes": 4_294_967_296,
                        "percent_used": 75,
                    },
                    "recall_file_bytes": 1300,
                    "user": {"bytes": 200, "chars": 200, "exists": True, "limit_chars": 1375, "percent_used": 15},
                    "total_bytes": 6_442_450_944,
                },
                {
                    "profile": "wahainspection",
                    "home": "/home/jenny/.hermes/profiles/wahainspection",
                    "data": {
                        "path": "/home/jenny/.hermes/profiles/wahainspection",
                        "scope": "profile_directory",
                        "exists": True,
                        "bytes": 49_283_072,
                        "components": {
                            "state": {"path": "/home/jenny/.hermes/profiles/wahainspection/state.db", "exists": True, "bytes": 36_696_064},
                            "sessions": {"path": "/home/jenny/.hermes/profiles/wahainspection/sessions", "exists": True, "bytes": 12_582_912},
                            "memories": {"path": "/home/jenny/.hermes/profiles/wahainspection/memories", "exists": True, "bytes": 4096},
                        },
                    },
                    "memory": {"bytes": 0, "chars": 0, "exists": False, "limit_chars": 2200, "percent_used": 0},
                    "mount": {
                        "path": "/",
                        "total_bytes": 17_179_869_184,
                        "used_bytes": 12_884_901_888,
                        "free_bytes": 4_294_967_296,
                        "percent_used": 75,
                    },
                    "recall_file_bytes": 0,
                    "user": {"bytes": 0, "chars": 0, "exists": False, "limit_chars": 1375, "percent_used": 0},
                    "total_bytes": 49_283_072,
                },
            ],
            "total_bytes": 6_491_734_016,
            "total_memory_bytes": 1100,
            "total_profile_data_bytes": 6_491_734_016,
            "total_recall_file_bytes": 1300,
            "total_user_bytes": 200,
            "errors": [],
        },
    )

    response = client.get("/api/plugins/mission-control-governance/workspace/profile-memory-storage")

    assert response.status_code == 200
    payload = response.json()
    assert payload["stored"] is False
    assert payload["display_only"] is True
    assert payload["dispatch_enabled"] is False
    assert payload["profile_count"] == 2
    assert payload["profiles"][0]["profile"] == "default"
    assert payload["profiles"][0]["total_bytes"] == 6_442_450_944
    assert payload["profiles"][0]["data"]["components"]["state"]["bytes"] == 3_652_108_288
    assert payload["profiles"][0]["data"]["components"]["sessions"]["bytes"] == 2_790_309_888
    assert payload["profiles"][0]["memory"]["percent_used"] == 50
    assert payload["profiles"][0]["mount"]["path"] == "/"
    assert payload["profiles"][0]["mount"]["total_bytes"] == 17_179_869_184
    assert payload["profiles"][0]["mount"]["used_bytes"] == 12_884_901_888
    assert payload["profiles"][0]["mount"]["percent_used"] == 75
    assert payload["profiles"][1]["profile"] == "wahainspection"


def test_workspace_status_preview_accepts_accepted_baseline_source_but_remains_unstored(client):
    response = client.post(
        "/api/plugins/mission-control-governance/workspace-status/preview",
        json={
            "accepted_baseline_record": {
                "baseline_id": "preview-baseline",
                "runtime_path": "/home/jenny/.hermes/hermes-runtime-handoff-8c560c7",
                "head": "8c560c739606564aeeb4db464fe1989cb67a40b6",
                "rollback_runtime_path": "/home/jenny/.hermes/hermes-runtime-workspaceui-d11681f",
                "rollback_head": "d11681f81c7cd16a99c53649f157040b2d10a89f",
                "token": "placeholder-token",
                "raw_log": "forbidden",
            }
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["stored"] is False
    assert payload["accepted_baseline_source"] == "record"
    assert payload["accepted_baseline"]["head"] == "8c560c739606564aeeb4db464fe1989cb67a40b6"
    rendered = str(payload).lower()
    assert "placeholder-token" not in rendered
    assert "raw_log" not in rendered
