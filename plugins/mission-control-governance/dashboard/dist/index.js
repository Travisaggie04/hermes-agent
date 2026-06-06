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
  const TASK_CONTROL_ENVELOPES_URL = "/api/plugins/mission-control-governance/task-control-envelopes";
  const START_GATE_CHECKS_URL = "/api/plugins/mission-control-governance/start-gate-checks";
  const APPROVAL_SLICES_URL = "/api/plugins/mission-control-governance/approval-slices";
  const EVIDENCE_CARDS_URL = "/api/plugins/mission-control-governance/evidence-cards";
  const OPERATOR_ACTIONS_URL = "/api/plugins/mission-control-governance/operator-actions";
  const RECORDS_URL = "/api/plugins/mission-control-governance/records?limit=25";
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

  function GovernancePage() {
    const useState = hooks.useState;
    const useEffect = hooks.useEffect;
    const state = useState({
      loading: true,
      summary: null,
      startGate: null,
      evaluator: null,
      lanePreflight: null,
      envelopes: null,
      checks: null,
      approvals: null,
      evidence: null,
      actions: null,
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
        getJSON(TASK_CONTROL_ENVELOPES_URL),
        getJSON(START_GATE_CHECKS_URL),
        getJSON(APPROVAL_SLICES_URL),
        getJSON(EVIDENCE_CARDS_URL),
        getJSON(OPERATOR_ACTIONS_URL),
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
            envelopes: result[4],
            checks: result[5],
            approvals: result[6],
            evidence: result[7],
            actions: result[8],
            rows: (result[9] && result[9].records) || [],
            schema: result[10],
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
            envelopes: null,
            checks: null,
            approvals: null,
            evidence: null,
            actions: null,
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
    const envelope = startGate.envelope || {};
    const envelopes = data.envelopes || {};
    const checks = data.checks || {};
    const approvals = data.approvals || {};
    const evidence = data.evidence || {};
    const actions = data.actions || {};
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
