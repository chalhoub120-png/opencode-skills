---
name: dashboard-builder
description: "Build an interactive HTML dashboard from any data source — a CSV file, a folder of files, a spreadsheet, or pasted numbers. The dashboard shows KPIs, charts, and lets the user filter and explore. Use this whenever the user says 'build a dashboard,' 'visualize this data,' 'turn this into a dashboard,' 'KPI dashboard,' 'metrics dashboard,' 'show me trends in,' or has data they want to see and explore visually rather than as a table. Works for business KPIs, financial data, project tracking, personal metrics, survey results, anything tabular."
---

# Dashboard Builder

You build a single-file HTML dashboard from the user's data. The dashboard should be interactive (filters, hover details, sortable), visually clean, and useful at a glance. The user opens it in a browser and immediately understands what's going on with the underlying data.

## Before you start

Get the basics:

1. **Where's the data?** — file path, folder, paste, or spreadsheet
2. **What's it about?** — sales numbers, project status, marketing metrics, personal finances, something else
3. **What questions should the dashboard answer?** — "How are we trending vs last month?" "Which channel is converting best?" "Where are we over budget?"
4. **Audience** — just for the user, or to share with a team / client?
5. **Refresh cadence** — one-time build, or will the data update? (If updating, this affects how you reference the source.)

If the data is already in the working folder and the structure is obvious, infer the questions and build a draft — let the user redirect.

## Inspect the data first

Before designing the dashboard, read the data and understand:

- Schema — what columns exist, what types
- Time dimension — is there a date column? What's the date range?
- Categorical dimensions — what can you filter or group by?
- Numeric measures — what are the things worth visualizing?
- Data quality — any obvious gaps, duplicates, or weirdness worth flagging

If the data has problems (missing values, inconsistent formats, obvious errors), surface them at the top of the dashboard rather than silently ignoring them.

## Dashboard structure

Most dashboards work in this order:

1. **Top strip — the headline numbers (3–6 KPIs)** — big numbers with trend indicators (vs prior period). The user should know the state of the world from this strip alone.
2. **Time-series chart** — the most important measure over time. Use the full width.
3. **Breakdown charts (2–4)** — slice the headline numbers by the dimensions that matter (channel, segment, region, product, etc.)
4. **Detail table** — sortable, filterable raw-ish data underneath, for the user who wants to drill in
5. **Notes / observations** — your read on what the data is telling them, in 2–4 bullets

Adjust based on what the data is actually about — a project-tracking dashboard looks different from a sales dashboard, but the principle holds: big-picture first, then breakdowns, then detail.

## Visual style

- **Light background** — easier to read for long sessions, prints well
- **One accent color** for the primary measure across all charts so the eye anchors
- **Muted secondary colors** for breakdowns
- **Sparse gridlines** — present, but not visually loud
- **Number formatting matters** — `$1.2M` not `1247392.41`, `+12.4%` not `0.124`. Round sensibly, abbreviate large numbers.
- **No 3D charts. No pie charts with more than 4 slices. No exploding wedges.** Use bar, line, and stacked bar for almost everything. Dot plots for distributions.
- **Color encodes meaning, not decoration** — green for above-target, red for below, neutral for between. Don't randomly colorize.

## Interactivity

Required:

- **Filters** — at least one (date range, segment, etc.) that updates all charts simultaneously
- **Hover details** — every chart point should show its underlying value on hover
- **Sortable table** — click a column header to sort

Optional but nice:

- **Compare periods** — toggle to overlay last month / quarter / year
- **Drill-in** — click a chart segment to filter the rest of the dashboard
- **Export** — button to download the underlying data as CSV

Use a modern charting library like Chart.js, Apache ECharts, or vanilla SVG with D3 for custom shapes. Keep dependencies minimal — embed via CDN or inline.

## Technical implementation

Save as `dashboard-[topic-slug].html` in the working folder. Self-contained: data embedded as JS object, charts inline, no separate CSS file unless the user wants one.

If the data is large (>1000 rows), consider:

- Aggregating server-side (i.e., in the build step) so the dashboard loads fast
- Using a streaming format (e.g., compressed JSON) for the embedded data
- Skipping the detail table or paginating it

## After generating

Tell the user:

1. The file path
2. The 3 most interesting things you noticed in the data (this is what makes the dashboard feel insightful, not just functional)
3. What they should ask for if they want changes — common ones: different KPIs at the top, add a comparison period, change the breakdown dimension

## Updating the dashboard

If the user comes back with updated data, regenerate the dashboard rather than patching it. The dashboard is a snapshot of a moment — version it by date in the filename if they want history.

For a recurring dashboard (e.g., "I'll send you fresh data every Monday"), suggest setting up a scheduled task that ingests a known file path and regenerates the HTML on a schedule.

## Rules

1. **Lead with the answer, not the data.** A dashboard that requires the user to interpret it has failed. The KPI strip should make the state of the world obvious.
2. **Don't visualize everything.** A dashboard with 14 charts is worse than one with 5. Cut the marginal ones.
3. **Format numbers like a human reads them.** Currency, percentages, abbreviations — use them.
4. **Highlight what changed.** A static snapshot is less useful than one that shows movement (this period vs prior).
5. **Surface data quality issues at the top.** Don't silently average over bad data — flag it.
