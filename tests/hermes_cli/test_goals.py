"""Tests for hermes_cli/goals.py — persistent cross-turn goals."""

from __future__ import annotations

import json
from unittest.mock import patch, MagicMock

import pytest


# ──────────────────────────────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────────────────────────────


@pytest.fixture
def hermes_home(tmp_path, monkeypatch):
    """Isolated HERMES_HOME so SessionDB.state_meta writes don't clobber the real one."""
    from pathlib import Path

    home = tmp_path / ".hermes"
    home.mkdir()
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    monkeypatch.setenv("HERMES_HOME", str(home))

    # Bust the goal-module's DB cache for each test so it re-resolves HERMES_HOME.
    from hermes_cli import goals

    goals._DB_CACHE.clear()
    yield home
    goals._DB_CACHE.clear()


# ──────────────────────────────────────────────────────────────────────
# _parse_judge_response
# ──────────────────────────────────────────────────────────────────────


class TestParseJudgeResponse:
    def test_clean_json_done(self):
        from hermes_cli.goals import _parse_judge_response

        done, reason, _ = _parse_judge_response('{"done": true, "reason": "all good"}')
        assert done is True
        assert reason == "all good"

    def test_clean_json_continue(self):
        from hermes_cli.goals import _parse_judge_response

        done, reason, _ = _parse_judge_response('{"done": false, "reason": "more work needed"}')
        assert done is False
        assert reason == "more work needed"

    def test_blocked_reason_detector_is_prefix_based(self):
        from hermes_cli.goals import _reason_indicates_blocked

        assert _reason_indicates_blocked("blocked: missing token")
        assert _reason_indicates_blocked("needs user input: choose a branch")
        assert _reason_indicates_blocked("external dependency: CI is down")
        assert not _reason_indicates_blocked("not blocked; tests passed")
        assert not _reason_indicates_blocked("completed after removing blockers")

    def test_json_in_markdown_fence(self):
        from hermes_cli.goals import _parse_judge_response

        raw = '```json\n{"done": true, "reason": "done"}\n```'
        done, reason, _ = _parse_judge_response(raw)
        assert done is True
        assert "done" in reason

    def test_json_embedded_in_prose(self):
        """Some models prefix reasoning before emitting JSON — we extract it."""
        from hermes_cli.goals import _parse_judge_response

        raw = 'Looking at this... the agent says X. Verdict: {"done": false, "reason": "partial"}'
        done, reason, _ = _parse_judge_response(raw)
        assert done is False
        assert reason == "partial"

    def test_string_done_values(self):
        from hermes_cli.goals import _parse_judge_response

        for s in ("true", "yes", "done", "1"):
            done, _, _ = _parse_judge_response(f'{{"done": "{s}", "reason": "r"}}')
            assert done is True
        for s in ("false", "no", "not yet"):
            done, _, _ = _parse_judge_response(f'{{"done": "{s}", "reason": "r"}}')
            assert done is False

    def test_malformed_json_fails_open(self):
        """Non-JSON → not done, with error-ish reason (so judge_goal can map to continue)."""
        from hermes_cli.goals import _parse_judge_response

        done, reason, _ = _parse_judge_response("this is not json at all")
        assert done is False
        assert reason  # non-empty

    def test_empty_response(self):
        from hermes_cli.goals import _parse_judge_response

        done, reason, _ = _parse_judge_response("")
        assert done is False
        assert reason


# ──────────────────────────────────────────────────────────────────────
# judge_goal — fail-open semantics
# ──────────────────────────────────────────────────────────────────────


