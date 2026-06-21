"""Non-coder PM decision packets for supervised Mission Control lanes.

The helpers here are pure formatting and classification code. They do not read
files, call GitHub, mutate records, dispatch work, or inspect secrets.
"""

from __future__ import annotations

import re
from typing import Any


ALLOWED_RECOMMENDATIONS = {
    "APPROVE_NEXT_STEP",
    "RECOMMEND_HUMAN_REVIEW_AND_MERGE",
    "RECOMMEND_KEEP_DRAFT",
    "RECOMMEND_REQUEST_CHANGES",
    "RECOMMEND_CLOSE",
    "RUN_ANOTHER_READ_ONLY_AUDIT",
    "BLOCKED_DO_NOT_MERGE",
    "DO_NOT_PROCEED",
}
ALLOWED_RISK_LEVELS = {"low", "medium", "high", "blocked"}
SENSITIVE_VALUE_PATTERNS = (
    re.compile(r"\bghp_[A-Za-z0-9_]{8,}\b", re.IGNORECASE),
    re.compile(r"\bgithub_pat_[A-Za-z0-9_]{8,}\b", re.IGNORECASE),
    re.compile(r"\b(?:ghp|github_pat|sk|xox[baprs])-[-A-Za-z0-9_]{8,}\b", re.IGNORECASE),
    re.compile(r"\bBearer\s+[-A-Za-z0-9._~+/]+=*\b", re.IGNORECASE),
    re.compile(r"\bAKIA[0-9A-Z]{12,}\b"),
)


def build_pm_decision_packet(
    *,
    goal: str,
    work_performed: list[str] | tuple[str, ...],
    result_status: str,
    risk_level: str,
    risk_explanation: str,
    rollback_note: str,
    travis_decision_needed: str,
    recommended_decision: str,
    next_safe_action: str,
    changed_files: list[str] | tuple[str, ...] = (),
    pr_url: str = "",
    tests: list[str] | tuple[str, ...] = (),
    blockers: list[str] | tuple[str, ...] = (),
    confidence: str = "medium",
    safety_checklist: dict[str, bool | str] | None = None,
    request_summary: str = "",
    operator_summary: str = "",
) -> dict[str, Any]:
    """Build a consistent non-coder decision packet.

    The packet intentionally uses explicit booleans for dangerous action classes
    so UI/reporting surfaces can fail closed if anything is uncertain.
    """

    recommendation = _canonical_recommendation(recommended_decision)
    risk = risk_level.strip().lower() if risk_level.strip().lower() in ALLOWED_RISK_LEVELS else "blocked"
    checks = _safety_defaults(safety_checklist)
    normalized_blockers = _clean_list(blockers)
    pause_reasons = _pause_reasons(
        risk_level=risk,
        blockers=normalized_blockers,
        safety_checklist=checks,
        recommendation=recommendation,
    )
    summary = operator_summary or _summary_for(
        goal=goal,
        result_status=result_status,
        recommendation=recommendation,
        risk_level=risk,
        blockers=normalized_blockers,
    )
    return {
        "source": "mission_control_pm_decision_packet_v1",
        "display_only": True,
        "trusted_for_execution": False,
        "would_execute": False,
        "execution_enabled": False,
        "plain_english_summary": _clean_text(summary, max_chars=600),
        "goal": _clean_text(goal, max_chars=600),
        "request_summary": _clean_text(request_summary or goal, max_chars=600),
        "work_performed": _clean_list(work_performed),
        "changed_files": _clean_list(changed_files),
        "pr_url": _clean_text(pr_url, max_chars=300),
        "tests": _clean_list(tests),
        "result_status": _clean_text(result_status, max_chars=120) or "blocked",
        "risk_level": risk,
        "risk_explanation": _clean_text(risk_explanation, max_chars=800),
        "rollback_note": _clean_text(rollback_note, max_chars=800),
        "safety_checklist": checks,
        "travis_decision_needed": _clean_text(travis_decision_needed, max_chars=800),
        "recommended_decision": recommendation,
        "confidence": _confidence(confidence),
        "next_safe_action": _clean_text(next_safe_action, max_chars=800),
        "blocked_reasons": normalized_blockers,
        "non_coder_pause_reasons": pause_reasons,
        "human_review_required": _human_review_required(recommendation, checks),
        "high_risk_actions_blocked": _high_risk_actions_blocked(checks),
    }


