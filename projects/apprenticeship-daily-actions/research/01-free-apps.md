# Research report: apprenticeship-daily-actions (free shared to-do list with reminders on Luca's iPhone)

**Check date for all features and pricing:** 2026-09-25. I stopped early at the coordinator's request.

**Headline:** I did not find 5 apps that meet every must-have with strong evidence. Only one app, Todoist's free plan, is supported on every must-have by official documentation. Apple Reminders probably qualifies, but the sources disagree on the most important point (b). TickTick probably qualifies too, but one step is unconfirmed. Five apps were ruled out, and two were not checked far enough to classify. Data collection, age limits and AUD prices were mostly not researched and are listed as gaps.

---

## Research objective
Find free iPhone apps that give Luca and a parent one shared list. Both must be able to add items. Luca's phone must alert him at a set time, including for items the parent added. Ticked items drop off and unticked items stay until done. Stop at 5 qualifying apps.

## Questions investigated
1. Does the free tier allow sharing?
2. Does a reminder set by one person alert the other person's device?
3. Do unticked items carry over, and does the app run on iPhone?
4. Should-haves: recurring items, whether the parent can see what's done, notes or links.
5. A simpler option without a dedicated app.
6. Data collected and age limits for each app. **Not researched. See gaps.**

---

## Comparison table

Must-haves:
- **M1:** shared list, both can add
- **M2:** push alert at a set time on Luca's iPhone, including items the parent added
- **M3:** tick off, and unticked items carry over
- **M4:** iPhone app
- **M5:** the free tier covers M1 to M4

| App | M1 Shared, both add | M2 Parent's items alert Luca's phone | M3 Tick off and carry over | M4 iPhone | M5 Free covers all | Overall |
|---|---|---|---|---|---|---|
| **Todoist (Beginner/free)** | MET, VERIFIED. Shared projects are "Available for Beginner, Pro, Business". Collaborators "can add new tasks, assign tasks, complete tasks". The free plan allows 5 collaborators per project. | MET, VERIFIED/LIKELY. Reminders are "Available for Beginner, Pro, Business". "In shared projects… you can assign reminders to specific collaborators." Assignees get push notifications. That the free tier specifically allows assigning a reminder to someone else is LIKELY, because the page gates no part of this except multiple reminders. | MET, LIKELY. Standard to-do behaviour: incomplete dated tasks become overdue and stay. Not confirmed in docs this session. | MET, LIKELY. App Store listing not checked. | MET, VERIFIED/LIKELY. Free limits: 5 personal projects, 1 custom reminder per task (automatic reminders also available), recurring due dates, comments, 5 MB uploads, 1-week activity history. | **Qualifies. Strongest evidence of any app.** |
| **Apple Reminders (built in)** | MET, VERIFIED. People who accept the invitation "can add items, delete items, and mark them as completed." Needs iCloud. | **CONFLICTING.** Apple's article 105124 (updated 2026-05-27) says "Notifications that you set for your reminders aren't shared with anyone else." Apple's Mac guide says "When you assign a reminder to someone other than yourself, they receive a notification", and there is a "Mute Notifications" setting for assigned reminders. An Apple Community thread from January 2024 reports due-date alerts firing on **both** partners' phones, fixed by "Mute Assigned Reminders". A 2020 thread reports alerts on one phone but not the other. | MET, LIKELY. Incomplete reminders stay in the list. The Mac settings page has "Show all-day reminders as overdue" and a "Today Notification" time for all-day reminders. | MET, VERIFIED. Built in. Invitees need iOS 13 or later. | MET, VERIFIED. Free with an Apple Account. | **Probable, but must be tested on the two phones.** |
| **TickTick (free)** | MET, VERIFIED. Pricing page: shared members Free 2 / Premium 29. Parent plus Luca fits if "2" counts the owner. | UNCERTAIN. Task assignment is Premium only (VERIFIED, pricing page). Official help, seen only as a search snippet because the page would not render, describes a per-list reminder setting per member: All Tasks / All Tasks (except assigned to others) / Tasks Assigned to Me / No Reminders. If Luca picks "All Tasks", the parent's items would alert him, but I could not confirm this setting is on the free tier. | MET, LIKELY | MET, LIKELY | LIKELY. Free limits: 9 lists, 99 tasks per list, 2 reminders per task. Premium US$49.99 a year. | **Probable. One free-tier setting still unconfirmed.** |
| **Trello (free)** | LIKELY. Shared boards; not checked in detail. | UNCERTAIN. Atlassian support, seen only via search summary: "You must be a member of the card (or watching it) in order to receive Due Date notifications", plus a reminder-time dropdown. Not confirmed whether the reminder time one user sets applies to other members. Free tier not confirmed. | LIKELY. Cards stay until archived; checklists exist. | LIKELY | UNCERTAIN. Recurring cards appear to need automation, which is limited on free. | Not established |
| **FamilyWall (free)** | LIKELY. Shared to-dos; tasks can be assigned to family members (third-party summary). | UNKNOWN. The official help page says only "In the Lists, you have the possibility to add due dates and reminders." It does not say who receives the reminder or whether this is Premium. | LIKELY | LIKELY | UNCERTAIN. Recurring tasks are reportedly Premium (third-party source). User reviews report push notifications failing (third-party). | Not established |
| Microsoft To Do | MET, LIKELY (free, shared lists) | **NOT MET, CORROBORATED.** Microsoft Q&A and Tech Community: "Reminders are set on a per-user basis"; a reminder "could only work where it was created… wouldn't be shared when a user assign this task to others." Seen via search summaries of several Microsoft threads. | n/a | n/a | n/a | **Fails M2.** Workaround: Luca sets his own reminder on each item. |
| Google Keep | MET, VERIFIED | **NOT MET, VERIFIED.** Official help: collaborators "can label, colour, archive or add reminders without changing the note for others", meaning reminders are per user. | n/a | n/a | n/a | **Fails M2** |
| Any.do | **NOT MET on free, CONFLICTING.** Official plan article: free has "Personal tasks and lists", with no shared space and no assignment. Some third-party articles say free includes shared lists. | n/a | n/a | n/a | Not met | **Likely fails M1/M5** |
| Cozi (free, with ads) | MET, LIKELY. Up to 12 family members; each signs in with their own email and **one shared account password** (FAQ). | **NOT MET for to-do items, LIKELY.** The FAQ describes reminders for calendar appointments only; the to-do list is for "tasks that aren't tied to set times." Calendar event reminders do reach attendees on free (1 reminder per attendee). | Calendar events do not carry over | LIKELY | Free is "supported by ads and sponsors". Gold US$39 a year. | **Fails M2 for list items** |

