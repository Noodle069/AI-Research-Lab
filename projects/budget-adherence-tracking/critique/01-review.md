# Critique 01: budget-adherence-tracking

Critic review of PROJECT_STATE.md, research/01-landscape.md, research/02-local-build-options.md and architecture/01-options.md. Date: 2026-09-24.

I made a small number of web checks myself. They are marked **[critic-check]** and listed under Sources at the end. Each finding has a severity (CRITICAL / HIGH / MEDIUM / LOW) and a type:
- **FACT**: needs research.
- **JUDGEMENT**: main agent or user decides.
- **USER**: needs the user's answer.

---

## What is well supported

- **Option A's platform facts are solid.**
  - Flask binds to 127.0.0.1 by default. VERIFIED from Flask docs.
  - macOS lacks a full Python 3, and the python.org installer is the route. VERIFIED.
  - Chart library licences. VERIFIED.
  - Browser-storage eviction and Safari's 7-day rule. VERIFIED from MDN.
  - File System Access API works only in Chrome/Edge. VERIFIED.
  - Together these support "disk-based storage behind a loopback server" over "browser-only storage".
- **The iCloud risk is real and now VERIFIED, not just a hypothesis (R1).** Apple's support article says that when Desktop & Documents Folders is on, "all of your files move to iCloud and any new files you create are automatically stored in iCloud" [critic-check]. The recommendation to keep data outside `~/Documents` and `~/Desktop` is correct.
- **CSV-first with PDF deferred is well supported.**
  - Every bank with an official source offers CSV, spreadsheet or QIF/OFX.
  - PDF extraction is text-PDF-only and needs a template per bank.
  - The user said "CSV and/or PDF", so CSV alone meets the must-have.
- **Rules-first categorisation with no AI in the minimum version is right.** It is supported by Actual's VERIFIED learned-rule pattern and the weak zero-shot LLM evidence. It also removes a whole class of data-egress risk.
- **These design choices are sound and cheap:**
  - explicit DD/MM/YYYY parsing
  - integer cents
  - a preview-before-commit gate
  - no partial imports
  - Uncategorised counted in the overall total
  - computing aggregates on read.
- **The architect was honest about uncertainty.** Most unverified items are labelled and turned into R1–R18. The document does not claim to be final.

---

## Critical weaknesses

### C1. CRITICAL (JUDGEMENT + USER): Nobody has said who builds and maintains this app, and the answer decides whether Option A is viable at all

The proposal describes a real software product. Phase 1 alone includes:
- declarative per-bank profiles plus a generic column-mapping UI
- five-layer duplicate detection with multiset matching
- atomic batches with undo that "restores the categorisations it changed"
- a rule engine with priorities and regex
- effective-dated budgets
- CSP, Host and CSRF protection
- pre-import SQLite backups
- a launcher script.

The user is a non-specialist maintainer. The architecture mentions "AI-assisted" development only as a derived ASSUMPTION. In practice this almost certainly means the app will be written, and later fixed, by an AI coding assistant driven by the user. That has three consequences the proposal does not address:

1. **The AI tool is inside the data path.** The hard constraint is "I don't want AI to send it anywhere without approval". Debugging a failed import is where real rows get pasted or read. The row-numbered error messages the architecture specifies would show real content. Normalised-payee rules are "UNKNOWN until real descriptions are seen", and whoever writes them must see real descriptions. The architecture's only control is "a process rule". See H2 for the technical controls needed.
2. **The maintenance ratings are really ratings of the user's ability to drive an AI assistant.** "Maintenance: Low" and "bank format changes are handled through the mapping screen, not code edits" have no evidence behind them (see H5). When something breaks after 12 months (Python upgrade, a bank format change the mapping UI cannot express, a Werkzeug security release), the user needs the builder again.
3. **The $0 constraint may already be breached.** If the build depends on a paid AI subscription, the true cost is not $0, or it relies on an existing subscription being kept. This is UNKNOWN.

**Why CRITICAL:** if the user cannot, or should not, act as the product owner of an AI-built codebase, the right answer is E (Actual as-is, now with custom themes, see H1), F, or a much smaller "A-minimal". That reverses the recommendation.

