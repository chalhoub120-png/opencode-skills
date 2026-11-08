---
name: deep-research
description: "Research a topic deeply across multiple sources and produce a sourced, bite-sized brief the user can read in 5 minutes. Use this whenever the user says 'research,' 'deep dive on,' 'tell me about,' 'what's the latest on,' 'do a brief on,' 'TL;DR of [topic],' 'catch me up on,' or asks about something they want to understand quickly but well. Works for AI tools, companies, people, technical concepts, market trends, news events, scientific topics. Output is a markdown brief with sources, pros/cons, and your read on what matters."
---

# Deep Research

You produce a 5-minute brief on a topic that's actually useful — not a Wikipedia summary, not a slop of search results. The brief tells the user what they need to know, where the open questions are, and what they should think about the topic.

## Before you start

Get just enough to scope properly:

1. **Topic** — what specifically?
2. **Why now** — what's prompting the research? (Meeting, decision, content piece, just curious?)
3. **Depth** — quick (10 min of effort) or deep (30+)?
4. **Format preference** — straight brief, comparison table, decision-oriented?
5. **What you already know** — so the brief doesn't waste space repeating it

If the user just dropped a topic with no context, default to: ~15 minutes of research, decision-neutral brief, assume baseline familiarity.

## Plan the research

Before searching, identify what kinds of sources you actually need:

- **For a company** — their site, recent news, funding history, founder background, key customers, competitors
- **For an AI tool** — official docs, the launch post or release notes, real-user reviews, benchmark or comparison content
- **For a person** — bio, recent public activity, what they're known for, who they're associated with
- **For a technical concept** — primary source (paper, official docs), one or two strong explainers, current debates
- **For a market trend** — primary data, analyst perspective, contrarian view
- **For a news event** — original source, multiple outlets, the underlying primary documents

If consensus MCP or web search is available, use them in parallel. For scientific topics specifically, prefer peer-reviewed sources via consensus over general web search.

## What makes a good brief

1. **Leads with the answer, not the setup** — first paragraph tells the user what they need to know
2. **Surfaces the disagreement** — most topics worth researching have a tension. Name it.
3. **Cites the strongest sources, not the most sources** — five good citations beat thirty mediocre ones
4. **Distinguishes facts from claims from interpretations** — be explicit when you're paraphrasing vs quoting vs editorializing
5. **Notes what you couldn't find out** — gaps matter. Don't paper over them with confident-sounding filler.

## Output format

Save as `research-[topic-slug]-YYYY-MM-DD.md` in the working folder. Structure:

```markdown
# [Topic]

**Date:** YYYY-MM-DD
**Depth:** Quick / Standard / Deep
**Why I researched this:** [one line]

## TL;DR
3–4 sentences. The headline answer.

## What it is / who they are / what happened
The core facts. 1–3 paragraphs. Plain English.

## The state of play
What's happening with this right now. Recent developments, current debates, where the action is.

## Pros / strengths / what's working
Bullet list.

## Cons / weaknesses / open questions
Bullet list. Be honest — don't hedge.

## Compared to alternatives
For tools/companies/products: brief comparison to 2-3 alternatives. For concepts: how this relates to adjacent ideas.

## What the experts disagree on
The honest disagreement in the space. Cite which expert says what.

## My read
Your synthesis — what you think the user should take away. One paragraph. Be willing to render a verdict, especially if the user is researching this to make a decision.

## Sources
Numbered list with title, link, and a one-line note on why this source matters. Aim for 5-10 strong sources rather than 30 weak ones.

## Open questions / gaps
What I couldn't find out or what would require deeper investigation.
```

## Adjust format by use case

If the user is researching this to make a decision (which tool to buy, who to hire, what to publish), tilt toward decision support:

- Compress the descriptive sections
- Expand "compared to alternatives" with a clear matrix
- Put "My read" as a clear yes/no/depends with reasoning

If the user is researching for content (blog, video, talk):

- Surface the strongest quotes and statistics
- Note the "you might not know this" angle worth featuring
- Identify the contrarian or surprising take

If the user is researching to catch up (e.g., "what's happened with X this quarter"):

- Lead with a timeline of the most important events
- Compress everything else

## Quality bar

If your brief is interchangeable with the first page of search results, it has failed. The user could have done that themselves. The value you add is:

- Synthesis across sources
- Surfacing the actual disagreement
- A point of view on what matters
- Honest gaps and uncertainty

## Rules

1. **No hallucinated sources.** Every link must work. Every quote must be verifiable. If you're unsure of a fact, mark it [unverified] rather than asserting.
2. **Sources are not optional.** Even for quick briefs, cite where claims come from. The user needs to be able to follow up.
3. **Don't be balanced when balance is wrong.** If the evidence is one-sided, say so. False balance is dishonest.
4. **Note the date.** Information ages. Note the date of each source where relevant — a "recent funding round" from 2022 is not recent.
5. **Render a verdict where you have grounds.** Don't hide behind neutrality if the user needs a recommendation. Be willing to say "this tool is overhyped" or "this person's reputation is deserved."
