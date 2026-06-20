from dataclasses import FrozenInstanceError

import pytest

from mission_control.records.models import (
    ApprovalRecord,
    ApprovalSlice,
    ArtifactRef,
    ChallengeReviewRecord,
    ChildRunRecord,
    EvidenceCard,
    GoalContract,
    GitHubBridgeMailboxStatusRecord,
    GitHubBridgeMessageRecord,
    JennyBridgeMessageRequestRecord,
    JennyBridgeMessageResponseRecord,
    JennyBridgePollerStatusRecord,
    JennyReplyReviewRecord,
    JennyReportRecord,
    LaneRequestRecord,
    MissionBrief,
    AcceptedBaselineRecord,
    OperatingWorkspaceHandoffRecord,
    OperatorAction,
    ProjectBriefRecord,
    ProjectRecord,
    ReportRecord,
    RECORD_TYPES,
    RoomContractRecord,
    RoomJournalEventRecord,
    RunRecord,
    StartGateCheck,
    TaskControlEnvelope,
    WorkerNodeRunRecord,
)


def _assert_inert_execution_metadata(metadata):
    assert metadata["would_execute"] is False
    assert metadata["would_dispatch"] is False
    assert metadata["would_session_send"] is False
    assert metadata["execution_enabled"] is False
    assert metadata["dispatch_enabled"] is False
    assert metadata["dispatch_in_gateway"] is False
    assert metadata["dispatch_state"] is False
    assert metadata["execution_ready"] is False
    assert metadata["live_operations_enabled"] is False
    assert metadata["send_to_jenny_enabled"] is False
    assert metadata["session_send_enabled"] is False
    assert metadata["worker_enabled"] is False
    assert metadata["workers_enabled"] is False
    assert metadata["worker_dispatch_enabled"] is False
    assert metadata["timer_enabled"] is False
    assert metadata["daemon_enabled"] is False
    assert metadata["waha_enabled"] is False
    assert metadata["social_enabled"] is False
    assert metadata["payment_enabled"] is False
    assert metadata["queue_mutation_enabled"] is False
    assert metadata["model_routing_enabled"] is False
    assert metadata["trusted_for_execution"] is False
    assert metadata["inert_context_only"] is True


def test_project_record_round_trips_workspace_fields():
    record = ProjectRecord(
        project_id="project-hermes",
        name="Hermes / Mission Control",
        status="live",
        current_goal="Make Mission Control the workspace.",
        next_recommended_lane="Draft the next safe lane.",
        mistakes_guards="No dispatch without approval.",
        source_of_truth="Mission Control",
        profile="default",
        created_at="2026-06-10T10:00:00Z",
        updated_at="2026-06-10T10:01:00Z",
        metadata={"source": "unit-test"},
    )

    data = record.to_dict()

    assert data["project_id"] == "project-hermes"
    assert data["name"] == "Hermes / Mission Control"
    assert data["metadata"] == {"source": "unit-test"}
    assert ProjectRecord.from_dict(data) == record
    assert RECORD_TYPES["ProjectRecord"] is ProjectRecord


def test_room_contract_record_round_trips_source_of_truth_paths():
    record = RoomContractRecord(
        room_id="room-hermes-mission-control",
        project_id="project-hermes-mission-control",
        title="Hermes / Mission Control",
        status="active",
        brief_path="projects/hermes-mission-control/current-state.md",
        facts_path="projects/hermes-mission-control/facts",
        specs_path="projects/hermes-mission-control/specs",
        decisions_path="projects/hermes-mission-control/decisions",
        reports_path="projects/hermes-mission-control/reports",
        mailbox_path="projects/hermes-mission-control/mailbox",
        journal_path="projects/hermes-mission-control/journal",
        owner="travis",
        allowed_actions=("docs", "schemas"),
        forbidden_actions=("dispatch", "gateway restart"),
        stop_conditions=("protected surface",),
        created_at="2026-06-13T05:00:00Z",
        updated_at="2026-06-13T05:01:00Z",
        metadata={"source": "unit-test"},
    )

    data = record.to_dict()

    assert data["room_id"] == "room-hermes-mission-control"
    assert data["allowed_actions"] == ["docs", "schemas"]
    assert data["forbidden_actions"] == ["dispatch", "gateway restart"]
    assert RoomContractRecord.from_dict(data) == record
    assert isinstance(RoomContractRecord.from_dict(data).stop_conditions, tuple)
    assert RECORD_TYPES["RoomContractRecord"] is RoomContractRecord


def test_room_journal_event_record_forces_inert_append_only_flags():
    record = RoomJournalEventRecord(
        event_id="event-001",
        room_id="room-hermes-mission-control",
        project_id="project-hermes-mission-control",
        event_type="challenge_passed",
        summary="Challenge review cleared a read-only lane.",
        event_time="2026-06-13T05:00:00Z",
        actor="jenny",
        source="challenge-review",
        artifact_refs=("docs/mission-control/example.md",),
        parent_event_ids=("event-000",),
        append_only=False,
        trusted_for_execution=True,
        metadata={"decision_state": "clear_and_safe"},
    )

    data = record.to_dict()

    assert data["append_only"] is True
    assert data["trusted_for_execution"] is False
    assert data["artifact_refs"] == ["docs/mission-control/example.md"]
    assert RoomJournalEventRecord.from_dict(data) == record
    assert isinstance(RoomJournalEventRecord.from_dict(data).artifact_refs, tuple)
    assert RECORD_TYPES["RoomJournalEventRecord"] is RoomJournalEventRecord