def build_read_only_result_pm_decision_packet(
    *,
    status: dict[str, Any],
    run_id: str,
    report_id: str,
    record_counts: dict[str, int],
) -> dict[str, Any]:
    readiness = _mapping(status.get("orchestration_readiness"))
    runtime = _mapping(status.get("runtime_provenance"))
    baseline = _mapping(status.get("accepted_baseline_record"))
    blockers = _text_list(readiness.get("blocked_reasons"))
    runtime_state = _clean_text(runtime.get("primary_status")) or "unknown"
    return build_pm_decision_packet(
        goal="Inspect Hermes/Mission Control current state and produce an operator handoff summary.",
        request_summary="One supervised read-only Mission Control status report.",
        work_performed=[
            f"Read Mission Control status projection for run {run_id}.",
            f"Captured record counts: total={record_counts.get('total', 0)}.",
            f"Checked accepted baseline {baseline.get('baseline_id', 'unknown')}.",
            "Appended one result ReportRecord and one terminal RunRecord through the guarded backend path.",
        ],
        changed_files=(),
        pr_url="",
        tests=["backend one-run read-only gate authorized the status report packet"],
        result_status="completed",
        risk_level="low",
        risk_explanation=(
            "This was a read-only status report. It did not edit source files, create commits, "
            "open PRs, deploy, restart, switch runtimes, dispatch workers, or use external systems."
        ),
        rollback_note=(
            f"No rollback is needed because no files or services changed. Runtime provenance stayed {runtime_state}; "
            "the existing AcceptedBaselineRecord rollback pointer remains the recovery path."
        ),
        safety_checklist={
            "files_changed": False,
            "commits_created": False,
            "prs_created": False,
            "merged": False,
            "deploy_restart_runtime_switch": False,
            "dispatch_session_worker": False,
            "external_systems": False,
            "sensitive_values_printed": False,
        },
        travis_decision_needed=(
            "Decide whether this status report is clear enough to use as the starting point for the next bounded lane."
        ),
        recommended_decision="APPROVE_NEXT_STEP" if runtime_state == "CLEAN_AND_ALIGNED" else "DO_NOT_PROCEED",
        confidence="high" if runtime_state == "CLEAN_AND_ALIGNED" else "medium",
        next_safe_action=(
            "Use Jenny for another supervised read-only or draft-only lane; keep merge/deploy/restart/runtime switch blocked."
        ),
        blockers=blockers,
        operator_summary=(
            "Jenny completed a read-only operator handoff report. It is safe to use for deciding the next bounded lane; "
            "broader autonomy remains blocked."
        ),
    ) | {"report_id": _clean_text(report_id), "run_id": _clean_text(run_id)}


