from __future__ import annotations

import json
from pathlib import Path

from mission_control.github_bridge_mailbox import (
    GITHUB_BRIDGE_MARKER,
    append_response,
    github_bridge_latest,
    github_bridge_status,
    list_pending_messages,
    main,
    notify_jenny_now,
    parse_bridge_comments,
    post_github_message,
    post_github_response,
    poll_comments,
    response_comment_body,
    watch_github_issue,
)
from mission_control.records import GitHubBridgeMailboxStatusRecord, GitHubBridgeMessageRecord, JsonlRecordStore


def _comment(comment_id: int, body: str, created_at: str = "2026-06-13T00:00:00Z") -> dict:
    return {"id": comment_id, "body": body, "created_at": created_at, "user": {"login": "codex"}}


def _body(**overrides: str) -> str:
    payload = {
        "request_id": "req-1",
        "project_id": "project-hermes-mission-control",
        "from_agent": "codex",
        "to_agent": "jenny",
        "status": "queued",
        "message": "Review this bounded lane.",
        "created_at": "2026-06-13T00:00:00Z",
    }
    payload.update(overrides)
    return f"{GITHUB_BRIDGE_MARKER}\n```json\n{json.dumps(payload)}\n```"


def test_parse_bridge_comments_uses_bounded_message_format():
    messages = parse_bridge_comments([_comment(101, _body())], repo="Travisaggie04/hermes-agent", issue_number=79)

    assert len(messages) == 1
    assert messages[0].request_id == "req-1"
    assert messages[0].project_id == "project-hermes-mission-control"
    assert messages[0].from_agent == "codex"
    assert messages[0].to_agent == "jenny"
    assert messages[0].status == "queued"
    assert messages[0].message == "Review this bounded lane."
    assert messages[0].metadata["github_comment_id"] == 101


def test_poll_comments_appends_new_messages_and_status_without_duplicates(tmp_path: Path):
    records = tmp_path / "records.jsonl"

    result1 = poll_comments(
        [_comment(101, _body(request_id="req-1")), _comment(102, _body(request_id="req-2"))],
        repo="Travisaggie04/hermes-agent",
        issue_number=79,
        path=records,
    )
    result2 = poll_comments(
        [_comment(101, _body(request_id="req-1")), _comment(102, _body(request_id="req-2"))],
        repo="Travisaggie04/hermes-agent",
        issue_number=79,
        path=records,
    )

    store = JsonlRecordStore(records)
    messages = store.read_all(GitHubBridgeMessageRecord)
    statuses = store.read_all(GitHubBridgeMailboxStatusRecord)
    assert result1["new_message_count"] == 2
    assert result2["new_message_count"] == 0
    assert [message.request_id for message in messages] == ["req-1", "req-2"]
    assert [status.status for status in statuses] == ["poll_completed", "poll_completed"]
    assert statuses[-1].metadata["manual_start_only"] is True
    assert statuses[-1].metadata["dispatch_enabled"] is False
    assert statuses[-1].metadata["worker_enabled"] is False


def test_poll_comments_dedupes_new_request_comments_by_request_id(tmp_path: Path):
    records = tmp_path / "records.jsonl"

    poll_comments([_comment(101, _body(request_id="req-1", message="First."))], repo="Travisaggie04/hermes-agent", issue_number=79, path=records)
    result = poll_comments([_comment(102, _body(request_id="req-1", message="Duplicate."))], repo="Travisaggie04/hermes-agent", issue_number=79, path=records)

    messages = JsonlRecordStore(records).read_all(GitHubBridgeMessageRecord)
    assert result["new_message_count"] == 0
    assert [message.message for message in messages] == ["First."]


def test_pending_projection_excludes_replied_requests(tmp_path: Path):
    records = tmp_path / "records.jsonl"
    poll_comments(
        [_comment(101, _body(request_id="req-open")), _comment(102, _body(request_id="req-done"))],
        repo="Travisaggie04/hermes-agent",
        issue_number=79,
        path=records,
    )
    append_response(
        request_id="req-done",
        project_id="project-hermes-mission-control",
        message="Done.",
        repo="Travisaggie04/hermes-agent",
        issue_number=79,
        github_comment_id=201,
        path=records,
    )

    pending = list_pending_messages(path=records)
    status = github_bridge_status(path=records)

    assert [item.record.request_id for item in pending] == ["req-open"]
    assert status["pending_count"] == 1
    assert status["last_response_request_id"] == "req-done"
    assert status["manual_start_only"] is True
    assert status["dispatch_enabled"] is False
    assert status["session_send_enabled"] is False
    assert status["worker_enabled"] is False
    assert status["timer_enabled"] is False