def test_project_brief_record_round_trips_project_intake_fields():
    record = ProjectBriefRecord(
        brief_id="brief-1",
        project_id="project-hermes",
        name="Hermes / Mission Control",
        outcome="Make Jenny reliable before autonomy.",
        audience="Travis",
        source_of_truth="Mission Control records",
        success_criteria=("status agrees", "challenge gate exists"),
        constraints=("manual-copy only",),
        forbidden_actions=("dispatch", "session-send"),
        approval_rules=("deploy requires explicit approval",),
        context_pack_path="context-packs/mission-control-current.md",
        status="active",
        created_at="2026-06-12T10:00:00Z",
        updated_at="2026-06-12T10:01:00Z",
        metadata={"challenge_gate_required": True},
    )

    data = record.to_dict()

    assert data["success_criteria"] == ["status agrees", "challenge gate exists"]
    assert data["forbidden_actions"] == ["dispatch", "session-send"]
    assert ProjectBriefRecord.from_dict(data) == record
    assert isinstance(ProjectBriefRecord.from_dict(data).approval_rules, tuple)
    assert RECORD_TYPES["ProjectBriefRecord"] is ProjectBriefRecord


def test_challenge_review_record_round_trips_judgment_fields():
    record = ChallengeReviewRecord(
        review_id="review-1",
        project_id="project-hermes",
        request_summary="Make Jenny post automatically every day.",
        decision_state="wrong_approach_likely",
        challenge_categories=("wrong_approach", "protected_surface"),
        blocking_verdicts=("blocks_lane_draft", "requires_travis_approval"),
        recommended_path="Start with scheduled drafts and approval-gated posting.",
        concerns=("automation before observability",),
        questions=("Which platform fails first?",),
        required_spec_updates=("add posting failure policy",),
        required_approvals=("public posting approval",),
        suggested_lane_title="Read-only scheduler readiness audit",
        status="draft",
        created_at="2026-06-12T10:00:00Z",
        reviewed_by="jenny",
        metadata={"manual_copy_only": True},
    )

    data = record.to_dict()

    assert data["decision_state"] == "wrong_approach_likely"
    assert data["challenge_categories"] == ["wrong_approach", "protected_surface"]
    assert data["blocking_verdicts"] == ["blocks_lane_draft", "requires_travis_approval"]
    assert data["concerns"] == ["automation before observability"]
    assert ChallengeReviewRecord.from_dict(data) == record
    assert isinstance(ChallengeReviewRecord.from_dict(data).questions, tuple)
    assert isinstance(ChallengeReviewRecord.from_dict(data).challenge_categories, tuple)
    assert RECORD_TYPES["ChallengeReviewRecord"] is ChallengeReviewRecord


def test_lane_request_record_round_trips_manual_copy_fields():
    record = LaneRequestRecord(
        lane_request_id="lane-request-1",
        project_id="project-hermes",
        title="Read-only status refresh",
        mode="read-only/manual-copy",
        objective="Inspect project state and recommend next lane.",
        allowed_actions=("read context", "report status"),
        forbidden_actions=("dispatch", "execute", "queue mutation"),
        stop_conditions=("workspace-status fails",),
        expected_report_format=("preflight", "no-mutation confirmation"),
        draft_prompt="Active lane:\nRead-only status refresh",
        status="draft",
        created_at="2026-06-10T10:00:00Z",
        updated_at="2026-06-10T10:01:00Z",
        metadata={"manual_copy_only": True},
    )

    data = record.to_dict()

    assert data["allowed_actions"] == ["read context", "report status"]
    assert data["forbidden_actions"] == ["dispatch", "execute", "queue mutation"]
    assert LaneRequestRecord.from_dict(data) == record
    assert isinstance(LaneRequestRecord.from_dict(data).allowed_actions, tuple)
    assert RECORD_TYPES["LaneRequestRecord"] is LaneRequestRecord


def test_jenny_report_record_round_trips_manual_report_fields():
    record = JennyReportRecord(
        report_id="report-1",
        project_id="project-hermes",
        lane_request_id="lane-request-1",
        summary="Report summary",
        result="Completed safely.",
        changed_files=("a.py", "b.py"),
        tests=("pytest -q",),
        risks=("none",),
        next_recommended_lane="Review next lane",
        created_at="2026-06-10T12:00:00Z",
        metadata={"manual": True},
    )

    data = record.to_dict()

    assert data["changed_files"] == ["a.py", "b.py"]
    assert data["tests"] == ["pytest -q"]
    assert data["risks"] == ["none"]
    assert JennyReportRecord.from_dict(data) == record
    assert isinstance(JennyReportRecord.from_dict(data).changed_files, tuple)
    assert RECORD_TYPES["JennyReportRecord"] is JennyReportRecord


