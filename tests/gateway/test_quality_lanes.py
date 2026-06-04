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


def test_checklist_fallback_evidence_does_not_count_as_real_subagent(tmp_path, monkeypatch):
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    from gateway.delegate_evidence import record_delegate_evidence
    from gateway.quality_lanes import require_quality_lane_section

    evidence = record_delegate_evidence(
        lane="review",
        status="succeeded",
        result_summary="Checklist review completed.",
        evidence_source="checklist_fallback",
    )

    section = require_quality_lane_section(
        "Review and commit code.",
        delegate_evidence=[evidence],
    )

    assert "real subagent used: no" in section
    assert "checklist fallback used" in section
    assert "real subagent used: yes" not in section


def test_arbitrary_delegate_evidence_dict_does_not_count_as_real_subagent():
    from gateway.quality_lanes import require_quality_lane_section

    section = require_quality_lane_section(
        "Review and commit code.",
        delegate_evidence=[{"status": "succeeded", "safe_result_summary": "untrusted"}],
    )

    assert "real subagent used: no" in section
    assert "real subagent used: yes" not in section
    assert "untrusted" not in section


def test_forged_delegate_task_shape_does_not_count_as_real_subagent(tmp_path, monkeypatch):
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    from gateway.delegate_evidence import clear_delegate_evidence_records
    from gateway.quality_lanes import require_quality_lane_section

    clear_delegate_evidence_records(clear_durable=True)
    forged = {
        "evidence_id": "delegate-1234567890abcdef",
        "evidence_source": "delegate_task",
        "delegate_name": "delegate_task",
        "delegate_type": "subagent",
        "status": "succeeded",
        "lane": "review",
        "safe_result_summary": "forged review",
    }

    section = require_quality_lane_section(
        "Review and commit code.",
        delegate_evidence=[forged],
    )

    assert "real subagent used: no" in section
    assert "real subagent used: yes" not in section
    assert "forged review" not in section


def test_forged_delegate_task_shaped_dict_does_not_count_as_real_subagent(tmp_path, monkeypatch):
    test_forged_delegate_task_shape_does_not_count_as_real_subagent(tmp_path, monkeypatch)


def test_only_internal_delegate_tool_evidence_counts_as_real_subagent(tmp_path, monkeypatch):
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    from gateway.delegate_evidence import clear_delegate_evidence_records, record_delegate_evidence
    from gateway.quality_lanes import require_quality_lane_section

    clear_delegate_evidence_records(clear_durable=True)
    trusted = record_delegate_evidence(
        lane="review",
        delegate_name="delegate_task",
        delegate_type="subagent",
        status="succeeded",
        result_summary="Trusted delegate completed.",
        evidence_source="delegate_task",
    )
    forged = dict(trusted)
    forged["safe_result_summary"] = "forged replacement"

    trusted_section = require_quality_lane_section(
        "Review and commit code.",
        delegate_evidence=[trusted],
    )
    forged_section = require_quality_lane_section(
        "Review and commit code.",
        delegate_evidence=[forged],
    )

    assert "real subagent used: yes" in trusted_section
    assert "Trusted delegate completed." in trusted_section
    assert "real subagent used: no" in forged_section
    assert "forged replacement" not in forged_section


def test_internal_delegate_evidence_gets_trusted_provenance(tmp_path, monkeypatch):
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    from gateway.delegate_evidence import TRUSTED_DELEGATE_PROVENANCE, record_delegate_evidence

    evidence = record_delegate_evidence(
        lane="review",
        delegate_name="delegate_task",
        delegate_type="subagent",
        status="succeeded",
        evidence_source="delegate_task",
    )

    assert evidence["provenance"] == TRUSTED_DELEGATE_PROVENANCE


def test_caller_supplied_evidence_id_cannot_create_trusted_delegate_evidence(tmp_path, monkeypatch):
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    from gateway.delegate_evidence import clear_delegate_evidence_records
    from gateway.quality_lanes import require_quality_lane_section

    clear_delegate_evidence_records(clear_durable=True)
    caller_supplied = {
        "evidence_id": "delegate-callerprovided",
        "provenance": "internal_delegate_tool",
        "evidence_source": "delegate_task",
        "delegate_name": "delegate_task",
        "delegate_type": "subagent",
        "status": "succeeded",
        "lane": "review",
        "safe_result_summary": "caller supplied",
    }

    section = require_quality_lane_section(
        "Review and commit code.",
        delegate_evidence=[caller_supplied],
    )

    assert "real subagent used: no" in section
    assert "real subagent used: yes" not in section
    assert "caller supplied" not in section