class TestJudgeGoal:
    def test_empty_goal_skipped(self):
        from hermes_cli.goals import judge_goal

        verdict, _, _ = judge_goal("", "some response")
        assert verdict == "skipped"

    def test_empty_response_continues(self):
        from hermes_cli.goals import judge_goal

        verdict, _, _ = judge_goal("ship the thing", "")
        assert verdict == "continue"

    def test_no_aux_client_continues(self):
        """Fail-open: if no aux client, we must return continue, not skipped/done."""
        from hermes_cli import goals

        with patch(
            "agent.auxiliary_client.get_text_auxiliary_client",
            return_value=(None, None),
        ):
            verdict, _, _ = goals.judge_goal("my goal", "my response")
        assert verdict == "continue"

    def test_api_error_continues(self):
        """Judge exception → fail-open continue (don't wedge progress on judge bugs)."""
        from hermes_cli import goals

        fake_client = MagicMock()
        fake_client.chat.completions.create.side_effect = RuntimeError("boom")
        with patch(
            "agent.auxiliary_client.get_text_auxiliary_client",
            return_value=(fake_client, "judge-model"),
        ):
            verdict, reason, _ = goals.judge_goal("goal", "response")
        assert verdict == "continue"
        assert "judge error" in reason.lower()

    def test_judge_says_done(self):
        from hermes_cli import goals

        fake_client = MagicMock()
        fake_client.chat.completions.create.return_value = MagicMock(
            choices=[
                MagicMock(
                    message=MagicMock(content='{"done": true, "reason": "achieved"}')
                )
            ]
        )
        with patch(
            "agent.auxiliary_client.get_text_auxiliary_client",
            return_value=(fake_client, "judge-model"),
        ):
            verdict, reason, _ = goals.judge_goal("goal", "agent response")
        assert verdict == "done"
        assert reason == "achieved"

    def test_judge_says_continue(self):
        from hermes_cli import goals

        fake_client = MagicMock()
        fake_client.chat.completions.create.return_value = MagicMock(
            choices=[
                MagicMock(
                    message=MagicMock(content='{"done": false, "reason": "not yet"}')
                )
            ]
        )
        with patch(
            "agent.auxiliary_client.get_text_auxiliary_client",
            return_value=(fake_client, "judge-model"),
        ):
            verdict, reason, _ = goals.judge_goal("goal", "agent response")
        assert verdict == "continue"
        assert reason == "not yet"


# ──────────────────────────────────────────────────────────────────────
# GoalManager lifecycle + persistence
# ──────────────────────────────────────────────────────────────────────