**Resolve by** asking the user:
- who will build the app, and with what tool?
- is any paid subscription involved?
- will they accept a rule that real statement data is never shown to the AI tool, including when debugging?

Then size Phase 1 against that answer (see H4 for a smaller scope).

---

## HIGH findings

### H1. HIGH (USER + FACT): "My own app" was a one-word answer given before the evidence existed, and new evidence narrows the custom app's advantage further

The decision to build rests on "my own app", given on 2026-09-24 in answer to a binary question, before research showed how close Actual Budget comes. IDEA_INTAKE says never to assume the user wants custom development. A preference stated before the costs were known is thin ground for a multi-phase build.

New evidence the research and architecture missed [critic-check]:
- **Actual Budget has stable Custom Themes.** You can paste CSS, or install from a community catalog, which fetches from GitHub on selection. This is in the main docs, not under experimental features (actualbudget.org/docs/custom-themes). It weakens the "fresh look" argument, which is one of only three things the custom app would add.
- **Per-category spent figures are likely available through Actual's API.** Third-party sources report that Actual's budget-month data returns per-category budgeted, spent and balance. The actualpy docs (a third-party Python reimplementation) list "budgeted", "spent", "balance" and "carryover". Official API reference pages do not document the return type. Status: LIKELY, not VERIFIED. This bears on R16 and D2.
- **Actual's desktop app has no working auto-updater.** The maintainers removed the broken updater (GitHub issue #2972, PR #2983). That means fewer background network calls, but updates are manual.

With these, the custom app's only unique outcome-level benefits over E are:
- a multi-month budget-vs-actual trend chart per category (Actual has this only as the experimental Budget Analysis report, VERIFIED)
- PDF import (deferred anyway)
- ownership.

**Resolve by:**
- a 30–60 minute local trial of the Actual desktop app with one real CSV and a pasted custom theme, done by the user on their own machine
- then re-asking "my own app?" with a concrete cost comparison: build effort and ongoing upkeep versus "Actual plus one missing chart".

This is the "does this need to exist" gate. It is cheap and should come before Phase 0.

### H2. HIGH (JUDGEMENT, partly FACT): The data-locality analysis misses several realistic leak paths, and the ones it names rely on process discipline rather than controls

The architecture lists five egress paths. These are missing or under-controlled:

1. **The AI development tool (see C1).**
   - The data folder must be outside any folder the AI tool can read, and the tool should be technically denied access, not just told not to look. For example, Claude Code supports permission deny rules; the exact mechanism needs verifying.
   - Error messages and logs must never include row content. The architecture says logs exclude descriptions, but the row-numbered import error shown in the UI is the thing a user will copy into an AI chat. The error should report row number and field type only, for example "row 14: date '31/02/2026' invalid" is itself data, so show "row 14: invalid date" with the value visible only in the UI.
   - Payee normalisation rules will need real description patterns. Either the user writes them, or redacted samples are shared with explicit approval. That approval step must be designed in.
2. **Browser extensions and AI browser features.**
   - Any extension with "all sites" access can read `http://127.0.0.1` pages. Examples: password managers, grammar tools, AI sidebar assistants.
   - AI features built into browsers can send page content to a vendor.
   - This is directly relevant to "I don't want AI to send it anywhere". A separate browser profile with no extensions is a cheap mitigation.
3. **Browser history and sync.**
   - If URLs or page titles contain payee names or amounts (for example `/transactions?payee=WOOLWORTHS` or a title like "Groceries: $812 over"), Safari iCloud history or Chrome Sync may upload them. Whether localhost URLs are synced is UNCERTAIN (FACT).
   - Design rule: no transaction data in URLs or titles; filter by ID or POST.
4. **Python-side outbound calls.**
   - CSP only restricts the browser. It does nothing if a Python dependency, or a future AI-added dependency, makes network calls. Streamlit, a likely "easier" alternative an AI assistant might suggest, defaults `browser.gatherUsageStats` to true (VERIFIED from Streamlit config docs [critic-check]).
   - Controls: a dependency allow-list, pinned versions, and the outbound-monitor check repeated after every dependency change, not once.
