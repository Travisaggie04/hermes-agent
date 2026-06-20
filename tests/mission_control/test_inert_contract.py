"""Shared inert live-operation contract coverage."""

from __future__ import annotations

from mission_control.action_policy_guardrails import evaluate_action_policy, get_action_policy_guardrails
from mission_control.domain_governance import get_domain_governance_policies
from mission_control.global_resource_guard import evaluate_global_resource_guard, get_global_resource_guard_policy
from mission_control.inert_contract import INERT_LIVE_OPERATION_FLAGS, inert_live_operation_flags
from mission_control.lane_preflight import run_lane_start_preflight
from mission_control.model_registry import get_model_registry_records
from mission_control.pr_merge_packet_hash import validate_pr_merge_packet_hash
from mission_control.pr_merge_verifier_gate import evaluate_pr_merge_verifier_gate, get_pr_merge_verifier_gate_policy
from mission_control.preflight import evaluate_lane_start_preflight
from mission_control.records import TaskControlEnvelope
from mission_control.runtime_worktree_guard import evaluate_runtime_worktree_guard
from mission_control.start_gate import evaluate_start_gate
from mission_control.storage_guard import build_storage_cleanup_manifest, evaluate_storage_guard, get_storage_guard_policy
from mission_control.verifier_workflow import evaluate_verifier_workflow, get_verifier_workflow_policy


def _assert_inert_contract(payload: dict) -> None:
    for key, expected in INERT_LIVE_OPERATION_FLAGS.items():
        assert payload[key] is expected


def _lane_start_request() -> dict:
    return {
        "active_lane": "contract coverage lane",
        "mode": "bounded implementation in a new clean worktree only",
        "allowed_actions": ("inspect status",),
        "forbidden_actions": ("no live enforcement", "no deploy", "no secrets"),
        "stop_condition": "Stop after dry-run contract check.",
        "report_requirements": ("tests run",),
        "repo_target": "Travisaggie04/hermes-agent",
        "branch": "contract-coverage",
        "worktree_state": "clean",
        "token_context_policy": "bounded records only",
        "requested_actions": ("inspect status",),
    }


def _task_control_envelope() -> TaskControlEnvelope:
    return TaskControlEnvelope(
        envelope_id="contract-envelope",
        active_lane="contract coverage lane",
        mode="bounded implementation in a new clean worktree only",
        allowed_actions=("inspect status",),
        forbidden_actions=("no live enforcement", "no deploy", "no secrets"),
        current_repo="Travisaggie04/hermes-agent",
        stop_condition="Stop after dry-run contract check.",
        report_requirements=("tests run",),
        token_context_policy="bounded records only",
        metadata={"target_remote": "Travisaggie04/hermes-agent"},
    )


def test_common_inert_live_operation_flags_are_fail_closed():
    assert inert_live_operation_flags() == INERT_LIVE_OPERATION_FLAGS
    assert INERT_LIVE_OPERATION_FLAGS["inert_context_only"] is True
    for key, value in INERT_LIVE_OPERATION_FLAGS.items():
        if key != "inert_context_only":
            assert value is False


def test_policy_surfaces_share_inert_live_operation_contract():
    _assert_inert_contract(get_action_policy_guardrails())
    _assert_inert_contract(get_global_resource_guard_policy())
    _assert_inert_contract(get_storage_guard_policy())
    _assert_inert_contract(get_verifier_workflow_policy())
    _assert_inert_contract(get_pr_merge_verifier_gate_policy())
    for record in get_model_registry_records():
        _assert_inert_contract(record)
    for policy in get_domain_governance_policies():
        _assert_inert_contract(policy["enforcement"])


def test_evaluator_surfaces_share_inert_live_operation_contract():
    payloads = [
        evaluate_action_policy({"request": "Inspect approved status only."}),
        evaluate_global_resource_guard({}),
        evaluate_storage_guard({}),
        build_storage_cleanup_manifest({}),
        evaluate_verifier_workflow({}),
        evaluate_pr_merge_verifier_gate({}),
        validate_pr_merge_packet_hash({}, ""),
        evaluate_runtime_worktree_guard({}),
        run_lane_start_preflight(_lane_start_request()),
    ]
    payloads.append(evaluate_start_gate(_task_control_envelope()).metadata)
    payloads.append(evaluate_lane_start_preflight(_lane_start_request()).metadata)

    for payload in payloads:
        _assert_inert_contract(payload)