class TestGoalManager:
    def test_no_goal_initial(self, hermes_home):
        from hermes_cli.goals import GoalManager

        mgr = GoalManager(session_id="test-sid-1")
        assert mgr.state is None
        assert not mgr.is_active()
        assert not mgr.has_goal()
        assert "No active goal" in mgr.status_line()

    def test_set_then_status(self, hermes_home):
        from hermes_cli.goals import GoalManager

        mgr = GoalManager(session_id="test-sid-2", default_max_turns=5)
        state = mgr.set("port the thing")
        assert state.goal == "port the thing"
        assert state.status == "active"
        assert state.max_turns == 5
        assert state.turns_used == 0
        assert mgr.is_active()
        assert "active" in mgr.status_line().lower()
        assert "port the thing" in mgr.status_line()

    def test_set_rejects_empty(self, hermes_home):
        from hermes_cli.goals import GoalManager

        mgr = GoalManager(session_id="test-sid-3")
        with pytest.raises(ValueError):
            mgr.set("")
        with pytest.raises(ValueError):
            mgr.set("   ")

    def test_pause_and_resume(self, hermes_home):
        from hermes_cli.goals import GoalManager

        mgr = GoalManager(session_id="test-sid-4")
        mgr.set("goal text")
        mgr.pause(reason="user-paused")
        assert mgr.state.status == "paused"
        assert not mgr.is_active()
        assert mgr.has_goal()

        mgr.resume()
        assert mgr.state.status == "active"
        assert mgr.is_active()

    def test_clear(self, hermes_home):
        from hermes_cli.goals import GoalManager

        mgr = GoalManager(session_id="test-sid-5")
        mgr.set("goal")
        mgr.clear()
        assert mgr.state is None
        assert not mgr.is_active()

    def test_persistence_across_managers(self, hermes_home):
        """Key invariant: a second manager on the same session sees the goal.

        This is what makes /resume work — each session rebinds its
        GoalManager and picks up the saved state.
        """
        from hermes_cli.goals import GoalManager

        mgr1 = GoalManager(session_id="persist-sid")
        mgr1.set("do the thing")

        mgr2 = GoalManager(session_id="persist-sid")
        assert mgr2.state is not None
        assert mgr2.state.goal == "do the thing"
        assert mgr2.is_active()

    def test_evaluate_after_turn_done(self, hermes_home):
        """Judge says done → status=done, no continuation."""
        from hermes_cli import goals
        from hermes_cli.goals import GoalManager

        mgr = GoalManager(session_id="eval-sid-1")
        mgr.set("ship it")

        with patch.object(goals, "judge_goal", return_value=("done", "shipped", False)):
            decision = mgr.evaluate_after_turn("I shipped the feature.")

        assert decision["verdict"] == "done"
        assert decision["should_continue"] is False
        assert decision["continuation_prompt"] is None
        assert mgr.state.status == "done"
        assert mgr.state.turns_used == 1

    def test_evaluate_after_turn_continue_under_budget(self, hermes_home):
        from hermes_cli import goals
        from hermes_cli.goals import GoalManager

        mgr = GoalManager(session_id="eval-sid-2", default_max_turns=5)
        mgr.set("a long goal")

        with patch.object(goals, "judge_goal", return_value=("continue", "more work", False)):
            decision = mgr.evaluate_after_turn("made some progress")

        assert decision["verdict"] == "continue"
        assert decision["should_continue"] is True
        assert decision["continuation_prompt"] is not None
        assert "a long goal" in decision["continuation_prompt"]
        assert mgr.state.status == "active"
        assert mgr.state.turns_used == 1

    def test_evaluate_after_turn_budget_exhausted(self, hermes_home):
        """When turn budget hits ceiling, auto-pause instead of continuing."""
        from hermes_cli import goals
        from hermes_cli.goals import GoalManager

        mgr = GoalManager(session_id="eval-sid-3", default_max_turns=2)
        mgr.set("hard goal")

        with patch.object(goals, "judge_goal", return_value=("continue", "not yet", False)):
            d1 = mgr.evaluate_after_turn("step 1")
            assert d1["should_continue"] is True
            assert mgr.state.turns_used == 1
            assert mgr.state.status == "active"

            d2 = mgr.evaluate_after_turn("step 2")
            # turns_used is now 2 which equals max_turns → paused
            assert d2["should_continue"] is False
            assert mgr.state.status == "paused"
            assert mgr.state.turns_used == 2
            assert "budget" in (mgr.state.paused_reason or "").lower()

    def test_evaluate_after_turn_inactive(self, hermes_home):
        """evaluate_after_turn is a no-op when goal isn't active."""
        from hermes_cli.goals import GoalManager

        mgr = GoalManager(session_id="eval-sid-4")
        d = mgr.evaluate_after_turn("anything")
        assert d["verdict"] == "inactive"
        assert d["should_continue"] is False

        mgr.set("a goal")
        mgr.pause()
        d2 = mgr.evaluate_after_turn("anything")
        assert d2["verdict"] == "inactive"
        assert d2["should_continue"] is False

    def test_blocked_reason_stops_goal_without_marking_done(self, hermes_home):
        from hermes_cli import goals
        from hermes_cli.goals import GoalManager

        mgr = GoalManager(session_id="blocked-sid")
        mgr.set("ship safely")

        with patch.object(
            goals,
            "judge_goal",
            return_value=("continue", "blocked: missing deployment approval", False),
        ):
            decision = mgr.evaluate_after_turn("Need deployment approval before continuing.")

        assert decision["status"] == "blocked"
        assert decision["verdict"] == "blocked"
        assert decision["should_continue"] is False
        assert decision["continuation_prompt"] is None
        assert mgr.state.status == "blocked"
        assert "missing deployment approval" in (mgr.state.paused_reason or "")
        assert "Goal blocked" in decision["message"]

    def test_done_verdict_with_blocked_reason_still_blocks(self, hermes_home):
        from hermes_cli import goals
        from hermes_cli.goals import GoalManager

        mgr = GoalManager(session_id="blocked-done-sid")
        mgr.set("ship safely")

        with patch.object(
            goals,
            "judge_goal",
            return_value=("done", "blocked: user must pick a release window", False),
        ):
            decision = mgr.evaluate_after_turn("Blocked until Travis picks a release window.")

        assert decision["status"] == "blocked"
        assert decision["verdict"] == "blocked"
        assert mgr.state.status == "blocked"
        assert mgr.state.last_verdict == "done"

    def test_continuation_prompt_shape(self, hermes_home):
        """The continuation prompt must include an engineering work contract
        while staying a normal user-role message (no system-prompt mutation)."""
        from hermes_cli.goals import GoalManager

        mgr = GoalManager(session_id="cont-sid")
        mgr.set("port goal command to hermes")
        prompt = mgr.next_continuation_prompt()
        assert prompt is not None
        assert "Continuing engineering goal" in prompt
        assert "port goal command to hermes" in prompt
        assert "evidence already gathered" in prompt
        assert "next smallest concrete action" in prompt
        assert "Completion audit before final answer" in prompt
        assert "map every explicit requirement to current evidence" in prompt
        assert "treat missing, indirect, or stale evidence as incomplete" in prompt
        assert "Blocked audit before stopping" in prompt
        assert "name the exact missing input, failing command, or external dependency" in prompt
        assert "keep making safe progress if another bounded step remains" in prompt
        assert "Do not declare completion without evidence" in prompt
        assert prompt.strip()  # non-empty

    def test_continuation_prompt_carries_last_progress_checkpoint(self, hermes_home):
        """After a turn, the next continuation should carry a compact durable
        checkpoint so long goals survive context loss better."""
        from hermes_cli import goals
        from hermes_cli.goals import GoalManager

        mgr = GoalManager(session_id="checkpoint-sid")
        mgr.set("ship a reliable goal loop")

        with patch.object(
            goals,
            "judge_goal",
            return_value=("continue", "needs evidence", False),
        ):
            decision = mgr.evaluate_after_turn(
                "Changed hermes_cli/goals.py and ran tests/hermes_cli/test_goals.py."
            )

        assert decision["should_continue"] is True
        assert mgr.state.last_progress_excerpt is not None
        assert "Changed hermes_cli/goals.py" in mgr.state.last_progress_excerpt
        continuation = decision["continuation_prompt"]
        assert "Last progress checkpoint" in continuation
        assert "Changed hermes_cli/goals.py" in continuation
        assert "last judge reason: needs evidence" in continuation

    def test_status_report_includes_progress_and_next_step(self, hermes_home):
        from hermes_cli import goals
        from hermes_cli.goals import GoalManager

        mgr = GoalManager(session_id="status-report-sid")
        mgr.set("ship a reliable goal loop")
        with patch.object(
            goals,
            "judge_goal",
            return_value=("continue", "needs one more check", False),
        ):
            mgr.evaluate_after_turn("Ran focused tests and found one missing status field.")

        report = mgr.status_report()
        assert "Goal (active, 1/20 turns)" in report
        assert "Last verdict: continue" in report
        assert "Last reason: needs one more check" in report
        assert "Last progress checkpoint:" in report
        assert "Ran focused tests" in report
        assert "Hermes will continue after the current turn" in report

    def test_status_report_for_blocked_goal_points_to_resume_or_clear(self, hermes_home):
        from hermes_cli import goals
        from hermes_cli.goals import GoalManager

        mgr = GoalManager(session_id="status-report-blocked-sid")
        mgr.set("ship a reliable goal loop")
        with patch.object(
            goals,
            "judge_goal",
            return_value=("continue", "blocked: missing approval", False),
        ):
            mgr.evaluate_after_turn("Cannot continue without approval.")

        report = mgr.status_report()
        assert "Goal (blocked" in report
        assert "blocked: missing approval" in report
        assert "use /goal resume" in report
        assert "use /goal clear" in report

    def test_kickoff_prompt_includes_engineering_contract(self, hermes_home):
        """Goal kickoff should prime the agent with scope/evidence/stop
        conditions instead of sending only the raw objective."""
        from hermes_cli.goals import GoalManager

        mgr = GoalManager(session_id="kickoff-sid")
        mgr.set("make Jenny safer for long engineering work")
        prompt = mgr.kickoff_prompt()
        assert prompt is not None
        assert "Engineering goal kickoff" in prompt
        assert "make Jenny safer for long engineering work" in prompt
        assert "in-scope work and explicit non-goals" in prompt
        assert "protected surfaces" in prompt
        assert "evidence required to prove completion" in prompt
        assert "rollback or stop conditions" in prompt
        assert "completed items, evidence gathered, open risks or approvals" in prompt
        assert "runtime checks, or artifact paths" in prompt