def test_respond_dedupes_by_request_id_and_appends_skipped_duplicate_status(tmp_path: Path):
    records = tmp_path / "records.jsonl"
    poll_comments([_comment(101, _body(request_id="req-1"))], repo="Travisaggie04/hermes-agent", issue_number=79, path=records)

    first = append_response(
        request_id="req-1",
        project_id="project-hermes-mission-control",
        message="First reply.",
        repo="Travisaggie04/hermes-agent",
        issue_number=79,
        github_comment_id=201,
        path=records,
    )
    duplicate = append_response(
        request_id="req-1",
        project_id="project-hermes-mission-control",
        message="Duplicate reply.",
        repo="Travisaggie04/hermes-agent",
        issue_number=79,
        github_comment_id=202,
        path=records,
    )

    store = JsonlRecordStore(records)
    messages = store.read_all(GitHubBridgeMessageRecord)
    statuses = store.read_all(GitHubBridgeMailboxStatusRecord)
    assert first[1] is not None
    assert duplicate[1] is None
    assert [message.status for message in messages] == ["queued", "replied"]
    assert [status.status for status in statuses] == ["poll_completed", "response_appended", "skipped_duplicate"]


def test_duplicate_non_dry_run_response_does_not_post_to_github(tmp_path: Path, monkeypatch):
    records = tmp_path / "records.jsonl"
    poll_comments([_comment(101, _body(request_id="req-duplicate"))], repo="Travisaggie04/hermes-agent", issue_number=79, path=records)
    append_response(
        request_id="req-duplicate",
        project_id="project-hermes-mission-control",
        message="First reply.",
        repo="Travisaggie04/hermes-agent",
        issue_number=79,
        github_comment_id=201,
        path=records,
    )
    gh_calls: list[list[str]] = []

    def fake_run_gh_api(args: list[str]):
        gh_calls.append(args)
        return {"id": 202}

    monkeypatch.setattr("mission_control.github_bridge_mailbox._run_gh_api", fake_run_gh_api)

    duplicate = post_github_response(
        request_id="req-duplicate",
        project_id="project-hermes-mission-control",
        message="Duplicate reply.",
        repo="Travisaggie04/hermes-agent",
        issue_number=79,
        path=records,
    )

    store = JsonlRecordStore(records)
    messages = store.read_all(GitHubBridgeMessageRecord)
    statuses = store.read_all(GitHubBridgeMailboxStatusRecord)
    assert gh_calls == []
    assert duplicate["response"] is None
    assert duplicate["status"]["status"] == "skipped_duplicate"
    assert [message.status for message in messages] == ["queued", "replied"]
    assert [status.status for status in statuses] == ["poll_completed", "response_appended", "skipped_duplicate"]


def test_send_posts_one_bridge_message_and_records_status(tmp_path: Path, monkeypatch):
    records = tmp_path / "records.jsonl"
    gh_calls: list[list[str]] = []

    def fake_run_gh_api(args: list[str]):
        gh_calls.append(args)
        return {"id": 501}

    monkeypatch.setattr("mission_control.github_bridge_mailbox._run_gh_api", fake_run_gh_api)

    payload = post_github_message(
        request_id="req-send",
        project_id="project-hermes-mission-control",
        message="Bounded request from Codex.",
        path=records,
    )

    messages = JsonlRecordStore(records).read_all(GitHubBridgeMessageRecord)
    statuses = JsonlRecordStore(records).read_all(GitHubBridgeMailboxStatusRecord)
    assert len(gh_calls) == 1
    assert gh_calls[0][0] == "repos/Travisaggie04/hermes-agent/issues/79/comments"
    assert "hermes-github-bridge" in gh_calls[0][-1]
    assert payload["message"]["request_id"] == "req-send"
    assert messages[0].github_comment_id == "501"
    assert messages[0].from_agent == "codex"
    assert messages[0].to_agent == "jenny"
    assert statuses[-1].status == "message_posted"
    assert statuses[-1].metadata["daemon_enabled"] is False


