import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

const getMissionControlWorkspaceStatus = vi.fn()
const getMissionControlProjects = vi.fn()
const getMissionControlProjectBriefs = vi.fn()
const getMissionControlChallengeReviews = vi.fn()
const getMissionControlJennyBridgeInbox = vi.fn()
const getMissionControlJennyBridgeOutbox = vi.fn()
const getMissionControlJennyBridgePollerStatus = vi.fn()
const getMissionControlJennyReplyReviews = vi.fn()
const getMissionControlGitHubBridgeStatus = vi.fn()
const getMissionControlLaneRequests = vi.fn()
const getMissionControlProfileMemoryStorage = vi.fn()
const getMissionControlReports = vi.fn()
const getMissionControlProjectState = vi.fn()
const getMissionControlProjectSessions = vi.fn()
const createMissionControlChallengeReview = vi.fn()
const createMissionControlGitHubBridgeRequest = vi.fn()
const createMissionControlJennyReplyReview = vi.fn()
const answerMissionControlGitHubBridgeOnce = vi.fn()
const createMissionControlJennyBridgeRequest = vi.fn()
const createMissionControlLaneRequest = vi.fn()
const createMissionControlReport = vi.fn()
const createMissionControlSessionProjectLink = vi.fn()

vi.mock('@/hermes', () => ({
  answerMissionControlGitHubBridgeOnce: (payload: unknown) => answerMissionControlGitHubBridgeOnce(payload),
  createMissionControlChallengeReview: (payload: unknown) => createMissionControlChallengeReview(payload),
  createMissionControlGitHubBridgeRequest: (payload: unknown) => createMissionControlGitHubBridgeRequest(payload),
  createMissionControlJennyReplyReview: (payload: unknown) => createMissionControlJennyReplyReview(payload),
  createMissionControlJennyBridgeRequest: (payload: unknown) => createMissionControlJennyBridgeRequest(payload),
  createMissionControlLaneRequest: (payload: unknown) => createMissionControlLaneRequest(payload),
  createMissionControlReport: (payload: unknown) => createMissionControlReport(payload),
  createMissionControlSessionProjectLink: (payload: unknown) => createMissionControlSessionProjectLink(payload),
  getMissionControlChallengeReviews: () => getMissionControlChallengeReviews(),
  getMissionControlJennyBridgeInbox: () => getMissionControlJennyBridgeInbox(),
  getMissionControlJennyBridgeOutbox: () => getMissionControlJennyBridgeOutbox(),
  getMissionControlJennyBridgePollerStatus: () => getMissionControlJennyBridgePollerStatus(),
  getMissionControlJennyReplyReviews: () => getMissionControlJennyReplyReviews(),
  getMissionControlGitHubBridgeStatus: () => getMissionControlGitHubBridgeStatus(),
  getMissionControlWorkspaceStatus: () => getMissionControlWorkspaceStatus(),
  getMissionControlProjectBriefs: () => getMissionControlProjectBriefs(),
  getMissionControlProjects: () => getMissionControlProjects(),
  getMissionControlLaneRequests: () => getMissionControlLaneRequests(),
  getMissionControlProfileMemoryStorage: () => getMissionControlProfileMemoryStorage(),
  getMissionControlReports: () => getMissionControlReports(),
  getMissionControlProjectState: () => getMissionControlProjectState(),
  getMissionControlProjectSessions: () => getMissionControlProjectSessions()
}))

const realProjects = [
  ['project-hermes-mission-control', 'Hermes / Mission Control'],
  ['project-long-form-video', 'Long-form Video'],
  ['project-shorts-video', 'Shorts Video'],
  ['project-tool-tally', 'Tool & Tally'],
  ['project-waha-work', 'Waha Work']
] as const

function renderMissionControl() {
  return import('./index').then(({ MissionControlView }) =>
    render(
      <MemoryRouter initialEntries={['/mission-control']}>
        <MissionControlView />
      </MemoryRouter>
    )
  )
}

function statusItemValue(label: string): HTMLElement {
  const value = screen.getByText(label).nextElementSibling
  expect(value).toBeTruthy()

  return value as HTMLElement
}

