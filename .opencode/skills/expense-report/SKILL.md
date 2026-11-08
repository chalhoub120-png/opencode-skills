---
name: expense-report
description: "Scan a folder of receipts (PDFs, images, screenshots) and produce a categorized expense spreadsheet plus a dashboard summarizing the period. Use this whenever the user says 'process my receipts,' 'expense report,' 'categorize these expenses,' 'tax prep,' 'monthly/quarterly expenses,' 'bookkeeping,' or points you at a folder of receipts. The skill works on whatever's in the folder — no setup required — but improves over time as it learns the user's category structure. Often paired with a scheduled task that runs weekly or monthly."
---

# Expense Report

You scan a folder of receipts and produce two things: a categorized spreadsheet of every line item, and an HTML dashboard summarizing the period. The user drops receipts in a folder throughout the month; you handle the rest.

## Before you start

Identify the folder of receipts. The user may point at:

- A dedicated `receipts/` or `expenses/` folder
- A `Downloads/receipts/` folder
- A specific date-range subfolder
- A cloud-synced folder (Drive, Dropbox)

Check if `expense-config.md` exists. If yes, read it — it should define:

- The user's expense categories (e.g., Software / SaaS, Travel, Meals, Marketing, Contractors, Office, Other)
- Personal vs business split rules (if mixed)
- Default currency
- Tax-relevant categories (deductible, reimbursable)
- Anything to auto-exclude (personal Amazon receipts, recurring subscriptions already tracked elsewhere)

If no config exists, run a one-time setup based on a sample of receipts:

1. Scan 10–20 receipts to understand the user's spending shape
2. Propose a category list
3. Confirm with the user
4. Save to `expense-config.md`

## Process the receipts

For each receipt file:

1. **Extract** — vendor name, date, total amount, tax (if shown), payment method (if shown), individual line items if itemized
2. **Categorize** — assign to one of the user's categories. If a vendor has been categorized before (e.g., AWS = Software), use the prior categorization for consistency.
3. **Flag** — receipts that are unclear (image too dark, partially cropped, unclear total) get flagged for user review rather than guessed
4. **Detect duplicates** — same vendor + same amount + within 3 days = likely duplicate. Flag, don't auto-merge.

If a receipt has multiple categories (e.g., a Costco run with both office supplies and personal items), either split into multiple line items or flag for the user to review.

## Output 1: The spreadsheet

Save as `expenses-YYYY-MM.xlsx` (or `.csv` if Excel isn't available). Columns:

| Date | Vendor | Description | Category | Subcategory | Amount | Tax | Total | Payment method | Receipt file | Notes |

Sorted by date descending. Include a totals row at the bottom and subtotals by category in a second sheet.

Also include a "Flagged for review" sheet with anything you couldn't confidently categorize.

## Output 2: The dashboard

Save as `expense-dashboard-YYYY-MM.html`. Interactive HTML dashboard with:

1. **Headline strip** — total spend, vs prior period, count of receipts, average receipt size
2. **Spend by category** — donut or bar chart, with totals and percentages
3. **Spend over time** — line or bar chart showing daily/weekly spend in the period
4. **Top vendors** — table, ranked by total spend, with count of receipts
5. **Trends** — any category trending up or down vs prior period, with your read on why if obvious
6. **Tax-relevant subtotals** — total of categories marked deductible/reimbursable
7. **Flagged items** — anything that needs the user's eyes

## Output 3: A short chat summary

In the chat reply, print:

```
📊 Expense report — [month/period]

Total spend: $X,XXX across [N] receipts
Biggest category: [Category] at $XXX ([%])
Notable: [one specific observation — "you tripled software spend this month," "5 meal receipts over $200 in 3 days," etc.]
Tax-relevant: $X,XXX deductible

Flagged for review: [N] items
Spreadsheet: [path]
Dashboard: [path]
```

## Running on a schedule

After the first manual run, suggest scheduling:

"Want me to run this every Sunday and roll up the week, then send you a Slack summary? At the end of the month, I'll produce the full report."

If yes, set up a recurring task. The weekly version is short (just the chat summary + spreadsheet update). The monthly version is the full dashboard + report.

## Edge cases

- **Receipts in non-English languages** — translate vendor and item descriptions but keep totals in original currency, then convert.
- **Receipts that are actually invoices** — distinguish: a receipt = paid, an invoice = owed. Don't lump unpaid invoices into the expense report.
- **Crypto / unusual payment methods** — extract what you can but flag.
- **Tips on restaurant receipts** — include in the total, note tip separately if shown.
- **Subscription receipts (Stripe, etc.)** — categorize as recurring software unless context suggests otherwise.
- **Sales tax handling** — separate sales tax in its own column. Some jurisdictions need it reported separately for accounting.

## Why this works the way it does

Most bookkeeping software requires manual entry or fragile OCR pipelines. By dropping receipts in a folder and having a skill that re-processes the whole folder every run, you get a system that's idempotent and self-correcting: if a categorization is wrong, re-run after editing `expense-config.md` and it'll re-categorize cleanly. The user owns the data (it's just files in a folder) and the dashboard is regenerable on demand.

## Rules

1. **Don't guess when unsure.** Flag for review. A flagged item is recoverable; a wrongly categorized expense compounds.
2. **Use consistent vendor naming.** "Amazon," "amazon.com," and "AMZN Mktp US" should all be normalized to "Amazon." Maintain a vendor-name map in `expense-config.md` and grow it over time.
3. **Don't reprocess from scratch every run unless asked.** Cache extracted data so re-runs are fast.
4. **Surface anomalies in the dashboard.** A 5x jump in a category, an unusually large single receipt, a new vendor — these deserve a callout.
5. **Don't moralize.** This is an accounting tool, not a financial advisor. If the user spent $4K on meals last month, report it; don't comment.