def build_pr_review_pm_decision_packet(
    *,
    pr_number: int | str,
    title: str,
    url: str,
    state: str,
    is_draft: bool,
    merged: bool,
    base_branch: str,
    head_branch: str,
    changed_files: list[str] | tuple[str, ...],
    commit_shas: list[str] | tuple[str, ...],
    checks: list[str] | tuple[str, ...],
    smoke_test_artifact: bool = False,
    expected_file: str = "",
) -> dict[str, Any]:
    blockers: list[str] = []
    files = _clean_list(changed_files)
    commits = _clean_list(commit_shas)
    if merged:
        blockers.append("PR is already merged.")
    if state.lower() != "open":
        blockers.append("PR is not open.")
    if not is_draft:
        blockers.append("PR is not draft.")
    if expected_file and files != [expected_file]:
        blockers.append("PR changed files outside the approved scope.")
    if len(commits) != 1:
        blockers.append("PR does not have exactly one commit.")
    if not checks:
        blockers.append("No check evidence was provided.")
    risk_level = "blocked" if blockers else "low"
    recommendation = "BLOCKED_DO_NOT_MERGE" if blockers else (
        "RECOMMEND_KEEP_DRAFT" if smoke_test_artifact else "RECOMMEND_HUMAN_REVIEW_AND_MERGE"
    )
    decision = (
        "Decide whether to leave this smoke-test PR open as evidence or close it as completed."
        if smoke_test_artifact and not blockers
        else "Review the PR as a human before any merge decision."
    )
    return build_pm_decision_packet(
        goal=f"Review PR #{pr_number}: {title}",
        request_summary="Non-coder PM review of a Codex/Jenny-created draft PR.",
        work_performed=[
            f"Inspected PR #{pr_number} metadata.",
            f"Confirmed base {base_branch} and branch {head_branch}.",
            f"Reviewed {len(files)} changed file(s) and {len(commits)} commit(s).",
            "Reviewed available CI/check evidence.",
        ],
        changed_files=files,
        pr_url=url,
        tests=checks,
        result_status="needs review" if not blockers else "blocked",
        risk_level=risk_level,
        risk_explanation=(
            "Low risk because this is a draft-only documentation PR with human review required before merge."
            if not blockers
            else "Do not proceed until the PR evidence matches the approved scope."
        ),
        rollback_note=(
            "No live rollback is needed. The PR can be left draft, closed, or updated before merge; no runtime changed."
        ),
        safety_checklist={
            "files_changed": bool(files),
            "commits_created": bool(commits),
            "prs_created": True,
            "merged": merged,
            "deploy_restart_runtime_switch": False,
            "dispatch_session_worker": False,
            "external_systems": False,
            "sensitive_values_printed": False,
        },
        travis_decision_needed=decision,
        recommended_decision=recommendation,
        confidence="high" if not blockers else "medium",
        next_safe_action=(
            "Leave PR draft/open for evidence, or close it as a completed smoke test; do not merge automatically."
            if smoke_test_artifact and not blockers
            else "Human-review the PR and approve a separate merge lane only if the content is useful."
        ),
        blockers=blockers,
        operator_summary=(
            f"PR #{pr_number} is valid as a draft-only smoke-test artifact; merging is optional and not required."
            if smoke_test_artifact and not blockers
            else ""
        ),
    ) | {
        "pr_number": str(pr_number),
        "base_branch": _clean_text(base_branch),
        "head_branch": _clean_text(head_branch),
        "commit_shas": commits,
    }


def render_pm_decision_packet(packet: dict[str, Any]) -> str:
    """Render a packet into stable operator-facing Markdown."""

    checklist = _mapping(packet.get("safety_checklist"))
    sections = [
        "PM decision packet",
        f"Plain-English summary: {_clean_text(packet.get('plain_english_summary'))}",
        f"Goal / request: {_clean_text(packet.get('goal'))}",
        "Work performed: " + _join_or_none(_text_list(packet.get("work_performed"))),
        "Changed files: " + _join_or_none(_text_list(packet.get("changed_files"))),
        f"PR link: {_clean_text(packet.get('pr_url')) or 'none'}",
        "Tests/checks: " + _join_or_none(_text_list(packet.get("tests"))),
        f"Result status: {_clean_text(packet.get('result_status'))}",
        f"Risk level: {_clean_text(packet.get('risk_level'))}",
        f"Risk explanation: {_clean_text(packet.get('risk_explanation'))}",
        f"Rollback / undo: {_clean_text(packet.get('rollback_note'))}",
        "Safety checklist: " + _safety_text(checklist),
        f"What Travis needs to decide: {_clean_text(packet.get('travis_decision_needed'))}",
        f"Recommended decision: {_clean_text(packet.get('recommended_decision'))}",
        f"Confidence: {_clean_text(packet.get('confidence'))}",
        f"Next safe action: {_clean_text(packet.get('next_safe_action'))}",
        "Still blocked / pause reasons: " + _join_or_none(_text_list(packet.get("non_coder_pause_reasons"))),
    ]
    return "\n".join(sections)