beforeEach(() => {
  Object.assign(navigator, {
    clipboard: {
      writeText: vi.fn().mockResolvedValue(undefined)
    }
  })

  getMissionControlWorkspaceStatus.mockResolvedValue({
    accepted_baseline: {
      head: '9f8863c0bf28dc0b7da702480b9b3337b983e7e8',
      runtime_path: '/home/jenny/.hermes/hermes-runtime-project-seed-9f8863c',
      would_execute: false
    },
    approval_lifecycle: {
      append_only_projection: true,
      available_approval_ids: ['approval-live'],
      blocked: true,
      blocked_reasons: ['run_id run-parent-1 references unavailable approval_id approval-old'],
      consumed_approval_ids: [],
      dispatch_enabled: false,
      display_only: true,
      duplicate_approval_ids: [],
      execution_enabled: false,
      expired_approval_ids: ['approval-old'],
      pending_approval_ids: ['approval-pending'],
      rejected_or_cancelled_approval_ids: [],
      runs_missing_approval_id: [],
      runs_with_missing_approval_record: {},
      runs_with_unavailable_approval: { 'run-parent-1': 'approval-old' },
      session_send_enabled: false,
      trusted_for_execution: false,
      worker_dispatch_enabled: false
    },
    child_agent_orchestration: {
      active_count: 1,
      active_runs: [
        {
          agent_identity: 'jenny-child',
          child_run_id: 'child-run-1',
          linked_report_review_status: 'needs_review',
          linked_report_status: 'received',
          linked_report_summary: 'Child reported evidence.',
          objective: 'Inspect bounded Mission Control context.',
          parent_run_id: 'run-parent-1',
          report_id: 'report-child',
          report_link_status: 'linked_report_found',
          status: 'running'
        }
      ],
      blocked_reasons: ['report_id report-child still needs review'],
      dispatch_enabled: false,
      display_only: true,
      execution_enabled: false,
      trusted_for_execution: false,
      worker_dispatch_enabled: false
    },
    child_agent_instruction_preview: {
      agent_identity: 'jenny-child',
      allowed_actions: ['read approved context', 'report evidence'],
      available: true,
      blocked: true,
      blocked_reasons: ['report_id report-child still needs review'],
      child_run_id: 'child-run-1',
      dispatch_enabled: false,
      display_only: true,
      dry_run_only: true,
      execution_enabled: false,
      forbidden_actions: ['dispatch', 'mutate records', 'no live delegation activation', 'no live session sending'],
      instruction_lines: [
        'Child agent: jenny-child.',
        'Objective: Inspect bounded Mission Control context.',
        'Allowed actions: read approved context, report evidence.',
        'Forbidden actions: dispatch, mutate records, no live delegation activation, no live session sending.',
        'Report contract: Report evidence, result, blockers, safety confirmation, and the next suggested review step.',
        'Handoff readiness: blocked until child-agent blockers are cleared.',
        'Manual delegation preview only; execution and dispatch remain disabled.'
      ],
      manual_handoff_only: true,
      manual_handoff_prompt: 'Child agent: jenny-child.\nObjective: Inspect bounded Mission Control context.\nAllowed actions: read approved context, report evidence.\nForbidden actions: dispatch, mutate records, no live delegation activation, no live session sending.\nReport contract: Report evidence, result, blockers, safety confirmation, and the next suggested review step.\nHandoff readiness: blocked until child-agent blockers are cleared.\nManual delegation preview only; execution and dispatch remain disabled.',
      objective: 'Inspect bounded Mission Control context.',
      parent_run_id: 'run-parent-1',
      ready_for_handoff: false,
      report_contract: 'Report evidence, result, blockers, safety confirmation, and the next suggested review step.',
      report_id: 'report-child',
      report_review_status: 'needs_review',
      session_send_enabled: false,
      source: 'mission_control_child_agent_instruction_preview_v1',
      stored: false,
      trusted_for_execution: false,
      worker_dispatch_enabled: false,
      would_execute: false
    },
    control_plane_lifecycle: {
      active_mutation_lane_count: 0,
      append_only_projection: true,
      latest_runs_by_id: {
        'run-parent-1': { run_id: 'run-parent-1', status: 'running' }
      },
      source: 'mission_control_records_jsonl'
    },
    deployment_gap: {
      accepted_live_head: '0f87620038d220eb016612ba0b466c2407663743',
      dashboard_deploy_needed: true,
      deployed_head: '9f8863c0bf28dc0b7da702480b9b3337b983e7e8',
      latest_merged_pr: '108',
      state: 'merged_not_deployed'
    },
    execution_mode_classification: {
      action_class: 'pr_creation',
      blocked: false,
      blocked_reasons: [],
      dispatch_enabled: false,
      display_only: true,
      dry_run_only: true,
      execution_enabled: false,
      higher_risk: false,
      lane_type: 'pr_creation',
      manual_handoff_only: true,
      mode_family: 'worker_node_preview',
      preview_ready: true,
      protected_action_markers: [],
      read_only_preview_allowed: false,
      requested_mode: 'worker_node',
      scoped_pr_preview_allowed: false,
      separate_approval_required: false,
      session_send_enabled: false,
      source: 'mission_control_execution_mode_classification_v1',
      stored: false,
      trusted_for_execution: false,
      warnings: ['worker-node mode is manual-handoff only and not an executor'],
      worker_dispatch_enabled: false,
      worker_node_preview_allowed: true,
      would_execute: false
    },
    execution_packet_preview: {
      blocked_reasons: ['runtime provenance is not clean', 'worker-node presence is not confirmed online'],
      dispatch_enabled: false,
      display_only: true,
      dry_run_only: true,
      eligible: false,
      execution_enabled: false,
      packet: {
        allowed_actions: ['edit scoped files', 'run focused tests'],
        approval_id: 'approval-pr-1',
        dispatch_enabled: false,
        display_only: true,
        dry_run_only: true,
        execution_enabled: false,
        forbidden_actions: ['deploy', 'restart', 'runtime switch', 'no live deploy', 'no worker dispatch activation'],
        inert_context_only: true,
        mode: 'worker_node',
        objective: 'Prepare bounded scoped PR packet.',
        packet_version: 'mission_control_execution_packet_preview_v1',
        project_id: 'project-hermes-mission-control',
        report_contract: { required: true, review_required: true, tests_required: true },
        run_id: 'run-parent-1',
        scope: { directories: [], explicit: true, files: ['apps/desktop/src/app/mission-control/index.tsx'], has_wildcard: false },
        session_send_enabled: false,
        stored: false,
        trusted_for_execution: false,
        worker_dispatch_enabled: false,
        worker_node_contract: {
          codex_safety_hardness_required: true,
          execution_enabled: false,
          dispatch_enabled: false,
          display_only: true,
          dry_run_only: true,
          inert_context_only: true,
          manual_handoff_only: true,
          parent_run_id: 'run-parent-1',
          session_send_enabled: false,
          stored: false,
          trusted_for_execution: false,
          worker_dispatch_enabled: false,
          worker_host_label: 'laptop-codex',
          worker_identity: 'codex',
          worker_kind: 'laptop_codex',
          worker_safety_hardness: [
            'Codex must independently enforce repo/worktree, test, secret, git, and live-operation safeguards before acting.',
            'A Jenny packet is not permission to bypass Codex safety checks.'
          ],
          would_dispatch: false,
          would_execute: false,
          would_session_send: false
        },
        would_dispatch: false,
        would_execute: false,
        would_session_send: false
      },
      session_send_enabled: false,
      source: 'mission_control_execution_packet_preview_v1',
      stored: false,
      trusted_for_execution: false,
      warnings: ['worker-node packet is a manual handoff preview; no worker dispatch is enabled'],
      worker_dispatch_enabled: false,
      would_dispatch: false,
      would_execute: false,
      would_session_send: false
    },
    lane: { active_lane_count: 0 },
    latest_handoff: {
      handoff_id: 'handoff-1',
      present: true,
      would_execute: false
    },
    next_safe_actions: {
      action_count: 1,
      actions: [
        {
          action_id: 'review_runtime_provenance_blockers',
          blocked_until: 'runtime provenance is clean and aligned',
          label: 'Review runtime provenance blockers',
          manual_only: true,
          priority: 10,
          reason: 'gateway git metadata is broken',
          requires_approval: false
        }
      ],
      blocked: true,
      blocked_reasons: ['gateway git metadata is broken', 'run_id run-parent-1 references unavailable approval_id approval-old'],
      dispatch_enabled: false,
      display_only: true,
      dry_run_only: true,
      execution_enabled: false,
      primary_action: {
        action_id: 'review_runtime_provenance_blockers',
        blocked_until: 'runtime provenance is clean and aligned',
        label: 'Review runtime provenance blockers',
        manual_only: true,
        priority: 10,
        reason: 'gateway git metadata is broken',
        requires_approval: false
      },
      primary_action_id: 'review_runtime_provenance_blockers',
      primary_action_label: 'Review runtime provenance blockers',
      session_send_enabled: false,
      source: 'mission_control_next_safe_actions_v1',
      stored: false,
      trusted_for_execution: false,
      worker_dispatch_enabled: false,
      would_execute: false
    },
    operator_decision_packet: {
      approval_required: true,
      blocked: true,
      blocked_reasons: [
        'gateway git metadata is broken',
        'report_id report-worker has multiple append-only records',
        'report_id report-worker attempts to overwrite append-only report fields: status',
        'report_id report-worker still needs Jenny review',
        'worker node offline',
        'worker-node presence_status is not recorded',
        'runtime provenance is not clean',
        'worker-node presence is not confirmed online',
        'report_id report-worker missing contract fields: result, evidence, tests, next lane, safety confirmation',
        'run run-stopped has no stop_reason',
        'run run-stopped has no linked stop/cancel report'
      ],
      child_instruction_available: true,
      child_instruction_ready_for_handoff: false,
      dispatch_enabled: false,
      display_only: true,
      dry_run_only: true,
      execution_mode_blocked_reasons: [],
      execution_mode_family: 'worker_node_preview',
      execution_packet_blocked_reasons: ['runtime provenance is not clean', 'worker-node presence is not confirmed online'],
      execution_packet_eligible: false,
      execution_packet_mode: 'worker_node',
      execution_lock_blocked_reasons: [],
      execution_enabled: false,
      execution_ready: false,
      jenny_review_required: true,
      manual_operator_review_only: true,
      next_safe_action_id: 'review_runtime_provenance_blockers',
      next_safe_action_label: 'Review runtime provenance blockers',
      next_safe_action_reason: 'gateway git metadata is broken',
      plain_language_summary: 'Operator state: report review required. Approval required: yes. Runtime provenance: GATEWAY_UNTRUSTED. Readiness: read-only blocked, scoped PR blocked, laptop Codex blocked. Worker presence: unknown. Execution mode: worker_node_preview; execution disabled. Execution packet preview: worker_node, eligible false; execution disabled. Next safe action: Review runtime provenance blockers. Top report review: Laptop Codex reported scoped PR evidence. because report_id report-worker still needs Jenny review. Report overwrite conflicts: 1; duplicate report IDs are quarantined. Result ingestion: 1 ready, 0 blocked. Report contract completeness: 0 complete, 1 incomplete. Report completion path: 0 ready, 2 blocked. Stop/cancel control: 1 item, blocked true. Worker instruction: preview available but blocked; laptop Codex dispatch remains disabled. Child instruction: preview available but blocked; execution remains disabled. Hard locks: no deploy, restart, runtime switch, record/state/config mutation, secrets, live dispatch, session sending, or worker activation.',
      recommended_operator_instruction: 'Jenny reviews Laptop Codex reported scoped PR evidence. before issuing another worker instruction.',
      report_contract_blocked_reasons: ['report_id report-worker missing contract fields: result, evidence, tests, next lane, safety confirmation'],
      report_contract_incomplete_count: 1,
      report_contract_primary_item_id: 'report-contract:report-worker',
      report_completion_blocked_count: 2,
      report_completion_blocked_reasons: [
        'run run-parent-1 has no linked completion report',
        'report_id report-worker still needs Jenny review before completion',
        'report_id report-worker missing completion contract fields: result, evidence, tests, next lane, safety confirmation'
      ],
      report_completion_link_mismatch_count: 0,
      report_completion_primary_item_id: 'report-completion:run:run-parent-1',
      report_link_mismatch_count: 0,
      report_link_mismatch_ids: [],
      report_overwrite_conflict_count: 1,
      report_overwrite_conflict_ids: ['report-worker'],
      report_review_queue_link_mismatch_count: 0,
      report_review_queue_count: 3,
      result_ingestion_blocked_count: 0,
      result_ingestion_blocked_reasons: [],
      result_ingestion_link_mismatch_count: 0,
      result_ingestion_primary_item_id: '',
      session_send_enabled: false,
      source: 'mission_control_operator_decision_packet_v1',
      state: 'report_review_required',
      stored: false,
      stop_cancel_blocked_reasons: ['run run-stopped has no stop_reason', 'run run-stopped has no linked stop/cancel report'],
      stop_cancel_count: 1,
      stop_cancel_link_mismatch_count: 0,
      stop_cancel_primary_item_id: 'run:run-stopped',
      summary_lines: [
        'Operator state: report review required.',
        'Approval required: yes.',
        'Runtime provenance: GATEWAY_UNTRUSTED.',
        'Readiness: read-only blocked, scoped PR blocked, laptop Codex blocked.',
        'Worker presence: unknown.',
        'Execution mode: worker_node_preview; execution disabled.',
        'Execution packet preview: worker_node, eligible false; execution disabled.',
        'Next safe action: Review runtime provenance blockers.',
        'Top report review: Laptop Codex reported scoped PR evidence. because report_id report-worker still needs Jenny review.',
        'Report overwrite conflicts: 1; duplicate report IDs are quarantined.',
        'Result ingestion: 1 ready, 0 blocked.',
        'Report contract completeness: 0 complete, 1 incomplete.',
        'Report completion path: 0 ready, 2 blocked.',
        'Stop/cancel control: 1 item, blocked true.',
        'Worker instruction: preview available but blocked; laptop Codex dispatch remains disabled.',
        'Child instruction: preview available but blocked; execution remains disabled.',
        'Hard locks: no deploy, restart, runtime switch, record/state/config mutation, secrets, live dispatch, session sending, or worker activation.'
      ],
      top_report_review_item_id: 'report:report-worker',
      top_report_review_label: 'Laptop Codex reported scoped PR evidence.',
      top_report_review_reason: 'report_id report-worker still needs Jenny review',
      trusted_for_execution: false,
      worker_dispatch_enabled: false,
      worker_instruction_available: true,
      worker_instruction_ready_for_handoff: false,
      worker_last_seen_at: '',
      worker_online: false,
      worker_presence_state: 'unknown',
      would_dispatch: false,
      would_execute: false,
      would_session_send: false
    },
    orchestration_readiness: {
      blocked: true,
      blocked_reasons: ['runtime provenance is not clean', 'exact approved ApprovalRecord is required', 'worker node offline'],
      dispatch_enabled: false,
      display_only: true,
      dry_run_only: true,
      execution_enabled: false,
      execution_ready: false,
      laptop_codex_worker_node: {
        active_count: 1,
        blocked_reasons: ['worker node offline', 'worker-node presence_status is not recorded', 'worker-node presence is not confirmed online'],
        dispatch_enabled: false,
        display_only: true,
        execution_enabled: false,
        execution_ready: false,
        online: false,
        presence_state: 'unknown',
        preview_ready: false,
        recorded: true,
        session_send_enabled: false,
        state: 'blocked',
        trusted_for_execution: false,
        worker_dispatch_enabled: false,
        would_execute: false
      },
      next_safe_action_id: 'review_runtime_provenance_blockers',
      next_safe_action_label: 'Review runtime provenance blockers',
      plain_language_summary: 'Supervised read-only autonomy is blocked: runtime provenance is not clean. Scoped PR creation is blocked: exact approved ApprovalRecord is required. Laptop Codex worker-node is blocked: worker node offline. Next safe action: Review runtime provenance blockers.',
      scoped_pr_creation: {
        blocked_reasons: ['exact approved ApprovalRecord is required'],
        dispatch_enabled: false,
        display_only: true,
        eligible: false,
        execution_enabled: false,
        execution_ready: false,
        preview_ready: false,
        session_send_enabled: false,
        state: 'blocked',
        trusted_for_execution: false,
        worker_dispatch_enabled: false,
        would_execute: false
      },
      session_send_enabled: false,
      source: 'mission_control_orchestration_readiness_v1',
      states: {
        laptop_codex_worker_node: 'blocked',
        scoped_pr_creation: 'blocked',
        supervised_read_only_autonomy: 'blocked'
      },
      stored: false,
      summary_lines: [
        'Supervised read-only autonomy is blocked: runtime provenance is not clean.',
        'Scoped PR creation is blocked: exact approved ApprovalRecord is required.',
        'Laptop Codex worker-node is blocked: worker node offline.',
        'Next safe action: Review runtime provenance blockers.'
      ],
      supervised_read_only_autonomy: {
        blocked_reasons: ['runtime provenance is not clean'],
        dispatch_enabled: false,
        display_only: true,
        eligible: false,
        execution_enabled: false,
        execution_ready: false,
        preview_ready: false,
        session_send_enabled: false,
        state: 'blocked',
        trusted_for_execution: false,
        worker_dispatch_enabled: false,
        would_execute: false
      },
      trusted_for_execution: false,
      worker_dispatch_enabled: false,
      would_execute: false
    },
    orchestration_run_graph: {
      blocked: true,
      blocked_reasons: ['worker_run_id worker-run-1 references missing parent run_id run-parent-1'],
      child_run_node_count: 1,
      dispatch_enabled: false,
      display_only: true,
      dry_run_only: true,
      edge_count: 3,
      edges: [
        { edge_type: 'child_run', source_id: 'run-parent-1', target_id: 'child-run-1' },
        { edge_type: 'linked_report', source_id: 'worker-run-1', target_id: 'report-worker' },
        { edge_type: 'produced_report', source_id: 'worker-run-1', target_id: 'report-worker' }
      ],
      execution_enabled: false,
      node_count: 4,
      nodes: [
        { label: 'Parent run', node_id: 'run-parent-1', node_type: 'run', status: 'running' },
        { label: 'Inspect bounded Mission Control context.', node_id: 'child-run-1', node_type: 'child_run', parent_run_id: 'run-parent-1', report_id: 'report-child', report_review_status: 'needs_review', status: 'running' },
        { label: 'Prepare bounded scoped PR packet.', node_id: 'worker-run-1', node_type: 'worker_node_run', parent_run_id: 'run-parent-1', report_id: 'report-worker', report_review_status: 'accepted', status: 'blocked' },
        { label: 'Worker node reported evidence.', node_id: 'report-worker', node_type: 'report', parent_run_id: 'worker-run-1', report_id: 'report-worker', report_review_status: 'accepted', status: 'accepted' }
      ],
      report_node_count: 1,
      run_node_count: 1,
      session_send_enabled: false,
      source: 'mission_control_orchestration_run_graph_v1',
      stored: false,
      trusted_for_execution: false,
      worker_dispatch_enabled: false,
      worker_node_run_count: 1,
      would_execute: false
    },
    read_only_autonomy_eligibility: {
      blocked_reasons: ['runtime provenance is not clean', 'gateway git metadata is broken'],
      bridge_permissions: {
        permission_classification: 'write_capable',
        read_only_safe: false
      },
      dispatch_enabled: false,
      dry_run_only: true,
      eligible: false,
      execution_enabled: false,
      session_send_enabled: false,
      would_execute: false
    },
    scoped_pr_lane_eligibility: {
      blocked_reasons: ['exact approved ApprovalRecord is required'],
      bridge_permissions: {
        permission_classification: 'manual_only',
        read_only_safe: false
      },
      dispatch_enabled: false,
      dry_run_only: true,
      eligible: false,
      execution_enabled: false,
      merge_enabled: false,
      scope: { directories: [], files: [] },
      session_send_enabled: false,
      worker_dispatch_enabled: false,
      would_commit: false,
      would_create_pr: false,
      would_execute: false
    },
    runtime_provenance: {
      autonomy_blocked: true,
      autonomy_blocked_reasons: ['gateway git metadata is broken'],
      default_branch_head: 'c06898098b865b5a8f48535c08ad9de5459211e4',
      primary_status: 'GATEWAY_UNTRUSTED',
      source_head: '0f87620038d220eb016612ba0b466c2407663743',
      status: 'BLOCKED_UNSAFE_FOR_AUTONOMY',
      statuses: ['BROKEN_GIT_METADATA', 'GATEWAY_UNTRUSTED']
    },
    rollback_baseline: {
      head: 'cb42bbc1ed372576079ce8162e6c66fe11872fa4',
      runtime_path: '/home/jenny/.hermes/hermes-runtime-evidencehash-cb42bbc',
      would_execute: false
    },
    runtime_worktree_guard: { decision_state: 'pass' },
    report_lifecycle: {
      append_only_projection: true,
      blocked: true,
      blocked_reasons: [
        'report_id report-worker has multiple append-only records',
        'report_id report-worker attempts to overwrite append-only report fields: status',
        'run_id run-parent-1 has no linked report',
        'report_id report-worker still needs review'
      ],
      dispatch_enabled: false,
      display_only: true,
      duplicate_report_ids: ['report-worker'],
      execution_enabled: false,
      open_report_ids: ['report-worker'],
      raw_report_count: 2,
      report_count: 1,
      report_overwrite_conflict_count: 1,
      report_overwrite_conflict_ids: ['report-worker'],
      report_overwrite_conflicts: { 'report-worker': ['status'] },
      reports_by_run_id: { 'worker-run-1': ['report-worker'] },
      reviewed_report_ids: [],
      runs_missing_report: ['run-parent-1'],
      runs_with_missing_linked_report_ids: {},
      session_send_enabled: false,
      terminal_report_ids: [],
      trusted_for_execution: false,
      worker_dispatch_enabled: false
    },
    report_contract_compliance: {
      blocked: true,
      blocked_reasons: ['report_id report-worker missing contract fields: result, evidence, tests, next lane, safety confirmation'],
      complete_report_count: 0,
      dispatch_enabled: false,
      display_only: true,
      dry_run_only: true,
      execution_enabled: false,
      incomplete_report_count: 1,
      items: [
        {
          complete: false,
          item_id: 'report-contract:report-worker',
          linked_record_id: 'worker-run-1',
          linked_record_type: 'worker_node_run',
          manual_only: true,
          missing_fields: ['result', 'evidence', 'tests', 'next lane', 'safety confirmation'],
          recommended_action: 'Jenny reviews the report contract fields before accepting the worker or child result.',
          report_id: 'report-worker',
          required_fields: ['summary', 'result', 'risks/blockers', 'evidence', 'tests', 'next lane', 'safety confirmation'],
          review_status: 'needs_review',
          run_id: 'worker-run-1',
          status: 'needs_review',
          summary: 'Laptop Codex reported scoped PR evidence.'
        }
      ],
      manual_review_only: true,
      primary_item_id: 'report-contract:report-worker',
      primary_item_label: 'Laptop Codex reported scoped PR evidence.',
      report_count: 1,
      session_send_enabled: false,
      source: 'mission_control_report_contract_compliance_v1',
      stored: false,
      trusted_for_execution: false,
      worker_dispatch_enabled: false,
      would_execute: false
    },
    report_completion_path: {
      blocked: true,
      blocked_reasons: [
        'run run-parent-1 has no linked completion report',
        'report_id report-worker still needs Jenny review before completion',
        'report_id report-worker missing completion contract fields: result, evidence, tests, next lane, safety confirmation'
      ],
      blocked_completion_count: 2,
      completion_ready_count: 0,
      contract_incomplete_count: 2,
      dispatch_enabled: false,
      display_only: true,
      dry_run_only: true,
      duplicate_report_count: 0,
      execution_enabled: false,
      ingestion_blocked_count: 0,
      items: [
        {
          blocked_reasons: ['run run-parent-1 has no linked completion report'],
          completion_ready: false,
          contract_missing_fields: [],
          duplicate_report: false,
          forbidden_metadata_keys: [],
          item_id: 'report-completion:run:run-parent-1',
          label: 'Parent run',
          manual_review_required: true,
          parent_run_id: '',
          recommended_action: 'Jenny reviews the linked report, contract fields, ingestion safety, and final run status before treating this work as complete.',
          record_id: 'run-parent-1',
          record_type: 'run',
          redaction_status: '',
          report_contract_complete: false,
          report_id: '',
          report_link_status: 'missing_linked_report',
          report_review_status: 'missing_report',
          result_ingestion_ready: false,
          safety_confirmation_present: false,
          status: 'completed'
        },
        {
          blocked_reasons: [
            'report_id report-worker still needs Jenny review before completion',
            'report_id report-worker missing completion contract fields: result, evidence, tests, next lane, safety confirmation'
          ],
          completion_ready: false,
          contract_missing_fields: ['result', 'evidence', 'tests', 'next lane', 'safety confirmation'],
          duplicate_report: false,
          forbidden_metadata_keys: [],
          item_id: 'report-completion:worker_node_run:worker-run-1',
          label: 'Prepare bounded scoped PR packet.',
          manual_review_required: true,
          parent_run_id: 'run-parent-1',
          recommended_action: 'Jenny reviews the linked report, contract fields, ingestion safety, and final run status before treating this work as complete.',
          record_id: 'worker-run-1',
          record_type: 'worker_node_run',
          redaction_status: 'operator_supplied_redacted',
          report_contract_complete: false,
          report_id: 'report-worker',
          report_link_status: 'linked_report_found',
          report_review_status: 'needs_review',
          result_ingestion_ready: true,
          safety_confirmation_present: true,
          status: 'blocked'
        }
      ],
      link_mismatch_count: 0,
      manual_review_only: true,
      missing_report_count: 1,
      needs_review_count: 1,
      primary_item_id: 'report-completion:run:run-parent-1',
      primary_item_label: 'Parent run',
      rejected_report_count: 0,
      session_send_enabled: false,
      source: 'mission_control_report_completion_path_v1',
      stored: false,
      terminal_item_count: 2,
      trusted_for_execution: false,
      worker_dispatch_enabled: false,
      would_execute: false
    },
    report_review_queue: {
      blocked: true,
      blocked_reasons: [
        'report_id report-worker still needs Jenny review',
        'report_id report-child still needs Jenny review',
        'run_id run-parent-1 has no linked report'
      ],
      dispatch_enabled: false,
      display_only: true,
      dry_run_only: true,
      duplicate_report_count: 1,
      execution_enabled: false,
      items: [
        {
          item_id: 'report:report-worker',
          item_type: 'report_needs_review',
          linked_record_id: 'worker-run-1',
          linked_record_type: 'worker_node_run',
          manual_only: true,
          priority: 10,
          reason: 'report_id report-worker still needs Jenny review',
          recommended_action: 'Jenny reviews the report evidence, blockers, changed files, and tests before any next instruction.',
          report_id: 'report-worker',
          review_status: 'needs_review',
          run_id: 'worker-run-1',
          status: 'needs_review',
          summary: 'Laptop Codex reported scoped PR evidence.'
        },
        {
          item_id: 'report:report-child',
          item_type: 'report_needs_review',
          linked_record_id: 'child-run-1',
          linked_record_type: 'child_run',
          manual_only: true,
          priority: 15,
          reason: 'report_id report-child still needs Jenny review',
          recommended_action: 'Jenny reviews the report evidence, blockers, changed files, and tests before any next instruction.',
          report_id: 'report-child',
          review_status: 'needs_review',
          run_id: 'child-run-1',
          status: 'received',
          summary: 'Child reported evidence.'
        },
        {
          item_id: 'missing-report:run:run-parent-1',
          item_type: 'missing_required_report',
          linked_record_id: 'run-parent-1',
          linked_record_type: 'run',
          manual_only: true,
          priority: 25,
          reason: 'run_id run-parent-1 has no linked report',
          recommended_action: 'Find or request the terminal run report before marking the lane complete.',
          review_status: 'missing_report',
          run_id: 'run-parent-1',
          status: 'completed',
          summary: 'Parent run'
        }
      ],
      manual_review_only: true,
      link_mismatch_count: 0,
      missing_report_count: 1,
      needs_review_count: 2,
      primary_review_item: {
        item_id: 'report:report-worker',
        linked_record_id: 'worker-run-1',
        linked_record_type: 'worker_node_run',
        reason: 'report_id report-worker still needs Jenny review',
        report_id: 'report-worker',
        review_status: 'needs_review',
        summary: 'Laptop Codex reported scoped PR evidence.'
      },
      primary_review_item_id: 'report:report-worker',
      primary_review_label: 'Laptop Codex reported scoped PR evidence.',
      primary_review_reason: 'report_id report-worker still needs Jenny review',
      queue_count: 3,
      session_send_enabled: false,
      source: 'mission_control_report_review_queue_v1',
      stored: false,
      trusted_for_execution: false,
      worker_dispatch_enabled: false,
      would_execute: false
    },
    result_ingestion_contract: {
      blocked: false,
      blocked_reasons: [],
      blocked_report_count: 0,
      dispatch_enabled: false,
      display_only: true,
      dry_run_only: true,
      duplicate_report_count: 0,
      execution_enabled: false,
      forbidden_metadata_count: 0,
      ingestion_ready_count: 1,
      items: [
        {
          ingestion_ready: true,
          item_id: 'result-ingestion:report-worker',
          linked_record_id: 'worker-run-1',
          linked_record_type: 'worker_node_run',
          manual_review_required: true,
          recommended_action: 'Jenny reviews the linked, redacted report and safety confirmation before relying on it.',
          redaction_status: 'operator_supplied_redacted',
          report_id: 'report-worker',
          review_status: 'needs_review',
          run_id: 'worker-run-1',
          safety_confirmation_present: true,
          status: 'needs_review',
          submitted_by: 'codex',
          submitted_from: 'laptop-codex',
          summary: 'Laptop Codex reported scoped PR evidence.'
        }
      ],
      link_mismatch_count: 0,
      manual_review_only: true,
      missing_link_count: 0,
      missing_safety_confirmation_count: 0,
      primary_item_id: '',
      primary_item_label: '',
      raw_report_count: 1,
      report_count: 1,
      session_send_enabled: false,
      source: 'mission_control_result_ingestion_contract_v1',
      stored: false,
      trusted_for_execution: false,
      unsafe_redaction_count: 0,
      worker_dispatch_enabled: false,
      would_execute: false
    },
    orchestration_stop_control: {
      active_stop_count: 0,
      blocked: true,
      blocked_reasons: ['run run-stopped has no stop_reason', 'run run-stopped has no linked stop/cancel report'],
      dispatch_enabled: false,
      display_only: true,
      dry_run_only: true,
      execution_enabled: false,
      items: [
        {
          item_id: 'run:run-stopped',
          label: 'run run-stopped stopped',
          manual_review_required: true,
          record_id: 'run-stopped',
          record_type: 'run',
          recommended_action: 'Jenny reviews stop reason, final report, blockers, and safety confirmation before assigning follow-up work.',
          report_link_status: 'missing_linked_report',
          report_review_status: 'missing',
          status: 'stopped',
          stop_reason: '',
          stopped_at: ''
        }
      ],
      link_mismatch_count: 0,
      manual_review_only: true,
      needs_report_count: 1,
      needs_review_count: 0,
      primary_item: {
        item_id: 'run:run-stopped',
        label: 'run run-stopped stopped',
        record_id: 'run-stopped',
        record_type: 'run',
        report_link_status: 'missing_linked_report',
        status: 'stopped'
      },
      primary_item_id: 'run:run-stopped',
      primary_item_label: 'run run-stopped stopped',
      session_send_enabled: false,
      source: 'mission_control_orchestration_stop_control_v1',
      stop_cancel_count: 1,
      stored: false,
      terminal_stop_count: 1,
      trusted_for_execution: false,
      worker_dispatch_enabled: false,
      would_execute: false
    },
    run_lifecycle: {
      active_mutation_lane_count: 0,
      active_mutation_run_ids: [],
      active_run_ids: ['run-parent-1'],
      append_only_projection: true,
      blocked: true,
      blocked_reasons: ['terminal run_id run-reportless has no linked report'],
      dispatch_enabled: false,
      display_only: true,
      duplicate_run_ids: [],
      execution_enabled: false,
      one_active_mutation_lane_rule_passed: true,
      run_count: 3,
      session_send_enabled: false,
      stop_cancel_run_ids: ['run-stopped'],
      terminal_run_ids: ['run-reportless', 'run-stopped'],
      terminal_runs_missing_report: ['run-reportless'],
      terminal_runs_with_missing_linked_report_ids: {},
      trusted_for_execution: false,
      worker_dispatch_enabled: false
    },
    safety: { dispatch_in_gateway: false, send_to_jenny_enabled: false },
    stale_context: { warnings: [] },
    tool_permission_classification: {
      blocked_path_count: 1,
      dispatch_enabled: false,
      display_only: true,
      dry_run_only: true,
      execution_enabled: false,
      path_count: 2,
      paths: [
        {
          label: 'audit read',
          path_id: 'audit_read',
          permission_classification: 'read_only_safe',
          read_only_safe: true,
          reasons: []
        },
        {
          label: 'laptop Codex',
          path_id: 'laptop_codex_worker_node',
          permission_classification: 'write_capable_not_safe_for_autonomy',
          read_only_safe: false,
          reasons: ['path exposes write or execution capabilities: worker_node_path']
        }
      ],
      permission_classification: 'write_capable_not_safe_for_autonomy',
      read_only_safe: false,
      session_send_enabled: false,
      stored: false,
      worker_dispatch_enabled: false,
      write_capable_path_ids: ['laptop_codex_worker_node']
    },
    worker_node_presence: {
      active_worker_node_run_count: 1,
      blocked: true,
      blocked_reasons: ['worker-node presence_status is not recorded'],
      capability_summary: '',
      dispatch_enabled: false,
      display_only: true,
      dry_run_only: true,
      execution_enabled: false,
      last_seen_age_seconds: null,
      last_seen_at: '',
      online: false,
      parent_run_id: 'run-parent-1',
      presence_state: 'unknown',
      presence_status: '',
      recorded_worker_node_run_count: 1,
      session_send_enabled: false,
      source: 'mission_control_worker_node_presence_v1',
      stale_after_seconds: 900,
      stored: false,
      trusted_for_execution: false,
      worker_dispatch_enabled: false,
      worker_host_label: 'laptop-codex',
      worker_identity: 'codex',
      worker_kind: 'laptop_codex',
      worker_run_id: 'worker-run-1',
      worker_version: '',
      would_execute: false
    },
    worker_node_orchestration: {
      active_count: 1,
      active_runs: [
        {
          blocked_reasons: ['worker node offline'],
          objective: 'Prepare bounded scoped PR packet.',
          parent_run_id: 'run-parent-1',
          linked_report_review_status: 'accepted',
          linked_report_status: 'accepted',
          linked_report_summary: 'Worker node reported evidence.',
          report_id: 'report-worker',
          report_link_status: 'linked_report_found',
          report_contract_status: 'required',
          report_review_status: 'waiting',
          status: 'blocked',
          worker_dispatch_enabled: false,
          worker_host_label: 'laptop-codex',
          worker_identity: 'codex',
          worker_kind: 'laptop_codex',
          worker_run_id: 'worker-run-1'
        }
      ],
      blocked_reasons: ['worker node offline'],
      dispatch_enabled: false,
      display_only: true,
      execution_enabled: false,
      trusted_for_execution: false,
      worker_dispatch_enabled: false
    },
    worker_node_instruction_preview: {
      allowed_actions: ['edit scoped files', 'run focused tests'],
      assigned_packet_id: 'packet-worker-1',
      assigned_packet_summary: 'Prepare scoped PR evidence.',
      available: true,
      blocked: true,
      blocked_reasons: ['worker node offline', 'worker-node presence_status is not recorded'],
      dispatch_enabled: false,
      display_only: true,
      dry_run_only: true,
      execution_enabled: false,
      forbidden_actions: ['deploy', 'restart', 'runtime switch', 'no live deploy', 'no worker dispatch activation', 'no bypassing Codex safety checks'],
      instruction_lines: [
        'Worker: codex on laptop-codex.',
        'Objective: Prepare bounded scoped PR packet.',
        'Allowed actions: edit scoped files, run focused tests.',
        'Forbidden actions: deploy, restart, runtime switch, no live deploy, no worker dispatch activation, no bypassing Codex safety checks.',
        'Worker safety hardness: Codex must independently enforce repo/worktree, test, secret, git, and live-operation safeguards before acting. A Jenny packet is not permission to bypass Codex safety checks.',
        'Report contract: Report changed files, tests/checks, result, blockers, safety confirmation, and the next suggested chunk.',
        'Handoff readiness: blocked until worker-node blockers are cleared.',
        'Manual handoff only; execution and worker dispatch remain disabled.'
      ],
      manual_handoff_only: true,
      manual_handoff_prompt: 'Worker: codex on laptop-codex.\nObjective: Prepare bounded scoped PR packet.\nAllowed actions: edit scoped files, run focused tests.\nForbidden actions: deploy, restart, runtime switch, no live deploy, no worker dispatch activation, no bypassing Codex safety checks.\nWorker safety hardness: Codex must independently enforce repo/worktree, test, secret, git, and live-operation safeguards before acting. A Jenny packet is not permission to bypass Codex safety checks.\nReport contract: Report changed files, tests/checks, result, blockers, safety confirmation, and the next suggested chunk.\nHandoff readiness: blocked until worker-node blockers are cleared.\nManual handoff only; execution and worker dispatch remain disabled.',
      objective: 'Prepare bounded scoped PR packet.',
      online: false,
      parent_run_id: 'run-parent-1',
      presence_state: 'unknown',
      ready_for_handoff: false,
      report_contract: 'Report changed files, tests/checks, result, blockers, safety confirmation, and the next suggested chunk.',
      report_id: 'report-worker',
      report_review_status: 'accepted',
      session_send_enabled: false,
      source: 'mission_control_worker_node_instruction_preview_v1',
      stored: false,
      trusted_for_execution: false,
      worker_dispatch_enabled: false,
      worker_host_label: 'laptop-codex',
      worker_identity: 'codex',
      worker_run_id: 'worker-run-1',
      worker_safety_hardness: [
        'Codex must independently enforce repo/worktree, test, secret, git, and live-operation safeguards before acting.',
        'A Jenny packet is not permission to bypass Codex safety checks.'
      ],
      would_execute: false
    }
  })
  createMissionControlReport.mockResolvedValue({
    dispatch_enabled: false,
    manual_copy_only: true,
    report: {
      project_id: 'project-hermes-mission-control',
      report_id: 'report-created',
      summary: 'Manual report saved'
    },
    send_to_jenny_enabled: false,
    stored: true
  })
  createMissionControlChallengeReview.mockResolvedValue({
    challenge_review: {
      decision_state: 'needs_spec_first',
      project_id: 'project-hermes-mission-control',
      request_summary: 'Make Mission Control usable from project rooms'
    },
    dispatch_enabled: false,
    manual_copy_only: true,
    record_type: 'ChallengeReviewRecord',
    send_to_jenny_enabled: false,
    stored: true
  })
  createMissionControlLaneRequest.mockResolvedValue({
    dispatch_enabled: false,
    lane_request: {
      lane_request_id: 'lane-created',
      project_id: 'project-hermes-mission-control',
      status: 'draft',
      title: 'Read-only project room request'
    },
    manual_copy_only: true,
    record_type: 'LaneRequestRecord',
    send_to_jenny_enabled: false,
    stored: true
  })
  createMissionControlJennyBridgeRequest.mockResolvedValue({
    dispatch_enabled: false,
    manual_copy_only: false,
    record_type: 'JennyBridgeMessageRequestRecord',
    request: {
      message: 'Project room request packet',
      project_id: 'project-hermes-mission-control',
      request_id: 'bridge-request-created',
      status: 'queued',
      target_agent: 'jenny'
    },
    send_to_jenny_enabled: false,
    stored: true
  })
  createMissionControlGitHubBridgeRequest.mockResolvedValue({
    dispatch_enabled: false,
    github_bridge_enabled: true,
    manual_copy_only: false,
    message: {
      created_at: '2026-06-13T01:01:00Z',
      from_agent: 'travis',
      message: 'Project room request packet',
      project_id: 'project-hermes-mission-control',
      request_id: 'github-bridge-request-created',
      status: 'queued',
      to_agent: 'jenny'
    },
    record_type: 'GitHubBridgeMessageRecord',
    send_to_jenny_enabled: true,
    stored: true
  })
  createMissionControlJennyReplyReview.mockResolvedValue({
    dispatch_enabled: false,
    manual_start_only: true,
    record_type: 'JennyReplyReviewRecord',
    reply_review: {
      decision: 'needs_evidence',
      note: 'Reviewed: needs evidence',
      project_id: 'project-hermes-mission-control',
      response_id: 'bridge-response-1',
      review_id: 'reply-review-created',
      reviewer: 'travis'
    },
    send_to_jenny_enabled: false,
    stored: true,
    timer_enabled: false,
    worker_enabled: false
  })
  getMissionControlProfileMemoryStorage.mockResolvedValue({
    display_only: true,
    dry_run_only: true,
    profile_count: 2,
    profiles: [
      {
        data: {
          bytes: 6_442_450_944,
          components: {
            memories: { bytes: 32_768, exists: true, path: '/home/jenny/.hermes/memories' },
            sessions: { bytes: 2_790_309_888, exists: true, path: '/home/jenny/.hermes/sessions' },
            state: { bytes: 3_652_108_288, exists: true, path: '/home/jenny/.hermes/state.db' }
          },
          exists: true,
          path: '/home/jenny/.hermes',
          scope: 'default_profile_state_sessions_memories'
        },
        home: '/home/jenny/.hermes',
        memory: { bytes: 1100, chars: 1100, exists: true, limit_chars: 2200, percent_used: 50 },
        mount: { free_bytes: 4_294_967_296, path: '/', percent_used: 76, total_bytes: 17_179_869_184, used_bytes: 12_884_901_888 },
        profile: 'default',
        recall_file_bytes: 1300,
        total_bytes: 6_442_450_944,
        user: { bytes: 200, chars: 200, exists: true, limit_chars: 1375, percent_used: 15 }
      },
      {
        data: {
          bytes: 49_283_072,
          components: {
            memories: { bytes: 4096, exists: true, path: '/home/jenny/.hermes/profiles/wahainspection/memories' },
            sessions: { bytes: 12_582_912, exists: true, path: '/home/jenny/.hermes/profiles/wahainspection/sessions' },
            state: { bytes: 36_696_064, exists: true, path: '/home/jenny/.hermes/profiles/wahainspection/state.db' }
          },
          exists: true,
          path: '/home/jenny/.hermes/profiles/wahainspection',
          scope: 'profile_directory'
        },
        home: '/home/jenny/.hermes/profiles/wahainspection',
        memory: { bytes: 0, chars: 0, exists: false, limit_chars: 2200, percent_used: 0 },
        mount: { free_bytes: 4_294_967_296, path: '/', percent_used: 76, total_bytes: 17_179_869_184, used_bytes: 12_884_901_888 },
        profile: 'wahainspection',
        recall_file_bytes: 0,
        total_bytes: 49_283_072,
        user: { bytes: 0, chars: 0, exists: false, limit_chars: 1375, percent_used: 0 }
      }
    ],
    stored: false,
    total_bytes: 6_491_734_016,
    total_memory_bytes: 1100,
    total_profile_data_bytes: 6_491_734_016,
    total_recall_file_bytes: 1300,
    total_user_bytes: 200
  })
  answerMissionControlGitHubBridgeOnce.mockResolvedValue({
    answered: true,
    dispatch_enabled: false,
    manual_start_only: true,
    request: {
      created_at: '2026-06-13T01:06:00Z',
      from_agent: 'travis',
      message: 'Second request.',
      project_id: 'project-hermes-mission-control',
      request_id: 'github-bridge-request-2',
      status: 'queued',
      to_agent: 'jenny'
    },
    response: {
      created_at: '2026-06-13T01:07:00Z',
      from_agent: 'jenny',
      message: 'Jenny answered the second request.',
      project_id: 'project-hermes-mission-control',
      request_id: 'github-bridge-request-2',
      status: 'replied',
      to_agent: 'travis'
    },
    send_to_jenny_enabled: true,
    stored: true,
    worker_enabled: false,
    timer_enabled: false
  })
  createMissionControlSessionProjectLink.mockResolvedValue({
    dispatch_enabled: false,
    manual_copy_only: true,
    record_index: 38,
    record_type: 'SessionProjectLinkRecord',
    send_to_jenny_enabled: false,
    session_project_link: {
      durable_session_id: 'root-suggested-hermes',
      link_id: 'session-project-link-test',
      link_method: 'manual',
      project_id: 'project-hermes-mission-control',
      session_id: 'session-suggested-hermes',
      status: 'active'
    },
    stored: true
  })
  getMissionControlProjects.mockResolvedValue({
    count: 6,
    dispatch_enabled: false,
    manual_copy_only: true,
    send_to_jenny_enabled: false,
    projects: [
      {
        record: {
          project_id: 'project-smoke',
          name: 'Smoke Test Project',
          status: 'smoke-test',
          current_goal: 'Verify smoke behavior.',
          next_recommended_lane: 'Smoke lane',
          source_of_truth: 'Smoke fixture'
        },
        record_type: 'ProjectRecord'
      },
      ...realProjects.map(([project_id, name]) => ({
        record: {
          project_id,
          name,
          status: `${name} status`,
          current_goal: `${name} goal`,
          next_recommended_lane: `${name} next lane`,
          source_of_truth: 'Mission Control records'
        },
        record_type: 'ProjectRecord'
      }))
    ]
  })
  getMissionControlProjectBriefs.mockResolvedValue({
    count: 1,
    dispatch_enabled: false,
    manual_copy_only: true,
    project_briefs: [
      {
        record: {
          approval_rules: ['explicit approval before send path'],
          constraints: ['manual-copy only'],
          outcome: 'Make Jenny OS native chat the obvious operating surface before enabling execution.',
          project_id: 'project-hermes-mission-control',
          status: 'active',
          success_criteria: ['project rooms visible', 'challenge gate visible']
        },
        record_type: 'ProjectBriefRecord'
      }
    ],
    send_to_jenny_enabled: false
  })
  getMissionControlChallengeReviews.mockResolvedValue({
    challenge_reviews: [
      {
        record: {
          concerns: [],
          decision_state: 'clear_and_safe',
          project_id: 'project-hermes-mission-control',
          recommended_path: 'Use a bounded read-only workspace usability lane.',
          request_summary: 'Make project rooms visible',
          required_approvals: ['deploy/restart approval'],
          status: 'accepted',
          suggested_lane_title: 'Read-only project room usability check'
        },
        record_type: 'ChallengeReviewRecord'
      }
    ],
    count: 1,
    dispatch_enabled: false,
    manual_copy_only: true,
    send_to_jenny_enabled: false
  })
  getMissionControlLaneRequests.mockResolvedValue({
    count: 1,
    dispatch_enabled: false,
    manual_copy_only: true,
    send_to_jenny_enabled: false,
    lane_requests: [
      {
        record: {
          lane_request_id: 'lane-1',
          project_id: 'project-hermes-mission-control',
          title: 'Read-only status refresh',
          status: 'draft'
        },
        record_type: 'LaneRequestRecord'
      }
    ]
  })
  getMissionControlReports.mockResolvedValue({
    count: 1,
    dispatch_enabled: false,
    manual_copy_only: true,
    send_to_jenny_enabled: false,
    reports: [
      {
        record: {
          report_id: 'report-1',
          project_id: 'project-hermes-mission-control',
          summary: 'Jenny finished the desktop architecture review.',
          result: 'Use Mission Control backend with desktop frontend.',
          risks: ['dashboard overbuild'],
          blockers: ['none'],
          next_recommended_lane: 'Desktop read-only workspace v1'
        },
        record_type: 'JennyReportRecord'
      }
    ]
  })
  getMissionControlProjectState.mockResolvedValue({
    count: 6,
    dispatch_enabled: false,
    manual_copy_only: true,
    send_to_jenny_enabled: false,
    stored: false,
    project_states: [
      {
        project_id: 'project-smoke',
        name: 'Smoke Test Project',
        status: 'smoke-test',
        current_goal: 'Verify smoke behavior.',
        latest_report_summary: 'Smoke report.',
        latest_result: 'Smoke result.',
        risks: ['none'],
        blockers: [],
        next_recommended_lane: 'Smoke lane'
      },
      {
        project_id: 'project-hermes-mission-control',
        name: 'Hermes / Mission Control',
        status: 'Live workspace',
        current_goal: 'Make desktop the main workspace.',
        latest_report_summary: 'Jenny finished the desktop architecture review.',
        latest_result: 'Use Mission Control backend with desktop frontend.',
        risks: ['dashboard overbuild'],
        blockers: ['none'],
        next_recommended_lane: 'Desktop read-only workspace v1',
        artifact_links: ['reports/hermes/desktop-review.md'],
        has_real_report: true,
        latest_activity_at: '2026-06-11T10:00:00Z',
        latest_activity_source: 'report',
        linked_session_count: 1,
        recent_sessions: [
          {
            cwd: '/home/jenny/.hermes/hermes-runtime-session-links-573658a',
            durable_session_id: 'root-linked-hermes',
            last_active: 1781202705,
            linked_project_id: 'project-hermes-mission-control',
            profile: 'default',
            session_id: 'session-linked-hermes',
            source: 'discord',
            suggested_project_id: '',
            title: 'Mission Control linked session'
          }
        ],
        unassigned_suggestion_count: 2,
        missing_state_fields: ['report_contract'],
        report_contract: {
          complete: false,
          display_only: true,
          missing_fields: ['evidence', 'tests'],
          required_fields: ['summary', 'result', 'risks/blockers', 'evidence', 'tests', 'next lane'],
          state: 'incomplete',
          trusted_for_execution: false
        },
        latest_lane_request: {
          lane_request_id: 'lane-1',
          project_id: 'project-hermes-mission-control',
          title: 'Read-only status refresh',
          status: 'draft'
        },
        latest_report: {
          report_id: 'report-1',
          project_id: 'project-hermes-mission-control',
          summary: 'Jenny finished the desktop architecture review.',
          result: 'Use Mission Control backend with desktop frontend.',
          risks: ['dashboard overbuild'],
          blockers: ['none'],
          next_recommended_lane: 'Desktop read-only workspace v1'
        }
      },
      ...realProjects.slice(1).map(([project_id, name]) => ({
        project_id,
        name,
        status: `${name} status`,
        current_goal: `${name} goal`,
        latest_report_summary: '',
        latest_result: '',
        has_real_report: false,
        missing_state_fields: ['latest_lane', 'latest_jenny_report', 'latest_result', 'risks_blockers', 'artifact_links', 'report_contract'],
        report_contract: {
          complete: false,
          display_only: true,
          missing_fields: ['report'],
          required_fields: ['summary', 'result', 'risks/blockers', 'evidence', 'tests', 'next lane'],
          state: 'missing_report',
          trusted_for_execution: false
        },
        latest_activity_source: 'project',
        risks: [],
        blockers: [],
        next_recommended_lane: `${name} next lane`
      }))
    ]
  })
  getMissionControlProjectSessions.mockResolvedValue({
    active_link_count: 1,
    count: 6,
    dispatch_enabled: false,
    display_only: true,
    execution_enabled: false,
    groups: [
      {
        linked_session_count: 1,
        name: 'Hermes / Mission Control',
        project_id: 'project-hermes-mission-control',
        sessions: [
          {
            cwd: '/home/jenny/.hermes/hermes-runtime-session-links-573658a',
            durable_session_id: 'root-linked-hermes',
            last_active: 1781202705,
            linked_project_id: 'project-hermes-mission-control',
            profile: 'default',
            session_id: 'session-linked-hermes',
            source: 'discord',
            suggested_project_id: '',
            title: 'Mission Control linked session'
          }
        ],
        unassigned_suggestion_count: 0
      },
      {
        linked_session_count: 0,
        name: 'Unassigned / General',
        project_id: 'unassigned-general',
        sessions: [
          {
            cwd: '/home/jenny/.hermes/hermes-runtime-session-links-573658a',
            durable_session_id: 'root-suggested-hermes',
            last_active: 1781202600,
            linked_project_id: '',
            profile: 'default',
            session_id: 'session-suggested-hermes',
            source: 'discord',
            suggested_project_id: 'project-hermes-mission-control',
            title: 'Suggested Mission Control session'
          },
          {
            cwd: '',
            durable_session_id: 'root-general',
            last_active: 1781202500,
            linked_project_id: '',
            profile: 'default',
            session_id: 'session-general',
            source: 'discord',
            suggested_project_id: '',
            title: 'General unassigned session'
          }
        ],
        unassigned_suggestion_count: 1
      }
    ],
    manual_copy_only: true,
    send_to_jenny_enabled: false,
    stored: false,
    trusted_for_execution: false
  })
  getMissionControlJennyBridgeOutbox.mockResolvedValue({
    count: 2,
    dispatch_enabled: false,
    manual_copy_only: false,
    requests: [
      {
        record: {
          created_at: '2026-06-12T15:21:00Z',
          message: 'Old unanswered bridge request that should not keep the room pending.',
          project_id: 'project-hermes-mission-control',
          request_id: 'bridge-request-old',
          status: 'queued',
          target_agent: 'jenny'
        },
        record_type: 'JennyBridgeMessageRequestRecord'
      },
      {
        record: {
          created_at: '2026-06-12T15:22:00Z',
          message: 'Review PR #75 and report readiness.',
          project_id: 'project-hermes-mission-control',
          request_id: 'bridge-request-1',
          status: 'queued',
          target_agent: 'jenny'
        },
        record_type: 'JennyBridgeMessageRequestRecord'
      }
    ],
    send_to_jenny_enabled: false
  })
  getMissionControlJennyBridgeInbox.mockResolvedValue({
    count: 1,
    dispatch_enabled: false,
    manual_copy_only: false,
    responses: [
      {
        record: {
          created_at: '2026-06-12T15:23:00Z',
          message: 'Safe to mark ready.',
          project_id: 'project-hermes-mission-control',
          request_id: 'bridge-request-1',
          responder: 'jenny',
          response_id: 'bridge-response-1',
          status: 'received'
        },
        record_type: 'JennyBridgeMessageResponseRecord'
      }
    ],
    send_to_jenny_enabled: false
  })
  getMissionControlJennyBridgePollerStatus.mockResolvedValue({
    count: 1,
    dispatch_enabled: false,
    display_only: true,
    execution_enabled: false,
    last_error: '',
    last_poll_at: '2026-06-12T15:22:00Z',
    last_response_at: '2026-06-12T15:23:00Z',
    last_response_request_id: 'bridge-request-1',
    last_status: 'response_appended',
    manual_start_only: true,
    pending_count: 0,
    send_to_jenny_enabled: false,
    session_send_enabled: false,
    status_records: [],
    stored: false,
    timer_enabled: false,
    worker_enabled: false
  })
  getMissionControlJennyReplyReviews.mockResolvedValue({
    count: 1,
    dispatch_enabled: false,
    manual_start_only: true,
    reply_reviews: [
      {
        record: {
          created_at: '2026-06-12T15:24:00Z',
          decision: 'needs_evidence',
          note: 'Reviewed: needs evidence',
          project_id: 'project-hermes-mission-control',
          response_id: 'bridge-response-1',
          review_id: 'reply-review-1',
          reviewer: 'travis'
        },
        record_type: 'JennyReplyReviewRecord'
      }
    ],
    send_to_jenny_enabled: false,
    stored: false,
    timer_enabled: false,
    worker_enabled: false
  })
  getMissionControlGitHubBridgeStatus.mockResolvedValue({
    count: 1,
    daemon_enabled: false,
    discord_automation_enabled: false,
    dispatch_enabled: false,
    display_only: true,
    execution_enabled: false,
    last_error: '',
    last_poll_at: '2026-06-13T01:00:00Z',
    last_response_at: '2026-06-13T01:05:00Z',
    last_response_request_id: 'github-bridge-request-1',
    last_status: 'poll_completed',
    manual_start_only: true,
    mode: 'watch_foreground',
    foreground_watch_supported: true,
    foreground_watch_running: true,
    model_routing_enabled: false,
    pending_count: 1,
    visible_pending_count: 0,
    background_pending_count: 1,
    recent_messages: [
      {
        record: {
          created_at: '2026-06-13T01:00:00Z',
          from_agent: 'travis',
          message: 'Hermes / Mission Control Request: Review the Mission Control room. Current brief: Replace Discord as Travis primary workspace. Challenge state: clear_and_safe / start record-only manual-copy. Allowed: read approved context. Forbidden: no direct session send.',
          metadata: {
            user_message: 'Review the Mission Control room.'
          },
          project_id: 'project-hermes-mission-control',
          request_id: 'github-bridge-request-1',
          status: 'queued',
          to_agent: 'jenny'
        }
      },
      {
        record: {
          created_at: '2026-06-13T01:05:00Z',
          from_agent: 'jenny',
          message: 'I can see the Mission Control room request.',
          project_id: 'project-hermes-mission-control',
          request_id: 'github-bridge-request-1',
          status: 'replied',
          to_agent: 'travis'
        }
      },
      {
        record: {
          created_at: '2026-06-13T01:05:30Z',
          from_agent: 'travis',
          message: 'Hermes / Mission Control Request: testing. tell me a short story Current brief: Replace Discord as Travis primary workspace. Challenge state: clear_and_safe / start record-only manual-copy. Allowed: read approved context. Forbidden: no direct session send.',
          project_id: 'project-hermes-mission-control',
          request_id: 'github-bridge-request-replied-user',
          status: 'replied',
          to_agent: 'jenny'
        }
      },
      {
        record: {
          created_at: '2026-06-13T01:05:40Z',
          from_agent: 'travis',
          message: 'Project room request: Hermes / Mission Control Request: fix the two way communication with codex through the bridge Current brief: Replace Discord as Travis primary workspace. Challenge state: clear_and_safe / start record-only manual-copy. Allowed: read approved context. Forbidden: no direct session send.',
          project_id: 'project-hermes-mission-control',
          request_id: 'github-bridge-request-project-room-legacy',
          status: 'replied',
          to_agent: 'jenny'
        }
      },
      {
        record: {
          created_at: '2026-06-13T01:06:00Z',
          from_agent: 'travis',
          message: 'Local error guard smoke. This should not post a reply.',
          project_id: 'project-hermes-mission-control',
          request_id: 'github-bridge-diagnostic-1',
          status: 'queued',
          to_agent: 'jenny'
        }
      },
      {
        record: {
          created_at: '2026-06-13T01:07:00Z',
          from_agent: 'jenny',
          message: 'Error: codex app-server startup failed: initialize timed out.',
          project_id: 'project-hermes-mission-control',
          request_id: 'github-bridge-diagnostic-2',
          status: 'replied',
          to_agent: 'travis'
        }
      },
      {
        record: {
          created_at: '2026-06-13T01:08:00Z',
          from_agent: 'jenny',
          message: 'Bridge works. The success smoke reached Jenny and failures are guarded.',
          project_id: 'project-hermes-mission-control',
          request_id: 'github-bridge-diagnostic-3',
          status: 'replied',
          to_agent: 'travis'
        }
      },
      {
        record: {
          created_at: '2026-06-13T01:09:00Z',
          from_agent: 'codex',
          message: 'Bounded dashboard-only deploy check request for accepted-live.',
          project_id: 'project-hermes-mission-control',
          request_id: 'codex-pr151-dashboard-deploy-structured-20260614-001',
          status: 'queued',
          to_agent: 'jenny'
        }
      },
      {
        record: {
          created_at: '2026-06-13T01:10:00Z',
          from_agent: 'jenny',
          message: 'Dashboard-only deploy check completed for Codex.',
          project_id: 'project-hermes-mission-control',
          request_id: 'codex-pr151-dashboard-deploy-structured-20260614-001',
          status: 'replied',
          to_agent: 'codex'
        }
      }
    ],
    response_messages: [],
    send_to_jenny_enabled: false,
    session_send_enabled: false,
    status_records: [
      {
        record: {
          created_at: '2026-06-13T01:04:00Z',
          handled_request_id: 'github-bridge-request-1',
          mode: 'manual_hermes_answer',
          pending_count: 1,
          status: 'hermes_answer_started',
          status_id: 'github-status-started'
        }
      },
      {
        record: {
          created_at: '2026-06-13T01:05:00Z',
          handled_request_id: 'github-bridge-request-1',
          mode: 'manual_hermes_answer',
          pending_count: 0,
          status: 'hermes_answer_completed',
          status_id: 'github-status-completed'
        }
      }
    ],
    stored: false,
    timer_enabled: false,
    worker_enabled: false
  })
})

