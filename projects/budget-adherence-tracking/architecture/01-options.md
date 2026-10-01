# Architecture Options: budget-adherence-tracking

Date: 2026-09-24
Author: architect agent
Inputs: PROJECT_STATE.md, research/01-landscape.md, research/02-local-build-options.md, DECISION_FRAMEWORK.md, plus three extra checks made during this pass (marked **[arch-check]** below).
Status: Hypothesis for critique. This document does not choose an option.

**Extra checks made during this pass (not in the research files):**
- **[arch-check 1]** Actual Budget provides an official Node.js client, `@actual-app/api`. Its docs say: "If no `serverURL` is provided, no network connections will be made, and you'll only be able to access budget files already downloaded locally." It exposes `getBudgetMonth`, `getTransactions`, `getCategories`, `getAccounts`, and `importTransactions`, which "go[es] through the same process as importing a file… with reconciliation to avoid duplicates". It has a `dataDir` setting for local budget files. **VERIFIED (vendor docs)**. Sources: https://actualbudget.org/docs/api/ and https://actualbudget.org/docs/api/reference
  - Whether this API can open the Actual *desktop app's* budget file directly: **UNCERTAIN**.
  - Whether `getBudgetMonth` returns the amount *spent* per category as well as the amount budgeted: **UNCERTAIN**. The docs text only says "budgeted amounts per category".
