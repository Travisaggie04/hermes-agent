from __future__ import annotations

from mission_control.pm_decision_packet import (
    build_pm_decision_packet,
    build_pr_review_pm_decision_packet,
    build_read_only_result_pm_decision_packet,
    render_pm_decision_packet,
)


def test_read_only_pm_packet_has_non_coder_decision_sections() -> None:
    packet = build_read_only_result_pm_decision_packet(
        status={
            "runtime_provenance": {"primary_status": "CLEAN_AND_ALIGNED"},
            "accepted_baseline_record": {
                "baseline_id": "accepted-pr413",
                "runtime_path": "/runtime",
            },
            "orchestration_readiness": {"blocked_reasons": ["merge remains blocked"]},
        },
        run_id="run-read-only",
        report_id="report-read-only",
        record_counts={"total": 10, "RunRecord": 2, "ReportRecord": 2},
    )
    rendered = render_pm_decision_packet(packet)

    assert packet["plain_english_summary"].startswith("Jenny completed a read-only operator handoff")
    assert packet["risk_level"] == "low"
    assert packet["recommended_decision"] == "APPROVE_NEXT_STEP"
    assert packet["confidence"] == "high"
    assert packet["changed_files"] == []
    assert packet["safety_checklist"]["files_changed"] is False
    assert packet["high_risk_actions_blocked"] is True
    assert "PM decision packet" in rendered
    assert "Plain-English summary:" in rendered
    assert "Changed files: none" in rendered
    assert "Tests/checks:" in rendered
    assert "Risk level: low" in rendered
    assert "Rollback / undo:" in rendered
    assert "Recommended decision: APPROVE_NEXT_STEP" in rendered
    assert "deploy/restart/runtime switch=no" in rendered


def test_pr_review_packet_recommends_keep_draft_for_smoke_test_artifact() -> None:
    packet = build_pr_review_pm_decision_packet(
        pr_number=414,
        title="docs: record scoped PR creation smoke test",
        url="https://github.com/Travisaggie04/hermes-agent/pull/414",
        state="OPEN",
        is_draft=True,
        merged=False,
        base_branch="accepted-live/approval-safety-5ad8906",
        head_branch="codex/scoped-pr-docs-smoke-test",
        changed_files=("docs/mission-control/jenny-engineering-orchestrator-runbook-2026-06-19.md",),
        commit_shas=("698897915e6096f6f232956713a8fee6f9607a5a",),
        checks=("nix ubuntu passed", "nix macOS passed", "supply-chain audit passed"),
        smoke_test_artifact=True,
        expected_file="docs/mission-control/jenny-engineering-orchestrator-runbook-2026-06-19.md",
    )

    assert packet["recommended_decision"] == "RECOMMEND_KEEP_DRAFT"
    assert packet["risk_level"] == "low"
    assert packet["human_review_required"] is True
    assert packet["high_risk_actions_blocked"] is True
    assert packet["blocked_reasons"] == []
    assert "valid as a draft-only smoke-test artifact" in packet["plain_english_summary"]


def test_pr_review_packet_blocks_when_evidence_is_missing() -> None:
    packet = build_pr_review_pm_decision_packet(
        pr_number=414,
        title="docs: unsafe",
        url="https://github.com/Travisaggie04/hermes-agent/pull/414",
        state="OPEN",
        is_draft=False,
        merged=False,
        base_branch="accepted-live/approval-safety-5ad8906",
        head_branch="codex/scoped-pr-docs-smoke-test",
        changed_files=("docs/mission-control/jenny-engineering-orchestrator-runbook-2026-06-19.md", "web/src/App.tsx"),
        commit_shas=("a" * 40, "b" * 40),
        checks=(),
        smoke_test_artifact=True,
        expected_file="docs/mission-control/jenny-engineering-orchestrator-runbook-2026-06-19.md",
    )

    assert packet["recommended_decision"] == "BLOCKED_DO_NOT_MERGE"
    assert packet["risk_level"] == "blocked"
    assert "PR is not draft." in packet["blocked_reasons"]
    assert "PR changed files outside the approved scope." in packet["blocked_reasons"]
    assert "No check evidence was provided." in packet["blocked_reasons"]
    assert packet["non_coder_pause_reasons"]


def test_pm_packet_redacts_sensitive_values() -> None:
    packet = build_pm_decision_packet(
        goal="Review ghp_1234567890abcdef",
        work_performed=("Saw Bearer abcdef1234567890",),
        result_status="completed",
        risk_level="low",
        risk_explanation="No sensitive value should render.",
        rollback_note="Close the draft PR.",
        travis_decision_needed="Review the summary.",
        recommended_decision="APPROVE_NEXT_STEP",
        next_safe_action="Continue.",
    )
    rendered = render_pm_decision_packet(packet)

    assert "ghp_1234567890abcdef" not in rendered
    assert "Bearer abcdef1234567890" not in rendered
    assert "[redacted sensitive value]" in rendered