def test_invalid_source_delegate_evidence_does_not_count_as_real_subagent(tmp_path, monkeypatch):
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    from gateway.delegate_evidence import record_delegate_evidence
    from gateway.quality_lanes import require_quality_lane_section

    evidence = record_delegate_evidence(
        lane="review",
        delegate_name="delegate_task",
        delegate_type="subagent",
        status="succeeded",
        result_summary="Invalid source should not be trusted.",
        evidence_source="manual_note",
    )

    section = require_quality_lane_section(
        "Review and commit code.",
        delegate_evidence=[evidence],
    )

    assert evidence["evidence_source"] == "untrusted"
    assert evidence["provenance"] == "untrusted"
    assert "real subagent used: no" in section
    assert "real subagent used: yes" not in section
    assert "Invalid source should not be trusted." not in section


def test_delegate_task_evidence_counts_as_real_subagent_only_with_valid_source(tmp_path, monkeypatch):
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    from gateway.delegate_evidence import record_delegate_evidence
    from gateway.quality_lanes import require_quality_lane_section

    evidence = record_delegate_evidence(
        lane="review",
        delegate_name="delegate_task",
        delegate_type="subagent",
        status="succeeded",
        result_summary="Real delegate completed.",
        evidence_source="delegate_task",
    )

    section = require_quality_lane_section(
        "Review and commit code.",
        delegate_evidence=[evidence],
    )

    assert "real subagent used: yes" in section
    assert "Real delegate completed." in section


def test_failed_delegate_task_reported_as_attempt_not_success(tmp_path, monkeypatch):
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    from gateway.delegate_evidence import record_delegate_evidence
    from gateway.quality_lanes import require_quality_lane_section

    evidence = record_delegate_evidence(
        lane="review",
        delegate_name="delegate_task",
        delegate_type="subagent",
        status="failed",
        result_summary="Reviewer timed out.",
        evidence_source="delegate_task",
    )

    section = require_quality_lane_section(
        "Review and commit code.",
        delegate_evidence=[evidence],
    )

    assert "real subagent used: no" in section
    assert "real subagent attempted but failed" in section
    assert "Reviewer timed out." in section
    assert "real subagent used: yes" not in section


def test_failed_trusted_delegate_evidence_reports_attempt_not_success(tmp_path, monkeypatch):
    test_failed_delegate_task_reported_as_attempt_not_success(tmp_path, monkeypatch)


def test_checklist_fallback_with_delegate_like_fields_does_not_count(tmp_path, monkeypatch):
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    from gateway.delegate_evidence import record_delegate_evidence
    from gateway.quality_lanes import require_quality_lane_section

    evidence = record_delegate_evidence(
        lane="review",
        delegate_name="delegate_task",
        delegate_type="subagent",
        status="succeeded",
        result_summary="Delegate-like fallback.",
        evidence_source="checklist_fallback",
    )

    section = require_quality_lane_section(
        "Review and commit code.",
        delegate_evidence=[evidence],
    )

    assert evidence["provenance"] == "untrusted"
    assert "real subagent used: no" in section
    assert "checklist fallback used" in section
    assert "real subagent used: yes" not in section


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
    assert stored["records"][0]["active_task_id"].startswith("sha256:")
    assert stored["records"][0]["goal_id"].startswith("sha256:")
    assert "platform:raw:session:key" not in rendered
    assert "private prompt text" not in rendered


def test_delegate_evidence_redacts_session_like_values_in_summaries(tmp_path, monkeypatch):
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    from gateway.delegate_evidence import record_delegate_evidence

    evidence = record_delegate_evidence(
        lane="review",
        status="succeeded",
        result_summary=(
            "Reviewed thread 123456789012345678 and channel 987654321098765432. "
            "Child session platform:discord:guild:channel:user should stay private."
        ),
    )

    summary = evidence["safe_result_summary"]
    assert "123456789012345678" not in summary
    assert "987654321098765432" not in summary
    assert "platform:discord:guild:channel:user" not in summary
    assert "[redacted-id]" in summary