def test_control_plane_lifecycle_records_force_inert_execution_metadata():
    approval = ApprovalRecord(
        approval_id="approval-1",
        project_id="project-hermes",
        action_class="read_only_lane",
        approval_scope="bounded read-only audit",
        approved_actions=("inspect",),
        status="approved",
        metadata={
            "would_execute": True,
            "execution_enabled": True,
            "dispatch_enabled": True,
            "session_send_enabled": True,
            "worker_dispatch_enabled": True,
            "trusted_for_execution": True,
        },
    )
    run = RunRecord(
        run_id="run-1",
        project_id="project-hermes",
        lane_type="read_only_inspection",
        objective="Inspect status only.",
        metadata={
            "would_execute": True,
            "execution_enabled": True,
            "dispatch_enabled": True,
            "session_send_enabled": True,
            "worker_dispatch_enabled": True,
            "trusted_for_execution": True,
        },
    )
    report = ReportRecord(
        report_id="report-1",
        run_id="run-1",
        project_id="project-hermes",
        summary="Reported status only.",
        metadata={
            "would_execute": True,
            "execution_enabled": True,
            "dispatch_enabled": True,
            "session_send_enabled": True,
            "worker_dispatch_enabled": True,
            "trusted_for_execution": True,
        },
    )

    for record in (approval, run, report):
        _assert_inert_execution_metadata(record.to_dict()["metadata"])
        assert type(record).from_dict(record.to_dict()) == record

    assert RECORD_TYPES["ApprovalRecord"] is ApprovalRecord
    assert RECORD_TYPES["RunRecord"] is RunRecord
    assert RECORD_TYPES["ReportRecord"] is ReportRecord


def test_jenny_bridge_message_request_record_round_trips_outbound_fields():
    record = JennyBridgeMessageRequestRecord(
        request_id="bridge-request-1",
        project_id="project-hermes",
        lane_request_id="lane-request-1",
        sender="travis",
        target_agent="jenny",
        message="Please review this lane.",
        status="queued",
        ack_key="bridge-request-1",
        created_at="2026-06-12T15:20:00Z",
        metadata={"dispatch_enabled": False},
    )

    data = record.to_dict()

    assert data["message"] == "Please review this lane."
    assert data["status"] == "queued"
    assert JennyBridgeMessageRequestRecord.from_dict(data) == record
    assert RECORD_TYPES["JennyBridgeMessageRequestRecord"] is JennyBridgeMessageRequestRecord


def test_jenny_bridge_message_response_record_round_trips_inbound_fields():
    record = JennyBridgeMessageResponseRecord(
        response_id="bridge-response-1",
        request_id="bridge-request-1",
        project_id="project-hermes",
        lane_request_id="lane-request-1",
        responder="jenny",
        message="Safe to proceed with a read-only lane.",
        status="received",
        created_at="2026-06-12T15:21:00Z",
        metadata={"external_jenny_response": True},
    )

    data = record.to_dict()

    assert data["request_id"] == "bridge-request-1"
    assert data["message"] == "Safe to proceed with a read-only lane."
    assert JennyBridgeMessageResponseRecord.from_dict(data) == record
    assert RECORD_TYPES["JennyBridgeMessageResponseRecord"] is JennyBridgeMessageResponseRecord


def test_jenny_reply_review_record_round_trips_operator_decision_fields():
    record = JennyReplyReviewRecord(
        review_id="reply-review-001",
        project_id="project-hermes-mission-control",
        response_id="response-001",
        request_id="request-001",
        decision="needs_evidence",
        reviewer="travis",
        note="Ask Jenny for files, checks, risks, and next safe lane.",
        created_at="2026-06-14T19:00:00Z",
        metadata={
            "display_only": True,
            "dispatch_enabled": False,
            "execution_enabled": False,
        },
    )

    data = record.to_dict()

    assert data == {
        "review_id": "reply-review-001",
        "project_id": "project-hermes-mission-control",
        "response_id": "response-001",
        "request_id": "request-001",
        "decision": "needs_evidence",
        "reviewer": "travis",
        "note": "Ask Jenny for files, checks, risks, and next safe lane.",
        "created_at": "2026-06-14T19:00:00Z",
        "metadata": {
            "display_only": True,
            "dispatch_enabled": False,
            "execution_enabled": False,
        },
    }
    assert JennyReplyReviewRecord.from_dict(data) == record
    assert RECORD_TYPES["JennyReplyReviewRecord"] is JennyReplyReviewRecord


