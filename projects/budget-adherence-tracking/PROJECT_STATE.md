# Project State

## Project

Name: Budget adherence tracking (Budget tracker)

Created: 2026-09-24

Last updated: 2026-10-01

## Original Idea

> I want an online budget app where i paste my statement into it and it assess my statements based on my budget to see if i have staayed within my budget or not, and i want to make it look fresh and nice and easy to ready, i would like to see monthly stats and tracking for each budget category i will have 9-10 categores

Clarification, 2026-09-24:

> i dont want AI to send it anywhere without approval, i live in Australia, so i want all answrs in australis and AUD, i bank with a few banks here and can get .csv and PDF easy

Clarification, 2026-09-24:

> i want $0 for now, something local host that works can that be done?
> i will be downloading statemnts and adding them to my app, so it wont be integrated for now, i have my budget, what is in each categy and amounts defined

Clarification, 2026-09-24 (answer to: own custom-built app, or an existing free local tool?):

> my own app

## Desired Outcome

Each month I can tell quickly, without manual tallying, whether I stayed within my budget overall and in each of my 9–10 categories, and I can see how each category is trending month to month.

## Problem Definition

Underlying problem: checking whether actual spending matched a planned budget currently takes effort (ASSUMPTION: done manually or not at all). Transactions from statements across several banks have to be sorted into budget categories, totalled, and compared against per-category limits, and the result needs to be presented clearly enough to act on.

Embedded solution (recorded, not adopted): a custom locally hosted budget app ("my app") into which downloaded statements are added, which categorises transactions, compares them to the budget, and shows monthly per-category stats with a fresh, easy-to-read design. Originally described as an "online" app with pasted statements. The user confirmed on 2026-09-24 that they want their own app, so a custom local app is now a requirement rather than one candidate. Existing tools and spreadsheets are still researched as a benchmark, as a source of reusable components, and as a fallback.

## Current Stage

RELEASE

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

- Nothing leaves the computer: the app makes no outbound network connection, verified by test (user stated, 2026-09-30).
- Import statements I download manually from my banks (user stated; originally pasting, 2026-09-24: downloading statements and adding them).
- Works with statements from several Australian banks (user stated, 2026-09-24).
- Accepts CSV and/or PDF statements (user stated, 2026-09-24: both easily available).
- Assign each transaction to one of 9–10 budget categories I define (user stated; categories, their contents and amounts already defined by the user, 2026-09-24).
- Compare actual spending per category against my budget and show whether I stayed within it (user stated).
- Show monthly stats and per-category tracking across months (user stated).
- Clear, easy-to-read, modern-looking presentation (user stated).
- It is the user's own custom-built app, not an existing budgeting product (user stated, 2026-09-24).

### Should Have

- Categorisation that remembers merchants so I do not recategorise the same payee every month (ASSUMPTION).
- Ability to correct a transaction's category manually (ASSUMPTION).
- History retained between months so trends can be shown (ASSUMPTION; implied by "monthly stats and tracking").
- Handle refunds, transfers between my own accounts, and income so they do not distort category spending (ASSUMPTION).
- Detect duplicate transactions when overlapping statements are imported (ASSUMPTION; research/01 shows bank export limits make overlapping imports likely, so this may become a must-have).

### Nice to Have

- Alerts when a category is close to its limit (ASSUMPTION).

## Constraints

- Location: Australia. All research, products, pricing and regulation must be Australian-applicable; amounts in AUD (user stated, 2026-09-24).
- Budget: AUD $0, one-off and recurring, for now (user stated, 2026-09-24).
- Hosting: runs locally on the user's own computer (localhost) (user stated, 2026-09-24).
- No bank integration for now; statements are downloaded manually and imported (user stated, 2026-09-24).
- Data transmission: statement data must not be sent anywhere without the user's explicit approval (user stated, 2026-09-24). Interpreted as covering AI services and any other external service. Combined with the localhost constraint, the working rule is that statement data stays on the user's computer.

## Verified Facts

