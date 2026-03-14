# TinyFish Operator Notes

Use these notes when choosing modes or interpreting failures. They are intentionally compact; the public docs remain the source of truth.

## Current Docs Surface

- Documentation home: <https://docs.tinyfish.ai/>
- Quick Start: <https://docs.tinyfish.ai/getting-started/quick-start>
- Goal Prompting Guide: <https://docs.tinyfish.ai/guides/goal-prompting-guide>
- Common Patterns: <https://docs.tinyfish.ai/guides/common-patterns>
- Runs: <https://docs.tinyfish.ai/key-concepts/runs>
- Build with AI / MCP: <https://docs.tinyfish.ai/getting-started/build-with-ai>

## Endpoints Used By The Runner

- `POST /v1/automation/run`
  use for synchronous single-response runs
- `POST /v1/automation/run-sse`
  use for interactive streaming runs
- `POST /v1/automation/run-async`
  use for queued runs that return a `run_id`
- `GET /v1/runs/{run_id}`
  use for polling async run status

Default base URL in this skill: `https://agent.tinyfish.ai`

## Modes

- `sse`
  best default for interactive audits; often exposes a live-view URL and returns a final `COMPLETE` event
- `sync`
  keep for smaller jobs where a single response is enough
- `async`
  start the run immediately, then poll only when the operator wants the final result in the same turn

## Request Shape

The docs surface shows these core request fields across automation endpoints:

- `url`
- `goal`
- `browser_profile`
- `proxy_config`

The runner also sends `api_integration: "codex-skill"` for traceability.

## Browser Profiles

- `lite`
  normal/default profile
- `stealth`
  anti-detection profile for blocked or rate-limited sites

## Proxy Notes

TinyFish docs show `proxy_config.enabled` and optional `country_code`. This skill exposes a local environment variable named `TINYFISH_RESIDENTIAL_PROXY_URL` as the signal that proxy fallback is allowed, but the runner only sends docs-backed `proxy_config` fields by default.

Use `--proxy residential` or `--proxy residential:US` to enable a proxy on the initial run. If the environment variable is present and the crawl is blocked, the runner can enable proxy fallback automatically on the final retry.

## Retry Policy

Retry only when the failure looks like bot protection, rate limiting, or access blocking:

1. initial request
2. retry with `stealth`
3. retry with `proxy_config.enabled=true` if proxy fallback is allowed

Do not retry endlessly. Preserve the blocker in the final report.

## Run Lifecycle

Expected terminal outcomes:

- `COMPLETED`
- `FAILED`
- `ERROR`
- `CANCELLED`

For SSE runs, parse the stream until a terminal event or payload status arrives. For async runs, poll `GET /v1/runs/{run_id}` until a terminal status or timeout.