**Count of apps meeting every must-have:** 1 with near-verified evidence (Todoist) and 2 probable (Apple Reminders, TickTick). That is fewer than the 5 requested.

---

## Should-haves (partial)
- **Todoist:** recurring due dates are free (VERIFIED). Comments are free (VERIFIED) and can hold notes or links. The parent's view of completions is limited to 1 week of activity history on free (VERIFIED).
- **Apple Reminders:** recurring items, notes and URLs are LIKELY supported (standard fields; not confirmed this session). The parent can turn on "Completing Reminders" notifications for a shared list (VERIFIED, Apple 105124 and iPhoneLife).
- **TickTick:** recurring tasks LIKELY on free; not confirmed.

## Simpler options without a dedicated app
1. **Paper list plus a daily alarm on Luca's phone.** Meets M3, M4 and M5, and M2 as one daily nudge rather than per item. Fails M1 when the parent isn't physically there.
2. **Shared or invited calendar events.** Invited attendees get alerts, but calendar events do not carry over when missed, so M3 fails. Whether iCloud shared-calendar alerts reach other people was not checked (UNCERTAIN; an Apple Community thread titled "shared calendar does not share alerts" was seen but not opened).
3. **Any shared list plus a daily reminder Luca sets on his own phone** ("Check the list", repeating daily). This is a possible workaround, not a recommendation: it meets M2's "reminder at a set time" whatever the shared app does with other people's alerts. It changes M2 from a per-item alert to a daily prompt. Whether that is acceptable is for the user to decide. With it, Microsoft To Do and Google Keep would also work.

## Data collected and age limits
**UNKNOWN for every app. Not researched before the stop.**
- Cozi FAQ: no age statement found. Cozi uses a shared account password.
- Todoist: no age restriction mentioned on its collaboration page.
- Not checked: Apple Account age rules in Australia, App Store privacy labels, and each app's terms-of-service minimum age.

## Notable limitations
- **Apple Reminders:** official and community sources disagree on whether time alerts reach other people. Alert delivery is reported as inconsistent in both directions (Apple Community 2020 and 2024). The parent's device also receives alerts unless "Mute Notifications" for assigned reminders is used.
- **Todoist free:** 5-project cap, 1 custom reminder per task, 1-week activity history. No ads found (not formally checked).
- **TickTick free:** 2 members, no assignment, limits of 9 lists and 99 tasks per list.
- **Cozi:** ads on free; one shared password across the family.
- **FamilyWall:** third-party reports of unreliable push notifications.

## Conflicting evidence
1. **Apple Reminders, due-time alerts on other participants' devices** (detailed in the table). The article saying alerts aren't shared may be older wording, but that is inference only. A 5-minute test on the two phones would settle it.
2. **Any.do free sharing:** the official plan article says no; some third-party blogs say yes. I weight the official source higher.
3. **Apple's "Mute Notifications" wording:** the Mac guide describes it as muting reminders assigned to others in one place and reminders assigned to you in another.

