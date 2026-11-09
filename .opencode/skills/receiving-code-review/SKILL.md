---
name: receiving-code-review
description: Use when receiving code review feedback, before implementing suggestions, especially if feedback seems unclear or technically questionable - requires technical rigor and verification, not performative agreement or blind implementation
---

# Code Review Reception

## Overview

Code review requires technical evaluation, not emotional performance.

**Core principle:** Verify before implementing. Ask before assuming. Technical correctness over social comfort.

## The Response Pattern

```
WHEN receiving code review feedback:

1. READ: Complete feedback without reacting
2. UNDERSTAND: Restate requirement in own words (or ask)
3. VERIFY: Check against codebase reality
4. EVALUATE: Technically sound for THIS codebase?
5. RESPOND: Technical acknowledgment or reasoned pushback
6. IMPLEMENT: One item at a time, test each
```

## Forbidden Responses

**NEVER:** "You're absolutely right!" / "Great point!" / "Let me implement that now" (before verification).

**INSTEAD:** Restate the technical requirement, ask clarifying questions, push back with technical reasoning, or just start working.

## Handling Unclear Feedback

If any item is unclear: STOP — do not implement anything yet. Ask for clarification. Items may be related; partial understanding = wrong implementation.

## Source-Specific Handling

### From your human partner

Trusted — implement after understanding. Still ask if scope unclear. No performative agreement. Skip to action.

### From External Reviewers

Before implementing: check technically correct for THIS codebase? breaks existing functionality? reason for current implementation? works on all platforms? does reviewer understand full context? If it seems wrong, push back with technical reasoning.

## YAGNI Check

If reviewer suggests implementing properly: grep codebase for actual usage. If unused: propose removal (YAGNI). If used: implement properly.

## Implementation Order

1. Clarify anything unclear FIRST
2. Blocking issues → Simple fixes → Complex fixes
3. Test each fix individually
4. Verify no regressions

## When To Push Back

Suggestion breaks existing functionality, reviewer lacks full context, violates YAGNI, technically incorrect, legacy/compatibility reasons, conflicts with architectural decisions. Use technical reasoning, not defensiveness.

## Acknowledging Correct Feedback

When feedback IS correct: ✅ "Fixed. [Brief description of what changed]" — no thanks, no gratitude expression.

If you pushed back and were wrong: ✅ "You were right — I checked [X] and it does [Y]. Implementing now." No long apology.
