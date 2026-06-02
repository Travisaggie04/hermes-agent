from __future__ import annotations

import json
from types import SimpleNamespace

from gateway.config import GatewayConfig, Platform
from gateway.run import GatewayRunner
from gateway.session import SessionSource, build_session_context, build_session_context_prompt
from hermes_cli.goals import CONTINUATION_PROMPT_TEMPLATE


def test_quality_lane_section_required_for_code_change_report():
    from gateway.quality_lanes import (
        require_quality_lane_section,
        validate_quality_lane_section,
    )

    section = require_quality_lane_section(
        "Make code changes and run tests before the final report.",
        verification_summary="pytest tests/gateway/test_quality_lanes.py",
    )

    assert "## Quality lanes" in section
    assert "Task classification: high-rigor" in section
    assert "Required lanes:" in section
    assert "Implementation lane result:" in section
    assert "Review lane result:" in section
    assert "Verification lane result:" in section
    assert "Safety lane result:" in section
    assert "Remaining risks:" in section
    assert validate_quality_lane_section(section)["valid"] is True


def test_quality_lane_section_required_for_restart_report():
    from gateway.quality_lanes import require_quality_lane_section

    section = require_quality_lane_section(
        "Verify restart and deployment runtime state.",
        verification_summary="systemctl --user show hermes-gateway.service",
    )

    assert "Deployment/runtime lane result:" in section
    assert "restart required/performed/not performed" in section


def test_quality_lane_fallback_when_subagent_unavailable():
    from gateway.quality_lanes import require_quality_lane_section

    section = require_quality_lane_section(
        "Clean up a repo worktree.",
        subagent_available=False,
        subagent_invoked=False,
    )

    assert "real subagent used: no" in section
    assert "Subagent unavailable/not invoked; checklist fallback used." in section


def test_no_claim_real_subagent_without_delegate_execution():
    from gateway.quality_lanes import require_quality_lane_section

    section = require_quality_lane_section(
        "Review and commit code.",
        subagent_available=True,
        subagent_invoked=False,
    )

    assert "real subagent used: no" in section
    assert "real subagent used: yes" not in section


def test_quality_report_uses_delegate_evidence_when_present(tmp_path, monkeypatch):
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    from gateway.delegate_evidence import record_delegate_evidence
    from gateway.quality_lanes import require_quality_lane_section

    evidence = record_delegate_evidence(
        lane="review",
        task_goal="Review confidential prompt text",
        delegate_name="delegate_task",
        status="succeeded",
        result_summary="Reviewed the implementation and found no blocker.",
        session_key="platform:sample:session:id",
    )

    section = require_quality_lane_section(
        "Review and commit code.",
        delegate_evidence=[evidence],
    )

    assert "real subagent used: yes" in section
    assert "lane=review" in section
    assert "status=succeeded" in section
    assert "Reviewed the implementation" in section
    assert "platform:sample:session:id" not in section


def test_quality_report_falls_back_when_no_delegate_evidence():
    from gateway.quality_lanes import require_quality_lane_section

    section = require_quality_lane_section(
        "Review and commit code.",
        subagent_available=True,
        subagent_invoked=True,
        delegate_evidence=[],
    )

    assert "real subagent used: no" in section
    assert "checklist fallback used" in section
    assert "real subagent used: yes" not in section


def test_delegate_evidence_redacts_confidential_prompt_content(tmp_path, monkeypatch):
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    from gateway.delegate_evidence import record_delegate_evidence

    evidence = record_delegate_evidence(
        lane="implementation",
        task_goal="Do sensitive work with confidential prompt body",
        delegate_name="delegate_task",
        status="succeeded",
        result_summary="Result mentions confidential prompt body.",
        session_key="platform:sample:session:id",
    )

    rendered = repr(evidence)
    assert "confidential prompt body" not in rendered
    assert "platform:sample:session:id" not in rendered
    assert evidence["task_ref"].startswith("sha256:")


def test_delegate_evidence_filters_by_session_id(tmp_path, monkeypatch):
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    from gateway.delegate_evidence import (
        clear_delegate_evidence_records,
        get_recent_delegate_evidence,
        record_delegate_evidence,
    )

    clear_delegate_evidence_records(clear_durable=True)
    record_delegate_evidence(
        lane="review",
        task_goal="first",
        status="succeeded",
        result_summary="first summary",
        session_key="session-a",
    )
    record_delegate_evidence(
        lane="verification",
        task_goal="second",
        status="succeeded",
        result_summary="second summary",
        session_key="session-b",
    )

    records = get_recent_delegate_evidence(session_id="session-b")

    assert len(records) == 1
    assert records[0]["lane"] == "verification"
    assert "second summary" in records[0]["safe_result_summary"]