# ──────────────────────────────────────────────────────────────────────
# Smoke: CommandDef is wired
# ──────────────────────────────────────────────────────────────────────


def test_goal_command_in_registry():
    from hermes_cli.commands import resolve_command

    cmd = resolve_command("goal")
    assert cmd is not None
    assert cmd.name == "goal"


def test_goal_command_dispatches_in_cli_registry_helpers():
    """goal shows up in autocomplete / help categories alongside other Session cmds."""
    from hermes_cli.commands import COMMANDS, COMMANDS_BY_CATEGORY

    assert "/goal" in COMMANDS
    session_cmds = COMMANDS_BY_CATEGORY.get("Session", {})
    assert "/goal" in session_cmds


# ──────────────────────────────────────────────────────────────────────
# Auto-pause on consecutive judge parse failures
# ──────────────────────────────────────────────────────────────────────


class TestJudgeParseFailureAutoPause:
    """Regression: weak judge models (e.g. deepseek-v4-flash) that return
    empty strings or non-JSON prose must auto-pause the loop after N turns
    instead of burning the whole turn budget."""

    def test_parse_response_flags_empty_as_parse_failure(self):
        from hermes_cli.goals import _parse_judge_response

        done, reason, parse_failed = _parse_judge_response("")
        assert done is False
        assert parse_failed is True
        assert "empty" in reason.lower()

    def test_parse_response_flags_non_json_as_parse_failure(self):
        from hermes_cli.goals import _parse_judge_response

        done, reason, parse_failed = _parse_judge_response(
            "Let me analyze whether the goal is fully satisfied based on the agent's response..."
        )
        assert done is False
        assert parse_failed is True
        assert "not json" in reason.lower()

    def test_parse_response_clean_json_is_not_parse_failure(self):
        from hermes_cli.goals import _parse_judge_response

        done, _, parse_failed = _parse_judge_response(
            '{"done": false, "reason": "more work"}'
        )
        assert done is False
        assert parse_failed is False

    def test_api_error_does_not_count_as_parse_failure(self):
        """Transient network/API errors must not trip the auto-pause guard."""
        from hermes_cli import goals

        fake_client = MagicMock()
        fake_client.chat.completions.create.side_effect = RuntimeError("connection reset")
        with patch(
            "agent.auxiliary_client.get_text_auxiliary_client",
            return_value=(fake_client, "judge-model"),
        ):
            verdict, _, parse_failed = goals.judge_goal("goal", "response")
        assert verdict == "continue"
        assert parse_failed is False

    def test_empty_judge_reply_flagged_as_parse_failure(self):
        """End-to-end: judge returns empty content → parse_failed=True."""
        from hermes_cli import goals

        fake_client = MagicMock()
        fake_client.chat.completions.create.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content=""))]
        )
        with patch(
            "agent.auxiliary_client.get_text_auxiliary_client",
            return_value=(fake_client, "judge-model"),
        ):
            verdict, _, parse_failed = goals.judge_goal("goal", "response")
        assert verdict == "continue"
        assert parse_failed is True

    def test_auto_pause_after_three_consecutive_parse_failures(self, hermes_home):
        """N=3 consecutive parse failures → auto-pause with config pointer."""
        from hermes_cli import goals
        from hermes_cli.goals import GoalManager, DEFAULT_MAX_CONSECUTIVE_PARSE_FAILURES

        assert DEFAULT_MAX_CONSECUTIVE_PARSE_FAILURES == 3
        mgr = GoalManager(session_id="parse-fail-sid-1", default_max_turns=20)
        mgr.set("do a thing")

        with patch.object(
            goals, "judge_goal", return_value=("continue", "judge returned empty response", True)
        ):
            d1 = mgr.evaluate_after_turn("step 1")
            assert d1["should_continue"] is True
            assert mgr.state.consecutive_parse_failures == 1

            d2 = mgr.evaluate_after_turn("step 2")
            assert d2["should_continue"] is True
            assert mgr.state.consecutive_parse_failures == 2

            d3 = mgr.evaluate_after_turn("step 3")
            assert d3["should_continue"] is False
            assert d3["status"] == "paused"
            assert mgr.state.consecutive_parse_failures == 3
            # Message points at the config surface so the user can fix it.
            assert "auxiliary" in d3["message"]
            assert "goal_judge" in d3["message"]
            assert "config.yaml" in d3["message"]

    def test_parse_failure_counter_resets_on_good_reply(self, hermes_home):
        """A single good judge reply resets the counter — transient flakes don't pause."""
        from hermes_cli import goals
        from hermes_cli.goals import GoalManager

        mgr = GoalManager(session_id="parse-fail-sid-2", default_max_turns=20)
        mgr.set("another goal")

        # Two parse failures…
        with patch.object(
            goals, "judge_goal", return_value=("continue", "not json", True)
        ):
            mgr.evaluate_after_turn("step 1")
            mgr.evaluate_after_turn("step 2")
            assert mgr.state.consecutive_parse_failures == 2

        # …then one clean reply resets the counter.
        with patch.object(
            goals, "judge_goal", return_value=("continue", "making progress", False)
        ):
            d = mgr.evaluate_after_turn("step 3")
            assert d["should_continue"] is True
            assert mgr.state.consecutive_parse_failures == 0

    def test_parse_failure_counter_not_incremented_by_api_errors(self, hermes_home):
        """API/transport errors must NOT count toward the auto-pause threshold."""
        from hermes_cli import goals
        from hermes_cli.goals import GoalManager

        mgr = GoalManager(session_id="parse-fail-sid-3", default_max_turns=20)
        mgr.set("goal")

        with patch.object(
            goals, "judge_goal", return_value=("continue", "judge error: RuntimeError", False)
        ):
            for _ in range(5):
                d = mgr.evaluate_after_turn("still going")
                assert d["should_continue"] is True
            assert mgr.state.consecutive_parse_failures == 0
            assert mgr.state.status == "active"

    def test_consecutive_parse_failures_persists_across_goalmanager_reloads(
        self, hermes_home
    ):
        """The counter must be durable so cross-session resumes see it."""
        from hermes_cli import goals
        from hermes_cli.goals import GoalManager, load_goal

        mgr = GoalManager(session_id="parse-fail-sid-4", default_max_turns=20)
        mgr.set("persistent goal")

        with patch.object(
            goals, "judge_goal", return_value=("continue", "empty", True)
        ):
            mgr.evaluate_after_turn("r")
            mgr.evaluate_after_turn("r")

        reloaded = load_goal("parse-fail-sid-4")
        assert reloaded is not None
        assert reloaded.consecutive_parse_failures == 2


