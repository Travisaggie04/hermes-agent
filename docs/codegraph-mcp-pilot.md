# Codegraph MCP Pilot

This document records the conservative Jenny-only pilot for `colbymchenry/codegraph` as a local Hermes MCP server candidate. Codegraph remains disabled in the real Hermes user config and should not be enabled for live gateway or background service use without an explicit follow-up approval.

## Purpose

Codegraph gives Hermes a local code graph for repo navigation through MCP. The intended use is to reduce blind file searches and tool-call churn when answering bounded questions about Hermes source structure, symbol locations, and related code paths.

Treat this as an optional MCP adapter, not a Hermes core dependency.

## Current Status

- Upstream: `https://github.com/colbymchenry/codegraph`
- Local checkout: `/home/jenny/.hermes/external/codegraph`
- Pinned commit: `b026e64b413bb4dca1bc7326d7de0837afe0a899`
- License: MIT, found in upstream `LICENSE`
- Codegraph CLI version: `0.9.7`
- Node: `v22.22.2`
- npm: `10.9.7`
- Build: `npm run build` succeeded
- Install: `npm ci` succeeded, but reported 8 audit findings: 6 moderate and 2 high
- Real Hermes config: `/home/jenny/.hermes/config.yaml` contains `mcp_servers.codegraph.enabled: false`
- Live agent use: not enabled
- Hermes services restarted: no

## Repo Index

- Index path: `/home/jenny/.hermes/hermes-agent-backup/.codegraph`
- Index size: `154M`
- Files indexed: `2549`
- Nodes: `75326`
- Edges: `177290`
- Backend: `node-sqlite`

Monitor `.codegraph/` growth if the index is kept. Remove and rebuild the index if stale-index behavior appears.

## Disabled Config Shape

The real user config should keep codegraph disabled:

```yaml
mcp_servers:
  codegraph:
    command: "/home/jenny/.hermes/node/bin/node"
    args:
      - "/home/jenny/.hermes/external/codegraph/dist/bin/codegraph.js"
      - "serve"
      - "--mcp"
      - "--path"
      - "/home/jenny/.hermes/hermes-agent-backup"
      - "--no-watch"
    env:
      CODEGRAPH_MCP_TOOLS: "codegraph_search,codegraph_context,codegraph_trace,codegraph_node,codegraph_status,codegraph_files"
      CODEGRAPH_NO_DAEMON: "1"
      CODEGRAPH_NO_WATCH: "1"
    enabled: false
    connect_timeout: 10
    timeout: 30
    supports_parallel_tool_calls: false
    sampling:
      enabled: false
    tools:
      include:
        - codegraph_search
        - codegraph_context
        - codegraph_trace
        - codegraph_node
        - codegraph_status
        - codegraph_files
      resources: false
      prompts: false
```

## Allowed MCP Tools

The isolated enabled test exposed only these allowlisted Hermes tool names:

- `mcp_codegraph_codegraph_context`
- `mcp_codegraph_codegraph_files`
- `mcp_codegraph_codegraph_node`
- `mcp_codegraph_codegraph_search`
- `mcp_codegraph_codegraph_status`
- `mcp_codegraph_codegraph_trace`

Do not expose all codegraph tools unless a later review finds a concrete need.

## Verification Completed

- Disabled one-shot MCP test passed.
- Isolated enabled test used a temporary `HERMES_HOME`, not the real Hermes home.
- Isolated enabled test returned six exposed tools.
- Bounded query used `mcp_codegraph_codegraph_context` with `maxNodes: 10` and `includeCode: false`.
- Bounded query returned 491 characters.
- No `codegraph.js serve --mcp` process remained after testing.
- No Hermes services were restarted.

## Jenny Usage Guidance

Keep codegraph disabled by default. Use it only for controlled local tests or a future explicitly approved Jenny-only session.

Prefer the lower-output tools first:

- Use `codegraph_status` to confirm the index health.
- Use `codegraph_search` for symbol or file discovery.
- Use `codegraph_files` for bounded file tree checks.
- Use `codegraph_context` for a focused repo-structure question.
- Use `codegraph_node` after a specific symbol is known.
- Use `codegraph_trace` last, only when call-path information is needed.

Output-bounding rules:

- Use small `maxNodes` values, such as `10` or lower, unless there is a clear reason.
- Set `includeCode: false` by default.
- Avoid dumping full file bodies.
- Ask for summaries and file paths before requesting code snippets.
- Stop and disable again if responses become large, noisy, or stale.

## Decision Checklist Before Live Enablement

Codegraph can be considered for Jenny or live gateway use only if all of the following are true:

- The npm vulnerability details are reviewed and accepted or mitigated.
- `.codegraph/` index size and growth are monitored.
- Output remains bounded in additional local tests.
- No stale-index confusion appears.
- No service stability issue appears.
- Travis explicitly approves enabling it beyond disabled/local test use.

## Rollback

Restore the prior user config if needed:

```bash
cp /home/jenny/.hermes/config.yaml.bak-codegraph-20260530T174929Z /home/jenny/.hermes/config.yaml
```

Remove the Hermes repo index:

```bash
rm -rf /home/jenny/.hermes/hermes-agent-backup/.codegraph
```

Remove the external checkout:

```bash
rm -rf /home/jenny/.hermes/external/codegraph
```