def test_jenny_bridge_poller_status_record_round_trips_manual_status_fields():
    record = JennyBridgePollerStatusRecord(
        status_id="bridge-status-1",
        poller_id="manual-jenny-bridge-relay",
        mode="manual",
        status="response_appended",
        pending_count=1,
        handled_request_id="bridge-request-1",
        handled_response_id="bridge-response-1",
        last_error="",
        runtime_path="/home/jenny/.hermes/runtime",
        head="abc123",
        operator="jenny",
        created_at="2026-06-12T15:22:00Z",
        metadata={
            "manual_start_only": True,
            "dispatch_enabled": False,
            "session_send_enabled": False,
            "worker_enabled": False,
            "timer_enabled": False,
        },
    )

    data = record.to_dict()

    assert data["status"] == "response_appended"
    assert data["pending_count"] == 1
    assert data["metadata"]["manual_start_only"] is True
    assert data["metadata"]["dispatch_enabled"] is False
    assert data["metadata"]["session_send_enabled"] is False
    assert data["metadata"]["worker_enabled"] is False
    assert data["metadata"]["timer_enabled"] is False
    assert JennyBridgePollerStatusRecord.from_dict(data) == record
    assert RECORD_TYPES["JennyBridgePollerStatusRecord"] is JennyBridgePollerStatusRecord


def test_github_bridge_message_and_status_records_round_trip_manual_mailbox_fields():
    message = GitHubBridgeMessageRecord(
        request_id="github-bridge-request-1",
        project_id="project-hermes",
        from_agent="codex",
        to_agent="jenny",
        status="queued",
        message="Please review this from GitHub.",
        created_at="2026-06-13T00:00:00Z",
        github_repo="Travisaggie04/hermes-agent",
        github_issue_number=79,
        github_comment_id="12345",
        metadata={"manual_start_only": True, "dispatch_enabled": False},
    )
    status = GitHubBridgeMailboxStatusRecord(
        status_id="github-bridge-status-1",
        bridge_id="manual-github-issue-mailbox",
        repo="Travisaggie04/hermes-agent",
        issue_number=79,
        status="poll_completed",
        pending_count=1,
        new_message_count=1,
        handled_request_id="github-bridge-request-1",
        created_at="2026-06-13T00:01:00Z",
        metadata={"manual_start_only": True, "worker_enabled": False, "timer_enabled": False},
    )

    assert GitHubBridgeMessageRecord.from_dict(message.to_dict()) == message
    assert GitHubBridgeMailboxStatusRecord.from_dict(status.to_dict()) == status
    assert RECORD_TYPES["GitHubBridgeMessageRecord"] is GitHubBridgeMessageRecord
    assert RECORD_TYPES["GitHubBridgeMailboxStatusRecord"] is GitHubBridgeMailboxStatusRecord


def test_mission_brief_round_trips_nested_records_to_plain_dicts():
    brief = MissionBrief(
        mission_id="mission-001",
        title="PR-A records",
        created_at="2026-06-04T10:00:00Z",
        goal=GoalContract(
            goal_id="goal-001",
            statement="Implement inert Mission Control governance records.",
            success_criteria=("models round-trip", "jsonl store round-trips"),
        ),
        control=TaskControlEnvelope(
            active_lane="code/test",
            mode="code/test only",
            allowed_actions=("edit records files", "run focused tests"),
            forbidden_actions=("gateway edits", "dashboard edits", "tool execution"),
            current_repo="/repo",
            expected_systems_files=("mission_control/records/models.py",),
            stop_condition="stop before commit",
            other_threads_excluded=("Mission Control OS development",),
        ),
        approvals=(
            ApprovalSlice(
                approval_id="approval-001",
                lane="code/test",
                mode="code/test only",
                approved_actions=("create inert records",),
                forbidden_actions=("runtime wiring",),
                approver="Travisaggie04",
                approved_at="2026-06-04T10:01:00Z",
            ),
        ),
        evidence=(
            EvidenceCard(
                evidence_id="evidence-001",
                summary="Focused tests passed.",
                artifact_refs=(
                    ArtifactRef(
                        ref_id="artifact-001",
                        kind="test-output",
                        location="pytest://tests/mission_control",
                        description="pytest output reference",
                    ),
                ),
            ),
        ),
        artifacts=(
            ArtifactRef(
                ref_id="artifact-002",
                kind="file",
                location="mission_control/records/models.py",
            ),
        ),
        metadata={"tag": "v2026.5.29.2"},
    )

    data = brief.to_dict()

    assert data == {
        "mission_id": "mission-001",
        "title": "PR-A records",
        "created_at": "2026-06-04T10:00:00Z",
        "goal": {
            "goal_id": "goal-001",
            "statement": "Implement inert Mission Control governance records.",
            "success_criteria": ["models round-trip", "jsonl store round-trips"],
            "constraints": [],
            "metadata": {},
        },
        "control": {
            "envelope_id": "",
            "active_lane": "code/test",
            "mode": "code/test only",
            "allowed_actions": ["edit records files", "run focused tests"],
            "forbidden_actions": ["gateway edits", "dashboard edits", "tool execution"],
            "current_repo": "/repo",
            "expected_systems_files": ["mission_control/records/models.py"],
            "stop_condition": "stop before commit",
            "other_threads_excluded": ["Mission Control OS development"],
            "report_requirements": [],
            "risk_level": "",
            "approval_required": False,
            "approval_slice_ids": [],
            "evidence_ids": [],
            "token_context_policy": "",
            "created_at": "",
            "status": "",
            "metadata": {},
        },
        "approvals": [
            {
                "approval_slice_id": "approval-001",
                "related_action_id": "",
                "approval_type": "",
                "decision_state": "pending",
                "required_by": "Travisaggie04",
                "reason": "",
                "safety_conditions": ["runtime wiring"],
                "evidence_ids": [],
                "created_at": "2026-06-04T10:01:00Z",
                "expires_at": None,
                "metadata": {},
                "lane": "code/test",
                "mode": "code/test only",
                "approved_actions": ["create inert records"],
                "forbidden_actions": ["runtime wiring"],
                "approver": "Travisaggie04",
                "approved_at": "2026-06-04T10:01:00Z",
            }
        ],
        "evidence": [
            {
                "evidence_id": "evidence-001",
                "related_lane": "",
                "related_action_id": "",
                "related_record_type": "",
                "summary": "Focused tests passed.",
                "evidence_type": "",
                "source_label": "",
                "created_at": "",
                "risk_notes": [],
                "metadata": {},
                "artifact_refs": [
                    {
                        "ref_id": "artifact-001",
                        "kind": "test-output",
                        "location": "pytest://tests/mission_control",
                        "description": "pytest output reference",
                        "metadata": {},
                    }
                ],
            }
        ],
        "artifacts": [
            {
                "ref_id": "artifact-002",
                "kind": "file",
                "location": "mission_control/records/models.py",
                "description": "",
                "metadata": {},
            }
        ],
        "metadata": {"tag": "v2026.5.29.2"},
    }
    assert MissionBrief.from_dict(data) == brief
    assert isinstance(MissionBrief.from_dict(data).approvals, tuple)
    assert isinstance(MissionBrief.from_dict(data).evidence[0].artifact_refs, tuple)


