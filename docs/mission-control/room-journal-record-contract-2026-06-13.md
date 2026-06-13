# Mission Control Room And Journal Record Contract - 2026-06-13

This note defines the first record-backed room contract for Mission Control.
It is intentionally inert: these records describe source-of-truth structure
and journal events, but they do not authorize execution.

## Records

### RoomContractRecord

Purpose:

- define one project room's durable source-of-truth paths,
- make allowed actions, forbidden actions, and stop conditions visible,
- keep room state reconstructable without relying on chat history.

Required fields:

- `room_id`
- `project_id`
- `title`

Important optional fields:

- `brief_path`
- `facts_path`
- `specs_path`
- `decisions_path`
- `reports_path`
- `mailbox_path`
- `journal_path`
- `allowed_actions`
- `forbidden_actions`
- `stop_conditions`

### RoomJournalEventRecord

Purpose:

- append an auditable event when a room state changes,
- link state changes to artifact paths or prior events,
- keep current room state derivable from journal history.

Required fields:

- `event_id`
- `room_id`
- `project_id`
- `event_type`
- `summary`

Important optional fields:

- `event_time`
- `actor`
- `source`
- `artifact_refs`
- `parent_event_ids`

Forced inert flags:

- `append_only: true`
- `trusted_for_execution: false`

## Safety Boundary

These records are not approvals, lane requests, dispatch instructions, or
runtime switches. A bridge message or journal event becomes executable only
after it is converted into the normal lane/request/approval records and passes
the challenge and policy gates.

## Next Work

The next safe PR should add a read-only Mission Control projection that shows:

- room contract path completeness,
- latest journal event,
- missing facts/specs/decision/report paths,
- whether the current lane has challenge and report-contract evidence.