def test_duplicate_send_does_not_post_second_github_comment(tmp_path: Path, monkeypatch):
    records = tmp_path / "records.jsonl"
    gh_calls: list[list[str]] = []

    def fake_run_gh_api(args: list[str]):
        gh_calls.append(args)
        return {"id": 501 + len(gh_calls)}

    monkeypatch.setattr("mission_control.github_bridge_mailbox._run_gh_api", fake_run_gh_api)

    first = post_github_message(
        request_id="req-duplicate-send",
        project_id="project-hermes-mission-control",
        message="First request.",
        path=records,
    )
    duplicate = post_github_message(
        request_id="req-duplicate-send",
        project_id="project-hermes-mission-control",
        message="Duplicate request.",
        path=records,
    )

    messages = JsonlRecordStore(records).read_all(GitHubBridgeMessageRecord)
    statuses = JsonlRecordStore(records).read_all(GitHubBridgeMailboxStatusRecord)
    assert first["message"]["message"] == "First request."
    assert duplicate["message"] is None
    assert duplicate["status"]["status"] == "skipped_duplicate"
    assert len(gh_calls) == 1
    assert [message.message for message in messages] == ["First request."]
    assert [status.status for status in statuses] == ["message_posted", "skipped_duplicate"]


def test_notify_jenny_now_posts_message_and_runs_one_ssh_poll(tmp_path: Path, monkeypatch):
    records = tmp_path / "records.jsonl"
    gh_calls: list[list[str]] = []
    ssh_calls: list[list[str]] = []

    def fake_run_gh_api(args: list[str]):
        gh_calls.append(args)
        return {"id": 801}

    def fake_run_ssh(args: list[str]):
        ssh_calls.append(args)
        return json.dumps({"stored": True, "new_message_count": 1, "pending_count": 1})

    monkeypatch.setattr("mission_control.github_bridge_mailbox._run_gh_api", fake_run_gh_api)
    monkeypatch.setattr("mission_control.github_bridge_mailbox._run_ssh", fake_run_ssh)

    payload = notify_jenny_now(
        request_id="req-notify",
        project_id="project-hermes-mission-control",
        message="Review this bounded request.",
        ssh_known_hosts=tmp_path / "known_hosts",
        path=records,
    )

    messages = JsonlRecordStore(records).read_all(GitHubBridgeMessageRecord)
    assert len(gh_calls) == 1
    assert len(ssh_calls) == 1
    assert messages[0].request_id == "req-notify"
    assert payload["message_result"]["message"]["github_comment_id"] == "801"
    assert payload["remote_poll_result"]["remote_poll"]["new_message_count"] == 1
    assert ssh_calls[0][0] == "ssh"
    assert "BatchMode=yes" in ssh_calls[0]
    assert any(item.startswith("UserKnownHostsFile=") for item in ssh_calls[0])
    assert not any("StrictHostKeyChecking=no" in item for item in ssh_calls[0])
    assert ssh_calls[0][-2] == "jenny@100.115.125.111"
    assert "mission_control.github_bridge_mailbox poll" in ssh_calls[0][-1]


def test_notify_jenny_now_duplicate_skips_github_but_still_polls(tmp_path: Path, monkeypatch):
    records = tmp_path / "records.jsonl"
    gh_calls: list[list[str]] = []
    ssh_calls: list[list[str]] = []

    def fake_run_gh_api(args: list[str]):
        gh_calls.append(args)
        return {"id": 901}

    def fake_run_ssh(args: list[str]):
        ssh_calls.append(args)
        return json.dumps({"stored": True, "new_message_count": 0, "pending_count": 1})

    monkeypatch.setattr("mission_control.github_bridge_mailbox._run_gh_api", fake_run_gh_api)
    monkeypatch.setattr("mission_control.github_bridge_mailbox._run_ssh", fake_run_ssh)

    first = notify_jenny_now(
        request_id="req-notify-duplicate",
        project_id="project-hermes-mission-control",
        message="First notify request.",
        path=records,
    )
    duplicate = notify_jenny_now(
        request_id="req-notify-duplicate",
        project_id="project-hermes-mission-control",
        message="Duplicate notify request.",
        path=records,
    )

    messages = JsonlRecordStore(records).read_all(GitHubBridgeMessageRecord)
    statuses = JsonlRecordStore(records).read_all(GitHubBridgeMailboxStatusRecord)
    assert first["message_result"]["message"]["message"] == "First notify request."
    assert duplicate["message_result"]["message"] is None
    assert duplicate["message_result"]["status"]["status"] == "skipped_duplicate"
    assert len(gh_calls) == 1
    assert len(ssh_calls) == 2
    assert [message.message for message in messages] == ["First notify request."]
    assert [status.status for status in statuses] == ["message_posted", "skipped_duplicate"]


