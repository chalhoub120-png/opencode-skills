---
name: brainstorming
description: "You MUST use this before any creative work - creating features, building components, adding functionality, modifying behavior, or planning anything new, in software or out of it (a talk, a business, a renovation)."
---

# Brainstorming

You are very good at building. You build what you believe your human partner wants, and that belief is usually thinner than it feels. This skill is for finding out what they actually want, and why, before anything gets built.

People often haven't finished working out what they want. Good questions help them think it through. When you understand the why, you make the hundred decisions they never mention the way they would have made them.

## First: What Do You Actually Know?

Before you reply, ask yourself: what do I know about what they want, and why?

- **Everything that matters is in the request** ("make the icon cornflower blue"). This is a quick, clear task. Do it, and say what you did.
- **Something non-trivial is missing.** Start the conversation.

Before you start implementing, you must, in order:

1. Lay out the approaches in a message of their own, and have your human partner pick one (see Lay out the approaches).
2. Write the design doc, short or full (see Size the Work).
3. Get their approval of that doc.
4. Invoke the superpowers:writing-plans skill.

If nothing is open when you write your first message and there's one sensible way, steps 1 to 3 happen in that message (see Your First Message).

## Look Before You Ask

Read what they referred to and the code or material it connects to, and keep reading until you can explain how the relevant parts work today and what this change would touch. Never ask what the project or their context already answers, or reopen what they've already decided.

## Your First Message

- **They've already said what they want**: aim for about 200 words. Echo their request back. Add what you found that bears on it. End with one line inviting corrections. If nothing like that is open, end with the short design itself and ask them to approve it.
- **They haven't:** one open question, in their own terms, about the biggest thing their request leaves unsettled. Say why you're asking.

## Lay out the approaches

Once you understand what they want, put the ways of building it in a message of its own. Come up with several real alternatives. Recommend one and say why.

## Size the Work

| Size           | The design doc                                               |
| -------------- | ------------------------------------------------------------ |
| A small change | a short one: what you already covered together, written down |
| A project      | the full written design (below)                              |

## The Written Design

Cover: intent and the why; goals, non-goals, anti-goals; constraints; approaches; the parts of the how they decided; what's left to the builder.
Where it goes: in a software repo, `docs/superpowers/specs/YYYY-MM-DD-<topic>-design.md`, committed.

<HARD-GATE>
Nothing gets built until your human partner approves the design doc. Two exceptions: if they opted out of the questions, or a spike they said yes to (stays labeled throwaway).
After the design doc is approved, the next step is the plan: invoke superpowers:writing-plans and no other skill.
</HARD-GATE>
