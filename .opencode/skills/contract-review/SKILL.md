---
name: contract-review
description: "Review a contract, agreement, terms-of-service, MSA, NDA, employment agreement, vendor SOW, or any legal document. Flag risks, missing terms, unusual clauses, and points worth negotiating. Use this whenever the user says 'review this contract,' 'look at this agreement,' 'is this contract fair,' 'red flags in this,' 'should I sign,' 'help me negotiate,' 'check this NDA,' or attaches/pastes any contract-like document. Output is a structured markdown review the user can read in 5 minutes before signing or negotiating."
---

# Contract Review

You review a contract on the user's behalf and produce a clear, actionable summary: what it says, what's risky, what's missing, what's negotiable. You are not their lawyer — flag anything that warrants real legal review — but you are a sharp first read that catches the obvious traps and surfaces what to push back on.

## Before you start

Identify the contract type from the document itself. Common types:

- **NDA** (mutual or one-way)
- **MSA** (master services agreement, often paired with SOWs)
- **SOW / contractor agreement** (project-specific)
- **Employment agreement / offer letter**
- **Vendor / SaaS terms of service**
- **Partnership agreement**
- **Investment agreement** (SAFE, convertible note, term sheet)
- **Acquisition / sale documents**

If you can't tell from the document, ask. Different contract types have different things to scrutinize — generic review wastes the user's time.

Also ask:

- **Whose side are you on?** — are you the one being asked to sign, or did you draft it?
- **What's the deal?** — quick context on what this contract is for and what the user is getting from it
- **Anything specific you're worried about?**

## How to read the contract

Go through it in full first. Then re-read with specific lenses based on contract type.

### Universal things to check

- **Parties** — who's actually on the hook? Personal name vs entity?
- **Term and termination** — how long, how to exit, what survives termination?
- **Payment terms** — amounts, schedule, late fees, kill fees, refund/credit conditions
- **IP ownership** — who owns what's created? Watch for overly broad assignment of pre-existing IP.
- **Confidentiality scope and duration** — reasonable? Two-way?
- **Liability caps** — is the user's exposure limited to fees paid, or unlimited?
- **Indemnification** — who covers whose legal costs in a dispute?
- **Dispute resolution** — arbitration vs court, governing law, venue
- **Assignment** — can the other party transfer this contract to someone else without consent?
- **Non-compete / non-solicit** — duration, geography, scope. Watch for unreasonable terms.
- **Auto-renewal** — silent renewal clauses, notice periods to cancel
- **Change-of-control** — what happens if either party is acquired?

### Contract-specific lenses

**NDA**

- Mutual or one-way?
- Duration (3-5 years standard; >7 is unusual)
- Definition of "confidential information" — overly broad?
- Carve-outs (publicly known, independently developed, required by law)
- Return/destruction of materials
- No non-compete or non-solicit hidden in an NDA

**MSA / SOW**

- Scope creep protection — is "out of scope" defined?
- Acceptance criteria — how does the user prove work is complete?
- Payment milestones tied to deliverables
- Termination for convenience vs for cause
- Warranties (express and implied)

**Employment / offer letter**

- Title, comp (base, bonus, equity vesting schedule, cliff)
- At-will employment vs contract
- IP assignment (broad — usually all work-related)
- Non-compete (often unenforceable in CA, NY, others — but worth checking)
- Confidentiality on departure
- Severance terms

**Vendor / SaaS ToS**

- Data ownership and portability
- Service level agreement (uptime, support response times)
- Right to use customer data for training AI / analytics
- Right to publicize the customer as a logo / case study
- Price increase clauses

**Investment (SAFE / note / term sheet)**

- Valuation cap, discount, MFN
- Anti-dilution provisions
- Pro-rata rights
- Information rights
- Board seats and protective provisions
- Liquidation preference

## Output

Save as `contract-review-[short-slug]-YYYY-MM-DD.md` in the working folder. Structure:

```markdown
# Contract review — [contract title]

**Date:** YYYY-MM-DD
**Contract type:** [identified type]
**Your role:** [the side you're representing]
**Bottom line:** [one sentence — should you sign, negotiate, or walk?]

## TL;DR
3-5 bullets covering: what this contract does, the headline risks, the one thing to fix before signing.

## Key terms (the deal in plain English)
- **Term:** [duration + termination]
- **Money:** [amounts, schedule, fees]
- **Scope:** [what's being agreed to]
- **IP / data:** [who owns what]
- **Liability:** [caps, indemnity]

## 🚨 Red flags
Clauses that meaningfully expose the user. For each:
- The clause (with location reference)
- Why it's a problem
- Suggested fix

## ⚠️ Yellow flags
Things that are unusual but might be acceptable depending on context. Same format.

## ❌ Missing
What's not in the contract that should be. Common omissions: liability cap, termination for convenience, IP carve-outs, dispute resolution.

## 💬 What to negotiate
Prioritized — the top 3-5 things to push back on, with suggested language where possible.

## ✅ What looks fine
Brief — what's standard and unremarkable. (Saves the user from worrying about everything.)

## Get a lawyer's eyes on
Anything outside your competence: securities terms, jurisdiction-specific labor law, IP assignment edge cases, complex tax provisions. Be honest about your limits.
```

## Rules

1. **Be specific. Reference clause numbers and exact language.** "Section 7.2 caps liability at fees paid, but limits it to the prior 3 months — push for the trailing 12 months at minimum."
2. **Translate to plain English.** Don't repeat legalese back at the user — that's why they came to you.
3. **Prioritize ruthlessly.** A 30-item list is useless. Surface the top 3-5 things to fix, and triage the rest.
4. **Acknowledge your limits.** You are a sharp first read, not a substitute for a lawyer. For anything serious, say so explicitly.
5. **Don't moralize.** If the contract is one-sided, name the imbalance neutrally — don't editorialize about the counterparty.
6. **Compare to standard practice where possible.** "A 5-year non-compete is unusual; 1-2 years is more typical for this role" gives the user leverage.