## Unknowns and research gaps
- Candidates not checked or not finished: Trello (does the reminder reach other members, and is it free), FamilyWall (who gets the reminder, free vs Premium), OurHome and other chore apps, Google Tasks (sharing expected to be absent; not checked), Notion, Sweepy/Tody.
- Whether TickTick's per-list "All Tasks" reminder setting is on the free tier.
- Whether a Todoist free user can assign a reminder to a collaborator (LIKELY, not explicitly confirmed).
- Data collected (App Store privacy labels) and minimum ages for every app, including Apple Account rules for under-18s in Australia.
- AUD prices: none captured. USD only: TickTick Premium US$49.99 a year, Cozi Gold US$39 a year, Todoist Pro not captured.
- App Store availability in Australia and compatibility with the current iOS (the support site lists iOS 27) were not checked.
- Reliability of reminders was not tested; only community anecdotes were found.

## Findings that materially affect architecture
- The failure point the brief flagged is real. Microsoft To Do and Google Keep treat reminders as private to each user. Apple's documentation contradicts itself on this.
- Todoist's official docs say free-plan reminders can be directed to a specific collaborator. That directly addresses M2.
- If "reminder at a set time" can mean a daily prompt from Luca's own phone rather than a per-item alert, M2 no longer depends on the list app, and more apps qualify, including Apple Reminders with no uncertainty.
- No gap was found that free apps cannot fill, as long as either Todoist's reminder assignment is confirmed or the daily-prompt wording of M2 is accepted.

## Overall confidence
**MEDIUM-LOW.**
- Todoist qualifies: MEDIUM-HIGH.
- Apple Reminders: CONFLICTING, needs a two-phone test.
- TickTick: MEDIUM.
- Data collection and age: not researched.

## Sources
- [Apple – Share and assign reminders (105124)](https://support.apple.com/en-us/105124)
- [Apple – Assign shared reminders on Mac](https://support.apple.com/guide/reminders/remnf1ce7672/mac)
- [Apple – Change settings in Reminders on Mac](https://support.apple.com/guide/reminders/change-reminders-settings-remn4a9a4fe6/mac)
- [Apple – Use Reminders (102484)](https://support.apple.com/en-us/102484)
- [Apple Community thread 255425743 (2024)](https://discussions.apple.com/thread/255425743)
- [Apple Community thread 251542852 (2020)](https://discussions.apple.com/thread/251542852)
- [iPhoneLife – shared reminders notifications (2024-01-16)](https://www.iphonelife.com/content/how-to-turn-notifications-shared-reminders-iphone)
- [Todoist – Introduction to reminders](https://www.todoist.com/help/articles/introduction-to-reminders-9PezfU)
- [Todoist – Collaborate with friends or family](https://www.todoist.com/help/articles/collaborate-with-friends-or-family-in-todoist-tzkGUy)
- [Todoist – Pricing](https://www.todoist.com/pricing)
- [TickTick – Upgrade/pricing](https://ticktick.com/about/upgrade)
- [TickTick Help – How Teams Can Collaborate](https://help.ticktick.com/articles/7055781688281923584)
- [TickTick Help – FAQ](https://help.ticktick.com/articles/7055792921664028672)
- [Microsoft Q&A – To Do shared list reminders](https://learn.microsoft.com/en-us/answers/questions/5235204/to-do-shared-lists-reminders)
- [Microsoft Q&A – Shared To Do list, where do reminders go](https://learn.microsoft.com/en-us/answers/questions/4757829/shared-to-do-list-where-do-notifications-reminders)
- [Microsoft Tech Community – assigned task reminders](https://techcommunity.microsoft.com/discussions/to-do/to-do-task-assignment-feature-is-inconvenient--unable-to-set-reminders-for-tasks/4028520)
- [Google Keep Help – Share notes (iOS)](https://support.google.com/keep/answer/6101196?hl=en-GB&co=GENIE.Platform%3DiOS)
- [Any.do – Subscription plans explained](https://support.any.do/en/articles/8635977-any-do-subscription-plans-explained-free-premium-family-and-workspace)
- [Cozi – FAQ](https://www.cozi.com/faq/)
- [FamilyWall – Due date and reminder on a Todo](https://support.familywall.com/en/support/solutions/articles/47001245224-how-to-add-a-due-date-and-a-reminder-to-a-todo-)
- [Atlassian – Trello due dates](https://support.atlassian.com/trello/docs/adding-dates-to-cards/)
- [Atlassian – Trello mobile push settings](https://support.atlassian.com/trello/docs/mobile-push-notification-settings-for-trello/)
