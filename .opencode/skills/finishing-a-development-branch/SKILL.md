---
name: finishing-a-development-branch
description: Use when implementation is complete, all tests pass, and you need to decide how to integrate the work
---

# Finishing a Development Branch

## Overview

**Core principle:** Verify tests → Detect environment → Present options → Execute choice → Clean up.

**Announce at start:** "I'm using the finishing-a-development-branch skill to complete this work."

## Step 1: Verify Tests

Run the project's full test suite (`npm test` / `cargo test` / `pytest` / `go test ./...`).

**If tests fail**, report the failures and stop. **If tests pass:** continue.

## Step 2: Detect Environment

```bash
GIT_DIR=$(cd "$(git rev-parse --git-dir)" 2>/dev/null && pwd -P)
GIT_COMMON=$(cd "$(git rev-parse --git-common-dir)" 2>/dev/null && pwd -P)
WORKTREE_PATH=$(git rev-parse --show-toplevel)
```

| State                                  | Menu                         | Cleanup                 |
| -------------------------------------- | ---------------------------- | ----------------------- |
| `GIT_DIR == GIT_COMMON` (normal repo)  | Standard 3 options           | No worktree to clean up |
| `GIT_DIR != GIT_COMMON`, named branch  | Standard 3 options           | Provenance-based        |
| `GIT_DIR != GIT_COMMON`, detached HEAD | Reduced 2 options (no merge) | Externally managed      |

## Step 3: Determine Base Branch

Confirm the fork point before merging: "This branch split from <your best guess> - is that correct?"

## Step 4: Present Options

**Normal repo and named-branch worktree — present exactly these 3 options:**

```
Implementation complete. What would you like to do?

1. Merge back to <base-branch> locally
2. Push and create a Pull Request
3. Keep the branch as-is (I'll handle it later)

Which option?
```

**Detached HEAD — present exactly these 2 options:**

```
Implementation complete. You're on a detached HEAD (externally managed workspace).

1. Push as new branch and create a Pull Request
2. Keep as-is (I'll handle it later)

Which option?
```

Wait for their answer; the integration decision is theirs.

## Step 5: Execute Choice

### Option 1: Merge Locally

```bash
MAIN_ROOT=$(git -C "$(git rev-parse --git-common-dir)/.." rev-parse --show-toplevel)
cd "$MAIN_ROOT"
git checkout <base-branch>
git pull
git merge <feature-branch>
<test command>
```

Once green: clean up (Step 6), then delete branch.

### Option 2: Push and Create PR

```bash
git push -u origin <feature-branch>
```

Create PR against <base-branch>, report URL. Keep the worktree.

### Option 3: Keep As-Is

Report: "Keeping branch <name>. Worktree preserved at <path>."

### Discard (explicit request only)

Requires typed confirmation `discard`, then force-delete branch and clean worktree.

## Step 6: Cleanup Workspace

Runs for Option 1 and confirmed discards. If worktree is under `.worktrees/` or `worktrees/` — Superpowers created it, we own cleanup. If removal is refused, show files and ask. Otherwise the host owns the workspace — leave it in place.
