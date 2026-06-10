(function () {
  "use strict";

  const SDK = window.__HERMES_PLUGIN_SDK__;
  if (!SDK || !window.__HERMES_PLUGINS__) return;

  const React = SDK.React;
  const h = React.createElement;
  const hooks = SDK.hooks;
  const C = SDK.components;

  const SUMMARY_URL = "/api/plugins/mission-control-governance/summary";
  const START_GATE_URL = "/api/plugins/mission-control-governance/start-gate";
  const START_GATE_EVALUATE_URL = "/api/plugins/mission-control-governance/start-gate/evaluate";
  const LANE_PREFLIGHT_EVALUATE_URL = "/api/plugins/mission-control-governance/lane-preflight/evaluate";
  const MODEL_REGISTRY_URL = "/api/plugins/mission-control-governance/model-registry";
  const TASK_CONTROL_ENVELOPES_URL = "/api/plugins/mission-control-governance/task-control-envelopes";
  const START_GATE_CHECKS_URL = "/api/plugins/mission-control-governance/start-gate-checks";
  const APPROVAL_SLICES_URL = "/api/plugins/mission-control-governance/approval-slices";
  const EVIDENCE_CARDS_URL = "/api/plugins/mission-control-governance/evidence-cards";
  const OPERATOR_ACTIONS_URL = "/api/plugins/mission-control-governance/operator-actions";
  const WORKSPACE_STATUS_URL = "/api/plugins/mission-control-governance/workspace-status";
  const RECORDS_URL = "/api/plugins/mission-control-governance/records?limit=25";
  const WORKSPACE_PROJECTS_URL = "/api/plugins/mission-control-governance/workspace/projects";
  const WORKSPACE_PROJECT_CREATE_URL = "/api/plugins/mission-control-governance/workspace/projects/create";
  const WORKSPACE_LANE_REQUESTS_URL = "/api/plugins/mission-control-governance/workspace/lane-requests";
  const WORKSPACE_LANE_REQUEST_CREATE_URL = "/api/plugins/mission-control-governance/workspace/lane-requests/create";
  const WORKSPACE_REPORTS_URL = "/api/plugins/mission-control-governance/workspace/reports";
  const WORKSPACE_REPORT_CREATE_URL = "/api/plugins/mission-control-governance/workspace/reports/create";
  const SCHEMA_URL = "/api/plugins/mission-control-governance/schema";
  const RECORD_DETAIL_URL = function (index) {
    return "/api/plugins/mission-control-governance/records/" + encodeURIComponent(String(index));
  };
  const SAMPLE_EVALUATOR_ENVELOPE = {
    envelope_id: "dashboard-sample-start-gate",
    active_lane: "PR-M display-only Start Gate evaluator panel",
    mode: "bounded display-only sample",
    allowed_actions: [
      "render inert evaluator output",
      "call bounded evaluator API",
    ],
    forbidden_actions: [
      "live enforcement",
      "approval execution",
      "tool execution",
      "broad context loading",
      "persistent writes",
    ],
    current_repo: "Travisaggie04/hermes-agent",
    expected_systems_files: [
      "plugins/mission-control-governance/dashboard/dist/index.js",
      "plugins/mission-control-governance/dashboard/dist/style.css",
    ],
    stop_condition: "Stop after display-only evaluator result is shown.",
    other_threads_excluded: [
      "Signal Room",
      "Instagram",
      "unrelated PR cleanup",
    ],
    report_requirements: [
      "files changed",
      "tests run",
      "safety confirmation",
    ],
    token_context_policy: "compact fixed sample only",
    metadata: {
      authoritative_remote: "travis",
      worktree_state: "clean sample",
    },
  };

  async function getJSON(url) {
    const headers = {};
    const token = window.__HERMES_SESSION_TOKEN__ || "";
    if (token) headers["X-Hermes-Session-Token"] = token;
    const res = await fetch(url, { headers });
    if (!res.ok) throw new Error(String(res.status));
    return res.json();
  }

  async function postJSON(url, body) {
    const headers = { "Content-Type": "application/json" };
    const token = window.__HERMES_SESSION_TOKEN__ || "";
    if (token) headers["X-Hermes-Session-Token"] = token;
    const res = await fetch(url, {
      method: "POST",
      headers: headers,
      body: JSON.stringify(body),
    });
    if (!res.ok) throw new Error(String(res.status));
    return res.json();
  }

  function StatCard(props) {
    return h(C.Card, { className: "mcg-stat" },
      h(C.CardContent, { className: "mcg-stat-body" },
        h("span", { className: "mcg-stat-label" }, props.label),
        h("strong", null, props.value),
        props.hint ? h("span", { className: "mcg-stat-hint" }, props.hint) : null
      )
    );
  }

  function recordTitle(item) {
    const body = item && item.record ? item.record : {};
    return body.title || body.statement || body.active_lane || body.summary || body.mission_id || body.goal_id || "";
  }

  function formatStoreState(status, error) {
    if (error) return status + ": " + error;
    if (status === "missing") return "Record store has not been created.";
    if (status === "empty") return "Record store is empty.";
    if (status === "malformed") return "Record store cannot be read.";
    return "Record store is readable.";
  }

  function formatLinkedKanbanTask(link) {
    if (!link) return "No Kanban link";
    const board = link.board_name || link.board_id || "board unknown";
    const task = link.task_title || link.task_id || "task unknown";
    const status = link.task_status || link.link_state || "state unknown";
    return board + " / " + task + " / " + status;
  }

  function PrettyRecord(props) {
    return h("pre", { className: "mcg-json" }, JSON.stringify(props.value || {}, null, 2));
  }

  function listText(value) {
    if (!Array.isArray(value) || value.length === 0) return "None";
    return value.join(", ");
  }

  function boolText(value) {
    return value ? "true" : "false";
  }

  function valueText(value, fallback) {
    if (value === true) return "true";
    if (value === false) return "false";
    if (value === null || typeof value === "undefined" || value === "") return fallback || "Unknown";
    if (Array.isArray(value)) return value.length ? value.join(", ") : (fallback || "None");
    return String(value);
  }

  function shortHead(value) {
    const text = valueText(value, "Unknown");
    return text.length > 12 ? text.slice(0, 12) : text;
  }

  function WorkspaceField(props) {
    return h("div", { className: "mcg-workspace-field" },
      h("span", { className: "mcg-start-label" }, props.label),
      h("strong", null, valueText(props.value, props.fallback))
    );
  }

  function WorkspaceList(props) {
    const items = props.items || [];
    return h("div", { className: "mcg-workspace-section" },
      h("div", { className: "mcg-workspace-section-title" }, props.title),
      h("div", { className: "mcg-workspace-list" },
        items.map(function (item, index) {
          return h("span", { className: "mcg-workspace-pill", key: props.title + "-" + index }, item);
        })
      )
    );
  }

  function listFromText(value) {
    return String(value || "")
      .split("\n")
      .map(function (item) { return item.trim(); })
      .filter(Boolean);
  }

  function bulletListFromText(value, fallback) {
    const items = listFromText(value);
    if (!items.length) return "- " + (fallback || "None");
    return items.map(function (item) { return "- " + item; }).join("\n");
  }

  function makeHandoffPrompt(form, workspaceStatus) {
    const accepted = workspaceStatus.accepted_baseline || {};
    const rollback = workspaceStatus.rollback_baseline || {};
    const lane = workspaceStatus.lane || {};
    const safety = workspaceStatus.safety || {};
    const staleContext = workspaceStatus.stale_context || {};
    const warnings = Array.isArray(staleContext.warnings) ? staleContext.warnings : [];
    const staleBlock = warnings.length
      ? [
        "STOP: Mission Control stale-context warnings are present",
        warnings.map(function (item) { return "- " + item; }).join("\n"),
        "Do not proceed until this is resolved.",
        "",
      ].join("\n")
      : "";
    const targetLines = [];
    if (form.target.trim()) {
      targetLines.push("Target repo/path/branch:");
      targetLines.push(form.target.trim());
      targetLines.push("");
    }
    if (form.notes.trim()) {
      targetLines.push("Notes:");
      targetLines.push(form.notes.trim());
      targetLines.push("");
    }
    return [
      staleBlock,
      "Active lane:",
      form.laneName.trim() || "<lane name>",
      "",
      "Mode:",
      form.mode.trim() || "Draft-only Mission Control handoff packet",
      "",
      "Objective:",
      form.objective.trim() || "<objective>",
      "",
      "Allowed actions:",
      bulletListFromText(form.allowedActions, "Read context and report only"),
      "",
      "Forbidden actions:",
      bulletListFromText(form.forbiddenActions, "No deploy, restart, record, config, code, or live mutation unless separately approved"),
      "",
      "Stop conditions:",
      bulletListFromText(form.stopConditions, "Stop if preflight fails or scope changes"),
      "",
      "Expected report format:",
      bulletListFromText(form.reportFormat, "Preflight, actions taken, verification, risks, no-mutation confirmation"),
      "",
      targetLines.join("\n"),
      "Accepted baseline:",
      "- runtime=" + valueText(accepted.runtime_path, "unknown"),
      "- head=" + valueText(accepted.head, "unknown"),
      "",
      "Rollback baseline:",
      "- runtime=" + valueText(rollback.runtime_path, "unknown"),
      "- head=" + valueText(rollback.head, "unknown"),
      "",
      "Mission Control lane limits:",
      "- max_active_lane=" + valueText(lane.max_active_lane, "1"),
      "- active_lane_count=" + valueText(lane.active_lane_count, "0"),
      "- dispatch_in_gateway=" + valueText(safety.dispatch_in_gateway, "false"),
      "",
      "Inert safety flags:",
      "- display_only=true",
      "- dry_run_only=true",
      "- execution_enabled=false",
      "- dispatch_in_gateway=false",
      "- model_routing=false",
      "- queue_mutation=false",
      "- waha_mutation=false",
      "- enforcement_enabled=false",
      "",
      "Manual transport only — paste into Discord. This does not start work.",
      "Draft packet only. This is not an active lane.",
    ].filter(function (part) { return part !== "" || part === ""; }).join("\n").replace(/\n{3,}/g, "\n\n").trim();
  }


  const PROJECT_WORKSPACE_CARDS = [
    {
      name: "Hermes / Mission Control",
      status: "Live accepted baseline; workspace v1 is display/manual-copy only.",
      current_goal: "Make Mission Control the obvious operating surface before enabling any execution path.",
      last_report_summary: "PR #51 deployed the handoff builder usability fix and accepted the handoffbuilder baseline.",
      next_recommended_lane: "Project Workspace v1 static cards PR: no backend, no records, no dispatch.",
      mistakes_guards: "Guard against gateway restarts, token printing, stale baseline drift, and accidental runtime enforcement.",
    },
    {
      name: "Long-form Video",
      status: "Planning/toolchain proof lane; no publishing from Mission Control.",
      current_goal: "Keep adult animated long-form work on the best-product toolchain path.",
      last_report_summary: "Toolchain direction favors character-rig proofs and HyperFrames assembly before long content runs.",
      next_recommended_lane: "Read-only status refresh or bounded proof packet for the video profile.",
      mistakes_guards: "Guard against avatar-first fallback, static-card regression, unapproved paid renders, and public posting.",
    },
    {
      name: "Shorts Video",
      status: "Production strategy exists; posting remains gated.",
      current_goal: "Produce source-backed short-form concepts with strong hooks and visible review packages.",
      last_report_summary: "Signal Room and Impossible Footage lanes require research-backed packaging and proof review before publishing.",
      next_recommended_lane: "Manual-copy research or review packet lane for a specific short concept.",
      mistakes_guards: "Guard against generic AI clips, weak hooks, skipped source checks, paid API drift, and public posting.",
    },
    {
      name: "Tool & Tally",
      status: "Pre-launch gated; customer/public actions require explicit approval.",
      current_goal: "Keep owner-facing evidence-first pages and paid-order monitoring stable without accidental launch actions.",
      last_report_summary: "Public site and API exist, but outreach, paid delivery, and customer sends remain approval-gated.",
      next_recommended_lane: "Read-only status check or critical hardening packet only.",
      mistakes_guards: "Guard against payment changes, public intake drift, outreach sends, customer delivery, and private asset leaks.",
    },
    {
      name: "Waha Work",
      status: "Owner-side engineering workspace; isolated from Main Jenny execution.",
      current_goal: "Support Waha inspection/reporting work with exact, review-only engineering packets.",
      last_report_summary: "Waha work should stay in the Waha profile with simple management summaries and review gates.",
      next_recommended_lane: "Manual-copy Waha profile handoff for one bounded document, tracker, or review task.",
      mistakes_guards: "Guard against mixing Waha context into Main Jenny memory, unapproved figures, and management-ready claims without review.",
    },
  ];

  function makeProjectWorkspacePrompt(project, workspaceStatus, laneDraft) {
    const accepted = workspaceStatus.accepted_baseline || {};
    const lane = workspaceStatus.lane || {};
    const safety = workspaceStatus.safety || {};
    const draft = laneDraft || {};
    return [
      "Active lane:",
      draft.title || project.next_recommended_lane,
      "",
      "Mode:",
      draft.mode || "Read-only/manual-copy Mission Control project workspace lane.",
      "",
      "Project:",
      project.name,
      "",
      "Objective:",
      draft.objective || "Use this project card as context, then inspect only the approved source of truth before recommending work.",
      "",
      "Allowed actions:",
      "- Read approved context",
      "- Report status and next safe lane",
      "- Propose bounded manual-copy prompt",
      "",
      "Forbidden actions:",
      "- No dispatch, execution, records beyond the approved workspace record, queue mutation, Waha mutation, model routing, enforcement, deploy, restart, config mutation, or public/customer action unless separately approved",
      "",
      "Stop conditions:",
      "- Stop if workspace-status preflight fails",
      "- Stop if the request needs live mutation or a different profile",
      "- Stop if project source of truth is missing or stale",
      "",
      "Expected report format:",
      "- preflight",
      "- current project state",
      "- recommended next lane",
      "- risks/guards",
      "- no-mutation confirmation",
      "",
      "Project state:",
      "- status=" + valueText(project.status, "unknown"),
      "- current_goal=" + valueText(project.current_goal, "unknown"),
      "- last_report_summary=" + valueText(project.last_report_summary, "not recorded"),
      "- next_recommended_lane=" + valueText(project.next_recommended_lane, "unknown"),
      "- mistakes_guards=" + valueText(project.mistakes_guards, "none"),
      "",
      "Accepted baseline:",
      "- runtime=" + valueText(accepted.runtime_path, "unknown"),
      "- head=" + valueText(accepted.head, "unknown"),
      "- active_lane_count=" + valueText(lane.active_lane_count, "0"),
      "- dispatch_in_gateway=" + valueText(safety.dispatch_in_gateway, "false"),
      "",
      "Manual transport only — paste into Discord. This does not start work.",
      "Draft packet only. This is not an active lane.",
    ].join("\n").trim();
  }

  function projectFromRecord(item) {
    return item && item.record ? item.record : null;
  }

  function laneRequestFromRecord(item) {
    return item && item.record ? item.record : null;
  }

  function reportFromRecord(item) {
    return item && item.record ? item.record : null;
  }

  function ProjectWorkspaceCard(props) {
    const project = props.project;
    return h("div", { className: "mcg-project-card" },
      h("div", { className: "mcg-project-card-head" },
        h("div", { className: "mcg-workspace-section-title" }, project.name),
        h("span", { className: "mcg-badge" }, project.project_id ? "Durable" : "Seed")
      ),
      h(WorkspaceField, { label: "status", value: project.status }),
      h(WorkspaceField, { label: "current goal", value: project.current_goal }),
      h(WorkspaceField, { label: "next recommended lane", value: project.next_recommended_lane }),
      h("div", { className: "mcg-project-actions" },
        h("span", { className: "mcg-copy-control", role: "link", tabIndex: 0, onClick: function () { props.onOpen(project); }, onKeyDown: function (event) { if (event.key === "Enter" || event.key === " ") props.onOpen(project); } }, "Open Project"),
        h("span", { className: "mcg-copy-control", role: "link", tabIndex: 0, onClick: function () { props.onCopy(makeProjectWorkspacePrompt(project, props.workspaceStatus || {})); }, onKeyDown: function (event) { if (event.key === "Enter" || event.key === " ") props.onCopy(makeProjectWorkspacePrompt(project, props.workspaceStatus || {})); } }, "Copy prompt")
      )
    );
  }

  function LaneRequestDraftForm(props) {
    const useState = hooks.useState;
    const titleState = useState("");
    const objectiveState = useState("");
    const title = titleState[0];
    const setTitle = titleState[1];
    const objective = objectiveState[0];
    const setObjective = objectiveState[1];
    function submitDraft() {
      props.onCreate({ title: title, objective: objective });
      setTitle("");
      setObjective("");
    }
    return h("div", { className: "mcg-project-lane-draft" },
      h("div", { className: "mcg-workspace-section-title" }, "Create durable lane request draft"),
      h("p", { className: "mcg-muted" }, "Append-only record. No send, dispatch, queue, Waha, model routing, enforcement, or hidden worker."),
      h("label", { className: "mcg-handoff-field" },
        h("span", { className: "mcg-start-label" }, "Lane title"),
        h("input", { className: "mcg-handoff-input", value: title, placeholder: "Read-only project status refresh", onChange: function (event) { setTitle(event.target.value); } })
      ),
      h("label", { className: "mcg-handoff-field" },
        h("span", { className: "mcg-start-label" }, "Objective"),
        h("textarea", { className: "mcg-handoff-textarea", rows: 3, value: objective, placeholder: "Inspect current project state and recommend the next safe lane.", onChange: function (event) { setObjective(event.target.value); } })
      ),
      h("span", { className: "mcg-copy-control", role: "link", tabIndex: 0, onClick: submitDraft, onKeyDown: function (event) { if (event.key === "Enter" || event.key === " ") submitDraft(); } }, "Save lane request draft")
    );
  }

  function ManualJennyReportInbox(props) {
    const useState = hooks.useState;
    const summaryState = useState("");
    const resultState = useState("");
    const nextLaneState = useState("");
    const summary = summaryState[0];
    const setSummary = summaryState[1];
    const result = resultState[0];
    const setResult = resultState[1];
    const nextLane = nextLaneState[0];
    const setNextLane = nextLaneState[1];
    const lanes = props.laneRequests || [];
    const reports = props.reports || [];

    function submitReport() {
      props.onCreate({
        summary: summary,
        result: result,
        next_recommended_lane: nextLane,
        lane_request_id: lanes[0] ? lanes[0].lane_request_id : "",
      });
      setSummary("");
      setResult("");
      setNextLane("");
    }

    return h("div", { className: "mcg-manual-report-inbox" },
      h("div", { className: "mcg-workspace-section-title" }, "Manual Jenny Report Inbox"),
      h("p", { className: "mcg-muted" }, "Paste Jenny’s report manually and attach it to this project and optional lane request. Append-only record; no callback, dispatch, queue, Waha, model routing, enforcement, or hidden worker."),
      h("label", { className: "mcg-handoff-field" },
        h("span", { className: "mcg-start-label" }, "Report summary"),
        h("textarea", { className: "mcg-handoff-textarea", rows: 3, value: summary, placeholder: "Short report summary", onChange: function (event) { setSummary(event.target.value); } })
      ),
      h("label", { className: "mcg-handoff-field" },
        h("span", { className: "mcg-start-label" }, "Result"),
        h("textarea", { className: "mcg-handoff-textarea", rows: 3, value: result, placeholder: "What Jenny completed or found", onChange: function (event) { setResult(event.target.value); } })
      ),
      h("label", { className: "mcg-handoff-field" },
        h("span", { className: "mcg-start-label" }, "Next recommended lane"),
        h("input", { className: "mcg-handoff-input", value: nextLane, placeholder: "Optional next lane", onChange: function (event) { setNextLane(event.target.value); } })
      ),
      h("span", { className: "mcg-copy-control", role: "link", tabIndex: 0, onClick: submitReport, onKeyDown: function (event) { if (event.key === "Enter" || event.key === " ") submitReport(); } }, "Save Jenny report manually"),
      h("div", { className: "mcg-project-report-list" },
        h("div", { className: "mcg-workspace-section-title" }, "Saved Jenny reports"),
        reports.length ? reports.map(function (report) {
          return h("div", { className: "mcg-compact-row", key: report.report_id },
            h("strong", null, report.summary),
            h("span", null, report.result || "Manual report record"),
            h("span", null, "next: " + valueText(report.next_recommended_lane, "none"))
          );
        }) : h("p", { className: "mcg-muted" }, "No manual Jenny reports saved for this project yet.")
      )
    );
  }

  function ProjectWorkspacePanel(props) {
    const useState = hooks.useState;
    const useEffect = hooks.useEffect;
    const copyState = useState("");
    const copyMessage = copyState[0];
    const setCopyMessage = copyState[1];
    const recordsState = useState({ loading: true, projects: [], laneRequests: [], reports: [], error: "" });
    const records = recordsState[0];
    const setRecords = recordsState[1];
    const selectedState = useState(null);
    const selectedProject = selectedState[0] || (records.projects[0] ? projectFromRecord(records.projects[0]) : PROJECT_WORKSPACE_CARDS[0]);
    const setSelectedProject = selectedState[1];

    function refreshWorkspaceRecords() {
      Promise.all([
        getJSON(WORKSPACE_PROJECTS_URL),
        getJSON(WORKSPACE_LANE_REQUESTS_URL),
        getJSON(WORKSPACE_REPORTS_URL),
      ]).then(function (result) {
        setRecords({
          loading: false,
          projects: (result[0] && result[0].projects) || [],
          laneRequests: (result[1] && result[1].lane_requests) || [],
          reports: (result[2] && result[2].reports) || [],
          error: "",
        });
      }).catch(function (err) {
        setRecords({ loading: false, projects: [], laneRequests: [], reports: [], error: String(err && err.message ? err.message : err) });
      });
    }

    useEffect(function () { refreshWorkspaceRecords(); }, []);

    function copyProjectPrompt(prompt) {
      if (!navigator.clipboard || !navigator.clipboard.writeText) {
        setCopyMessage("Clipboard unavailable — select and copy the generated prompt manually.");
        return;
      }
      navigator.clipboard.writeText(prompt).then(function () {
        setCopyMessage("Copied project workspace prompt. Paste it manually.");
      }).catch(function () {
        setCopyMessage("Clipboard failed — select and copy the generated prompt manually.");
      });
    }

    function createLaneRequest(draft) {
      if (!selectedProject) return;
      const prompt = makeProjectWorkspacePrompt(selectedProject, props.workspaceStatus || {}, draft);
      postJSON(WORKSPACE_LANE_REQUEST_CREATE_URL, {
        project_id: selectedProject.project_id || selectedProject.name,
        title: draft.title || selectedProject.next_recommended_lane,
        objective: draft.objective || selectedProject.current_goal,
        mode: "read-only/manual-copy",
        allowed_actions: ["read approved context", "report status", "recommend next lane"],
        forbidden_actions: ["dispatch", "run tools", "queue mutation", "Waha mutation", "model routing", "enforcement", "automatic session send"],
        stop_conditions: ["workspace-status preflight fails", "scope requires live mutation"],
        expected_report_format: ["preflight", "current project state", "recommended next lane", "no-mutation confirmation"],
        draft_prompt: prompt,
      }).then(function () {
        setCopyMessage("Saved durable lane request draft. Send to Jenny remains disabled.");
        refreshWorkspaceRecords();
      }).catch(function (err) {
        setCopyMessage("Lane request was not saved: " + String(err && err.message ? err.message : err));
      });
    }

    function createJennyReport(report) {
      if (!selectedProject) return;
      postJSON(WORKSPACE_REPORT_CREATE_URL, {
        project_id: selectedProject.project_id || selectedProject.name,
        lane_request_id: report.lane_request_id || "",
        summary: report.summary,
        result: report.result,
        changed_files: [],
        tests: [],
        risks: [],
        next_recommended_lane: report.next_recommended_lane,
      }).then(function () {
        setCopyMessage("Saved manual Jenny report. Send to Jenny remains disabled.");
        refreshWorkspaceRecords();
      }).catch(function (err) {
        setCopyMessage("Jenny report was not saved: " + String(err && err.message ? err.message : err));
      });
    }

    const durableProjects = records.projects.map(projectFromRecord).filter(Boolean);
    const projectCards = durableProjects.length ? durableProjects : PROJECT_WORKSPACE_CARDS;
    const selectedId = selectedProject ? (selectedProject.project_id || selectedProject.name) : "";
    const projectLaneRequests = records.laneRequests.map(laneRequestFromRecord).filter(function (lane) { return lane && lane.project_id === selectedId; });
    const projectReports = records.reports.map(reportFromRecord).filter(function (report) { return report && report.project_id === selectedId; });

    return h(C.Card, { className: "mcg-project-workspace-card" },
      h(C.CardContent, { className: "mcg-project-workspace-body" },
        h("div", { className: "mcg-panel-heading" },
          h("div", null,
            h("div", { className: "mcg-panel-title" }, "Project Workspace"),
            h("p", { className: "mcg-muted" }, "Project + LaneRequest records only. Manual-copy workspace; no send path.")
          ),
          h("span", { className: "mcg-badge" }, "Records v1 thin slice")
        ),
        h("p", { className: "mcg-handoff-warning" }, "Manual transport only — paste into Discord. This does not start work. Draft packet only. This is not an active lane."),
        h("p", { className: "mcg-muted" }, "Send to Jenny — disabled. No dispatch, queue, Waha, model routing, enforcement, automatic session send, storage, timers, or hidden workers."),
        records.error ? h("p", { className: "mcg-handoff-stop" }, records.error) : null,
        copyMessage ? h("p", { className: "mcg-muted" }, copyMessage) : null,
        h("div", { className: "mcg-project-grid" },
          projectCards.map(function (project) {
            return h(ProjectWorkspaceCard, {
              key: project.project_id || project.name,
              project: project,
              workspaceStatus: props.workspaceStatus || {},
              onOpen: setSelectedProject,
              onCopy: copyProjectPrompt,
            });
          })
        ),
        selectedProject ? h("div", { className: "mcg-project-detail-workspace" },
          h("div", { className: "mcg-project-card-head" },
            h("div", { className: "mcg-workspace-section-title" }, "Open Project: " + selectedProject.name),
            h("span", { className: "mcg-badge" }, "Send to Jenny disabled")
          ),
          h(WorkspaceField, { label: "current goal", value: selectedProject.current_goal }),
          h(WorkspaceField, { label: "last report summary", value: selectedProject.last_report_summary }),
          h(WorkspaceField, { label: "next recommended lane", value: selectedProject.next_recommended_lane }),
          h(WorkspaceField, { label: "mistakes/guards", value: selectedProject.mistakes_guards }),
          h(LaneRequestDraftForm, { onCreate: createLaneRequest }),
          h("div", { className: "mcg-project-lane-list" },
            h("div", { className: "mcg-workspace-section-title" }, "Saved lane request drafts"),
            projectLaneRequests.length ? projectLaneRequests.map(function (lane) {
              return h("div", { className: "mcg-compact-row", key: lane.lane_request_id },
                h("strong", null, lane.title),
                h("span", null, lane.objective || lane.mode),
                h("span", { className: "mcg-copy-control", role: "link", tabIndex: 0, onClick: function () { copyProjectPrompt(lane.draft_prompt); }, onKeyDown: function (event) { if (event.key === "Enter" || event.key === " ") copyProjectPrompt(lane.draft_prompt); } }, "Copy saved prompt")
              );
            }) : h("p", { className: "mcg-muted" }, "No saved lane request records yet.")
          ),
          h(ManualJennyReportInbox, { laneRequests: projectLaneRequests, reports: projectReports, onCreate: createJennyReport })
        ) : null
      )
    );
  }

  function LaneDraftField(props) {
    const multiline = props.multiline === true;
    const common = {
      className: multiline ? "mcg-handoff-textarea" : "mcg-handoff-input",
      value: props.value,
      onChange: function (event) { props.onChange(event.target.value); },
      placeholder: props.placeholder || "",
    };
    return h("label", { className: multiline ? "mcg-handoff-field mcg-handoff-field-wide" : "mcg-handoff-field" },
      h("span", { className: "mcg-start-label" }, props.label),
      multiline
        ? h("textarea", Object.assign({}, common, { rows: props.rows || 4 }))
        : h("input", Object.assign({}, common, { type: "text" }))
    );
  }

  function LaneHandoffDraftBuilder(props) {
    const useState = hooks.useState;
    const workspaceStatus = props.workspaceStatus || {};
    const accepted = workspaceStatus.accepted_baseline || {};
    const rollback = workspaceStatus.rollback_baseline || {};
    const lane = workspaceStatus.lane || {};
    const safety = workspaceStatus.safety || {};
    const staleContext = workspaceStatus.stale_context || {};
    const staleWarnings = Array.isArray(staleContext.warnings) ? staleContext.warnings : [];
    const initial = {
      laneName: "Mission Control lane-handoff draft copy",
      objective: "Create a bounded lane handoff packet for manual Discord approval.",
      mode: "Draft-only discovery/implementation lane. Manual transport only.",
      allowedActions: "Read approved context\nImplement only approved files\nRun scoped tests\nReport verification",
      forbiddenActions: "No deploy\nNo restart\nNo record mutation\nNo config migration\nNo dispatch\nNo enforcement\nNo queue/board mutation\nNo model routing\nNo Waha mutation",
      stopConditions: "Stop if Mission Control preflight fails\nStop if scope changes\nStop if live mutation would be required",
      reportFormat: "Preflight result\nFiles changed\nTests run\nSafety/inertness confirmation\nNo-mutation confirmation",
      target: "",
      notes: "",
    };
    const state = useState(initial);
    const form = state[0];
    const setForm = state[1];
    const copyState = useState("");
    const copyMessage = copyState[0];
    const setCopyMessage = copyState[1];
    function update(field, value) {
      setForm(Object.assign({}, form, { [field]: value }));
    }
    const prompt = makeHandoffPrompt(form, workspaceStatus);
    const safetyLocks = [
      "display_only=true",
      "dry_run_only=true",
      "execution_enabled=false",
      "dispatch_in_gateway=false",
      "model_routing=false",
      "queue_mutation=false",
      "waha_mutation=false",
      "enforcement_enabled=false",
      "record_write_enabled=false",
    ];
    function copyPrompt() {
      if (!navigator.clipboard || !navigator.clipboard.writeText) {
        setCopyMessage("Clipboard unavailable — select and copy the prompt manually.");
        return;
      }
      navigator.clipboard.writeText(prompt).then(function () {
        setCopyMessage("Copied draft handoff prompt. Paste it into Discord manually.");
      }).catch(function () {
        setCopyMessage("Clipboard failed — select and copy the prompt manually.");
      });
    }
    return h(C.Card, { className: "mcg-handoff-card" },
      h(C.CardContent, { className: "mcg-handoff-body" },
        h("div", { className: "mcg-panel-heading" },
          h("div", null,
            h("div", { className: "mcg-panel-title" }, "Start New Lane / Draft Handoff"),
            h("p", { className: "mcg-muted" }, "Lane Handoff Draft Builder · Manual transport only — paste into Discord. This does not start work.")
          ),
          h("span", { className: "mcg-badge" }, "Draft-only")
        ),
        h("p", { className: "mcg-handoff-warning" }, "Draft packet only. This is not an active lane."),
        staleWarnings.length ? h("div", { className: "mcg-handoff-stop" },
          h("strong", null, "STOP: Mission Control stale-context warnings are present"),
          h("ul", null, staleWarnings.map(function (item, index) { return h("li", { key: "stale-" + index }, item); })),
          h("span", null, "Do not proceed until this is resolved.")
        ) : null,
        h("div", { className: "mcg-handoff-baselines" },
          h(WorkspaceField, { label: "Accepted runtime", value: accepted.runtime_path }),
          h(WorkspaceField, { label: "Accepted head", value: accepted.head }),
          h(WorkspaceField, { label: "Rollback runtime", value: rollback.runtime_path }),
          h(WorkspaceField, { label: "Rollback head", value: rollback.head }),
          h(WorkspaceField, { label: "Active lane count", value: lane.active_lane_count }),
          h(WorkspaceField, { label: "Max active lane", value: lane.max_active_lane }),
          h(WorkspaceField, { label: "dispatch_in_gateway", value: safety.dispatch_in_gateway }),
          h(WorkspaceField, { label: "Stale warnings", value: staleWarnings, fallback: "None" })
        ),
        h("div", { className: "mcg-handoff-grid" },
          h(LaneDraftField, { label: "Lane name", value: form.laneName, onChange: function (value) { update("laneName", value); } }),
          h(LaneDraftField, { label: "Mode", value: form.mode, onChange: function (value) { update("mode", value); } }),
          h(LaneDraftField, { label: "Objective", value: form.objective, multiline: true, rows: 3, onChange: function (value) { update("objective", value); } }),
          h(LaneDraftField, { label: "Allowed actions", value: form.allowedActions, multiline: true, rows: 5, onChange: function (value) { update("allowedActions", value); } }),
          h(LaneDraftField, { label: "Forbidden actions", value: form.forbiddenActions, multiline: true, rows: 6, onChange: function (value) { update("forbiddenActions", value); } }),
          h(LaneDraftField, { label: "Stop conditions", value: form.stopConditions, multiline: true, rows: 4, onChange: function (value) { update("stopConditions", value); } }),
          h(LaneDraftField, { label: "Expected report format", value: form.reportFormat, multiline: true, rows: 4, onChange: function (value) { update("reportFormat", value); } }),
          h(LaneDraftField, { label: "Target repo/path/branch optional", value: form.target, onChange: function (value) { update("target", value); } }),
          h(LaneDraftField, { label: "Notes optional", value: form.notes, multiline: true, rows: 3, onChange: function (value) { update("notes", value); } })
        ),
        h(WorkspaceList, { title: "Fixed Safety Locks", items: safetyLocks }),
        h("div", { className: "mcg-handoff-output" },
          h("div", { className: "mcg-panel-heading" },
            h("div", { className: "mcg-workspace-section-title" }, "Generated handoff prompt"),
            h("span", { className: "mcg-copy-control", role: "link", tabIndex: 0, onClick: copyPrompt, onKeyDown: function (event) { if (event.key === "Enter" || event.key === " ") copyPrompt(); } }, "Copy prompt")
          ),
          copyMessage ? h("p", { className: "mcg-muted" }, copyMessage) : null,
          h("pre", { className: "mcg-handoff-prompt" }, prompt)
        )
      )
    );
  }

  const AUTONOMY_READINESS_LEDGER = [
    {
      occurred_at: "2026-06-09",
      lane: "dashboard import-binding repair",
      severity: "medium",
      status: "fixed",
      event: "dashboard import-binding verifier false rollback",
      root_cause: "Local import-source emulation ran from the wrong working directory before live route checks.",
      caught_by_jenny: "partial",
      guardrail_added: "Verify live process cwd, command line, plugin inventory, and workspace-status before local import emulation.",
      remaining_manual_dependency: "Live repair lanes still require explicit operator approval for service changes.",
      autonomy_impact: "Improves deploy reliability by proving the process actually imports the selected runtime.",
    },
    {
      occurred_at: "2026-06-09",
      lane: "dashboard import-binding repair",
      severity: "medium",
      status: "accepted risk",
      event: "unapproved skill/reference update during live repair",
      root_cause: "A durable learning update was made during a narrow live-ops lane instead of being reported for later approval.",
      caught_by_jenny: "no",
      guardrail_added: "Report recommended durable learning updates and wait for explicit approval during narrow live-ops lanes.",
      remaining_manual_dependency: "Operator approval remains required before skill, memory, or reference updates in gated operations.",
      autonomy_impact: "Improves process discipline by separating live mutation from durable learning capture.",
    },
    {
      occurred_at: "2026-06-09",
      lane: "lane-handoff draft builder deployment",
      severity: "medium",
      status: "fixed",
      event: "stale dashboard session token printed during final verification",
      root_cause: "A verification command printed an ephemeral dashboard token while checking authenticated workspace-status.",
      caught_by_jenny: "yes",
      guardrail_added: "Never print dashboard session token values; report only boolean/status outcomes and fetch fresh tokens after dashboard process changes.",
      remaining_manual_dependency: "Dashboard restarts for token rotation still require explicit approval unless urgent.",
      autonomy_impact: "Reduces credential-handling risk while preserving authenticated smoke checks.",
    },
    {
      occurred_at: "2026-06-09",
      lane: "dashboard session-token hygiene",
      severity: "low",
      status: "fixed",
      event: "token rotation remediation",
      root_cause: "The previously printed dashboard session token needed process rotation proof.",
      caught_by_jenny: "yes",
      guardrail_added: "Confirm old token returns 401 and new token returns 200 without printing token values.",
      remaining_manual_dependency: "Service restarts remain gated live operations.",
      autonomy_impact: "Improves confidence that accidental token exposure can be remediated safely.",
    },
    {
      occurred_at: "2026-06-09",
      lane: "lane-handoff draft builder",
      severity: "low",
      status: "open",
      event: "PR #48 / lane-handoff builder safely deployed",
      root_cause: "Long Discord prompts create manual copy risk and approval drift.",
      caught_by_jenny: "yes",
      guardrail_added: "Mission Control now provides manual-copy draft prompts with fixed inert safety flags and no backend write path.",
      remaining_manual_dependency: "Travis still manually copies/approves lane packets; no direct dispatch is enabled.",
      autonomy_impact: "Improves OS usefulness while preserving manual approval and no-dispatch boundaries.",
    },
    {
      occurred_at: "2026-06-10",
      lane: "mission-control-runtime-worktree-guard-v1",
      severity: "high",
      status: "fixed",
      event: "runtime worktree used as PR checkout",
      root_cause: "A PR-opening lane fell back to the accepted live runtime when the requested non-live worktree was missing.",
      caught_by_jenny: "yes",
      guardrail_added: "runtime/worktree guard reports live-runtime and rollback-runtime candidate paths, runtime disk-head mismatch, runtime feature branch, rollback mismatch, and missing requested dev worktree blockers.",
      remaining_manual_dependency: "Guard remains display-only/dry-run until a separately approved enforcement lane wires it into real execution gates.",
      autonomy_impact: "Blocks the class of mistake that contaminated the live runtime checkout before more workspace autonomy or PR #52 deployment work.",
    },
    {
      occurred_at: "2026-06-10",
      lane: "mission-control-project-workspace-v1",
      severity: "low",
      status: "open",
      event: "Project Workspace v1 static cards added",
      root_cause: "Mission Control was still a safety console and prompt builder, not a project operating surface.",
      caught_by_jenny: "yes",
      guardrail_added: "Five static manual-copy project cards keep work selection visible without backend writes or dispatch.",
      remaining_manual_dependency: "Travis still manually approves and transports every project lane packet.",
      autonomy_impact: "Improves project navigation while preserving display-only and no-dispatch boundaries.",
    },
  ];

  function AutonomyReadinessLedgerPanel() {
    const safetyLocks = [
      "display_only=true",
      "dry_run_only=true",
      "execution_enabled=false",
      "dispatch_in_gateway=false",
      "model_routing=false",
      "queue_mutation=false",
      "waha_mutation=false",
      "enforcement_enabled=false",
      "record_write_enabled=false",
    ];
    const entries = AUTONOMY_READINESS_LEDGER;
    const fixedCount = entries.filter(function (entry) { return entry.status === "fixed"; }).length;
    const openCount = entries.filter(function (entry) { return entry.status === "open"; }).length;
    const acceptedRiskCount = entries.filter(function (entry) { return entry.status === "accepted risk"; }).length;
    return h(C.Card, { className: "mcg-workspace-card mcg-autonomy-ledger-card" },
      h(C.CardContent, { className: "mcg-workspace-body" },
        h("div", { className: "mcg-panel-heading" },
          h("div", null,
            h("div", { className: "mcg-panel-title" }, "Autonomy Readiness Ledger"),
            h("p", { className: "mcg-muted" }, "Display-only ledger. This is not an enforcement surface.")
          ),
          h("span", { className: "mcg-badge" }, "Display-only")
        ),
        h("div", { className: "mcg-workspace-grid" },
          h("div", { className: "mcg-workspace-section" },
            h("div", { className: "mcg-workspace-section-title" }, "Summary"),
            h(WorkspaceField, { label: "Entries", value: entries.length }),
            h(WorkspaceField, { label: "fixed", value: fixedCount }),
            h(WorkspaceField, { label: "open", value: openCount }),
            h(WorkspaceField, { label: "accepted risk", value: acceptedRiskCount })
          ),
          h(WorkspaceList, { title: "Ledger Safety Locks", items: safetyLocks })
        ),
        h("div", { className: "mcg-workspace-grid" }, entries.map(function (entry, index) {
          return h("div", { className: "mcg-workspace-section", key: "autonomy-ledger-" + index },
            h("div", { className: "mcg-workspace-section-title" }, entry.event),
            h(WorkspaceField, { label: "date/time", value: entry.occurred_at }),
            h(WorkspaceField, { label: "lane", value: entry.lane }),
            h(WorkspaceField, { label: "severity", value: entry.severity }),
            h(WorkspaceField, { label: "status", value: entry.status }),
            h(WorkspaceField, { label: "mistake / near miss", value: entry.event }),
            h(WorkspaceField, { label: "root cause", value: entry.root_cause }),
            h(WorkspaceField, { label: "caught by Jenny", value: entry.caught_by_jenny }),
            h(WorkspaceField, { label: "guardrail", value: entry.guardrail_added }),
            h(WorkspaceField, { label: "remaining manual dependency", value: entry.remaining_manual_dependency }),
            h(WorkspaceField, { label: "autonomy impact", value: entry.autonomy_impact })
          );
        }))
      )
    );
  }

  function GovernancePage() {
    const useState = hooks.useState;
    const useEffect = hooks.useEffect;
    const state = useState({
      loading: true,
      summary: null,
      startGate: null,
      evaluator: null,
      lanePreflight: null,
      modelRegistry: null,
      envelopes: null,
      checks: null,
      approvals: null,
      evidence: null,
      actions: null,
      workspaceStatus: null,
      rows: [],
      schema: null,
      detail: null,
      detailLoading: false,
      detailError: "",
      selectedIndex: null,
      error: "",
    });
    const data = state[0];
    const setData = state[1];

    useEffect(function () {
      let cancelled = false;
      Promise.all([
        getJSON(SUMMARY_URL),
        getJSON(START_GATE_URL),
        postJSON(START_GATE_EVALUATE_URL, SAMPLE_EVALUATOR_ENVELOPE),
        postJSON(LANE_PREFLIGHT_EVALUATE_URL, {}),
        getJSON(MODEL_REGISTRY_URL),
        getJSON(TASK_CONTROL_ENVELOPES_URL),
        getJSON(START_GATE_CHECKS_URL),
        getJSON(APPROVAL_SLICES_URL),
        getJSON(EVIDENCE_CARDS_URL),
        getJSON(OPERATOR_ACTIONS_URL),
        getJSON(WORKSPACE_STATUS_URL),
        getJSON(RECORDS_URL),
        getJSON(SCHEMA_URL),
      ])
        .then(function (result) {
          if (cancelled) return;
          setData({
            loading: false,
            summary: result[0],
            startGate: result[1],
            evaluator: result[2],
            lanePreflight: result[3],
            modelRegistry: result[4],
            envelopes: result[5],
            checks: result[6],
            approvals: result[7],
            evidence: result[8],
            actions: result[9],
            workspaceStatus: result[10],
            rows: (result[11] && result[11].records) || [],
            schema: result[12],
            detail: null,
            detailLoading: false,
            detailError: "",
            selectedIndex: null,
            error: "",
          });
        })
        .catch(function (err) {
          if (cancelled) return;
          setData({
            loading: false,
            summary: null,
            startGate: null,
            evaluator: null,
            lanePreflight: null,
            modelRegistry: null,
            envelopes: null,
            checks: null,
            approvals: null,
            evidence: null,
            actions: null,
            workspaceStatus: null,
            rows: [],
            schema: null,
            detail: null,
            detailLoading: false,
            detailError: "",
            selectedIndex: null,
            error: String(err && err.message ? err.message : err),
          });
        });
      return function () { cancelled = true; };
    }, []);

    function selectRecord(index) {
      setData(Object.assign({}, data, {
        detail: null,
        detailLoading: true,
        detailError: "",
        selectedIndex: index,
      }));
      getJSON(RECORD_DETAIL_URL(index))
        .then(function (detail) {
          setData(function (current) {
            return Object.assign({}, current, {
              detail: detail,
              detailLoading: false,
              detailError: "",
              selectedIndex: index,
            });
          });
        })
        .catch(function (err) {
          setData(function (current) {
            return Object.assign({}, current, {
              detail: null,
              detailLoading: false,
              detailError: String(err && err.message ? err.message : err),
              selectedIndex: index,
            });
          });
        });
    }

    const summary = data.summary || {};
    const startGate = data.startGate || {};
    const evaluator = data.evaluator || {};
    const evaluatorDecision = evaluator.decision || {};
    const lanePreflight = data.lanePreflight || {};
    const modelRegistry = data.modelRegistry || {};
    const modelRows = modelRegistry.model_registry || [];
    const envelope = startGate.envelope || {};
    const envelopes = data.envelopes || {};
    const checks = data.checks || {};
    const approvals = data.approvals || {};
    const evidence = data.evidence || {};
    const actions = data.actions || {};
    const workspaceStatus = data.workspaceStatus || {};
    const acceptedBaseline = workspaceStatus.accepted_baseline || {};
    const rollbackBaseline = workspaceStatus.rollback_baseline || {};
    const workspaceLane = workspaceStatus.lane || {};
    const workspaceSafety = workspaceStatus.safety || {};
    const workspaceActivity = workspaceStatus.activity || {};
    const prGate = workspaceStatus.pr_gate || {};
    const deployment = workspaceStatus.deployment || {};
    const latestHandoff = workspaceStatus.latest_handoff || { present: false };
    const handoffWarnings = Array.isArray(latestHandoff.warnings) ? latestHandoff.warnings : [];
    const runtimeGuard = workspaceStatus.runtime_worktree_guard || {};
    const runtimeGuardBlockers = Array.isArray(runtimeGuard.blockers) ? runtimeGuard.blockers : [];
    const runtimeGuardRisks = Array.isArray(runtimeGuard.observed_risks) ? runtimeGuard.observed_risks : [];
    const runtimeGuardLabels = [
      "dev_worktree_is_live_runtime",
      "dev_worktree_is_rollback_runtime",
      "runtime_disk_head_mismatch",
      "runtime_on_feature_branch",
      "rollback_disk_head_mismatch",
      "requested_dev_worktree_missing",
    ];
    const staleContext = workspaceStatus.stale_context || {};
    const staleWarnings = Array.isArray(staleContext.warnings) ? staleContext.warnings : [];
    const safetyLocks = [
      "dispatch_in_gateway=" + valueText(workspaceSafety.dispatch_in_gateway, "unknown"),
      "workers_enabled=" + valueText(workspaceSafety.workers_enabled, "unknown"),
      "queue_mutation_enabled=" + valueText(workspaceSafety.queue_mutation_enabled, "unknown"),
      "model_routing_enabled=" + valueText(workspaceSafety.model_routing_enabled, "unknown"),
      "enforcement_enabled=" + valueText(workspaceSafety.enforcement_enabled, "unknown"),
    ];
    const inertFlags = [
      "display_only=" + valueText(workspaceStatus.display_only, "unknown"),
      "dry_run_only=" + valueText(workspaceStatus.dry_run_only, "unknown"),
      "stored=" + valueText(workspaceStatus.stored, "unknown"),
      "enforces_runtime=" + valueText(workspaceStatus.enforces_runtime, "unknown"),
    ];
    const envelopeRows = envelopes.task_control_envelopes || [];
    const checkRows = checks.start_gate_checks || [];
    const approvalRows = approvals.approval_slices || [];
    const evidenceRows = evidence.evidence_cards || [];
    const actionRows = actions.operator_actions || [];
    const types = summary.record_types || {};
    const schemaTypes = data.schema && data.schema.record_types ? data.schema.record_types : {};
    const schemaNames = Object.keys(schemaTypes).sort();
    const typeCount = Object.keys(types).length;
    const storeStatus = summary.store_status || (data.schema && data.schema.record_store && data.schema.record_store.status) || "unknown";
    const storeMessage = formatStoreState(storeStatus, summary.error);

    return h("div", { className: "mcg-page" },
      h("section", { className: "mcg-header" },
        h("div", null,
          h("div", { className: "mcg-kicker" }, "Mission Control"),
          h("h1", null, "Governance"),
          h("p", null, "Read-only record inventory for lane, goal, and evidence context.")
        ),
        h("span", { className: "mcg-badge" }, "Inert")
      ),
      data.error ? h(C.Card, { className: "mcg-error" },
        h(C.CardContent, null, "Unable to load governance records: " + data.error)
      ) : null,
      !data.loading ? h(C.Card, { className: "mcg-state" },
        h(C.CardContent, null,
          h("strong", null, storeStatus),
          h("span", null, storeMessage)
        )
      ) : null,
      h("div", { className: "mcg-stats" },
        h(StatCard, { label: "Records", value: data.loading ? "..." : String(summary.record_count || 0), hint: "total stored items" }),
        h(StatCard, { label: "Types", value: data.loading ? "..." : String(typeCount), hint: "record categories" }),
        h(StatCard, { label: "Latest mission", value: summary.latest_mission_title || "None", hint: summary.latest_mission_created_at || "no mission brief" })
      ),


      h(ProjectWorkspacePanel, { workspaceStatus: workspaceStatus }),
      h(C.Card, { className: "mcg-workspace-card" },
        h(C.CardContent, { className: "mcg-workspace-body" },
          h("div", { className: "mcg-panel-heading" },
            h("div", null,
              h("div", { className: "mcg-panel-title" }, "Operating Workspace"),
              h("p", { className: "mcg-muted" }, "Execution disabled — use approved lane.")
            ),
            h("span", { className: "mcg-badge" }, "Display-only")
          ),
          data.loading
            ? h("p", { className: "mcg-muted" }, "Loading operating workspace...")
            : h("div", { className: "mcg-workspace-grid" },
              h("div", { className: "mcg-workspace-section" },
                h("div", { className: "mcg-workspace-section-title" }, "Accepted Baseline"),
                h(WorkspaceField, { label: "Runtime", value: acceptedBaseline.runtime_path }),
                h(WorkspaceField, { label: "Head", value: shortHead(acceptedBaseline.head) }),
                h(WorkspaceField, { label: "Status", value: acceptedBaseline.status })
              ),
              h("div", { className: "mcg-workspace-section" },
                h("div", { className: "mcg-workspace-section-title" }, "Rollback Baseline"),
                h(WorkspaceField, { label: "Runtime", value: rollbackBaseline.runtime_path }),
                h(WorkspaceField, { label: "Head", value: shortHead(rollbackBaseline.head) }),
                h(WorkspaceField, { label: "Clean", value: rollbackBaseline.clean })
              ),
              h("div", { className: "mcg-workspace-section" },
                h("div", { className: "mcg-workspace-section-title" }, "Active Lane"),
                h(WorkspaceField, { label: "Lane", value: workspaceLane.active_lane }),
                h(WorkspaceField, { label: "Mode", value: workspaceLane.mode }),
                h(WorkspaceField, { label: "Max active lane", value: workspaceLane.max_active_lane }),
                h(WorkspaceField, { label: "Active lane count", value: workspaceLane.active_lane_count })
              ),

              h("div", { className: "mcg-workspace-section" },
                h("div", { className: "mcg-workspace-section-title" }, "Latest Lane Handoff"),
                latestHandoff.present
                  ? h("div", null,
                    h(WorkspaceField, { label: "Handoff", value: latestHandoff.handoff_id, fallback: "Unknown" }),
                    h(WorkspaceField, { label: "Lane", value: latestHandoff.active_lane, fallback: "None" }),
                    h(WorkspaceField, { label: "Mode", value: latestHandoff.lane_mode, fallback: "None" }),
                    h(WorkspaceField, { label: "Target", value: [latestHandoff.target_type, latestHandoff.target_id].filter(Boolean).join(" "), fallback: "None" }),
                    h(WorkspaceField, { label: "Target head", value: shortHead(latestHandoff.target_head), fallback: "Missing" }),
                    h(WorkspaceField, { label: "Last result", value: latestHandoff.last_result, fallback: "None" }),
                    h(WorkspaceField, { label: "Next action", value: latestHandoff.next_action, fallback: "None" }),
                    h(WorkspaceField, { label: "Warnings", value: handoffWarnings, fallback: "None" }),
                    h(WorkspaceField, { label: "display_only", value: latestHandoff.display_only }),
                    h(WorkspaceField, { label: "enforces_runtime", value: latestHandoff.enforces_runtime })
                  )
                  : h("p", { className: "mcg-muted" }, "No lane handoff record found.")
              ),
              h(WorkspaceList, { title: "Safety Locks", items: safetyLocks }),
              h("div", { className: "mcg-workspace-section" },
                h("div", { className: "mcg-workspace-section-title" }, "Activity Counts"),
                h(WorkspaceField, { label: "Workers", value: workspaceActivity.active_workers }),
                h(WorkspaceField, { label: "Tasks", value: workspaceActivity.active_tasks }),
                h(WorkspaceField, { label: "Runs", value: workspaceActivity.active_runs }),
                h(WorkspaceField, { label: "App/server pairs", value: workspaceActivity.appserver_pairs, fallback: "Unknown" })
              ),
              h("div", { className: "mcg-workspace-section" },
                h("div", { className: "mcg-workspace-section-title" }, "PR Packet / Evidence / Approval Status"),
                h(WorkspaceField, { label: "Latest PR", value: prGate.latest_pr, fallback: "None" }),
                h(WorkspaceField, { label: "packet_hash", value: prGate.packet_hash, fallback: "Missing" }),
                h(WorkspaceField, { label: "verifier_evidence_record_id", value: prGate.verifier_evidence_record_id, fallback: "Missing" }),
                h(WorkspaceField, { label: "approval_record_id", value: prGate.approval_record_id, fallback: "Missing" }),
                h(WorkspaceField, { label: "guard_advisory_only", value: prGate.guard_advisory_only })
              ),
              h("div", { className: "mcg-workspace-section" },
                h("div", { className: "mcg-workspace-section-title" }, "Deployment Status"),
                h(WorkspaceField, { label: "Status", value: deployment.status }),
                h(WorkspaceField, { label: "Target runtime", value: deployment.target_runtime }),
                h(WorkspaceField, { label: "Target head", value: shortHead(deployment.target_head) }),
                h(WorkspaceField, { label: "rollback_used", value: deployment.rollback_used })
              ),
              h("div", { className: "mcg-workspace-section mcg-runtime-guard-blockers" },
                h("div", { className: "mcg-workspace-section-title" }, "Runtime Worktree Guard"),
                h(WorkspaceField, { label: "decision_state", value: runtimeGuard.decision_state, fallback: "unknown" }),
                h(WorkspaceField, { label: "would_block", value: runtimeGuard.would_block, fallback: "false" }),
                h(WorkspaceField, { label: "dry_run_only", value: runtimeGuard.dry_run_only, fallback: "true" }),
                h(WorkspaceField, { label: "enforces_runtime", value: runtimeGuard.enforces_runtime, fallback: "false" }),
                h(WorkspaceField, { label: "blockers", value: runtimeGuardBlockers, fallback: "None" }),
                h(WorkspaceField, { label: "observed_risks", value: runtimeGuardRisks, fallback: "None" }),
                h(WorkspaceList, { title: "Blocker labels", items: runtimeGuardLabels })
              ),
              h("div", { className: "mcg-workspace-section" },
                h("div", { className: "mcg-workspace-section-title" }, "Stale Context Warnings"),
                h(WorkspaceField, { label: "baseline_mismatch", value: staleContext.baseline_mismatch }),
                h(WorkspaceField, { label: "thread_mismatch", value: staleContext.thread_mismatch }),
                h(WorkspaceField, { label: "Warnings", value: staleWarnings, fallback: "None" })
              )
            ),
          !data.loading ? h(WorkspaceList, { title: "Inert Flags", items: inertFlags }) : null
        )
      ),
      h(LaneHandoffDraftBuilder, { workspaceStatus: workspaceStatus }),
      h(AutonomyReadinessLedgerPanel, null),
      h(C.Card, { className: "mcg-start-card" },
        h(C.CardContent, { className: "mcg-start-body" },
          h("div", { className: "mcg-panel-title" }, "Start Gate"),
          data.loading
            ? h("p", { className: "mcg-muted" }, "Loading start gate...")
            : !startGate.has_active_envelope
              ? h("p", { className: "mcg-muted" }, "No active task envelope found.")
              : h("div", { className: "mcg-start-grid" },
                h("div", null,
                  h("span", { className: "mcg-start-label" }, "Lane"),
                  h("strong", null, envelope.active_lane || "Unnamed")
                ),
                h("div", null,
                  h("span", { className: "mcg-start-label" }, "Mode"),
                  h("strong", null, envelope.mode || "Unspecified")
                ),
                h("div", null,
                  h("span", { className: "mcg-start-label" }, "Source"),
                  h("strong", null, startGate.source || "none")
                ),
                h("div", null,
                  h("span", { className: "mcg-start-label" }, "Kanban"),
                  h("strong", null, formatLinkedKanbanTask(envelope.linked_kanban_task))
                ),
                h("div", null,
                  h("span", { className: "mcg-start-label" }, "Stop"),
                  h("strong", null, envelope.stop_condition || "Unspecified")
                )
          )
        )
      ),
      h(C.Card, { className: "mcg-evaluator-card" },
        h(C.CardContent, { className: "mcg-evaluator-body" },
          h("div", { className: "mcg-panel-heading" },
            h("div", { className: "mcg-panel-title" }, "Start Gate Evaluator"),
            h("span", { className: "mcg-badge" }, "Display-only")
          ),
          h("p", { className: "mcg-muted" }, "Uses a compact fixed sample envelope. The evaluator is default-off, inert, and provides no runtime enforcement."),
          data.loading
            ? h("p", { className: "mcg-muted" }, "Evaluating sample envelope...")
            : h("div", { className: "mcg-evaluator-grid" },
              h("div", null,
                h("span", { className: "mcg-start-label" }, "Decision"),
                h("strong", null, evaluatorDecision.decision_state || "unknown")
              ),
              h("div", null,
                h("span", { className: "mcg-start-label" }, "Source"),
                h("strong", null, evaluator.source || "proposed_envelope")
              ),
              h("div", null,
                h("span", { className: "mcg-start-label" }, "Stored"),
                h("strong", null, evaluator.stored === false ? "false" : "unknown")
              ),
              h("div", null,
                h("span", { className: "mcg-start-label" }, "Runtime"),
                h("strong", null, evaluator.enforces_runtime ? "enforcing" : "not enforcing")
              )
            ),
          !data.loading ? h("div", { className: "mcg-evaluator-lists" },
            h("div", null,
              h("span", { className: "mcg-start-label" }, "Reasons"),
              h("ul", null, (Array.isArray(evaluatorDecision.reasons) && evaluatorDecision.reasons.length ? evaluatorDecision.reasons : ["No reasons returned."]).map(function (item, index) {
                return h("li", { key: "reason-" + index }, item);
              }))
            ),
            h("div", null,
              h("span", { className: "mcg-start-label" }, "Blocked actions"),
              h("ul", null, (Array.isArray(evaluatorDecision.blocked_actions) && evaluatorDecision.blocked_actions.length ? evaluatorDecision.blocked_actions : ["No blocked actions returned."]).map(function (item, index) {
                return h("li", { key: "blocked-" + index }, item);
              }))
            ),
            h("div", null,
              h("span", { className: "mcg-start-label" }, "Required approvals"),
              h("ul", null, (Array.isArray(evaluatorDecision.required_approvals) && evaluatorDecision.required_approvals.length ? evaluatorDecision.required_approvals : ["No required approvals returned."]).map(function (item, index) {
                return h("li", { key: "approval-" + index }, item);
              }))
            ),
            h("div", null,
              h("span", { className: "mcg-start-label" }, "Flags"),
              h("ul", null,
                h("li", null, "default_off: " + String(evaluator.default_off !== false)),
                h("li", null, "inert: " + String(evaluator.inert !== false)),
                h("li", null, "enforces_runtime: " + String(Boolean(evaluator.enforces_runtime))),
                h("li", null, "token_context_state: " + (evaluatorDecision.token_context_state || "unknown")),
                h("li", null, "secret_safety_state: " + (evaluatorDecision.secret_safety_state || "unknown"))
              )
            )
          ) : null
        )
      ),
      h(C.Card, { className: "mcg-lane-preflight-card" },
        h(C.CardContent, { className: "mcg-evaluator-body" },
          h("div", { className: "mcg-panel-heading" },
            h("div", { className: "mcg-panel-title" }, "Lane Preflight"),
            h("span", { className: "mcg-badge" }, "Display-only")
          ),
          h("p", { className: "mcg-muted" }, "Uses a compact fixed lane-start sample. The caller is default-off, dry-run only, and provides no runtime enforcement."),
          data.loading
            ? h("p", { className: "mcg-muted" }, "Evaluating sample lane preflight...")
            : h("div", { className: "mcg-evaluator-grid" },
              h("div", null,
                h("span", { className: "mcg-start-label" }, "Decision"),
                h("strong", null, lanePreflight.decision_state || "unknown")
              ),
              h("div", null,
                h("span", { className: "mcg-start-label" }, "would_block"),
                h("strong", null, String(Boolean(lanePreflight.would_block)))
              ),
              h("div", null,
                h("span", { className: "mcg-start-label" }, "would_require_approval"),
                h("strong", null, String(Boolean(lanePreflight.would_require_approval)))
              ),
              h("div", null,
                h("span", { className: "mcg-start-label" }, "Runtime"),
                h("strong", null, lanePreflight.enforces_runtime ? "enforcing" : "not enforcing")
              ),
              h("div", null,
                h("span", { className: "mcg-start-label" }, "Linked Kanban task"),
                h("strong", null, formatLinkedKanbanTask(lanePreflight.linked_kanban_task))
              )
            ),
          !data.loading ? h("div", { className: "mcg-evaluator-lists" },
            h("div", null,
              h("span", { className: "mcg-start-label" }, "Reasons"),
              h("ul", null, (Array.isArray(lanePreflight.reasons) && lanePreflight.reasons.length ? lanePreflight.reasons : ["No reasons returned."]).map(function (item, index) {
                return h("li", { key: "lane-reason-" + index }, item);
              }))
            ),
            h("div", null,
              h("span", { className: "mcg-start-label" }, "Blocked actions"),
              h("ul", null, (Array.isArray(lanePreflight.blocked_actions) && lanePreflight.blocked_actions.length ? lanePreflight.blocked_actions : ["No blocked actions returned."]).map(function (item, index) {
                return h("li", { key: "lane-blocked-" + index }, item);
              }))
            ),
            h("div", null,
              h("span", { className: "mcg-start-label" }, "Required approvals"),
              h("ul", null, (Array.isArray(lanePreflight.required_approvals) && lanePreflight.required_approvals.length ? lanePreflight.required_approvals : ["No required approvals returned."]).map(function (item, index) {
                return h("li", { key: "lane-approval-" + index }, item);
              }))
            ),
            h("div", null,
              h("span", { className: "mcg-start-label" }, "Flags"),
              h("ul", null,
                h("li", null, "default_off: " + String(lanePreflight.default_off !== false)),
                h("li", null, "dry_run_only: " + String(lanePreflight.dry_run_only !== false)),
                h("li", null, "enforces_runtime: " + String(Boolean(lanePreflight.enforces_runtime))),
                h("li", null, "stored: " + String(lanePreflight.stored === false ? false : "unknown"))
              )
            )
          ) : null
        )
      ),
      h(C.Card, { className: "mcg-model-picker-card" },
        h(C.CardContent, { className: "mcg-panel-body" },
          h("div", { className: "mcg-panel-heading" },
            h("div", { className: "mcg-panel-title" }, "Model Picker"),
            h("span", { className: "mcg-badge" }, "Display-only / routing disabled")
          ),
          h("p", { className: "mcg-muted" }, "Read-only view of governed model registry policy. No execution controls, provider calls, or credential checks are available here."),
          h("div", { className: "mcg-model-warnings" },
            h("span", null, "Waha requires explicit approved models."),
            h("span", null, "Free-cloud and unknown models are blocked for Waha until approved."),
            h("span", null, "Verifier roles stay blocked until explicitly qualified."),
            h("span", null, "routing_enabled=false")
          ),
          data.loading
            ? h("p", { className: "mcg-muted" }, "Loading model registry...")
            : modelRows.length === 0
              ? h("p", { className: "mcg-muted" }, "No model registry records found.")
              : h("div", { className: "mcg-model-grid" },
                modelRows.map(function (model, index) {
                  return h("div", { className: "mcg-model-row", key: model.model_id || index },
                    h("div", { className: "mcg-model-title" },
                      h("strong", null, model.display_name || model.model_id || "Model policy"),
                      h("code", null, model.model_id || "model-id-missing")
                    ),
                    h("div", { className: "mcg-model-pills" },
                      h("span", { className: "mcg-model-pill" }, "provider: " + (model.provider_type || "unknown")),
                      h("span", { className: "mcg-model-pill" }, "mode: " + (model.execution_mode || "unknown")),
                      h("span", { className: "mcg-model-pill" }, "cost: " + (model.cost_class || "unknown")),
                      h("span", { className: "mcg-model-pill" }, "privacy: " + (model.privacy_class || "unknown")),
                      h("span", { className: "mcg-model-pill" }, "routing_enabled=" + boolText(model.routing_enabled)),
                      h("span", { className: "mcg-model-pill" }, "allowed_for_waha=" + boolText(model.allowed_for_waha)),
                      h("span", { className: "mcg-model-pill" }, "verifier_allowed=" + boolText(model.verifier_allowed)),
                      h("span", { className: "mcg-model-pill" }, "fallback_allowed=" + boolText(model.fallback_allowed))
                    ),
                    h("div", { className: "mcg-model-fields" },
                      h("span", null, "roles: " + listText(model.suitable_roles)),
                      h("span", null, "allowed domains: " + listText(model.allowed_domains)),
                      h("span", null, "forbidden domains: " + listText(model.forbidden_domains)),
                      h("span", null, "unresolved: " + listText(model.unresolved_before_routing)),
                      h("span", null, "notes: " + (model.notes || "No notes"))
                    )
                  );
                })
              )
        )
      ),
      h("div", { className: "mcg-summary-panels" },
        h(C.Card, { className: "mcg-envelope-card" },
          h(C.CardContent, { className: "mcg-panel-body" },
            h("div", { className: "mcg-panel-heading" },
              h("div", { className: "mcg-panel-title" }, "Task Control Envelopes"),
              h("span", { className: "mcg-count" }, data.loading ? "..." : String(envelopes.count || 0))
            ),
            data.loading
              ? h("p", { className: "mcg-muted" }, "Loading task envelopes...")
              : envelopeRows.length === 0
                ? h("p", { className: "mcg-muted" }, "No task envelopes found.")
                : h("div", { className: "mcg-compact-list" },
                  envelopeRows.map(function (item, index) {
                    return h("div", { className: "mcg-compact-row", key: item.envelope_id || index },
                      h("strong", null, item.active_lane || item.envelope_id || "Task envelope"),
                      h("span", null, (item.mode || "mode unknown") + " - " + (item.status || "status unknown")),
                      h("span", null, String(item.allowed_action_count || 0) + " allowed / " + String(item.forbidden_action_count || 0) + " blocked"),
                      item.linked_kanban_task ? h("span", null, "Kanban: " + formatLinkedKanbanTask(item.linked_kanban_task)) : null,
                      h("span", null, (item.risk_level || "risk unknown") + " / " + String(item.evidence_count || 0) + " evidence ids")
                    );
                  })
                )
          )
        ),
        h(C.Card, { className: "mcg-check-card" },
          h(C.CardContent, { className: "mcg-panel-body" },
            h("div", { className: "mcg-panel-heading" },
              h("div", { className: "mcg-panel-title" }, "Start Gate Checks"),
              h("span", { className: "mcg-count" }, data.loading ? "..." : String(checks.count || 0))
            ),
            data.loading
              ? h("p", { className: "mcg-muted" }, "Loading start gate checks...")
              : checkRows.length === 0
                ? h("p", { className: "mcg-muted" }, "No start gate checks found.")
                : h("div", { className: "mcg-compact-list" },
                  checkRows.map(function (item, index) {
                    return h("div", { className: "mcg-compact-row", key: item.start_gate_id || index },
                      h("strong", null, item.start_gate_id || "Start gate check"),
                      h("span", null, (item.decision_state || "informational") + " - " + (item.envelope_id || "no envelope")),
                      h("span", null, String(item.reason_count || 0) + " reasons / " + String(item.blocked_action_count || 0) + " blocked actions"),
                      h("span", null, (item.branch_safety_state || "branch unknown") + " / " + (item.secret_safety_state || "secret state unknown"))
                    );
                  })
                )
          )
        ),
        h(C.Card, { className: "mcg-approval-card" },
          h(C.CardContent, { className: "mcg-panel-body" },
            h("div", { className: "mcg-panel-heading" },
              h("div", { className: "mcg-panel-title" }, "Approval Slices"),
              h("span", { className: "mcg-count" }, data.loading ? "..." : String(approvals.count || 0))
            ),
            data.loading
              ? h("p", { className: "mcg-muted" }, "Loading approval slices...")
              : approvalRows.length === 0
                ? h("p", { className: "mcg-muted" }, "No approval slices found.")
                : h("div", { className: "mcg-compact-list" },
                  approvalRows.map(function (item, index) {
                    return h("div", { className: "mcg-compact-row", key: item.approval_slice_id || item.approval_id || index },
                      h("strong", null, item.lane || item.approval_slice_id || item.approval_id || "Approval slice"),
                      item.related_action_id
                        ? h("span", null, item.decision_state + " - " + item.approval_type + " - action " + item.related_action_id)
                        : h("span", null, (item.mode || "mode unknown") + " - " + String(item.approved_action_count || 0) + " allowed / " + String(item.forbidden_action_count || 0) + " blocked"),
                      h("span", null, (item.required_by || item.approver || "unknown") + (item.created_at || item.approved_at ? " - " + (item.created_at || item.approved_at) : ""))
                    );
                  })
                )
          )
        ),

        h(C.Card, { className: "mcg-action-card" },
          h(C.CardContent, { className: "mcg-panel-body" },
            h("div", { className: "mcg-panel-heading" },
              h("div", { className: "mcg-panel-title" }, "Operator Action Queue"),
              h("span", { className: "mcg-count" }, data.loading ? "..." : String(actions.count || 0))
            ),
            data.loading
              ? h("p", { className: "mcg-muted" }, "Loading requested actions...")
              : actionRows.length === 0
                ? h("p", { className: "mcg-muted" }, "No requested actions found.")
                : h("div", { className: "mcg-compact-list" },
                  actionRows.map(function (item, index) {
                    return h("div", { className: "mcg-compact-row", key: item.action_id || index },
                      h("strong", null, item.title || item.action_id || "Requested action"),
                      h("span", null, (item.lane || "lane unknown") + " - " + (item.mode || "mode unknown")),
                      h("span", null, item.requested_action || "No requested action summary"),
                      h("span", null, (item.status || "requested") + " / " + (item.risk_level || "risk unknown") + " / " + String(item.evidence_count || 0) + " evidence ids")
                    );
                  })
                )
          )
        ),
        h(C.Card, { className: "mcg-evidence-card" },
          h(C.CardContent, { className: "mcg-panel-body" },
            h("div", { className: "mcg-panel-heading" },
              h("div", { className: "mcg-panel-title" }, "Evidence Cards"),
              h("span", { className: "mcg-count" }, data.loading ? "..." : String(evidence.count || 0))
            ),
            data.loading
              ? h("p", { className: "mcg-muted" }, "Loading evidence cards...")
              : evidenceRows.length === 0
                ? h("p", { className: "mcg-muted" }, "No evidence cards found.")
                : h("div", { className: "mcg-compact-list" },
                  evidenceRows.map(function (item, index) {
                    return h("div", { className: "mcg-compact-row", key: item.evidence_id || index },
                      h("strong", null, item.title || item.evidence_id || "Evidence card"),
                      h("span", null, item.summary || "No summary"),
                      h("span", null, String(item.artifact_refs_count || item.artifact_count || 0) + " artifact refs" + (item.source_label || item.source ? " - " + (item.source_label || item.source) : ""))
                    );
                  })
                )
          )
        )
      ),
      h("div", { className: "mcg-panels" },
        h(C.Card, { className: "mcg-schema-card" },
          h(C.CardContent, { className: "mcg-panel-body" },
            h("div", { className: "mcg-panel-title" }, "Schema"),
            data.loading
              ? h("p", { className: "mcg-muted" }, "Loading schema...")
              : schemaNames.length === 0
                ? h("p", { className: "mcg-muted" }, "No schema metadata available.")
                : h("div", { className: "mcg-schema-list" },
                  schemaNames.map(function (name) {
                    const entry = schemaTypes[name] || {};
                    return h("div", { className: "mcg-schema-item", key: name },
                      h("code", null, name),
                      h("span", null, (entry.fields || []).join(", "))
                    );
                  })
                )
          )
        ),
        h(C.Card, { className: "mcg-detail-card" },
          h(C.CardContent, { className: "mcg-panel-body" },
            h("div", { className: "mcg-panel-title" }, "Record detail"),
            data.detailLoading
              ? h("p", { className: "mcg-muted" }, "Loading record...")
              : data.detailError
                ? h("p", { className: "mcg-detail-error" }, "Unable to load record: " + data.detailError)
                : data.detail
                  ? h("div", { className: "mcg-detail" },
                    h("div", null,
                      h("span", { className: "mcg-muted" }, "#" + data.detail.record_index + " "),
                      h("code", null, data.detail.record_type)
                    ),
                    h(PrettyRecord, { value: data.detail.record })
                  )
                  : h("p", { className: "mcg-muted" }, "Select a record to inspect its stored fields.")
          )
        )
      ),
      h(C.Card, { className: "mcg-table-card" },
        h(C.CardContent, { className: "mcg-table-wrap" },
          h("table", { className: "mcg-table" },
            h("thead", null,
              h("tr", null,
                h("th", null, "Type"),
                h("th", null, "Record"),
                h("th", null, "Count")
              )
            ),
            h("tbody", null,
              data.loading
                ? h("tr", null, h("td", { colSpan: 3 }, "Loading records..."))
                : data.rows.length === 0
                  ? h("tr", null, h("td", { colSpan: 3 }, "No governance records found."))
                  : data.rows.map(function (item, index) {
                    return h("tr", {
                      className: data.selectedIndex === item.record_index ? "mcg-selected" : "",
                      key: index,
                      onClick: function () { selectRecord(item.record_index); },
                      tabIndex: 0,
                      onKeyDown: function (event) {
                        if (event.key === "Enter" || event.key === " ") selectRecord(item.record_index);
                      },
                    },
                      h("td", null, h("code", null, item.record_type)),
                      h("td", null, recordTitle(item)),
                      h("td", null, String(types[item.record_type] || 0))
                    );
                  })
            )
          )
        )
      )
    );
  }

  window.__HERMES_PLUGINS__.register("mission-control-governance", GovernancePage);
})();
