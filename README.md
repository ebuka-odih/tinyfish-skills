# TinyFish Skills

Installable Codex skills for TinyFish workflows.

TinyFish website: <https://www.tinyfish.ai/>

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

It gives Codex a repeatable way to run TinyFish with stronger audit prompts, consistent presets, retry handling, and a readable Markdown report by default.

For reusable outputs, the skill can also export context artifacts such as `context.md`, `pages.csv`, `evidence.jsonl`, and `raw.json`.

## Runtime Requirements

- `TINYFISH_API_KEY`
- optional `TINYFISH_BASE_URL`
- optional `TINYFISH_BROWSER_PROFILE`
- optional `TINYFISH_RESIDENTIAL_PROXY_URL`