def test_response_dedupe_is_scoped_to_repo_and_issue_number(tmp_path: Path):
    records = tmp_path / "records.jsonl"
    poll_comments([_comment(101, _body(request_id="req-shared"))], repo="Travisaggie04/hermes-agent", issue_number=79, path=records)
    poll_comments([_comment(102, _body(request_id="req-shared", message="Other issue."))], repo="Travisaggie04/hermes-agent", issue_number=80, path=records)
    append_response(
        request_id="req-shared",
        project_id="project-hermes-mission-control",
        message="Reply in issue 80 only.",
        repo="Travisaggie04/hermes-agent",
        issue_number=80,
        github_comment_id=301,
        path=records,
    )

    pending_79 = list_pending_messages(path=records, repo="Travisaggie04/hermes-agent", issue_number=79)
    pending_80 = list_pending_messages(path=records, repo="Travisaggie04/hermes-agent", issue_number=80)

    assert [item.record.request_id for item in pending_79] == ["req-shared"]
    assert pending_80 == []


def test_latest_summary_uses_default_mailbox_and_lists_pending(tmp_path: Path):
    records = tmp_path / "records.jsonl"
    poll_comments(
        [_comment(101, _body(request_id="req-latest", message="Latest should show this."))],
        repo="Travisaggie04/hermes-agent",
        issue_number=79,
        path=records,
    )

    latest = github_bridge_latest(path=records)

    assert latest["repo"] == "Travisaggie04/hermes-agent"
    assert latest["issue_number"] == 79
    assert latest["pending_count"] == 1
    assert latest["pending_messages"][0]["record"]["request_id"] == "req-latest"
    assert latest["manual_start_only"] is True
    assert latest["worker_enabled"] is False


def test_response_comment_body_preserves_small_bridge_format():
    body = response_comment_body(
        request_id="req-1",
        project_id="project-hermes-mission-control",
        from_agent="jenny",
        to_agent="codex",
        message="Safe to proceed.",
    )

    messages = parse_bridge_comments([_comment(202, body, created_at="2026-06-13T00:10:00Z")], repo="Travisaggie04/hermes-agent", issue_number=79)
    assert messages[0].status == "replied"
    assert messages[0].request_id == "req-1"
    assert messages[0].message == "Safe to proceed."


def test_watch_github_issue_foreground_loop_prints_new_pending_and_stops(tmp_path: Path):
    records = tmp_path / "records.jsonl"
    batches = [
        [],
        [_comment(101, _body(request_id="req-watch", message="Watch found me."))],
        [_comment(101, _body(request_id="req-watch", message="Watch found me."))],
    ]
    printed: list[str] = []
    slept: list[float] = []

    def fetch_comments() -> list[dict]:
        return batches.pop(0)

    result = watch_github_issue(
        repo="Travisaggie04/hermes-agent",
        issue_number=79,
        interval_seconds=2,
        to_agent="jenny",
        max_iterations=3,
        path=records,
        fetch_comments=fetch_comments,
        sleep_fn=lambda seconds: slept.append(seconds),
        print_fn=printed.append,
    )

    store = JsonlRecordStore(records)
    statuses = store.read_all(GitHubBridgeMailboxStatusRecord)
    messages = store.read_all(GitHubBridgeMessageRecord)
    assert result["iterations"] == 3
    assert [status.status for status in statuses] == [
        "watch_started",
        "watch_poll_completed",
        "watch_poll_completed",
        "watch_poll_completed",
        "watch_stopped",
    ]
    assert [message.request_id for message in messages] == ["req-watch"]
    assert any("req-watch" in line and "Watch found me." in line for line in printed)
    assert slept == [2, 2]
    assert statuses[0].mode == "watch_foreground"
    assert statuses[-1].metadata["worker_enabled"] is False


