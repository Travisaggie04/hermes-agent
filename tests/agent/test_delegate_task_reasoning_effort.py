"""Reasoning-effort selection for delegated subagents."""

from __future__ import annotations

import threading
from unittest.mock import MagicMock, patch

from tools.delegate_tool import (
    _build_child_agent,
    _build_child_system_prompt,
    delegate_task,
    _resolve_child_reasoning_config,
)


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
    parent.enabled_toolsets = ["terminal", "file", "delegation"]
    parent.valid_tool_names = []
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


class _FakeAgent:
    instances = []

    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)
        self.base_url = kwargs.get("base_url")
        self.api_key = kwargs.get("api_key")
        self.provider = kwargs.get("provider")
        self.api_mode = kwargs.get("api_mode")
        self.acp_command = kwargs.get("acp_command")
        self.acp_args = kwargs.get("acp_args") or []
        self.model = kwargs.get("model")
        self.platform = kwargs.get("platform") or "cli"
        self.providers_allowed = kwargs.get("providers_allowed")
        self.providers_ignored = kwargs.get("providers_ignored")
        self.providers_order = kwargs.get("providers_order")
        self.provider_sort = kwargs.get("provider_sort")
        self.openrouter_min_coding_score = kwargs.get("openrouter_min_coding_score")
        self.enabled_toolsets = kwargs.get("enabled_toolsets")
        self.reasoning_config = kwargs.get("reasoning_config")
        self._credential_pool = None
        _FakeAgent.instances.append(self)

    def run_conversation(self, *args, **kwargs):
        return {"final_response": "ok", "completed": True, "api_calls": 1}

    def close(self):
        pass


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


def test_delegate_task_rejects_invalid_top_level_reasoning_effort_before_spawn():
    with patch("tools.delegate_tool._build_child_agent") as build_child:
        raw = delegate_task(
            goal="Summarize status",
            reasoning_effort="turbo",
            parent_agent=_make_parent({"enabled": True, "effort": "medium"}),
        )

    assert "reasoning_effort" in raw
    assert "turbo" in raw
    build_child.assert_not_called()


def test_delegate_task_rejects_invalid_per_task_reasoning_effort_before_spawn():
    with patch("tools.delegate_tool._build_child_agent") as build_child:
        raw = delegate_task(
            tasks=[{"goal": "Summarize status", "reasoning_effort": "turbo"}],
            parent_agent=_make_parent({"enabled": True, "effort": "medium"}),
        )

    assert "Task 0 reasoning_effort" in raw
    assert "turbo" in raw
    build_child.assert_not_called()


def test_delegate_task_rejects_invalid_config_reasoning_effort_before_spawn(monkeypatch):
    monkeypatch.setattr(
        "tools.delegate_tool._load_config",
        lambda: {"reasoning_effort": "turbo", "max_iterations": 10},
    )

    with patch("tools.delegate_tool._build_child_agent") as build_child:
        raw = delegate_task(
            goal="Summarize status",
            parent_agent=_make_parent({"enabled": True, "effort": "medium"}),
        )

    assert "delegation.reasoning_effort" in raw
    assert "turbo" in raw
    build_child.assert_not_called()


def test_build_child_agent_passes_resolved_reasoning_config_to_subagent(monkeypatch):
    parent = _make_parent({"enabled": True, "effort": "xhigh"})
    monkeypatch.setattr("tools.delegate_tool._load_config", lambda: {"reasoning_effort": "auto"})
    monkeypatch.setattr("tools.delegate_tool._get_max_spawn_depth", lambda: 2)
    monkeypatch.setattr("tools.delegate_tool._get_orchestrator_enabled", lambda: True)
    _FakeAgent.instances = []

    with patch("run_agent.AIAgent", _FakeAgent):
        child = _build_child_agent(
            task_index=0,
            goal="Implement a small bug fix",
            context="repo path: /tmp/example",
            toolsets=["terminal", "file"],
            model=None,
            max_iterations=10,
            task_count=1,
            parent_agent=parent,
            reasoning_effort=None,
            role="leaf",
        )

    assert getattr(child, "reasoning_config") == {"enabled": True, "effort": "medium"}
    assert getattr(child, "_delegate_reasoning_config") == {
        "enabled": True,
        "effort": "medium",
    }
    assert getattr(child, "_delegate_reasoning_effort") == "medium"


def test_orchestrator_prompt_teaches_nested_reasoning_effort_policy():
    prompt = _build_child_system_prompt(
        "Coordinate a review",
        role="orchestrator",
        max_spawn_depth=3,
        child_depth=1,
    )

    assert "reasoning_effort" in prompt
    assert "simple summaries/status" in prompt
    assert "normal coding/debugging" in prompt
    assert "PR review or ambiguous multi-file" in prompt
    assert "gateway/runtime/deploy/security/payment/destructive" in prompt


def test_orchestrator_subagent_propagates_per_task_effort_to_grandchild(monkeypatch):
    parent = _make_parent({"enabled": True, "effort": "xhigh"})
    monkeypatch.setattr("tools.delegate_tool._load_config", lambda: {"max_iterations": 10})
    monkeypatch.setattr("tools.delegate_tool._get_max_spawn_depth", lambda: 3)
    monkeypatch.setattr("tools.delegate_tool._get_orchestrator_enabled", lambda: True)
    monkeypatch.setattr(
        "tools.delegate_tool._resolve_delegation_credentials",
        lambda cfg, parent_agent: {
            "model": None,
            "provider": None,
            "base_url": None,
            "api_key": None,
            "api_mode": None,
            "command": None,
            "args": None,
        },
    )
    _FakeAgent.instances = []

    with patch("run_agent.AIAgent", _FakeAgent):
        orchestrator = _build_child_agent(
            task_index=0,
            goal="Coordinate a review",
            context=None,
            toolsets=["terminal", "file"],
            model=None,
            max_iterations=10,
            task_count=1,
            parent_agent=parent,
            reasoning_effort="high",
            role="orchestrator",
        )
        assert "delegation" in getattr(orchestrator, "enabled_toolsets")
        assert getattr(orchestrator, "reasoning_config") == {
            "enabled": True,
            "effort": "high",
        }

        delegate_task(
            goal="Summarize status",
            reasoning_effort="low",
            parent_agent=orchestrator,
        )

    grandchild = _FakeAgent.instances[-1]
    assert grandchild is not orchestrator
    assert getattr(grandchild, "reasoning_config") == {"enabled": True, "effort": "low"}
    assert getattr(grandchild, "_delegate_reasoning_effort") == "low"