def test_records_are_frozen_value_objects():
    artifact = ArtifactRef(ref_id="artifact-001", kind="file", location="README.md")

    with pytest.raises(FrozenInstanceError):
        artifact.location = "changed.md"


def test_from_dict_rejects_missing_required_fields():
    with pytest.raises(TypeError):
        GoalContract.from_dict({"goal_id": "goal-001"})


def test_approval_slice_round_trips_pr_h_planning_fields():
    approval = ApprovalSlice(
        approval_slice_id="approval-slice-001",
        related_action_id="action-001",
        approval_type="human",
        decision_state="pending",
        required_by="Travis",
        reason="Approve only after focused tests pass.",
        safety_conditions=("no deploy", "no tool execution"),
        evidence_ids=("evidence-001", "evidence-002"),
        created_at="2026-06-06T00:00:00Z",
        expires_at="2026-06-07T00:00:00Z",
        metadata={"internal_note": "store only"},
    )

    data = approval.to_dict()

    assert data == {
        "approval_slice_id": "approval-slice-001",
        "related_action_id": "action-001",
        "approval_type": "human",
        "decision_state": "pending",
        "required_by": "Travis",
        "reason": "Approve only after focused tests pass.",
        "safety_conditions": ["no deploy", "no tool execution"],
        "evidence_ids": ["evidence-001", "evidence-002"],
        "created_at": "2026-06-06T00:00:00Z",
        "expires_at": "2026-06-07T00:00:00Z",
        "metadata": {"internal_note": "store only"},
    }
    assert ApprovalSlice.from_dict(data) == approval
    assert isinstance(ApprovalSlice.from_dict(data).safety_conditions, tuple)
    assert isinstance(ApprovalSlice.from_dict(data).evidence_ids, tuple)


def test_evidence_card_round_trips_pr_h_planning_fields():
    evidence = EvidenceCard(
        evidence_id="evidence-001",
        related_lane="PR-H Evidence Cards",
        related_action_id="action-001",
        related_record_type="OperatorAction",
        summary="Focused tests show bounded read-only behavior.",
        evidence_type="test",
        source_label="pytest",
        created_at="2026-06-06T00:00:00Z",
        risk_notes=("No execution path added.",),
        metadata={"raw_log": "store only"},
    )

    data = evidence.to_dict()

    assert data == {
        "evidence_id": "evidence-001",
        "related_lane": "PR-H Evidence Cards",
        "related_action_id": "action-001",
        "related_record_type": "OperatorAction",
        "summary": "Focused tests show bounded read-only behavior.",
        "evidence_type": "test",
        "source_label": "pytest",
        "created_at": "2026-06-06T00:00:00Z",
        "risk_notes": ["No execution path added."],
        "metadata": {"raw_log": "store only"},
    }
    assert EvidenceCard.from_dict(data) == evidence
    assert isinstance(EvidenceCard.from_dict(data).risk_notes, tuple)


