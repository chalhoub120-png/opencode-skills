---
name: using-git-worktrees
description: Use when starting feature work that needs isolation from current workspace or before executing implementation plans - ensures an isolated workspace exists via native tools or git worktree fallback
---

# Using Git Worktrees

## Overview

Ensure work happens in an isolated workspace. Prefer your platform's native worktree tools. Fall back to manual git worktrees only when no native tool is available.

**Core principle:** Detect existing isolation first. Then use native tools. Then fall back to git. Never fight the harness.

**Announce at start:** "I'm using the using-git-worktrees skill to set up an isolated workspace."

## Step 0: Detect Existing Isolation

**Before creating anything, check if you are already in an isolated workspace.**

```bash
GIT_DIR=$(cd "$(git rev-parse --git-dir)" 2>/dev/null && pwd -P)
GIT_COMMON=$(cd "$(git rev-parse --git-common-dir)" 2>/dev/null && pwd -P)
BRANCH=$(git branch --show-current)
```

**If `GIT_DIR != GIT_COMMON` (and not a submodule):** You are already in a linked worktree. Skip to Step 2 (Project Setup). Do NOT create another worktree.

Report with branch state:

- On a branch: "Already in isolated workspace at `<path>` on branch `<name>`."
- Detached HEAD: "Already in isolated workspace at `<path>` (detached HEAD, externally managed). Branch creation needed at finish time."

**If `GIT_DIR == GIT_COMMON` (or in a submodule):** You are in a normal repo checkout.

Has the user already indicated their worktree preference in your instructions? If not, ask for consent before creating a worktree:

> "Would you like me to set up an isolated worktree? It protects your current branch from changes."

## Step 1: Create Isolated Workspace

**You have two mechanisms. Try them in this order.**

### 1a. Native Worktree Tools (preferred)

If you have a tool like `EnterWorktree`, `WorktreeCreate`, a `/worktree` command, or `--worktree` flag — use it and skip to Step 2.

Only proceed to Step 1b if you have no native worktree tool available.

### 1b. Git Worktree Fallback

**Only use this if Step 1a does not apply.**

#### Directory Selection

1. Check your instructions for a declared worktree directory preference.
2. Check for `.worktrees` or `worktrees` at project root. If found, use it (`.worktrees` wins).
3. Otherwise default to `.worktrees/` at project root.

#### Safety Verification (project-local directories only)

**MUST verify directory is ignored before creating worktree:**

```bash
git check-ignore -q .worktrees 2>/dev/null || git check-ignore -q worktrees 2>/dev/null
```

**If NOT ignored:** Add to .gitignore, commit the change, then proceed.

#### Create the Worktree

```bash
path="$LOCATION/$BRANCH_NAME"
git worktree add "$path" -b "$BRANCH_NAME"
cd "$path"
```

**Sandbox fallback:** If `git worktree add` fails with a permission error, tell the user and work in place.

## Step 2: Project Setup

Auto-detect and run appropriate setup (npm / cargo / pip / poetry / go mod).

## Step 3: Verify Clean Baseline

Run tests to ensure workspace starts clean. If tests fail: report and ask. If pass: report ready.

```
Worktree ready at <full-path>
Tests passing (<N> tests, 0 failures)
Ready to implement <feature-name>
```

## Quick Reference

| Situation                      | Action                          |
| ------------------------------ | ------------------------------- |
| Already in linked worktree     | Skip creation (Step 0)          |
| Native worktree tool available | Use it (Step 1a)                |
| No native tool                 | Git worktree fallback (Step 1b) |
| `.worktrees/` exists           | Use it (verify ignored)         |
| Directory not ignored          | Add to .gitignore + commit      |
| Permission error on create     | Sandbox fallback, work in place |
| Tests fail during baseline     | Report failures + ask           |
