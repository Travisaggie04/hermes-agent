"""Pure value objects for inert Mission Control governance records."""

from __future__ import annotations

from dataclasses import dataclass, field
import re
from typing import Any, ClassVar


def _tuple(value: Any) -> tuple[Any, ...]:
    if value is None:
        return ()
    return tuple(value)


def _dict(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    return dict(value)


def _nonnegative_int(value: Any) -> int:
    if isinstance(value, bool):
        return 0
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return 0
    return max(0, parsed)


def _inert_execution_metadata(value: Any) -> dict[str, Any]:
    metadata = _dict(value)
    metadata.update(
        {
            "would_execute": False,
            "would_dispatch": False,
            "would_session_send": False,
            "execution_enabled": False,
            "dispatch_enabled": False,
            "dispatch_in_gateway": False,
            "dispatch_state": False,
            "execution_ready": False,
            "live_operations_enabled": False,
            "send_to_jenny_enabled": False,
            "session_send_enabled": False,
            "worker_enabled": False,
            "workers_enabled": False,
            "worker_dispatch_enabled": False,
            "timer_enabled": False,
            "daemon_enabled": False,
            "waha_enabled": False,
            "social_enabled": False,
            "payment_enabled": False,
            "queue_mutation_enabled": False,
            "model_routing_enabled": False,
            "trusted_for_execution": False,
            "inert_context_only": True,
        }
    )
    return metadata


_WORKER_NODE_PRESENCE_STATUSES = {"online", "offline"}


def _normalize_worker_node_presence_status(value: Any) -> str:
    text = str(value or "").strip().lower()
    return text if text in _WORKER_NODE_PRESENCE_STATUSES else "offline"


def _normalize_worker_node_smoke_status(*, smoke_status: Any, presence_status: Any, metadata: dict[str, Any]) -> str:
    explicit = str(smoke_status or "").strip()
    if explicit:
        return explicit
    metadata_smoke_status = str(metadata.get("smoke_status") or "").strip()
    if metadata_smoke_status:
        return metadata_smoke_status
    presence_text = str(presence_status or "").strip().lower()
    if presence_text and presence_text not in _WORKER_NODE_PRESENCE_STATUSES:
        return presence_text
    return ""


def _required(data: dict[str, Any], field_name: str) -> Any:
    try:
        return data[field_name]
    except KeyError as exc:
        raise TypeError(f"missing required field: {field_name}") from exc


_PACKET_HASH_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
_FULL_SHA_RE = re.compile(r"^[0-9a-f]{40}$")
_PACKET_VERSION = "pr_merge_packet_v1"
_ALLOWED_MERGE_METHODS = {"merge", "squash", "rebase"}
_MAX_REPO_CHARS = 120
_MAX_PR_NUMBER_CHARS = 20
_MAX_BASE_BRANCH_CHARS = 200
_MAX_OPERATOR_ID_CHARS = 80
_APPROVED_PR_MERGE_SCOPE = "merge_pr_only"


def _clean_text(value: Any, max_chars: int) -> str:
    text = str(value or "").strip()
    if not text or len(text) > max_chars:
        return ""
    return text


def _normalize_packet_repo(value: Any) -> str:
    text = _clean_text(value, _MAX_REPO_CHARS + 32)
    if text.startswith("https://github.com/"):
        text = text.removeprefix("https://github.com/")
    elif text.startswith("http://github.com/"):
        text = text.removeprefix("http://github.com/")
    if text.endswith(".git"):
        text = text.removesuffix(".git")
    text = text.strip("/").lower()
    if len(text) > _MAX_REPO_CHARS or text.count("/") != 1 or any(not part for part in text.split("/")):
        return ""
    return text


def _normalize_packet_pr_number(value: Any) -> str:
    text = _clean_text(value, _MAX_PR_NUMBER_CHARS + 1)
    if text.startswith("#"):
        text = text[1:]
    if not text.isdecimal():
        return ""
    normalized = str(int(text))
    if len(normalized) > _MAX_PR_NUMBER_CHARS or int(normalized) <= 0:
        return ""
    return normalized


def _normalize_packet_sha(value: Any) -> str:
    text = str(value or "").strip().lower()
    return text if _FULL_SHA_RE.fullmatch(text) else ""


def _normalize_packet_merge_method(value: Any) -> str:
    text = str(value or "").strip().lower()
    return text if text in _ALLOWED_MERGE_METHODS else ""


def _sanitize_pr_merge_packet_identity(action_class: str, value: Any) -> dict[str, str]:
    if action_class != "pr_merge" or not isinstance(value, dict):
        return {}
    candidate = {
        "repo": _normalize_packet_repo(value.get("repo")),
        "pr_number": _normalize_packet_pr_number(value.get("pr_number")),
        "base_branch": _clean_text(value.get("base_branch"), _MAX_BASE_BRANCH_CHARS),
        "head_commit": _normalize_packet_sha(value.get("head_commit")),
        "expected_base_head": _normalize_packet_sha(value.get("expected_base_head")),
        "merge_method": _normalize_packet_merge_method(value.get("merge_method")),
    }
    return {field: text for field, text in candidate.items() if text}


def _sanitize_pr_merge_packet_hash(action_class: str, value: Any) -> str:
    if action_class != "pr_merge":
        return ""
    text = str(value or "").strip()
    return text if _PACKET_HASH_RE.fullmatch(text) else ""


def _sanitize_pr_merge_packet_version(action_class: str, value: Any) -> str:
    if action_class != "pr_merge":
        return ""
    text = str(value or "").strip() or _PACKET_VERSION
    return text if text == _PACKET_VERSION else ""


def _sanitize_pr_merge_action_class(value: Any) -> str:
    text = str(value or "").strip()
    return text if text == "pr_merge" else ""


def _sanitize_pr_merge_approved_scope(value: Any) -> str:
    text = str(value or "").strip()
    return text if text == _APPROVED_PR_MERGE_SCOPE else ""


def _sanitize_operator_id(value: Any) -> str:
    return _clean_text(value, _MAX_OPERATOR_ID_CHARS)


@dataclass(frozen=True)
class ArtifactRef:
    ref_id: str
    kind: str
    location: str
    description: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    record_type: ClassVar[str] = "ArtifactRef"

    def __post_init__(self) -> None:
        object.__setattr__(self, "metadata", _dict(self.metadata))

    def to_dict(self) -> dict[str, Any]:
        return {
            "ref_id": self.ref_id,
            "kind": self.kind,
            "location": self.location,
            "description": self.description,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ArtifactRef:
        return cls(
            ref_id=_required(data, "ref_id"),
            kind=_required(data, "kind"),
            location=_required(data, "location"),
            description=data.get("description", ""),
            metadata=data.get("metadata") or {},
        )


@dataclass(frozen=True)
class GoalContract:
    goal_id: str
    statement: str
    success_criteria: tuple[str, ...] = ()
    constraints: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)

    record_type: ClassVar[str] = "GoalContract"

    def __post_init__(self) -> None:
        object.__setattr__(self, "success_criteria", _tuple(self.success_criteria))
        object.__setattr__(self, "constraints", _tuple(self.constraints))
        object.__setattr__(self, "metadata", _dict(self.metadata))

    def to_dict(self) -> dict[str, Any]:
        return {
            "goal_id": self.goal_id,
            "statement": self.statement,
            "success_criteria": list(self.success_criteria),
            "constraints": list(self.constraints),
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> GoalContract:
        return cls(
            goal_id=_required(data, "goal_id"),
            statement=_required(data, "statement"),
            success_criteria=data.get("success_criteria") or (),
            constraints=data.get("constraints") or (),
            metadata=data.get("metadata") or {},
        )


@dataclass(frozen=True)
class ProjectRecord:
    project_id: str
    name: str
    status: str = ""
    current_goal: str = ""
    next_recommended_lane: str = ""
    mistakes_guards: str = ""
    source_of_truth: str = ""
    profile: str = ""
    created_at: str = ""
    updated_at: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    record_type: ClassVar[str] = "ProjectRecord"

    def __post_init__(self) -> None:
        object.__setattr__(self, "metadata", _dict(self.metadata))

    def to_dict(self) -> dict[str, Any]:
        return {
            "project_id": self.project_id,
            "name": self.name,
            "status": self.status,
            "current_goal": self.current_goal,
            "next_recommended_lane": self.next_recommended_lane,
            "mistakes_guards": self.mistakes_guards,
            "source_of_truth": self.source_of_truth,
            "profile": self.profile,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ProjectRecord:
        return cls(
            project_id=_required(data, "project_id"),
            name=_required(data, "name"),
            status=data.get("status", ""),
            current_goal=data.get("current_goal", ""),
            next_recommended_lane=data.get("next_recommended_lane", ""),
            mistakes_guards=data.get("mistakes_guards", ""),
            source_of_truth=data.get("source_of_truth", ""),
            profile=data.get("profile", ""),
            created_at=data.get("created_at", ""),
            updated_at=data.get("updated_at", ""),
            metadata=data.get("metadata") or {},
        )


@dataclass(frozen=True)
class RoomContractRecord:
    room_id: str
    project_id: str
    title: str
    status: str = "active"
    brief_path: str = ""
    facts_path: str = ""
    specs_path: str = ""
    decisions_path: str = ""
    reports_path: str = ""
    mailbox_path: str = ""
    journal_path: str = ""
    owner: str = ""
    allowed_actions: tuple[str, ...] = ()
    forbidden_actions: tuple[str, ...] = ()
    stop_conditions: tuple[str, ...] = ()
    created_at: str = ""
    updated_at: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    record_type: ClassVar[str] = "RoomContractRecord"

    def __post_init__(self) -> None:
        object.__setattr__(self, "allowed_actions", tuple(str(item) for item in _tuple(self.allowed_actions)))
        object.__setattr__(self, "forbidden_actions", tuple(str(item) for item in _tuple(self.forbidden_actions)))
        object.__setattr__(self, "stop_conditions", tuple(str(item) for item in _tuple(self.stop_conditions)))
        object.__setattr__(self, "metadata", _dict(self.metadata))

    def to_dict(self) -> dict[str, Any]:
        return {
            "room_id": self.room_id,
            "project_id": self.project_id,
            "title": self.title,
            "status": self.status,
            "brief_path": self.brief_path,
            "facts_path": self.facts_path,
            "specs_path": self.specs_path,
            "decisions_path": self.decisions_path,
            "reports_path": self.reports_path,
            "mailbox_path": self.mailbox_path,
            "journal_path": self.journal_path,
            "owner": self.owner,
            "allowed_actions": list(self.allowed_actions),
            "forbidden_actions": list(self.forbidden_actions),
            "stop_conditions": list(self.stop_conditions),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RoomContractRecord:
        return cls(
            room_id=_required(data, "room_id"),
            project_id=_required(data, "project_id"),
            title=_required(data, "title"),
            status=data.get("status", "active"),
            brief_path=data.get("brief_path", ""),
            facts_path=data.get("facts_path", ""),
            specs_path=data.get("specs_path", ""),
            decisions_path=data.get("decisions_path", ""),
            reports_path=data.get("reports_path", ""),
            mailbox_path=data.get("mailbox_path", ""),
            journal_path=data.get("journal_path", ""),
            owner=data.get("owner", ""),
            allowed_actions=data.get("allowed_actions") or (),
            forbidden_actions=data.get("forbidden_actions") or (),
            stop_conditions=data.get("stop_conditions") or (),
            created_at=data.get("created_at", ""),
            updated_at=data.get("updated_at", ""),
            metadata=data.get("metadata") or {},
        )


@dataclass(frozen=True)
class RoomJournalEventRecord:
    event_id: str
    room_id: str
    project_id: str
    event_type: str
    summary: str
    event_time: str = ""
    actor: str = ""
    source: str = ""
    artifact_refs: tuple[str, ...] = ()
    parent_event_ids: tuple[str, ...] = ()
    append_only: bool = True
    trusted_for_execution: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)

    record_type: ClassVar[str] = "RoomJournalEventRecord"

    def __post_init__(self) -> None:
        object.__setattr__(self, "artifact_refs", tuple(str(item) for item in _tuple(self.artifact_refs)))
        object.__setattr__(self, "parent_event_ids", tuple(str(item) for item in _tuple(self.parent_event_ids)))
        object.__setattr__(self, "append_only", True)
        object.__setattr__(self, "trusted_for_execution", False)
        object.__setattr__(self, "metadata", _dict(self.metadata))

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "room_id": self.room_id,
            "project_id": self.project_id,
            "event_type": self.event_type,
            "summary": self.summary,
            "event_time": self.event_time,
            "actor": self.actor,
            "source": self.source,
            "artifact_refs": list(self.artifact_refs),
            "parent_event_ids": list(self.parent_event_ids),
            "append_only": True,
            "trusted_for_execution": False,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RoomJournalEventRecord:
        return cls(
            event_id=_required(data, "event_id"),
            room_id=_required(data, "room_id"),
            project_id=_required(data, "project_id"),
            event_type=_required(data, "event_type"),
            summary=_required(data, "summary"),
            event_time=data.get("event_time", ""),
            actor=data.get("actor", ""),
            source=data.get("source", ""),
            artifact_refs=data.get("artifact_refs") or (),
            parent_event_ids=data.get("parent_event_ids") or (),
            append_only=True,
            trusted_for_execution=False,
            metadata=data.get("metadata") or {},
        )


@dataclass(frozen=True)
class ProjectBriefRecord:
    brief_id: str
    project_id: str
    name: str
    outcome: str = ""
    audience: str = ""
    source_of_truth: str = ""
    success_criteria: tuple[str, ...] = ()
    constraints: tuple[str, ...] = ()
    forbidden_actions: tuple[str, ...] = ()
    approval_rules: tuple[str, ...] = ()
    context_pack_path: str = ""
    status: str = "draft"
    created_at: str = ""
    updated_at: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    record_type: ClassVar[str] = "ProjectBriefRecord"

    def __post_init__(self) -> None:
        object.__setattr__(self, "success_criteria", tuple(str(item) for item in _tuple(self.success_criteria)))
        object.__setattr__(self, "constraints", tuple(str(item) for item in _tuple(self.constraints)))
        object.__setattr__(self, "forbidden_actions", tuple(str(item) for item in _tuple(self.forbidden_actions)))
        object.__setattr__(self, "approval_rules", tuple(str(item) for item in _tuple(self.approval_rules)))
        object.__setattr__(self, "metadata", _dict(self.metadata))

    def to_dict(self) -> dict[str, Any]:
        return {
            "brief_id": self.brief_id,
            "project_id": self.project_id,
            "name": self.name,
            "outcome": self.outcome,
            "audience": self.audience,
            "source_of_truth": self.source_of_truth,
            "success_criteria": list(self.success_criteria),
            "constraints": list(self.constraints),
            "forbidden_actions": list(self.forbidden_actions),
            "approval_rules": list(self.approval_rules),
            "context_pack_path": self.context_pack_path,
            "status": self.status,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ProjectBriefRecord:
        return cls(
            brief_id=_required(data, "brief_id"),
            project_id=_required(data, "project_id"),
            name=_required(data, "name"),
            outcome=data.get("outcome", ""),
            audience=data.get("audience", ""),
            source_of_truth=data.get("source_of_truth", ""),
            success_criteria=data.get("success_criteria") or (),
            constraints=data.get("constraints") or (),
            forbidden_actions=data.get("forbidden_actions") or (),
            approval_rules=data.get("approval_rules") or (),
            context_pack_path=data.get("context_pack_path", ""),
            status=data.get("status", "draft"),
            created_at=data.get("created_at", ""),
            updated_at=data.get("updated_at", ""),
            metadata=data.get("metadata") or {},
        )


@dataclass(frozen=True)
class ChallengeReviewRecord:
    review_id: str
    project_id: str
    request_summary: str
    decision_state: str = "needs_spec_first"
    challenge_categories: tuple[str, ...] = ()
    blocking_verdicts: tuple[str, ...] = ()
    recommended_path: str = ""
    concerns: tuple[str, ...] = ()
    questions: tuple[str, ...] = ()
    required_spec_updates: tuple[str, ...] = ()
    required_approvals: tuple[str, ...] = ()
    suggested_lane_title: str = ""
    status: str = "draft"
    created_at: str = ""
    reviewed_by: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    record_type: ClassVar[str] = "ChallengeReviewRecord"

    def __post_init__(self) -> None:
        object.__setattr__(self, "challenge_categories", tuple(str(item) for item in _tuple(self.challenge_categories)))
        object.__setattr__(self, "blocking_verdicts", tuple(str(item) for item in _tuple(self.blocking_verdicts)))
        object.__setattr__(self, "concerns", tuple(str(item) for item in _tuple(self.concerns)))
        object.__setattr__(self, "questions", tuple(str(item) for item in _tuple(self.questions)))
        object.__setattr__(self, "required_spec_updates", tuple(str(item) for item in _tuple(self.required_spec_updates)))
        object.__setattr__(self, "required_approvals", tuple(str(item) for item in _tuple(self.required_approvals)))
        object.__setattr__(self, "metadata", _dict(self.metadata))

    def to_dict(self) -> dict[str, Any]:
        return {
            "review_id": self.review_id,
            "project_id": self.project_id,
            "request_summary": self.request_summary,
            "decision_state": self.decision_state,
            "challenge_categories": list(self.challenge_categories),
            "blocking_verdicts": list(self.blocking_verdicts),
            "recommended_path": self.recommended_path,
            "concerns": list(self.concerns),
            "questions": list(self.questions),
            "required_spec_updates": list(self.required_spec_updates),
            "required_approvals": list(self.required_approvals),
            "suggested_lane_title": self.suggested_lane_title,
            "status": self.status,
            "created_at": self.created_at,
            "reviewed_by": self.reviewed_by,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ChallengeReviewRecord:
        return cls(
            review_id=_required(data, "review_id"),
            project_id=_required(data, "project_id"),
            request_summary=_required(data, "request_summary"),
            decision_state=data.get("decision_state", "needs_spec_first"),
            challenge_categories=data.get("challenge_categories") or (),
            blocking_verdicts=data.get("blocking_verdicts") or (),
            recommended_path=data.get("recommended_path", ""),
            concerns=data.get("concerns") or (),
            questions=data.get("questions") or (),
            required_spec_updates=data.get("required_spec_updates") or (),
            required_approvals=data.get("required_approvals") or (),
            suggested_lane_title=data.get("suggested_lane_title", ""),
            status=data.get("status", "draft"),
            created_at=data.get("created_at", ""),
            reviewed_by=data.get("reviewed_by", ""),
            metadata=data.get("metadata") or {},
        )


@dataclass(frozen=True)
class LaneRequestRecord:
    lane_request_id: str
    project_id: str
    title: str
    mode: str = "read-only/manual-copy"
    objective: str = ""
    allowed_actions: tuple[str, ...] = ()
    forbidden_actions: tuple[str, ...] = ()
    stop_conditions: tuple[str, ...] = ()
    expected_report_format: tuple[str, ...] = ()
    draft_prompt: str = ""
    status: str = "draft"
    created_at: str = ""
    updated_at: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    record_type: ClassVar[str] = "LaneRequestRecord"

    def __post_init__(self) -> None:
        object.__setattr__(self, "allowed_actions", tuple(str(item) for item in _tuple(self.allowed_actions)))
        object.__setattr__(self, "forbidden_actions", tuple(str(item) for item in _tuple(self.forbidden_actions)))
        object.__setattr__(self, "stop_conditions", tuple(str(item) for item in _tuple(self.stop_conditions)))
        object.__setattr__(self, "expected_report_format", tuple(str(item) for item in _tuple(self.expected_report_format)))
        object.__setattr__(self, "metadata", _dict(self.metadata))

    def to_dict(self) -> dict[str, Any]:
        return {
            "lane_request_id": self.lane_request_id,
            "project_id": self.project_id,
            "title": self.title,
            "mode": self.mode,
            "objective": self.objective,
            "allowed_actions": list(self.allowed_actions),
            "forbidden_actions": list(self.forbidden_actions),
            "stop_conditions": list(self.stop_conditions),
            "expected_report_format": list(self.expected_report_format),
            "draft_prompt": self.draft_prompt,
            "status": self.status,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> LaneRequestRecord:
        return cls(
            lane_request_id=_required(data, "lane_request_id"),
            project_id=_required(data, "project_id"),
            title=_required(data, "title"),
            mode=data.get("mode", "read-only/manual-copy"),
            objective=data.get("objective", ""),
            allowed_actions=data.get("allowed_actions") or (),
            forbidden_actions=data.get("forbidden_actions") or (),
            stop_conditions=data.get("stop_conditions") or (),
            expected_report_format=data.get("expected_report_format") or (),
            draft_prompt=data.get("draft_prompt", ""),
            status=data.get("status", "draft"),
            created_at=data.get("created_at", ""),
            updated_at=data.get("updated_at", ""),
            metadata=data.get("metadata") or {},
        )


@dataclass(frozen=True)
class JennyReportRecord:
    report_id: str
    project_id: str
    lane_request_id: str = ""
    summary: str = ""
    result: str = ""
    changed_files: tuple[str, ...] = ()
    tests: tuple[str, ...] = ()
    risks: tuple[str, ...] = ()
    next_recommended_lane: str = ""
    created_at: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    record_type: ClassVar[str] = "JennyReportRecord"

    def __post_init__(self) -> None:
        object.__setattr__(self, "changed_files", tuple(str(item) for item in _tuple(self.changed_files)))
        object.__setattr__(self, "tests", tuple(str(item) for item in _tuple(self.tests)))
        object.__setattr__(self, "risks", tuple(str(item) for item in _tuple(self.risks)))
        object.__setattr__(self, "metadata", _dict(self.metadata))

    def to_dict(self) -> dict[str, Any]:
        return {
            "report_id": self.report_id,
            "project_id": self.project_id,
            "lane_request_id": self.lane_request_id,
            "summary": self.summary,
            "result": self.result,
            "changed_files": list(self.changed_files),
            "tests": list(self.tests),
            "risks": list(self.risks),
            "next_recommended_lane": self.next_recommended_lane,
            "created_at": self.created_at,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> JennyReportRecord:
        return cls(
            report_id=_required(data, "report_id"),
            project_id=_required(data, "project_id"),
            lane_request_id=data.get("lane_request_id", ""),
            summary=_required(data, "summary"),
            result=data.get("result", ""),
            changed_files=data.get("changed_files") or (),
            tests=data.get("tests") or (),
            risks=data.get("risks") or (),
            next_recommended_lane=data.get("next_recommended_lane", ""),
            created_at=data.get("created_at", ""),
            metadata=data.get("metadata") or {},
        )


@dataclass(frozen=True)
class JennyBridgeMessageRequestRecord:
    request_id: str
    project_id: str
    message: str
    lane_request_id: str = ""
    sender: str = "travis"
    target_agent: str = "jenny"
    status: str = "queued"
    ack_key: str = ""
    created_at: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    record_type: ClassVar[str] = "JennyBridgeMessageRequestRecord"

    def __post_init__(self) -> None:
        object.__setattr__(self, "metadata", _dict(self.metadata))

    def to_dict(self) -> dict[str, Any]:
        return {
            "request_id": self.request_id,
            "project_id": self.project_id,
            "lane_request_id": self.lane_request_id,
            "sender": self.sender,
            "target_agent": self.target_agent,
            "message": self.message,
            "status": self.status,
            "ack_key": self.ack_key,
            "created_at": self.created_at,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> JennyBridgeMessageRequestRecord:
        return cls(
            request_id=_required(data, "request_id"),
            project_id=_required(data, "project_id"),
            lane_request_id=data.get("lane_request_id", ""),
            sender=data.get("sender", "travis"),
            target_agent=data.get("target_agent", "jenny"),
            message=_required(data, "message"),
            status=data.get("status", "queued"),
            ack_key=data.get("ack_key", ""),
            created_at=data.get("created_at", ""),
            metadata=data.get("metadata") or {},
        )


@dataclass(frozen=True)
class JennyBridgeMessageResponseRecord:
    response_id: str
    request_id: str
    project_id: str
    message: str
    lane_request_id: str = ""
    responder: str = "jenny"
    status: str = "received"
    created_at: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    record_type: ClassVar[str] = "JennyBridgeMessageResponseRecord"

    def __post_init__(self) -> None:
        object.__setattr__(self, "metadata", _dict(self.metadata))

    def to_dict(self) -> dict[str, Any]:
        return {
            "response_id": self.response_id,
            "request_id": self.request_id,
            "project_id": self.project_id,
            "lane_request_id": self.lane_request_id,
            "responder": self.responder,
            "message": self.message,
            "status": self.status,
            "created_at": self.created_at,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> JennyBridgeMessageResponseRecord:
        return cls(
            response_id=_required(data, "response_id"),
            request_id=_required(data, "request_id"),
            project_id=_required(data, "project_id"),
            lane_request_id=data.get("lane_request_id", ""),
            responder=data.get("responder", "jenny"),
            message=_required(data, "message"),
            status=data.get("status", "received"),
            created_at=data.get("created_at", ""),
            metadata=data.get("metadata") or {},
        )


@dataclass(frozen=True)
class JennyReplyReviewRecord:
    review_id: str
    project_id: str
    response_id: str
    decision: str
    request_id: str = ""
    reviewer: str = "travis"
    note: str = ""
    created_at: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    record_type: ClassVar[str] = "JennyReplyReviewRecord"

    def __post_init__(self) -> None:
        object.__setattr__(self, "metadata", _dict(self.metadata))

    def to_dict(self) -> dict[str, Any]:
        return {
            "review_id": self.review_id,
            "project_id": self.project_id,
            "response_id": self.response_id,
            "request_id": self.request_id,
            "decision": self.decision,
            "reviewer": self.reviewer,
            "note": self.note,
            "created_at": self.created_at,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> JennyReplyReviewRecord:
        return cls(
            review_id=_required(data, "review_id"),
            project_id=_required(data, "project_id"),
            response_id=_required(data, "response_id"),
            request_id=data.get("request_id", ""),
            decision=_required(data, "decision"),
            reviewer=data.get("reviewer", "travis"),
            note=data.get("note", ""),
            created_at=data.get("created_at", ""),
            metadata=data.get("metadata") or {},
        )


@dataclass(frozen=True)
class JennyBridgePollerStatusRecord:
    status_id: str
    poller_id: str = "manual-jenny-bridge-relay"
    mode: str = "manual"
    status: str = "idle"
    pending_count: int = 0
    handled_request_id: str = ""
    handled_response_id: str = ""
    last_error: str = ""
    runtime_path: str = ""
    head: str = ""
    operator: str = "manual"
    created_at: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    record_type: ClassVar[str] = "JennyBridgePollerStatusRecord"

    def __post_init__(self) -> None:
        object.__setattr__(self, "metadata", _dict(self.metadata))

    def to_dict(self) -> dict[str, Any]:
        return {
            "status_id": self.status_id,
            "poller_id": self.poller_id,
            "mode": self.mode,
            "status": self.status,
            "pending_count": self.pending_count,
            "handled_request_id": self.handled_request_id,
            "handled_response_id": self.handled_response_id,
            "last_error": self.last_error,
            "runtime_path": self.runtime_path,
            "head": self.head,
            "operator": self.operator,
            "created_at": self.created_at,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> JennyBridgePollerStatusRecord:
        return cls(
            status_id=_required(data, "status_id"),
            poller_id=data.get("poller_id", "manual-jenny-bridge-relay"),
            mode=data.get("mode", "manual"),
            status=data.get("status", "idle"),
            pending_count=int(data.get("pending_count", 0) or 0),
            handled_request_id=data.get("handled_request_id", ""),
            handled_response_id=data.get("handled_response_id", ""),
            last_error=data.get("last_error", ""),
            runtime_path=data.get("runtime_path", ""),
            head=data.get("head", ""),
            operator=data.get("operator", "manual"),
            created_at=data.get("created_at", ""),
            metadata=data.get("metadata") or {},
        )


@dataclass(frozen=True)
class GitHubBridgeMessageRecord:
    request_id: str
    project_id: str
    from_agent: str
    to_agent: str
    status: str
    message: str
    created_at: str = ""
    github_repo: str = ""
    github_issue_number: int = 0
    github_comment_id: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    record_type: ClassVar[str] = "GitHubBridgeMessageRecord"

    def __post_init__(self) -> None:
        object.__setattr__(self, "github_issue_number", int(self.github_issue_number or 0))
        object.__setattr__(self, "metadata", _dict(self.metadata))

    def to_dict(self) -> dict[str, Any]:
        return {
            "request_id": self.request_id,
            "project_id": self.project_id,
            "from_agent": self.from_agent,
            "to_agent": self.to_agent,
            "status": self.status,
            "message": self.message,
            "created_at": self.created_at,
            "github_repo": self.github_repo,
            "github_issue_number": self.github_issue_number,
            "github_comment_id": self.github_comment_id,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> GitHubBridgeMessageRecord:
        return cls(
            request_id=_required(data, "request_id"),
            project_id=_required(data, "project_id"),
            from_agent=_required(data, "from_agent"),
            to_agent=_required(data, "to_agent"),
            status=data.get("status", "queued"),
            message=_required(data, "message"),
            created_at=data.get("created_at", ""),
            github_repo=data.get("github_repo", ""),
            github_issue_number=data.get("github_issue_number", 0),
            github_comment_id=data.get("github_comment_id", ""),
            metadata=data.get("metadata") or {},
        )


@dataclass(frozen=True)
class GitHubBridgeMailboxStatusRecord:
    status_id: str
    bridge_id: str = "manual-github-issue-mailbox"
    repo: str = ""
    issue_number: int = 0
    mode: str = "manual"
    status: str = "idle"
    pending_count: int = 0
    new_message_count: int = 0
    handled_request_id: str = ""
    handled_response_id: str = ""
    last_error: str = ""
    runtime_path: str = ""
    head: str = ""
    operator: str = "manual"
    created_at: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    record_type: ClassVar[str] = "GitHubBridgeMailboxStatusRecord"

    def __post_init__(self) -> None:
        object.__setattr__(self, "issue_number", int(self.issue_number or 0))
        object.__setattr__(self, "pending_count", int(self.pending_count or 0))
        object.__setattr__(self, "new_message_count", int(self.new_message_count or 0))
        object.__setattr__(self, "metadata", _dict(self.metadata))

    def to_dict(self) -> dict[str, Any]:
        return {
            "status_id": self.status_id,
            "bridge_id": self.bridge_id,
            "repo": self.repo,
            "issue_number": self.issue_number,
            "mode": self.mode,
            "status": self.status,
            "pending_count": self.pending_count,
            "new_message_count": self.new_message_count,
            "handled_request_id": self.handled_request_id,
            "handled_response_id": self.handled_response_id,
            "last_error": self.last_error,
            "runtime_path": self.runtime_path,
            "head": self.head,
            "operator": self.operator,
            "created_at": self.created_at,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> GitHubBridgeMailboxStatusRecord:
        return cls(
            status_id=_required(data, "status_id"),
            bridge_id=data.get("bridge_id", "manual-github-issue-mailbox"),
            repo=data.get("repo", ""),
            issue_number=data.get("issue_number", 0),
            mode=data.get("mode", "manual"),
            status=data.get("status", "idle"),
            pending_count=data.get("pending_count", 0),
            new_message_count=data.get("new_message_count", 0),
            handled_request_id=data.get("handled_request_id", ""),
            handled_response_id=data.get("handled_response_id", ""),
            last_error=data.get("last_error", ""),
            runtime_path=data.get("runtime_path", ""),
            head=data.get("head", ""),
            operator=data.get("operator", "manual"),
            created_at=data.get("created_at", ""),
            metadata=data.get("metadata") or {},
        )


@dataclass(frozen=True)
class ApprovalRecord:
    approval_id: str
    project_id: str = ""
    session_id: str = ""
    lane_request_id: str = ""
    run_id: str = ""
    action_class: str = ""
    approval_scope: str = ""
    approved_actions: tuple[str, ...] = ()
    forbidden_actions: tuple[str, ...] = ()
    status: str = "proposed"
    approval_mode: str = "one_time"
    approved_by: str = ""
    approval_source: str = ""
    approval_text: str = ""
    created_at: str = ""
    approved_at: str = ""
    expires_at: str | None = None
    consumed_at: str = ""
    baseline_runtime_path: str = ""
    baseline_head: str = ""
    packet_hash: str = ""
    scope_fingerprint: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    record_type: ClassVar[str] = "ApprovalRecord"

    def __post_init__(self) -> None:
        object.__setattr__(self, "approved_actions", tuple(str(item) for item in _tuple(self.approved_actions)))
        object.__setattr__(self, "forbidden_actions", tuple(str(item) for item in _tuple(self.forbidden_actions)))
        object.__setattr__(self, "approval_mode", self.approval_mode or "one_time")
        object.__setattr__(self, "expires_at", str(self.expires_at).strip() if self.expires_at else None)
        object.__setattr__(self, "metadata", _inert_execution_metadata(self.metadata))

    def to_dict(self) -> dict[str, Any]:
        return {
            "approval_id": self.approval_id,
            "project_id": self.project_id,
            "session_id": self.session_id,
            "lane_request_id": self.lane_request_id,
            "run_id": self.run_id,
            "action_class": self.action_class,
            "approval_scope": self.approval_scope,
            "approved_actions": list(self.approved_actions),
            "forbidden_actions": list(self.forbidden_actions),
            "status": self.status,
            "approval_mode": self.approval_mode,
            "approved_by": self.approved_by,
            "approval_source": self.approval_source,
            "approval_text": self.approval_text,
            "created_at": self.created_at,
            "approved_at": self.approved_at,
            "expires_at": self.expires_at,
            "consumed_at": self.consumed_at,
            "baseline_runtime_path": self.baseline_runtime_path,
            "baseline_head": self.baseline_head,
            "packet_hash": self.packet_hash,
            "scope_fingerprint": self.scope_fingerprint,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ApprovalRecord:
        return cls(
            approval_id=_required(data, "approval_id"),
            project_id=data.get("project_id", ""),
            session_id=data.get("session_id", ""),
            lane_request_id=data.get("lane_request_id", ""),
            run_id=data.get("run_id", ""),
            action_class=data.get("action_class", ""),
            approval_scope=data.get("approval_scope", ""),
            approved_actions=data.get("approved_actions") or (),
            forbidden_actions=data.get("forbidden_actions") or (),
            status=data.get("status", "proposed"),
            approval_mode=data.get("approval_mode", "one_time"),
            approved_by=data.get("approved_by", ""),
            approval_source=data.get("approval_source", ""),
            approval_text=data.get("approval_text", ""),
            created_at=data.get("created_at", ""),
            approved_at=data.get("approved_at", ""),
            expires_at=data.get("expires_at"),
            consumed_at=data.get("consumed_at", ""),
            baseline_runtime_path=data.get("baseline_runtime_path", ""),
            baseline_head=data.get("baseline_head", ""),
            packet_hash=data.get("packet_hash", ""),
            scope_fingerprint=data.get("scope_fingerprint", ""),
            metadata=data.get("metadata") or {},
        )


@dataclass(frozen=True)
class RunRecord:
    run_id: str
    project_id: str
    lane_request_id: str = ""
    approval_id: str = ""
    lane_type: str = ""
    title: str = ""
    objective: str = ""
    status: str = "requested"
    execution_mode: str = "manual_copy"
    allowed_actions: tuple[str, ...] = ()
    forbidden_actions: tuple[str, ...] = ()
    stop_conditions: tuple[str, ...] = ()
    baseline_runtime_path: str = ""
    baseline_head: str = ""
    runtime_guard_state: str = ""
    dispatch_state: bool = False
    active_lane_count_at_start: int = 0
    agent_identity: str = ""
    session_id: str = ""
    source: str = ""
    started_at: str = ""
    stopped_at: str = ""
    stop_reason: str = ""
    safety_gate_status: str = ""
    safety_gate_reasons: tuple[str, ...] = ()
    report_ids: tuple[str, ...] = ()
    result_record_ids: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)

    record_type: ClassVar[str] = "RunRecord"

    def __post_init__(self) -> None:
        object.__setattr__(self, "execution_mode", self.execution_mode or "manual_copy")
        object.__setattr__(self, "allowed_actions", tuple(str(item) for item in _tuple(self.allowed_actions)))
        object.__setattr__(self, "forbidden_actions", tuple(str(item) for item in _tuple(self.forbidden_actions)))
        object.__setattr__(self, "stop_conditions", tuple(str(item) for item in _tuple(self.stop_conditions)))
        object.__setattr__(self, "dispatch_state", self.dispatch_state is True)
        object.__setattr__(self, "active_lane_count_at_start", _bounded_handoff_int(self.active_lane_count_at_start, default=0))
        object.__setattr__(self, "safety_gate_reasons", tuple(str(item) for item in _tuple(self.safety_gate_reasons)))
        object.__setattr__(self, "report_ids", tuple(str(item) for item in _tuple(self.report_ids)))
        object.__setattr__(self, "result_record_ids", tuple(str(item) for item in _tuple(self.result_record_ids)))
        object.__setattr__(self, "metadata", _inert_execution_metadata(self.metadata))

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "project_id": self.project_id,
            "lane_request_id": self.lane_request_id,
            "approval_id": self.approval_id,
            "lane_type": self.lane_type,
            "title": self.title,
            "objective": self.objective,
            "status": self.status,
            "execution_mode": self.execution_mode,
            "allowed_actions": list(self.allowed_actions),
            "forbidden_actions": list(self.forbidden_actions),
            "stop_conditions": list(self.stop_conditions),
            "baseline_runtime_path": self.baseline_runtime_path,
            "baseline_head": self.baseline_head,
            "runtime_guard_state": self.runtime_guard_state,
            "dispatch_state": self.dispatch_state,
            "active_lane_count_at_start": self.active_lane_count_at_start,
            "agent_identity": self.agent_identity,
            "session_id": self.session_id,
            "source": self.source,
            "started_at": self.started_at,
            "stopped_at": self.stopped_at,
            "stop_reason": self.stop_reason,
            "safety_gate_status": self.safety_gate_status,
            "safety_gate_reasons": list(self.safety_gate_reasons),
            "report_ids": list(self.report_ids),
            "result_record_ids": list(self.result_record_ids),
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RunRecord:
        return cls(
            run_id=_required(data, "run_id"),
            project_id=_required(data, "project_id"),
            lane_request_id=data.get("lane_request_id", ""),
            approval_id=data.get("approval_id", ""),
            lane_type=data.get("lane_type", ""),
            title=data.get("title", ""),
            objective=data.get("objective", ""),
            status=data.get("status", "requested"),
            execution_mode=data.get("execution_mode", "manual_copy"),
            allowed_actions=data.get("allowed_actions") or (),
            forbidden_actions=data.get("forbidden_actions") or (),
            stop_conditions=data.get("stop_conditions") or (),
            baseline_runtime_path=data.get("baseline_runtime_path", ""),
            baseline_head=data.get("baseline_head", ""),
            runtime_guard_state=data.get("runtime_guard_state", ""),
            dispatch_state=data.get("dispatch_state") is True,
            active_lane_count_at_start=data.get("active_lane_count_at_start", 0),
            agent_identity=data.get("agent_identity", ""),
            session_id=data.get("session_id", ""),
            source=data.get("source", ""),
            started_at=data.get("started_at", ""),
            stopped_at=data.get("stopped_at", ""),
            stop_reason=data.get("stop_reason", ""),
            safety_gate_status=data.get("safety_gate_status", ""),
            safety_gate_reasons=data.get("safety_gate_reasons") or (),
            report_ids=data.get("report_ids") or (),
            result_record_ids=data.get("result_record_ids") or (),
            metadata=data.get("metadata") or {},
        )


@dataclass(frozen=True)
class ReportRecord:
    report_id: str
    run_id: str = ""
    approval_id: str = ""
    project_id: str = ""
    lane_request_id: str = ""
    status: str = "received"
    report_kind: str = "jenny_result"
    summary: str = ""
    result: str = ""
    risks: tuple[str, ...] = ()
    blockers: tuple[str, ...] = ()
    changed_files: tuple[str, ...] = ()
    tests: tuple[str, ...] = ()
    next_recommended_lane: str = ""
    evidence_refs: tuple[str, ...] = ()
    artifact_refs: tuple[str, ...] = ()
    submitted_by: str = ""
    submitted_from: str = ""
    created_at: str = ""
    reviewed_at: str = ""
    reviewed_by: str = ""
    redaction_status: str = "operator_supplied_redacted"
    metadata: dict[str, Any] = field(default_factory=dict)

    record_type: ClassVar[str] = "ReportRecord"

    def __post_init__(self) -> None:
        object.__setattr__(self, "risks", tuple(str(item) for item in _tuple(self.risks)))
        object.__setattr__(self, "blockers", tuple(str(item) for item in _tuple(self.blockers)))
        object.__setattr__(self, "changed_files", tuple(str(item) for item in _tuple(self.changed_files)))
        object.__setattr__(self, "tests", tuple(str(item) for item in _tuple(self.tests)))
        object.__setattr__(self, "evidence_refs", tuple(str(item) for item in _tuple(self.evidence_refs)))
        object.__setattr__(self, "artifact_refs", tuple(str(item) for item in _tuple(self.artifact_refs)))
        object.__setattr__(self, "redaction_status", self.redaction_status or "operator_supplied_redacted")
        object.__setattr__(self, "metadata", _inert_execution_metadata(self.metadata))

    def to_dict(self) -> dict[str, Any]:
        return {
            "report_id": self.report_id,
            "run_id": self.run_id,
            "approval_id": self.approval_id,
            "project_id": self.project_id,
            "lane_request_id": self.lane_request_id,
            "status": self.status,
            "report_kind": self.report_kind,
            "summary": self.summary,
            "result": self.result,
            "risks": list(self.risks),
            "blockers": list(self.blockers),
            "changed_files": list(self.changed_files),
            "tests": list(self.tests),
            "next_recommended_lane": self.next_recommended_lane,
            "evidence_refs": list(self.evidence_refs),
            "artifact_refs": list(self.artifact_refs),
            "submitted_by": self.submitted_by,
            "submitted_from": self.submitted_from,
            "created_at": self.created_at,
            "reviewed_at": self.reviewed_at,
            "reviewed_by": self.reviewed_by,
            "redaction_status": self.redaction_status,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ReportRecord:
        return cls(
            report_id=_required(data, "report_id"),
            run_id=data.get("run_id", ""),
            approval_id=data.get("approval_id", ""),
            project_id=data.get("project_id", ""),
            lane_request_id=data.get("lane_request_id", ""),
            status=data.get("status", "received"),
            report_kind=data.get("report_kind", "jenny_result"),
            summary=data.get("summary", ""),
            result=data.get("result", ""),
            risks=data.get("risks") or (),
            blockers=data.get("blockers") or (),
            changed_files=data.get("changed_files") or (),
            tests=data.get("tests") or (),
            next_recommended_lane=data.get("next_recommended_lane", ""),
            evidence_refs=data.get("evidence_refs") or (),
            artifact_refs=data.get("artifact_refs") or (),
            submitted_by=data.get("submitted_by", ""),
            submitted_from=data.get("submitted_from", ""),
            created_at=data.get("created_at", ""),
            reviewed_at=data.get("reviewed_at", ""),
            reviewed_by=data.get("reviewed_by", ""),
            redaction_status=data.get("redaction_status", "operator_supplied_redacted"),
            metadata=data.get("metadata") or {},
        )


@dataclass(frozen=True)
class ChildRunRecord:
    child_run_id: str
    parent_run_id: str
    project_id: str = ""
    agent_identity: str = ""
    delegation_source: str = ""
    objective: str = ""
    allowed_actions: tuple[str, ...] = ()
    forbidden_actions: tuple[str, ...] = ()
    status: str = "requested"
    failure_reason: str = ""
    report_id: str = ""
    result_record_id: str = ""
    depends_on_child_run_ids: tuple[str, ...] = ()
    created_at: str = ""
    updated_at: str = ""
    stopped_at: str = ""
    stop_reason: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    record_type: ClassVar[str] = "ChildRunRecord"

    def __post_init__(self) -> None:
        object.__setattr__(self, "allowed_actions", tuple(str(item) for item in _tuple(self.allowed_actions)))
        object.__setattr__(self, "forbidden_actions", tuple(str(item) for item in _tuple(self.forbidden_actions)))
        object.__setattr__(self, "depends_on_child_run_ids", tuple(str(item) for item in _tuple(self.depends_on_child_run_ids)))
        metadata = _inert_execution_metadata(self.metadata)
        metadata.update(
            {
                "display_only": True,
            }
        )
        object.__setattr__(self, "metadata", metadata)

    def to_dict(self) -> dict[str, Any]:
        return {
            "child_run_id": self.child_run_id,
            "parent_run_id": self.parent_run_id,
            "project_id": self.project_id,
            "agent_identity": self.agent_identity,
            "delegation_source": self.delegation_source,
            "objective": self.objective,
            "allowed_actions": list(self.allowed_actions),
            "forbidden_actions": list(self.forbidden_actions),
            "status": self.status,
            "failure_reason": self.failure_reason,
            "report_id": self.report_id,
            "result_record_id": self.result_record_id,
            "depends_on_child_run_ids": list(self.depends_on_child_run_ids),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "stopped_at": self.stopped_at,
            "stop_reason": self.stop_reason,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ChildRunRecord:
        return cls(
            child_run_id=_required(data, "child_run_id"),
            parent_run_id=_required(data, "parent_run_id"),
            project_id=data.get("project_id", ""),
            agent_identity=data.get("agent_identity", ""),
            delegation_source=data.get("delegation_source", ""),
            objective=data.get("objective", ""),
            allowed_actions=data.get("allowed_actions") or (),
            forbidden_actions=data.get("forbidden_actions") or (),
            status=data.get("status", "requested"),
            failure_reason=data.get("failure_reason", ""),
            report_id=data.get("report_id", ""),
            result_record_id=data.get("result_record_id", ""),
            depends_on_child_run_ids=data.get("depends_on_child_run_ids") or (),
            created_at=data.get("created_at", ""),
            updated_at=data.get("updated_at", ""),
            stopped_at=data.get("stopped_at", ""),
            stop_reason=data.get("stop_reason", ""),
            metadata=data.get("metadata") or {},
        )


@dataclass(frozen=True)
class WorkerNodeRunRecord:
    worker_run_id: str
    parent_run_id: str
    project_id: str = ""
    worker_id: str = ""
    worker_type: str = "codex"
    display_name: str = ""
    worker_identity: str = "codex"
    worker_host_label: str = "laptop-codex"
    worker_kind: str = "laptop_codex"
    objective: str = ""
    assigned_packet_id: str = ""
    assigned_packet_summary: str = ""
    allowed_actions: tuple[str, ...] = ()
    forbidden_actions: tuple[str, ...] = ()
    status: str = "requested"
    blocked_reasons: tuple[str, ...] = ()
    failure_reason: str = ""
    report_id: str = ""
    report_review_status: str = ""
    report_contract_status: str = ""
    created_at: str = ""
    updated_at: str = ""
    stopped_at: str = ""
    stop_reason: str = ""
    presence_status: str = "offline"
    smoke_status: str = ""
    last_heartbeat_at: str = ""
    last_seen_at: str = ""
    worker_version: str = ""
    capability_summary: str = ""
    capabilities_advertised: tuple[str, ...] = ()
    capabilities_allowed: tuple[str, ...] = ()
    capabilities_blocked: tuple[str, ...] = ()
    project_scope: tuple[str, ...] = ()
    lane_scope: tuple[str, ...] = ()
    max_concurrent_read_only_lanes: int = 0
    max_concurrent_mutation_lanes: int = 0
    source_of_truth: str = "WorkerNodeRunRecord"
    safety_notes: tuple[str, ...] = ()
    worker_dispatch_enabled: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)

    record_type: ClassVar[str] = "WorkerNodeRunRecord"

    def __post_init__(self) -> None:
        object.__setattr__(self, "worker_id", str(self.worker_id or self.worker_run_id))
        object.__setattr__(self, "worker_type", str(self.worker_type or "codex"))
        object.__setattr__(
            self,
            "display_name",
            str(self.display_name or f"{self.worker_identity or 'codex'} on {self.worker_host_label or 'laptop-codex'}"),
        )
        object.__setattr__(self, "allowed_actions", tuple(str(item) for item in _tuple(self.allowed_actions)))
        object.__setattr__(self, "forbidden_actions", tuple(str(item) for item in _tuple(self.forbidden_actions)))
        object.__setattr__(self, "blocked_reasons", tuple(str(item) for item in _tuple(self.blocked_reasons)))
        metadata = _inert_execution_metadata(self.metadata)
        smoke_status = _normalize_worker_node_smoke_status(
            smoke_status=self.smoke_status,
            presence_status=self.presence_status,
            metadata=metadata,
        )
        object.__setattr__(self, "presence_status", _normalize_worker_node_presence_status(self.presence_status))
        object.__setattr__(self, "smoke_status", smoke_status)
        object.__setattr__(self, "last_heartbeat_at", str(self.last_heartbeat_at or self.last_seen_at))
        object.__setattr__(
            self,
            "capabilities_advertised",
            tuple(str(item) for item in _tuple(self.capabilities_advertised)),
        )
        object.__setattr__(
            self,
            "capabilities_allowed",
            tuple(str(item) for item in _tuple(self.capabilities_allowed)),
        )
        object.__setattr__(
            self,
            "capabilities_blocked",
            tuple(str(item) for item in _tuple(self.capabilities_blocked)),
        )
        object.__setattr__(self, "project_scope", tuple(str(item) for item in _tuple(self.project_scope)))
        object.__setattr__(self, "lane_scope", tuple(str(item) for item in _tuple(self.lane_scope)))
        object.__setattr__(
            self,
            "max_concurrent_read_only_lanes",
            _nonnegative_int(self.max_concurrent_read_only_lanes),
        )
        object.__setattr__(
            self,
            "max_concurrent_mutation_lanes",
            _nonnegative_int(self.max_concurrent_mutation_lanes),
        )
        object.__setattr__(self, "source_of_truth", str(self.source_of_truth or "WorkerNodeRunRecord"))
        object.__setattr__(self, "safety_notes", tuple(str(item) for item in _tuple(self.safety_notes)))
        object.__setattr__(self, "worker_dispatch_enabled", False)
        if smoke_status:
            metadata["smoke_status"] = smoke_status
        metadata.update(
            {
                "display_only": True,
            }
        )
        object.__setattr__(self, "metadata", metadata)

    def to_dict(self) -> dict[str, Any]:
        return {
            "worker_run_id": self.worker_run_id,
            "parent_run_id": self.parent_run_id,
            "project_id": self.project_id,
            "worker_id": self.worker_id,
            "worker_type": self.worker_type,
            "display_name": self.display_name,
            "worker_identity": self.worker_identity,
            "worker_host_label": self.worker_host_label,
            "worker_kind": self.worker_kind,
            "objective": self.objective,
            "assigned_packet_id": self.assigned_packet_id,
            "assigned_packet_summary": self.assigned_packet_summary,
            "allowed_actions": list(self.allowed_actions),
            "forbidden_actions": list(self.forbidden_actions),
            "status": self.status,
            "blocked_reasons": list(self.blocked_reasons),
            "failure_reason": self.failure_reason,
            "report_id": self.report_id,
            "report_review_status": self.report_review_status,
            "report_contract_status": self.report_contract_status,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "stopped_at": self.stopped_at,
            "stop_reason": self.stop_reason,
            "presence_status": self.presence_status,
            "smoke_status": self.smoke_status,
            "last_heartbeat_at": self.last_heartbeat_at,
            "last_seen_at": self.last_seen_at,
            "worker_version": self.worker_version,
            "capability_summary": self.capability_summary,
            "capabilities_advertised": list(self.capabilities_advertised),
            "capabilities_allowed": list(self.capabilities_allowed),
            "capabilities_blocked": list(self.capabilities_blocked),
            "project_scope": list(self.project_scope),
            "lane_scope": list(self.lane_scope),
            "max_concurrent_read_only_lanes": self.max_concurrent_read_only_lanes,
            "max_concurrent_mutation_lanes": self.max_concurrent_mutation_lanes,
            "source_of_truth": self.source_of_truth,
            "safety_notes": list(self.safety_notes),
            "worker_dispatch_enabled": False,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> WorkerNodeRunRecord:
        return cls(
            worker_run_id=_required(data, "worker_run_id"),
            parent_run_id=_required(data, "parent_run_id"),
            project_id=data.get("project_id", ""),
            worker_id=data.get("worker_id", ""),
            worker_type=data.get("worker_type", "codex"),
            display_name=data.get("display_name", ""),
            worker_identity=data.get("worker_identity", "codex"),
            worker_host_label=data.get("worker_host_label", "laptop-codex"),
            worker_kind=data.get("worker_kind", "laptop_codex"),
            objective=data.get("objective", ""),
            assigned_packet_id=data.get("assigned_packet_id", ""),
            assigned_packet_summary=data.get("assigned_packet_summary", ""),
            allowed_actions=data.get("allowed_actions") or (),
            forbidden_actions=data.get("forbidden_actions") or (),
            status=data.get("status", "requested"),
            blocked_reasons=data.get("blocked_reasons") or (),
            failure_reason=data.get("failure_reason", ""),
            report_id=data.get("report_id", ""),
            report_review_status=data.get("report_review_status", ""),
            report_contract_status=data.get("report_contract_status", ""),
            created_at=data.get("created_at", ""),
            updated_at=data.get("updated_at", ""),
            stopped_at=data.get("stopped_at", ""),
            stop_reason=data.get("stop_reason", ""),
            presence_status=data.get("presence_status", "offline"),
            smoke_status=data.get("smoke_status", "") or _dict(data.get("metadata")).get("smoke_status", ""),
            last_heartbeat_at=data.get("last_heartbeat_at", ""),
            last_seen_at=data.get("last_seen_at", ""),
            worker_version=data.get("worker_version", ""),
            capability_summary=data.get("capability_summary", ""),
            capabilities_advertised=data.get("capabilities_advertised") or (),
            capabilities_allowed=data.get("capabilities_allowed") or (),
            capabilities_blocked=data.get("capabilities_blocked") or (),
            project_scope=data.get("project_scope") or (),
            lane_scope=data.get("lane_scope") or (),
            max_concurrent_read_only_lanes=data.get("max_concurrent_read_only_lanes", 0),
            max_concurrent_mutation_lanes=data.get("max_concurrent_mutation_lanes", 0),
            source_of_truth=data.get("source_of_truth", "WorkerNodeRunRecord"),
            safety_notes=data.get("safety_notes") or (),
            worker_dispatch_enabled=False,
            metadata=data.get("metadata") or {},
        )


@dataclass(frozen=True)
class TaskControlEnvelope:
    envelope_id: str = ""
    active_lane: str = ""
    mode: str = ""
    allowed_actions: tuple[str, ...] = ()
    forbidden_actions: tuple[str, ...] = ()
    current_repo: str = ""
    expected_systems_files: tuple[str, ...] = ()
    stop_condition: str = ""
    other_threads_excluded: tuple[str, ...] = ()
    report_requirements: tuple[str, ...] = ()
    risk_level: str = ""
    approval_required: bool = False
    approval_slice_ids: tuple[str, ...] = ()
    evidence_ids: tuple[str, ...] = ()
    token_context_policy: str = ""
    created_at: str = ""
    status: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    record_type: ClassVar[str] = "TaskControlEnvelope"

    def __post_init__(self) -> None:
        object.__setattr__(self, "allowed_actions", _tuple(self.allowed_actions))
        object.__setattr__(self, "forbidden_actions", _tuple(self.forbidden_actions))
        object.__setattr__(self, "expected_systems_files", _tuple(self.expected_systems_files))
        object.__setattr__(self, "other_threads_excluded", _tuple(self.other_threads_excluded))
        object.__setattr__(self, "report_requirements", tuple(str(item) for item in _tuple(self.report_requirements)))
        object.__setattr__(self, "approval_slice_ids", tuple(str(item) for item in _tuple(self.approval_slice_ids)))
        object.__setattr__(self, "evidence_ids", tuple(str(item) for item in _tuple(self.evidence_ids)))
        object.__setattr__(self, "metadata", _dict(self.metadata))

    def to_dict(self) -> dict[str, Any]:
        return {
            "envelope_id": self.envelope_id,
            "active_lane": self.active_lane,
            "mode": self.mode,
            "allowed_actions": list(self.allowed_actions),
            "forbidden_actions": list(self.forbidden_actions),
            "current_repo": self.current_repo,
            "expected_systems_files": list(self.expected_systems_files),
            "stop_condition": self.stop_condition,
            "other_threads_excluded": list(self.other_threads_excluded),
            "report_requirements": list(self.report_requirements),
            "risk_level": self.risk_level,
            "approval_required": self.approval_required,
            "approval_slice_ids": list(self.approval_slice_ids),
            "evidence_ids": list(self.evidence_ids),
            "token_context_policy": self.token_context_policy,
            "created_at": self.created_at,
            "status": self.status,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TaskControlEnvelope:
        return cls(
            envelope_id=data.get("envelope_id", ""),
            active_lane=_required(data, "active_lane"),
            mode=_required(data, "mode"),
            allowed_actions=data.get("allowed_actions") or (),
            forbidden_actions=data.get("forbidden_actions") or (),
            current_repo=data.get("current_repo", ""),
            expected_systems_files=data.get("expected_systems_files") or (),
            stop_condition=data.get("stop_condition", ""),
            other_threads_excluded=data.get("other_threads_excluded") or (),
            report_requirements=data.get("report_requirements") or (),
            risk_level=data.get("risk_level", ""),
            approval_required=bool(data.get("approval_required", False)),
            approval_slice_ids=data.get("approval_slice_ids") or (),
            evidence_ids=data.get("evidence_ids") or (),
            token_context_policy=data.get("token_context_policy", ""),
            created_at=data.get("created_at", ""),
            status=data.get("status", ""),
            metadata=data.get("metadata") or {},
        )


@dataclass(frozen=True)
class StartGateCheck:
    start_gate_id: str
    envelope_id: str
    decision_state: str = "informational"
    reasons: tuple[str, ...] = ()
    blocked_actions: tuple[str, ...] = ()
    required_approvals: tuple[str, ...] = ()
    dirty_worktree_state: str = ""
    branch_safety_state: str = ""
    secret_safety_state: str = ""
    token_context_state: str = ""
    created_at: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    record_type: ClassVar[str] = "StartGateCheck"

    def __post_init__(self) -> None:
        object.__setattr__(self, "reasons", tuple(str(item) for item in _tuple(self.reasons)))
        object.__setattr__(self, "blocked_actions", tuple(str(item) for item in _tuple(self.blocked_actions)))
        object.__setattr__(self, "required_approvals", tuple(str(item) for item in _tuple(self.required_approvals)))
        object.__setattr__(self, "metadata", _dict(self.metadata))

    def to_dict(self) -> dict[str, Any]:
        return {
            "start_gate_id": self.start_gate_id,
            "envelope_id": self.envelope_id,
            "decision_state": self.decision_state,
            "reasons": list(self.reasons),
            "blocked_actions": list(self.blocked_actions),
            "required_approvals": list(self.required_approvals),
            "dirty_worktree_state": self.dirty_worktree_state,
            "branch_safety_state": self.branch_safety_state,
            "secret_safety_state": self.secret_safety_state,
            "token_context_state": self.token_context_state,
            "created_at": self.created_at,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> StartGateCheck:
        return cls(
            start_gate_id=_required(data, "start_gate_id"),
            envelope_id=_required(data, "envelope_id"),
            decision_state=data.get("decision_state", "informational"),
            reasons=data.get("reasons") or (),
            blocked_actions=data.get("blocked_actions") or (),
            required_approvals=data.get("required_approvals") or (),
            dirty_worktree_state=data.get("dirty_worktree_state", ""),
            branch_safety_state=data.get("branch_safety_state", ""),
            secret_safety_state=data.get("secret_safety_state", ""),
            token_context_state=data.get("token_context_state", ""),
            created_at=data.get("created_at", ""),
            metadata=data.get("metadata") or {},
        )


@dataclass(frozen=True)
class VerifierWorkflowEvidenceRecord:
    record_id: str
    created_at: str
    guard_type: str = "verifier_workflow"
    source: str = "caller_supplied_workflow_state"
    lane_id: str = ""
    task_id: str = ""
    domain_id: str = ""
    action_class: str = ""
    decision_state: str = "unknown"
    would_block: bool = False
    reasons: tuple[str, ...] = ()
    blocked_actions: tuple[str, ...] = ()
    required_approvals: tuple[str, ...] = ()
    unresolved_policy_fields: tuple[str, ...] = ()
    would_execute: bool = False
    dry_run_only: bool = True
    enforces_runtime: bool = False
    packet_hash: str = ""
    packet_version: str = ""
    packet_identity: dict[str, str] = field(default_factory=dict)

    record_type: ClassVar[str] = "VerifierWorkflowEvidenceRecord"

    def __post_init__(self) -> None:
        object.__setattr__(self, "guard_type", "verifier_workflow")
        object.__setattr__(self, "reasons", tuple(str(item) for item in _tuple(self.reasons)))
        object.__setattr__(self, "blocked_actions", tuple(str(item) for item in _tuple(self.blocked_actions)))
        object.__setattr__(self, "required_approvals", tuple(str(item) for item in _tuple(self.required_approvals)))
        object.__setattr__(self, "unresolved_policy_fields", tuple(str(item) for item in _tuple(self.unresolved_policy_fields)))
        object.__setattr__(self, "would_execute", False)
        object.__setattr__(self, "dry_run_only", True)
        object.__setattr__(self, "enforces_runtime", False)
        object.__setattr__(self, "packet_hash", _sanitize_pr_merge_packet_hash(self.action_class, self.packet_hash))
        object.__setattr__(self, "packet_version", _sanitize_pr_merge_packet_version(self.action_class, self.packet_version))
        object.__setattr__(self, "packet_identity", _sanitize_pr_merge_packet_identity(self.action_class, self.packet_identity))

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "record_id": self.record_id,
            "created_at": self.created_at,
            "guard_type": "verifier_workflow",
            "source": self.source,
            "lane_id": self.lane_id,
            "task_id": self.task_id,
            "domain_id": self.domain_id,
            "action_class": self.action_class,
            "decision_state": self.decision_state,
            "would_block": self.would_block,
            "reasons": list(self.reasons),
            "blocked_actions": list(self.blocked_actions),
            "required_approvals": list(self.required_approvals),
            "unresolved_policy_fields": list(self.unresolved_policy_fields),
            "would_execute": False,
            "dry_run_only": True,
            "enforces_runtime": False,
        }
        if self.packet_hash:
            payload["packet_hash"] = self.packet_hash
        if self.packet_version:
            payload["packet_version"] = self.packet_version
        if self.packet_identity:
            payload["packet_identity"] = dict(self.packet_identity)
        return payload

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> VerifierWorkflowEvidenceRecord:
        return cls(
            record_id=_required(data, "record_id"),
            created_at=_required(data, "created_at"),
            source=data.get("source", "caller_supplied_workflow_state"),
            lane_id=data.get("lane_id", ""),
            task_id=data.get("task_id", ""),
            domain_id=data.get("domain_id", ""),
            action_class=data.get("action_class", ""),
            decision_state=data.get("decision_state", "unknown"),
            would_block=bool(data.get("would_block", False)),
            reasons=data.get("reasons") or (),
            blocked_actions=data.get("blocked_actions") or (),
            required_approvals=data.get("required_approvals") or (),
            unresolved_policy_fields=data.get("unresolved_policy_fields") or (),
            packet_hash=data.get("packet_hash", ""),
            packet_version=data.get("packet_version", ""),
            packet_identity=data.get("packet_identity") or {},
        )


@dataclass(frozen=True)
class PrMergeApprovalRecord:
    approval_id: str
    created_at: str
    expires_at: str | None = None
    action_class: str = ""
    packet_hash: str = ""
    packet_version: str = ""
    repo: str = ""
    pr_number: str = ""
    base_branch: str = ""
    head_commit: str = ""
    expected_base_head: str = ""
    merge_method: str = ""
    operator_id: str = ""
    approved_scope: str = ""
    consumed: bool = False
    would_execute: bool = False
    dry_run_only: bool = True
    enforces_runtime: bool = False

    record_type: ClassVar[str] = "PrMergeApprovalRecord"

    def __post_init__(self) -> None:
        action_class = _sanitize_pr_merge_action_class(self.action_class)
        object.__setattr__(self, "action_class", action_class)
        object.__setattr__(self, "packet_hash", _sanitize_pr_merge_packet_hash(action_class, self.packet_hash))
        object.__setattr__(self, "packet_version", _sanitize_pr_merge_packet_version(action_class, self.packet_version))
        object.__setattr__(self, "repo", _normalize_packet_repo(self.repo) if action_class == "pr_merge" else "")
        object.__setattr__(self, "pr_number", _normalize_packet_pr_number(self.pr_number) if action_class == "pr_merge" else "")
        object.__setattr__(self, "base_branch", _clean_text(self.base_branch, _MAX_BASE_BRANCH_CHARS) if action_class == "pr_merge" else "")
        object.__setattr__(self, "head_commit", _normalize_packet_sha(self.head_commit) if action_class == "pr_merge" else "")
        object.__setattr__(self, "expected_base_head", _normalize_packet_sha(self.expected_base_head) if action_class == "pr_merge" else "")
        object.__setattr__(self, "merge_method", _normalize_packet_merge_method(self.merge_method) if action_class == "pr_merge" else "")
        object.__setattr__(self, "operator_id", _sanitize_operator_id(self.operator_id))
        object.__setattr__(self, "approved_scope", _sanitize_pr_merge_approved_scope(self.approved_scope) if action_class == "pr_merge" else "")
        object.__setattr__(self, "expires_at", str(self.expires_at).strip() if self.expires_at else None)
        object.__setattr__(self, "consumed", False)
        object.__setattr__(self, "would_execute", False)
        object.__setattr__(self, "dry_run_only", True)
        object.__setattr__(self, "enforces_runtime", False)

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "approval_id": self.approval_id,
            "created_at": self.created_at,
        }
        if self.expires_at:
            payload["expires_at"] = self.expires_at
        for field_name in (
            "action_class",
            "packet_hash",
            "packet_version",
            "repo",
            "pr_number",
            "base_branch",
            "head_commit",
            "expected_base_head",
            "merge_method",
            "operator_id",
            "approved_scope",
        ):
            value = getattr(self, field_name)
            if value:
                payload[field_name] = value
        payload["consumed"] = False
        payload["would_execute"] = False
        payload["dry_run_only"] = True
        payload["enforces_runtime"] = False
        return payload

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PrMergeApprovalRecord:
        return cls(
            approval_id=_required(data, "approval_id"),
            created_at=_required(data, "created_at"),
            expires_at=data.get("expires_at"),
            action_class=data.get("action_class", ""),
            packet_hash=data.get("packet_hash", ""),
            packet_version=data.get("packet_version", ""),
            repo=data.get("repo", ""),
            pr_number=data.get("pr_number", ""),
            base_branch=data.get("base_branch", ""),
            head_commit=data.get("head_commit", ""),
            expected_base_head=data.get("expected_base_head", ""),
            merge_method=data.get("merge_method", ""),
            operator_id=data.get("operator_id", ""),
            approved_scope=data.get("approved_scope", ""),
            consumed=False,
            would_execute=False,
            dry_run_only=True,
            enforces_runtime=False,
        )


def approval_matches_pr_merge_packet(
    approval: dict[str, Any] | PrMergeApprovalRecord | None,
    packet: dict[str, Any] | None,
    *,
    now: str | None = None,
) -> dict[str, Any]:
    reasons: list[str] = []
    missing_fields: list[str] = []
    invalid_fields: list[str] = []
    approval_record = approval if isinstance(approval, PrMergeApprovalRecord) else None
    if approval_record is None and isinstance(approval, dict):
        try:
            approval_record = PrMergeApprovalRecord.from_dict(approval)
        except (KeyError, TypeError, ValueError):
            approval_record = None
    packet_data = dict(packet or {})

    if approval_record is None:
        reasons.append("approval record missing or invalid")
    required = (
        "action_class",
        "packet_hash",
        "packet_version",
        "repo",
        "pr_number",
        "base_branch",
        "head_commit",
        "expected_base_head",
        "merge_method",
    )
    for field_name in required:
        if not packet_data.get(field_name):
            missing_fields.append(field_name)
            reasons.append(f"missing packet field: {field_name}")

    normalized_packet = {
        "action_class": _sanitize_pr_merge_action_class(packet_data.get("action_class")),
        "packet_hash": _sanitize_pr_merge_packet_hash("pr_merge", packet_data.get("packet_hash")),
        "packet_version": _sanitize_pr_merge_packet_version("pr_merge", packet_data.get("packet_version")),
        "repo": _normalize_packet_repo(packet_data.get("repo")),
        "pr_number": _normalize_packet_pr_number(packet_data.get("pr_number")),
        "base_branch": _clean_text(packet_data.get("base_branch"), _MAX_BASE_BRANCH_CHARS),
        "head_commit": _normalize_packet_sha(packet_data.get("head_commit")),
        "expected_base_head": _normalize_packet_sha(packet_data.get("expected_base_head")),
        "merge_method": _normalize_packet_merge_method(packet_data.get("merge_method")),
    }
    for field_name, value in normalized_packet.items():
        if packet_data.get(field_name) and not value:
            invalid_fields.append(field_name)
            reasons.append(f"invalid packet field: {field_name}")

    if approval_record is not None:
        approval_payload = approval_record.to_dict()
        if approval_payload.get("consumed") is not False:
            invalid_fields.append("consumed")
            reasons.append("approval consumed")
        if approval_payload.get("would_execute") is not False:
            invalid_fields.append("would_execute")
            reasons.append("approval would_execute is not false")
        if approval_payload.get("dry_run_only") is not True:
            invalid_fields.append("dry_run_only")
            reasons.append("approval dry_run_only is not true")
        if approval_payload.get("enforces_runtime") is not False:
            invalid_fields.append("enforces_runtime")
            reasons.append("approval enforces_runtime is not false")
        if now and approval_payload.get("expires_at") and str(now).strip() > str(approval_payload["expires_at"]).strip():
            invalid_fields.append("expires_at")
            reasons.append("approval expired")
        for field_name in required:
            if approval_payload.get(field_name) != normalized_packet.get(field_name):
                reasons.append(f"{field_name} mismatch")

    valid = not reasons
    return {
        "valid": valid,
        "matches_packet": valid,
        "reasons": reasons,
        "missing_fields": missing_fields,
        "invalid_fields": invalid_fields,
        "would_execute": False,
        "dry_run_only": True,
        "enforces_runtime": False,
    }


@dataclass(frozen=True)
class ApprovalSlice:
    approval_slice_id: str = ""
    related_action_id: str = ""
    approval_type: str = ""
    decision_state: str = "pending"
    required_by: str = ""
    reason: str = ""
    safety_conditions: tuple[str, ...] = ()
    evidence_ids: tuple[str, ...] = ()
    created_at: str = ""
    expires_at: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    # Legacy PR-E fields remain accepted for records already written by earlier
    # inert planning layers. They are not part of the canonical PR-H payload.
    approval_id: str = ""
    lane: str = ""
    mode: str = ""
    approved_actions: tuple[str, ...] = ()
    forbidden_actions: tuple[str, ...] = ()
    approver: str = ""
    approved_at: str = ""

    record_type: ClassVar[str] = "ApprovalSlice"

    def __post_init__(self) -> None:
        approval_slice_id = self.approval_slice_id or self.approval_id
        required_by = self.required_by or self.approver
        created_at = self.created_at or self.approved_at
        safety_conditions = self.safety_conditions or self.forbidden_actions
        if not self.decision_state:
            object.__setattr__(self, "decision_state", "pending")
        object.__setattr__(self, "approval_slice_id", approval_slice_id)
        object.__setattr__(self, "approval_id", self.approval_id or approval_slice_id)
        object.__setattr__(self, "required_by", required_by)
        object.__setattr__(self, "created_at", created_at)
        object.__setattr__(self, "safety_conditions", tuple(str(item) for item in _tuple(safety_conditions)))
        object.__setattr__(self, "evidence_ids", tuple(str(item) for item in _tuple(self.evidence_ids)))
        object.__setattr__(self, "approved_actions", _tuple(self.approved_actions))
        object.__setattr__(self, "forbidden_actions", _tuple(self.forbidden_actions))
        object.__setattr__(self, "metadata", _dict(self.metadata))

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "approval_slice_id": self.approval_slice_id,
            "related_action_id": self.related_action_id,
            "approval_type": self.approval_type,
            "decision_state": self.decision_state,
            "required_by": self.required_by,
            "reason": self.reason,
            "safety_conditions": list(self.safety_conditions),
            "evidence_ids": list(self.evidence_ids),
            "created_at": self.created_at,
            "expires_at": self.expires_at,
            "metadata": dict(self.metadata),
        }
        if any((self.lane, self.mode, self.approved_actions, self.approver, self.approved_at)):
            payload["lane"] = self.lane
            payload["mode"] = self.mode
            payload["approved_actions"] = list(self.approved_actions)
            payload["forbidden_actions"] = list(self.forbidden_actions)
            payload["approver"] = self.approver
            payload["approved_at"] = self.approved_at
        return payload

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ApprovalSlice:
        return cls(
            approval_slice_id=data.get("approval_slice_id", data.get("approval_id", "")),
            related_action_id=data.get("related_action_id", ""),
            approval_type=data.get("approval_type", ""),
            decision_state=data.get("decision_state", "pending"),
            required_by=data.get("required_by", data.get("approver", "")),
            reason=data.get("reason", ""),
            safety_conditions=data.get("safety_conditions", data.get("forbidden_actions") or ()),
            evidence_ids=data.get("evidence_ids") or (),
            created_at=data.get("created_at", data.get("approved_at", "")),
            expires_at=data.get("expires_at"),
            metadata=data.get("metadata") or {},
            approval_id=data.get("approval_id", ""),
            lane=data.get("lane", ""),
            mode=data.get("mode", ""),
            approved_actions=data.get("approved_actions") or (),
            forbidden_actions=data.get("forbidden_actions") or (),
            approver=data.get("approver", ""),
            approved_at=data.get("approved_at", ""),
        )


@dataclass(frozen=True)
class EvidenceCard:
    evidence_id: str
    summary: str
    related_lane: str = ""
    related_action_id: str = ""
    related_record_type: str = ""
    evidence_type: str = ""
    source_label: str = ""
    created_at: str = ""
    risk_notes: tuple[str, ...] = ()
    artifact_refs: tuple[ArtifactRef, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)

    record_type: ClassVar[str] = "EvidenceCard"

    def __post_init__(self) -> None:
        refs = tuple(
            item if isinstance(item, ArtifactRef) else ArtifactRef.from_dict(item)
            for item in self.artifact_refs
        )
        object.__setattr__(self, "artifact_refs", refs)
        object.__setattr__(self, "risk_notes", tuple(str(item) for item in _tuple(self.risk_notes)))
        object.__setattr__(self, "metadata", _dict(self.metadata))

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "evidence_id": self.evidence_id,
            "related_lane": self.related_lane,
            "related_action_id": self.related_action_id,
            "related_record_type": self.related_record_type,
            "summary": self.summary,
            "evidence_type": self.evidence_type,
            "source_label": self.source_label,
            "created_at": self.created_at,
            "risk_notes": list(self.risk_notes),
            "metadata": dict(self.metadata),
        }
        if self.artifact_refs:
            payload["artifact_refs"] = [artifact.to_dict() for artifact in self.artifact_refs]
        return payload

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> EvidenceCard:
        return cls(
            evidence_id=_required(data, "evidence_id"),
            summary=_required(data, "summary"),
            related_lane=data.get("related_lane", ""),
            related_action_id=data.get("related_action_id", ""),
            related_record_type=data.get("related_record_type", ""),
            evidence_type=data.get("evidence_type", data.get("type", "")),
            source_label=data.get("source_label", data.get("source", "")),
            created_at=data.get("created_at", ""),
            risk_notes=data.get("risk_notes") or (),
            artifact_refs=tuple(ArtifactRef.from_dict(item) for item in data.get("artifact_refs") or ()),
            metadata=data.get("metadata") or {},
        )


@dataclass(frozen=True)
class OperatorAction:
    action_id: str
    title: str
    lane: str
    mode: str
    requested_action: str
    risk_level: str = ""
    status: str = "requested"
    required_approval: str = ""
    approval_id: str = ""
    evidence_ids: tuple[str, ...] = ()
    stop_condition: str = ""
    created_at: str = ""
    expires_at: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    record_type: ClassVar[str] = "OperatorAction"

    def __post_init__(self) -> None:
        object.__setattr__(self, "evidence_ids", tuple(str(item) for item in _tuple(self.evidence_ids)))
        object.__setattr__(self, "metadata", _dict(self.metadata))

    def to_dict(self) -> dict[str, Any]:
        return {
            "action_id": self.action_id,
            "title": self.title,
            "lane": self.lane,
            "mode": self.mode,
            "requested_action": self.requested_action,
            "risk_level": self.risk_level,
            "status": self.status,
            "required_approval": self.required_approval,
            "approval_id": self.approval_id,
            "evidence_ids": list(self.evidence_ids),
            "stop_condition": self.stop_condition,
            "created_at": self.created_at,
            "expires_at": self.expires_at,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> OperatorAction:
        return cls(
            action_id=_required(data, "action_id"),
            title=_required(data, "title"),
            lane=_required(data, "lane"),
            mode=_required(data, "mode"),
            requested_action=_required(data, "requested_action"),
            risk_level=data.get("risk_level", ""),
            status=data.get("status", "requested"),
            required_approval=data.get("required_approval", ""),
            approval_id=data.get("approval_id", ""),
            evidence_ids=data.get("evidence_ids") or (),
            stop_condition=data.get("stop_condition", ""),
            created_at=data.get("created_at", ""),
            expires_at=data.get("expires_at"),
            metadata=data.get("metadata") or {},
        )


@dataclass(frozen=True)
class SessionProjectLinkRecord:
    link_id: str
    project_id: str
    session_id: str
    lineage_root_id: str = ""
    profile: str = ""
    source: str = ""
    title_snapshot: str = ""
    cwd_snapshot: str = ""
    linked_at: str = ""
    linked_by: str = ""
    link_method: str = "manual"
    confidence: str = "manual"
    status: str = "active"
    metadata: dict[str, Any] = field(default_factory=dict)

    record_type: ClassVar[str] = "SessionProjectLinkRecord"

    def __post_init__(self) -> None:
        object.__setattr__(self, "metadata", _dict(self.metadata))

    @property
    def durable_session_id(self) -> str:
        return self.lineage_root_id or self.session_id

    def to_dict(self) -> dict[str, Any]:
        return {
            "link_id": self.link_id,
            "project_id": self.project_id,
            "session_id": self.session_id,
            "lineage_root_id": self.lineage_root_id,
            "profile": self.profile,
            "source": self.source,
            "title_snapshot": self.title_snapshot,
            "cwd_snapshot": self.cwd_snapshot,
            "linked_at": self.linked_at,
            "linked_by": self.linked_by,
            "link_method": self.link_method,
            "confidence": self.confidence,
            "status": self.status,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SessionProjectLinkRecord:
        return cls(
            link_id=_required(data, "link_id"),
            project_id=_required(data, "project_id"),
            session_id=_required(data, "session_id"),
            lineage_root_id=data.get("lineage_root_id", ""),
            profile=data.get("profile", ""),
            source=data.get("source", ""),
            title_snapshot=data.get("title_snapshot", ""),
            cwd_snapshot=data.get("cwd_snapshot", ""),
            linked_at=data.get("linked_at", ""),
            linked_by=data.get("linked_by", ""),
            link_method=data.get("link_method", "manual"),
            confidence=data.get("confidence", "manual"),
            status=data.get("status", "active"),
            metadata=data.get("metadata") or {},
        )


@dataclass(frozen=True)
class MissionBrief:
    mission_id: str
    title: str
    created_at: str
    goal: GoalContract
    control: TaskControlEnvelope
    approvals: tuple[ApprovalSlice, ...] = ()
    evidence: tuple[EvidenceCard, ...] = ()
    artifacts: tuple[ArtifactRef, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)

    record_type: ClassVar[str] = "MissionBrief"

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "goal",
            self.goal if isinstance(self.goal, GoalContract) else GoalContract.from_dict(self.goal),
        )
        object.__setattr__(
            self,
            "control",
            self.control
            if isinstance(self.control, TaskControlEnvelope)
            else TaskControlEnvelope.from_dict(self.control),
        )
        object.__setattr__(
            self,
            "approvals",
            tuple(
                item if isinstance(item, ApprovalSlice) else ApprovalSlice.from_dict(item)
                for item in self.approvals
            ),
        )
        object.__setattr__(
            self,
            "evidence",
            tuple(
                item if isinstance(item, EvidenceCard) else EvidenceCard.from_dict(item)
                for item in self.evidence
            ),
        )
        object.__setattr__(
            self,
            "artifacts",
            tuple(
                item if isinstance(item, ArtifactRef) else ArtifactRef.from_dict(item)
                for item in self.artifacts
            ),
        )
        object.__setattr__(self, "metadata", _dict(self.metadata))

    def to_dict(self) -> dict[str, Any]:
        return {
            "mission_id": self.mission_id,
            "title": self.title,
            "created_at": self.created_at,
            "goal": self.goal.to_dict(),
            "control": self.control.to_dict(),
            "approvals": [approval.to_dict() for approval in self.approvals],
            "evidence": [card.to_dict() for card in self.evidence],
            "artifacts": [artifact.to_dict() for artifact in self.artifacts],
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> MissionBrief:
        return cls(
            mission_id=_required(data, "mission_id"),
            title=_required(data, "title"),
            created_at=_required(data, "created_at"),
            goal=GoalContract.from_dict(_required(data, "goal")),
            control=TaskControlEnvelope.from_dict(_required(data, "control")),
            approvals=tuple(ApprovalSlice.from_dict(item) for item in data.get("approvals") or ()),
            evidence=tuple(EvidenceCard.from_dict(item) for item in data.get("evidence") or ()),
            artifacts=tuple(ArtifactRef.from_dict(item) for item in data.get("artifacts") or ()),
            metadata=data.get("metadata") or {},
        )


_MAX_HANDOFF_TEXT_CHARS = 160
_MAX_HANDOFF_PATH_CHARS = 240
_MAX_HANDOFF_WARNINGS = 20
_MAX_RUNTIME_LIST_ITEMS = 20

_RUNTIME_TEXT_KEYS = {
    "branch",
    "error",
    "latest_merged_pr",
    "path",
    "runtime_path",
    "state",
    "status",
}
_RUNTIME_SHA_KEYS = {
    "default_branch_head",
    "head",
}
_RUNTIME_BOOL_KEYS = {
    "broken_git_metadata",
    "clean",
    "dirty",
    "exists",
    "git_healthy",
    "missing_path",
    "recorded",
    "unrecorded",
}
_RUNTIME_LIST_KEYS = {
    "dirty_files",
    "merged_prs_after_accepted_baseline",
    "status_short",
    "untracked_files",
}


def _bounded_handoff_text(value: Any, max_chars: int = _MAX_HANDOFF_TEXT_CHARS) -> str:
    text = str(value or "").strip().replace("\x00", "")
    if len(text) > max_chars:
        return text[: max_chars - 1] + "…"
    return text


def _bounded_handoff_int(value: Any, default: int = 0) -> int:
    if isinstance(value, bool):
        return default
    try:
        number = int(value)
    except (TypeError, ValueError):
        return default
    return max(0, min(number, 999))


def _bounded_handoff_warnings(value: Any) -> tuple[str, ...]:
    output: list[str] = []
    for item in _tuple(value):
        text = _bounded_handoff_text(item)
        if text and text not in output:
            output.append(text)
        if len(output) >= _MAX_HANDOFF_WARNINGS:
            break
    return tuple(output)


def _bounded_runtime_list(value: Any) -> list[str]:
    output: list[str] = []
    for item in _tuple(value):
        text = _bounded_handoff_text(item)
        if text and text not in output:
            output.append(text)
        if len(output) >= _MAX_RUNTIME_LIST_ITEMS:
            break
    return output


def _bounded_runtime_section(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    section: dict[str, Any] = {}
    for key in sorted(_RUNTIME_TEXT_KEYS):
        if key in value:
            max_chars = (
                _MAX_HANDOFF_PATH_CHARS
                if key in {"path", "runtime_path"}
                else _MAX_HANDOFF_TEXT_CHARS
            )
            section[key] = _bounded_handoff_text(value.get(key), max_chars)
    for key in sorted(_RUNTIME_SHA_KEYS):
        if key in value:
            section[key] = _normalize_packet_sha(value.get(key))
    for key in sorted(_RUNTIME_BOOL_KEYS):
        if key in value and isinstance(value.get(key), bool):
            section[key] = value[key]
    for key in sorted(_RUNTIME_LIST_KEYS):
        if key in value:
            section[key] = _bounded_runtime_list(value.get(key))
    return section


@dataclass(frozen=True)
class AcceptedBaselineRecord:
    baseline_id: str = ""
    recorded_at: str = ""
    source: str = ""
    runtime_path: str = ""
    head: str = ""
    rollback_runtime_path: str = ""
    rollback_head: str = ""
    dispatch_in_gateway: bool = False
    active_kanban: int = 0
    max_active_lane: int = 1
    max_read_only_lanes: int = 2
    max_mutation_lanes: int = 1
    issue: str = ""
    source_runtime: dict[str, Any] = field(default_factory=dict)
    dashboard_runtime: dict[str, Any] = field(default_factory=dict)
    gateway_runtime: dict[str, Any] = field(default_factory=dict)
    rollback_runtime: dict[str, Any] = field(default_factory=dict)
    display_only: bool = True
    would_execute: bool = False
    dry_run_only: bool = True
    enforces_runtime: bool = False

    record_type: ClassVar[str] = "AcceptedBaselineRecord"

    def __post_init__(self) -> None:
        object.__setattr__(self, "baseline_id", _bounded_handoff_text(self.baseline_id))
        object.__setattr__(self, "recorded_at", _bounded_handoff_text(self.recorded_at))
        object.__setattr__(self, "source", _bounded_handoff_text(self.source))
        object.__setattr__(self, "runtime_path", _bounded_handoff_text(self.runtime_path, _MAX_HANDOFF_PATH_CHARS))
        object.__setattr__(self, "head", _normalize_packet_sha(self.head))
        object.__setattr__(self, "rollback_runtime_path", _bounded_handoff_text(self.rollback_runtime_path, _MAX_HANDOFF_PATH_CHARS))
        object.__setattr__(self, "rollback_head", _normalize_packet_sha(self.rollback_head))
        object.__setattr__(self, "dispatch_in_gateway", self.dispatch_in_gateway is True)
        object.__setattr__(self, "active_kanban", _bounded_handoff_int(self.active_kanban, default=0))
        object.__setattr__(self, "max_active_lane", _bounded_handoff_int(self.max_active_lane, default=1) or 1)
        object.__setattr__(self, "max_read_only_lanes", _bounded_handoff_int(self.max_read_only_lanes, default=2) or 2)
        object.__setattr__(self, "max_mutation_lanes", _bounded_handoff_int(self.max_mutation_lanes, default=1) or 1)
        object.__setattr__(self, "issue", _bounded_handoff_text(self.issue))
        object.__setattr__(self, "source_runtime", _bounded_runtime_section(self.source_runtime))
        object.__setattr__(self, "dashboard_runtime", _bounded_runtime_section(self.dashboard_runtime))
        object.__setattr__(self, "gateway_runtime", _bounded_runtime_section(self.gateway_runtime))
        object.__setattr__(self, "rollback_runtime", _bounded_runtime_section(self.rollback_runtime))
        object.__setattr__(self, "display_only", True)
        object.__setattr__(self, "would_execute", False)
        object.__setattr__(self, "dry_run_only", True)
        object.__setattr__(self, "enforces_runtime", False)

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "baseline_id": self.baseline_id,
            "recorded_at": self.recorded_at,
            "source": self.source,
            "runtime_path": self.runtime_path,
            "head": self.head,
            "rollback_runtime_path": self.rollback_runtime_path,
            "rollback_head": self.rollback_head,
            "dispatch_in_gateway": self.dispatch_in_gateway,
            "active_kanban": self.active_kanban,
            "max_active_lane": self.max_active_lane,
            "max_read_only_lanes": self.max_read_only_lanes,
            "max_mutation_lanes": self.max_mutation_lanes,
            "issue": self.issue,
            "display_only": True,
            "would_execute": False,
            "dry_run_only": True,
            "enforces_runtime": False,
        }
        if self.source_runtime:
            payload["source_runtime"] = self.source_runtime
        if self.dashboard_runtime:
            payload["dashboard_runtime"] = self.dashboard_runtime
        if self.gateway_runtime:
            payload["gateway_runtime"] = self.gateway_runtime
        if self.rollback_runtime:
            payload["rollback_runtime"] = self.rollback_runtime
        return payload

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AcceptedBaselineRecord:
        return cls(
            baseline_id=data.get("baseline_id", ""),
            recorded_at=data.get("recorded_at", ""),
            source=data.get("source", ""),
            runtime_path=data.get("runtime_path", ""),
            head=data.get("head", ""),
            rollback_runtime_path=data.get("rollback_runtime_path", ""),
            rollback_head=data.get("rollback_head", ""),
            dispatch_in_gateway=data.get("dispatch_in_gateway") is True,
            active_kanban=data.get("active_kanban", 0),
            max_active_lane=data.get("max_active_lane", 1),
            max_read_only_lanes=data.get("max_read_only_lanes", 2),
            max_mutation_lanes=data.get("max_mutation_lanes", 1),
            issue=data.get("issue", ""),
            source_runtime=data.get("source_runtime") or {},
            dashboard_runtime=data.get("dashboard_runtime") or {},
            gateway_runtime=data.get("gateway_runtime") or {},
            rollback_runtime=data.get("rollback_runtime") or {},
            display_only=True,
            would_execute=False,
            dry_run_only=True,
            enforces_runtime=False,
        )


@dataclass(frozen=True)
class OperatingWorkspaceHandoffRecord:
    handoff_id: str = ""
    created_at: str = ""
    source: str = ""
    active_lane: str = ""
    lane_mode: str = ""
    accepted_runtime_path: str = ""
    accepted_head: str = ""
    rollback_runtime_path: str = ""
    rollback_head: str = ""
    dispatch_in_gateway: bool = False
    max_active_lane: int = 1
    active_lane_count: int = 0
    target_type: str = ""
    target_id: str = ""
    target_head: str = ""
    status: str = ""
    last_result: str = ""
    next_action: str = ""
    warnings: tuple[str, ...] = ()
    would_execute: bool = False
    dry_run_only: bool = True
    enforces_runtime: bool = False
    display_only: bool = True

    record_type: ClassVar[str] = "OperatingWorkspaceHandoffRecord"

    def __post_init__(self) -> None:
        object.__setattr__(self, "handoff_id", _bounded_handoff_text(self.handoff_id))
        object.__setattr__(self, "created_at", _bounded_handoff_text(self.created_at))
        object.__setattr__(self, "source", _bounded_handoff_text(self.source))
        object.__setattr__(self, "active_lane", _bounded_handoff_text(self.active_lane))
        object.__setattr__(self, "lane_mode", _bounded_handoff_text(self.lane_mode))
        object.__setattr__(self, "accepted_runtime_path", _bounded_handoff_text(self.accepted_runtime_path, _MAX_HANDOFF_PATH_CHARS))
        object.__setattr__(self, "accepted_head", _normalize_packet_sha(self.accepted_head))
        object.__setattr__(self, "rollback_runtime_path", _bounded_handoff_text(self.rollback_runtime_path, _MAX_HANDOFF_PATH_CHARS))
        object.__setattr__(self, "rollback_head", _normalize_packet_sha(self.rollback_head))
        object.__setattr__(self, "dispatch_in_gateway", self.dispatch_in_gateway is True)
        object.__setattr__(self, "max_active_lane", _bounded_handoff_int(self.max_active_lane, default=1) or 1)
        object.__setattr__(self, "active_lane_count", _bounded_handoff_int(self.active_lane_count, default=0))
        object.__setattr__(self, "target_type", _bounded_handoff_text(self.target_type))
        object.__setattr__(self, "target_id", _bounded_handoff_text(self.target_id))
        object.__setattr__(self, "target_head", _normalize_packet_sha(self.target_head))
        object.__setattr__(self, "status", _bounded_handoff_text(self.status))
        object.__setattr__(self, "last_result", _bounded_handoff_text(self.last_result))
        object.__setattr__(self, "next_action", _bounded_handoff_text(self.next_action))
        object.__setattr__(self, "warnings", _bounded_handoff_warnings(self.warnings))
        object.__setattr__(self, "would_execute", False)
        object.__setattr__(self, "dry_run_only", True)
        object.__setattr__(self, "enforces_runtime", False)
        object.__setattr__(self, "display_only", True)

    def to_dict(self) -> dict[str, Any]:
        return {
            "handoff_id": self.handoff_id,
            "created_at": self.created_at,
            "source": self.source,
            "active_lane": self.active_lane,
            "lane_mode": self.lane_mode,
            "accepted_runtime_path": self.accepted_runtime_path,
            "accepted_head": self.accepted_head,
            "rollback_runtime_path": self.rollback_runtime_path,
            "rollback_head": self.rollback_head,
            "dispatch_in_gateway": self.dispatch_in_gateway,
            "max_active_lane": self.max_active_lane,
            "active_lane_count": self.active_lane_count,
            "target_type": self.target_type,
            "target_id": self.target_id,
            "target_head": self.target_head,
            "status": self.status,
            "last_result": self.last_result,
            "next_action": self.next_action,
            "warnings": list(self.warnings),
            "would_execute": False,
            "dry_run_only": True,
            "enforces_runtime": False,
            "display_only": True,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> OperatingWorkspaceHandoffRecord:
        return cls(
            handoff_id=data.get("handoff_id", ""),
            created_at=data.get("created_at", ""),
            source=data.get("source", ""),
            active_lane=data.get("active_lane", ""),
            lane_mode=data.get("lane_mode", ""),
            accepted_runtime_path=data.get("accepted_runtime_path", ""),
            accepted_head=data.get("accepted_head", ""),
            rollback_runtime_path=data.get("rollback_runtime_path", ""),
            rollback_head=data.get("rollback_head", ""),
            dispatch_in_gateway=data.get("dispatch_in_gateway") is True,
            max_active_lane=data.get("max_active_lane", 1),
            active_lane_count=data.get("active_lane_count", 0),
            target_type=data.get("target_type", ""),
            target_id=data.get("target_id", ""),
            target_head=data.get("target_head", ""),
            status=data.get("status", ""),
            last_result=data.get("last_result", ""),
            next_action=data.get("next_action", ""),
            warnings=data.get("warnings") or (),
            would_execute=False,
            dry_run_only=True,
            enforces_runtime=False,
            display_only=True,
        )


RECORD_TYPES = {
    cls.record_type: cls
    for cls in (
        AcceptedBaselineRecord,
        ApprovalRecord,
        ApprovalSlice,
        ChildRunRecord,
        PrMergeApprovalRecord,
        ArtifactRef,
        ChallengeReviewRecord,
        EvidenceCard,
        GoalContract,
        ProjectRecord,
        RoomContractRecord,
        RoomJournalEventRecord,
        ProjectBriefRecord,
        LaneRequestRecord,
        JennyReportRecord,
        GitHubBridgeMailboxStatusRecord,
        GitHubBridgeMessageRecord,
        JennyBridgeMessageRequestRecord,
        JennyBridgeMessageResponseRecord,
        JennyBridgePollerStatusRecord,
        JennyReplyReviewRecord,
        ReportRecord,
        RunRecord,
        SessionProjectLinkRecord,
        MissionBrief,
        OperatingWorkspaceHandoffRecord,
        OperatorAction,
        StartGateCheck,
        TaskControlEnvelope,
        VerifierWorkflowEvidenceRecord,
        WorkerNodeRunRecord,
    )
}