def test_operator_action_round_trips_to_plain_dicts():
    action = OperatorAction(
        action_id="action-001",
        title="Request bounded implementation slice",
        lane="PR-G Operator Action Queue implementation",
        mode="focused tests only",
        requested_action="Implement inert read-only queue summary.",
        risk_level="low",
        status="requested",
        required_approval="Travis approval before commit",
        approval_id="approval-001",
        evidence_ids=("evidence-001", "evidence-002"),
        stop_condition="Stop after focused tests.",
        created_at="2026-06-05T10:00:00Z",
        expires_at="2026-06-06T10:00:00Z",
        metadata={"source": "planning", "internal_note": "display only"},
    )

    data = action.to_dict()

    assert data == {
        "action_id": "action-001",
        "title": "Request bounded implementation slice",
        "lane": "PR-G Operator Action Queue implementation",
        "mode": "focused tests only",
        "requested_action": "Implement inert read-only queue summary.",
        "risk_level": "low",
        "status": "requested",
        "required_approval": "Travis approval before commit",
        "approval_id": "approval-001",
        "evidence_ids": ["evidence-001", "evidence-002"],
        "stop_condition": "Stop after focused tests.",
        "created_at": "2026-06-05T10:00:00Z",
        "expires_at": "2026-06-06T10:00:00Z",
        "metadata": {"source": "planning", "internal_note": "display only"},
    }
    assert OperatorAction.from_dict(data) == action
    assert isinstance(OperatorAction.from_dict(data).evidence_ids, tuple)


def test_task_control_envelope_round_trips_pr_i_fields():
    envelope = TaskControlEnvelope(
        envelope_id="envelope-001",
        active_lane="PR-I Start Gate",
        mode="bounded implementation",
        allowed_actions=("create inert records",),
        forbidden_actions=("execute tools", "approve actions"),
        stop_condition="Stop after draft PR.",
        report_requirements=("report tests", "report safety posture"),
        risk_level="low",
        approval_required=True,
        approval_slice_ids=("approval-001",),
        evidence_ids=("evidence-001",),
        token_context_policy="summary-first latest-N only",
        created_at="2026-06-06T00:00:00Z",
        status="active",
        metadata={"raw_context": "stored only"},
    )

    data = envelope.to_dict()

    assert data == {
        "envelope_id": "envelope-001",
        "active_lane": "PR-I Start Gate",
        "mode": "bounded implementation",
        "allowed_actions": ["create inert records"],
        "forbidden_actions": ["execute tools", "approve actions"],
        "current_repo": "",
        "expected_systems_files": [],
        "stop_condition": "Stop after draft PR.",
        "other_threads_excluded": [],
        "report_requirements": ["report tests", "report safety posture"],
        "risk_level": "low",
        "approval_required": True,
        "approval_slice_ids": ["approval-001"],
        "evidence_ids": ["evidence-001"],
        "token_context_policy": "summary-first latest-N only",
        "created_at": "2026-06-06T00:00:00Z",
        "status": "active",
        "metadata": {"raw_context": "stored only"},
    }
    assert TaskControlEnvelope.from_dict(data) == envelope
    assert isinstance(TaskControlEnvelope.from_dict(data).approval_slice_ids, tuple)


def test_start_gate_check_round_trips_descriptive_fields_only():
    check = StartGateCheck(
        start_gate_id="start-gate-001",
        envelope_id="envelope-001",
        decision_state="needs_approval",
        reasons=("approval slice required",),
        blocked_actions=("push", "deploy"),
        required_approvals=("approval-001",),
        dirty_worktree_state="clean",
        branch_safety_state="exact base",
        secret_safety_state="not touched",
        token_context_state="bounded",
        created_at="2026-06-06T00:01:00Z",
        metadata={"raw_scan": "stored only"},
    )

    data = check.to_dict()

    assert data == {
        "start_gate_id": "start-gate-001",
        "envelope_id": "envelope-001",
        "decision_state": "needs_approval",
        "reasons": ["approval slice required"],
        "blocked_actions": ["push", "deploy"],
        "required_approvals": ["approval-001"],
        "dirty_worktree_state": "clean",
        "branch_safety_state": "exact base",
        "secret_safety_state": "not touched",
        "token_context_state": "bounded",
        "created_at": "2026-06-06T00:01:00Z",
        "metadata": {"raw_scan": "stored only"},
    }
    assert StartGateCheck.from_dict(data) == check
    assert isinstance(StartGateCheck.from_dict(data).blocked_actions, tuple)


def test_operator_action_is_registered_and_exported():
    from mission_control.records import OperatorAction as ExportedOperatorAction
    from mission_control.records.models import RECORD_TYPES

    assert ExportedOperatorAction is OperatorAction
    assert RECORD_TYPES["OperatorAction"] is OperatorAction


def test_operator_action_metadata_is_optional():
    action = OperatorAction.from_dict({
        "action_id": "action-minimal",
        "title": "Minimal requested action",
        "lane": "read-only lane",
        "mode": "inventory only",
        "requested_action": "Review summary card.",
    })

    assert action.metadata == {}
    assert action.evidence_ids == ()
    assert action.risk_level == ""
    assert action.status == "requested"