def _summary_for(*, goal: str, result_status: str, recommendation: str, risk_level: str, blockers: list[str]) -> str:
    if blockers or recommendation in {"BLOCKED_DO_NOT_MERGE", "DO_NOT_PROCEED"}:
        return "Pause. Jenny found missing or unsafe evidence before the next step."
    return (
        f"Jenny reviewed the work for '{_clean_text(goal, max_chars=120)}'. "
        f"Status is {_clean_text(result_status) or 'unknown'}, risk is {risk_level}, "
        f"and the recommendation is {recommendation}."
    )


def _pause_reasons(
    *,
    risk_level: str,
    blockers: list[str],
    safety_checklist: dict[str, bool | str],
    recommendation: str,
) -> list[str]:
    reasons = list(blockers)
    if risk_level in {"high", "blocked"}:
        reasons.append(f"risk level is {risk_level}")
    if recommendation in {"BLOCKED_DO_NOT_MERGE", "DO_NOT_PROCEED"}:
        reasons.append("recommendation says do not proceed")
    unsafe_true = [
        label
        for label in ("merged", "deploy_restart_runtime_switch", "dispatch_session_worker", "external_systems", "sensitive_values_printed")
        if safety_checklist.get(label) is True
    ]
    if unsafe_true:
        reasons.append("unsafe action observed: " + ", ".join(unsafe_true))
    return _clean_list(reasons)


def _human_review_required(recommendation: str, checklist: dict[str, bool | str]) -> bool:
    return (
        recommendation
        in {"RECOMMEND_HUMAN_REVIEW_AND_MERGE", "RECOMMEND_KEEP_DRAFT", "RECOMMEND_CLOSE", "RECOMMEND_REQUEST_CHANGES"}
        or checklist.get("prs_created") is True
    )


def _high_risk_actions_blocked(checklist: dict[str, bool | str]) -> bool:
    return not any(
        checklist.get(label) is True
        for label in ("merged", "deploy_restart_runtime_switch", "dispatch_session_worker", "external_systems", "sensitive_values_printed")
    )


def _canonical_recommendation(value: str) -> str:
    text = _clean_text(value).upper().replace(" ", "_").replace("-", "_")
    return text if text in ALLOWED_RECOMMENDATIONS else "DO_NOT_PROCEED"


def _confidence(value: str) -> str:
    text = _clean_text(value).lower()
    return text if text in {"high", "medium", "low"} else "medium"


def _safety_defaults(values: dict[str, bool | str] | None) -> dict[str, bool | str]:
    defaults: dict[str, bool | str] = {
        "files_changed": False,
        "commits_created": False,
        "prs_created": False,
        "merged": False,
        "deploy_restart_runtime_switch": False,
        "dispatch_session_worker": False,
        "external_systems": False,
        "sensitive_values_printed": False,
    }
    for key, value in (values or {}).items():
        defaults[_clean_text(key)] = value if isinstance(value, bool) else _clean_text(value)
    return defaults


def _safety_text(checklist: dict[str, bool | str]) -> str:
    labels = [
        ("files changed", "files_changed"),
        ("commits", "commits_created"),
        ("PRs", "prs_created"),
        ("merge", "merged"),
        ("deploy/restart/runtime switch", "deploy_restart_runtime_switch"),
        ("dispatch/session-send/worker", "dispatch_session_worker"),
        ("Waha/queue/model/social/payment", "external_systems"),
        ("sensitive values printed", "sensitive_values_printed"),
    ]
    return "; ".join(f"{label}={'yes' if checklist.get(key) is True else 'no'}" for label, key in labels)


def _clean_list(values: list[str] | tuple[str, ...] | Any) -> list[str]:
    if not isinstance(values, (list, tuple)):
        return []
    output: list[str] = []
    for value in values:
        text = _clean_text(value)
        if text and text not in output:
            output.append(text)
    return output


def _text_list(value: Any) -> list[str]:
    return [_clean_text(item) for item in value] if isinstance(value, list) else []


def _clean_text(value: Any, *, max_chars: int = 1000) -> str:
    if value is None:
        return ""
    text = str(value).replace("\x00", "").strip()
    for pattern in SENSITIVE_VALUE_PATTERNS:
        text = pattern.sub("[redacted sensitive value]", text)
    return text[:max_chars]


def _mapping(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _join_or_none(values: list[str]) -> str:
    return "; ".join(values) if values else "none"
