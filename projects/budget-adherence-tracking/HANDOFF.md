# Handoff: Budget adherence tracker (option P1)

Approved by the user 2026-09-30. Sources: PROJECT_STATE.md, architecture/02-revision.md, research/03, 04, 05. Implementation stages (BUILD, TEST, RELEASE) still need the user's go-ahead to start.

## Outcome
Each month the user can see, without manual tallying, whether they stayed within budget overall and in each of their 9-10 categories, and how each category trends month to month.

## Stack (fixed; do not change without asking)
- Python (python.org installer), Flask, SQLite, pdfplumber (0.11.8 worked on Python 3.9.6 in the spike; pin exact versions and hashes), Chart.js bundled locally.
- Runs on localhost only. macOS.
- Code in `projects/budget-adherence-tracking/app/`. User data in a folder that iCloud does not sync, outside `~/Documents` and `~/Desktop`, chosen by the user.

## MUST requirements
1. Nothing leaves the computer. The app makes no outbound network connection. Verified by test (see Acceptance).
2. Import text PDF statements. No CSV support in the first build.
3. Support these layouts (details in research/04 and research/05):
   - ING Orange Everyday statement (columns Date, Details, Money out, Money in, Balance)
   - ING short report (Date, Description, Deposit, Withdrawal, Balance)
   - NAB credit card statement (two dates, description, amount with CR/DR, no per-row balance)
   - Offset account and home loan transaction listings (Debits, Credits, Balance with CR/DR; rows "Mon dd" with year from the month heading)
4. Each import passes two hard gates or is rejected entirely (no partial import):
   - Statement gate: opening + in - out = closing to the cent (NAB: printed Payments and Purchases totals).
   - Row gate: where each row prints a balance, previous balance + signed amount = this balance.
   Error messages name the row number and field type only, never amounts or descriptions.
5. Preview before commit: date range, counts, totals in and out, gate results, inferred years, detected transfers, duplicates, Uncategorised count. Nothing is written until the user approves.
6. Assign each transaction to one of the user's 10 categories (see `budget-categories.md`; categories 9 Buffer and 10 Spare have no monthly amount). The app's category config is built from the user's source PDF at build time.
7. Compare actual spending per category against the budget, and overall, per month, showing within/over. Transactions from all imported accounts are combined and assigned to a month by transaction date. Categories are labels assigned by rules and manual correction (not tied to one account each; user confirmed 2026-09-30).
7a. "Where am I bleeding" view: categories ranked by overspend (amount and percent over budget), the transactions or merchants driving each overspend, and the month-to-date pace against the month's budget. Source of the budget figures: `budget-categories.md`.
7b. Sinking funds (user decision 2026-09-30): judge each category's month by actual spending against its Regular amount. Track each Sinking pool separately as a running balance (monthly amount set aside, minus irregular bills paid). Which transactions draw on a sinking pool versus regular spending is set by rules and manual correction; the item-level split lives in the user's source PDF. Do not treat a large irregular bill as an overspend on the Regular amount if it belongs to a sinking pool.
8. Monthly stats and per-category trend across months.
9. Clear, easy-to-read pages (plain layout is acceptable in slice 6; polished look is the optional styling pass). All amounts in AUD, dates dd/mm/yyyy.
10. Stay within AUD $0 for tools and libraries.

## SHOULD requirements
- Remember payee-to-category rules; manual category correction.
- Duplicate detection: file hash, then per-account matching on date, cents and description. Balance is never part of the identity key.
- Per-account role (spending, credit card, loan, offset). Exclude transfers between own accounts, card repayments and loan flows from category spending. Coverage panel: which accounts and date ranges each month has.
- Backups: automatic copy before every import, plus manual copy to an external drive. No cloud backup (user decision).

## Parsing rules (VERIFIED in research/05)
- ING statement: money out is printed negative. Rows oldest-first. Skip continuation lines with no date.
- Offset and loan listings: assign amounts to columns by the header's right edge (about 12 points tolerance). CR/DR is a separate token after the balance; a DR balance is a negative signed balance. Month-year heading lines (four-digit year, no amount) supply the year.
- NAB: sum CR and DR rows and compare with the printed summary. Remove whitespace inside amounts.
- Column positions come from each page's header row, not hard-coded.
- Use integer cents everywhere. Parse dates explicitly (no locale-dependent parsing).
- Unknown layout: reject and say so; never guess.

## Security and offline design
- Bind explicitly to 127.0.0.1, debug off, TRUSTED_HOSTS, per-launch token, CSRF and Origin checks.
- Content-Security-Policy `default-src 'self'`; connect-src 'self'. No CDN, web fonts, analytics or telemetry. Bundle all assets.
- No transaction data in URLs, page titles or logs.
- Do not use PyMuPDF (AGPL). No OCR or cloud PDF services.

## Data boundary for the builder
- The user approved sharing whole real statements with Claude for building and debugging this project only (2026-09-30). Anything read is sent to Claude's service. Read only what is needed. Prefer counts and pass/fail output over printing values.
- Do not copy real statements into the workspace or the repo. Test fixtures use fake data.
- Do not record account numbers, names or transactions in project files.

## Build slices (each leaves the app runnable)
1. Skeleton: Flask on localhost, SQLite schema, config file for categories and budgets, offline asset bundle.
2. ING statement parser + both gates + preview (the layout with the most files).
3. Remaining parsers: ING short, NAB card, offset, home loan.
4. Commit, duplicates, backups, account roles and transfers.
5. Categorisation rules and manual correction.
6. Monthly view, budget vs actual, trends, overspend ("where am I bleeding") view, coverage panel. Function first, with a clean, plain, readable layout. (User decision 2026-10-01: colour, look and feel are a separate, optional styling pass afterwards.)
7. Optional styling pass: colours, fonts, layout polish, bundled chart styling. Changes CSS and templates only; no logic changes.
Stop for the user after slices 2 and 6, and before the optional styling pass.

## Acceptance (tester)
- Every MUST above, with fake-data fixtures for each layout.
- On the user's real files, run locally by the user or the tester: all files that passed the spike (research/05) still pass both gates.
- Offline test: run a full import with Wi-Fi off, and again while a network monitor watches for outbound connections from the app process. Zero connections. The monitor tool choice is UNKNOWN (LuLu unverified; macOS built-in tools may suffice). Verify before relying on it.
- Negative tests: corrupted PDF, altered amount (gate must fail), unknown layout, duplicate file, overlapping periods.
- Dependency audit; no secrets or personal data in the repo.

## Release (local)
Local release means run instructions, a launcher, pinned dependencies, and a rollback (restore the pre-import backup). No external publishing.

## Open items and risks
| Item | Status |
|---|---|
| Category list and amounts | Received 2026-09-30 in `budget-categories.md` (category level). Sinking-fund handling decided 2026-09-30 (requirement 7b) |
| Description parsing: multi-line, refunds, foreign currency | UNKNOWN; test during slices 2-3 |
| pdfplumber outbound behaviour | UNKNOWN; covered by the offline test |
| Offset and loan reports are Macquarie | UNVERIFIED; does not affect parsing |
| iCloud Desktop & Documents setting; statements folder is under Documents | UNKNOWN; recommend moving data outside |
| $0: Claude usage covered by an existing subscription | ASSUMPTION |
| NAB tested on one 11-row statement | Widen coverage when more files exist |

## What would change the plan
- PDF parsing failing on real descriptions or new statements in ways the gates cannot fix: reconsider P2 or a CSV route.
- The user wanting phone access, bank integration or hosting: out of scope for this handoff.