5. **Where downloads land.**
   - Statements are downloaded manually. If the user's browser saves to Desktop, or the user files them in Documents, they sync to iCloud before the app ever sees them. The same applies to the app's "periodic CSV export" backups.
   - The setup checklist should cover the browser download location and whether Desktop & Documents sync is on.
6. **The research workspace itself** is at `~/Documents/AI Research Lab`. Any fixtures, header samples or spike outputs saved there are in iCloud if Desktop & Documents sync is on.

The constraint wording also needs confirming (USER). The user said "don't want AI to send it anywhere **without approval**". PROJECT_STATE hardened this to "never leaves the computer". That stricter reading rules out an encrypted offsite backup, which matters for data-loss risk (see Operational risks). Ask the user which reading they intend.

### H3. HIGH (JUDGEMENT + USER + FACT): The budget maths is underspecified for the cases that most often make personal budget reports wrong

"Did I stay within budget?" is only as right as the classification of non-spending flows. Gaps:

- **Account coverage is a hidden must-have.**
  - If the user imports only the transaction account and pays a credit card from it, card spending shows up as one lump "repayment" that cannot be categorised.
  - If the user imports both, the repayment must be a Transfer on both sides.
  - The requirement should be explicit: every account where spending happens must be imported, and every flow between the user's own accounts must be classified.
  - Transfer detection by "hints" (descriptions containing account names, "payment thank you") is weak, and the pattern list is UNKNOWN.
- **Savings may be a budget category.** Many personal budgets have a "Savings" line. If transfers to savings are excluded from spending as Transfers, that category always shows $0 used. The user's category list is not recorded, so this is UNKNOWN.
- **Credit card sign conventions.** Card CSVs often show purchases as positive. The profile needs a per-account sign flip. Status: UNKNOWN per bank, FACT.
- **Buy-now-pay-later (Afterpay, Zip), common in Australia.** Instalments hide the merchant and are spread over weeks, so the category is lost or the timing is distorted.
- **Split transactions.** One supermarket purchase covering groceries and household items. The data model allows one category per transaction. This may be acceptable, but it should be a stated simplification.
- **Refunds crossing months** can push a category's month negative. The display rule is undefined.
- **Pending versus posted transactions** in CSV exports (R5) affect both totals and duplicates.
- **The Phase 1 exit criterion cannot be checked as written.** "Reconciles with the bank statements' totals" works per account (net movement, or opening balance + transactions = closing balance). It cannot validate category totals. Category correctness needs a user review of each category for one month, possibly cross-checked in a spreadsheet (F).

**Resolve by:**
- asking the user for their accounts (transaction, cards, savings, offset, BNPL) and whether savings is one of the 9–10 categories
- adding a "flow type" field (spend / income / transfer / savings contribution) separate from category
- defining how refunds are displayed.

### H4. HIGH (JUDGEMENT + FACT): The duplicate design has a correctness flaw and redundant layers; simplify it

- **Layer (d), putting the running balance in the fingerprint, can cause false non-matches.** If a bank's balance for the same transaction differs between two exports (pending versus posted, intra-day ordering, recalculation), the same transaction is imported twice. That is silent double-counting, the exact failure dedupe exists to prevent. Whether AU bank balance columns are stable across exports is UNKNOWN (R5/R6).
- **Layer (b), the occurrence index within a file, depends on row order and duplicates what layer (c) does.**
  - If one export ends mid-day and the next starts on the same day, the indices do not line up.
  - The multiset match in (c) already handles two identical coffees correctly.
- **Layer (a), blocking on the same file hash, gives false comfort.** Re-downloading the same date range usually gives a different file, so hash equality rarely fires. It is harmless but adds nothing.
- **Minimum correct design:**
  - per account, a multiset match on (date, amount in cents, normalised description) over the date range that overlaps existing data
  - the preview shows "N new, M already present"
  - near-matches (same amount, date ±3 days) are only flagged, and only once real data shows date shifting (R5).
  - Balance should be used for reconciliation (first balance + sum = last balance), not identity.

### H5. HIGH (JUDGEMENT): The option comparison is tilted towards A through unsupported maintenance and effort ratings

