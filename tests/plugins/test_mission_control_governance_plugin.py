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
    ApprovalSlice,
    ArtifactRef,
    EvidenceCard,
    GoalContract,
    JsonlRecordStore,
    JennyReportRecord,
    LaneRequestRecord,
    MissionBrief,
    OperatingWorkspaceHandoffRecord,
    OperatorAction,
    ProjectRecord,
    StartGateCheck,
    TaskControlEnvelope,
    VerifierWorkflowEvidenceRecord,
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
    assert hermes_state["missing_state_fields"] == []
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
    ]


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
        "Manual transport only — paste into Discord. This does not start work.",
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
        "Send to Jenny — disabled",
        "WORKSPACE_PROJECTS_URL",
        "WORKSPACE_LANE_REQUESTS_URL",
        "WORKSPACE_REPORTS_URL",
        "WORKSPACE_REPORT_CREATE_URL",
        "WORKSPACE_PROJECT_STATE_URL",
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
        "Paste Jenny’s report manually",
        "Manual transport only — paste into Discord. This does not start work.",
        "Draft packet only. This is not an active lane.",
        "Read-only/manual-copy Mission Control project workspace lane.",
        "Use this project card as context",
        "No dispatch, queue, Waha, model routing, enforcement, automatic session send, storage, timers, or hidden workers.",
        "PROJECT_WORKSPACE_CARDS",
        "ProjectWorkspacePanel",
        "ProjectWorkspaceCard",
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
        "/global-resource-guard": {"GET"},
        "/global-resource-guard/evaluate": {"POST"},
        "/storage-guard": {"GET"},
        "/storage-guard/evaluate": {"POST"},
        "/verifier-workflow": {"GET"},
        "/pr-merge-verifier-gate": {"GET"},
        "/workspace-status": {"GET"},
        "/workspace-status/preview": {"POST"},
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
        "/workspace/project-templates": {"GET"},
        "/workspace/projects/seed-defaults": {"POST"},
        "/workspace/lane-requests": {"GET"},
        "/workspace/lane-requests/create": {"POST"},
        "/workspace/reports": {"GET"},
        "/workspace/reports/create": {"POST"},
        "/workspace/project-state": {"GET"},
        "/records": {"GET"},
        "/schema": {"GET"},
        "/records/{record_index}": {"GET"},
    }

    for path in (
        "/health",
        "/summary",
        "/start-gate",
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
        "/workspace/project-templates",
        "/workspace/lane-requests",
        "/workspace/reports",
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
            "/api/plugins/mission-control-governance/global-resource-guard/evaluate"
        )
        assert response.status_code == 405
        response = getattr(client, method)(
            "/api/plugins/mission-control-governance/storage-guard/evaluate"
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
    assert "disk_warning_threshold_percent" in payload["unresolved_policy_fields"]


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
    assert "Execution disabled — use approved lane." in bundle
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
