#!/usr/bin/env python3
"""Run TinyFish Web Agent with opinionated presets and report formatting."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import textwrap
import time
from dataclasses import dataclass, field
from typing import Any
from urllib import error, request


DEFAULT_BASE_URL = "https://agent.tinyfish.ai"
DEFAULT_BROWSER_PROFILE = "lite"
DEFAULT_TIMEOUT = 300
DEFAULT_POLL_INTERVAL = 5
TERMINAL_STATUSES = {"COMPLETED", "FAILED", "ERROR", "CANCELLED"}
BLOCK_PATTERNS = (
    "rate limit",
    "rate_limit",
    "too many requests",
    "captcha",
    "forbidden",
    "access denied",
    "blocked",
    "bot protection",
    "challenge",
)

PRESETS: dict[str, dict[str, str]] = {
    "broken-links-audit": {
        "objective": "Audit the target site for broken links, bad redirects, and inaccessible assets.",
        "goal": textwrap.dedent(
            """\
            Objective:
            Audit the target site for broken links, redirect issues, missing pages, and inaccessible assets.

            Scope:
            Start at {url}. Stay on the target domain. Cover primary navigation, footer links, key landing pages, and representative content pages.

            Crawl boundaries:
            Follow internal links that appear important to navigation or task completion. Skip authenticated areas unless explicitly requested.

            Required checks:
            - Detect links that return 4xx or 5xx responses.
            - Flag redirect chains, loops, or redirects that land on irrelevant destinations.
            - Flag links visible in navigation that fail to resolve correctly.
            - Note important assets or downloads that fail to load.

            Evidence:
            Include the broken URL, the referring page, the observed failure, and any status code or visible error.

            Output contract:
            Return JSON with keys summary, coverage, broken_links, redirect_issues, asset_issues, healthy_sections, blockers.

            Failure handling:
            If bot protection, auth, or rate limits prevent coverage, record the exact affected URLs under blockers.

            Stop conditions:
            Stop after enough representative pages have been checked to identify systemic link issues and the major healthy sections.
            """
        ),
    },
    "content-awareness": {
        "objective": "Map the site's main content areas and summarize what it contains.",
        "goal": textwrap.dedent(
            """\
            Objective:
            Map the target site's main content areas and summarize what it contains.

            Scope:
            Start at {url}. Stay within the target domain and focus on public-facing pages.

            Crawl boundaries:
            Inspect home, navigation hubs, category pages, docs indexes, blog indexes, pricing, product, company, and support sections when present.

            Required checks:
            - Identify the site's major sections and sub-sections.
            - Summarize the type of content found in each section.
            - Extract notable entities such as products, plans, categories, docs collections, or resource types.
            - Note obvious gaps or stale-looking sections if visible.

            Evidence:
            Include the page URL for each major section and each extracted entity cluster.

            Output contract:
            Return JSON with keys summary, sections, content_map, entities, important_pages, blockers.

            Failure handling:
            If a section is blocked or inaccessible, list it under blockers instead of inferring its contents.

            Stop conditions:
            Stop after the site structure is clear and the major sections have evidence URLs.
            """
        ),
    },
    "navigation-and-structure": {
        "objective": "Review information architecture and navigation quality.",
        "goal": textwrap.dedent(
            """\
            Objective:
            Review the target site's information architecture and navigation quality.

            Scope:
            Start at {url}. Stay on the target domain and concentrate on public navigation paths.

            Crawl boundaries:
            Check header navigation, footer navigation, breadcrumbs, key hub pages, and at least one representative page from each major section.

            Required checks:
            - Verify that primary navigation paths lead to sensible destinations.
            - Summarize the site's hierarchy and how sections relate to each other.
            - Flag orphan-looking pages, dead-end paths, duplicated navigation labels, or inconsistent menus.
            - Highlight confusing or missing pathways for a new visitor.

            Evidence:
            Include the source URL for each navigation issue and each major section summary.

            Output contract:
            Return JSON with keys summary, site_hierarchy, navigation_paths, issues, orphan_signals, important_pages, blockers.

            Failure handling:
            If navigation elements are hidden behind interaction or auth, record the limitation explicitly.

            Stop conditions:
            Stop after the main information architecture and major navigation problems are clear.
            """
        ),
    },
    "targeted-extraction": {
        "objective": "Extract a specific set of fields from a known page or section.",
        "goal": textwrap.dedent(
            """\
            Objective:
            Extract a specific set of fields from the target page or section.

            Scope:
            Start at {url}. Stay tightly focused on the requested page set.

            Crawl boundaries:
            Do not broaden the crawl unless needed to complete the extraction accurately.

            Required checks:
            - Extract only the requested fields.
            - Preserve the source URL for each extracted record.
            - If multiple pages are involved, keep records grouped by page or source.
            - Report uncertainty when a field is missing or ambiguous.

            Evidence:
            Attach the page URL to every extracted item.

            Output contract:
            Return JSON with keys summary, records, missing_fields, blockers.

            Failure handling:
            If the page cannot be accessed or parsed confidently, return a blocker instead of guessed data.

            Stop conditions:
            Stop once the requested fields have been extracted with source URLs.
            """
        ),
    },
    "change-risk-scan": {
        "objective": "Identify pages where changes would likely create user or business risk.",
        "goal": textwrap.dedent(
            """\
            Objective:
            Scan the target site for pages or sections where changes would likely create user or business risk.

            Scope:
            Start at {url}. Stay on the target domain.

            Crawl boundaries:
            Inspect pricing, signup, checkout, docs, legal, API reference, product, and support areas when present.

            Required checks:
            - Identify pages that appear critical for conversion, support, compliance, or developer onboarding.
            - Flag sections with stale-looking content, contradictory information, broken pathways, or missing ownership cues.
            - Surface links or flows where a small change could have outsized impact.

            Evidence:
            Include URLs and the reason each page is considered risk-sensitive.

            Output contract:
            Return JSON with keys summary, risk_areas, supporting_evidence, issues, blockers.

            Failure handling:
            Record inaccessible pages as blockers.

            Stop conditions:
            Stop when the top risk areas are supported by concrete URLs.
            """
        ),
    },
    "competitor-docs-comparison": {
        "objective": "Compare the target site or docs experience against a named reference site.",
        "goal": textwrap.dedent(
            """\
            Objective:
            Compare the target site or docs experience against the explicitly named reference site for content coverage and navigation quality.

            Scope:
            Start at {url}. Compare only the target and the competitor or reference site named in the task.

            Crawl boundaries:
            Review equivalent sections such as docs home, getting started, pricing, product overviews, and support hubs.

            Required checks:
            - Compare breadth of coverage and obvious content gaps.
            - Compare onboarding clarity and navigation paths.
            - Highlight strengths and weaknesses on both sides.
            - Keep claims tied to concrete pages.

            Evidence:
            Include URLs for both the target and comparison pages.

            Output contract:
            Return JSON with keys summary, comparison_points, target_gaps, target_strengths, reference_strengths, blockers.

            Failure handling:
            If one side is inaccessible, record that and avoid unsupported comparisons.

            Stop conditions:
            Stop when the major comparison points are evidenced by URLs on both sites.
            """
        ),
    },
}


@dataclass
class AttemptSummary:
    number: int
    mode: str
    browser_profile: str
    proxy_enabled: bool
    success: bool
    status: str | None = None
    run_id: str | None = None
    live_view_url: str | None = None
    error: str | None = None


@dataclass
class RunResult:
    mode: str
    url: str
    goal: str
    browser_profile: str
    proxy_config: dict[str, Any] | None
    status: str | None
    run_id: str | None
    live_view_url: str | None
    result: Any
    raw: Any
    error: str | None = None
    attempts: list[AttemptSummary] = field(default_factory=list)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run TinyFish Web Agent with presets, retries, and Markdown reporting.",
    )
    parser.add_argument("--url", required=True, help="Target URL to audit or extract from.")
    parser.add_argument(
        "--goal",
        help="Custom goal text. If --preset is also provided, this is appended as a refinement.",
    )
    parser.add_argument(
        "--preset",
        choices=sorted(PRESETS),
        default="content-awareness",
        help="Preset goal template to use.",
    )
    parser.add_argument(
        "--mode",
        choices=("sync", "async", "sse"),
        default="sse",
        help="TinyFish execution mode. Default: sse.",
    )
    parser.add_argument(
        "--browser-profile",
        choices=("lite", "stealth"),
        default=os.environ.get("TINYFISH_BROWSER_PROFILE", DEFAULT_BROWSER_PROFILE),
        help="Browser profile for the initial attempt.",
    )
    parser.add_argument(
        "--proxy",
        help="Initial proxy mode: off, residential, residential:US, or a JSON object for proxy_config.",
    )
    parser.add_argument(
        "--format",
        choices=("report", "json"),
        default="report",
        help="Output format. Default: report.",
    )
    parser.add_argument("--output", help="Optional file path for the final output.")
    parser.add_argument(
        "--poll",
        action="store_true",
        help="Poll async runs until a terminal status is reached.",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=DEFAULT_TIMEOUT,
        help=f"Request and poll timeout in seconds. Default: {DEFAULT_TIMEOUT}.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the resolved request payload without calling TinyFish.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    goal = build_goal(args.url, args.preset, args.goal)
    initial_proxy = parse_proxy_value(args.proxy)
    env_proxy_hint = os.environ.get("TINYFISH_RESIDENTIAL_PROXY_URL", "").strip()

    if args.dry_run:
        payload = build_payload(
            url=args.url,
            goal=goal,
            browser_profile=args.browser_profile,
            proxy_config=initial_proxy,
        )
        output = json.dumps(
            {
                "mode": args.mode,
                "preset": args.preset,
                "payload": payload,
                "proxy_fallback_enabled": bool(env_proxy_hint),
            },
            indent=2,
            sort_keys=True,
        )
        emit_output(output, args.output)
        return 0

    api_key = os.environ.get("TINYFISH_API_KEY", "").strip()
    if not api_key:
        print("TINYFISH_API_KEY is required.", file=sys.stderr)
        return 2

    client = TinyFishClient(
        api_key=api_key,
        base_url=os.environ.get("TINYFISH_BASE_URL", DEFAULT_BASE_URL).strip() or DEFAULT_BASE_URL,
        timeout=args.timeout,
    )

    try:
        result = execute_with_retries(
            client=client,
            mode=args.mode,
            url=args.url,
            goal=goal,
            browser_profile=args.browser_profile,
            initial_proxy=initial_proxy,
            proxy_fallback_enabled=bool(env_proxy_hint),
            poll_async=args.poll,
        )
    except TinyFishError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    if args.format == "json":
        output = json.dumps(result.raw, indent=2, sort_keys=True, ensure_ascii=True)
    else:
        output = render_report(result, preset=args.preset)

    emit_output(output, args.output)
    if (result.status or "").upper() not in {"COMPLETED", "SUCCESS"}:
        return 1
    return 0


def build_goal(url: str, preset: str, custom_goal: str | None) -> str:
    preset_goal = PRESETS[preset]["goal"].format(url=url)
    if not custom_goal:
        return preset_goal.strip()
    custom_goal = custom_goal.strip()
    return f"{preset_goal.strip()}\n\nAdditional operator refinement:\n- {custom_goal}"


def parse_proxy_value(raw: str | None) -> dict[str, Any] | None:
    if not raw:
        return None
    value = raw.strip()
    lowered = value.lower()
    if lowered in {"off", "false", "none", "disabled"}:
        return None
    if lowered.startswith("residential"):
        config: dict[str, Any] = {"enabled": True}
        if ":" in value:
            _, country = value.split(":", 1)
            country = country.strip().upper()
            if country:
                config["country_code"] = country
        return config
    if value.startswith("{"):
        parsed = json.loads(value)
        if not isinstance(parsed, dict):
            raise TinyFishError("--proxy JSON must decode to an object.")
        return parsed
    raise TinyFishError("--proxy must be off, residential, residential:CC, or JSON.")


def build_payload(
    *,
    url: str,
    goal: str,
    browser_profile: str,
    proxy_config: dict[str, Any] | None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "url": url,
        "goal": goal,
        "browser_profile": browser_profile,
        "api_integration": "codex-skill",
    }
    if proxy_config:
        payload["proxy_config"] = proxy_config
    return payload


class TinyFishError(RuntimeError):
    pass


class TinyFishHttpError(TinyFishError):
    def __init__(self, status_code: int, body: str):
        super().__init__(f"TinyFish request failed with status {status_code}: {body}")
        self.status_code = status_code
        self.body = body


class TinyFishClient:
    def __init__(self, *, api_key: str, base_url: str, timeout: int):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def run_sync(self, payload: dict[str, Any]) -> RunResult:
        raw = self._request_json("/v1/automation/run", payload)
        return normalize_json_run(raw, mode="sync", url=payload["url"], goal=payload["goal"], browser_profile=payload["browser_profile"], proxy_config=payload.get("proxy_config"))

    def run_async(self, payload: dict[str, Any], poll: bool) -> RunResult:
        raw = self._request_json("/v1/automation/run-async", payload)
        run_id = first_string_value(raw, "run_id", "runId", "id")
        if not run_id:
            raise TinyFishError("TinyFish async response did not include a run_id.")
        if not poll:
            return RunResult(
                mode="async",
                url=payload["url"],
                goal=payload["goal"],
                browser_profile=payload["browser_profile"],
                proxy_config=payload.get("proxy_config"),
                status="QUEUED",
                run_id=run_id,
                live_view_url=extract_live_view_url(raw),
                result=None,
                raw=raw,
                error=extract_error(raw),
            )
        return self.poll_run(run_id, payload=payload)

    def run_sse(self, payload: dict[str, Any]) -> RunResult:
        raw_text = self._request_text("/v1/automation/run-sse", payload, accept="text/event-stream")
        frames = parse_sse_frames(raw_text)
        run_id = None
        live_view_url = None
        last_payload: Any = None
        for frame in frames:
            payload_obj = parse_json_maybe(frame["data"])
            last_payload = payload_obj
            run_id = run_id or first_string_value(payload_obj, "run_id", "runId", "session_id", "sessionId", "id")
            live_view_url = live_view_url or extract_live_view_url(payload_obj)
            event_type = resolve_event_type(frame["event"], payload_obj)
            if event_type == "ERROR":
                raise TinyFishError(extract_error(payload_obj) or "TinyFish SSE stream returned an error.")
            if event_type == "COMPLETE":
                status = extract_status(payload_obj) or "COMPLETED"
                if status not in {"COMPLETED", "SUCCESS"}:
                    raise TinyFishError(extract_error(payload_obj) or f"TinyFish completed with status {status}.")
                return RunResult(
                    mode="sse",
                    url=payload["url"],
                    goal=payload["goal"],
                    browser_profile=payload["browser_profile"],
                    proxy_config=payload.get("proxy_config"),
                    status=status,
                    run_id=run_id,
                    live_view_url=live_view_url,
                    result=extract_result(payload_obj),
                    raw=payload_obj,
                )
        if run_id or live_view_url or last_payload is not None:
            return RunResult(
                mode="sse",
                url=payload["url"],
                goal=payload["goal"],
                browser_profile=payload["browser_profile"],
                proxy_config=payload.get("proxy_config"),
                status=extract_status(last_payload) or "UNKNOWN",
                run_id=run_id,
                live_view_url=live_view_url,
                result=extract_result(last_payload),
                raw=last_payload,
                error=extract_error(last_payload),
            )
        raise TinyFishError("TinyFish SSE stream ended before a terminal payload arrived.")

    def poll_run(self, run_id: str, *, payload: dict[str, Any]) -> RunResult:
        deadline = time.time() + self.timeout
        last_raw: Any = None
        while time.time() <= deadline:
            raw = self._request_json(f"/v1/runs/{run_id}", None, method="GET")
            last_raw = raw
            status = extract_status(raw)
            if status in TERMINAL_STATUSES:
                return RunResult(
                    mode="async",
                    url=payload["url"],
                    goal=payload["goal"],
                    browser_profile=payload["browser_profile"],
                    proxy_config=payload.get("proxy_config"),
                    status=status,
                    run_id=run_id,
                    live_view_url=extract_live_view_url(raw),
                    result=extract_result(raw),
                    raw=raw,
                    error=extract_error(raw),
                )
            time.sleep(DEFAULT_POLL_INTERVAL)
        raise TinyFishError(f"Timed out while polling TinyFish run {run_id}. Last payload: {json.dumps(last_raw)}")

    def _request_json(self, path: str, payload: dict[str, Any] | None, method: str = "POST") -> Any:
        response_text = self._request_text(path, payload, accept="application/json", method=method)
        return parse_json_maybe(response_text)

    def _request_text(
        self,
        path: str,
        payload: dict[str, Any] | None,
        *,
        accept: str,
        method: str = "POST",
    ) -> str:
        data = None if payload is None else json.dumps(payload).encode("utf-8")
        headers = {
            "Accept": accept,
            "Content-Type": "application/json",
            "X-API-Key": self.api_key,
        }
        req = request.Request(f"{self.base_url}{path}", data=data, headers=headers, method=method)
        try:
            with request.urlopen(req, timeout=self.timeout) as response:
                return response.read().decode("utf-8", "replace")
        except error.HTTPError as exc:
            body = exc.read().decode("utf-8", "replace")
            raise TinyFishHttpError(exc.code, body) from exc
        except error.URLError as exc:
            raise TinyFishError(f"TinyFish request failed: {exc}") from exc


def execute_with_retries(
    *,
    client: TinyFishClient,
    mode: str,
    url: str,
    goal: str,
    browser_profile: str,
    initial_proxy: dict[str, Any] | None,
    proxy_fallback_enabled: bool,
    poll_async: bool,
) -> RunResult:
    plans = [
        (browser_profile, initial_proxy),
    ]

    if browser_profile != "stealth":
        plans.append(("stealth", initial_proxy))

    if proxy_fallback_enabled:
        final_proxy = initial_proxy or {"enabled": True}
        if not any(profile == "stealth" and proxy == final_proxy for profile, proxy in plans):
            plans.append(("stealth", final_proxy))

    attempts: list[AttemptSummary] = []
    last_error: str | None = None

    for index, (attempt_profile, attempt_proxy) in enumerate(plans, start=1):
        if index > 1 and not looks_like_blocker(last_error):
            break

        payload = build_payload(
            url=url,
            goal=goal,
            browser_profile=attempt_profile,
            proxy_config=attempt_proxy,
        )
        try:
            result = execute_once(
                client=client,
                mode=mode,
                payload=payload,
                poll_async=poll_async,
            )
            attempts.append(
                AttemptSummary(
                    number=index,
                    mode=mode,
                    browser_profile=attempt_profile,
                    proxy_enabled=bool(attempt_proxy),
                    success=True,
                    status=result.status,
                    run_id=result.run_id,
                    live_view_url=result.live_view_url,
                )
            )
            result.attempts = attempts
            return result
        except TinyFishError as exc:
            last_error = str(exc)
            attempts.append(
                AttemptSummary(
                    number=index,
                    mode=mode,
                    browser_profile=attempt_profile,
                    proxy_enabled=bool(attempt_proxy),
                    success=False,
                    error=last_error,
                )
            )

    failure_status = "BLOCKED" if looks_like_blocker(last_error) else "FAILED"
    raw = {
        "status": failure_status,
        "error": last_error,
        "attempts": [attempt.__dict__ for attempt in attempts],
    }
    return RunResult(
        mode=mode,
        url=url,
        goal=goal,
        browser_profile=attempts[-1].browser_profile if attempts else browser_profile,
        proxy_config={"enabled": True} if attempts and attempts[-1].proxy_enabled else initial_proxy,
        status=failure_status,
        run_id=None,
        live_view_url=None,
        result=None,
        raw=raw,
        error=last_error,
        attempts=attempts,
    )


def execute_once(*, client: TinyFishClient, mode: str, payload: dict[str, Any], poll_async: bool) -> RunResult:
    if mode == "sync":
        return client.run_sync(payload)
    if mode == "async":
        return client.run_async(payload, poll=poll_async)
    return client.run_sse(payload)


def normalize_json_run(
    raw: Any,
    *,
    mode: str,
    url: str,
    goal: str,
    browser_profile: str,
    proxy_config: dict[str, Any] | None,
) -> RunResult:
    status = extract_status(raw) or "COMPLETED"
    return RunResult(
        mode=mode,
        url=url,
        goal=goal,
        browser_profile=browser_profile,
        proxy_config=proxy_config,
        status=status,
        run_id=first_string_value(raw, "run_id", "runId", "id"),
        live_view_url=extract_live_view_url(raw),
        result=extract_result(raw),
        raw=raw,
        error=extract_error(raw),
    )


def looks_like_blocker(message: str | None) -> bool:
    if not message:
        return False
    lowered = message.lower()
    return any(pattern in lowered for pattern in BLOCK_PATTERNS)


def parse_sse_frames(body: str) -> list[dict[str, str]]:
    frames: list[dict[str, str]] = []
    for chunk in re.split(r"\r?\n\r?\n", body):
        chunk = chunk.strip()
        if not chunk:
            continue
        event_name = ""
        data_lines: list[str] = []
        for line in chunk.splitlines():
            if line.startswith("event:"):
                event_name = line.split(":", 1)[1].strip()
            elif line.startswith("data:"):
                data_lines.append(line.split(":", 1)[1].strip())
        frames.append({"event": event_name, "data": "\n".join(data_lines)})
    return frames


def parse_json_maybe(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    stripped = value.strip()
    if not stripped:
        return None
    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        return {"message": stripped}


def resolve_event_type(event_name: str, payload: Any) -> str:
    if isinstance(payload, dict):
        type_value = payload.get("type")
        if isinstance(type_value, str) and type_value.strip():
            return type_value.strip().upper()
    return event_name.strip().upper()


def extract_result(payload: Any) -> Any:
    if isinstance(payload, dict):
        for key in ("resultJson", "result", "data"):
            if key in payload:
                return payload[key]
    return payload


def extract_live_view_url(payload: Any) -> str | None:
    return first_string_value(
        payload,
        "live_view_url",
        "liveViewUrl",
        "stream_url",
        "streamUrl",
        "session_url",
        "sessionUrl",
        "viewer_url",
        "viewerUrl",
        "preview_url",
        "previewUrl",
    )


def extract_status(payload: Any) -> str | None:
    status = first_string_value(payload, "status")
    return status.upper() if status else None


def extract_error(payload: Any) -> str | None:
    if isinstance(payload, dict):
        error_value = payload.get("error")
        if isinstance(error_value, str) and error_value.strip():
            return error_value.strip()
        if isinstance(error_value, dict):
            message = error_value.get("message")
            if isinstance(message, str) and message.strip():
                return message.strip()
        message = payload.get("message")
        if isinstance(message, str) and message.strip():
            return message.strip()
    return None


def first_string_value(payload: Any, *keys: str) -> str | None:
    if isinstance(payload, dict):
        for key in keys:
            value = payload.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
    return None


def emit_output(content: str, output_path: str | None) -> None:
    if output_path:
        with open(output_path, "w", encoding="utf-8") as handle:
            handle.write(content)
            if not content.endswith("\n"):
                handle.write("\n")
    else:
        print(content)


def render_report(result: RunResult, *, preset: str) -> str:
    report_payload = normalize_result_for_report(result.result)
    lines: list[str] = []
    lines.append("# TinyFish Audit Report")
    lines.append("")
    lines.append(f"- Target: {result.url}")
    lines.append(f"- Preset: {preset}")
    lines.append(f"- Mode: {result.mode}")
    lines.append(f"- Status: {result.status or 'UNKNOWN'}")
    if result.run_id:
        lines.append(f"- Run ID: `{result.run_id}`")
    if result.live_view_url:
        lines.append(f"- Live View: {result.live_view_url}")
    lines.append("")

    lines.append("## Audit Objective")
    lines.append("")
    lines.append(PRESETS[preset]["objective"])
    lines.append("")

    lines.append("## Crawl Coverage")
    lines.append("")
    lines.extend(render_flat_list(build_coverage_items(result)))
    lines.append("")

    lines.append("## Key Findings")
    lines.append("")
    key_findings = build_key_findings(report_payload)
    lines.extend(render_flat_list(key_findings or ["No major findings were surfaced in the final payload."]))
    lines.append("")

    lines.append("## Evidence URLs")
    lines.append("")
    evidence_urls = collect_urls(report_payload, limit=10)
    lines.extend(render_flat_list(evidence_urls or ["No evidence URLs were returned in the final payload."]))
    lines.append("")

    lines.append("## Broken Links or Issues")
    lines.append("")
    issues = collect_issues(report_payload, limit=12)
    lines.extend(render_flat_list(issues or ["No explicit broken links or issues were extracted."]))
    lines.append("")

    lines.append("## Content Map")
    lines.append("")
    content_map = collect_content_map(report_payload, limit=12)
    lines.extend(render_flat_list(content_map or ["No structured content map was detected in the final payload."]))
    lines.append("")

    lines.append("## Important Pages or Entities")
    lines.append("")
    pages_entities = collect_pages_and_entities(report_payload, limit=12)
    lines.extend(render_flat_list(pages_entities or ["No important pages or entities were extracted explicitly."]))
    lines.append("")

    lines.append("## Blockers")
    lines.append("")
    blockers = build_blockers(result, report_payload)
    lines.extend(render_flat_list(blockers or ["No blockers reported."]))
    lines.append("")

    lines.append("## Confidence")
    lines.append("")
    lines.append(confidence_summary(result, report_payload))
    lines.append("")

    lines.append("## Recommended Next Actions")
    lines.append("")
    lines.extend(render_flat_list(build_next_actions(result, report_payload, issues, blockers)))
    return "\n".join(lines).rstrip() + "\n"


def render_flat_list(items: list[str]) -> list[str]:
    return [f"- {item}" for item in items]


def build_coverage_items(result: RunResult) -> list[str]:
    items = [
        f"Primary URL: {result.url}",
        f"Browser profile used on final attempt: {result.browser_profile}",
    ]
    if result.proxy_config:
        items.append("Residential proxy was enabled on the final attempt.")
    if result.attempts:
        items.append(f"Attempts made: {len(result.attempts)}")
    evidence_urls = collect_urls(normalize_result_for_report(result.result), limit=8)
    if evidence_urls:
        items.append(f"Evidence URLs surfaced: {len(evidence_urls)}")
    return items


def build_key_findings(result_payload: Any) -> list[str]:
    findings: list[str] = []
    if isinstance(result_payload, dict):
        summary = result_payload.get("summary")
        if isinstance(summary, str) and summary.strip():
            findings.append(summary.strip())
        for key in ("coverage", "site_hierarchy", "navigation_paths", "risk_areas"):
            value = result_payload.get(key)
            findings.extend(summarize_value(key, value, limit=3))
    elif isinstance(result_payload, list):
        findings.append(f"Returned {len(result_payload)} top-level records.")
    return dedupe_preserve_order(findings)[:8]


def collect_issues(value: Any, *, limit: int) -> list[str]:
    issues: list[str] = []
    walk(value, issues.append, issue_only=True)
    return dedupe_preserve_order(issues)[:limit]


def collect_content_map(value: Any, *, limit: int) -> list[str]:
    content: list[str] = []
    if isinstance(value, dict):
        for key in ("sections", "content_map", "healthy_sections", "site_hierarchy"):
            content.extend(summarize_value(key, value.get(key), limit=4))
    return dedupe_preserve_order(content)[:limit]


def collect_pages_and_entities(value: Any, *, limit: int) -> list[str]:
    entities: list[str] = []
    if isinstance(value, dict):
        for key in ("important_pages", "entities", "records", "comparison_points"):
            entities.extend(summarize_value(key, value.get(key), limit=4))
    return dedupe_preserve_order(entities)[:limit]


def build_blockers(result: RunResult, report_payload: Any) -> list[str]:
    blockers: list[str] = []
    if result.error:
        blockers.append(result.error)
    if isinstance(report_payload, dict):
        blockers.extend(summarize_value("blockers", report_payload.get("blockers"), limit=5))
    for attempt in result.attempts:
        if not attempt.success and attempt.error:
            blockers.append(
                f"Attempt {attempt.number} failed with profile={attempt.browser_profile}, proxy={attempt.proxy_enabled}: {attempt.error}"
            )
    return dedupe_preserve_order(blockers)[:10]


def confidence_summary(result: RunResult, report_payload: Any) -> str:
    status = (result.status or "").upper()
    if status in {"COMPLETED", "SUCCESS"} and report_payload:
        if result.attempts and len(result.attempts) > 1:
            return "Medium confidence: the run completed, but retries were needed to reach a usable result."
        return "High confidence: the run completed and returned structured output."
    if status == "QUEUED":
        return "Low confidence: the run was queued but not polled to completion."
    if status == "BLOCKED":
        return "Low confidence: the crawl appears blocked or rate-limited."
    return "Low confidence: the run did not complete with a strong final payload."


def build_next_actions(result: RunResult, report_payload: Any, issues: list[str], blockers: list[str]) -> list[str]:
    actions: list[str] = []
    if blockers and blockers != ["No blockers reported."]:
        actions.append("Review blockers first and rerun with narrower scope or authenticated access if needed.")
    if issues:
        actions.append("Open the evidence URLs for the highest-severity issues and confirm whether they are reproducible.")
    if result.status == "QUEUED":
        actions.append("Re-run with --poll or fetch the run later with GET /v1/runs/{run_id}.")
    if not collect_urls(report_payload, limit=1):
        actions.append("Refine the goal to require evidence URLs for each claim and rerun.")
    else:
        actions.append("Convert confirmed findings into tickets grouped by broken links, navigation issues, and content gaps.")
    return dedupe_preserve_order(actions)


def normalize_result_for_report(result_payload: Any) -> Any:
    if isinstance(result_payload, dict):
        provided_json = result_payload.get("provided_json")
        if isinstance(provided_json, dict):
            normalized = dict(provided_json)
            if "summary" not in normalized:
                input_description = result_payload.get("input_description")
                if isinstance(input_description, str) and input_description.strip():
                    normalized["summary"] = input_description.strip()
            return normalized
    return result_payload


def summarize_value(key: str, value: Any, *, limit: int) -> list[str]:
    label = key.replace("_", " ")
    items: list[str] = []
    if value is None:
        return items
    if isinstance(value, str):
        items.append(f"{label}: {value.strip()}")
        return items[:limit]
    if isinstance(value, list):
        for entry in value[:limit]:
            items.extend(summarize_item(label, entry))
        return items[:limit]
    if isinstance(value, dict):
        items.extend(summarize_item(label, value))
        return items[:limit]
    items.append(f"{label}: {value}")
    return items[:limit]


def summarize_item(label: str, value: Any) -> list[str]:
    if isinstance(value, str):
        return [f"{label}: {value.strip()}"]
    if isinstance(value, dict):
        pieces = []
        for key in ("title", "name", "label", "url", "status", "reason", "summary", "description"):
            item = value.get(key)
            if isinstance(item, str) and item.strip():
                pieces.append(item.strip())
        if pieces:
            return [f"{label}: {' | '.join(pieces[:4])}"]
        compact = json.dumps(value, ensure_ascii=True, sort_keys=True)
        return [f"{label}: {compact[:220]}"]
    if isinstance(value, list):
        return [f"{label}: {json.dumps(value[:3], ensure_ascii=True)}"]
    return [f"{label}: {value}"]


def walk(value: Any, collector, *, issue_only: bool) -> None:
    if isinstance(value, dict):
        if issue_only and looks_like_issue_dict(value):
            collector(format_issue(value))
        for nested in value.values():
            walk(nested, collector, issue_only=issue_only)
    elif isinstance(value, list):
        for item in value:
            walk(item, collector, issue_only=issue_only)


def looks_like_issue_dict(value: dict[str, Any]) -> bool:
    status_code = value.get("status_code") or value.get("statusCode")
    if isinstance(status_code, int) and status_code >= 400:
        return True
    text = json.dumps(value, ensure_ascii=True).lower()
    return any(token in text for token in ("broken", "redirect", "error", "issue", "failed", "404", "500"))


def format_issue(value: dict[str, Any]) -> str:
    pieces = []
    for key in ("url", "href", "source_url", "sourceUrl", "referrer", "status_code", "statusCode", "error", "reason", "message"):
        item = value.get(key)
        if item is None:
            continue
        pieces.append(f"{key}={item}")
    if pieces:
        return "; ".join(pieces[:6])
    return json.dumps(value, ensure_ascii=True, sort_keys=True)[:220]


def collect_urls(value: Any, *, limit: int) -> list[str]:
    urls: list[str] = []

    def _walk(item: Any) -> None:
        if len(urls) >= limit:
            return
        if isinstance(item, str) and re.match(r"^https?://", item):
            urls.append(item)
            return
        if isinstance(item, dict):
            for nested in item.values():
                _walk(nested)
        elif isinstance(item, list):
            for nested in item:
                _walk(nested)

    _walk(value)
    return dedupe_preserve_order(urls)[:limit]


def dedupe_preserve_order(items: list[str]) -> list[str]:
    seen: set[str] = set()
    output: list[str] = []
    for item in items:
        trimmed = item.strip()
        if not trimmed or trimmed in seen:
            continue
        seen.add(trimmed)
        output.append(trimmed)
    return output


if __name__ == "__main__":
    raise SystemExit(main())