# ──────────────────────────────────────────────────────────────────────
# /subgoal — user-added criteria
# ──────────────────────────────────────────────────────────────────────


class TestGoalStateSubgoalsBackcompat:
    def test_old_state_meta_row_loads_without_subgoals(self):
        """A goal serialized BEFORE the subgoals field existed must
        round-trip with an empty list, not crash."""
        from hermes_cli.goals import GoalState

        legacy = json.dumps({
            "goal": "do a thing",
            "status": "active",
            "turns_used": 2,
            "max_turns": 20,
            "created_at": 1.0,
            "last_turn_at": 2.0,
            "consecutive_parse_failures": 0,
        })
        state = GoalState.from_json(legacy)
        assert state.goal == "do a thing"
        assert state.subgoals == []
        assert state.last_progress_excerpt is None

    def test_subgoals_round_trip(self):
        from hermes_cli.goals import GoalState
        state = GoalState(goal="g", subgoals=["a", "b", "c"])
        rt = GoalState.from_json(state.to_json())
        assert rt.subgoals == ["a", "b", "c"]

    def test_progress_excerpt_round_trip(self):
        from hermes_cli.goals import GoalState
        state = GoalState(goal="g", last_progress_excerpt="ran tests and found one failure")
        rt = GoalState.from_json(state.to_json())
        assert rt.last_progress_excerpt == "ran tests and found one failure"