def test_delegate_evidence_persists_safe_metadata(tmp_path, monkeypatch):
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    from gateway.delegate_evidence import (
        clear_delegate_evidence_records,
        get_delegate_evidence_store_path,
        record_delegate_evidence,
    )

    clear_delegate_evidence_records(clear_durable=True)
    evidence = record_delegate_evidence(
        lane="review",
        task_goal="Review private prompt text",
        status="succeeded",
        result_summary="Reviewed private prompt text.",
        session_key="platform:raw:session:key",
        active_task_id="task-123",
        goal_id="goal-456",
        repo_path=str(tmp_path / "repo"),
        branch="main",
        head="abc123",
    )

    store_path = get_delegate_evidence_store_path()
    stored = json.loads(store_path.read_text(encoding="utf-8"))
    rendered = json.dumps(stored)
    assert evidence["evidence_id"]
    assert evidence["session_key_hash"].startswith("sha256:")
    assert stored["records"][0]["active_task_id"] == "task-123"
    assert stored["records"][0]["goal_id"] == "goal-456"
    assert "platform:raw:session:key" not in rendered
    assert "private prompt text" not in rendered


def test_delegate_evidence_survives_store_reload(tmp_path, monkeypatch):
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    from gateway.delegate_evidence import (
        clear_delegate_evidence_records,
        get_recent_delegate_evidence,
        record_delegate_evidence,
    )

    clear_delegate_evidence_records(clear_durable=True)
    record_delegate_evidence(
        lane="verification",
        status="succeeded",
        result_summary="pytest passed",
        session_key="session-reload",
    )
    clear_delegate_evidence_records()

    records = get_recent_delegate_evidence(session_id="session-reload")

    assert len(records) == 1
    assert records[0]["lane"] == "verification"
    assert "pytest passed" in records[0]["safe_result_summary"]


def test_quality_report_uses_durable_delegate_evidence(tmp_path, monkeypatch):
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    from gateway.delegate_evidence import (
        clear_delegate_evidence_records,
        get_recent_delegate_evidence,
        record_delegate_evidence,
    )
    from gateway.quality_lanes import require_quality_lane_section

    clear_delegate_evidence_records(clear_durable=True)
    record_delegate_evidence(
        lane="review",
        status="succeeded",
        result_summary="Durable review found no blocker.",
        session_key="durable-session",
    )
    clear_delegate_evidence_records()

    section = require_quality_lane_section(
        "Review and commit code.",
        delegate_evidence=get_recent_delegate_evidence(session_id="durable-session"),
    )

    assert "real subagent used: yes" in section
    assert "Durable review found no blocker." in section


def test_failed_delegate_lane_marks_report_incomplete_or_risky(tmp_path, monkeypatch):
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    from gateway.delegate_evidence import clear_delegate_evidence_records, record_delegate_evidence
    from gateway.quality_lanes import require_quality_lane_section

    clear_delegate_evidence_records(clear_durable=True)
    evidence = record_delegate_evidence(
        lane="review",
        status="failed",
        result_summary="Reviewer timed out.",
        session_key="failed-session",
    )

    section = require_quality_lane_section(
        "Review and commit code.",
        delegate_evidence=[evidence],
    )

    assert "Completion status: incomplete/risky" in section
    assert "Reviewer timed out." in section


def test_high_risk_task_requires_delegate_or_fallback_reason():
    from gateway.quality_lanes import require_quality_lane_section

    section = require_quality_lane_section("Deploy code and verify production runtime.")

    assert "Review lane result:" in section
    assert "real subagent used: no" in section
    assert "Subagent unavailable/not invoked; checklist fallback used." in section


def test_goal_task_receives_quality_lane_requirement():
    prompt = CONTINUATION_PROMPT_TEMPLATE.format(goal="make code changes and verify them")

    assert "Quality lanes" in prompt
    assert "Task classification" in prompt
    assert "Subagent unavailable/not invoked; checklist fallback used." in prompt


def test_session_prompt_includes_enforceable_quality_lane_requirement():
    source = SessionSource(platform=Platform.DISCORD, chat_id="channel-1")
    ctx = build_session_context(source, GatewayConfig())

    prompt = build_session_context_prompt(ctx)

    assert "## Quality Lanes for High-Rigor Work" in prompt
    assert "Quality lanes section is required in final reports" in prompt
    assert "Do not claim real subagents ran unless delegation actually ran" in prompt


def test_recovery_report_includes_quality_lane_requirement():
    runner = GatewayRunner.__new__(GatewayRunner)
    runner._build_repo_identity_guard = lambda _record: {
        "ok": True,
        "lines": ["Repo identity guard passed"],
        "repo_path": "/tmp/repo",
        "branch": "main",
        "head": "abc123",
    }
    record = SimpleNamespace(
        task_summary="restart/deployment verification",
        command="systemctl status",
        expected_commit=None,
        final_report_path=None,
    )

    report = runner._build_active_execute_recovery_report(record, "not_found", None)

    assert "## Quality lanes" in report
    assert "Task classification: high-rigor" in report
    assert "Deployment/runtime lane result:" in report
