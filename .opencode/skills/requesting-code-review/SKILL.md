---
name: requesting-code-review
description: Use when completing tasks, implementing major features, or before merging to verify work meets requirements
---

# Requesting Code Review

Dispatch a code reviewer subagent to catch issues before they cascade. The reviewer gets precisely crafted context for evaluation — never your session's history.

**Core principle:** Review early, review often.

## When to Request Review

**Mandatory:** After each task in subagent-driven development, after completing major feature, before merge to main.
**Optional but valuable:** When stuck, before refactoring, after fixing complex bug.

## How to Request

**1. Get git SHAs:**

```bash
BASE_SHA=$(git rev-parse HEAD~1)  # or: git merge-base origin/main HEAD
HEAD_SHA=$(git rev-parse HEAD)
```

**2. Dispatch code reviewer subagent** with `general-purpose` subagent, filling the template at `code-reviewer.md` (DESCRIPTION, PLAN_OR_REQUIREMENTS, BASE_SHA, HEAD_SHA).

**3. Act on feedback:**

- Fix Critical immediately
- Fix Important before proceeding
- Note Minor for later
- Push back if reviewer is wrong (with reasoning)

## Example

```
[Just completed Task 2] Let me request code review before proceeding.
BASE_SHA=..., HEAD_SHA=...
[Dispatch reviewer] → Returns: Strengths / Important: Missing progress indicators / Minor: Magic number (100) / Assessment: Ready
You: [Fix progress indicators] [Continue]
```

## Common Rationalizations

| Excuse                                        | Reality                                                                               |
| --------------------------------------------- | ------------------------------------------------------------------------------------- |
| "I'll just review the diff myself"            | You're the coordinator — dispatch a reviewer subagent; the diff lives in its context. |
| "The reviewer needs my whole session history" | Hand it precisely crafted context, never your session's history.                      |

## Red Flags

**Never:** Skip review because "it's simple"; ignore Critical; proceed with unfixed Important; argue with valid technical feedback. If reviewer wrong: push back with technical reasoning, show code/tests.
