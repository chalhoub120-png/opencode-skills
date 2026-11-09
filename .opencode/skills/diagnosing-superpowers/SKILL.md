---
name: diagnosing-superpowers
description: Use when a superpowers session went wrong and your human partner wants to know why — repeated work, ignored plans, stumbles, poor results, a skill that didn't fire, "it took too long", "why is it so expensive", "what is it doing" — or wants to build a bug report for the superpowers maintainers, for the current session or a past one identified by id or path, on any harness.
---

# Diagnosing Superpowers

## Overview

Pin down with your human partner what went wrong in a session, read the transcripts on disk, and report what happened with evidence. You report; you do not diagnose superpowers.

**Core principle:** Every finding cites `path:line`. No citation, no finding. Every number comes from the transcript or from a command you ran, never from memory.

## Workflow

1. **Problem intake.** Ask one question at a time until you can write a statement naming the session(s), the turn range if known, what your partner expected, what happened, and the observable they care about.
2. **Locate.** Resolve each session to verified absolute filesystem paths. Confirm a past session by quoting its first prompt and timestamp. Create `~/.superpowers/diagnosing-superpowers/<session-id>/`, tell your partner the path.
3. **Triage.** Read the region around the reported problem yourself. Then dispatch one analyst subagent per dimension in parallel.
4. **Report.** Fill every section of the report template in order, write it to the workspace, show it, and give the path.
5. **GitHub issues** — when report says possible or likely, or your partner asks. Search open and closed issues for the symptoms. Create the issue only after approval.
6. **Export** — only when your partner asks for a bundle; never build one unprompted.
7. **Similar sessions** — when asked.

## Quick reference

| Complaint                        | Read first, lead with         |
| -------------------------------- | ----------------------------- |
| "It took too long"               | cost-and-time, stumbles       |
| "Why did it do this extra work?" | repeated-work, plan-adherence |
| "Why is it so expensive?"        | cost-and-time                 |
| "What the hell is it doing?"     | skill-timeline                |
| "It ignored the plan"            | plan-adherence                |
| "Skill X never fired"            | skill-timeline                |

## Hard rules

- **Context safety.** One transcript line can be a megabyte.
- **Read-only.** Never modify, move, or delete a session file.
- **Human prompts only.** Hook output, system reminders, and tool results are not your partner's words.
- **No superpowers diagnosis.** Report involvement and stop. Never name a defect in a skill or propose a change.
- **Approval gates.** No archive before your partner has seen the scrub log and file list. No issue or comment before they approve the exact text.
- **Intake before analysis.** Nothing starts until your partner has answered.