def test_operating_workspace_handoff_record_round_trips_display_only_fields():
    record = OperatingWorkspaceHandoffRecord(
        handoff_id="handoff-001",
        created_at="2026-06-09T00:00:00Z",
        source="operator_supplied_handoff",
        active_lane="PR #45 Operating Workspace handoff records",
        lane_mode="bounded display-only PR",
        accepted_runtime_path="/home/jenny/.hermes/hermes-runtime-workspaceui-d11681f",
        accepted_head="d11681f81c7cd16a99c53649f157040b2d10a89f",
        rollback_runtime_path="/home/jenny/.hermes/hermes-runtime-workspace-f20aa2d",
        rollback_head="f20aa2da2a2e978d72f837007d8ab1b14301795b",
        dispatch_in_gateway=False,
        max_active_lane=1,
        active_lane_count=1,
        target_type="pr",
        target_id="45",
        target_head="d11681f81c7cd16a99c53649f157040b2d10a89f",
        status="active",
        last_result="PR #44 accepted",
        next_action="Implement PR #45 tests",
        warnings=("display-only",),
        would_execute=True,
        dry_run_only=False,
        enforces_runtime=True,
        display_only=False,
    )

    data = record.to_dict()

    assert data == {
        "handoff_id": "handoff-001",
        "created_at": "2026-06-09T00:00:00Z",
        "source": "operator_supplied_handoff",
        "active_lane": "PR #45 Operating Workspace handoff records",
        "lane_mode": "bounded display-only PR",
        "accepted_runtime_path": "/home/jenny/.hermes/hermes-runtime-workspaceui-d11681f",
        "accepted_head": "d11681f81c7cd16a99c53649f157040b2d10a89f",
        "rollback_runtime_path": "/home/jenny/.hermes/hermes-runtime-workspace-f20aa2d",
        "rollback_head": "f20aa2da2a2e978d72f837007d8ab1b14301795b",
        "dispatch_in_gateway": False,
        "max_active_lane": 1,
        "active_lane_count": 1,
        "target_type": "pr",
        "target_id": "45",
        "target_head": "d11681f81c7cd16a99c53649f157040b2d10a89f",
        "status": "active",
        "last_result": "PR #44 accepted",
        "next_action": "Implement PR #45 tests",
        "warnings": ["display-only"],
        "would_execute": False,
        "dry_run_only": True,
        "enforces_runtime": False,
        "display_only": True,
    }
    assert OperatingWorkspaceHandoffRecord.from_dict(data) == record
    assert isinstance(OperatingWorkspaceHandoffRecord.from_dict(data).warnings, tuple)
    assert RECORD_TYPES["OperatingWorkspaceHandoffRecord"] is OperatingWorkspaceHandoffRecord


def test_operating_workspace_handoff_record_sanitizes_allowlist_bounds_and_shas():
    record = OperatingWorkspaceHandoffRecord.from_dict(
        {
            "handoff_id": "h" * 500,
            "created_at": "2026-06-09T00:00:00Z",
            "source": "operator",
            "active_lane": "x" * 500,
            "lane_mode": "mode",
            "accepted_runtime_path": "/home/jenny/.hermes/hermes-runtime-workspaceui-d11681f",
            "accepted_head": "not-a-sha",
            "rollback_runtime_path": "/home/jenny/.hermes/hermes-runtime-workspace-f20aa2d",
            "rollback_head": "f20aa2da2a2e978d72f837007d8ab1b14301795b",
            "dispatch_in_gateway": True,
            "max_active_lane": 5000,
            "active_lane_count": 5001,
            "target_type": "pr",
            "target_id": "45",
            "target_head": "also-not-a-sha",
            "status": "active",
            "last_result": "raw log must not appear",
            "next_action": "next",
            "warnings": [str(i) for i in range(25)],
            "raw_log": "forbidden",
            "discord_messages": ["forbidden"],
            "token": "secret-token",
            "github_response": {"raw": "forbidden"},
        }
    )

    data = record.to_dict()

    assert len(data["handoff_id"]) <= 160
    assert len(data["active_lane"]) <= 160
    assert data["accepted_head"] == ""
    assert data["target_head"] == ""
    assert len(data["warnings"]) == 20
    rendered = str(data).lower()
    assert "raw_log" not in rendered
    assert "discord_messages" not in rendered
    assert "secret-token" not in rendered
    assert "github_response" not in rendered



def test_accepted_baseline_record_round_trips_and_forces_inert_flags():
    record = AcceptedBaselineRecord(
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
        display_only=False,
        would_execute=True,
        dry_run_only=False,
        enforces_runtime=True,
    )

    data = record.to_dict()

    assert data == {
        "baseline_id": "baseline-001",
        "recorded_at": "2026-06-09T00:00:00Z",
        "source": "operator_accepted_baseline",
        "runtime_path": "/home/jenny/.hermes/hermes-runtime-handoff-8c560c7",
        "head": "8c560c739606564aeeb4db464fe1989cb67a40b6",
        "rollback_runtime_path": "/home/jenny/.hermes/hermes-runtime-workspaceui-d11681f",
        "rollback_head": "d11681f81c7cd16a99c53649f157040b2d10a89f",
        "dispatch_in_gateway": False,
        "active_kanban": 0,
        "max_active_lane": 1,
        "issue": "none",
        "display_only": True,
        "would_execute": False,
        "dry_run_only": True,
        "enforces_runtime": False,
    }
    assert AcceptedBaselineRecord.from_dict(data) == record
    assert RECORD_TYPES["AcceptedBaselineRecord"] is AcceptedBaselineRecord