- **A is rated "Ongoing maintenance: Low" and D2 "Medium (API drift)".** Both ratings are judgements with no evidence. A carries its own code drift, Python and Werkzeug upgrades, pip dependency updates, and every bug the user cannot fix unaided. D2 offloads the hardest code (import, dedupe, rules) to a maintained project. That asymmetry needs justifying, not asserting.
- **"Bank format changes are handled through the mapping screen, not code edits"** assumes the mapping UI can express every future change. It cannot handle:
  - a new XLSX format (NAB "spreadsheet", UNCERTAIN)
  - multi-line descriptions
  - a changed date format with text months
  - a new CR/DR suffix convention.
- **The comparison table has no build-effort estimate for any option.** "Time to a useful result: Medium" for A, versus minutes to install Actual, is the most decision-relevant number, and it is missing.
- **E and F are screened out as benchmark-only** because they "fail my own app". They are never scored on outcome fit, cost or upkeep, so the user cannot see what the custom app costs them relative to E and F.

**Resolve by** adding a build-effort estimate (in hours of the user's time, AI-assisted) and a 12-month upkeep estimate for A, D2 and E, and presenting E and F in the scored table with "fails stated preference" as a flag rather than an exclusion.

---

## MEDIUM findings

### M1. MEDIUM (JUDGEMENT): Phase 1 is over-scoped for a single-user personal budget

This is the true minimum, in my view.

**Keep:**
- hardcoded declarative profiles for the user's 2–4 banks, written from their real header rows
- strict date parsing
- integer cents
- multiset dedupe (H4)
- preview then commit
- a single SQLite file outside iCloud
- a pre-import backup copy
- exact-payee and "contains" rules with a simple first-match order
- manual override
- system categories plus a flow type (H3)
- the month view
- `TRUSTED_HOSTS` plus a random per-launch token (M2).

**Defer or remove:**
- the generic column-mapping UI: with a few known banks, an error message plus a profile edit is enough
- rule priorities and regex
- batch undo that restores categorisations: deleting a batch's rows plus the pre-import backup covers recovery
- near-duplicate review
- the "offer to delete the source file" feature: an unnecessary destructive action.

**Seed rules from the user's own definition.** The user says they have already defined "what is in each category". That list is a ready-made starting rule set, which cuts early manual categorisation. The architecture does not use it.

**Trends are a MUST HAVE (#4)** but land in Phase 2. With history import (NAB 731 days VERIFIED, CBA about 2 years UNCERTAIN), a basic trends view is cheap once data exists. Consider moving a simple version into Phase 1.

### M2. MEDIUM (FACT, largely resolvable now): The localhost threat is real, not overstated, but the mitigation is a few lines of config, not a design workstream; R7 can be mostly closed

- **Real-world evidence exists.** CVE-2024-34069: the Werkzeug debugger on localhost was reachable through an attacker-controlled domain because the Host header was not validated. Fixed in Werkzeug 3.0.3 (GitHub advisory GHSA-2g68-c3qc-8985) [critic-check].
- **Flask 3.1 provides `TRUSTED_HOSTS`**, a built-in Host allow-list that returns 400 for other hosts (Flask config docs, VERIFIED [critic-check]).
- **Chrome 142+ enforces Local Network Access**, a permission prompt before public sites can reach loopback addresses (Chrome for Developers blog). That reduces CSRF from web pages in Chrome. Status: CORROBORATED. Safari has no equivalent in the evidence (UNKNOWN).
- **The biggest practical risk is debug mode.** AI-generated Flask code commonly uses `app.run(debug=True)`, which enables an interactive debugger that can execute code. It must be a hard rule: no debug mode in the launcher, and Werkzeug 3.0.3 or later pinned.
- **Minimum controls:**
  - `TRUSTED_HOSTS = ["127.0.0.1", "localhost"]`
  - SameSite=Strict cookie, or a per-launch random token in forms
  - explicit `host="127.0.0.1"`
  - debug off.

  That is about ten lines, not an engineering item.

### M3. MEDIUM (FACT): D2 is presented as both easier and harder than the evidence shows, and a simpler variant is missing

- **Local access to the desktop app's budget is unconfirmed.** The API docs VERIFY that with no `serverURL` "no network connections will be made, and you'll only be able to access budget files already downloaded locally" [critic-check]. But the documented flow uses `downloadBudget` with a sync ID, and nothing documents opening the desktop app's own budget folder directly (R16 stands).
- **Concurrency is not considered.** The desktop app and the API writing the same SQLite-backed budget at the same time risks corruption. A D2 dashboard should be read-only and run only while Actual is closed. This is UNKNOWN and needs research.
- **"D2 needs Node" is not strictly true.** actualpy exists as a third-party Python reimplementation. But all its examples connect to a server, so local-only use is UNCERTAIN.
- **Missing variant, D3:** Actual does all the budgeting; the user's own small app or Numbers sheet reads Actual's CSV export (or an exported copy) and draws the trend charts. There is no API coupling and no concurrency risk, and it would be "my own dashboard".

### M4. MEDIUM (FACT): The architect upgraded some research claims

| Architect statement | Research status | Issue |
|---|---|---|
| OFX "VERIFIED available from Westpac and CBA (CBA from research/01's table)" | Westpac VERIFIED. CBA formats come from vendor blogs; the official CBA page "did not render" | CBA should be UNCERTAIN |
| "Every bank researched offers CSV or spreadsheet export" (used to justify deferring PDF) | Bendigo and St.George are UNCERTAIN; NAB's "spreadsheet" may be XLSX | Overstated. Holds only for the banks with VERIFIED formats |
| LuLu "named in research/01 as free" | Mentioned without a source | Correctly flagged as R18, but it is the only proposed control for Python-side egress, so it is load-bearing |
| "Security exposure is low because the app is loopback-only" | Not researched | Judgement. Depends on M2 controls and H2 |
| SQLite online backup API existence "LIKELY" | Python's `sqlite3.Connection.backup()` is in the standard library docs (since 3.7) | Can be VERIFIED trivially. Low risk |
| "Maintenance: Low", setup "medium-low" | Not researched | Judgement presented as a trade-off conclusion (H5) |

The new [arch-check] facts are reasonably labelled. The `@actual-app/api` no-network quote is confirmed by my check.

### M5. MEDIUM (JUDGEMENT + USER): Backup and data-loss risk is traded against locality without asking the user

- Keeping data out of iCloud leaves only two protections:
  - pre-import copies on the same disk, which do not help against disk failure, theft or loss
  - Time Machine, which needs an external disk the user may not own. Buying one conflicts with $0.
- Months of categorised history is exactly what the trends requirement needs.
- The user should choose between:
  - local-only with an external disk
  - an approved encrypted offsite copy, which their "without approval" wording may allow (H2)
  - accepting the risk.

### M6. MEDIUM (JUDGEMENT): Some options were missing or dismissed too quickly

- **Actual Budget plus a custom theme (E+).** No code at all, and the fastest route to the outcome. It was not considered because custom themes were not known.
- **D3** (see M3).
- **A-static: a Python script that writes a static HTML report.** No server, listener, CSRF or Host checks. Categorisation is edited in a rules CSV and an "uncategorised" CSV opened in Numbers. It is less friendly, but it removes a whole security surface and most of the UI code. It is a genuinely different "own app".
- **Low-code Python UIs (Streamlit, NiceGUI).** An AI assistant is likely to suggest these because tables and charts are nearly free. They should be assessed and either rejected or configured deliberately:
  - Streamlit's `gatherUsageStats` defaults to true (VERIFIED)
  - its `server.address` default is "(unset)", and which interfaces it listens on is UNCERTAIN from the docs.
- **Beancount + Fava**, a local web UI with budget support. Not investigated. Probably too much plain-text friction, but it was never checked.
- **Node/Express dismissal is weak.** "Bare `listen()` binds all interfaces" is fixed by one argument. Built-in `node:sqlite` availability is a researchable fact, not an unknown. This does not change the ranking (Python still wins on pdfplumber and simplicity), but the stated reasons are thin.

### M7. MEDIUM (JUDGEMENT): Automation risk is really about silent wrong answers, not destructive actions

- The system takes no external actions, so blast radius is limited to local data, which backups recover.
- The real harm is the user believing they are within budget when they are not. Causes:
  - an over-broad learned rule
  - a missed transfer
  - a double import
  - an unimported account.
- Mitigations should target visibility:
  - a per-month "coverage" panel: accounts imported and date ranges covered per account
  - the Uncategorised count
  - count of transactions per rule
  - a flag for any category that moves more than X% month on month.

  The coverage panel matters most, because a missing statement looks exactly like "under budget".

---

## LOW findings

- **L1.** The `.command` launcher opens a Terminal window, and closing it stops the server. Port conflicts and a second instance are partly handled. Fine for a first version.
- **L2.** Amount parsing: thousands separators, quoted fields, CR/DR suffixes, and file encoding (a BOM, a byte-order mark at the start of the file) need handling per profile. Small, but a frequent source of import bugs.
- **L3.** Pay-cycle versus calendar month is handled reversibly. Good.
- **L4.** The Flask development server is officially "not for production". For one user on loopback this is acceptable, but it should be stated as a conscious choice. Waitress is an alternative if needed.
- **L5.** The optional "delete source file from Downloads" feature should be removed; it adds a destructive action for no outcome benefit.

---

## Unsupported assumptions

- The user can direct an AI assistant to build and maintain a multi-component app (C1).
- The user will accept a browser tab plus launcher (open question 5).
- A column-mapping UI will absorb future bank format changes (H5).
- Maintenance for A is low (H5).
- A monthly routine takes under 15 minutes (ASSUMPTION, no basis).
- Transfer "hints" can reliably spot inter-account flows (H3).
- Balance columns are stable enough to use as a fingerprint (H4).
- "Statement data must never leave the computer" is exactly what the user meant (H2; their words say "without approval").
- The user has a local Time Machine disk (M5).

## Questionable evidence

- CBA export formats and limits: vendor blogs only (UNCERTAIN). The architect treats OFX as VERIFIED.
- All column layouts except CBA come from 2022–2023 community configs. ANZ is CONFLICTING.
- The zero-shot LLM accuracy figure comes from a single business-banking study.
- "Actual has no standard multi-month budget-vs-actual per category": Budget Analysis is VERIFIED experimental, but whether Custom Reports can overlay budget amounts was not checked.
- Actual's privacy position is a vendor statement. The custom theme catalog fetches from GitHub (network call, metadata only).

## Simpler alternatives

In order of increasing effort:
1. **E+:** Actual desktop app with tracking budget, a pasted custom CSS theme, and Custom Reports. No code.
2. **F:** a Numbers spreadsheet, as a stopgap and cross-check.
3. **D3:** Actual as the engine, plus the user's own trend dashboard or Numbers sheet built from Actual's CSV export.
4. **A-static:** a Python script that turns bank CSVs plus a rules CSV into a static HTML report.
5. **A-minimal:** the reduced Phase 1 in M1.
6. Option A as proposed.

## Security and privacy concerns

In order of real-world likelihood:
1. Real data reaching an AI tool during development or debugging (H2.1, C1).
2. Files in iCloud-synced Desktop or Documents, including downloads and exports (H2.5; VERIFIED sync behaviour).
3. Browser extensions or AI browser features reading localhost pages (H2.2).
4. History and sync leaks through URLs and titles (H2.3).
5. Debug mode left on (M2).
6. CSRF or DNS rebinding from web pages (M2): real but cheaply mitigated.
7. Exposure on the local network: low, given Flask's default plus an explicit bind.

## Automation risks

- An over-broad learned rule silently miscategorises.
- A retroactive rule change rewrites history. The preview gate is appropriate.
- Double import or a missing account produces a falsely reassuring result.
- No external blast radius. Human gates are sensibly placed; do not add more.

## Operational risks

- A Python upgrade breaks the virtual environment. Mitigated by a setup script, which itself needs maintaining.
- A bank format change blocks imports mid-month.
- No offsite backup (M5).
- The builder is unavailable when something breaks (C1).
- No health check for coverage (M7).

## Cost and lock-in concerns

- The $0 claim ignores the AI tool subscription, if one is used (C1), and an external backup disk (M5).
- Lock-in is low for A (SQLite plus CSV export).
- For D2, the dependency is on Actual's API and schema across monthly releases; D3 reduces this.
- Nothing here gets expensive at scale; this is a single user.

## Failure scenarios

1. User imports the transaction account only, and card purchases are hidden → every month looks within budget except one giant "repayment". (H3)
2. Overlapping CBA exports with a balance-in-fingerprint mismatch → a week of spending double-counted. (H4)
3. An import fails, the user pastes the error with row content into an AI chat → hard constraint breached. (H2)
4. Downloads saved to Desktop with iCloud sync on → statements in iCloud before import. (H2)
5. After 12 months a Python or Werkzeug upgrade breaks the launcher, the user cannot fix it, and the app is abandoned with its history locked in SQLite. Mitigated only if CSV export exists early.
6. The laptop is lost with no offsite backup → trend history gone. (M5)

---

## Required research (disputed facts)

1. **Actual API `getBudgetMonth` return type.** Does it include per-category `spent` and `balance`? Use official type definitions in the actualbudget/actual repo. Third-party sources say yes.
2. **Actual API local access.** Can `@actual-app/api` open the desktop app's local budget without a sync server? Is concurrent access with the running desktop app safe? Where does the desktop app store its data on macOS?
3. **Actual custom themes.** Confirm CSS paste works fully offline, and what network calls the theme catalog makes.
4. **Actual desktop Mac build.** Signing and notarisation status. Outbound connections (R17).
5. **CBA formats and limits.** OFX/CSV availability and export limits from an official source, correcting the architect's "VERIFIED".
6. **Bendigo and St.George export formats**, and whether NAB's "spreadsheet" is CSV or XLSX. Only if these are the user's banks.
7. **Pending transactions and balance stability.** Do AU bank CSV exports include pending transactions, and do running balances or descriptions change between exports (R5/R6)? This decides the dedupe design.
8. **Credit card CSV sign conventions** for the user's card issuers.
9. **Browser protections for loopback.**
   - Chrome Local Network Access: current status and whether it applies to top-level navigation or form POSTs to 127.0.0.1.
   - Safari equivalent, if any.
10. **Browser history sync of localhost URLs.** Do Safari iCloud history and Chrome Sync include `http://127.0.0.1` URLs and titles?
11. **Technical denial of AI tool access to a directory.** How the user's AI coding tool can be blocked from reading a directory (for example, Claude Code permission deny rules), and that tool's data retention.
12. **LuLu (R18):** current, free, compatible with the user's macOS.
13. **Streamlit** listen address when `server.address` is unset, only if Streamlit or NiceGUI is considered.
14. **Beancount/Fava budget capability**, for completeness of the landscape.

## Required architecture changes

1. **Add a "Builder and maintainer" section:**
   - who builds, with what tool, and at what cost
   - an AI-tool data boundary enforced technically (directory deny, data outside the workspace, error messages without row values, redacted-sample approval step).
2. **Rescope Phase 1 to A-minimal (M1).** Move the mapping UI, rule priorities, categorisation-restoring undo and near-duplicate review later. Use the user's category definitions as seed rules. Consider a basic trends view in Phase 1.
3. **Replace the layered dedupe with multiset matching** on (account, date, cents, normalised description) over the overlap range. Use balance only for reconciliation.
4. **Add a flow-type dimension** (spend / income / transfer / savings contribution), an account-coverage requirement and panel, per-account sign handling, a refund display rule, and a per-account reconciliation exit criterion.
5. **Specify security controls concretely:**
   - `TRUSTED_HOSTS`
   - an explicit 127.0.0.1 bind
   - debug forbidden
   - Werkzeug 3.0.3 or later
   - a per-launch token or SameSite=Strict
   - no data in URLs or titles
   - a dedicated browser profile with no extensions
   - a dependency allow-list with outbound monitoring repeated after changes.
6. **Add E+ and D3 to the options**, and score E, E+, F and D3 in the comparison table instead of excluding them. Add build-effort and 12-month upkeep estimates.
7. **Add a backup decision for the user** (M5), and include the browser download location and Desktop & Documents sync in the setup checklist.
8. **Export categorised transactions to CSV from Phase 1**, not Phase 2, as an exit route if the app is abandoned.

## Reasons not to proceed

- A maintained, MIT-licensed, local-first product (Actual) already covers:
  - import with mapping, duplicate detection and learned rules
  - per-category budget versus spent
  - custom styling.

  The remaining gap is essentially one chart.
- The builder and maintainer is unidentified, and the likely builder (an AI assistant) is itself the main threat to the user's stated data constraint.
- The user's preference for "my own app" has not yet been tested against a concrete statement of what building and owning it costs.

None of these is decisive on its own. Together they justify one informed user gate before any build work.

---

## Verdict on the provisional recommendation

**The ranking is acceptable as a technology choice, but the recommendation as written is not ready.**

- If a custom app is built, Option A (Python/Flask on loopback, SQLite outside iCloud, bundled charts, CSV-first, PDF deferred) is the right family. The platform evidence supports it better than B, C or D1.
- D2 as runner-up is reasonable, but it is riskier than presented (local access and concurrency are unverified), and D3 or E+ probably dominate it.

Three conditions come before Phase 0:
1. C1 is answered: who builds, with what tool, at what cost, and under what enforced data boundary.
2. H1 is answered: an informed reconfirmation of "my own app" after a short local trial of Actual with a custom theme.
3. H3 is answered: which accounts are imported, and whether savings is a budget category.

If the user reconfirms, proceed with A-minimal, not the full Phase 1.

This triggers the WORKFLOW human gate "when a CRITICAL finding suggests abandoning or reframing the project".

**Overall confidence in the proposal:**
- **MEDIUM** that A is the right technology family if something is built.
- **LOW-MEDIUM** that the proposal as written (scope, maintenance claims, privacy controls, budget maths) is ready to hand off.

---

## Sources ([critic-check])

- [Actual Budget: Custom Themes](https://actualbudget.org/docs/custom-themes/)
- [Actual Budget: API overview](https://actualbudget.org/docs/api/)
- [Actual Budget: API reference](https://actualbudget.org/docs/api/reference/)
- [Actual Budget: Reports](https://actualbudget.org/docs/reports/)
- [Actual Budget: Tracking budget](https://actualbudget.org/docs/getting-started/tracking-budget/)
- [actualpy: Getting budget information (third-party)](https://actualpy.readthedocs.io/en/stable/examples/getting-budget-information/)
- [Actual issue #2972: remove broken Electron autoupdate](https://github.com/actualbudget/actual/issues/2972)
- [Actual PR #2983: remove About screen and broken updater](https://github.com/actualbudget/actual/pull/2983)
- [Flask configuration (TRUSTED_HOSTS, DEBUG)](https://flask.palletsprojects.com/en/stable/config/)
- [GitHub Advisory GHSA-2g68-c3qc-8985 / CVE-2024-34069 (Werkzeug debugger)](https://github.com/advisories/GHSA-2g68-c3qc-8985)
- [Chrome for Developers: Local Network Access permission prompt](https://developer.chrome.com/blog/local-network-access)
- [gHacks: Chrome 142 restricts local network access](https://www.ghacks.net/2025/10/29/google-chrome-142-restricts-local-network-access-and-changes-sync-on-desktop/)
- [Streamlit config.toml reference](https://docs.streamlit.io/develop/api-reference/configuration/config.toml)
- [Apple Support: Add your Desktop and Documents files to iCloud Drive](https://support.apple.com/en-us/109344)

Files reviewed:
- /Users/alphakings/Documents/AI Research Lab/projects/budget-adherence-tracking/PROJECT_STATE.md
- /Users/alphakings/Documents/AI Research Lab/projects/budget-adherence-tracking/research/01-landscape.md
- /Users/alphakings/Documents/AI Research Lab/projects/budget-adherence-tracking/research/02-local-build-options.md
- /Users/alphakings/Documents/AI Research Lab/projects/budget-adherence-tracking/architecture/01-options.md
