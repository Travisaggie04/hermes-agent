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
  const APPROVAL_SLICES_URL = "/api/plugins/mission-control-governance/approval-slices";
  const EVIDENCE_CARDS_URL = "/api/plugins/mission-control-governance/evidence-cards";
  const RECORDS_URL = "/api/plugins/mission-control-governance/records";
  const SCHEMA_URL = "/api/plugins/mission-control-governance/schema";
  const RECORD_DETAIL_URL = function (index) {
    return "/api/plugins/mission-control-governance/records/" + encodeURIComponent(String(index));
  };

  async function getJSON(url) {
    const headers = {};
    const token = window.__HERMES_SESSION_TOKEN__ || "";
    if (token) headers["X-Hermes-Session-Token"] = token;
    const res = await fetch(url, { headers });
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
      approvals: null,
      evidence: null,
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
        getJSON(APPROVAL_SLICES_URL),
        getJSON(EVIDENCE_CARDS_URL),
        getJSON(RECORDS_URL),
        getJSON(SCHEMA_URL),
      ])
        .then(function (result) {
          if (cancelled) return;
          setData({
            loading: false,
            summary: result[0],
            startGate: result[1],
            approvals: result[2],
            evidence: result[3],
            rows: (result[4] && result[4].records) || [],
            schema: result[5],
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
            approvals: null,
            evidence: null,
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
    const envelope = startGate.envelope || {};
    const approvals = data.approvals || {};
    const evidence = data.evidence || {};
    const approvalRows = approvals.approval_slices || [];
    const evidenceRows = evidence.evidence_cards || [];
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
                  h("span", { className: "mcg-start-label" }, "Stop"),
                  h("strong", null, envelope.stop_condition || "Unspecified")
                )
              )
        )
      ),
      h("div", { className: "mcg-summary-panels" },
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
                    return h("div", { className: "mcg-compact-row", key: item.approval_id || index },
                      h("strong", null, item.lane || item.approval_id || "Approval slice"),
                      h("span", null, (item.mode || "mode unknown") + " - " + String(item.approved_action_count || 0) + " allowed / " + String(item.forbidden_action_count || 0) + " blocked"),
                      h("span", null, (item.approver || "unknown") + (item.approved_at ? " - " + item.approved_at : ""))
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
                      h("span", null, String(item.artifact_refs_count || item.artifact_count || 0) + " artifact refs" + (item.source ? " - " + item.source : ""))
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