- Actual Budget is MIT-licensed, releases roughly monthly (v26.9.0, 2026-09-01), has macOS desktop builds, stores data locally, and learns payee→category rules from user corrections. Evidence: research/01-landscape.md Q1, Q4.
- Actual Budget imports CSV/QIF/OFX with field mapping, debit/credit split and duplicate detection, but not PDF. Evidence: research/01-landscape.md Q1.
- NAB exports "spreadsheet, QIF or PDF" with up to 731 days of history; Westpac exports CSV, QBO, QIF and OFX; Macquarie exports CSV and QIF (personal: on-screen transactions only). Evidence: research/01-landscape.md Q3.
- Browser storage is best-effort and can be evicted; Safari deletes script-created storage for a site not interacted with in 7 days of browser use. Evidence: research/01-landscape.md Q5 (MDN).
- pdfplumber (MIT) and Camelot (MIT) extract tables locally from text-based PDFs only; tabula-py needs Java. Evidence: research/01-landscape.md Q8.
- Flask, Uvicorn and Vite listen on 127.0.0.1/localhost by default; Python http.server and Node server.listen() without a host listen on all network interfaces. Evidence: research/02-local-build-options.md A.
- A browser app can save to a real file on disk (File System Access API) only in Chrome/Edge, not Safari or Firefox. Evidence: research/02-local-build-options.md D.
- Chart.js, uPlot (MIT) and Recharts (MIT, React-only) are free to bundle; ECharts is Apache-2.0 (CORROBORATED). Evidence: research/02-local-build-options.md E.
- macOS does not ship a full Python 3; the python.org graphical installer is the recommended route. Evidence: research/02-local-build-options.md G.
- Tauri v2 needs Xcode, Rust and Node; Electron needs macOS 13 Ventura or later. Evidence: research/02-local-build-options.md C.
- Apple silicon and T2 Macs encrypt the disk automatically; FileVault ties the key to the login password. Evidence: research/02-local-build-options.md B.

## Corroborated Facts

- Australian bank CSV formats differ in header row presence (CBA and ANZ reportedly headerless), signed amount vs separate debit/credit columns, date format and column count. Evidence: research/01-landscape.md Q3.
- Australian bank dates are day/month/year. Evidence: research/01-landscape.md Q3.
- An app built on the user's own Mac is not blocked by Gatekeeper's unidentified-developer check (applies to quarantined downloads). Evidence: research/02-local-build-options.md C.
- Apple Numbers is free to edit on Mac; Excel for Mac cannot save edits without a paid licence. Evidence: research/02-local-build-options.md F.
- CommBank and Macquarie limit export size, so overlapping imports and duplicate detection are likely. Evidence: research/01-landscape.md Q3.

## Assumptions

- The user is the only user (personal budget, not shared household). Reasonable from wording. If wrong, multi-user access becomes a requirement.
- The user's computer is a Mac (from the working environment). If wrong, platform compatibility of local options changes.
- The user can install and run a local app or start a local server. If wrong, only zero-setup options such as a spreadsheet or a single HTML file remain.
- Budget periods are calendar months. If periods follow pay cycles, date handling changes.
- A single currency (AUD) is used. Reasonable given the user's statements. If wrong, currency conversion is needed.
- CSV exports differ in column layout between the user's banks. Reasonable from general experience. If wrong, import is simpler.
- Manual categorisation effort is acceptable at first as long as it reduces over time. If zero-effort categorisation is required, rule-based or local AI categorisation becomes necessary.

## Unknowns

- Which specific Australian banks. Affects CSV and PDF formats. Not blocking; research can cover the major banks.
- Budget periods: calendar month or pay cycle.
- Exact current CSV columns for each of the user's banks (only CommBank CORROBORATED; ANZ CONFLICTING; NAB export may be XLSX not CSV). Evidence: research/01-landscape.md Q3.
- Whether the user's banks' PDF statements are text-based and parseable.
- Accuracy of local categorisation on Australian personal transactions.
- User's macOS version and chip; whether FileVault and the macOS firewall are on.
- How the user currently tracks spending, and what has failed with previous tools.

## Research Questions

