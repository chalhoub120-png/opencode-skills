---
name: executing-plans
description: Use when executing an implementation plan in the current session as the implementer yourself — your human partner chose inline execution, or no subagent tool is available
---

# Executing Plans

Execute the plan yourself, task by task, in this session: no implementer subagent per task, no reviewer per task. One fresh-context review of the whole branch at the end.

**Why inline:** Subagent-driven development pays for a fresh implementer and a fresh reviewer on every task. Inline execution pays for one context (yours) plus one reviewer at the end.

**Core principle:** The plan already did the thinking. Execute it exactly, prove each step with a test you watched fail and then pass, and leave a record that survives your own forgetting.

**Narration:** between tool calls, narrate at most one short line — the ledger and the tool results carry the record.

**Continuous execution:** Do not pause to check in with your human partner between tasks. Execute all tasks from the plan without stopping.

**Rulings, not stalls.** Conflicts, ambiguities, plan defects — decide them. Record every decision in the ledger as `Ruling: <what you decided> — <why> — <what it costs if wrong>`, and keep going.

Four things stop you, and only these: an irreversible or destructive operation; a security-sensitive action; a side effect outside this worktree that norms say you ask about first (a merge, a push to a shared branch, a publish); and a plan so broken that every path forward is a guess. For those, stop and ask.

## When to Use

- You have a plan from superpowers:writing-plans and your human partner chose inline execution.
- Your harness has no subagent tool.
- Tasks are mostly independent.

## The Process

Setup: worktree, workspace + ledger, read plan + spec, pre-flight scan.
Per task: read brief + BASE; work steps in order (TDD, run every verification, read every output); commit as the plan's commit steps say; run tests, ledger the result; mark todo complete.
Final: whole-branch review (fresh reviewer if you have one); Critical/Important → ONE fix pass; Minor → ledger.
Finish: collect every `Ruling:` line into your final message. Use superpowers:finishing-a-development-branch.

## Setup

Ensure isolation via superpowers:using-git-worktrees. Track progress in a ledger file (`progress.md`), not only todos. Check for this plan's ledger; tasks with a `Task <N>: complete` line are DONE — do not redo them.

**REQUIRED SUB-SKILL:** load superpowers:test-driven-development now, before Task 1.

## The completion contract

Before a task's ledger line: every test the brief names exists and ran; final run passed; every `Expected:` line compared against real output; every deviation has a `Ruling:` line. **REQUIRED SUB-SKILL:** superpowers:verification-before-completion governs the claim.

## Common Rationalizations

| Excuse                                                          | Reality                                  |
| --------------------------------------------------------------- | ---------------------------------------- |
| "I remember what Task N says"                                   | The brief has the exact values. Read it. |
| "I'll run the full suite at the end"                            | Per-step runs show which step broke it.  |
| "I read my own diff carefully; the final reviewer is redundant" | Same author, same blind spots.           |
| "Tests should pass, the change was trivial"                     | "Should" is not evidence. Run it.        |
