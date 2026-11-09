---
name: writing-skills
description: Use when creating new skills, editing existing skills, or verifying skills work before deployment
---

# Writing Skills

## Overview

**Writing skills IS Test-Driven Development applied to process documentation.**

**Core principle:** If you didn't watch an agent fail without the skill, you don't know if the skill teaches the right thing.

**REQUIRED BACKGROUND:** You MUST understand superpowers:test-driven-development before using this skill.

## What is a Skill?

A **skill** is a reference guide for proven techniques, patterns, or tools. Skills help future agents find and apply effective approaches.
**Skills are:** Reusable techniques, patterns, tools, reference guides.
**Skills are NOT:** Narratives about how you solved a problem once.

## TDD Mapping for Skills

| TDD Concept             | Skill Creation                               |
| ----------------------- | -------------------------------------------- |
| **Test case**           | Pressure scenario with subagent              |
| **Production code**     | Skill document (SKILL.md)                    |
| **Test fails (RED)**    | Agent violates rule without skill (baseline) |
| **Test passes (GREEN)** | Agent complies with skill present            |
| **Refactor**            | Close loopholes while maintaining compliance |

## When to Create a Skill

Create when technique wasn't intuitively obvious; you'd reference it again; pattern applies broadly; others would benefit.
Don't create for one-off solutions, standard practices well-documented elsewhere, project-specific conventions, or mechanical constraints (automate instead).

## Skill Types

- **Technique** (condition-based-waiting, root-cause-tracing)
- **Pattern** (flatten-with-flags, test-invariants)
- **Reference** (API docs, syntax guides)

## Directory Structure

```
skills/skill-name/SKILL.md + supporting-file.* only if needed
```

Flat namespace. Separate heavy reference (100+ lines) and reusable tools.

## Writing SKILL.md

Description says only when to use it: triggering conditions, starting with "Use when...". Never summarizes workflow. Name uses only letters, numbers, hyphens. Keywords throughout for search.

## The Iron Law (Same as TDD)

```
NO SKILL WITHOUT A FAILING TEST FIRST
```

Write skill before testing? Delete it. Edit skill without testing? Same violation. **No exceptions.**

## Testing All Skill Types

- **Discipline-enforcing** (TDD): pressure scenarios; success = follows rule under maximum pressure.
- **Technique** (how-to): application scenarios; success = applies technique correctly.
- **Pattern** (mental models): recognition + application + counter-examples.
- **Reference** (docs/APIs): retrieval + application + gap testing.

## Common Rationalizations for Skipping Testing

| Excuse                         | Reality                                                   |
| ------------------------------ | --------------------------------------------------------- |
| "Skill is obviously clear"     | Clear to you ≠ clear to other agents. Test it.            |
| "Testing is overkill"          | Untested skills have issues. Always.                      |
| "I'll test if problems emerge" | Problems = agents can't use skill. Test BEFORE deploying. |

**All of these mean: Test before deploying. No exceptions.**

## Match the Form to the Failure

| Baseline failure                    | Right form                                      | Wrong form                                 |
| ----------------------------------- | ----------------------------------------------- | ------------------------------------------ |
| Skips/violates rule under pressure  | Prohibition + rationalization table + red flags | Soft guidance ("prefer...", "consider...") |
| Complies, but output wrong shape    | Positive recipe/contract: state what output IS  | Prohibition list                           |
| Omits required element              | Structural: REQUIRED field/slot                 | Prose reminders                            |
| Behavior should depend on condition | Conditional keyed to observable predicate       | Unconditional rule + exemptions            |

No nuance clauses. Exemption clauses don't scope.

## Bulletproofing Against Rationalization

When baseline failure is discipline failure, read `references/bulletproofing.md`: closing loopholes, spirit-vs-letter, rationalization table, red-flags list.

## RED-GREEN-REFACTOR for Skills

**RED:** Run pressure scenario WITHOUT skill. Document exact behavior and rationalizations.
**GREEN:** Write minimal skill addressing those violations. Run WITH skill.
**REFACTOR:** New rationalization? Add counter. Re-test until bulletproof.

## STOP: Before Moving to Next Skill

After writing ANY skill, you MUST STOP and complete the deployment process. Do NOT batch without testing each.

## Skill Creation Checklist (TDD Adapted)

- [ ] Create pressure scenarios (RED)
- [ ] Run WITHOUT skill - document baseline verbatim
- [ ] Name uses only letters, numbers, hyphens
- [ ] YAML frontmatter with `name` and `description`
- [ ] Description starts with "Use when..."
- [ ] Run WITH skill - verify comply (GREEN)
- [ ] Add explicit counters for new rationalizations (REFACTOR)
- [ ] Commit skill to git

## Discovery Workflow

1. Encounters problem → 2. Searches skills → 3. Finds SKILL (description matches) → 4. Scans overview → 5. Reads patterns → 6. Loads example.
   Optimize: put searchable terms early and often.