1. Does an existing free, locally run budgeting tool (open-source or free desktop app) already achieve the outcome (per-category budget vs actual, monthly trends, clear visuals, CSV import, AUD) on a Mac with data kept on the device? What are its licence, maintenance status and limitations? (Benchmark, fallback and possible source of reusable components, since the user wants their own app.)
2. Would a simpler process change achieve the outcome, e.g. a free spreadsheet template (Excel, Numbers, LibreOffice) with imported CSV and category rules?
3. What CSV and PDF statement formats do major Australian banks provide, how consistent are they across banks, and how reliably can each be parsed?
4. What methods exist for automatic transaction categorisation that run locally at no cost (merchant/keyword rules, bank-provided categories, local AI models), and how accurate are they in practice?
5. How can a local-only setup keep statement data safe on the device (storage location, encryption, backups), and does any candidate tool make hidden network calls (telemetry, sync, AI)?
6. What free technology options exist for building a local-only personal app on a Mac (e.g. a browser app served on localhost, a single-file HTML app, a desktop app framework), including local data storage and charting, and what are their trade-offs in complexity, maintenance and data safety?
7. What setup and ongoing maintenance does each local option require (installation, updates, dependencies, backups) for a non-specialist user?
8. Can PDF statements from Australian banks be converted to transactions locally, at no cost, with acceptable accuracy, or should CSV be the primary input?

## Research Findings

Research pass 1 (research/01-landscape.md, 2026-09-24) is partial: the researcher hit its turn limit. Q1, Q3, Q4 and Q8 were researched against sources. Q2, Q5, Q6 and Q7 rest mostly on general knowledge (LIKELY at best).

Summary:
- A $0, local-only budget tool on a Mac is feasible: several free local tools exist, and the building blocks (CSV parsing, local PDF extraction, local storage, charting) are free.
- Bank CSV formats vary enough that the app needs per-bank import profiles or a mapping step, with explicit day/month/year date parsing.
- CSV (or OFX/QIF) should be the primary input. PDF parsing is possible locally but per-bank and fragile; it is useful mainly for history beyond the CSV window (LIKELY).
- Rules learned from user corrections are the proven categorisation pattern. Zero-shot AI categorisation of terse descriptions shows weak accuracy (UNCERTAIN, one study).
- Browser-only storage risks silent data loss; disk-based storage (e.g. SQLite) avoids this (LIKELY).

Research pass 2 (research/02-local-build-options.md, 2026-09-24) closed the platform gaps:
- Everything needed to run a local app is free (Python/Node, SQLite, chart libraries); the Apple Developer Program is only needed to distribute apps to others.
- Network exposure depends on server choice: some servers listen on the whole network by default, so the app must be bound to 127.0.0.1.
- A browser-only app can save to a real file only in Chrome/Edge.
- Setup effort differs sharply: Python needs one installer; Tauri needs Xcode + Rust + Node; SQLCipher encryption needs a source build. Disk encryption is largely handled by the Mac hardware/FileVault.

RESEARCH stage complete: every must-have has a researched answer or explicit UNKNOWN; existing-product and spreadsheet options investigated.

## Existing Solutions

- Actual Budget: closest benchmark and fallback; MIT code is legally reusable. Gaps: no PDF import; multi-month budget-vs-actual trend by category is experimental only; network behaviour not independently audited. (research/01)
- GnuCash: budget vs actual report, official Mac builds; double-entry and dated UI. (research/01)
- hledger: strong monthly budget reports; text/command-line only. (research/01)
- HomeBank, Firefly III, Sure: higher friction on a Mac (fixed CSV format / Docker + database). (research/01)
- Spreadsheet (Numbers or LibreOffice): feasible at $0 but weak on multi-bank normalisation, rules, duplicates and look; Google Sheets conflicts with local-only. Not researched against sources. (research/01)

## Architecture Options

Architecture pass 1 (architecture/01-options.md, 2026-09-24). Hypothesis for critique.

- A: Localhost Python web app. Flask bound to 127.0.0.1, SQLite file in a non-iCloud folder, server-rendered pages, bundled Chart.js/uPlot, double-click launcher. Provisionally strongest.
- B: Single-file browser app (no server). Browser storage or File System Access API (Chrome/Edge only). Zero install, but risks data loss.
- C: Desktop-packaged app. C1 Electron, C2 Tauri, C3 native-window wrapper around A. Toolchain-heavy except C3, which could be a later phase.
- D: Build on Actual Budget. D1 fork (high burden); D2 Actual as engine plus the user's own dashboard. Runner-up if "my own app" allows it.
- E: Actual Budget as-is. Benchmark and fallback; fails "my own app".
- F: Spreadsheet (Numbers/LibreOffice). Stopgap and cross-check; fails "my own app".

