---
name: invoice-generator
description: "Generate a professional PDF invoice from a one-sentence description, with line items, totals, tax, and payment terms. Use this whenever the user says 'create an invoice,' 'invoice [name] for,' 'generate a bill,' 'bill [client] for [amount],' 'invoice template,' or describes work that needs to be billed. The first run sets up the user's invoice template (their business info, payment details, default terms); subsequent runs produce invoices in seconds. Output is a polished PDF saved to the working folder."
---

# Invoice Generator

You produce a polished, ready-to-send PDF invoice from a short prompt. The first run sets up the user's defaults so future invoices are one-sentence requests.

## First-run setup

Check if `invoice-config.md` exists in the working folder. If not, run setup:

Ask once for:

1. **Your business** — name, logo path (optional), address, email, phone, website
2. **Your tax / business ID** — EIN, ABN, VAT number, depending on country
3. **Payment details** — bank transfer details, Stripe payment link, PayPal email, check mailing address, or all of the above
4. **Default payment terms** — Net 7? Net 15? Net 30? Due on receipt?
5. **Default tax handling** — none / sales tax / VAT / GST, and rate
6. **Late fee policy** — flat fee, percentage, or none
7. **Invoice number format** — sequential (INV-001, INV-002), date-based (2026-001), or custom
8. **Currency** — USD, EUR, GBP, AUD, etc.
9. **Brand color** (optional) — one accent color for the invoice design

Save all of this to `invoice-config.md`. Don't ask again.

Also create `invoice-log.md` to track invoice numbers issued so the next one auto-increments.

## Generating an invoice

The user will say something like:

> "Invoice Acme Corp $5,000 for the November consulting retainer"

Or longer:

> "Invoice ABC Inc — 40 hours of design work at $150/hr, plus a $500 rush fee, due in 7 days"

Parse the request for:

- **Recipient** — name, company, billing address, email
- **Line items** — description, quantity, rate, total
- **Discounts or rush fees**
- **Due date** (use default terms if not specified)
- **Payment method preference** (if specified)
- **Special notes** (e.g., PO number, reference number, project name)

If recipient billing details aren't on file, ask once and save to `clients/[client-slug].md` for future invoices.

## The invoice format

Generate a clean, single-page PDF saved as `invoice-[number]-[client-slug].pdf`. Layout:

**Header**

- Business logo (top left, if provided)
- "INVOICE" in large type (top right)
- Invoice number, issue date, due date (top right, below "INVOICE")

**Parties**

- "From:" — your business info, left column
- "Bill to:" — client info, right column

**Line items table**

| Description | Quantity | Rate | Amount |
|-------------|----------|------|--------|

- Right-aligned numeric columns
- Subtotal below the table
- Tax line if applicable
- Discount line if applicable
- **Total** in larger, bolder type

**Payment section**

- Payment methods accepted (with details — bank info, Stripe link, etc.)
- Due date in plain English ("Payment due by [date]")
- Late fee policy if applicable

**Footer**

- "Thank you" line (one sentence, warm but not effusive)
- Notes / PO number / project reference
- Small contact info

## Visual style

- Clean, professional, minimal
- One accent color (from config) used for headers and the total line
- White or near-white background
- One sans-serif font (Inter, Helvetica, or system stack)
- Plenty of whitespace — don't cram

Avoid: gradients, drop shadows, clipart, watermarks, "PAID" / "OVERDUE" stamps unless the user asks.

## After generating

1. Save the PDF to the working folder
2. Update `invoice-log.md` with the new invoice (number, date, client, amount, status: sent / paid / overdue)
3. Tell the user: file path, summary of the invoice, and offer to:
   - Draft an email to send the invoice
   - Set a reminder to follow up if unpaid
   - Generate a recurring invoice schedule if this is a retainer

## Edge cases

- **Multiple currencies** — note the currency clearly. If converting, show both amounts.
- **International tax** — VAT handling differs by country and customer status (B2B reverse charge in EU, etc.). Ask if unsure rather than guess.
- **Discounts** — apply before or after tax depending on jurisdiction. Default: discount before tax unless told otherwise.
- **Time tracking integration** — if the user has time-tracking data in the folder (Toggl export, Harvest CSV), offer to use it directly rather than re-typing hours.
- **Retainer invoices** — if this is a recurring retainer, note "Retainer for [month/period]" in the description and suggest a scheduled task to auto-generate next month's.

## Rules

1. **The first run takes 2 minutes. Every subsequent run takes 10 seconds.** Setup is intentional — invest once, save forever.
2. **Don't surprise the user with custom design choices.** Invoices should look like invoices, not graphic design experiments.
3. **Auto-increment the invoice number.** Never reuse a number.
4. **Round to whole units.** Cents are fine; fractional hours are not. If the user says "37.5 hours," use it — but don't introduce sub-unit precision they didn't.
5. **Save client details after first invoice.** Every repeat client should be a one-word reference next time ("invoice Acme for $4,000 retainer").