afterEach(() => {
  cleanup()
  vi.clearAllMocks()
})

describe('MissionControlView', () => {
  it('fetches read-only Mission Control endpoints and renders the five real projects as primary cards', async () => {
    await renderMissionControl()

    await waitFor(() => expect(getMissionControlProjectState).toHaveBeenCalledTimes(1))
    expect(getMissionControlWorkspaceStatus).toHaveBeenCalledTimes(1)
    expect(getMissionControlProjects).toHaveBeenCalledTimes(1)
    expect(getMissionControlProjectBriefs).toHaveBeenCalledTimes(1)
    expect(getMissionControlChallengeReviews).toHaveBeenCalledTimes(1)
    expect(getMissionControlLaneRequests).toHaveBeenCalledTimes(1)
    expect(getMissionControlReports).toHaveBeenCalledTimes(1)
    expect(getMissionControlProjectSessions).toHaveBeenCalledTimes(1)
    expect(getMissionControlJennyBridgeOutbox).toHaveBeenCalledTimes(1)
    expect(getMissionControlJennyBridgeInbox).toHaveBeenCalledTimes(1)
    expect(getMissionControlJennyBridgePollerStatus).toHaveBeenCalledTimes(1)
    expect(getMissionControlGitHubBridgeStatus).toHaveBeenCalledTimes(1)

    const auditNotice = screen.getByLabelText('Advanced audit console notice')
    expect(auditNotice).toBeTruthy()
    expect(auditNotice.textContent).toContain('Advanced audit console. Use Jenny OS in the sidebar for normal project chat.')
    expect(screen.getByText('Project report archive')).toBeTruthy()
    expect(screen.getAllByText('Safety details').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Request options').length).toBeGreaterThan(0)
    expect(screen.getByText('Active Jenny OS Lane')).toBeTruthy()
    expect(screen.getByText('Mission Control/Jenny stability lane only. Display-only; lane state is derived from briefs, challenge reviews, lane drafts, and reports.')).toBeTruthy()
    expect(screen.getByText('display-only / no dispatch')).toBeTruthy()
    expect(screen.getAllByText('next safe lane').length).toBeGreaterThan(0)
    expect(screen.getByRole('region', { name: 'Project chat workspace' })).toBeTruthy()
    expect(screen.getByText('Projects')).toBeTruthy()
    expect(screen.getAllByText('5 projects').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Paused until Jenny is stable').length).toBe(4)
    expect(screen.getByText('Local studio')).toBeTruthy()
    expect(screen.getByText('IV. — Jenny workspace')).toBeTruthy()
    expect(screen.getByRole('complementary', { name: 'Safety details' })).toBeTruthy()
    expect(screen.getAllByRole('heading', { name: 'Hermes / Mission Control' }).length).toBeGreaterThan(0)
    expect(screen.getByText('Conversation')).toBeTruthy()
    expect(screen.getByLabelText('Jenny chat status')).toBeTruthy()
    expect(screen.getByText('Jenny status')).toBeTruthy()
    expect(screen.getByRole('heading', { name: 'Jenny' })).toBeTruthy()
    expect(screen.getAllByText((_, element) => element?.textContent?.includes('Next: Review before relying') ?? false).length).toBeGreaterThan(0)
    expect(screen.getByRole('region', { name: 'Latest Jenny outcome' })).toBeTruthy()
    expect(screen.getByText('Review before relying')).toBeTruthy()
    expect(screen.getAllByText(/Review the latest Jenny reply in the chat before acting on it/).length).toBeGreaterThan(0)
    expect(screen.getByText(/Next: Use the reply review buttons/)).toBeTruthy()
    expect(screen.getByLabelText('Jenny operator guidance')).toBeTruthy()
    expect(screen.getByText('Review Jenny reply')).toBeTruthy()
    expect(screen.getByText(/Ask for evidence or challenge the plan/)).toBeTruthy()
    expect(screen.getAllByText('one reply at a time').length).toBeGreaterThan(0)
    expect(screen.getAllByText('evidence required').length).toBeGreaterThan(0)
    expect(screen.getAllByText('no hidden execution').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Current phase').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Last sent').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Reply state').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Elapsed').length).toBeGreaterThan(0)
    expect(screen.getByText('Jenny activity')).toBeTruthy()
    expect(screen.getByText('recent bridge status')).toBeTruthy()
    expect(screen.getByText('Jenny is thinking')).toBeTruthy()
    expect(screen.getAllByText('request github-bridge-request-1').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Jenny').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Jenny is watching').length).toBeGreaterThan(0)
    expect(screen.getByText(/Bridge watching for replies/)).toBeTruthy()
    expect(screen.getByText(/Bridge is watching for replies/)).toBeTruthy()
    expect(screen.getByText('Next step')).toBeTruthy()
    expect(screen.getAllByText(/Ask Jenny for exact files, commands, checks, CI\/runtime status/).length).toBeGreaterThan(0)
    expect(screen.getAllByText('Pending 0').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Replies 2').length).toBeGreaterThan(0)
    expect(screen.queryByText(/Local error guard smoke/i)).toBeNull()
    expect(screen.queryByText(/codex app-server startup failed/i)).toBeNull()
    expect(screen.queryByText(/Bridge works/i)).toBeNull()
    expect(screen.queryByText(/success smoke reached/i)).toBeNull()
    expect(screen.queryByText(/Bounded dashboard-only deploy check/i)).toBeNull()
    expect(screen.queryByText(/Dashboard-only deploy check completed/i)).toBeNull()
    expect(screen.getByText('Previous sessions')).toBeTruthy()
    expect(screen.getByText('Advanced')).toBeTruthy()
    expect(screen.getAllByText('Jenny bridge').length).toBeGreaterThan(0)
    expect(screen.getAllByText('manual-start only').length).toBeGreaterThanOrEqual(2)
    expect(screen.getAllByText('replied').length).toBeGreaterThan(0)
    expect(screen.getByText('GitHub mailbox')).toBeTruthy()
    expect(screen.getByText('visible 0 / background 1')).toBeTruthy()
    expect(screen.getByText('worker disabled / timer disabled')).toBeTruthy()
    expect(screen.getByText('daemon disabled / worker disabled / timer disabled')).toBeTruthy()
    expect(screen.getByText('deploy state')).toBeTruthy()
    expect(screen.getByText('merged not deployed')).toBeTruthy()
    expect(screen.getByText('runtime provenance')).toBeTruthy()
    expect(screen.getByText('GATEWAY UNTRUSTED')).toBeTruthy()
    expect(screen.getByText('read-only autonomy')).toBeTruthy()
    expect(screen.getAllByText('blocked / no execution').length).toBeGreaterThanOrEqual(2)
    expect(screen.getByText('bridge permission')).toBeTruthy()
    expect(screen.getByText('write capable')).toBeTruthy()
    expect(screen.getByText('tool permissions')).toBeTruthy()
    expect(screen.getByText('write capable not safe for autonomy / blocked paths 1')).toBeTruthy()
    expect(screen.getByText('write-capable tool paths')).toBeTruthy()
    expect(screen.getByText('laptop_codex_worker_node')).toBeTruthy()
    expect(screen.getByText('scoped PR lane')).toBeTruthy()
    expect(screen.getByText('scoped PR bridge')).toBeTruthy()
    expect(screen.getByText('manual only')).toBeTruthy()
    expect(screen.getByText('execution mode')).toBeTruthy()
    expect(screen.getByText('worker node preview / preview yes / execution no')).toBeTruthy()
    expect(screen.getByText('execution packet')).toBeTruthy()
    expect(screen.getByText('worker node / eligible no / execute no')).toBeTruthy()
    expect(screen.getByText('execution packet body locks')).toBeTruthy()
    expect(screen.getAllByText('execute no / dispatch no / session no / worker no').length).toBeGreaterThanOrEqual(2)
    expect(screen.getByText('worker contract locks')).toBeTruthy()
    expect(screen.getByText('lifecycle projection')).toBeTruthy()
    expect(screen.getByText('append-only yes / active mutation lanes 0')).toBeTruthy()
    expect(screen.getByText('next safe action')).toBeTruthy()
    expect(screen.getByText('Review runtime provenance blockers')).toBeTruthy()
    expect(screen.getByText('next action mode')).toBeTruthy()
    expect(screen.getByText('display-only yes / actions 1')).toBeTruthy()
    expect(screen.getByText('operator packet')).toBeTruthy()
    expect(screen.getByText('report review required / approval required yes / display-only yes')).toBeTruthy()
    expect(screen.getByText('operator review gates')).toBeTruthy()
    expect(screen.getByText('Jenny review yes / execution-ready no / worker dispatch no')).toBeTruthy()
    expect(screen.getByText('operator packet locks')).toBeTruthy()
    expect(screen.getByText('execute no / dispatch no / session no / worker no / would dispatch no / would session no')).toBeTruthy()
    expect(screen.getByText('operator next instruction')).toBeTruthy()
    expect(screen.getByText('Jenny reviews Laptop Codex reported scoped PR evidence. before issuing another worker instruction.')).toBeTruthy()
    expect(screen.getByText('operator report links')).toBeTruthy()
    expect(screen.getByText('mismatch 0 / queue 0 / ingestion 0 / completion 0 / stop 0')).toBeTruthy()
    expect(screen.getByText('next action reasons')).toBeTruthy()
    expect(screen.getByText('gateway git metadata is broken, run_id run-parent-1 references unavailable approval_id approval-old')).toBeTruthy()
    expect(screen.getByText('operator summary')).toBeTruthy()
    expect(screen.getByText(/Operator state: report review required/)).toBeTruthy()
    expect(screen.getByText(/Approval required: yes/)).toBeTruthy()
    expect(screen.getByText(/Worker instruction: preview available but blocked/)).toBeTruthy()
    expect(screen.getByText(/Child instruction: preview available but blocked/)).toBeTruthy()
    expect(screen.getByText(/Report overwrite conflicts: 1; duplicate report IDs are quarantined/)).toBeTruthy()
    expect(screen.getByText('operator blockers')).toBeTruthy()
    expect(screen.getByText('gateway git metadata is broken, report_id report-worker has multiple append-only records, report_id report-worker attempts to overwrite append-only report fields: status, report_id report-worker still needs Jenny review, worker node offline, worker-node presence_status is not recorded, runtime provenance is not clean, worker-node presence is not confirmed online, report_id report-worker missing contract fields: result, evidence, tests, next lane, safety confirmation, run run-stopped has no stop_reason, run run-stopped has no linked stop/cancel report')).toBeTruthy()
    expect(screen.getByText('operator execution locks')).toBeTruthy()
    expect(statusItemValue('operator execution locks').textContent).toBe('none')
    expect(screen.getByText('projection execution locks')).toBeTruthy()
    expect(statusItemValue('projection execution locks').textContent).toBe('none')
    expect(screen.getByText('execution mode blockers')).toBeTruthy()
    expect(screen.getByText('protected execution markers')).toBeTruthy()
    expect(screen.getByText('execution packet blockers')).toBeTruthy()
    expect(screen.getByText('runtime provenance is not clean, worker-node presence is not confirmed online')).toBeTruthy()
    expect(screen.getByText('execution lock blockers')).toBeTruthy()
    expect(statusItemValue('execution lock blockers').textContent).toBe('none')
    expect(screen.getByText('orchestration readiness')).toBeTruthy()
    expect(screen.getByText('read-only blocked / scoped PR blocked')).toBeTruthy()
    expect(screen.getByText('worker readiness')).toBeTruthy()
    expect(screen.getByText('laptop Codex blocked / execution-ready no')).toBeTruthy()
    expect(screen.getByText('worker presence')).toBeTruthy()
    expect(screen.getByText('unknown / online no')).toBeTruthy()
    expect(screen.getByText('orchestration summary')).toBeTruthy()
    expect(screen.getByText(/Supervised read-only autonomy is blocked: runtime provenance is not clean/)).toBeTruthy()
    expect(screen.getByText('orchestration run graph')).toBeTruthy()
    expect(screen.getByText('nodes 4 / edges 3')).toBeTruthy()
    expect(screen.getByText('run graph nodes')).toBeTruthy()
    expect(screen.getByText('runs 1 / child 1 / worker 1 / reports 1')).toBeTruthy()
    expect(screen.getByText('run graph blockers')).toBeTruthy()
    expect(screen.getByText('worker_run_id worker-run-1 references missing parent run_id run-parent-1')).toBeTruthy()
    expect(screen.getByText('approval lifecycle')).toBeTruthy()
    expect(screen.getByText('available 1 / pending 1 / expired 1')).toBeTruthy()
    expect(screen.getByText('approval gaps')).toBeTruthy()
    expect(screen.getByText('duplicates 0 / consumed 0 / unavailable runs 1')).toBeTruthy()
    expect(screen.getByText('run lifecycle')).toBeTruthy()
    expect(screen.getByText('active 1 / terminal 2 / stop-cancel 1')).toBeTruthy()
    expect(screen.getByText('run gaps')).toBeTruthy()
    expect(screen.getByText('duplicates 0 / missing reports 1 / stale links 0')).toBeTruthy()
    expect(screen.getByText('report lifecycle')).toBeTruthy()
    expect(screen.getByText('open 1 / reviewed 0 / terminal 0')).toBeTruthy()
    expect(screen.getByText('report gaps')).toBeTruthy()
    expect(screen.getByText('duplicates 1 / overwrite conflicts 1 / missing 1 / stale links 0')).toBeTruthy()
    expect(screen.getAllByText('report contract').length).toBeGreaterThan(0)
    expect(screen.getByText('reports 1 / complete 0 / incomplete 1')).toBeTruthy()
    expect(screen.getByText('report completion')).toBeTruthy()
    expect(screen.getByText('ready 0 / blocked 2 / terminal 2')).toBeTruthy()
    expect(screen.getByText('report review queue')).toBeTruthy()
    expect(screen.getByText('items 3 / needs review 2 / missing 1 / mismatch 0')).toBeTruthy()
    expect(screen.getByText('result ingestion')).toBeTruthy()
    expect(screen.getByText('ready 1 / blocked 0 / reports 1')).toBeTruthy()
    expect(screen.getByText('stop/cancel control')).toBeTruthy()
    expect(screen.getByText('items 1 / stopping 0 / terminal 1 / mismatch 0')).toBeTruthy()
    expect(screen.getByText('top report review')).toBeTruthy()
    expect(screen.getByText('Laptop Codex reported scoped PR evidence.')).toBeTruthy()
    expect(screen.getByText('baseline execute lock')).toBeTruthy()
    expect(screen.getByText('accepted no / rollback no / handoff no')).toBeTruthy()
    expect(screen.getByText('report review blockers')).toBeTruthy()
    expect(screen.getByText('report_id report-worker has multiple append-only records, report_id report-worker attempts to overwrite append-only report fields: status, run_id run-parent-1 has no linked report, report_id report-worker still needs review')).toBeTruthy()
    expect(screen.getByText('report contract blockers')).toBeTruthy()
    expect(screen.getByText('report_id report-worker missing contract fields: result, evidence, tests, next lane, safety confirmation')).toBeTruthy()
    expect(screen.getByText('report completion blockers')).toBeTruthy()
    expect(screen.getByText('run run-parent-1 has no linked completion report, report_id report-worker still needs Jenny review before completion, report_id report-worker missing completion contract fields: result, evidence, tests, next lane, safety confirmation')).toBeTruthy()
    expect(screen.getByText('report completion gaps')).toBeTruthy()
    expect(screen.getByText('missing 1 / review 1 / rejected 0 / contract 2 / ingestion 0 / mismatch 0 / duplicates 0')).toBeTruthy()
    expect(screen.getByText('report queue reason')).toBeTruthy()
    expect(screen.getByText('report_id report-worker still needs Jenny review, report_id report-child still needs Jenny review, run_id run-parent-1 has no linked report')).toBeTruthy()
    expect(screen.getByText('result ingestion blockers')).toBeTruthy()
    expect(screen.getByText('No result ingestion blockers recorded')).toBeTruthy()
    expect(screen.getByText('result ingestion gaps')).toBeTruthy()
    expect(screen.getByText('duplicates 0 / unlinked 0 / mismatch 0 / redaction 0 / metadata 0 / safety 0')).toBeTruthy()
    expect(screen.getByText('stop/cancel blockers')).toBeTruthy()
    expect(screen.getByText('run run-stopped has no stop_reason, run run-stopped has no linked stop/cancel report')).toBeTruthy()
    expect(screen.getByText('child-agent status')).toBeTruthy()
    expect(screen.getByText('1 active / latest running')).toBeTruthy()
    expect(screen.getByText('child-agent objective')).toBeTruthy()
    expect(screen.getByText('Inspect bounded Mission Control context.')).toBeTruthy()
    expect(screen.getByText('child-agent report')).toBeTruthy()
    expect(screen.getByText('linked report found / needs review / report-child')).toBeTruthy()
    expect(screen.getByText('child instruction preview')).toBeTruthy()
    expect(screen.getAllByText('available yes / handoff ready no / manual yes').length).toBeGreaterThanOrEqual(2)
    expect(screen.getByText('child instruction prompt')).toBeTruthy()
    expect(screen.getByText(/Child agent: jenny-child/)).toBeTruthy()
    expect(screen.getByText(/Handoff readiness: blocked until child-agent blockers are cleared/)).toBeTruthy()
    expect(screen.getByText('laptop Codex worker-node')).toBeTruthy()
    expect(screen.getByText('laptop-codex / blocked')).toBeTruthy()
    expect(screen.getByText('worker-node objective')).toBeTruthy()
    expect(screen.getByText('Prepare bounded scoped PR packet.')).toBeTruthy()
    expect(screen.getByText('worker-node report')).toBeTruthy()
    expect(screen.getByText('required / linked report found / accepted / report-worker')).toBeTruthy()
    expect(screen.getByText('worker instruction preview')).toBeTruthy()
    expect(screen.getAllByText('available yes / handoff ready no / manual yes').length).toBeGreaterThanOrEqual(2)
    expect(screen.getByText('worker instruction prompt')).toBeTruthy()
    expect(screen.getByText(/Worker: codex on laptop-codex/)).toBeTruthy()
    expect(screen.getByText(/Codex must independently enforce repo\/worktree/)).toBeTruthy()
    expect(screen.getByText(/Handoff readiness: blocked until worker-node blockers are cleared/)).toBeTruthy()
    expect(screen.getByText('worker instruction blockers')).toBeTruthy()
    expect(screen.getByText('worker-node blockers')).toBeTruthy()
    expect(screen.getByText('worker presence blockers')).toBeTruthy()
    expect(screen.getAllByText('worker-node presence_status is not recorded').length).toBeGreaterThan(0)
    expect(screen.getAllByText('worker node offline').length).toBeGreaterThan(0)
    expect(screen.getByText('scoped PR blockers')).toBeTruthy()
    expect(screen.getByText('exact approved ApprovalRecord is required')).toBeTruthy()
    expect(screen.getByText('autonomy blockers')).toBeTruthy()
    expect(screen.getAllByText(/gateway git metadata is broken/).length).toBeGreaterThan(0)
    expect(screen.getByText('approval blockers')).toBeTruthy()
    expect(screen.getByText('run_id run-parent-1 references unavailable approval_id approval-old')).toBeTruthy()
    expect(screen.getByText('run blockers')).toBeTruthy()
    expect(screen.getByText('terminal run_id run-reportless has no linked report')).toBeTruthy()
    expect(screen.getByText('child-agent blockers')).toBeTruthy()
    expect(screen.getAllByText('report_id report-child still needs review').length).toBeGreaterThanOrEqual(2)
    expect(screen.getByText('child instruction blockers')).toBeTruthy()
    expect(screen.getByText(/Desktop can be current while phone\/web waits for a safe dashboard-only update/)).toBeTruthy()
    expect(screen.getByText('accepted-live head')).toBeTruthy()
    expect(screen.getByText('0f87620038d2')).toBeTruthy()
    expect(screen.getByText('default branch head')).toBeTruthy()
    expect(screen.getByText('c06898098b86')).toBeTruthy()
    expect(screen.getByText('deployed head')).toBeTruthy()
    expect(screen.getByText('9f8863c0bf28')).toBeTruthy()
    expect(screen.getByText('desktop app install')).toBeTruthy()
    expect(screen.getByText('separate laptop worker-node update; bottom-bar version is not changed by accepted-live/dashboard deploy')).toBeTruthy()
    expect(screen.queryByText('⌘K Command palette')).toBeNull()
    expect(screen.queryByText('All systems')).toBeNull()
    expect(screen.getByText('Outbound to Jenny')).toBeTruthy()
    expect(screen.getByText('Jenny replies')).toBeTruthy()
    expect(screen.getByRole('button', { name: 'Refresh bridge' })).toBeTruthy()
    expect(screen.getByText(/replied \/ jenny/)).toBeTruthy()
    expect(screen.getByText('Live reply refresh is on and read-only. Jenny can reply through the bridge; work still waits for the normal approval gates.')).toBeTruthy()
    expect(screen.getByText('Hermes health dashboard')).toBeTruthy()
    expect(screen.getByText('Profile storage usage')).toBeTruthy()
    expect(screen.getByText('Profile data')).toBeTruthy()
    expect(screen.getByText('State DB')).toBeTruthy()
    expect(screen.getByText('Sessions')).toBeTruthy()
    expect(screen.getByText('Recall files')).toBeTruthy()
    expect(screen.queryByText('Total memory files')).toBeNull()
    expect(screen.queryByText('MEMORY.md')).toBeNull()
    expect(screen.queryByText('USER.md')).toBeNull()
    expect(screen.queryByText('Memory cap')).toBeNull()
    expect(screen.queryByText('Memory %')).toBeNull()
    expect(screen.getByText('Mount max')).toBeTruthy()
    expect(screen.getByText('Mount used')).toBeTruthy()
    expect(screen.getAllByText('6.0 GB').length).toBeGreaterThan(0)
    expect(screen.getByText('3.4 GB')).toBeTruthy()
    expect(screen.getByText('2.6 GB')).toBeTruthy()
    expect(screen.getByText('Mount %')).toBeTruthy()
    expect(screen.getAllByText('16 GB').length).toBeGreaterThan(0)
    expect(screen.getAllByText('12 GB').length).toBeGreaterThan(0)
    expect(screen.getAllByText('76%').length).toBeGreaterThan(0)
    expect(screen.getByText('Kanban parked for later')).toBeTruthy()
    expect(screen.getByText('Advanced diagnostic records')).toBeTruthy()
    expect(screen.getAllByRole('heading', { name: 'Hermes / Mission Control' }).length).toBeGreaterThan(0)
    expect(screen.getByText('Hermes update lane')).toBeTruthy()
    expect(screen.getByRole('button', { name: 'Start Hermes update lane' })).toBeTruthy()
    expect(screen.getByText(/bottom-bar desktop app version is separate from accepted-live\/dashboard deploys/)).toBeTruthy()
    expect(screen.getAllByText('report contract').length).toBeGreaterThan(0)
    expect(screen.getByText('latest report contract')).toBeTruthy()
    expect(screen.getAllByText(/Missing:.*evidence.*tests/).length).toBeGreaterThan(0)
    expect(screen.getAllByText('1 active / 4 paused').length).toBeGreaterThan(0)
    expect(screen.getByText('Projects on hold')).toBeTruthy()

    for (const [, name] of realProjects) {
      expect((await screen.findAllByText(name)).length).toBeGreaterThan(0)
    }
    expect(screen.getAllByText('Primary project').length).toBeGreaterThanOrEqual(1)
  })

  it('keeps all five project chat rooms visible when project records are partially projected', async () => {
    getMissionControlProjects.mockResolvedValueOnce({
      count: 1,
      dispatch_enabled: false,
      manual_copy_only: true,
      projects: [
        {
          record: {
            current_goal: 'Make desktop the main workspace.',
            name: 'Hermes / Mission Control',
            next_recommended_lane: 'Desktop read-only workspace v1',
            project_id: 'project-hermes-mission-control',
            source_of_truth: 'Mission Control records',
            status: 'Live workspace'
          },
          record_type: 'ProjectRecord'
        }
      ],
      send_to_jenny_enabled: false
    })

    await renderMissionControl()

    expect(await screen.findByRole('region', { name: 'Project chat workspace' })).toBeTruthy()
    expect(screen.getAllByText('5 projects').length).toBeGreaterThan(0)
    for (const [, name] of realProjects) {
      expect(screen.getAllByText(name).length).toBeGreaterThan(0)
    }
    expect(screen.getAllByText('Paused until Jenny is stable').length).toBe(4)
  })

  it('parks Kanban until the real task board is reliable', async () => {
    await renderMissionControl()

    expect(await screen.findByText('Kanban parked for later')).toBeTruthy()
    expect(screen.getByText(/hidden from this daily view until it can show real tasks and reliable controls/)).toBeTruthy()
    expect(screen.queryByText('Project Kanban')).toBeNull()
    expect(screen.queryByRole('button', { name: /move card/i })).toBeNull()
    expect(screen.queryByRole('button', { name: /start work/i })).toBeNull()
  })

  it('renders the active Jenny OS lane as the only active project board', async () => {
    await renderMissionControl()

    const advanced = await screen.findByText('Advanced diagnostic records')
    expect(advanced).toBeTruthy()
    expect(screen.getByText('Active Jenny OS Lane')).toBeTruthy()
    expect(screen.getByText('Active lane count: 0')).toBeTruthy()
  })

  it('shows paused project rooms but keeps their Jenny actions disabled', async () => {
    await renderMissionControl()

    fireEvent.change(await screen.findByLabelText('Active project'), { target: { value: 'project-long-form-video' } })

    expect(screen.getByRole('heading', { name: 'Long-form Video' })).toBeTruthy()
    expect(screen.getAllByText('Paused').length).toBeGreaterThan(0)
    expect(screen.getByText('Paused until Jenny is stable. Review context only; sending work to Jenny is disabled for this project.')).toBeTruthy()
    expect(screen.getByText('This project is visible for planning context only. Resume it after the Mission Control/Jenny recovery lane is stable.')).toBeTruthy()
    expect(screen.getByText('Resume requirements')).toBeTruthy()
    expect(screen.getByText('Jenny challenge review clears the approach')).toBeTruthy()
    expect(screen.getByText('Travis approval is recorded before work resumes')).toBeTruthy()
    expect(screen.getByRole('button', { name: 'Send' })).toHaveProperty('disabled', true)
    expect(screen.queryByRole('button', { name: 'Ask Jenny to review first' })).toBeNull()
    expect(screen.queryByRole('button', { name: "Get Jenny's reply" })).toBeNull()
    expect(screen.getByRole('button', { name: 'Save challenge draft' })).toHaveProperty('disabled', true)
    expect(screen.getByRole('button', { name: 'Save read-only lane draft' })).toHaveProperty('disabled', true)
  })

  it('shows real project state, fallback empty-state copy, and disabled safety flags', async () => {
    await renderMissionControl()

    expect((await screen.findAllByText('Jenny finished the desktop architecture review.')).length).toBeGreaterThan(0)
    expect(screen.getByText('Manual record repair')).toBeTruthy()
    expect(screen.getByText('Save a missing Jenny report')).toBeTruthy()
    expect(screen.getByText('Use Mission Control backend with desktop frontend.')).toBeTruthy()
    expect(screen.getByText('dashboard overbuild · none')).toBeTruthy()
    expect(screen.getByText('reports/hermes/desktop-review.md')).toBeTruthy()
    expect(screen.getByText('Live report available')).toBeTruthy()
    expect(screen.getByText('2026-06-11T10:00:00Z (report)')).toBeTruthy()
    expect(screen.getAllByText('Desktop read-only workspace v1').length).toBeGreaterThan(0)
    expect(screen.getByText('Read-only status refresh (draft)')).toBeTruthy()
    expect(screen.getByText('Projects on hold')).toBeTruthy()
    expect(screen.getAllByText('Shorts Video').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Long-form Video').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Tool & Tally').length).toBeGreaterThan(0)
    expect(screen.getAllByText('send_to_jenny: disabled').length).toBeGreaterThan(0)
    expect(screen.getAllByText('dispatch: disabled').length).toBeGreaterThan(0)
    expect(screen.getAllByText('execution: disabled').length).toBeGreaterThan(0)
  })

  it('renders linked, suggested, and unassigned sessions without creating source-of-truth links', async () => {
    await renderMissionControl()

    expect((await screen.findAllByText('Project sessions')).length).toBeGreaterThan(0)
    expect(screen.getAllByText('1 linked').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Mission Control linked session').length).toBeGreaterThan(0)
    expect(screen.getByText('Suggested sessions — display-only')).toBeTruthy()
    expect(screen.getByText('Suggestions do not create links or become source-of-truth records.')).toBeTruthy()
    expect(screen.getAllByText('Suggested Mission Control session').length).toBeGreaterThan(0)
    expect(screen.getByText('Unassigned / General sessions')).toBeTruthy()
    expect(screen.getByText('2 recent · 1 suggestions')).toBeTruthy()
    expect(screen.getByText('General unassigned session')).toBeTruthy()
    expect(screen.getByText('Suggested: Hermes / Mission Control · display-only')).toBeTruthy()
    expect(screen.getByText('No suggested project')).toBeTruthy()

    expect(createMissionControlReport).not.toHaveBeenCalled()
    expect(createMissionControlSessionProjectLink).not.toHaveBeenCalled()
  })

  it('requires confirmation before suggested sessions write exactly one manual active link record', async () => {
    await renderMissionControl()

    fireEvent.click(await screen.findByRole('button', { name: 'Review link' }))
    expect(screen.getByRole('dialog')).toBeTruthy()
    expect(screen.getAllByText('Confirm suggested link').length).toBeGreaterThan(0)
    expect(screen.getByText('One append-only SessionProjectLinkRecord will be written.')).toBeTruthy()
    expect(screen.getByText('This does not edit the session database.')).toBeTruthy()
    expect(screen.getByText('This does not send work to Jenny.')).toBeTruthy()
    expect(screen.getByText('This does not dispatch anything.')).toBeTruthy()
    expect(screen.getByText('This does not enable routing.')).toBeTruthy()
    expect(screen.getByText('Suggestions are display-only until confirmed.')).toBeTruthy()
    expect(screen.getByText('Moving a link appends a newer record instead of changing old records.')).toBeTruthy()
    expect(createMissionControlSessionProjectLink).not.toHaveBeenCalled()

    const submit = screen.getByRole('button', { name: 'Confirm suggested link' })
    expect(submit).toHaveProperty('disabled', true)
    fireEvent.click(screen.getByLabelText('I understand this appends one Mission Control record only.'))
    fireEvent.click(submit)

    await waitFor(() => expect(createMissionControlSessionProjectLink).toHaveBeenCalledTimes(1))
    expect(createMissionControlSessionProjectLink).toHaveBeenCalledWith(
      expect.objectContaining({
        confidence: 'manual',
        cwd_snapshot: '/home/jenny/.hermes/hermes-runtime-session-links-573658a',
        lineage_root_id: 'root-suggested-hermes',
        link_method: 'manual',
        profile: 'default',
        project_id: 'project-hermes-mission-control',
        session_id: 'session-suggested-hermes',
        source: 'discord',
        status: 'active',
        title_snapshot: 'Suggested Mission Control session'
      })
    )
    expect(getMissionControlProjectSessions).toHaveBeenCalledTimes(2)
  })

  it('requires project selection and checkbox before manual unassigned links', async () => {
    await renderMissionControl()

    const manualButtons = await screen.findAllByRole('button', { name: 'Link manually' })
    fireEvent.click(manualButtons[1])

    const submit = screen.getByRole('button', { name: 'Append manual link record' })
    expect(submit).toHaveProperty('disabled', true)
    fireEvent.change(screen.getAllByLabelText('Project').at(-1)!, { target: { value: 'project-tool-tally' } })
    expect(submit).toHaveProperty('disabled', true)
    fireEvent.click(screen.getByLabelText('I understand this appends one Mission Control record only.'))
    fireEvent.click(submit)

    await waitFor(() => expect(createMissionControlSessionProjectLink).toHaveBeenCalledTimes(1))
    expect(createMissionControlSessionProjectLink).toHaveBeenCalledWith(
      expect.objectContaining({
        confidence: 'manual',
        lineage_root_id: 'root-general',
        link_method: 'manual',
        project_id: 'project-tool-tally',
        session_id: 'session-general',
        status: 'active'
      })
    )
  })

  it('moves linked sessions by appending a newer active record for the same durable session id', async () => {
    await renderMissionControl()

    fireEvent.click(await screen.findByRole('button', { name: 'Move link' }))
    fireEvent.change(screen.getAllByLabelText('Project').at(-1)!, { target: { value: 'project-tool-tally' } })
    fireEvent.click(screen.getByLabelText('I understand this appends one Mission Control record only.'))
    fireEvent.click(screen.getByRole('button', { name: 'Append superseding link record' }))

    await waitFor(() => expect(createMissionControlSessionProjectLink).toHaveBeenCalledTimes(1))
    expect(createMissionControlSessionProjectLink).toHaveBeenCalledWith(
      expect.objectContaining({
        confidence: 'manual',
        lineage_root_id: 'root-linked-hermes',
        link_method: 'manual',
        project_id: 'project-tool-tally',
        session_id: 'session-linked-hermes',
        status: 'active'
      })
    )
  })

  it('does not expose unlink, removal, bulk, or multi-select linking controls', async () => {
    await renderMissionControl()

    for (const label of [/unlink/i, /remove link/i, /link all/i, /confirm all/i, /bulk/i, /multi-select/i]) {
      expect(screen.queryByRole('button', { name: label })).toBeNull()
    }
  })

  it('de-emphasizes smoke records outside the primary workspace', async () => {
    await renderMissionControl()

    expect(await screen.findByText('Supporting / smoke records')).toBeTruthy()
    expect(screen.getByText(/Smoke Test Project/)).toBeTruthy()
    expect(screen.getByText(/de-emphasized smoke\/support record/)).toBeTruthy()
  })

  it('copies a bounded manual prompt without enabling send or dispatch', async () => {
    await renderMissionControl()

    const buttons = await screen.findAllByRole('button', { name: 'Copy next lane prompt' })
    fireEvent.click(buttons[0])

    await waitFor(() => expect(navigator.clipboard.writeText).toHaveBeenCalledTimes(1))
    const prompt = vi.mocked(navigator.clipboard.writeText).mock.calls[0][0]
    expect(prompt.length).toBeLessThanOrEqual(2000)
    expect(prompt).toContain('PROJECT NEXT LANE')
    expect(prompt).toContain('REVIEW PACKET')
    expect(prompt).toContain('Forbidden actions:')
    expect(prompt).toContain('Direct session send remains disabled')
    expect(screen.getByText(/Messages are saved/)).toBeTruthy()
  })

  it('shows project room controls and creates only inert challenge and lane drafts', async () => {
    await renderMissionControl()

    expect((await screen.findAllByRole('heading', { name: 'Hermes / Mission Control' })).length).toBeGreaterThan(0)
    expect(screen.getByText('Message Jenny')).toBeTruthy()
    expect(screen.getByText('Conversation')).toBeTruthy()
    expect(screen.getByText('Jenny status')).toBeTruthy()
    expect(screen.getByRole('region', { name: 'Latest Jenny outcome' })).toBeTruthy()
    expect(screen.getByText('Review before relying')).toBeTruthy()
    expect(screen.getAllByText('Current phase').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Last sent').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Reply state').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Elapsed').length).toBeGreaterThan(0)
    expect(screen.getByText('Work session')).toBeTruthy()
    expect(screen.getAllByText('Queued').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Jenny working').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Reply received').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Review next').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Safety details').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Request options').length).toBeGreaterThan(0)
    expect(screen.getAllByText(/Pending \d+/).length).toBeGreaterThan(0)
    expect(screen.getAllByText(/Replies \d+/).length).toBeGreaterThan(0)
    expect(screen.getAllByText(/Reply quality/).length).toBeGreaterThan(0)
    expect(screen.getAllByLabelText('Review latest Jenny reply').length).toBeGreaterThan(0)
    expect(screen.getByText('Phone-safe packet')).toBeTruthy()
    expect(screen.getByText('Previous sessions')).toBeTruthy()
    expect(screen.getByText('Hermes storage cleanup lane')).toBeTruthy()
    expect(screen.getByText('Jenny memory storage')).toBeTruthy()
    expect(screen.getAllByText(/2 profiles/).length).toBeGreaterThan(0)
    expect(screen.getAllByText('wahainspection').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Lane draft ok').length).toBeGreaterThan(0)
    expect(screen.getAllByText(/Use a bounded read-only workspace usability lane/).length).toBeGreaterThan(0)
    expect(screen.getAllByText(/Request intake: Needs request/).length).toBeGreaterThan(0)
    expect(screen.getByText('Review the Mission Control room.')).toBeTruthy()
    const transcript = within(screen.getByLabelText('Project chat transcript'))
    expect(transcript.getByText('testing. tell me a short story')).toBeTruthy()
    expect(transcript.getByText('fix the two way communication with codex through the bridge')).toBeTruthy()
    expect(transcript.getByText('Review the Mission Control room.')).toBeTruthy()
    expect(transcript.queryByText(/Project room request: Hermes/)).toBeNull()
    expect(transcript.queryByText(/Current brief: Replace Discord as Travis primary workspace/)).toBeNull()
    expect(transcript.queryByText(/Allowed: read approved context/)).toBeNull()
    expect(transcript.queryByText(/Forbidden: no direct session send/)).toBeNull()

    const composer = screen.getByPlaceholderText('Tell Jenny what you want to discuss or ask her to do next...')
    expect(screen.queryByRole('button', { name: 'Use spec-first prompt' })).toBeNull()
    expect((composer as HTMLTextAreaElement).value).toBe('')
    expect(screen.getAllByRole('button', { name: 'Looks good' }).length).toBeGreaterThan(0)
    expect(screen.getAllByRole('button', { name: 'Ask for evidence' }).length).toBeGreaterThan(0)
    expect(screen.getAllByRole('button', { name: 'Challenge' }).length).toBeGreaterThan(0)
    expect(screen.getAllByText('Reviewed: needs evidence').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Needs evidence').length).toBeGreaterThan(0)
    expect(screen.getAllByText(/Ask Jenny for exact files, commands, checks, CI\/runtime status/).length).toBeGreaterThan(0)
    fireEvent.click(screen.getAllByRole('button', { name: 'Ask for evidence' })[0])
    await waitFor(() => expect(createMissionControlJennyReplyReview).toHaveBeenCalledTimes(1))
    expect(createMissionControlJennyReplyReview).toHaveBeenCalledWith(
      expect.objectContaining({
        decision: 'needs_evidence',
        project_id: 'project-hermes-mission-control',
        response_id: 'github-bridge-request-1',
        reviewer: 'travis'
      })
    )
    expect((composer as HTMLTextAreaElement).value).toContain('needs stronger evidence')
    expect((composer as HTMLTextAreaElement).value).toContain('Do not take action. Report evidence only.')
    expect(createMissionControlGitHubBridgeRequest).not.toHaveBeenCalled()

    fireEvent.change(composer, {
      target: { value: 'Make the visible Mission Control page show project rooms on laptop and phone.' }
    })
    expect(screen.getAllByText(/Request intake: Ready/).length).toBeGreaterThan(0)
    fireEvent.click(screen.getByRole('button', { name: 'Copy phone-safe packet' }))
    await waitFor(() => expect(navigator.clipboard.writeText).toHaveBeenCalledTimes(1))
    expect(vi.mocked(navigator.clipboard.writeText).mock.calls[0][0]).toContain('Project room request:')
    expect(vi.mocked(navigator.clipboard.writeText).mock.calls[0][0]).toContain('Request intake:')
    expect(vi.mocked(navigator.clipboard.writeText).mock.calls[0][0]).toContain('Ready / Request is bounded enough for a guarded Jenny reply.')
    expect(vi.mocked(navigator.clipboard.writeText).mock.calls[0][0]).toContain('Jenny instruction:')
    expect(vi.mocked(navigator.clipboard.writeText).mock.calls[0][0]).toContain('Categories:')
    expect(vi.mocked(navigator.clipboard.writeText).mock.calls[0][0]).toContain('Blocking verdicts:')
    expect(vi.mocked(navigator.clipboard.writeText).mock.calls[0][0]).toContain('Structured handoff:')
    expect(vi.mocked(navigator.clipboard.writeText).mock.calls[0][0]).toContain('Challenge: question unclear, unsafe, or wrong-approach requests before implementation.')
    expect(vi.mocked(navigator.clipboard.writeText).mock.calls[0][0]).toContain('Evidence contract:')
    expect(vi.mocked(navigator.clipboard.writeText).mock.calls[0][0]).toContain('Recommendation: one-sentence next lane.')
    expect(vi.mocked(navigator.clipboard.writeText).mock.calls[0][0]).toContain('if evidence is missing, say "not proven"')

    fireEvent.click(screen.getByRole('button', { name: 'Send' }))
    await waitFor(() => expect(createMissionControlGitHubBridgeRequest).toHaveBeenCalledTimes(1))
    expect(createMissionControlGitHubBridgeRequest).toHaveBeenCalledWith(
      expect.objectContaining({
        from_agent: 'travis',
        message: expect.stringContaining('Project room request:'),
        project_id: 'project-hermes-mission-control',
        request_id: expect.stringContaining('mission-control-chat-'),
        to_agent: 'jenny',
        user_message: 'Make the visible Mission Control page show project rooms on laptop and phone.'
      })
    )
    expect(createMissionControlGitHubBridgeRequest).toHaveBeenCalledWith(
      expect.objectContaining({
        message: expect.stringContaining('Request intake:'),
      })
    )
    expect(createMissionControlGitHubBridgeRequest).toHaveBeenCalledWith(
      expect.objectContaining({
        message: expect.stringContaining('Structured handoff:')
      })
    )
    expect(createMissionControlGitHubBridgeRequest).toHaveBeenCalledWith(
      expect.objectContaining({
        message: expect.stringContaining('Evidence contract:')
      })
    )
    expect(createMissionControlJennyBridgeRequest).not.toHaveBeenCalled()

    fireEvent.change(composer, {
      target: { value: 'Make the visible Mission Control page show project rooms on laptop and phone.' }
    })
    fireEvent.click(screen.getByRole('button', { name: 'Save challenge draft' }))
    await waitFor(() => expect(createMissionControlChallengeReview).toHaveBeenCalledTimes(1))
    expect(createMissionControlChallengeReview).toHaveBeenCalledWith(
      expect.objectContaining({
        blocking_verdicts: ['requires_spec_update', 'blocks_lane_draft'],
        challenge_categories: ['questions_required', 'missing_context'],
        decision_state: 'needs_spec_first',
        project_id: 'project-hermes-mission-control',
        request_summary: 'Make the visible Mission Control page show project rooms on laptop and phone.'
      })
    )

    fireEvent.click(screen.getByRole('button', { name: 'Save read-only lane draft' }))
    await waitFor(() => expect(createMissionControlLaneRequest).toHaveBeenCalledTimes(1))
    expect(createMissionControlLaneRequest).toHaveBeenCalledWith(
      expect.objectContaining({
        forbidden_actions: expect.arrayContaining(['dispatch', 'automatic send']),
        project_id: 'project-hermes-mission-control',
        title: 'Read-only project room usability check'
      })
    )

    fireEvent.click(screen.getByRole('button', { name: 'Start Hermes update lane' }))
    await waitFor(() => expect(createMissionControlGitHubBridgeRequest).toHaveBeenCalledTimes(2))
    expect(createMissionControlGitHubBridgeRequest).toHaveBeenLastCalledWith(
      expect.objectContaining({
        from_agent: 'travis',
        message: expect.stringContaining('Hermes update lane request:'),
        project_id: 'project-hermes-mission-control',
        request_id: expect.stringContaining('mission-control-chat-'),
        to_agent: 'jenny',
        user_message: expect.stringContaining('Start a safe Hermes update readiness lane')
      })
    )
    expect(createMissionControlGitHubBridgeRequest.mock.calls.at(-1)?.[0].message).toContain('gateway update as a separate explicit lane')

    fireEvent.click(screen.getByRole('button', { name: 'Start storage cleanup lane' }))
    await waitFor(() => expect(createMissionControlGitHubBridgeRequest).toHaveBeenCalledTimes(3))
    expect(createMissionControlGitHubBridgeRequest).toHaveBeenLastCalledWith(
      expect.objectContaining({
        from_agent: 'travis',
        message: expect.stringContaining('Hermes storage cleanup lane request:'),
        project_id: 'project-hermes-mission-control',
        request_id: expect.stringContaining('mission-control-chat-'),
        to_agent: 'jenny',
        user_message: expect.stringContaining('Start a safe Hermes storage cleanup lane')
      })
    )
    expect(createMissionControlGitHubBridgeRequest.mock.calls.at(-1)?.[0].message).toContain('target of about 50% disk usage')
    expect(createMissionControlGitHubBridgeRequest.mock.calls.at(-1)?.[0].message).toContain('timestamped dry-run manifest')
    expect(createMissionControlGitHubBridgeRequest.mock.calls.at(-1)?.[0].message).toContain('Tool & Tally report-builder data')
    expect(createMissionControlGitHubBridgeRequest.mock.calls.at(-1)?.[0].message).toContain('With explicit cleanup approval')
    expect(createMissionControlJennyBridgeRequest).not.toHaveBeenCalled()
  })

  it('keeps paused project hold panels read-only', async () => {
    await renderMissionControl()

    await screen.findByText('Projects on hold')
    expect(screen.queryByRole('button', { name: 'Queue audit/proof lane' })).toBeNull()
    expect(screen.getAllByText('On hold. No work can be queued from this panel until the Mission Control/Jenny recovery lane is stable.').length).toBeGreaterThanOrEqual(4)
    expect(createMissionControlJennyBridgeRequest).not.toHaveBeenCalled()
  })

  it('auto-routes broad project messages to a spec-first Jenny challenge', async () => {
    await renderMissionControl()

    const composer = screen.getByPlaceholderText('Tell Jenny what you want to discuss or ask her to do next...')
    fireEvent.change(composer, { target: { value: 'make Jenny fully functional and autonomous' } })

    await waitFor(() => expect((composer as HTMLTextAreaElement).value).toBe('make Jenny fully functional and autonomous'))
    await waitFor(() => expect(screen.getAllByText(/Spec first/).length).toBeGreaterThan(0))
    expect(screen.getAllByText(/Jenny will challenge this request before planning any implementation/).length).toBeGreaterThan(0)
    expect(screen.getAllByText('Jenny must challenge first').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Question missing facts and unsafe assumptions.').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Push back on protected actions or broad scope.').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Return the smallest safe lane with evidence and approval needs.').length).toBeGreaterThan(0)

    fireEvent.click(screen.getByRole('button', { name: 'Send' }))

    await waitFor(() => expect(createMissionControlGitHubBridgeRequest).toHaveBeenCalledTimes(1))
    expect(createMissionControlGitHubBridgeRequest).toHaveBeenCalledWith(
      expect.objectContaining({
        from_agent: 'travis',
        message: expect.stringContaining('Spec-first request for Jenny:'),
        project_id: 'project-hermes-mission-control',
        to_agent: 'jenny',
        user_message: 'make Jenny fully functional and autonomous'
      })
    )
    expect(createMissionControlGitHubBridgeRequest).toHaveBeenCalledWith(
      expect.objectContaining({
        message: expect.stringContaining('Jenny, do not implement yet. First challenge the request like a senior engineer:')
      })
    )
    expect(createMissionControlGitHubBridgeRequest).toHaveBeenCalledWith(
      expect.objectContaining({
        message: expect.not.stringContaining('Project room request:')
      })
    )
    expect(createMissionControlJennyBridgeRequest).not.toHaveBeenCalled()
  })

  it('routes update and install requests through the approval challenge gate', async () => {
    await renderMissionControl()

    const composer = screen.getByPlaceholderText('Tell Jenny what you want to discuss or ask her to do next...')
    fireEvent.change(composer, { target: { value: 'update Hermes on the VPS and install the laptop worker node' } })

    await waitFor(() => expect(screen.getAllByText(/Approval check/).length).toBeGreaterThan(0))
    expect(screen.getAllByText(/Contains protected actions; Jenny should challenge scope and identify approvals before work/).length).toBeGreaterThan(0)

    fireEvent.click(screen.getByRole('button', { name: 'Send' }))

    await waitFor(() => expect(createMissionControlGitHubBridgeRequest).toHaveBeenCalledTimes(1))
    expect(createMissionControlGitHubBridgeRequest).toHaveBeenCalledWith(
      expect.objectContaining({
        message: expect.stringContaining('Current intake: Approval check / Contains protected actions'),
        user_message: 'update Hermes on the VPS and install the laptop worker node'
      })
    )
    expect(createMissionControlGitHubBridgeRequest).toHaveBeenCalledWith(
      expect.objectContaining({
        message: expect.stringContaining('First challenge the request like a senior engineer')
      })
    )
    await waitFor(() => expect(answerMissionControlGitHubBridgeOnce).toHaveBeenCalledWith({
      confirm_manual_hermes_answer: true,
      project_id: 'project-hermes-mission-control',
      request_id: 'github-bridge-request-created'
    }))
  })

  it('sends a chat message and immediately runs one guarded Jenny reply', async () => {
    let resolveAnswer: (value: unknown) => void = () => undefined
    answerMissionControlGitHubBridgeOnce.mockReturnValueOnce(new Promise(resolve => {
      resolveAnswer = resolve
    }))

    await renderMissionControl()

    fireEvent.change(await screen.findByLabelText('Message Jenny'), { target: { value: 'Please check the chat bridge.' } })
    const composer = screen.getByLabelText('Message Jenny') as HTMLTextAreaElement
    expect(screen.queryByRole('button', { name: /get.*jenny/i })).toBeNull()
    expect(screen.queryByRole('button', { name: /try jenny/i })).toBeNull()
    expect(screen.queryByRole('button', { name: /run jenny/i })).toBeNull()
    expect(screen.queryByRole('button', { name: 'Refresh replies' })).toBeNull()
    fireEvent.click(screen.getByRole('button', { name: 'Send' }))
    await waitFor(() => expect(composer.value).toBe(''))
    expect((await screen.findAllByText('Jenny is working')).length).toBeGreaterThanOrEqual(1)
    expect((await screen.findAllByText(/Mission Control sent the latest project message to Jenny/)).length).toBeGreaterThanOrEqual(2)
    await waitFor(() => expect(createMissionControlGitHubBridgeRequest).toHaveBeenCalledWith(
      expect.objectContaining({
        request_id: expect.stringContaining('mission-control-chat-'),
        user_message: 'Please check the chat bridge.'
      })
    ))
    await waitFor(() => expect(answerMissionControlGitHubBridgeOnce).toHaveBeenCalledTimes(1))
    expect(answerMissionControlGitHubBridgeOnce).toHaveBeenCalledWith({
      confirm_manual_hermes_answer: true,
      project_id: 'project-hermes-mission-control',
      request_id: 'github-bridge-request-created'
    })
    resolveAnswer({
      answered: true,
      dispatch_enabled: false,
      manual_start_only: true,
      response: {
        created_at: '2026-06-13T01:07:00Z',
        from_agent: 'jenny',
        message: 'Jenny answered the chat request.',
        project_id: 'project-hermes-mission-control',
        request_id: 'github-bridge-request-created',
        status: 'replied',
        to_agent: 'travis'
      },
      send_to_jenny_enabled: true,
      stored: true,
      timer_enabled: false,
      worker_enabled: false
    })
    expect(await screen.findByText('Jenny replied to the latest pending project message.')).toBeTruthy()
  })

  it('bounds long desktop Jenny bridge messages before sending', async () => {
    await renderMissionControl()

    const longRequest = (
      'Please inspect the current Mission Control bridge and report exact status for the desktop project chat grouping UI without changing files. '
    ).repeat(45)

    fireEvent.change(await screen.findByLabelText('Message Jenny'), { target: { value: longRequest } })
    fireEvent.click(screen.getByRole('button', { name: 'Send' }))

    await waitFor(() => expect(createMissionControlGitHubBridgeRequest).toHaveBeenCalledTimes(1))
    const payload = createMissionControlGitHubBridgeRequest.mock.calls[0][0] as { message: string; user_message: string }
    expect(payload.message.length).toBeLessThanOrEqual(1900)
    expect(payload.user_message.length).toBeLessThanOrEqual(1900)
    expect(payload.message).toContain('Project room request:')
    expect(payload.user_message).toContain('Please inspect the current Mission Control bridge')
    expect(payload.message).not.toContain('bridge field is too large')
  })

  it('shows plain language when the Jenny bridge is offline', async () => {
    createMissionControlGitHubBridgeRequest.mockRejectedValueOnce(
      new Error("Error invoking remote method 'hermes:api': Error: connect ECONNREFUSED 100.115.125.111:9119")
    )
    await renderMissionControl()

    fireEvent.change(await screen.findByLabelText('Message Jenny'), { target: { value: 'test' } })
    fireEvent.click(screen.getByRole('button', { name: 'Send' }))

    expect(await screen.findByText('Jenny bridge is offline. Start or reconnect the Hermes gateway, then send the message again.')).toBeTruthy()
    expect(screen.queryByText(/ECONNREFUSED/)).toBeNull()
    expect(answerMissionControlGitHubBridgeOnce).not.toHaveBeenCalled()
  })

  it('warns when accepted child or worker reports have mismatched lineage', async () => {
    const status = JSON.parse(JSON.stringify(await getMissionControlWorkspaceStatus()))
    const childMismatch = 'report_id report-child run_id other-child-run does not match linked child_run child-run-1'
    const workerMismatch = 'report_id report-worker run_id other-worker-run does not match linked worker_node_run worker-run-1'

    Object.assign(status.child_agent_orchestration.active_runs[0], {
      blocked_reasons: [childMismatch],
      linked_report_review_status: 'accepted',
      report_link_mismatch: true,
      report_link_mismatch_reason: childMismatch,
      report_link_status: 'linked_report_run_id_mismatch'
    })
    Object.assign(status.worker_node_orchestration.active_runs[0], {
      blocked_reasons: [workerMismatch],
      linked_report_review_status: 'accepted',
      report_link_mismatch: true,
      report_link_mismatch_reason: workerMismatch,
      report_link_status: 'linked_report_run_id_mismatch'
    })
    status.child_agent_orchestration.blocked_reasons = [childMismatch]
    status.worker_node_orchestration.blocked_reasons = [workerMismatch]
    status.report_review_queue.link_mismatch_count = 2
    status.operator_decision_packet.report_link_mismatch_count = 2
    status.operator_decision_packet.report_review_queue_link_mismatch_count = 2
    status.operator_decision_packet.result_ingestion_link_mismatch_count = 0
    status.operator_decision_packet.report_completion_link_mismatch_count = 0
    status.operator_decision_packet.stop_cancel_link_mismatch_count = 0
    getMissionControlWorkspaceStatus.mockResolvedValueOnce(status)

    await renderMissionControl()
    await screen.findByText('child-agent report')

    const childReport = statusItemValue('child-agent report')
    expect(childReport.textContent).toContain('linked report run id mismatch / accepted / mismatch yes')
    expect(childReport.textContent).toContain(childMismatch)
    expect(childReport.className).toContain('text-amber')

    const workerReport = statusItemValue('worker-node report')
    expect(workerReport.textContent).toContain('required / linked report run id mismatch / accepted / mismatch yes')
    expect(workerReport.textContent).toContain(workerMismatch)
    expect(workerReport.className).toContain('text-amber')
    expect(screen.getByText('items 3 / needs review 2 / missing 1 / mismatch 2')).toBeTruthy()
    expect(screen.getByText('mismatch 2 / queue 2 / ingestion 0 / completion 0 / stop 0')).toBeTruthy()
  })

  it('restores Jenny working status from bridge audit records after refresh', async () => {
    getMissionControlGitHubBridgeStatus.mockResolvedValue({
      count: 1,
      daemon_enabled: false,
      discord_automation_enabled: false,
      dispatch_enabled: false,
      display_only: true,
      execution_enabled: false,
      last_error: '',
      last_poll_at: '2026-06-13T02:01:00Z',
      last_response_at: '',
      last_response_request_id: '',
      last_status: 'hermes_answer_started',
      manual_start_only: true,
      mode: 'manual_hermes_answer',
      foreground_watch_supported: true,
      foreground_watch_running: false,
      model_routing_enabled: false,
      pending_count: 1,
      visible_pending_count: 1,
      background_pending_count: 0,
      pending_messages: [
        {
          record: {
            created_at: '2026-06-13T02:00:00Z',
            from_agent: 'travis',
            message: 'Project room request: Please inspect the current Mission Control bridge.',
            metadata: {
              user_message: 'Please inspect the current Mission Control bridge.'
            },
            project_id: 'project-hermes-mission-control',
            request_id: 'github-bridge-working-request',
            status: 'queued',
            to_agent: 'jenny'
          }
        }
      ],
      visible_pending_messages: [
        {
          record: {
            created_at: '2026-06-13T02:00:00Z',
            from_agent: 'travis',
            message: 'Project room request: Please inspect the current Mission Control bridge.',
            metadata: {
              user_message: 'Please inspect the current Mission Control bridge.'
            },
            project_id: 'project-hermes-mission-control',
            request_id: 'github-bridge-working-request',
            status: 'queued',
            to_agent: 'jenny'
          }
        }
      ],
      recent_messages: [
        {
          record: {
            created_at: '2026-06-13T02:00:00Z',
            from_agent: 'travis',
            message: 'Project room request: Please inspect the current Mission Control bridge.',
            metadata: {
              user_message: 'Please inspect the current Mission Control bridge.'
            },
            project_id: 'project-hermes-mission-control',
            request_id: 'github-bridge-working-request',
            status: 'queued',
            to_agent: 'jenny'
          }
        }
      ],
      response_messages: [],
      send_to_jenny_enabled: false,
      session_send_enabled: false,
      status_records: [
        {
          record: {
            created_at: '2026-06-13T02:01:00Z',
            handled_request_id: 'github-bridge-working-request',
            mode: 'manual_hermes_answer',
            pending_count: 1,
            status: 'hermes_answer_started',
            status_id: 'github-status-working'
          }
        }
      ],
      stored: false,
      timer_enabled: false,
      worker_enabled: false
    })

    await renderMissionControl()

    expect((await screen.findAllByText(/Jenny is working on the latest project message/)).length).toBeGreaterThan(0)
    expect((await screen.findAllByText('Jenny is working')).length).toBeGreaterThan(0)
    expect(answerMissionControlGitHubBridgeOnce).not.toHaveBeenCalled()
  })

  it('blocks desktop lane drafts when the newest challenge review is not clear', async () => {
    getMissionControlChallengeReviews.mockResolvedValue({
      challenge_reviews: [
        {
          record: {
            decision_state: 'clear_and_safe',
            project_id: 'project-hermes-mission-control',
            recommended_path: 'Older clear review.',
            request_summary: 'Old request',
            status: 'accepted',
            suggested_lane_title: 'Old clear lane'
          },
          record_type: 'ChallengeReviewRecord'
        },
        {
          record: {
            decision_state: 'needs_spec_first',
            project_id: 'project-hermes-mission-control',
            recommended_path: 'Newest review requires a spec first.',
            request_summary: 'New request',
            status: 'draft',
            suggested_lane_title: 'Blocked lane'
          },
          record_type: 'ChallengeReviewRecord'
        }
      ],
      count: 2,
      dispatch_enabled: false,
      manual_copy_only: true,
      send_to_jenny_enabled: false
    })

    await renderMissionControl()

    fireEvent.change(await screen.findByPlaceholderText('Tell Jenny what you want to discuss or ask her to do next...'), {
      target: { value: 'Start a broad Mission Control lane without a spec.' }
    })
    fireEvent.click(screen.getByRole('button', { name: 'Save read-only lane draft' }))

    expect(await screen.findByText('Latest challenge review is needs_spec_first. Resolve that before saving a lane request draft.')).toBeTruthy()
    expect(createMissionControlLaneRequest).not.toHaveBeenCalled()
  })

  it('allows desktop lane drafts when the newest challenge review is clear', async () => {
    getMissionControlChallengeReviews.mockResolvedValue({
      challenge_reviews: [
        {
          record: {
            decision_state: 'needs_spec_first',
            project_id: 'project-hermes-mission-control',
            recommended_path: 'Older review required a spec.',
            request_summary: 'Old request',
            status: 'draft',
            suggested_lane_title: 'Old blocked lane'
          },
          record_type: 'ChallengeReviewRecord'
        },
        {
          record: {
            decision_state: 'clear_and_safe',
            project_id: 'project-hermes-mission-control',
            recommended_path: 'Newest review cleared a bounded lane.',
            request_summary: 'New request',
            status: 'accepted',
            suggested_lane_title: 'Newest clear lane'
          },
          record_type: 'ChallengeReviewRecord'
        }
      ],
      count: 2,
      dispatch_enabled: false,
      manual_copy_only: true,
      send_to_jenny_enabled: false
    })

    await renderMissionControl()

    fireEvent.change(await screen.findByPlaceholderText('Tell Jenny what you want to discuss or ask her to do next...'), {
      target: { value: 'Inspect whether Project Rooms are usable now.' }
    })
    fireEvent.click(screen.getByRole('button', { name: 'Save read-only lane draft' }))

    await waitFor(() => expect(createMissionControlLaneRequest).toHaveBeenCalledTimes(1))
    expect(createMissionControlLaneRequest).toHaveBeenCalledWith(
      expect.objectContaining({
        project_id: 'project-hermes-mission-control',
        title: 'Newest clear lane'
      })
    )
  })

  it('builds distinct project-specific next-lane prompts for all five real projects', async () => {
    const { buildMissionControlCopyPrompt, summarizeWorkspaceStatus } = await import('./index')
    const status = summarizeWorkspaceStatus(await getMissionControlWorkspaceStatus())

    const prompts = realProjects.map(([project_id, name]) =>
      buildMissionControlCopyPrompt({
        project: {
          project_id,
          name,
          status: `${name} status`,
          current_goal: `${name} goal`,
          next_recommended_lane: `${name} next lane`,
          source_of_truth: 'Mission Control records'
        },
        report: null,
        state: null,
        status
      })
    )

    expect(new Set(prompts).size).toBe(5)

    for (const prompt of prompts) {
      expect(prompt.length).toBeLessThanOrEqual(2000)
      expect(prompt).toContain('Allowed actions:')
      expect(prompt).toContain('Forbidden actions:')
      expect(prompt).toContain('Preflight checks:')
      expect(prompt).toContain('Stop conditions:')
      expect(prompt).toContain('Expected report format:')
      expect(prompt).toContain('No prior report/result exists')
    }
  })

  it('keeps project-specific restrictions in the generated lane packets', async () => {
    const { buildMissionControlCopyPrompt, summarizeWorkspaceStatus } = await import('./index')
    const status = summarizeWorkspaceStatus(await getMissionControlWorkspaceStatus())

    const promptFor = (project_id: string, name: string) =>
      buildMissionControlCopyPrompt({
        project: {
          project_id,
          name,
          status: `${name} status`,
          current_goal: `${name} goal`,
          next_recommended_lane: `${name} next lane`,
          source_of_truth: 'Mission Control records'
        },
        report: null,
        state: null,
        status
      })

    const longForm = promptFor('project-long-form-video', 'Long-form Video')
    expect(longForm).toContain('adult animated explainer')
    expect(longForm).toContain('reusable character/prop workflow')
    expect(longForm).not.toContain('Improve Mission Control as the primary Desktop workspace')
    expect(longForm).not.toContain('Make Mission Control the primary Jenny workspace')

    const toolTally = promptFor('project-tool-tally', 'Tool & Tally')
    expect(toolTally).toContain('No payments')
    expect(toolTally).toContain('outreach')
    expect(toolTally).toContain('public launch')

    const waha = promptFor('project-waha-work', 'Waha Work')
    expect(waha).toContain('Waha profile/context')
    expect(waha).toContain('No cross-profile memory bleed')
    expect(waha).toContain('cross-contamination')
  })

  it('saves missing Jenny reports through the append-only reports/create route only', async () => {
    await renderMissionControl()

    const projectSelect = await screen.findByLabelText('Project')
    fireEvent.change(projectSelect, { target: { value: 'project-hermes-mission-control' } })
    fireEvent.change(screen.getByLabelText('Jenny report summary'), { target: { value: 'Current Hermes report' } })
    fireEvent.change(screen.getByLabelText('Latest result'), { target: { value: 'Desktop and mobile now read projected state.' } })
    fireEvent.change(screen.getByLabelText('Risks/blockers — one per line'), { target: { value: 'proxy 9121 mismatch' } })
    fireEvent.change(screen.getByLabelText('Artifact/report links — one per line'), { target: { value: 'reports/hermes/current.md' } })
    fireEvent.click(screen.getByRole('button', { name: 'Save missing report' }))

    await waitFor(() => expect(createMissionControlReport).toHaveBeenCalledTimes(1))
    expect(createMissionControlReport).toHaveBeenCalledWith(
      expect.objectContaining({
        artifact_links: ['reports/hermes/current.md'],
        project_id: 'project-hermes-mission-control',
        result: 'Desktop and mobile now read projected state.',
        risks: ['proxy 9121 mismatch'],
        summary: 'Current Hermes report'
      })
    )
    expect(screen.getByText(/Use project chat for guarded Jenny messages/i)).toBeTruthy()
  })

  it('keeps Mission Control view source free of disallowed POST, dispatch wiring, timers, storage, and workers', async () => {
    const source = await import('./index?raw')
    const text = source.default as string

    expect(text).toContain('createMissionControlReport')
    expect(text).toContain('createMissionControlSessionProjectLink')
    expect(text).toContain('isNoPendingBridgeError')
    expect(text).toContain('hasGitHubBridgeSignal')
    expect(text).toContain('normalizedBridgeError')
    expect(text).toContain('const githubError = String(githubBridgeStatus.last_error || \'\')')
    expect(text).toContain('const legacyError = String(bridgeStatus.last_error || \'\')')
    expect(text).toContain('hasGitHubBridgeSignal(githubBridgeStatus) ? \'\' : legacyError')
    expect(text.indexOf('const githubError = String(githubBridgeStatus.last_error || \'\')')).toBeLessThan(
      text.indexOf('const legacyError = String(bridgeStatus.last_error || \'\')')
    )
    expect(text).toContain('Jenny is caught up. Send a new message to start the next reply.')

    for (const forbidden of [
      '.post(',
      '/dispatch',
      '/execute',
      '/api/status',
      '/api/plugins/kanban/tasks',
      'getStatus(',
      'PATCH',
      'DELETE',
      '9121',
      '/api/sessions/',
      'session-send',
      'sendSession',
      'localStorage',
      'sessionStorage',
      'setTimeout',
      'Worker(',
      'new Worker'
    ]) {
      expect(text).not.toContain(forbidden)
    }
  })

  it('fails closed before Desktop Mission Control GitHub bridge writes when live flags are unsafe', async () => {
    const source = await import('./index?raw')
    const text = source.default as string

    for (const expected of [
      'function missionControlGitHubBridgeSafety(',
      'reasons.push(\'GitHub bridge status not loaded\')',
      'status.manual_start_only !== true',
      '[\'would_execute\', \'would_execute must remain false\']',
      '[\'dispatch_enabled\', \'dispatch_enabled must remain false\']',
      '[\'execution_enabled\', \'execution_enabled must remain false\']',
      '[\'session_send_enabled\', \'session_send_enabled must remain false\']',
      '[\'worker_dispatch_enabled\', \'worker_dispatch_enabled must remain false\']',
      '[\'worker_enabled\', \'worker_enabled must remain false\']',
      '[\'timer_enabled\', \'timer_enabled must remain false\']',
      '[\'daemon_enabled\', \'daemon_enabled must remain false\']',
      '[\'discord_automation_enabled\', \'discord_automation_enabled must remain false\']',
      '[\'model_routing_enabled\', \'model_routing_enabled must remain false\']',
      'function missionControlBridgeBlockedMessage(safety: MissionControlBridgeSafety): string',
      'const githubBridgeSafety = missionControlGitHubBridgeSafety(githubBridgeStatus)',
      'const bridgeActionDisabled = saving || paused || !githubBridgeSafety.safe',
      'disabled={bridgeActionDisabled}',
      'Manual Jenny bridge blocked:'
    ]) {
      expect(text).toContain(expected)
    }

    const queue = text.slice(text.indexOf('async function queueJennyBridgeRequest'), text.indexOf('async function runJennyOnce'))
    const runOnce = text.slice(text.indexOf('async function runJennyOnce'), text.indexOf('async function reviewJennyReply'))
    const updateLane = text.slice(text.indexOf('async function queueHermesUpdateLane'), text.indexOf('async function queueHermesStorageCleanupLane'))
    const cleanupLane = text.slice(text.indexOf('async function queueHermesStorageCleanupLane'), text.indexOf('async function saveChallengeDraft'))

    for (const block of [queue, runOnce, updateLane, cleanupLane]) {
      expect(block).toContain('const bridgeSafety = missionControlGitHubBridgeSafety(snapshot.githubBridgeStatus)')
      expect(block).toContain('if (!bridgeSafety.safe)')
      expect(block).toContain('setProjectRoomMessage(missionControlBridgeBlockedMessage(bridgeSafety))')
    }

    expect(queue.indexOf('if (!bridgeSafety.safe)')).toBeLessThan(queue.indexOf('createMissionControlGitHubBridgeRequest'))
    expect(runOnce.indexOf('if (!bridgeSafety.safe)')).toBeLessThan(runOnce.indexOf('answerMissionControlGitHubBridgeOnce'))
    expect(updateLane.indexOf('if (!bridgeSafety.safe)')).toBeLessThan(updateLane.indexOf('createMissionControlGitHubBridgeRequest'))
    expect(cleanupLane.indexOf('if (!bridgeSafety.safe)')).toBeLessThan(cleanupLane.indexOf('createMissionControlGitHubBridgeRequest'))
  })
})