Shared design: per-bank declarative CSV profiles plus a mapping fallback; strict DD/MM/YYYY parsing; layered duplicate detection; preview-and-approve import gate with undo; rules-first categorisation learned from user corrections (no AI in the minimum version); Transfer/Income/Uncategorised system categories; Host-header and CSRF checks against browser-borne localhost attacks.

Phases: 0 preparation (checklist, header rows only) → 1 CSV import and month view → 2 trends and rule management → 3 PDF (conditional) → 4 optional wrapper or ML suggestions.

Architect confidence: MEDIUM. Research requirements R1–R18 are listed in architecture/01-options.md. Most relevant: R1 (iCloud sync of the data folder), R2/R3 (real bank CSV layouts and account types), R7 (localhost browser attacks), R8 (sqlite3 in the python.org build), R16/R17 (Actual API and network behaviour, D2 only).

## Critic Findings

Critique 01 (critique/01-review.md, 2026-09-24). Verdict: Option A is the right technology family if something is built, but the recommendation is not ready. Critic confidence in the proposal as written: LOW-MEDIUM.

### Critical

- C1. Nobody has said who builds and maintains the app. The likely builder is an AI coding assistant, which is itself inside the data path, and its cost may breach $0. Classification: ACCEPTED, and needs the user's answer. Triggers the WORKFLOW human gate (reframing).

### High

- H1. "My own app" was answered before the evidence existed. Actual Budget also has stable custom CSS themes (critic-check), which narrows the custom app's unique benefit to a multi-month trend chart, PDF import and ownership. Classification: DISPUTED JUDGEMENT, referred to the user. The main agent does not override the user's stated preference, but the user should reconfirm it now that the costs are known. The theme facts go to research (disputed facts 1–4).
- H2. Data-locality leak paths are missing or rely on discipline: the AI development tool, browser extensions and AI browser features, browser history sync, Python-side outbound calls, download location, and the research workspace in ~/Documents. The main agent also hardened "without approval" into "never leaves". Classification: ACCEPTED. The architecture must add technical controls. The constraint wording goes back to the user.
- H3. The budget maths is underspecified: account coverage, credit card repayments, savings as a category, card sign conventions, buy-now-pay-later, refunds crossing months, and an exit criterion that cannot be checked as written. Classification: ACCEPTED. Add a flow-type dimension, a coverage panel and a per-account reconciliation check. Account list referred to the user.
- H4. The duplicate design has a flaw (a balance column in the fingerprint can double-count) and redundant layers. Classification: ACCEPTED. Replace with per-account multiset matching; use balance for reconciliation only.
- H5. The option comparison is tilted: maintenance ratings are unsupported, there are no build-effort or upkeep estimates, and E/F were excluded rather than scored. Classification: ACCEPTED.

### Medium

- M1. Phase 1 over-scoped; define A-minimal; seed rules from the user's category definitions; basic trends in Phase 1. ACCEPTED.
- M2. Localhost threat real but cheaply mitigated (TRUSTED_HOSTS, explicit bind, debug off, Werkzeug ≥3.0.3, per-launch token). ACCEPTED; R7 largely closed by critic-check evidence.
- M3. D2 local access and concurrency unverified; missing variant D3 (Actual plus own dashboard from CSV export). ACCEPTED.
- M4. Architect upgraded some claims (CBA OFX, "every bank offers CSV", LuLu). ACCEPTED; correct in revision.
- M5. Backup vs locality trade-off not put to the user. ACCEPTED; referred to user.
- M6. Missing options: E+ (Actual with custom theme), D3, A-static, Streamlit/NiceGUI, Beancount/Fava. ACCEPTED for E+, D3, A-static; others noted.
- M7. Main automation risk is silently wrong answers; add a coverage panel. ACCEPTED.

### Low

- L1–L5 (launcher Terminal window, amount parsing details, pay-cycle handling, Flask dev server, remove delete-source-file feature). ACCEPTED; carry into revision.

## Research Gaps

- Disputed facts from critique/01-review.md (items 1–14): Actual API spent figures and local access, Actual custom themes offline, Actual Mac build network behaviour, CBA formats from an official source, pending transactions and balance stability, card sign conventions, browser loopback protections, localhost URL history sync, technical denial of AI tool access to a folder, LuLu. To run after the user gate, scoped by the user's answers.

