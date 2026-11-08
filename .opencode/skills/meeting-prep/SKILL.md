---
name: meeting-prep
description: "Generate a pre-meeting briefing dashboard before a call, or process post-meeting notes into a follow-up email and action items. Use this whenever the user says 'prep me for a meeting,' 'I have a call with,' 'meeting with [name],' 'debrief this meeting,' 'write a follow-up,' 'process these notes,' 'action items from,' or mentions an upcoming or just-finished meeting. Works for sales calls, investor meetings, podcast appearances, partner calls, team meetings, board meetings. Outputs an interactive HTML briefing for prep mode or a clean markdown debrief + ready-to-send email for debrief mode."
---

# Meeting Prep

You help the user walk into meetings sharper than everyone else in the room, and walk out with the follow-up email sent before they've closed their laptop.

This skill has two modes: **prep** (before the meeting) and **debrief** (after).

## Determine mode

If the user mentions an upcoming meeting → prep mode.
If the user mentions notes, outcomes, what was discussed → debrief mode.
If ambiguous, ask: "Prepping for this one or processing it after?"

---

## Mode: Prep

### Gather context

Ask conversationally, not as a form:

1. Who's the meeting with? (Name, role, company)
2. What's it about?
3. What outcome do you want?
4. Any history? (Prior conversations, existing relationship)
5. Meeting type? (Sales / investor / team / partner / podcast / board)

If a calendar connector is available, look up the event and infer what you can before asking. Skip questions you can already answer.

### Research

In parallel:

- Look up the person's company (website, news, recent funding)
- Look up the person (LinkedIn-style basics, recent public activity)
- Search past emails with this person if Gmail connector is available
- Check if the user has a `BUSINESS_CONTEXT.md` — use it to make goals and questions specific to the user's actual business, not generic

### Produce the briefing dashboard

Save as `meeting-prep-[name]-YYYY-MM-DD.html`. One scannable page, designed to be read in 90 seconds.

Sections:

1. **Top strip** — name, role, company, meeting time, location/link, your one-sentence read on what this meeting is really about
2. **Who they are** — bio paragraph, what their company does, recent signals (funding, news, hires, posts)
3. **What you want from this meeting**
   - Primary outcome (what success looks like)
   - Secondary outcome (what you'd settle for)
   - Information only this person can give you
4. **What they probably want**
   - What they're likely after
   - What they might ask that you should be ready for
5. **5 questions to ask** — lead with the sharpest. Mix: 2 information-gathering, 2 relationship, 1 that advances the deal/conversation. No softballs.
6. **Watch for** — signals this is going well or badly. Topics to steer toward or away from. The one thing not to say.
7. **Suggested agenda** — proposed time allocation if you're driving the meeting

### Meeting-type additions

**Sales / biz dev** — likely objections + responses, BANT-style qualification checklist, the next step to propose

**Investor** — numbers to have memorized (ARR, growth, burn, runway, churn), the narrative (why now, why you), questions investors ask that founders fumble

**Podcast** — 3 stories from your experience relevant to the topic, your contrarian or surprising take, a natural one-liner about your business

**Team / internal** — is this a decision meeting or info meeting? what decision should it produce? who shouldn't be there?

**Partner** — mutual benefit framing, what you can offer them, what would make a partnership meaningful enough to pursue

---

## Mode: Debrief

### Gather the notes

Ask the user to paste or describe what happened. Accept any format — rough notes, transcript, voice memo transcription, bullets.

### Produce two artifacts

**1. `meeting-debrief-[name]-YYYY-MM-DD.md`** — clean markdown debrief:

- **Summary** (3–5 bullets, no filler)
- **Decisions made** — what was decided and why
- **Action items table** — Action | Owner | Deadline | Priority. Propose deadlines if none were discussed and flag them as proposed.
- **Open questions** — anything unresolved that needs to come back
- **Flags** — anything surprising, concerning, or worth remembering about this person for next time

**2. A follow-up email draft** — saved as Gmail draft if connector available, otherwise printed in chat. Structure:

- Open with one specific line of genuine appreciation (not "thanks for your time" — something concrete from the conversation)
- Summarize what was discussed in 2–3 bullets
- List agreed-upon next steps with owners
- Propose the next meeting/checkpoint if appropriate
- Close with one clear CTA

Tone by meeting type: Sales = confident, moves the deal. Investor = professional, concise, leaves them wanting more. Team = direct, action-oriented. Podcast = warm, relationship-building. Partner = collaborative, specific about mutual benefit.

---

## Rules

1. **Specificity over comprehensiveness.** "Ask about their priorities" is useless. "Ask what's changed since they raised their Series B in March" is useful. Use real research, real names, real numbers.
2. **A prep brief should take 2 minutes to read.** Not 10. If it's longer, you're padding.
3. **The follow-up email is sacred.** Sent within 15 minutes of the call ending changes how the user is perceived. Make it good enough to send with minimal editing.
4. **Don't over-prepare.** A founder who reads 10 pages of prep sounds rehearsed. One who has 3 sharp questions and genuine curiosity sounds impressive. Choose 3 sharp things over 30 mediocre ones.
5. **Every debrief ends with a next step.** If the notes don't include one, flag that gap explicitly.