def test_accepted_baseline_record_sanitizes_bounds_shas_and_forbidden_fields():
    record = AcceptedBaselineRecord.from_dict({
        "baseline_id": "b" * 500,
        "recorded_at": "2026-06-09T00:00:00Z",
        "source": "operator",
        "runtime_path": "/home/jenny/.hermes/hermes-runtime-handoff-8c560c7",
        "head": "not-a-sha",
        "rollback_runtime_path": "/home/jenny/.hermes/hermes-runtime-workspaceui-d11681f",
        "rollback_head": "also-not-a-sha",
        "dispatch_in_gateway": True,
        "active_kanban": 5000,
        "max_active_lane": 5001,
        "issue": "x" * 500,
        "raw_log": "forbidden",
        "transcript": "forbidden",
        "discord_messages": ["forbidden"],
        "pr_body": "forbidden",
        "github_response": {"raw": "forbidden"},
        "token": "placeholder-token",
        "canonical_packet_json": {"raw": "forbidden"},
    })

    data = record.to_dict()

    assert len(data["baseline_id"]) <= 160
    assert len(data["issue"]) <= 160
    assert data["head"] == ""
    assert data["rollback_head"] == ""
    assert data["active_kanban"] == 999
    assert data["max_active_lane"] == 999
    rendered = str(data).lower()
    for forbidden in ("raw_log", "transcript", "discord_messages", "pr_body", "github_response", "placeholder-token", "canonical_packet_json"):
        assert forbidden not in rendered


def test_child_run_record_round_trips_orchestration_status_and_forces_disabled_flags():
    record = ChildRunRecord(
        child_run_id="child-run-1",
        parent_run_id="run-parent-1",
        project_id="project-hermes-mission-control",
        agent_identity="jenny-child",
        delegation_source="mission-control-preview",
        objective="Inspect one scoped file and report risks.",
        allowed_actions=("read files",),
        forbidden_actions=("dispatch", "deploy", "session-send"),
        status="running",
        report_id="report-child-1",
        result_record_id="result-child-1",
        depends_on_child_run_ids=("child-run-0",),
        metadata={
            "dispatch_enabled": True,
            "worker_dispatch_enabled": True,
            "waha_enabled": True,
            "social_enabled": True,
            "payment_enabled": True,
            "queue_mutation_enabled": True,
            "model_routing_enabled": True,
        },
    )

    data = record.to_dict()

    assert data["child_run_id"] == "child-run-1"
    assert data["allowed_actions"] == ["read files"]
    assert data["depends_on_child_run_ids"] == ["child-run-0"]
    assert data["metadata"]["display_only"] is True
    _assert_inert_execution_metadata(data["metadata"])
    assert ChildRunRecord.from_dict(data) == record
    assert RECORD_TYPES["ChildRunRecord"] is ChildRunRecord


def test_worker_node_run_record_round_trips_laptop_codex_state_and_forces_disabled_flags():
    record = WorkerNodeRunRecord(
        worker_run_id="worker-run-1",
        parent_run_id="run-parent-1",
        project_id="project-hermes-mission-control",
        worker_identity="codex",
        worker_host_label="laptop-codex",
        worker_kind="laptop_codex",
        objective="Prepare a scoped PR and report test results.",
        assigned_packet_id="packet-1",
        assigned_packet_summary="Scoped PR packet preview.",
        allowed_actions=("edit scoped files", "run focused tests"),
        forbidden_actions=("deploy", "restart", "runtime switch"),
        status="blocked",
        blocked_reasons=("worker node offline",),
        report_id="report-worker-1",
        report_review_status="needs_review",
        report_contract_status="incomplete",
        presence_status="online",
        last_seen_at="2026-06-19T12:00:00Z",
        worker_version="codex-desktop-1.2.3",
        capability_summary="repo-local engineering worker with guarded shell and patch tools",
        worker_dispatch_enabled=True,
        metadata={
            "execution_enabled": True,
            "dispatch_enabled": True,
            "worker_enabled": True,
            "workers_enabled": True,
            "timer_enabled": True,
            "daemon_enabled": True,
            "waha_enabled": True,
            "social_enabled": True,
            "payment_enabled": True,
            "queue_mutation_enabled": True,
            "model_routing_enabled": True,
        },
    )

    data = record.to_dict()

    assert data["worker_run_id"] == "worker-run-1"
    assert data["worker_host_label"] == "laptop-codex"
    assert data["blocked_reasons"] == ["worker node offline"]
    assert data["presence_status"] == "online"
    assert data["last_seen_at"] == "2026-06-19T12:00:00Z"
    assert data["worker_version"] == "codex-desktop-1.2.3"
    assert data["capability_summary"] == "repo-local engineering worker with guarded shell and patch tools"
    assert data["worker_dispatch_enabled"] is False
    assert data["metadata"]["display_only"] is True
    _assert_inert_execution_metadata(data["metadata"])
    assert WorkerNodeRunRecord.from_dict(data) == record
    assert RECORD_TYPES["WorkerNodeRunRecord"] is WorkerNodeRunRecord
