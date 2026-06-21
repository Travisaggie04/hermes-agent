"""Reasoning-effort selection for delegated subagents."""

from __future__ import annotations

import threading
from unittest.mock import MagicMock, patch

from tools.delegate_tool import delegate_task, _resolve_child_reasoning_config


def _make_parent(reasoning_config=None):
    parent = MagicMock()
    parent.base_url = "https://example.test/v1"
    parent.api_key = "***"
    parent.provider = "openai-codex"
    parent.api_mode = "chat_completions"
    parent.model = "gpt-5.5"
    parent.platform = "cli"
    parent.providers_allowed = None
    parent.providers_ignored = None
    parent.providers_order = None
    parent.provider_sort = None
    parent._session_db = None
    parent._delegate_depth = 0
    parent._active_children = []
    parent._active_children_lock = threading.Lock()
    parent._print_fn = None
    parent.tool_progress_callback = None
    parent.thinking_callback = None
    parent._memory_manager = None
    parent.session_id = "parent-session"
    parent.reasoning_config = reasoning_config
    return parent


def test_explicit_task_reasoning_effort_beats_auto_config():
    parent_reasoning = {"enabled": True, "effort": "xhigh"}

    result = _resolve_child_reasoning_config(
        parent_reasoning=parent_reasoning,
        delegation_cfg={"reasoning_effort": "auto"},
        requested_effort="high",
        goal="Summarize this status log",
        context="",
        toolsets=[],
    )

    assert result == {"enabled": True, "effort": "high"}


def test_auto_reasoning_effort_uses_low_for_simple_status_tasks():
    result = _resolve_child_reasoning_config(
        parent_reasoning={"enabled": True, "effort": "xhigh"},
        delegation_cfg={"reasoning_effort": "auto"},
        requested_effort=None,
        goal="Summarize the current status and format the answer as bullets",
        context="read-only lookup",
        toolsets=["file"],
    )

    assert result == {"enabled": True, "effort": "low"}


def test_auto_reasoning_effort_uses_medium_for_normal_coding_tasks():
    result = _resolve_child_reasoning_config(
        parent_reasoning={"enabled": True, "effort": "xhigh"},
        delegation_cfg={"reasoning_effort": "auto"},
        requested_effort=None,
        goal="Implement a small bug fix and add a focused test",
        context="repo path: /tmp/example",
        toolsets=["terminal", "file"],
    )

    assert result == {"enabled": True, "effort": "medium"}


def test_auto_reasoning_effort_uses_high_for_pr_review_or_ambiguous_bug_hunts():
    result = _resolve_child_reasoning_config(
        parent_reasoning={"enabled": True, "effort": "medium"},
        delegation_cfg={"reasoning_effort": "auto"},
        requested_effort=None,
        goal="Review this PR and investigate an ambiguous multi-file failure",
        context="failing tests are intermittent",
        toolsets=["terminal", "file"],
    )

    assert result == {"enabled": True, "effort": "high"}


def test_auto_reasoning_effort_uses_xhigh_for_gateway_security_deploy_tasks():
    result = _resolve_child_reasoning_config(
        parent_reasoning={"enabled": True, "effort": "medium"},
        delegation_cfg={"reasoning_effort": "auto"},
        requested_effort=None,
        goal="Review gateway restart and production deploy readiness with credential safety",
        context="live service, token hygiene, rollback gate",
        toolsets=["terminal", "file"],
    )

    assert result == {"enabled": True, "effort": "xhigh"}


def test_delegate_task_passes_top_level_reasoning_effort_to_child_builder():
    child = MagicMock()
    child._delegate_saved_tool_names = []
    child._credential_pool = None

    with patch("tools.delegate_tool._build_child_agent", return_value=child) as build_child:
        with patch("tools.delegate_tool._run_single_child") as run_child:
            run_child.return_value = {
                "task_index": 0,
                "status": "completed",
                "summary": "ok",
                "api_calls": 1,
                "duration_seconds": 0.1,
            }

            delegate_task(
                goal="Summarize status",
                reasoning_effort="low",
                parent_agent=_make_parent({"enabled": True, "effort": "xhigh"}),
            )

    assert build_child.call_args.kwargs["reasoning_effort"] == "low"


def test_delegate_task_per_task_reasoning_effort_beats_top_level_effort():
    child = MagicMock()
    child._delegate_saved_tool_names = []
    child._credential_pool = None

    with patch("tools.delegate_tool._build_child_agent", return_value=child) as build_child:
        with patch("tools.delegate_tool._run_single_child") as run_child:
            run_child.return_value = {
                "task_index": 0,
                "status": "completed",
                "summary": "ok",
                "api_calls": 1,
                "duration_seconds": 0.1,
            }

            delegate_task(
                tasks=[{"goal": "Review PR", "reasoning_effort": "high"}],
                reasoning_effort="low",
                parent_agent=_make_parent({"enabled": True, "effort": "xhigh"}),
            )

    assert build_child.call_args.kwargs["reasoning_effort"] == "high"
