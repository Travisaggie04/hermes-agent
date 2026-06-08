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


RECORD_TYPES = {
    cls.record_type: cls
    for cls in (
        ApprovalSlice,
        PrMergeApprovalRecord,
        ArtifactRef,
        EvidenceCard,
        GoalContract,
        MissionBrief,
        OperatorAction,
        StartGateCheck,
        TaskControlEnvelope,
        VerifierWorkflowEvidenceRecord,
    )
}