- Q2, Q5, Q6 and Q7 gaps from pass 1 were closed by research/02-local-build-options.md. Remaining minor gaps: formal Apple docs on ad-hoc signing; easy SQLCipher install route; Safari Origin Private File System.
- Ollama's official network behaviour, including remotely run `-cloud` models. Only needed if local AI categorisation is considered.
- Real CSV header/column layout from each of the user's banks.

## Decisions

Decision: Handle the 21 library vulnerabilities by upgrading what works on the current Python (3.9.6) inside the app's own virtual environment, re-testing, and reporting what remains. No newer Python install.

Reason: User chose the recommended option 2026-10-01. The app is local, offline and reads only the user's own PDFs; the Pillow image paths were not exercised.

Evidence: test/01-report.md (pip-audit: 21 known vulnerabilities in flask, click, pdfminer.six, pillow).

Alternatives considered: Install Python 3.14 from python.org (system change); leave as is.

What could cause this decision to change: Fixed versions not available for Python 3.9, leaving material vulnerabilities in code the app actually uses.

Decision: Slice 6 is function-first with a plain, readable layout; colour and look-and-feel move to a separate optional styling pass after the user has tried it.

Reason: User said 2026-10-01 that functionality is key and the look can be changed later.

Evidence: Conversation 2026-10-01; HANDOFF.md slices 6 and 7 and requirement 9 updated.

Alternatives considered: Styling inside slice 6 (declined).

What could cause this decision to change: The user wanting a particular look earlier.

Decision: The ING statement parser keeps the merchant line (the continuation line under each row) as part of the description.

Reason: User chose "Yes, keep the merchant line" 2026-10-01. Without it 43% of real spend rows (749 of 1,751) have no payee and cannot be categorised. No real data is saved in the app, so there is no migration.

Evidence: Conversation 2026-10-01; build/05-report.md. Supersedes the slice 2 rule "skip continuation lines" for the merchant line. The "Date dd/mm/yyyy Card ####" line stays excluded.

Alternatives considered: Leave as is (declined).

What could cause this decision to change: Real-file tests showing the merchant line is inconsistent across ING files.

Decision: Offset accounts are treated like spending accounts for flow defaults (money out = spend, money in = income). Transfers between own accounts are still detected as pairs and excluded. Loan accounts and credit card credits keep the transfer default for now.