def test_watch_main_supports_bounded_offline_comments_json_dir(tmp_path: Path, capsys):
    records = tmp_path / "records.jsonl"
    comments_dir = tmp_path / "comments"
    comments_dir.mkdir()
    (comments_dir / "001.json").write_text(json.dumps([]), encoding="utf-8")
    (comments_dir / "002.json").write_text(
        json.dumps([_comment(201, _body(request_id="req-cli-watch", message="CLI watch saw this."))]),
        encoding="utf-8",
    )

    exit_code = main(
        [
            "--records",
            str(records),
            "watch",
            "--repo",
            "Travisaggie04/hermes-agent",
            "--issue",
            "79",
            "--interval-seconds",
            "2",
            "--to-agent",
            "jenny",
            "--max-iterations",
            "2",
            "--comments-json-dir",
            str(comments_dir),
        ]
    )

    output = capsys.readouterr().out
    statuses = JsonlRecordStore(records).read_all(GitHubBridgeMailboxStatusRecord)
    assert exit_code == 0
    assert "req-cli-watch" in output
    assert [status.status for status in statuses] == ["watch_started", "watch_poll_completed", "watch_poll_completed", "watch_stopped"]
    assert statuses[-1].mode == "watch_foreground"


def test_send_main_defaults_to_pr79_mailbox(tmp_path: Path, monkeypatch, capsys):
    records = tmp_path / "records.jsonl"
    gh_calls: list[list[str]] = []

    def fake_run_gh_api(args: list[str]):
        gh_calls.append(args)
        return {"id": 701}

    monkeypatch.setattr("mission_control.github_bridge_mailbox._run_gh_api", fake_run_gh_api)

    exit_code = main(
        [
            "--records",
            str(records),
            "send",
            "--request-id",
            "req-cli-send",
            "--project-id",
            "project-hermes-mission-control",
            "--message",
            "CLI send uses defaults.",
        ]
    )

    output = json.loads(capsys.readouterr().out)
    messages = JsonlRecordStore(records).read_all(GitHubBridgeMessageRecord)
    assert exit_code == 0
    assert gh_calls[0][0] == "repos/Travisaggie04/hermes-agent/issues/79/comments"
    assert output["message"]["request_id"] == "req-cli-send"
    assert messages[0].github_repo == "Travisaggie04/hermes-agent"
    assert messages[0].github_issue_number == 79


def test_notify_jenny_now_main_uses_defaults_and_known_hosts(tmp_path: Path, monkeypatch, capsys):
    records = tmp_path / "records.jsonl"
    known_hosts = tmp_path / "known_hosts"
    known_hosts.write_text("100.115.125.111 ssh-ed25519 test\n", encoding="utf-8")
    gh_calls: list[list[str]] = []
    ssh_calls: list[list[str]] = []

    def fake_run_gh_api(args: list[str]):
        gh_calls.append(args)
        return {"id": 902}

    def fake_run_ssh(args: list[str]):
        ssh_calls.append(args)
        return json.dumps({"stored": True, "new_message_count": 1, "pending_count": 1})

    monkeypatch.setattr("mission_control.github_bridge_mailbox._run_gh_api", fake_run_gh_api)
    monkeypatch.setattr("mission_control.github_bridge_mailbox._run_ssh", fake_run_ssh)

    exit_code = main(
        [
            "--records",
            str(records),
            "notify-jenny-now",
            "--request-id",
            "req-cli-notify",
            "--project-id",
            "project-hermes-mission-control",
            "--message",
            "CLI notify uses defaults.",
            "--ssh-known-hosts",
            str(known_hosts),
        ]
    )

    output = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert gh_calls[0][0] == "repos/Travisaggie04/hermes-agent/issues/79/comments"
    assert ssh_calls[0][-2] == "jenny@100.115.125.111"
    assert "hermes-runtime-github-bridge-mailbox-944411a" in ssh_calls[0][-1]
    assert output["message_result"]["message"]["request_id"] == "req-cli-notify"
    assert output["remote_poll_result"]["remote_poll"]["stored"] is True