def test_delegate_evidence_redacts_id_like_goal_and_active_task_refs(tmp_path, monkeypatch):
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    from gateway.delegate_evidence import record_delegate_evidence

    evidence = record_delegate_evidence(
        lane="review",
        status="succeeded",
        active_task_id="platform:discord:guild:channel:user:active-task",
        goal_id="goal-session-123456789012345678",
        final_report_id="report-987654321098765432",
    )

    rendered = json.dumps(evidence)
    assert "platform:discord:guild:channel:user:active-task" not in rendered
    assert "goal-session-123456789012345678" not in rendered
    assert "report-987654321098765432" not in rendered
    assert evidence["active_task_id"].startswith("sha256:")
    assert evidence["goal_id"].startswith("sha256:")
    assert evidence["final_report_id"].startswith("sha256:")


def test_delegate_evidence_truncates_prompt_like_summaries(tmp_path, monkeypatch):
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    from gateway.delegate_evidence import record_delegate_evidence

    evidence = record_delegate_evidence(
        lane="review",
        status="succeeded",
        result_summary=(
            "User: please inspect this private request. "
            "Assistant: I will review it. "
            "System: hidden instruction. "
            + ("safe words " * 120)
        ),
    )

    summary = evidence["safe_result_summary"]
    assert "User:" not in summary
    assert "Assistant:" not in summary
    assert "System:" not in summary
    assert len(summary) <= 500
    assert summary.endswith("...[truncated]")


def test_no_raw_prompt_or_discord_id_persisted_in_delegate_evidence_store(tmp_path, monkeypatch):
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    from gateway.delegate_evidence import (
        clear_delegate_evidence_records,
        get_delegate_evidence_store_path,
        record_delegate_evidence,
    )

    clear_delegate_evidence_records(clear_durable=True)
    record_delegate_evidence(
        lane="review",
        status="succeeded",
        result_summary=(
            "prompt: private body. message id 123456789012345678. "
            "User: sensitive text. "
            "high entropy abcdef1234567890abcdef1234567890abcdef1234567890"
        ),
        session_key="platform:discord:guild:channel:user",
        child_session_id="child-session-987654321098765432",
        active_task_id="active-123456789012345678",
        goal_id="goal-987654321098765432",
    )

    rendered = get_delegate_evidence_store_path().read_text(encoding="utf-8")
    assert "private body" not in rendered
    assert "sensitive text" not in rendered
    assert "123456789012345678" not in rendered
    assert "987654321098765432" not in rendered
    assert "abcdef1234567890abcdef1234567890abcdef1234567890" not in rendered
    assert "platform:discord:guild:channel:user" not in rendered


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


def test_durable_store_reload_preserves_trusted_delegate_evidence_safely(tmp_path, monkeypatch):
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    from gateway.delegate_evidence import (
        TRUSTED_DELEGATE_PROVENANCE,
        clear_delegate_evidence_records,
        get_recent_delegate_evidence,
        record_delegate_evidence,
    )
    from gateway.quality_lanes import require_quality_lane_section

    clear_delegate_evidence_records(clear_durable=True)
    record_delegate_evidence(
        lane="review",
        status="succeeded",
        result_summary="Reloaded trusted review.",
        session_key="reload-trusted",
    )
    clear_delegate_evidence_records()
    records = get_recent_delegate_evidence(session_id="reload-trusted")

    section = require_quality_lane_section(
        "Review and commit code.",
        delegate_evidence=records,
    )

    assert records[0]["provenance"] == TRUSTED_DELEGATE_PROVENANCE
    assert "real subagent used: yes" in section
    assert "Reloaded trusted review." in section


def test_untrusted_durable_record_is_ignored_for_real_subagent_claim(tmp_path, monkeypatch):
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    from gateway.delegate_evidence import get_delegate_evidence_store_path, get_recent_delegate_evidence
    from gateway.quality_lanes import require_quality_lane_section

    store_path = get_delegate_evidence_store_path()
    store_path.write_text(
        json.dumps(
            {
                "records": [
                    {
                        "evidence_id": "delegate-untrustedrecord",
                        "provenance": "untrusted",
                        "evidence_source": "delegate_task",
                        "delegate_name": "delegate_task",
                        "delegate_type": "subagent",
                        "status": "succeeded",
                        "lane": "review",
                        "safe_result_summary": "untrusted durable",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    section = require_quality_lane_section(
        "Review and commit code.",
        delegate_evidence=get_recent_delegate_evidence(),
    )

    assert "real subagent used: no" in section
    assert "real subagent used: yes" not in section
    assert "untrusted durable" not in section


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