Reason: User said 2026-10-01 they pay bills directly out of the offset account; the transfer default would have hidden real bills from category totals (builder's real-file run: 1,393 of 2,230 rows were defaulting to transfer).

Evidence: Conversation 2026-10-01; build/03-report.md.

Alternatives considered: Keep offset as transfer-only (declined).

What could cause this decision to change: Real-file checks showing loan-account rows (interest, fees) need different handling, or card refunds being wrongly excluded.

Decision: Keep the row values for Sinking (total 3,095.93) in the app config; the $1.00 gap to the printed 3,096.93 stays flagged as unresolved.

Reason: User said 3,096.93 is the total sinking fund (2026-10-01), but every Sinking row matches its item lines and the printed grand total 13,361.74 only works with 3,095.93. No row or item accounts for the extra $1.00.

Evidence: budget-categories.md data note; source PDF pages 1-4.

Alternatives considered: Adding $1.00 to an unspecified category (not done, would be a guess).

What could cause this decision to change: The user naming the category that should hold the extra $1.00, or correcting the PDF.

Decision: Judge each category by actual spending against its Regular amount, and track each Sinking pool as a running balance (set aside minus irregular bills paid).

Reason: User chose the recommended option 2026-09-30 over comparing against the full monthly transfer.

Evidence: Conversation 2026-09-30; budget-categories.md; HANDOFF.md requirement 7b.

Alternatives considered: Total vs actual (simple); rejected because a quarterly bill would distort single months.

What could cause this decision to change: The user finding the two-layer view too complex.

Decision: Transactions from multiple accounts are combined; the month comes from transaction dates; categories are labels assigned by the app. The user also wants a view of where spending is over budget ("where I'm bleeding").

Reason: User answered 2026-09-30.

Evidence: Conversation 2026-09-30; budget-categories.md. HANDOFF.md requirement 7 and new 7a updated.

Alternatives considered: One real account per category (declined).

What could cause this decision to change: The user's account structure changing.

Decision: Recommendation approved: build option P1. HANDOFF.md written.

Reason: User approved 2026-09-30 ("Approve, write handoff").

Evidence: Conversation 2026-09-30; research/05; architecture/02.

Alternatives considered: P2, P3, Actual as-is, spreadsheet (see architecture/02).

What could cause this decision to change: Parsing failing on real descriptions in ways the gates cannot fix; the user changing scope.

Decision: The earlier approval stands: the AI builder (Claude) may read the user's real statements to build and debug the app. The "nothing leaves the computer" MUST applies to the finished app.

Reason: Asked 2026-09-30 after the conflict was pointed out; user chose "Keep the earlier approval" over "Fake data from now on".

Evidence: Conversation 2026-09-30. Note recorded for the user: anything Claude reads is sent to Claude's service; this can't be undone for data already read.

Alternatives considered: Fake data only from now on (recommended by main agent; declined by user).

What could cause this decision to change: The user revoking the approval at any time.

Decision: Skip critique round 2.

Reason: User chose to skip on 2026-09-30. Main agent had recommended skipping: critic C1, H1, H2, M5 resolved by user answers; the main design risk (PDF parsing) was tested in research/05. Stage skipped: CRITIQUE round 2. Risk accepted: design changes since round 1 were not independently attacked.

Evidence: research/05-parsing-spike.md; user answer 2026-09-30.

Alternatives considered: Run critique round 2.

What could cause this decision to change: The user asking for it, or a new material unknown appearing during build.

Decision: New MUST: nothing can leave the user's computer. The finished app must make no outbound network connection and this must be verified, not assumed.

Reason: User stated 2026-09-30 ("make sure nothing can leave my computer"). Strengthens the earlier "without approval" constraint for the app itself.

Evidence: User answer 2026-09-30. Scope of this rule for the AI builder's own access to real statements is being clarified with the user (earlier approval on 2026-09-30 allowed sharing whole statements with Claude).

Alternatives considered: N/A.

What could cause this decision to change: The user changing the wording.

Decision: Input is PDF only. The app must import text PDF statements from ING, NAB (credit card) and the offset/home-loan reports (likely Macquarie). CSV is not available to the user.

Reason: User answered 2026-09-30 ("PDF only") after research/04 showed all 11 real files are text PDFs. Reverses the earlier "CSV-first, PDF deferred" assumption in the critique and architecture/01.

Evidence: research/04-real-statement-shapes.md; user answer 2026-09-30.

Alternatives considered: CSV-first (not available to the user); Actual Budget fallback (no PDF import, per research/01).

What could cause this decision to change: The user finding CSV downloads, or PDF parsing proving unreliable on real transaction rows (not yet tested).

Decision: Statements come from NAB, ING and Macquarie, all as CSV. Other banks are out of scope for now.

Reason: User answered 2026-09-30 ("all csv, nab, ing, macquarie").

Evidence: Conversation 2026-09-30.

Alternatives considered: N/A.

What could cause this decision to change: The user adding another bank. Real CSV layouts for each bank are still UNKNOWN; validating them is an open research item.

Decision: Backups are local-only: automatic copies on the user's Mac plus manual copies to an external drive. No cloud backup.

Reason: Asked 2026-09-30 (critic M5); user chose "Local copies only", which keeps the $0 and data-stays-local constraints.

Evidence: Conversation 2026-09-30; critique/01-review.md M5.

Alternatives considered: Encrypted cloud copy; no backup. Not chosen.

What could cause this decision to change: The user wanting protection against loss of the whole Mac.

Decision: User reconfirmed a custom-built own app, after being told a free existing local tool (Actual Budget) covers most of the requirements (critic H1).

Reason: Asked 2026-09-30; user chose "Yes, custom app" over "Try Actual first".

Evidence: Conversation 2026-09-30; critique/01-review.md H1.

Alternatives considered: Trial Actual Budget with a custom theme (declined by user); Actual remains the fallback.

What could cause this decision to change: The user changing their mind, or the app proving too costly to maintain at $0.

Decision: User approved sharing whole real statements with Claude (the AI builder) for building and testing this app.

Reason: Asked 2026-09-30 which data rule to use; after the trade-off was explained, the user chose "whole statements" over fake-data-only and edited-rows options. Resolves the wording question in critic H2 (the constraint is "without approval", and this is that approval).

Evidence: Conversation 2026-09-30. Scope: statements the user provides for this project only. Does not extend to other projects or to any third-party service other than the Claude session itself. Each new class of sharing (for example, a different tool) needs fresh approval.

Alternatives considered: Fake data only (recommended by main agent; HIGH confidence, lower exposure); a few real rows. Declined by the user.

What could cause this decision to change: The user revoking it. Note for the user: whole statements can include account numbers and your name, and cannot be un-shared once sent.

Decision: Pause at the human gate before revising architecture.

Reason: Critical finding C1 and high finding H1 could reframe the project (custom build vs Actual Budget with a theme). WORKFLOW requires stopping when a CRITICAL finding suggests abandoning or reframing.

Evidence: critique/01-review.md.

Alternatives considered: Revising the architecture first. Rejected, because the user's answers decide what to revise.

What could cause this decision to change: N/A.

Decision: The data constraint was recorded more strictly than the user stated it.

Reason: The user said "without approval"; PROJECT_STATE recorded "never leaves the computer". Flagged by critic H2. The user is asked to confirm which is intended.

Evidence: Clarification 2026-09-24; critique/01-review.md H2.

Alternatives considered: N/A.

What could cause this decision to change: The user's answer.

Decision: Treat as a substantial project.

Reason: Involves personal financial data (sensitive) and more than one plausible approach (existing local tool, spreadsheet, custom local app).

Evidence: Substantiality test in WORKFLOW.md; original idea.

Alternatives considered: Small-idea path — rejected because sensitive data and multiple approaches are involved.

What could cause this decision to change: None expected.

Decision: Build the user's own custom app rather than adopt an existing product.

Reason: User stated preference, 2026-09-24 ("my own app").

Evidence: User clarification 2026-09-24.

Alternatives considered: Existing free local tools and spreadsheets. Retained as benchmark and fallback; research will still report whether they meet the outcome.

What could cause this decision to change: The user changing their preference, or research finding that a custom app cannot meet the must-haves at $0.

Decision: Intake approved; proceed to RESEARCH.

Reason: The user answered the final intake question on 2026-09-24 after being told research would start on their answer.

Evidence: Conversation 2026-09-24.

Alternatives considered: None.

What could cause this decision to change: N/A.

Decision: Scope limited to a free, local-only tool with manual statement import; bank integration and hosted options are out of scope for now.

Reason: User stated AUD $0 budget, localhost, and manual download/import (2026-09-24).

Evidence: User clarifications 2026-09-24.

Alternatives considered: Paid hosted apps and open-banking import — excluded by user constraints; may be revisited later.

What could cause this decision to change: User raising the budget, or wanting phone access or automatic import.

## Validation Required

- Check each bank's CSV layout against a real export from the user (header row and column order only; see note on data sharing).
- Test PDF extraction on a real statement with an opening/closing balance check, if PDF import stays in scope.

## Current Recommendation

Build option P1 from architecture/02-revision.md: a local Flask + SQLite app that reads PDF statements with pdfplumber, with reconciliation gates, preview-before-commit and an offline-only design. Approved by the user 2026-09-30.

## Recommendation Confidence

MEDIUM

Reason: Parsing of amounts, dates and balances is verified on all five real layouts (research/05). Description parsing, category rules, and the no-outbound-connection check are not yet tested.

## Blocking Unknowns

None.

## Next Stage

User trial in a browser. Then: optional styling pass; final tester pass if code changes; Python 3.10+ upgrade of click, pdfminer.six and pillow (deferred by user choice).

## Next Action

2026-10-01: user still saw "Forbidden" on every page after the 0.1.1 fix. Cause: the old (pre-fix) app copy was still running on port 5055; a relaunch could not bind the port but still printed a new-key link, which the old copy rejected. Fixed in 0.1.2 (run.py binds first; refuses and prints no link if the port is taken); old copy stopped; 194 tests pass; real Chrome flow re-verified on 0.1.2. User must start the app fresh (one Terminal window only). Not yet verified in Safari. Open: user's own import and categorising, optional styling, Python 3.10+ upgrade.
