# TinyFish Presets

Use these presets as the basis for `--preset` runs or for custom goals. Keep the structure and tighten the requested checks rather than rewriting them into vague prose.

## `broken-links-audit`

```text
Objective:
Audit the target site for broken links, bad redirects, missing pages, and obviously inaccessible assets.

Scope:
Start at {url}. Stay on the target domain. Cover primary navigation, footer links, high-traffic landing pages, and representative content pages.

Crawl boundaries:
Check enough pages to assess site health. Follow internal links that appear important to navigation or task completion. Skip authenticated areas unless explicitly requested.

Required checks:
- Detect links that return 4xx or 5xx responses.
- Flag redirect chains, loops, or redirects that land on irrelevant pages.
- Flag links that appear in navigation but do not resolve correctly.
- Note important assets or downloads that fail to load.

Evidence:
For each issue, include the broken URL, the referring page, the observed failure, and any status code or visible error.

Output contract:
Return JSON with `summary`, `coverage`, `broken_links`, `redirect_issues`, `asset_issues`, `healthy_sections`, and `blockers`.

Failure handling:
If bot protection or login gates prevent coverage, record the exact affected URLs as blockers.

Stop conditions:
Stop after enough representative pages have been checked to identify systemic link issues and the major healthy sections.
```

## `content-awareness`

```text
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
Return JSON with `summary`, `sections`, `content_map`, `entities`, `important_pages`, and `blockers`.

Failure handling:
If a section is blocked or inaccessible, list it under blockers instead of inferring its contents.

Stop conditions:
Stop after the site structure is clear and the major sections have evidence URLs.
```

## `navigation-and-structure`

```text
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
Return JSON with `summary`, `site_hierarchy`, `navigation_paths`, `issues`, `orphan_signals`, `important_pages`, and `blockers`.

Failure handling:
If navigation elements are hidden behind interaction or auth, record the limitation explicitly.

Stop conditions:
Stop after the main information architecture and major navigation problems are clear.
```

## `targeted-extraction`

```text
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
Return JSON with `summary`, `records`, `missing_fields`, and `blockers`.

Failure handling:
If the page cannot be accessed or parsed confidently, return a blocker instead of guessed data.

Stop conditions:
Stop once the requested fields have been extracted with source URLs.
```

## `knowledge-capture`

```text
Objective:
Capture reusable site context that another agent can load later without re-crawling immediately.

Scope:
Start at {url}. Stay within the target domain and focus on the public sections that explain what the site contains and how it is organized.

Crawl boundaries:
Inspect the home page, main navigation, docs indexes, pricing, product pages, support hubs, and representative content pages.

Required checks:
- Build a concise site summary that explains what the site is for.
- Identify major sections and representative pages.
- Extract notable entities such as products, plans, categories, collections, tools, or resource types.
- Preserve evidence URLs for each important section and entity.
- Return enough structure to create a reusable context file and page inventory.

Evidence:
Include source URLs for the summary, section list, important pages, and extracted entities.

Output contract:
Return JSON with `summary`, `sections`, `content_map`, `important_pages`, `entities`, `page_chunks`, and `blockers`.

Failure handling:
Record inaccessible sections as blockers instead of guessing their contents.

Stop conditions:
Stop when the site's main structure and key public resources are clear enough to form durable context artifacts.
```

## `change-risk-scan`

```text
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
Return JSON with `summary`, `risk_areas`, `supporting_evidence`, `issues`, and `blockers`.

Failure handling:
Record inaccessible pages as blockers.

Stop conditions:
Stop when the top risk areas are supported by concrete URLs.
```

## `competitor-docs-comparison`

```text
Objective:
Compare the target site or docs experience against a second site for content coverage and navigation quality.

Scope:
Start at {url}. Compare only the explicitly named competitor or reference site.

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
Return JSON with `summary`, `comparison_points`, `target_gaps`, `target_strengths`, `reference_strengths`, and `blockers`.

Failure handling:
If one side is inaccessible, record that and avoid unsupported comparisons.

Stop conditions:
Stop when the major comparison points are evidenced by URLs on both sites.
```
