# Research Workflow

## Project Layout
For substantial projects:

projects/<slug>/
  PROJECT_STATE.md
  research/
  architecture/
  critique/
  HANDOFF.md

PROJECT_STATE.md is the current source of truth.
Specialist outputs are immutable evidence; revisions use new files.
Specialist agents cannot write files: the main agent saves each output in full, as returned.
Number outputs in creation order: research/01-landscape.md, architecture/01-options.md, critique/01-review.md, research/02-disputed-claims.md.

PROJECT_STATE Current Stage values: DEFINE, RESEARCH, ARCHITECTURE, CRITIQUE, VALIDATION (research gaps and revision), RECOMMENDATION, READY_FOR_HANDOFF.
Update Last updated, Current Stage, Next Stage and Next Action at the end of every stage.

## DEFINE
Owner: main agent.

Produce:
- desired outcome/problem
- MUST requirements
- hard constraints
- material assumptions/unknowns
- research questions

Stop for approval for substantial projects.

## RESEARCH
Owner: researcher.

Research only questions that could affect feasibility, option elimination or recommendation.

Complete when each MUST requirement is:
- supported, or
- explicitly UNKNOWN with validation required.

Also check existing-product and simpler-process options.

## ARCHITECT
Owner: architect.

Use established evidence to produce genuinely different viable options.
Do not design eliminated options.
Flag any architecture dependency that remains unverified.

## CRITIQUE
Owner: critic.

Attack only material issues.

Classify findings:
- CRITICAL: invalidates or may invalidate approach
- HIGH: must resolve before implementation
- MEDIUM: material trade-off
- LOW: omit unless specifically useful

Main agent classifies CRITICAL/HIGH as:
- ACCEPTED
- DISPUTED FACT → research
- DISPUTED JUDGEMENT → main-agent decision
- REJECTED with reason

## VALIDATION / REVISION
Run only when critique reveals a disputed fact, blocking unknown or accepted material flaw.

Repeat critique only if:
- architecture materially changed, or
- CRITICAL/HIGH remains unresolved.

## RECOMMEND
Owner: main agent.

Apply DECISION_FRAMEWORK.md.
"Do not proceed", "use an existing product" and "keep current process" are valid outcomes.

## HANDOFF
Create HANDOFF.md only after recommendation approval.

## BUILD → TEST → RELEASE
Implementation stages. Run only after HANDOFF.md exists and the user approves starting implementation.
Code lives in `projects/<slug>/app/`. Record stage in PROJECT_STATE.md Next Stage/Next Action (BUILD, TEST, RELEASE).
These agents may write files, but only in their allowed paths. The main agent still owns PROJECT_STATE.md and saves each agent's report as `build/01-report.md`, `test/01-report.md`, `release/01-report.md`.

- BUILD. Owner: builder. Implements one approved slice of the handoff.
- TEST. Owner: tester. Verifies MUST requirements; reports defects, never fixes app code.
- Defects loop back to BUILD; repeat TEST until PASS or PASS WITH RISKS.
- RELEASE. Owner: releaser. Prepares (dry run) by default. Publishing needs explicit user approval for that specific action.

## Human Gates
Stop:
- before starting BUILD
- before any publish/deploy/purchase in RELEASE
- when TEST fails the same MUST requirement twice
- after DEFINE for substantial projects
- before a third critique round
- when a CRITICAL issue suggests abandoning/reframing
- at recommendation
- before implementation or external action

## Efficiency Rule
Skip any stage whose expected information value is low.
State the skipped stage and reason in one sentence.
