from __future__ import annotations

from pathlib import Path

import pytest

from hermes_cli.codex_handoff import (
    CODEX_HANDOFF_STORE_NAME,
    CodexHandoffStore,
    handle_codex_handoff_command,
    render_claim_packet,
)
from hermes_cli.commands import COMMANDS, SUBCOMMANDS, resolve_command


def _report() -> str:
    return "\n".join(
        [
            "Changed files: hermes_cli/codex_handoff.py",
            "Tests: tests/hermes_cli/test_codex_handoff.py passed",
            "PR: none",
            "Blockers: none",
            "Evidence: lifecycle exercised from queue through Jenny review",
        ]
    )


def _one_line_report() -> str:
    return "Changed files: hermes_cli/codex_handoff.py Tests: pytest passed PR: none Blockers: none Evidence: one-line command format accepted"


def test_codex_handoff_lifecycle_requires_jenny_review(tmp_path: Path) -> None:
    store = CodexHandoffStore(tmp_path / CODEX_HANDOFF_STORE_NAME)

    packet = store.create("Fix the desktop tests and open a PR.", session_id="session-1")
    assert packet.status == "queued"
    assert packet.session_id == "session-1"
    assert "never starts a daemon" in " ".join(packet.constraints)

    claimed = store.claim(packet.packet_id, claimed_by="laptop-codex")
    assert claimed.status == "claimed"
    assert "Return format:" in render_claim_packet(claimed)
    assert f"/codex-handoff return {packet.packet_id}" in render_claim_packet(claimed)

    returned = store.return_report(packet.packet_id, _report())
    assert returned.status == "returned"
    assert "Changed files:" in returned.report

    reviewed = store.review(packet.packet_id, "approve", "Evidence is specific enough to report done.")
    assert reviewed.status == "reviewed"
    assert reviewed.review == "Evidence is specific enough to report done."


def test_codex_handoff_return_report_must_include_required_evidence(tmp_path: Path) -> None:
    store = CodexHandoffStore(tmp_path / CODEX_HANDOFF_STORE_NAME)
    packet = store.create("Fix a risky issue.")
    store.claim(packet.packet_id)

    with pytest.raises(ValueError, match="missing required heading"):
        store.return_report(packet.packet_id, "Changed files: one file")


def test_codex_handoff_accepts_one_line_return_command_format(tmp_path: Path) -> None:
    store = CodexHandoffStore(tmp_path / CODEX_HANDOFF_STORE_NAME)
    packet = store.create("Return evidence from the foreground Codex harness.")
    store.claim(packet.packet_id)

    returned = store.return_report(packet.packet_id, _one_line_report())

    assert returned.status == "returned"
    assert "one-line command format accepted" in returned.report


def test_codex_handoff_review_can_request_changes_and_requeue(tmp_path: Path) -> None:
    store = CodexHandoffStore(tmp_path / CODEX_HANDOFF_STORE_NAME)
    packet = store.create("Update validation docs.")
    store.claim(packet.packet_id)
    store.return_report(packet.packet_id, _report())

    reviewed = store.review(packet.packet_id, "changes", "Tests were not broad enough.")
    assert reviewed.status == "revision_requested"

    claimed_again = store.claim(packet.packet_id)
    assert claimed_again.status == "claimed"


def test_codex_handoff_command_handler_uses_hermes_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    monkeypatch.setenv("HERMES_HOME", str(tmp_path / ".hermes"))

    created = handle_codex_handoff_command("create Re-run phone viewport validation.", session_id="session-1")
    assert "Queued Codex handoff codex-" in created
    packet_id = created.split("Queued Codex handoff ", 1)[1].split(".", 1)[0]

    listed = handle_codex_handoff_command("list")
    assert packet_id in listed
    assert "[queued]" in listed

    claimed = handle_codex_handoff_command(f"claim {packet_id}")
    assert "Codex foreground work packet" in claimed
    assert "Manual/foreground only" in claimed

    returned = handle_codex_handoff_command(f"return {packet_id} {_report()}")
    assert "for Jenny review" in returned

    reviewed = handle_codex_handoff_command(f"review {packet_id} approve Evidence reviewed.")
    assert "Jenny may report done" in reviewed


def test_codex_handoff_is_registered_for_desktop_and_tui_dispatch() -> None:
    command = resolve_command("codex")

    assert command is not None
    assert command.name == "codex-handoff"
    assert "/codex-handoff" in COMMANDS
    assert SUBCOMMANDS["/codex-handoff"] == ["list", "create", "show", "claim", "return", "review", "block"]