- **[arch-check 2]** PDF.js is Apache-2.0. **VERIFIED** from the GitHub repo footer (https://github.com/mozilla/pdf.js). Whether it can extract text with positions, which table reconstruction needs, was not confirmed this pass: **LIKELY**.

---

## Objective

Each month the user should be able to see quickly, without adding things up by hand:
- whether they stayed within budget overall and in each of their 9–10 categories
- how each category is trending from month to month.

The tool must be the user's own custom app. It must run only on their Mac, cost AUD $0, and statement data must never leave the computer.

## Requirements understood

**Must have (user-stated)**
1. Import statements the user downloads manually. Several Australian banks are involved, and CSV and/or PDF are available.
2. Assign each transaction to one of 9–10 categories the user defines. The categories, what belongs in each, and the amounts are already decided.
3. Show budget vs actual per category and overall for each month, with a clear within/over indication.
4. Show monthly stats and per-category trends across months.
5. A clean, modern, easy-to-read presentation.
6. The user's own custom-built app.

**Should have (assumed at intake; the architecture treats some as effectively required)**
- Remember merchant→category so the same payee is not recategorised every month.
- Manual override of a transaction's category.
- History kept between months, needed for trends.
- Transfers, refunds and income handled so they do not distort spending.
  - **Architect's note:** this is effectively a must-have if the user imports both a transaction account and a credit card. A card repayment from the bank account and the card purchases themselves would otherwise count the same spending twice. The logic behind this is sound (LIKELY), but it depends on which accounts the user actually has (UNKNOWN).
- Duplicate detection. research/01 found export limits make overlapping imports likely (CORROBORATED for CBA and Macquarie). The architecture treats it as required.

**Nice to have:** a warning when a category is close to its limit.

## Constraints

Hard constraints (user-stated):
- **AUD $0**, both one-off and recurring.
- **Local only:** localhost on the user's Mac. The Mac is an ASSUMPTION taken from the working environment.
- **Statement data does not leave the computer** without explicit approval. This covers AI services, cloud sync and CDNs.
- **Manual import:** no bank integration.
- **Australia / AUD:** DD/MM/YYYY dates and a single currency (single currency is an ASSUMPTION).

Derived constraints (architect inference, labelled):
- The maintainer is a non-specialist (stated in the brief). Setup and upkeep must be minimal, so every extra toolchain counts against an option.
- Development will probably be AI-assisted (ASSUMPTION). Real statements therefore must not be pasted into AI tools during development. Parsers should be built from column headers only and synthetic fixture files, as PROJECT_STATE already notes.

## Architecture options

| ID | Option | Role |
|---|---|---|
| **A** | Localhost Python web app: Flask on 127.0.0.1, SQLite file, server-rendered pages, bundled Chart.js | Primary custom candidate |
| **B** | Single-file browser app: HTML/JS, browser storage and/or a file on disk via the File System Access API | Zero-install custom candidate |
| **C** | Desktop-packaged app: Electron, Tauri, or a native-window wrapper around A | Custom candidate, or a later wrapper |
| **D** | Build on Actual Budget's MIT code: D1 fork it; D2 use Actual as the engine with the user's own dashboard | Reuse/hybrid candidate |
| **E** | Actual Budget desktop app as-is | Existing-product fallback. Violates "my own app"; kept as a benchmark only |
| **F** | Spreadsheet in Numbers or LibreOffice | Simplest-process baseline. Violates "my own app"; kept as a benchmark only |

Considered and not developed:
- **hledger + custom UI.** hledger's budget reports are VERIFIED, but a plain-text journal and command-line workflow is a poor fit for a non-specialist maintainer, and the user would still need a custom UI.
- **Firefly III / Sure.** Both need Docker plus a database (VERIFIED/LIKELY), which is high burden.
- **Node/Express localhost.** This is a legitimate variant of A. It is not preferred because:
  - bare `listen()` binds to all interfaces by default (VERIFIED);
  - SQLite in Node needs either a native module or a built-in module whose availability in the user's Node version is UNKNOWN.

---

## Shared design elements (apply to options A, B, C and D1)

These are described once to avoid repetition. Each option section notes where it differs.

### Data model (logical)

- **accounts**: bank, account label, type (transaction / credit card / savings), import profile.
- **categories**: 9–10 spending categories, each with a monthly budget amount.
  - Plus system categories: Income, Transfer (excluded from spending), Uncategorised, and optionally Ignore.
  - Budget amounts are stored with an "effective from month" date. Changing a budget later then does not rewrite history. This matters for trend accuracy.
- **import_batches**:
  - file name and file hash (SHA-256)
  - bank profile used
  - date range, rows parsed / committed / skipped as duplicate
  - imported-at timestamp
  - status: committed or undone.
- **transactions**:
  - account, date, amount in integer cents (signed: outflow negative)
  - raw description and normalised payee
  - balance, if the bank provides it
  - category, how the category was set (rule id / manual / bank-hint), batch id
  - duplicate fingerprint, notes.
- **rules**: match type (exact payee / contains / regex), pattern, category, priority, origin (learned or manual), hit count, last used.

### CSV import pipeline

1. **Choose the profile.** The user picks the account, which fixes the bank profile. Automatic detection is a convenience only. CBA and ANZ are reportedly headerless (CORROBORATED for CBA; CONFLICTING for ANZ), so header-based detection cannot be relied on, and shape detection alone is fragile (LIKELY).
2. **Bank profiles are declarative data, not code.** Each profile records:
   - whether there is a header row
   - the column positions or names for date, description, amount (or debit and credit), and balance
   - the explicit date format, e.g. `DD/MM/YYYY` or Macquarie's "d M Y"
   - the sign convention: a signed amount, or separate debit/credit columns
   - the encoding and delimiter.

   Profiles are created only from the user's real headers. Community layouts (the Firefly configs, massyn/bankcsv) are starting hints, not facts.
3. **Generic mapping fallback.** For an unknown bank or a changed format, a one-time mapping screen lets the user pick the columns, date format and sign convention. The result is saved as a new profile. This is how the app survives banks changing formats.
4. **Strict date parsing.**
   - Never guess the date format; never use a US month/day parser.
   - Reject impossible dates.
   - Show the first and last dates in the preview so a DD/MM vs MM/DD swap is visible to the user.
5. **Normalisation:**
   - amount → signed integer cents
   - strip extra whitespace from descriptions
   - derive a normalised payee by removing card numbers, dates and location suffixes. The exact rules are UNKNOWN until real descriptions are seen.
6. **Duplicate detection**, in layers:
   - **(a) File level:** the same file hash was already imported → warn and block.
   - **(b) Transaction level:** fingerprint = account + date + amount + normalised description, plus an occurrence index within the file for that key. The index ensures two genuine identical same-day purchases (two coffees) are both kept.
   - **(c) Overlap matching:** for dates inside the range of already-imported transactions for that account, match as a multiset. N identical rows in the new file against M existing rows means only max(0, N−M) are new.
   - **(d) Balance column:** where the bank provides a running balance, include it in the fingerprint. It makes identical-looking rows distinguishable.
   - **(e) Near-matches are flagged for review, never dropped silently.** Examples: same amount and account, date within ±3 days, similar description. This covers pending vs posted date shifts (ASSUMPTION that Australian banks shift dates this way).
7. **Preview and approval gate.** The user sees:
   - rows parsed, new rows, duplicates skipped, near-duplicates to review
   - the date range and totals in and out.

   Nothing is written until the user confirms.
8. **Atomic commit.** The whole batch commits in one database transaction, or nothing does. Every batch can be undone afterwards.

### Categorisation (rules first; no AI in the minimum version)

- **Order of evaluation:**
  1. manual override
  2. user rules, by priority
  3. learned exact-payee rules
  4. bank category hint, used only as a suggestion. Macquarie's category column is LIKELY; Westpac's is UNCERTAIN.
  5. Uncategorised.
- **Learning:** when the user categorises a transaction, the app offers "Always put <payee> in <category>?". This follows Actual's VERIFIED pattern of learning rules from user behaviour. Offering rather than silently creating the rule is a small human gate against over-broad rules.
- **Visibility:** every transaction shows *why* it has its category (which rule, or manual). Rules can be edited and re-applied to past months, with a preview first.
- **Month-end check:** the monthly view shows the Uncategorised count prominently. A month is not "closed" until it reaches zero.
- **Local ML / LLM: deferred.**
  - Accuracy of zero-shot LLMs on terse descriptions is UNCERTAIN, from one study: 60.4% for GPT-4o.
  - Ollama's network behaviour, including `-cloud` models, is UNCERTAIN.
  - The user's hardware is UNKNOWN.
  - Rules-first also meets the "reduces over time" assumption.
  - A later local TF-IDF classifier (the ing-categorizer pattern, VERIFIED as a project description) could be added. It would only make suggestions, and only after enough labelled data exists.

### Budget calculation

- **Per category per calendar month:**
  - actual = −(sum of outflows) − (sum of refunds, i.e. inflows categorised to that category)
  - status = actual / budget.
- **Overall:** the sum across spending categories, compared with the total budget. Income is shown separately. Transfers are excluded.
- **Status bands:** under (e.g. <90%), near (90–100%), over (>100%). The thresholds are configurable (nice-to-have).
- **Accessibility:** status is also shown as text or an icon, not colour alone. This is a design recommendation.
- **Pay-cycle periods:** calendar months are an ASSUMPTION. If the user budgets by pay cycle, the "period" becomes a configurable start date. The data model should keep dates raw and compute periods on the fly, so this remains reversible.

### UI and charting

- **Month view:**
  - a headline card ("Within budget: 8 of 10 categories; overall $X under")
  - one progress bar per category showing budgeted, spent and remaining
  - an Uncategorised badge.
- **Trends view:**
  - per category, small multiples of actual vs budget line or bar over the last 6–12 months
  - an overall stacked or total chart.
- **Transactions view:** filter, recategorise, and see the rule that applied.
- **Charting library:**
  - Chart.js (MIT, VERIFIED) or uPlot (MIT, VERIFIED), bundled as local files.
  - ECharts (Apache-2.0, CORROBORATED) is an alternative.
  - Recharts only if React is adopted (VERIFIED as React-only), which is not recommended for a non-specialist.
- **No external assets:** system font stack, no Google Fonts, no CDN.

### Network posture (the data-locality constraint made verifiable)

- Bind only to `127.0.0.1`. Flask's default is VERIFIED to be 127.0.0.1. The app should still set the address explicitly rather than rely on the default.
- Every asset is served locally.
- A Content-Security-Policy header of `default-src 'self'` makes the browser refuse external loads even if a dependency tries one. That this suffices is LIKELY; needs validation.
- **Localhost is not automatically safe from the browser itself.** Any website open in the same browser can send requests to `127.0.0.1:<port>`. DNS-rebinding attacks can go further and read responses. Mitigations:
  - reject requests whose `Host` header is not `127.0.0.1:<port>` or `localhost:<port>`
  - require a per-session token or CSRF protection on state-changing requests
  - use a non-default port.

  How exposed a Flask app is to this in practice is UNCERTAIN (research requirement R7).
- Verification: run the app with an outbound firewall monitor (LuLu, named in research/01 as free; UNVERIFIED) and confirm there are zero outbound connections.

### Storage location and backup

- **iCloud risk.** If the Mac's iCloud "Desktop & Documents" sync is on, a database under `~/Documents` (where this research workspace lives) would be uploaded to iCloud. That would violate the data-locality constraint.
  - Recommendation: keep data in a folder iCloud does not sync, e.g. `~/BudgetData/`.
  - The exact iCloud sync behaviour is UNVERIFIED (research requirement R1).
- **Backups:**
  - Time Machine to a local disk is compatible with the constraint (LIKELY).
  - The app also makes a dated copy of the database before every import commit, keeping the last N copies. This uses SQLite's online backup API rather than a raw file copy, to avoid WAL inconsistency. The API's existence is LIKELY; exact Python support is to be confirmed (R8).
- **Raw statement files:**
  - Default: do not keep them after import, just the file hash and batch metadata.
  - Optional archive folder next to the database.
  - PDFs contain name, address and account numbers (ASSUMPTION, highly likely).
- **At-rest encryption:**
  - Rely on Mac hardware encryption and FileVault. Hardware encryption is VERIFIED on Apple silicon/T2 Macs. FileVault being on is UNKNOWN; the user should check it.
  - SQLCipher is not recommended: it needs a source build (VERIFIED as the official route) and its easy $0 install routes are UNCERTAIN. The cost is too high for a non-specialist.

### Automation model (the import-and-review workflow; the same for every custom option)

| Element | Design |
|---|---|
| TRIGGER | The user selects or drags a downloaded statement file into the app. Nothing runs on a schedule; no folder watching in the minimum version. |
| INPUT | A CSV file (PDF in a later phase); the chosen account/profile; the existing transactions and rules. |
| DECISION | Profile parsing rules; duplicate layers (a)–(e); categorisation rule order; transfer detection hints (e.g. description contains the user's own account names or "payment thank you"; pattern list UNKNOWN until real data is seen). |
| ACTION | Stage parsed rows → show preview → on approval, commit the batch → apply rules → update the monthly figures (computed on read, not stored). |
| STATE | SQLite: transactions, batches, rules, categories and budgets. Pre-import backups. |
| VERIFICATION | Rows parsed = new + duplicates + rejected. Totals in and out shown before commit. Where there is a balance column: first balance + sum of amounts = last balance. After commit, the batch summary is recorded. For PDF (later): opening balance + transactions = closing balance is mandatory. |
| FAILURE | Any row that cannot be parsed (bad date, missing amount, wrong column count) → reject the whole file with a row-numbered error. No partial import. |
| RECOVERY | Undo a batch (deletes its rows and restores the categorisations it changed). Restore from a pre-import backup. Fix the profile via the mapping screen and re-import. |
| HUMAN GATE | Commit of an import; creation of a learned rule; applying an edited rule to past months; resolving near-duplicates; deleting data. |
| OBSERVABILITY | An import history screen, a "why this category" label on each transaction, and rule hit counts. A local app log that records counts and errors but **not** descriptions or amounts, to limit sensitive data in logs. |

---

## How each option works

### Option A: Localhost Python web app (Flask + SQLite + server-rendered UI)

**Components**
- Python 3 from the python.org installer (VERIFIED as the recommended route; free).
- A project folder with a virtual environment. Pinned dependencies: Flask, plus pdfplumber in the PDF phase.
- Flask on 127.0.0.1 with an explicit port (default binding VERIFIED).
- SQLite through the standard-library `sqlite3` (VERIFIED as standard but officially "optional"; inclusion in the python.org installer is LIKELY, R8).
- Jinja HTML templates with a small amount of plain JavaScript (drag-drop upload, chart rendering). There is no front-end build step (no Node, Vite or React).
- Chart.js or uPlot copied into `static/`.
- A double-clickable `Start Budget.command` script. It activates the virtual environment, starts the server bound to 127.0.0.1, opens the default browser, and prevents a second instance from starting. Whether macOS runs `.command` files from Finder without friction is LIKELY (R9).

**Data flow**
1. The user downloads a CSV in the bank's desktop site to `~/Downloads`.
2. In the browser at `http://127.0.0.1:<port>`, the user uploads it.
3. Flask parses it in memory, stages the rows and renders the preview.
4. The user approves → batch commit to `~/BudgetData/budget.sqlite` → redirect to the month view.
5. Optionally, the app offers to delete the source file from Downloads. This is a human gate, and deleting user files is a design decision for the user.

**Network exposure:** one TCP listener on loopback only. No outbound calls by design. CSP and Host-header checks as in the shared design.

**PDF:** Phase 3, using pdfplumber (MIT, VERIFIED, text-based PDFs only) with per-bank templates and a mandatory balance reconciliation check. Camelot is an alternative (MIT; latest release date UNKNOWN). tabula-py is excluded because it needs Java.

**UI:** server-rendered pages and small JS charts are enough for a clean look. A modern appearance depends on design effort, not on the framework (judgement). A small classless or utility CSS file, bundled locally, can help.

**Setup burden:**
- One graphical Python installer.
- One command to create the virtual environment and install pinned packages. This is simplified by a setup script.
- A launcher to double-click.

Estimate: medium-low (LIKELY).

**Maintenance:**
- Occasional `pip` upgrade of one or two pinned packages. Security exposure is low because the app is loopback-only (LIKELY).
- Python version upgrades are optional.
- Bank format changes are handled through the mapping screen, not code edits.

**Trade-offs (DECISION_FRAMEWORK)**
- **Gain:**
  - the simplest real-file storage (no browser eviction; VERIFIED risk avoided)
  - one language
  - no build toolchain
  - pdfplumber available for later
  - works in any browser, Safari included
  - easy to inspect: SQLite can be opened with free tools.
- **Lose:**
  - the app does not feel native: it runs in a browser tab and needs a start step
  - the user must start the server (or a login item starts it; R9).
- **Depend on:** Python (PSF), Flask (Pallets), Chart.js/uPlot. All are free, mature and replaceable. The SQLite file format is highly portable.
- **Failure:**
  - a misconfigured bind address (if someone later changes it to 0.0.0.0)
  - a browser-borne localhost attack if Host and CSRF checks are omitted
  - a Python upgrade breaking the virtual environment (recreate with the setup script)
  - the database in an iCloud-synced folder.
- **Regret:** if the user later wants phone access or a native app feel. Both are reversible: C3 can wrap A in a native window later, and the SQLite data carries over.
- **Change direction if:**
  - the user cannot or will not install Python → B
  - the user wants a dock app → C3 wrapper
  - the user decides Actual's engine is acceptable → D2.

### Option B: Single-file browser app (no server)

**Components**
- One `budget.html` file plus a folder with the JS/CSS/chart library (or everything inlined).
- Opened by double-clicking (`file://`) or served by any static server bound to 127.0.0.1. Python's `http.server` binds to *all interfaces* by default (VERIFIED), so `--bind 127.0.0.1` would be mandatory.
- CSV parsing in JavaScript: a hand-written parser, or a library such as Papa Parse (licence and offline bundling UNVERIFIED, R10).
- **Storage, variant B1 (Chrome/Edge only):** data kept in a user-chosen file (JSON, or a SQLite image via SQLite-WASM/sql.js, both UNVERIFIED) through the File System Access API. The API is VERIFIED in Chrome/Edge ≥105 and not supported in Safari or Firefox.
  - Whether the API works from a `file://` page is UNKNOWN (R11).
  - Browsers likely require re-granting permission each session (LIKELY, R11).
- **Storage, variant B2 (any browser):** IndexedDB with `navigator.storage.persist()` (VERIFIED to exist) plus mandatory export-to-file after every import.
  - Safari's 7-day eviction under tracking prevention is VERIFIED.
  - How eviction and `persist()` behave for `file://` origins is UNKNOWN (R11).

**Data flow:** file picker → JS parses in-page → preview → write to the IndexedDB or data file → render charts. No network is involved at all when opened from `file://` with bundled assets.

**PDF:** in principle PDF.js (Apache-2.0, [arch-check 2]) could extract text client-side. Positional text extraction is LIKELY, and table reconstruction would have to be built by hand. There is no JS equivalent of pdfplumber's table tools in the evidence. **Deferred; weaker than A for PDF.**

**Setup burden:** lowest; nothing to install.
**Maintenance:** low in code terms, but high operational discipline for backups (B2) or a dependence on a Chromium browser (B1).

**Trade-offs**
- **Gain:** zero install and no listener, so the smallest network attack surface. Portable.
- **Lose:**
  - reliable persistence (B2: evictable, VERIFIED)
  - browser choice (B1: Chrome/Edge only, VERIFIED)
  - a mature PDF path
  - SQL for reports (unless SQLite-WASM, which is unverified).
- **Depend on:** browser storage policy (outside the user's control and liable to change); File System Access API support (marked "Experimental" on MDN, VERIFIED).
- **Failure:** silent total data loss (B2). Lost file permission, or the user saving over the data file (B1). Corrupted export files.
- **Regret:** high if months of categorised history are evicted. That is exactly the data the trend requirement needs.
- **Change direction if:** Safari/`file://` behaviour turns out to be persistent and reliable (R11), or the user commits to Chrome and a disciplined export routine.

### Option C: Desktop-packaged app

Three sub-variants that differ materially:

- **C1: Electron** (MIT; prebuilt for macOS 13 Ventura and later, VERIFIED).
  - Node main process, SQLite through a Node module (native-module rebuild burden LIKELY, R12), HTML/JS UI, charts bundled.
  - Can avoid any TCP listener by using IPC, which is a genuine security advantage over A (LIKELY).
  - Requires Node (not preinstalled, LIKELY) and the npm ecosystem. App bundles are large.
  - Electron has frequent security releases (LIKELY), creating update pressure.
- **C2: Tauri v2.**
  - Requires Xcode, Rust and Node (VERIFIED); the Xcode download is several GB (LIKELY).
  - Small bundle; uses the system WebView.
  - The heaviest toolchain for a non-specialist.
- **C3: Native-window wrapper around A**, e.g. pywebview showing the Flask UI in a WKWebView window.
  - Its capabilities, licence and packaging are all UNVERIFIED (R13).
  - Keeps A's code and SQLite file and adds a dock-icon feel. Could be added later as a phase.

**Gatekeeper:** an app built on the user's own Mac is not quarantined, so the unidentified-developer block does not apply (CORROBORATED, not VERIFIED). Ad-hoc signing on Apple silicon happening automatically is LIKELY (R14). No paid Apple Developer Program is needed (VERIFIED: notarisation needs it only for distribution).

**Trade-offs**
- **Gain:** a native feel with no browser tab; C1 can run with no network listener.
- **Lose:**
  - substantially more toolchain (Node/npm; or Xcode and Rust)
  - larger bundles
  - rebuilds when dependencies update
  - Electron's macOS 13 minimum (the user's macOS version is UNKNOWN).
- **Depend on:** the Electron or Tauri release cadence, and native-module compatibility.
- **Failure:** a broken build after an OS or toolchain update, which a non-specialist cannot easily diagnose (LIKELY).
- **Regret:** spending effort on packaging rather than on the categorisation and reporting that deliver the outcome.
- **Change direction if:** the user strongly wants a dock app and accepts the toolchain. Even then, C3 on top of A is the least disruptive path, pending R13.

### Option D: Build on Actual Budget's MIT code

- **D1: Fork Actual and customise its UI and reports.**
  - Gains a mature CSV import (field mapping, debit/credit split, duplicate detection: VERIFIED), rules learned from behaviour (VERIFIED), budget pages, and a desktop build.
  - Loses simplicity. Actual is a large, actively developed codebase with monthly releases (VERIFIED). Its size and language (TypeScript monorepo) are LIKELY, not checked (R15).
  - Keeping a fork current is a real, ongoing software-engineering task. Letting it fall behind freezes it.
  - For a non-specialist maintainer this is the highest-burden custom option (LIKELY).
- **D2: Actual as the engine, the user's own app as the dashboard (hybrid).**
  - Actual (desktop app, or its local data through `@actual-app/api` with no `serverURL`, [arch-check 1]) does import, duplicate reconciliation (`importTransactions`, VERIFIED in vendor docs) and rules.
  - The user's own small local app reads months, categories and transactions through the API and renders the budget-vs-actual and trend dashboard that Actual lacks as a standard report. Actual's Budget Analysis report is experimental only (VERIFIED).
  - It could also run the user's own per-bank CSV pre-processor, feeding `importTransactions`.
  - Unverified dependencies:
    - whether the API can open the desktop app's budget file directly or needs its own copy (R16)
    - whether per-category *spent* figures are returned (R16)
    - Actual's actual network behaviour (UNKNOWN in research/01; R17).
  - D2 needs Node (for `@actual-app/api`) as well as the Actual app.
  - **Does D2 satisfy "my own app"?** Only partly: the dashboard is the user's own, the engine is not. **User question Q3.**

**Trade-offs (D2)**
- **Gain:** the hardest parts (import mapping, duplicate reconciliation, rule learning) are mature and maintained by others. The user builds only the part they care about most: the look and the trends.
- **Lose:** full ownership. Two systems to keep compatible. PDF is still not covered (Actual has no PDF import, VERIFIED).
- **Depend on:** Actual's API stability across its monthly releases (UNKNOWN), Node, and Actual's privacy posture (a vendor statement, not audited).
- **Failure:** an API or schema change breaking the dashboard after an Actual update. The Actual desktop app and the API disagreeing about file versions.
- **Regret:** if the user's real motive for "my own app" is ownership or learning, D2 undercuts it.
- **Change direction if:** R16 shows the API cannot read the desktop app's data cleanly, or the user rejects partial ownership.

### Option E: Actual Budget as-is (fallback benchmark)

- Download the macOS desktop build (VERIFIED to exist; signing and notarisation status not checked).
- Use tracking-budget mode (green/red indicators, VERIFIED) and Custom Reports by category per month (VERIFIED).
- Gaps:
  - no PDF import
  - no standard multi-month budget-vs-actual trend per category
  - network behaviour not audited.
- It is the fastest path to the outcome and the reference point any custom app must beat on look and trends. It violates the "my own app" requirement, so it is kept only as a benchmark and fallback.

### Option F: Spreadsheet baseline (Numbers or LibreOffice)

- One sheet per bank for pasted CSVs.
- A normalising sheet with formulas that convert each layout.
- A payee→category lookup table.
- SUMIFS by category and month against a budget table, conditional formatting, charts.
- Numbers is free (CORROBORATED); LibreOffice is MPL-2.0 and needs macOS 11+ (VERIFIED). Excel for Mac cannot save without a licence (CORROBORATED), so it fails the $0 constraint.
- Weak on multi-bank normalisation, duplicate detection and rule maintenance. The look is limited (LIKELY; not researched against sources).
- Useful as a two-hour stopgap while the app is built, and as a cross-check of the app's totals during validation.
- Violates "my own app" as the end state.

---

## Major components (summary)

| Component | A | B | C1 / C2 / C3 | D2 |
|---|---|---|---|---|
| Runtime | Python 3 | Browser only | Electron+Node / Tauri+Rust+Xcode / Python+wrapper | Actual app + Node |
| Storage | SQLite file | IndexedDB or FS-API file | SQLite | Actual's local store |
| Import engine | Own profiles + mapping | Own (JS) | Own | Actual (+ optional own pre-processor) |
| Rules | Own | Own | Own | Actual |
| Dashboard | Own (Jinja + Chart.js) | Own | Own | Own |
| PDF path (later) | pdfplumber | PDF.js (hand-built tables) | Via Python (C3) or JS | Own pre-processor → API |
| Network listener | 127.0.0.1 only | None (`file://`) | None (C1 IPC) / WebView / 127.0.0.1 (C3) | Actual's local server (desktop) + own dashboard |

## Data flows

All custom options follow the same flow:

**bank website → manual download (desktop browser; CSV not available in the CBA/Westpac mobile apps, UNCERTAIN) → local file → app parser → preview (human gate) → local store → computed monthly aggregates → UI.**

- No flow crosses the machine boundary.
- The only places data could leave are:
  - (1) the storage folder being cloud-synced
  - (2) a CDN or font load (prevented by bundling and CSP)
  - (3) a network-bound listener (prevented by binding to 127.0.0.1)
  - (4) a future AI categoriser (excluded; if added later, local-only with explicit approval)
  - (5) the development process: real statements pasted into an AI coding assistant, prevented by a process rule.

## Integration points

- **Bank files:** CSV now; OFX/QIF optional later. OFX may carry transaction IDs that make duplicate detection stronger (LIKELY), and it is VERIFIED available from Westpac and CBA (CBA from research/01's table). PDF deferred.
- **No bank APIs, no cloud services.**
- **D2 only:** the `@actual-app/api` local data access.
- **Export:** CSV export of categorised transactions and monthly summaries, for portability and for cross-checking in a spreadsheet (option F as a validation tool).

## Security boundaries

1. **The machine boundary.** Enforced by loopback binding, no external assets, CSP, and a storage folder outside cloud sync. Checked with an outbound-connection monitor.
2. **The browser-to-localhost boundary (A, C3, D2).** Enforced by Host-header validation, per-session tokens or CSRF protection, and a non-default port (R7).
3. **At rest.** Mac hardware encryption plus FileVault (the user should confirm FileVault is on). App-level encryption is excluded as disproportionate.
4. **Logs and backups.** No transaction descriptions in logs. Backups stay in the same non-synced folder or go to a local Time Machine disk.
5. **Development boundary.** Synthetic fixtures only. Real headers are shared only with the user's approval, and without data rows.

## Dependencies

| Dependency | Status | Used by |
|---|---|---|
| Python 3 (python.org installer) | VERIFIED recommended route | A, C3 |
| Flask binds to 127.0.0.1 by default | VERIFIED | A |
| Python `sqlite3` present in the python.org build | LIKELY (R8) | A, C3 |
| Chart.js / uPlot (MIT), bundled locally | VERIFIED licence; local bundling LIKELY | all custom |
| pdfplumber (MIT, text PDFs only) | VERIFIED | A (phase 3) |
| AU bank PDFs are text-based | LIKELY (R4) | PDF phase |
| Real CSV layouts of the user's banks | UNKNOWN (R2) | all |
| File System Access API in Chrome/Edge; not Safari/Firefox | VERIFIED | B1 |
| FS API and IndexedDB persistence from `file://` | UNKNOWN (R11) | B |
| Electron needs macOS 13+ | VERIFIED | C1 |
| Tauri needs Xcode + Rust + Node | VERIFIED | C2 |
| pywebview-style wrapper | UNVERIFIED (R13) | C3 |
| Locally built apps not blocked by Gatekeeper | CORROBORATED | C |
| `@actual-app/api` local mode, import with reconciliation | VERIFIED (vendor docs) | D2 |
| API reads desktop app data; spent per category | UNCERTAIN (R16) | D2 |
| Actual network behaviour | UNKNOWN (R17) | D, E |

## Trade-offs (comparison)

Hard-constraint screen:
- All options meet $0.
- E and F fail "my own app", so they are kept only as benchmarks.
- B2 puts the history needed for trends at material risk. That does not violate a hard constraint, but it weakens must-have 4.

| Criterion (weight) | A | B | C1/C2 | C3 | D1 | D2 |
|---|---|---|---|---|---|---|
| Solves the core problem (high) | Yes | Yes, with persistence risk | Yes | Yes | Yes | Yes, if R16 passes |
| Data safety / locality (high) | Strong, if Host/CSRF checks and a non-synced folder | Strong network-wise; weak persistence | Strong (C1 no listener) | As A | Depends on R17 | Depends on R17 |
| Setup burden for a non-specialist (high) | Low–medium | Lowest | High | Medium (R13) | High | Medium (two systems) |
| Ongoing maintenance (high) | Low | Low code, high backup discipline | Medium–high | Low–medium | High (fork drift) | Medium (API drift) |
| Import robustness (high) | Own; must be built well | Own; must be built well | Own | Own | Mature (Actual) | Mature (Actual) |
| PDF path (medium) | Best (pdfplumber) | Weakest | Via Python or JS | Best | Must be added | Pre-processor |
| Look / "fresh" UI (medium) | Full control | Full control | Full control | Full control | Constrained by Actual's design | Full control of the dashboard |
| Ownership ("my own app") (high, user-stated) | Full | Full | Full | Full | Partial (fork) | Partial |
| Reversibility (medium) | High (SQLite, CSV export) | Medium | Medium | High | Low | Medium |
| Time to a useful result (medium) | Medium | Medium | Slow | Medium+ | Slow | Medium |

## Failure modes (cross-option)

| Failure | Consequence | Mitigation |
|---|---|---|
| DD/MM parsed as MM/DD | Dates up to the 12th silently wrong; totals land in the wrong months | Explicit per-profile format, impossible-date rejection, date range shown in preview |
| Bank changes CSV layout | Import rejected (good) or columns misread (bad) | Strict column-count/header validation per profile; the mapping screen to re-profile |
| Overlapping exports | Double-counted spending | Layered duplicate detection; near-match review |
| Genuine identical transactions dropped as duplicates | Under-counted spending | Occurrence-index fingerprint; balance column where available |
| Credit card repayment counted as spending | Overall spending inflated | Transfer category; repayment-pattern hint; month-view warning if a large outflow matches the card account's inflow |
| Over-broad learned rule (e.g. "PAYPAL") | Many transactions miscategorised | Rule creation gated by the user; "why" label; rule preview before retroactive apply |
| Storage in an iCloud-synced folder | Constraint breached silently | Non-synced path; setup checklist (R1) |
| Listener exposed or localhost attack | Data readable from the LAN or by a malicious web page | 127.0.0.1 binding, Host validation, token (R7) |
| Browser storage eviction (B) | Total history loss | Choose A, or mandatory exports |
| PDF misread (later phase) | Wrong amounts | Mandatory opening + transactions = closing balance check; reject on mismatch |
| Python / venv broken by an upgrade | App won't start | Setup script recreates the venv; the data file is independent of the code |
| Uncategorised transactions ignored | Budget view understates spending | Uncategorised shown as a pseudo-category counted in the overall total, and a prominent badge |

## Operational considerations

- **Monthly routine** (target: under 15 minutes, ASSUMPTION):
  1. download CSVs from each bank on desktop
  2. import each and approve the previews
  3. clear the Uncategorised queue
  4. review the month view.
- **Pre-build setup checklist** for the user:
  - macOS version and chip
  - FileVault on?
  - iCloud Desktop & Documents on?
  - Firewall state
  - which banks and account types
  - calendar month or pay cycle.
- **Backups:** automatic pre-import snapshots. Recommend Time Machine to a local disk. Periodic CSV export as a format-independent copy.
- **Updates:** pin dependency versions; update deliberately, not automatically. No auto-update mechanism means no outbound calls.
- **Handling bank format changes:** the most likely recurring maintenance event (LIKELY). The mapping screen keeps it a user task, not a code task.

## Phased delivery (applies to A; adaptable to others)

- **Phase 0: Preparation.**
  - User answers the open questions and completes the setup checklist.
  - User supplies CSV *header rows only* (no transactions) per bank.
  - Build synthetic fixtures from those headers.
  - A spreadsheet (F) may be used meanwhile.
- **Phase 1: Minimum useful version.**
  - Categories and budgets configuration.
  - CSV import for the user's banks: profiles plus the generic mapping fallback, preview gate, duplicate layers (a)–(c), batch undo.
  - Transfer/Income/Uncategorised system categories.
  - Manual categorisation with learned exact-payee rules.
  - Month view: per-category and overall budget vs actual.
  - Pre-import backups.
  - Loopback binding, CSP, Host check.
  - *Exit criterion:* one full real month, imported from all the user's banks, reconciles with the bank statements' totals.
- **Phase 2: Trends and quality.**
  - The trends view (6–12 months).
  - Rule management (contains/regex, priorities, retroactive apply with preview).
  - Near-duplicate review (d)–(e).
  - Refund handling polish, near-limit warnings, CSV export.
  - Import older history from CSVs where banks allow (NAB 731 days VERIFIED; CBA about 2 years UNCERTAIN).
- **Phase 3: PDF import (conditional).** Only if older history beyond the CSV window is wanted, or a bank's CSV proves unusable.
  - Per-bank pdfplumber template.
  - Mandatory balance reconciliation.
  - Preview gate.
  - Test on one real statement first (on the user's machine; no sharing).
- **Phase 4: Optional.**
  - Native-window wrapper (C3).
  - Local ML *suggestions* for categories.
  - OFX/QIF import for stronger duplicate IDs.

**Why PDF is deferred:**
- The evidence favours CSV as primary (LIKELY): every bank researched offers CSV or spreadsheet export.
- PDF extraction works only on text PDFs (VERIFIED for the libraries), needs a template per bank, and breaks when layouts change (LIKELY).
- No Australian accuracy evidence exists.
- Its main value, history older than the CSV window, is not needed for the first month's budget check.
- NAB's "spreadsheet" may be XLSX rather than CSV (UNCERTAIN). If so, a small XLSX reader (e.g. openpyxl, UNVERIFIED) is a cheaper fix than PDF.

---

## Unknowns requiring research (research requirements)

| ID | Question | Why it matters | Blocks |
|---|---|---|---|
| R1 | Does macOS iCloud "Desktop & Documents" upload arbitrary files such as a SQLite database, and which home-folder locations are never synced? Is the user's setting on? | Silent breach of the data-locality constraint | All options (storage path) |
| R2 | Real header/column layout, sign convention, date format and encoding for each of the user's banks. NAB: CSV or XLSX? ANZ: resolve the conflict | Parser profiles | Phase 1 |
| R3 | Which banks and account types the user has (transaction, credit card, offset/savings) | Profile scope; transfer logic | Phase 1 |
| R4 | Are the user's banks' PDF statements text-based, and do they print opening/closing balances? | PDF feasibility | Phase 3 only |
| R5 | Do the user's banks shift dates between pending and posted, or change descriptions between exports? | Near-duplicate logic | Phase 2 |
| R6 | Balance column availability per bank | Stronger duplicate check; reconciliation | Phase 1 design detail |
| R7 | Practical DNS-rebinding/CSRF exposure of a loopback Flask app, and the standard mitigations (Host allow-list, tokens) | Security of A, C3, D2 | A before build |
| R8 | The python.org macOS installer includes a working `sqlite3` and the SQLite online-backup API | A's storage and backup design | A |
| R9 | Launch ergonomics: `.command` file behaviour in Finder on current macOS; optional login-item start | Non-specialist usability | A |
| R10 | Licence and offline use of a JS CSV parser (e.g. Papa Parse) | B | B only |
| R11 | Browser behaviour for `file://` pages: IndexedDB persistence, `persist()`, Safari 7-day eviction, File System Access API availability and permission persistence in Chrome | B's viability | B only |
| R12 | SQLite in Electron (native module rebuilds, or a built-in `node:sqlite` availability and stability) | C1 burden | C1 only |
| R13 | pywebview (or equivalent): licence, macOS WKWebView support, packaging to .app without paid signing | C3 viability | C3/Phase 4 |
| R14 | Formal Apple documentation on automatic ad-hoc signing of locally built apps on Apple silicon | C packaging | C only |
| R15 | Actual codebase size, language, build steps; feasibility of maintaining a fork | D1 | D1 only |
| R16 | Can `@actual-app/api` open the desktop app's local budget without a server? Does `getBudgetMonth` return spent/actual per category? API stability across releases | D2 viability | D2 only |
| R17 | Actual desktop app's outbound network calls (monitored with LuLu or similar) | D, E posture | D, E |
| R18 | LuLu: free, current, compatible with the user's macOS (proposed verification tool) | Verifying zero outbound traffic | Validation |

## Validation required before implementation

1. Complete the user's setup checklist: macOS version and chip, FileVault, iCloud Desktop & Documents, firewall (R1).
2. Collect header rows only for each bank. Confirm the date format and sign convention by inspecting one real file *on the user's machine*. No data leaves the machine (R2, R3, R6).
3. Spike (throwaway, local): parse one real CSV per bank with the planned profile and check that the totals match the bank's online view for the same period.
4. Confirm the loopback-only listener and zero outbound connections with a monitoring tool (R7, R18).
5. Only if PDF is pursued: run pdfplumber on one real statement with the balance-reconciliation check (R4).
6. Only if D2 is considered: a local spike reading an Actual desktop budget through the API with no `serverURL` (R16, R17).

## Architectural recommendation (provisional; for critique, not final)

**Option A (localhost Python/Flask + SQLite + server-rendered UI + bundled Chart.js/uPlot), delivered in phases with CSV first and PDF deferred, appears strongest.** Reasons:
- It is the only fully owned option that combines real on-disk persistence (avoiding the VERIFIED browser-eviction risk) with any-browser support and a single, VERIFIED-simple runtime install.
- It has a network posture that is verifiable and whose defaults are VERIFIED safe.
- It has the best later path to PDF (pdfplumber).
- Its choices are reversible: SQLite and CSV export make the data portable, and C3 can wrap it later.

**D2 is the credible runner-up** if the user's motivation for "my own app" is mainly the look and the trend dashboard rather than owning the import engine. It offloads the hardest-to-get-right parts (import reconciliation, rule learning) to a VERIFIED, maintained MIT product. It depends on R16 and R17 and on the user's answer to Q3.

**B** is viable only if the user refuses any install *and* accepts Chrome/Edge, or disciplined exports.

**C1/C2 and D1** add toolchain or fork burden that is disproportionate for a non-specialist maintainer.

**E and F** remain the benchmark and stopgap, and the answer if the user reconsiders custom development.

## Recommendation confidence

**MEDIUM.**

Why:
- The platform facts behind A are VERIFIED: binding defaults, Python install route, chart licences, browser storage limits.
- The largest risks are not platform risks. They are the user's actual bank CSV layouts (UNKNOWN or CONFLICTING for most banks) and the unverified storage-location and localhost-security details (R1, R7). Those affect every custom option equally, so they lower confidence in the build overall more than in the ranking.
- The A vs D2 ranking depends on an unanswered question about the user's intent.

## Open questions for the user

1. **Which banks and account types** do you import? In particular, will you import a credit card as well as the account that pays it? (Default: assume at least one transaction account and one credit card, and build transfer handling into Phase 1.)
2. **Budget period:** calendar month, or pay cycle? (Default: calendar month, with the data model kept able to change.)
3. **What does "my own app" mean to you?** Would a dashboard you own on top of a free engine (Actual Budget) count, or should every part be yours? (Default: every part is yours, i.e. Option A.)
4. **Do you need history older than your banks' CSV download window** (roughly 18 months to 2 years)? This decides whether PDF import is needed at all. (Default: no; PDF deferred to Phase 3.)
5. **Browser and launch:** is opening a browser tab via a double-click launcher acceptable, or do you want a dock app? Which browser do you use? (Default: a browser tab is fine; any browser.)

## What would change the ranking

- **R11 shows `file://` browser storage is persistent and reliable in Safari, or the user commits to Chrome and exports** → B rises (zero install).
- **The user will not install Python, or cannot** → B, or E/F.
- **R16 confirms clean local API access to Actual desktop data including spent-per-category, and the user accepts partial ownership (Q3)** → D2 may overtake A. It has less custom import code to get wrong.
- **R17 finds unwanted outbound calls from Actual** → D and E drop.
- **The user needs history beyond the CSV windows, or a bank's CSV is unusable (e.g. Macquarie personal on-screen-only limits bite)** → PDF moves to Phase 1. That strengthens A (pdfplumber) further and weakens B.
- **The user insists on a native dock app** → C3 on top of A (if R13 passes), rather than C1/C2.
- **R7 finds localhost web apps hard to secure for a non-specialist** → C1 (IPC, no listener) or B (`file://`, no listener) gain relative to A.
- **The user decides a spreadsheet or Actual is enough** → E/F become the recommendation. "Use an existing product" is a valid outcome under DECISION_FRAMEWORK.

---

Files read:
- /Users/alphakings/Documents/AI Research Lab/projects/budget-adherence-tracking/PROJECT_STATE.md
- /Users/alphakings/Documents/AI Research Lab/projects/budget-adherence-tracking/research/01-landscape.md
- /Users/alphakings/Documents/AI Research Lab/projects/budget-adherence-tracking/research/02-local-build-options.md
- /Users/alphakings/Documents/AI Research Lab/DECISION_FRAMEWORK.md

Suggested save location: /Users/alphakings/Documents/AI Research Lab/projects/budget-adherence-tracking/architecture/01-options.md

Sources for the new checks made in this pass:
- [Actual Budget API overview](https://actualbudget.org/docs/api/)
- [Actual Budget API reference](https://actualbudget.org/docs/api/reference)
- [PDF.js repository](https://github.com/mozilla/pdf.js)
