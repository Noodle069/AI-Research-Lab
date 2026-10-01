# Project State

## Project

Name: Apprenticeship daily actions (Luca's action checklist)

Created: 2026-09-25

Last updated: 2026-09-27

## Original Idea

> i wnt to start a new project, i want to develop an app where i can add action items for my son Luca, so that he can get reminders on his phone and check list that he can tick off each day, this is to help him grand trying to get a sparky apprenticeship

Clarification, 2026-09-25 (answers to intake questions):

> is there a free app, i am in Australia so if you find 5 free apps stop that part to save tokens, i want something that trigger reminders where either of can add and it helps him remember.
>
> prefernece is cheap as possible but pending if we build happy to pay just want cost effectove it is an investment into his futuer and hiopefully finding a job, what else can we do to him him find something keen to take him on?
>
> we both have iPhone 17 Pro , just ticked things off so that it helps him remember and if not ticked off stays ther
Clarification, 2026-09-25 (after research round 1):

> QLD, on the Gold Coast luca is 17 looking to leave school
>
> We have tried reminders, etc, but i want something that i can build and at the same learn how to use you. also part of your research here is his resume and cover letter, i want you to assess it for me assume you are a potential emploer pull out stragnhs weakness and waht you sugges to enhance it
>
> actualy how do i add pdf for you to assess?
Clarification, 2026-09-25 (answer to: what didn't work with Reminders?):

> was way too easy to ingnore skip and foret

Clarification, 2026-09-25:

> the pathways .md, why did you waste time with VIC and ACT etc, it is QLD only, you over cooked it, leverage his resume to give me ideas on what he can do to imrpove his changes

Clarification, 2026-09-25:

> he does not want school based

Clarification, 2026-09-25:

> also his resume and cover letter he can start immediately, updat the editable docs, i also attached his report LucaKelly_CON11C_profile, obviosuly dont mention attendance, also when he did work experince fo the week, he just helped with tools, and watched as he was not able to do anything with him, the dude was an old cranky fuck who tried talking luca out of being a sparky, so it actually broke his heart, (dont need ot include that but thought i would sahre for context for you)update the documents please

Clarification, 2026-09-25:

> format it so it reads easy and simple to follow so that he stands out in word format

> i would not say local i would say retriing, that is why he didnt take him on

## Desired Outcome

Confirmed by the user on 2026-09-25 (in substance: "it helps him remember", "hopefully finding a job"):

Luca reliably completes the steps that move him towards securing an electrical (sparky) apprenticeship, because the actions set by either of them are in front of him every day, he is reminded at the right time, and anything not done stays visible until it is.

Secondary outcome added 2026-09-25: identify what else can be done to help Luca find an employer willing to take him on as an apprentice.

Additional outcome added 2026-09-25 (later clarification): the user learns how to use Claude by building the app themselves. Learning is a goal in its own right, not only a means.

Additional deliverable added 2026-09-25: an employer's-eye assessment of Luca's resume and cover letter, covering strengths, weaknesses and suggested improvements.

## Problem Definition

Underlying problem: the path to an electrical apprenticeship involves many small, recurring and one-off actions (ASSUMPTION: e.g. applications, follow-ups, preparation). The user wants to be able to set those actions for Luca and have Luca see, be reminded of, and tick them off daily, so that momentum is kept and nothing is forgotten.

Embedded solution (recorded, not adopted): a custom-developed app in which the user adds action items, Luca receives reminders on his phone, and Luca ticks items off a daily checklist. Earlier on 2026-09-25 the user preferred a free existing app. Later that day the user said they had already tried Reminders and similar apps, and want to build the app themselves partly to learn how to use Claude. A custom build is therefore now a requirement chosen by the user. Existing apps remain the benchmark. Why Reminders fell short is UNKNOWN and should be captured, because it defines what the build must do better.

## Current Stage

RESEARCH

Possible stages:

DEFINE
RESEARCH
ARCHITECTURE
CRITIQUE
VALIDATION
RECOMMENDATION
READY_FOR_HANDOFF

## Requirements

### Must Have

- Both the user and Luca can add action items (user stated, 2026-09-25).
- Luca receives reminders on his iPhone (user stated).
- Luca has a checklist he can tick off each day (user stated).
- Items that are not ticked off stay on the list until they are (user stated, 2026-09-25).
- Works on iPhone 17 Pro for both users (user stated, 2026-09-25).
- The user builds it themselves with Claude's help, as a learning exercise (user stated, 2026-09-25).
- Reminders must be hard to ignore, skip or forget. Existing apps, including Reminders, failed on exactly this (user stated, 2026-09-25). How to achieve this is a research and design question and is not yet decided.

### Should Have

- Support both recurring daily actions and one-off tasks with due dates (ASSUMPTION; "each day" suggests recurring items, apprenticeship steps suggest one-offs).
- The user can see which items Luca has completed (ASSUMPTION; the user said "just ticked things off", so this is not a must-have).
- Items can be edited or removed by the user as circumstances change (ASSUMPTION).

### Nice to Have

- A simple view of progress or streaks over time (ASSUMPTION).
- Notes or links attached to an action item, e.g. an application link (ASSUMPTION).

## Constraints

- Location: Gold Coast, Queensland, Australia (user stated, 2026-09-25).
- Luca is 17 and intends to leave school (user stated, 2026-09-25).
- Queensland only. Research and advice must not cover other states (user stated, 2026-09-25).
- Full-time apprenticeship only; no school-based apprenticeship (user stated, 2026-09-25).
- Luca is available to start immediately (user stated, 2026-09-25).
- Resume must not mention attendance (user stated, 2026-09-25). Also left out: behaviour, the D grade, student ID and LUI.
- Work experience (1 week) was limited to carrying tools and watching. That electrician must not be named or used as a referee. Describe him as a "retiring electrician", which explains why there was no job offer (user stated, 2026-09-25). This supersedes the naming recommendation in reviews/01 (user context, 2026-09-25).
- School results, Year 11 Semester 1 2026 (report in documents/): four subjects B, two A, one D. Subject names were inferred from class codes and must be confirmed.
- Building software is outside the Current Boundary in CLAUDE.md. Research and design continue here; the build needs the user's explicit authorisation at handoff.
- Budget: as cheap as possible, free preferred. Paying is acceptable if it is cost-effective, e.g. for a build (user stated, 2026-09-25).
- Platform: both users have an iPhone 17 Pro (user stated, 2026-09-25). Android support not required.
- Research effort: stop searching for apps once 5 suitable free apps are found, to save tokens (user stated, 2026-09-25).

## Verified Facts

## Corroborated Facts

## Assumptions

- Luca has his own smartphone that can receive notifications.
  Reasonable because: the idea states reminders on his phone.
  If wrong: phone-based reminders are not viable; a different channel is needed.
- Luca is willing to use the system.
  Reasonable because: the goal is his apprenticeship.
  If wrong: any tool fails regardless of design; engagement becomes the core problem.
- The user wants to set tasks from their own device, separate from Luca's.
  Reasonable because: "i can add action items for my son".
  If wrong: a single shared device or paper list may be enough.
- The action items are low-sensitivity personal data (tasks, dates, possibly employer names).
  Reasonable because: they relate to job seeking, not health or finance.
  If wrong: stricter privacy handling and product selection would apply.
- A custom app is one option, not a requirement.
  Reasonable because: the outcome is Luca's progress, not software ownership.
  If wrong: existing products become benchmarks only (as in budget-adherence-tracking).

## Unknowns

- Custom app vs existing product: resolved 2026-09-25. Existing free app preferred.
- Phone platforms: resolved 2026-09-25. Both iPhone 17 Pro.
- Budget: resolved 2026-09-25. Free preferred, cost-effective paid acceptable.
- Apprenticeship pathway research: resolved 2026-09-25. In scope as a secondary outcome.
- Luca's age and whether he has agreed to this approach (not answered).
- State: resolved 2026-09-25, Qld (Gold Coast). Age 17, leaving school.
- Luca's credentials: resolved from his resume (documents/, 2026-09-25). Cert II Electrotechnology completed, White Card (Nov 2025), asbestos awareness (May 2026), P manual licence and own car, works at KFC, electrical work experience, casual trade assistant work. User-supplied, not independently verified.
- Why Reminders failed: resolved 2026-09-25. Too easy to ignore, skip and forget.
- Luca's intended start date for an apprenticeship.
- What techniques make phone reminders hard to ignore for a 17-year-old, and what iOS allows (e.g. repeating alerts, Time Sensitive / Critical notifications). A research question for the build.
- App data collection and age limits (research/01 gap).

## Research Questions

1. Does an existing product already let one person assign tasks to another, deliver phone reminders to the assignee, and let the assignee tick off a daily checklist, with the assigner able to see completion? (e.g. shared reminder/list apps, family organiser apps, habit/chore apps; candidates to be discovered by research, none presumed.)
2. Would a simpler process change achieve the outcome, e.g. a shared list or calendar using apps both phones already have, or a paper checklist plus phone alarms?
3. Which options support recurring daily items and one-off dated items together?
4. Which options deliver reliable push reminders on the relevant phone platforms, and what are their limitations?
5. What does each viable option cost in AUD, one-off and recurring, and what do free tiers include?
6. What personal data does each option collect about Luca, where is it stored, and are there age restrictions or parental-account requirements for users under 18?
7. If a custom app were built, what are the realistic minimum approaches for cross-device sync and push notifications, and what ongoing cost and maintenance would they carry? (Only if the user confirms custom development is wanted or no existing option is adequate.)
8. What are the typical steps to secure an electrical apprenticeship in the relevant Australian state, to inform the initial action list? (In scope, 2026-09-25.)
9. What else can realistically increase Luca's chances of an employer taking him on: e.g. pre-apprenticeship courses, Group Training Organisations, government incentives to employers, Apprenticeship Connect Australia providers, work experience, direct approaches to employers? (Added 2026-09-25; no option presumed.)

## Research Findings

App landscape (research/01-free-apps.md, checked 2026-09-25): fewer than 5 free apps meet every must-have with strong evidence. The critical differentiator is whether a reminder set by one person fires on the other person's phone. Research stopped early at the turn limit, so data collection and age limits are not yet researched.

Apprenticeship pathway (research/02-apprenticeship-pathway.md, 2026-09-25, overall MEDIUM):
- Luca needs an employer (direct or GTO) before he can enrol in the Cert III (UEE30820). Pathway takes about 4 years. VERIFIED/CORROBORATED.
- The screen he can most directly prepare for is the maths, mechanical-reasoning and literacy aptitude test. Free practice quizzes exist. VERIFIED/CORROBORATED.
- Other preparation: colour-vision test, White Card (about $100–190), driver licence, CV and referees, optional Cert II pre-apprenticeship ($0–~$8k depending on state and eligibility).
- Employer incentives: up to $5,000 (KAP) or $2,500 for 2026 commencements. From 1 Jan 2027 the KAP incentive drops to $4,000 and there is none for employers with 200+ staff (GTOs exempt). CORROBORATED from secondary sources only; must be checked on australianapprenticeships.gov.au before use. This makes Oct–Dec 2026 a good time to approach small contractors and GTOs.
- Most 2027 utility intakes have closed; the next cycle is LIKELY May–Jul 2027.
- Draft checklist of 15 actions in research/02 section 6.
- Much detail depends on Luca's state, which is still unknown.

## Existing Solutions

- Todoist free: meets all must-haves. VERIFIED/LIKELY; free-tier reminder assignment is LIKELY. Limits: 5 projects, 1 custom reminder per task, 1-week activity history. (research/01)
- Apple Reminders (built in): CONFLICTING on whether alerts fire on the other person's phone; needs a two-phone test. Otherwise meets all must-haves, free. (research/01)
- TickTick free: probable; whether the per-member "All Tasks" reminder setting is on free is UNCERTAIN. (research/01)
- Fail the must-have for reminders reaching the other phone: Microsoft To Do (CORROBORATED), Google Keep (VERIFIED), Cozi to-dos (LIKELY). Any.do free has no sharing (official source, CONFLICTING with third parties). (research/01)
- Not established: Trello, FamilyWall. (research/01)
- Workaround: any shared list plus a daily "check the list" alarm on Luca's phone. This changes the must-have from a per-item alert to a daily prompt; the user must decide. (research/01)

## Architecture Options

## Critic Findings

### Critical

### High

### Medium

### Low

## Research Gaps

## Decisions

Decision: Classified as a substantial project.

Reason: More than one plausible approach (existing app, shared list/calendar, custom app); involves automation acting on the user's behalf (reminders) and personal data about a family member; may involve spending money.

Evidence: IDEA_INTAKE.md step 9, WORKFLOW.md substantiality test.

Alternatives considered: Small idea with a single research pass. Rejected because of personal data about Luca and multiple plausible approaches.

What could cause this decision to change: Nothing likely.

Decision: Intake approved and research started (2026-09-25).

Reason: The user answered the intake questions and asked for research to begin ("is there a free app ... if you find 5 free apps stop").

Evidence: User clarification, 2026-09-25.

Alternatives considered: Asking about Luca's age and state before starting. Not done, because neither blocks the app research. The state is noted as a gap for the pathway research.

What could cause this decision to change: N/A.

## Validation Required

- Two-phone test of Apple Reminders: parent adds a timed reminder to a shared list; does it alert on Luca's iPhone? (research/01, CONFLICTING)
- Confirm Todoist free lets a reminder be set for a collaborator (research/01, LIKELY).
- Confirm employer incentive amounts and the 1 Jan 2027 changes on australianapprenticeships.gov.au or with an ACAP before Luca uses them in a pitch (research/02, CORROBORATED only).

## Current Recommendation

## Recommendation Confidence

HIGH / MEDIUM / LOW

Reason:

## Blocking Unknowns

None.

## Next Stage

ARCHITECTURE (or straight to RECOMMENDATION if an existing app meets every must-have)

## Next Action

2026-09-27: New versions made from the user's uploaded files (layout kept): documents/Luca Kelly Electrician Resume - 27 Sep.docx/.pdf (School Results section added: Industrial Skills A, Science in Practice A, Maths B, English B, from the report; BSQ D and attendance left out) and documents/Luca Kelly Cover Letter - 27 Sep.docx/.pdf (rewritten in Luca's voice with why he wants the apprenticeship and his results; duplicate text images removed). Later 2026-09-27: user chose a 1-page resume -> documents/Luca Kelly Electrician Resume - 1 Page.docx/.pdf (adds KFC Robina, casual front counter, from 20 Jun 2026, under 10 hrs/week; referee Lisa Crowe, RGM, taken from the offer letter; 'consistent attendance' line removed). Cover letter updated with KFC. Awaiting: user to check the subject names and the resume line "Consistent attendance at school"; go-ahead for research round 2.
