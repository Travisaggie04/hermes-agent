"""Manual Jenny-to-Codex work-packet handoff.

This module intentionally does not start workers, poll in the background, or
route model traffic. It gives Jenny a durable foreground queue for bounded
Codex work packets and keeps completion separate from Jenny's evidence review.
"""

from __future__ import annotations

import json
import re
import time
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from hermes_constants import get_hermes_home


CODEX_HANDOFF_SCHEMA_VERSION = 1
CODEX_HANDOFF_STORE_NAME = "codex_handoffs.json"
CODEX_HANDOFF_REQUIRED_REPORT_HEADINGS = (
    "changed files",
    "tests",
    "pr",
    "blockers",
    "evidence",
)
CODEX_HANDOFF_REQUIRED_RETURN_FIELDS = (
    "Changed files: files changed, or `none` for planning/review-only work",
    "Tests: commands run and results, or `not run` with reason",
    "PR: pull request link/number, or `none`",
    "Blockers: remaining blockers, approvals, or `none`",
    "Evidence: concise proof Jenny can review before reporting done",
)
CODEX_HANDOFF_DEFAULT_CONSTRAINTS = (
    "Manual/foreground only: this packet never starts a daemon, cron, timer, hidden worker, or gateway action.",
    "Laptop Codex execution is opportunistic: if unavailable, leave the packet queued or report waiting.",
    "Codex returns evidence; Jenny reviews evidence before telling Travis the work is done.",
    "Protected actions still require the shared Jenny OS ALLOW/ASK/DENY approval path.",
)