class TestGoalManagerSubgoals:
    def test_add_subgoal(self, hermes_home):
        from hermes_cli.goals import GoalManager
        mgr = GoalManager(session_id="sub-add")
        mgr.set("main goal")
        text = mgr.add_subgoal("  use bullet points  ")
        assert text == "use bullet points"
        assert mgr.state.subgoals == ["use bullet points"]

    def test_add_subgoal_requires_active_goal(self, hermes_home):
        import pytest
        from hermes_cli.goals import GoalManager
        mgr = GoalManager(session_id="sub-noactive")
        with pytest.raises(RuntimeError):
            mgr.add_subgoal("oops")

    def test_add_empty_subgoal_rejected(self, hermes_home):
        import pytest
        from hermes_cli.goals import GoalManager
        mgr = GoalManager(session_id="sub-empty")
        mgr.set("g")
        with pytest.raises(ValueError):
            mgr.add_subgoal("   ")

    def test_remove_subgoal(self, hermes_home):
        from hermes_cli.goals import GoalManager
        mgr = GoalManager(session_id="sub-remove")
        mgr.set("g")
        mgr.add_subgoal("first")
        mgr.add_subgoal("second")
        mgr.add_subgoal("third")
        removed = mgr.remove_subgoal(2)
        assert removed == "second"
        assert mgr.state.subgoals == ["first", "third"]

    def test_remove_subgoal_out_of_range(self, hermes_home):
        import pytest
        from hermes_cli.goals import GoalManager
        mgr = GoalManager(session_id="sub-oob")
        mgr.set("g")
        mgr.add_subgoal("only")
        with pytest.raises(IndexError):
            mgr.remove_subgoal(5)
        with pytest.raises(IndexError):
            mgr.remove_subgoal(0)

    def test_clear_subgoals(self, hermes_home):
        from hermes_cli.goals import GoalManager
        mgr = GoalManager(session_id="sub-clear")
        mgr.set("g")
        mgr.add_subgoal("a")
        mgr.add_subgoal("b")
        prev = mgr.clear_subgoals()
        assert prev == 2
        assert mgr.state.subgoals == []

    def test_subgoals_persist_across_reloads(self, hermes_home):
        """Subgoals stored in SessionDB survive a fresh GoalManager."""
        from hermes_cli.goals import GoalManager
        mgr = GoalManager(session_id="sub-persist")
        mgr.set("g")
        mgr.add_subgoal("first")
        mgr.add_subgoal("second")

        mgr2 = GoalManager(session_id="sub-persist")
        assert mgr2.state.subgoals == ["first", "second"]


