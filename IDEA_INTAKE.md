# Idea Intake

## Purpose
Define the problem well enough to decide what research is worth doing.

## Rules
- Record the user's original idea verbatim in a quote block; add later clarifications beneath it, dated. Never edit the original.
- Do not treat embedded solutions as requirements.
- Clarify outcome before researching products or designing architecture.
- Ask only questions whose answers could materially change direction.
- Do not turn small questions into projects.

## Intake
Capture:
1. Original idea
2. Desired outcome
3. Underlying problem
4. Embedded solution, if any
5. MUST / SHOULD / NICE requirements
6. Hard constraints
7. Material assumptions
8. Blocking unknowns
9. Decision-changing research questions

Always test:
- Does an existing solution already achieve the outcome?
- Would a simpler process/configuration change solve it?

## Ask vs Assume
Ask only when the answer could:
- change the outcome
- create/remove a hard constraint
- eliminate a solution category
- materially affect money, credentials, sensitive data or autonomous actions
- cause substantial wasted research

Otherwise make a reversible assumption and label it ASSUMPTION.

Never assume budget, acceptable automation autonomy, data sensitivity or that the user wants custom development. Ask when material.

Ask all necessary questions together, maximum five, with a proposed default.

## Project Test
Create a project when the work is materially complex, especially when it involves:
- meaningful spend
- external integrations
- automation acting on the user's behalf
- multiple credible approaches needing comparison

Otherwise use a short intake + one research pass.

## Human Gate
For a substantial project:
- choose a slug describing the problem, not a solution (lowercase, hyphenated, 2-5 words)
- if `projects/<slug>/` already exists, stop and ask; never overwrite a project
- copy `_templates/PROJECT_STATE.md` to `projects/<slug>/PROJECT_STATE.md`; never modify the template
- populate intake information
- stop for approval before research

Do not create placeholder content.

## Intake Summary
Keep to one screen:
- outcome/problem
- MUST requirements
- hard constraints
- material assumptions/unknowns
- research questions
- open questions
- project/not-project classification
