# TinyFish Skills

Installable Codex skills for TinyFish workflows.

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

## Skill Purpose

`tinyfish-web-agent` runs TinyFish against public websites and docs sites for tasks such as:

- broken link audits
- content awareness and site mapping
- navigation and information architecture review
- targeted structured extraction
- change-risk scans

## Runtime Requirements

- `TINYFISH_API_KEY`
- optional `TINYFISH_BASE_URL`
- optional `TINYFISH_BROWSER_PROFILE`
- optional `TINYFISH_RESIDENTIAL_PROXY_URL`