class TestContinuationPromptWithSubgoals:
    def test_empty_subgoals_uses_original_template(self, hermes_home):
        from hermes_cli.goals import GoalManager
        mgr = GoalManager(session_id="cp-empty")
        mgr.set("ship the feature")
        prompt = mgr.next_continuation_prompt()
        assert prompt is not None
        assert "ship the feature" in prompt
        assert "Additional criteria" not in prompt

    def test_with_subgoals_includes_them(self, hermes_home):
        from hermes_cli.goals import GoalManager
        mgr = GoalManager(session_id="cp-with")
        mgr.set("ship the feature")
        mgr.add_subgoal("write tests")
        mgr.add_subgoal("update docs")
        prompt = mgr.next_continuation_prompt()
        assert prompt is not None
        assert "ship the feature" in prompt
        assert "Additional user criteria" in prompt
        assert "1. write tests" in prompt
        assert "2. update docs" in prompt


class TestJudgeGoalWithSubgoals:
    def test_judge_system_prompt_requires_concrete_evidence(self):
        from hermes_cli.goals import JUDGE_SYSTEM_PROMPT

        assert "concrete evidence" in JUDGE_SYSTEM_PROMPT
        assert "changed files" in JUDGE_SYSTEM_PROMPT
        assert "command/test output" in JUDGE_SYSTEM_PROMPT
        assert "PR state" in JUDGE_SYSTEM_PROMPT
        assert "Do not accept generic phrases" in JUDGE_SYSTEM_PROMPT
        assert "it works" in JUDGE_SYSTEM_PROMPT

    def test_judge_uses_subgoals_template_when_provided(self, hermes_home):
        """judge_goal switches templates when subgoals is non-empty.

        We don't actually call the model — we patch the aux client to
        capture the prompt that would be sent.
        """
        from unittest.mock import patch
        from hermes_cli import goals

        captured = {}

        class _FakeMsg:
            content = '{"done": true, "reason": "all done"}'
        class _FakeChoice:
            message = _FakeMsg()
        class _FakeResp:
            choices = [_FakeChoice()]
        class _FakeClient:
            class chat:
                class completions:
                    @staticmethod
                    def create(**kwargs):
                        captured.update(kwargs)
                        return _FakeResp()

        with patch.object(goals, "get_text_auxiliary_client",
                          return_value=(_FakeClient, "fake-model"), create=True), \
             patch.object(goals, "get_auxiliary_extra_body",
                          return_value=None, create=True), \
             patch("agent.auxiliary_client.get_text_auxiliary_client",
                   return_value=(_FakeClient, "fake-model")), \
             patch("agent.auxiliary_client.get_auxiliary_extra_body",
                   return_value=None):
            verdict, reason, parse_failed = goals.judge_goal(
                "ship the feature",
                "ok shipped",
                subgoals=["write tests", "update docs"],
            )

        # The aux client was called with a prompt that includes the subgoals.
        sent_messages = captured.get("messages") or []
        user_msg = next((m["content"] for m in sent_messages if m["role"] == "user"), "")
        assert "Additional criteria" in user_msg
        assert "1. write tests" in user_msg
        assert "2. update docs" in user_msg
        assert "concrete evidence" in user_msg
        assert "specific evidence" in user_msg
        assert "every additional criterion" in user_msg
        assert verdict == "done"

    def test_judge_uses_original_template_when_no_subgoals(self, hermes_home):
        from unittest.mock import patch
        from hermes_cli import goals

        captured = {}

        class _FakeMsg:
            content = '{"done": true, "reason": "ok"}'
        class _FakeChoice:
            message = _FakeMsg()
        class _FakeResp:
            choices = [_FakeChoice()]
        class _FakeClient:
            class chat:
                class completions:
                    @staticmethod
                    def create(**kwargs):
                        captured.update(kwargs)
                        return _FakeResp()

        with patch("agent.auxiliary_client.get_text_auxiliary_client",
                   return_value=(_FakeClient, "fake-model")), \
             patch("agent.auxiliary_client.get_auxiliary_extra_body",
                   return_value=None):
            goals.judge_goal("ship it", "done", subgoals=None)

        sent_messages = captured.get("messages") or []
        user_msg = next((m["content"] for m in sent_messages if m["role"] == "user"), "")
        assert "Additional criteria" not in user_msg
        assert "ship it" in user_msg
        assert "concrete evidence" in user_msg
        assert "generic completion claims" in user_msg
        assert "files changed" in user_msg
        assert "command output" in user_msg
        assert "test results" in user_msg
        assert "return CONTINUE" in user_msg


class TestStatusLineSubgoalCount:
    def test_status_line_no_subgoals(self, hermes_home):
        from hermes_cli.goals import GoalManager
        mgr = GoalManager(session_id="sl-empty")
        mgr.set("ship it")
        line = mgr.status_line()
        assert "ship it" in line
        assert "subgoal" not in line.lower()

    def test_status_line_blocked(self, hermes_home):
        from hermes_cli.goals import GoalManager
        mgr = GoalManager(session_id="sl-blocked")
        mgr.set("ship it")
        mgr.state.status = "blocked"
        mgr.state.paused_reason = "blocked: waiting for approval"
        line = mgr.status_line()
        assert "blocked" in line
        assert "waiting for approval" in line

    def test_status_line_with_subgoals(self, hermes_home):
        from hermes_cli.goals import GoalManager
        mgr = GoalManager(session_id="sl-with")
        mgr.set("ship it")
        mgr.add_subgoal("a")
        mgr.add_subgoal("b")
        line = mgr.status_line()
        assert "2 subgoals" in line
