(function () {
  "use strict";

  const SDK = window.__HERMES_PLUGIN_SDK__;
  if (!SDK || !window.__HERMES_PLUGINS__) return;

  const React = SDK.React;
  const h = React.createElement;
  const hooks = SDK.hooks;
  const C = SDK.components;

  const SUMMARY_URL = "/api/plugins/mission-control-governance/summary";
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
      Promise.all([getJSON(SUMMARY_URL), getJSON(RECORDS_URL), getJSON(SCHEMA_URL)])
        .then(function (result) {
          if (cancelled) return;
          setData({
            loading: false,
            summary: result[0],
            rows: (result[1] && result[1].records) || [],
            schema: result[2],
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
