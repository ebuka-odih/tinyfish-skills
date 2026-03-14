# TinyFish Skills

Installable Codex skills for TinyFish workflows.

TinyFish website: <https://www.tinyfish.ai/>

TinyFish is useful when you need a browser agent that can crawl real websites, handle harder navigation flows, and often get through gated or bot-protected pages better than a basic scraper.

## Included Skills

- `tinyfish-web-agent`

## Install

Use the Codex skill installer:

```bash
python3 ~/.codex/skills/.system/skill-installer/scripts/install-skill-from-github.py \
  --repo ebuka-odih/tinyfish-skills \
  --path skills/tinyfish-web-agent
```

Restart Codex after installation.

## TinyFish Setup

1. Sign up at <https://www.tinyfish.ai/>.
2. Obtain your TinyFish API key from your TinyFish account.
3. Export it before using the skill:

```bash
export TINYFISH_API_KEY="your-api-key"
```

## Skill Purpose

`tinyfish-web-agent` runs TinyFish against public websites and docs sites for tasks such as:

- broken link audits
- content awareness and site mapping
- navigation and information architecture review
- targeted structured extraction
- knowledge capture for reusable site context
- change-risk scans
- crawling sites that are harder to inspect because of gating or bot protection

It gives Codex a repeatable way to run TinyFish with stronger audit prompts, consistent presets, retry handling, and a readable Markdown report by default.

For reusable outputs, the skill can also export context artifacts such as `context.md`, `pages.csv`, `evidence.jsonl`, and `raw.json`.

## Common Commands

Run a basic site audit:

```bash
~/.codex/skills/tinyfish-web-agent/scripts/run_tinyfish.py \
  --url https://example.com \
  --preset content-awareness
```

Run a broken-link audit:

```bash
~/.codex/skills/tinyfish-web-agent/scripts/run_tinyfish.py \
  --url https://docs.example.com \
  --preset broken-links-audit
```

Capture reusable context artifacts:

```bash
~/.codex/skills/tinyfish-web-agent/scripts/run_tinyfish.py \
  --url https://docs.example.com \
  --preset knowledge-capture \
  --export-dir /tmp/docs-context
```

Use a custom extraction goal:

```bash
~/.codex/skills/tinyfish-web-agent/scripts/run_tinyfish.py \
  --url https://example.com/pricing \
  --preset targeted-extraction \
  --goal "Return plan names, monthly price, annual price, and free-trial details."
```

## Main Options

- `--preset` chooses the workflow: `broken-links-audit`, `content-awareness`, `navigation-and-structure`, `targeted-extraction`, `knowledge-capture`, `change-risk-scan`, `competitor-docs-comparison`
- `--mode` chooses TinyFish execution style: `sse`, `sync`, or `async`
- `--goal` adds a custom refinement to the preset
- `--export-dir` writes reusable artifacts such as `context.md`, `summary.json`, `raw.json`, `evidence.jsonl`, and `pages.csv`
- `--output` writes the final report or JSON output to a file
- `--format` switches between `report` and `json`
- `--poll` waits for an async run to finish
- `--proxy` enables residential proxy usage when needed
- `--browser-profile` lets you start with `lite` or `stealth`

## Runtime Requirements

- `TINYFISH_API_KEY`
- optional `TINYFISH_BASE_URL`
- optional `TINYFISH_BROWSER_PROFILE`
- optional `TINYFISH_RESIDENTIAL_PROXY_URL`

## Notes

- The skill defaults to `sse` mode for interactive audits.
- If TinyFish hits rate limits or blocking, the runner can retry with `stealth` and then with proxy fallback when configured.
- After installation, you can invoke the skill in Codex by mentioning `$tinyfish-web-agent` or by asking Codex to use TinyFish for a site audit, extraction task, or context capture run.