@dataclass
class CodexHandoffPacket:
    packet_id: str
    goal: str
    status: str = "queued"
    created_at: float = 0.0
    updated_at: float = 0.0
    session_id: str = ""
    source: str = "jenny"
    claimed_by: str = ""
    claimed_at: float = 0.0
    returned_at: float = 0.0
    reviewed_at: float = 0.0
    report: str = ""
    review: str = ""
    blocker: str = ""
    required_return_fields: list[str] = field(default_factory=lambda: list(CODEX_HANDOFF_REQUIRED_RETURN_FIELDS))
    constraints: list[str] = field(default_factory=lambda: list(CODEX_HANDOFF_DEFAULT_CONSTRAINTS))

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CodexHandoffPacket":
        return cls(
            packet_id=str(data.get("packet_id") or ""),
            goal=str(data.get("goal") or ""),
            status=str(data.get("status") or "queued"),
            created_at=float(data.get("created_at") or 0.0),
            updated_at=float(data.get("updated_at") or 0.0),
            session_id=str(data.get("session_id") or ""),
            source=str(data.get("source") or "jenny"),
            claimed_by=str(data.get("claimed_by") or ""),
            claimed_at=float(data.get("claimed_at") or 0.0),
            returned_at=float(data.get("returned_at") or 0.0),
            reviewed_at=float(data.get("reviewed_at") or 0.0),
            report=str(data.get("report") or ""),
            review=str(data.get("review") or ""),
            blocker=str(data.get("blocker") or ""),
            required_return_fields=[
                str(item).strip()
                for item in data.get("required_return_fields", CODEX_HANDOFF_REQUIRED_RETURN_FIELDS)
                if str(item).strip()
            ],
            constraints=[
                str(item).strip()
                for item in data.get("constraints", CODEX_HANDOFF_DEFAULT_CONSTRAINTS)
                if str(item).strip()
            ],
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _now() -> float:
    return time.time()


def _stamp(value: float) -> str:
    if not value:
        return "never"
    return datetime.fromtimestamp(value, tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


def _packet_id() -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    return f"codex-{stamp}-{uuid.uuid4().hex[:6]}"


def _truncate(value: str, limit: int = 160) -> str:
    text = " ".join(value.split())
    return text if len(text) <= limit else f"{text[:limit - 3]}..."


class CodexHandoffStore:
    def __init__(self, path: Path | None = None):
        self.path = path or (get_hermes_home() / CODEX_HANDOFF_STORE_NAME)

    def _load(self) -> list[CodexHandoffPacket]:
        if not self.path.exists():
            return []
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except Exception:
            return []
        rows = raw.get("packets") if isinstance(raw, dict) else raw
        if not isinstance(rows, list):
            return []
        packets = [CodexHandoffPacket.from_dict(row) for row in rows if isinstance(row, dict)]
        return [packet for packet in packets if packet.packet_id and packet.goal]

    def _save(self, packets: list[CodexHandoffPacket]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "schema_version": CODEX_HANDOFF_SCHEMA_VERSION,
            "packets": [packet.to_dict() for packet in packets],
        }
        tmp = self.path.with_suffix(f"{self.path.suffix}.tmp")
        tmp.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        tmp.replace(self.path)

    def list(self) -> list[CodexHandoffPacket]:
        return sorted(self._load(), key=lambda packet: (packet.created_at, packet.packet_id))

    def get(self, packet_id: str) -> CodexHandoffPacket:
        packet_id = packet_id.strip()
        for packet in self._load():
            if packet.packet_id == packet_id:
                return packet
        raise ValueError(f"unknown Codex handoff packet: {packet_id}")

    def _replace(self, packet: CodexHandoffPacket) -> CodexHandoffPacket:
        packets = self._load()
        for index, existing in enumerate(packets):
            if existing.packet_id == packet.packet_id:
                packets[index] = packet
                self._save(packets)
                return packet
        raise ValueError(f"unknown Codex handoff packet: {packet.packet_id}")

    def create(self, goal: str, *, session_id: str = "", source: str = "jenny") -> CodexHandoffPacket:
        goal = goal.strip()
        if not goal:
            raise ValueError("usage: /codex-handoff create <bounded goal>")
        now = _now()
        packet = CodexHandoffPacket(
            packet_id=_packet_id(),
            goal=goal,
            created_at=now,
            updated_at=now,
            session_id=session_id.strip(),
            source=source.strip() or "jenny",
        )
        packets = self._load()
        packets.append(packet)
        self._save(packets)
        return packet

    def claim(self, packet_id: str = "", *, claimed_by: str = "laptop-codex") -> CodexHandoffPacket:
        packets = self._load()
        packet: CodexHandoffPacket | None = None
        if packet_id.strip():
            packet = next((item for item in packets if item.packet_id == packet_id.strip()), None)
        else:
            packet = next((item for item in packets if item.status == "queued"), None)
        if packet is None:
            raise ValueError(f"unknown or unavailable Codex handoff packet: {packet_id or 'oldest queued'}")
        if packet.status not in {"queued", "revision_requested"}:
            raise ValueError(f"packet {packet.packet_id} is {packet.status}, not queued")
        now = _now()
        packet.status = "claimed"
        packet.claimed_by = claimed_by.strip() or "laptop-codex"
        packet.claimed_at = now
        packet.updated_at = now
        self._replace(packet)
        return packet

    def return_report(self, packet_id: str, report: str) -> CodexHandoffPacket:
        packet = self.get(packet_id)
        if packet.status not in {"claimed", "revision_requested"}:
            raise ValueError(f"packet {packet.packet_id} is {packet.status}, not claimed")
        _validate_return_report(report)
        now = _now()
        packet.status = "returned"
        packet.report = report.strip()
        packet.returned_at = now
        packet.updated_at = now
        packet.review = ""
        self._replace(packet)
        return packet

    def review(self, packet_id: str, decision: str, notes: str) -> CodexHandoffPacket:
        packet = self.get(packet_id)
        if packet.status != "returned":
            raise ValueError(f"packet {packet.packet_id} is {packet.status}, not returned for review")
        cleaned_decision = decision.strip().lower()
        if cleaned_decision not in {"approve", "changes"}:
            raise ValueError("usage: /codex-handoff review <id> <approve|changes> <notes>")
        notes = notes.strip()
        if not notes:
            raise ValueError("review notes are required")
        now = _now()
        packet.status = "reviewed" if cleaned_decision == "approve" else "revision_requested"
        packet.review = notes
        packet.reviewed_at = now
        packet.updated_at = now
        self._replace(packet)
        return packet

    def block(self, packet_id: str, reason: str) -> CodexHandoffPacket:
        packet = self.get(packet_id)
        reason = reason.strip()
        if not reason:
            raise ValueError("usage: /codex-handoff block <id> <reason>")
        now = _now()
        packet.status = "blocked"
        packet.blocker = reason
        packet.updated_at = now
        self._replace(packet)
        return packet


def _validate_return_report(report: str) -> None:
    text = report.strip()
    if not text:
        raise ValueError("return report is required")
    lower = text.lower()
    missing = [
        heading
        for heading in CODEX_HANDOFF_REQUIRED_REPORT_HEADINGS
        if not re.search(rf"(?<![\w-]){re.escape(heading)}\s*:", lower)
    ]
    if missing:
        raise ValueError(
            "Codex return report is missing required heading(s): "
            + ", ".join(missing)
            + ". Include Changed files, Tests, PR, Blockers, and Evidence."
        )


def render_packet_summary(packet: CodexHandoffPacket) -> str:
    return (
        f"{packet.packet_id} [{packet.status}] "
        f"{_truncate(packet.goal, 110)} "
        f"(created {_stamp(packet.created_at)}, updated {_stamp(packet.updated_at)})"
    )


def render_packet_detail(packet: CodexHandoffPacket) -> str:
    lines = [
        f"Codex handoff packet: {packet.packet_id}",
        f"Status: {packet.status}",
        f"Goal: {packet.goal}",
        f"Session: {packet.session_id or 'none'}",
        f"Created: {_stamp(packet.created_at)}",
        f"Updated: {_stamp(packet.updated_at)}",
        "",
        "Constraints:",
        *[f"- {item}" for item in packet.constraints],
        "",
        "Codex must return:",
        *[f"- {item}" for item in packet.required_return_fields],
    ]
    if packet.claimed_by:
        lines.extend(["", f"Claimed by: {packet.claimed_by} at {_stamp(packet.claimed_at)}"])
    if packet.report:
        lines.extend(["", "Returned report:", packet.report])
    if packet.review:
        lines.extend(["", "Jenny review:", packet.review])
    if packet.blocker:
        lines.extend(["", "Blocker:", packet.blocker])
    return "\n".join(lines)


def render_claim_packet(packet: CodexHandoffPacket) -> str:
    return "\n".join(
        [
            "Codex foreground work packet",
            f"Packet ID: {packet.packet_id}",
            f"Goal: {packet.goal}",
            "",
            "Rules:",
            *[f"- {item}" for item in packet.constraints],
            "",
            "Return format:",
            *[f"- {item}" for item in packet.required_return_fields],
            "",
            "When complete, return evidence with:",
            f"/codex-handoff return {packet.packet_id} Changed files: ... Tests: ... PR: ... Blockers: ... Evidence: ...",
            "",
            "If blocked, use:",
            f"/codex-handoff block {packet.packet_id} <reason>",
        ]
    )


def handle_codex_handoff_command(arg: str, *, session_id: str = "", store: CodexHandoffStore | None = None) -> str:
    store = store or CodexHandoffStore()
    raw = (arg or "").strip()
    if not raw or raw in {"status", "list", "ls"}:
        packets = store.list()
        if not packets:
            return "No Codex handoff packets. Use /codex-handoff create <bounded goal>."
        return "Codex handoff packets:\n" + "\n".join(render_packet_summary(packet) for packet in packets)

    command, _, rest = raw.partition(" ")
    command = command.lower()
    rest = rest.strip()

    if command == "create":
        packet = store.create(rest, session_id=session_id, source="desktop-native-chat" if session_id else "jenny")
        return (
            f"Queued Codex handoff {packet.packet_id}.\n"
            "It will not run automatically. Start Codex on the laptop foreground harness and claim it with:\n"
            f"/codex-handoff claim {packet.packet_id}"
        )

    if command == "show":
        return render_packet_detail(store.get(rest))

    if command == "claim":
        packet = store.claim(rest)
        return render_claim_packet(packet)

    if command == "return":
        packet_id, _, report = rest.partition(" ")
        packet = store.return_report(packet_id, report)
        return (
            f"Returned Codex handoff {packet.packet_id} for Jenny review.\n"
            "Jenny must review this evidence before reporting the task done."
        )

    if command == "review":
        packet_id, _, remainder = rest.partition(" ")
        decision, _, notes = remainder.partition(" ")
        packet = store.review(packet_id, decision, notes)
        if packet.status == "reviewed":
            return f"Reviewed Codex handoff {packet.packet_id}. Jenny may report done with the returned evidence."
        return f"Requested Codex revisions for {packet.packet_id}. Packet is queued for another foreground claim."

    if command == "block":
        packet_id, _, reason = rest.partition(" ")
        packet = store.block(packet_id, reason)
        return f"Blocked Codex handoff {packet.packet_id}: {packet.blocker}"

    raise ValueError(
        "usage: /codex-handoff [list|create <goal>|show <id>|claim [id]|return <id> <report>|review <id> <approve|changes> <notes>|block <id> <reason>]"
    )


__all__ = [
    "CODEX_HANDOFF_REQUIRED_REPORT_HEADINGS",
    "CODEX_HANDOFF_REQUIRED_RETURN_FIELDS",
    "CODEX_HANDOFF_STORE_NAME",
    "CodexHandoffPacket",
    "CodexHandoffStore",
    "handle_codex_handoff_command",
    "render_claim_packet",
    "render_packet_detail",
    "render_packet_summary",
]
