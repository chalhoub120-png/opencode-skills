---
name: dispatching-parallel-agents
description: Use when facing 2+ independent tasks that can be worked on without shared state or sequential dependencies
---

# Dispatching Parallel Agents

## Overview

You delegate tasks to specialized agents with isolated context. By precisely crafting their instructions and context, you ensure they stay focused and succeed at their task. They should never inherit your session's context or history — you construct exactly what they need.

**Core principle:** Dispatch one agent per independent problem domain. Let them work concurrently.

## When to Use

**Use when:**

- 3+ test files failing with different root causes
- Multiple subsystems broken independently
- Each problem can be understood without context from others
- No shared state between investigations

**Don't use when:**

- Failures are related (fix one might fix others)
- Need to understand full system state
- Agents would interfere with each other

## The Pattern

### 1. Identify Independent Domains

Group failures by what's broken. Each domain is independent.

### 2. Create Focused Agent Tasks

Each agent gets: specific scope, clear goal, constraints, expected output.

### 3. Dispatch in Parallel

Issue all subagent dispatches in the same response — they run in parallel. Multiple dispatch calls in one response = parallel execution. One per response = sequential.

### 4. Review and Integrate

Read each summary, verify fixes don't conflict, run full test suite, integrate all changes.

## Agent Prompt Structure

Good agent prompts are: **Focused** (one clear problem domain), **Self-contained** (all context needed), **Specific about output**.

## Common Mistakes

**❌ Too broad:** "Fix all the tests" — agent gets lost
**✅ Specific:** "Fix agent-tool-abort.test.ts" — focused scope

**❌ No context / ❌ No constraints / ❌ Vague output** — give error messages, constraints like "Do NOT change production code", and a specific return.

## When NOT to Use

Related failures, need for full context, exploratory debugging, shared state (same files/resources).

## Verification

After agents return:

1. Review each summary
2. Check for conflicts (same code?)
3. Run full suite
4. Spot check — agents can make systematic errors
