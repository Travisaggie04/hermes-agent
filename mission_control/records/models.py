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
    approval_id: str
    lane: str
    mode: str
    approved_actions: tuple[str, ...] = ()
    forbidden_actions: tuple[str, ...] = ()
    approver: str = ""
    approved_at: str = ""
    expires_at: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    record_type: ClassVar[str] = "ApprovalSlice"

    def __post_init__(self) -> None:
        object.__setattr__(self, "approved_actions", _tuple(self.approved_actions))
        object.__setattr__(self, "forbidden_actions", _tuple(self.forbidden_actions))
        object.__setattr__(self, "metadata", _dict(self.metadata))

    def to_dict(self) -> dict[str, Any]:
        return {
            "approval_id": self.approval_id,
            "lane": self.lane,
            "mode": self.mode,
            "approved_actions": list(self.approved_actions),
            "forbidden_actions": list(self.forbidden_actions),
            "approver": self.approver,
            "approved_at": self.approved_at,
            "expires_at": self.expires_at,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ApprovalSlice:
        return cls(
            approval_id=_required(data, "approval_id"),
            lane=_required(data, "lane"),
            mode=_required(data, "mode"),
            approved_actions=data.get("approved_actions") or (),
            forbidden_actions=data.get("forbidden_actions") or (),
            approver=data.get("approver", ""),
            approved_at=data.get("approved_at", ""),
            expires_at=data.get("expires_at"),
            metadata=data.get("metadata") or {},
        )


@dataclass(frozen=True)
class EvidenceCard:
    evidence_id: str
    summary: str
    artifact_refs: tuple[ArtifactRef, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)

    record_type: ClassVar[str] = "EvidenceCard"

    def __post_init__(self) -> None:
        refs = tuple(
            item if isinstance(item, ArtifactRef) else ArtifactRef.from_dict(item)
            for item in self.artifact_refs
        )
        object.__setattr__(self, "artifact_refs", refs)
        object.__setattr__(self, "metadata", _dict(self.metadata))

    def to_dict(self) -> dict[str, Any]:
        return {
            "evidence_id": self.evidence_id,
            "summary": self.summary,
            "artifact_refs": [artifact.to_dict() for artifact in self.artifact_refs],
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> EvidenceCard:
        return cls(
            evidence_id=_required(data, "evidence_id"),
            summary=_required(data, "summary"),
            artifact_refs=tuple(ArtifactRef.from_dict(item) for item in data.get("artifact_refs") or ()),
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
        TaskControlEnvelope,
    )
}
