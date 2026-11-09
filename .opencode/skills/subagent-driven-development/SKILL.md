---
name: subagent-driven-development
description: Use when executing implementation plans with independent tasks in the current session
---

# Subagent-Driven Development

Execute plan by dispatching a fresh implementer subagent per task, a task review (spec compliance + code quality) after each, and a broad whole-branch review at the end.

**Why subagents:** You delegate tasks to specialized agents with isolated context. They never inherit your session's context or history.

**Core principle:** Fresh subagent per task + task review (spec + quality) + broad final review = high quality, fast iteration

**Narration:** between tool calls, narrate at most one short line — the ledger and the tool results carry the record.

**Continuous execution:** Do not pause to check in with your human partner between tasks. Only stop for: irreversible/destructive operation; security-sensitive action; side effect outside worktree that norms say you ask about (merge/push/publish); plan so broken every path is a guess.

**Rulings, not stalls.** Conflicts, ambiguities, plan defects — decide them. Record every decision in the ledger as `Ruling: <what you decided> — <why> — <what it costs if wrong>`, and keep going.

## When to Use

Have implementation plan + tasks mostly independent + partner did not choose inline. Otherwise use executing-plans or manual execution.

## Setup

Ensure isolation via superpowers:using-git-worktrees. Track progress in a ledger file (`progress.md`), not only todos. Check for this plan's ledger; read `references/resuming.md` if one exists.

## Model Selection

Use least powerful model that can handle each role. Mechanical tasks (1-2 files, clear spec) → cheap; integration/judgment → standard; architecture/design + whole-branch review → most capable. Always specify the model explicitly when dispatching.

## The Task Loop

**Small same-shape work:** read `references/batching.md` before dispatching.
Hand artifacts over as files. Record BASE before dispatching.

### 1. Dispatch the implementer (fresh subagent, one task, brief path, report path, no-subagents contract)

### 2. Handle the report (DONE / DONE_WITH_CONCERNS / NEEDS_CONTEXT / BLOCKED)

### 3. Review the task (diff file via review-package, spec compliance + quality)

### 4. The fix loop (read `references/fix-loop.md` before every round)

### 5. Complete the task (append ledger line, mark todo complete)

## Final Review

Read `references/final-review.md` and follow it.

## Common Rationalizations

| Excuse                                        | Reality                                           |
| --------------------------------------------- | ------------------------------------------------- |
| "Close enough on spec compliance"             | Reviewer found spec gaps = not done.              |
| "I'll fix it myself, dispatching is overhead" | Controller fixes pollute context and skip review. |
| "One more round will converge"                | Past the cap, rounds don't converge.              |
| "The fix was small, skip the re-review"       | Unreviewed fixes are how regressions land.        |
| "Ledger bookkeeping is overhead"              | Ledger is what survives compaction.               |
