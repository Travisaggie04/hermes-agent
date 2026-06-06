"""Pure value objects for inert Mission Control governance records."""

from __future__ import annotations

from dataclasses import dataclass, field
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
    active_lane: str
    mode: str
    allowed_actions: tuple[str, ...] = ()
    forbidden_actions: tuple[str, ...] = ()
    current_repo: str = ""
    expected_systems_files: tuple[str, ...] = ()
    stop_condition: str = ""
    other_threads_excluded: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)

    record_type: ClassVar[str] = "TaskControlEnvelope"

    def __post_init__(self) -> None:
        object.__setattr__(self, "allowed_actions", _tuple(self.allowed_actions))
        object.__setattr__(self, "forbidden_actions", _tuple(self.forbidden_actions))
        object.__setattr__(self, "expected_systems_files", _tuple(self.expected_systems_files))
        object.__setattr__(self, "other_threads_excluded", _tuple(self.other_threads_excluded))
        object.__setattr__(self, "metadata", _dict(self.metadata))

    def to_dict(self) -> dict[str, Any]:
        return {
            "active_lane": self.active_lane,
            "mode": self.mode,
            "allowed_actions": list(self.allowed_actions),
            "forbidden_actions": list(self.forbidden_actions),
            "current_repo": self.current_repo,
            "expected_systems_files": list(self.expected_systems_files),
            "stop_condition": self.stop_condition,
            "other_threads_excluded": list(self.other_threads_excluded),
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TaskControlEnvelope:
        return cls(
            active_lane=_required(data, "active_lane"),
            mode=_required(data, "mode"),
            allowed_actions=data.get("allowed_actions") or (),
            forbidden_actions=data.get("forbidden_actions") or (),
            current_repo=data.get("current_repo", ""),
            expected_systems_files=data.get("expected_systems_files") or (),
            stop_condition=data.get("stop_condition", ""),
            other_threads_excluded=data.get("other_threads_excluded") or (),
            metadata=data.get("metadata") or {},
        )


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
        ArtifactRef,
        EvidenceCard,
        GoalContract,
        MissionBrief,
        OperatorAction,
        TaskControlEnvelope,
    )
}
