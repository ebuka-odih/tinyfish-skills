---
name: tinyfish-web-agent
description: Run TinyFish Web Agent against websites, docs sites, portals, and listing pages to audit broken links, map content, review navigation, extract structured data, compare web experiences, or troubleshoot blocked crawls. Use when Codex needs a reliable operator workflow for TinyFish runs, stronger goal prompts, run-mode selection, retry handling, and a structured Markdown audit report instead of ad hoc API calls.
---

# TinyFish Web Agent

## Overview

Use this skill to operate TinyFish as a repeatable site-audit tool inside Codex. Prefer the bundled runner over ad hoc `curl` so runs use the same presets, retries, polling rules, and report format.

## Quick Start

1. Confirm `TINYFISH_API_KEY` is available in the shell environment.
2. Pick the smallest preset that matches the job.
3. Run `scripts/run_tinyfish.py` with `--format report` unless a downstream system explicitly needs raw JSON.

Examples:

```bash
scripts/run_tinyfish.py \
  --url https://docs.example.com \
  --preset broken-links-audit

scripts/run_tinyfish.py \
  --url https://example.com \
  --preset content-awareness \
  --output /tmp/example-audit.md

scripts/run_tinyfish.py \
  --url https://example.com/pricing \
  --preset targeted-extraction \
  --goal "Return plan names, monthly price, annual price, and free-trial details." \
  --mode sync

scripts/run_tinyfish.py \
  --url https://docs.example.com \
  --preset navigation-and-structure \
  --mode async \
  --poll

scripts/run_tinyfish.py \
  --url https://docs.example.com \
  --preset knowledge-capture \
  --export-dir /tmp/docs-context
```

Use `--dry-run` while shaping goals or verifying payloads:

```bash
scripts/run_tinyfish.py \
  --url https://example.com \
  --preset change-risk-scan \
  --dry-run
```

## Task Paths

### `broken-links-audit`

Use for broken links, dead navigation paths, redirect issues, missing docs pages, and media or asset failures.

### `content-awareness`

Use for content inventories, docs mapping, sitemap-like summaries, entity extraction, and "what is on this site" tasks.

### `navigation-and-structure`

Use for information architecture reviews, menu validation, user-path checks, orphan-page detection, and content hierarchy summaries.

### `targeted-extraction`

Use for extracting specific fields from a known page or small page set such as pricing tables, job listings, policies, changelog items, or structured catalog rows.

### `knowledge-capture`

Use for turning a crawl into reusable context artifacts such as a compact site-memory document, a page inventory, and evidence records that another agent can load later without re-crawling immediately.

Additional presets live in [presets.md](./references/presets.md):

- `change-risk-scan`
- `competitor-docs-comparison`

## Goal Framework

Write TinyFish goals with this structure:

1. State the objective.
2. Define scope and crawl boundaries.
3. Specify the checks TinyFish must perform.
4. Require evidence URLs for each important claim.
5. Define the output contract.
6. State failure handling.
7. State stop conditions.

Keep goals concrete. Ask for exact artifacts, not generic research. Good goals reduce wandering and improve result quality.

Use this template:

```text
Objective:
Audit {site_or_section} for {specific outcome}.

Scope:
Start at {url}. Stay within {allowed areas}. Do not leave the target domain unless following a redirect from the target.

Crawl boundaries:
Check primary navigation, footer links, key landing pages, and representative content pages. Skip login-only areas unless explicitly requested.

Required checks:
- {check 1}
- {check 2}
- {check 3}

Evidence:
Include the source URL for every major finding and for every broken or problematic link.

Output contract:
Return structured JSON with concise summaries that can be turned into a report.

Failure handling:
If a page is blocked, rate-limited, or requires auth, record it as a blocker with the exact URL and reason. Do not pretend the page was checked.

Stop conditions:
Stop after covering the requested sections and enough representative pages to support the conclusion.
```

If the user provides a preset and an extra `--goal`, treat the extra goal text as a refinement, not a replacement. Keep the preset structure intact and add the user constraint near the output contract or required checks.

## Run-Mode Selection

Use the smallest mode that fits the job:

- `sse`: default for interactive audits. Prefer this for most site-review tasks because it yields a live-view URL and returns a final payload when the run completes.
- `sync`: use only for small, likely single-page jobs where waiting for one response is acceptable.
- `async`: use for longer jobs, queued work, or when the user explicitly wants polling or later retrieval. Add `--poll` if the user still wants a final report in the same turn.

## Retry Rules

Use the runner's built-in retry flow instead of reissuing requests manually:

1. Try the requested browser profile, defaulting to `lite`.
2. If TinyFish is rate-limited or blocked, retry once with `stealth`.
3. If a residential proxy fallback is configured, retry once more with proxy enabled.
4. If the run is still blocked, return the blocker clearly in the report.

Do not silently downgrade the result after a blocked crawl. A blocker is a valid outcome and should remain visible to the user.

## Output Contract

Default to Markdown report output. The runner organizes the result into:

- target
- audit objective
- crawl coverage
- key findings
- broken links or issues
- content map
- important pages or entities
- blockers
- confidence
- recommended next actions

Use `--format json` only when another tool or script needs the raw TinyFish payload.

Use `--export-dir` when the goal is durable context capture rather than a one-off answer. The runner will write context artifacts such as:

- `context.md`
- `raw.json`
- `summary.json`
- `evidence.jsonl`
- `pages.csv`

## Operator Notes

Read [tinyfish-notes.md](./references/tinyfish-notes.md) when you need the API endpoints, run lifecycle, retry rationale, or proxy notes.

Read [presets.md](./references/presets.md) when the user wants a different audit shape or when you need a goal template to copy and adapt.

## Guardrails

- Keep the run inside the requested domain unless the goal explicitly requires broader comparison.
- Ask TinyFish for evidence URLs, not just conclusions.
- Prefer representative crawl coverage over exhaustive wandering.
- Do not claim a page is healthy if TinyFish could not access it.
- Keep the final report operator-readable. Summarize aggressively, but preserve URLs for follow-up.
