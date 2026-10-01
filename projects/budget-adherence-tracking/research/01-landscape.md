# Research Report: budget-adherence-tracking, Landscape (Research Questions 1–8)

Date of research: 2026-09-24
Status: **Partial.** The coordinator told me to stop before every question was fully covered. I researched Q1, Q3, Q4 and Q8 against sources. For Q2, Q5, Q6 and Q7 I only checked browser storage eviction against a source (MDN). The rest of those answers comes from general technical knowledge. Those claims are classified no higher than LIKELY and are listed as research gaps.

---

## Research objective

Find out what is true and available for a $0, local-only (Mac, localhost) personal budget-vs-actual tool for an Australian user. The user imports CSV and PDF statements they download from several Australian banks. The user wants their own custom app. Existing tools are researched as a benchmark, a fallback and a source of reusable parts.

## Questions investigated

1. Existing free, local budgeting tools. Researched: Actual Budget, Firefly III, GnuCash, HomeBank, Maybe/Sure, Money Manager Ex, hledger.
2. Spreadsheet approach. Not researched against sources.
3. Australian bank CSV and PDF formats. Researched: CBA, Westpac, NAB, ANZ, ING, Macquarie, Bendigo, St.George, Up.
4. Local categorisation methods. Partly researched.
5. Local data safety. Browser storage eviction researched; the rest not.
6. Technology options for a local app. Not researched against sources.
7. Setup and maintenance burden. Inferred from Q1 and Q6 evidence only.
8. Local PDF extraction. Researched: pdfplumber, Camelot, tabula-py, existing parsers.

---

## Key findings

### Q1. Existing free, locally run budgeting tools

**Actual Budget: the strongest benchmark found**
- Licence: MIT. **VERIFIED**, https://github.com/actualbudget/actual
- Maintenance: releases roughly monthly. Latest is v26.9.0 (1 September 2026); earlier ones are v26.8.1 (7 August 2026), v26.8.0 (2 August 2026) and v26.7.0 (2 July 2026). Desktop builds exist for macOS on both Intel and ARM. **VERIFIED as of 2026-09-24**, https://github.com/actualbudget/actual/releases
- Local-first design: "the primary database hosted on your local device rather than in a remote server". The desktop app bundles its own server, which runs on localhost. **VERIFIED**, https://actualbudget.org/docs/faq/ and https://actualbudget.org/docs/install/desktop-app/
- Privacy policy (last updated 13 January 2024) says: no automatic data collection, no tracking, and data is stored locally. Optional end-to-end encryption uses a locally generated key. **VERIFIED as a vendor statement**, https://actualbudget.org/docs/privacy-policy/
  - I did not independently confirm what network calls the desktop app actually makes, such as update checks or font or CDN loads. **UNKNOWN**
- CSV import (https://actualbudget.org/docs/transactions/importing/) **VERIFIED**:
  - Imports CSV, QIF, OFX, QFX and CAMT.
  - Lets you map fields and choose date formats and delimiters.
  - Has a "split amount into separate inflow/outflow columns" option, plus "flip amount" and a multiplier.
  - Detects duplicates by id, then by nearby date, same amount and similar payee.
  - Supports no PDF import. Mapping reuse is not documented, so whether saved mappings exist is **UNKNOWN**.
- Categorisation: Actual "will automatically create rules for you based on your behavior". When you categorise a transaction, it creates a rule setting the category for that payee. Rules can use is, contains, regex matches and one-of, run in pre, default and post stages, and match case-insensitively. **VERIFIED**, https://actualbudget.org/docs/budgeting/rules/
- Budget vs actual:
  - "Tracking budget" mode does traditional budgeting without rollover. Its pie indicators show under budget and on budget in green and overspent in red. **VERIFIED**, https://actualbudget.org/docs/getting-started/tracking-budget/
  - The standard dashboard widgets are Cash Flow, Net Worth, Spending Analysis, Summary, Calendar and Custom Reports. Custom Reports can split totals by category per month.
  - A "Budget Analysis" report exists only as an experimental feature. **VERIFIED**, https://actualbudget.org/docs/reports/
  - Implication: per-category budget vs actual per month is visible on the budget page. A dedicated trend chart of budget vs actual per category over months is not a standard report. **LIKELY**
- AUD: currency handling was not investigated. **UNKNOWN**, low risk because only one currency is used.

**Firefly III**
- Licence: AGPL-3.0. **VERIFIED**, https://github.com/firefly-iii/firefly-iii
- Maintenance: latest stable is v6.7.3 (18 September 2026), with v6.7.0 to v6.7.2 released 14–16 September 2026. **VERIFIED as of 2026-09-24**, https://github.com/firefly-iii/firefly-iii/releases
- Deployment: a PHP web app. Docker Compose needs a Firefly container plus a database container (MariaDB, MySQL or PostgreSQL) and two .env files. **VERIFIED**, https://docs.firefly-iii.org/how-to/firefly-iii/installation/docker/
- CSV import is a separate "Data Importer" tool driven by JSON configurations. **VERIFIED**, https://docs.firefly-iii.org/tutorials/data-importer/csv/
- There is a community repository of import configurations, including Australian ones for ANZ, Commonwealth Bank, ING and Macquarie. **VERIFIED**, https://github.com/firefly-iii/import-configurations
- Telemetry was removed from the product. **CORROBORATED** by issue #5063 and the changelog, https://github.com/firefly-iii/firefly-iii/issues/5063
- Supports budgets, categories, rules and reports. **VERIFIED** at feature-list level only.
- Maintenance burden for a non-specialist on a Mac: high, because it needs Docker plus a database. **LIKELY**

**GnuCash**
- Licence: GPL. Latest is 5.16 (28 June 2026). Official macOS builds exist for Apple Silicon (macOS 11+) and Intel (10.13+). **VERIFIED**, https://www.gnucash.org/ and https://github.com/Gnucash/gnucash/releases/tag/5.16
- Its Budget Report shows budgeted and actual amounts side by side per account for each period. **VERIFIED**, https://www.gnucash.org/docs/v5/C/gnucash-guide/budget_reporting1.html
- It is double-entry accounting, which is a steeper learning curve for simple category budgeting. **LIKELY**
- The UI is dated compared with the "fresh, modern" requirement. **LIKELY**, subjective.

**HomeBank**
- Latest is 5.10.3 (14 September 2026). There is no official macOS build; install is via Homebrew or MacPorts. **VERIFIED**, https://www.gethomebank.org/en/downloads.php
- CSV import requires HomeBank's own fixed column order (date, payment, number, payee, memo, amount, category, tags), semicolon-separated by default. Bank CSVs therefore need converting first. **VERIFIED**, https://www.gethomebank.org/help/misc-csvformat.html
- Licence: GPL. **LIKELY**, not confirmed this session.

**Maybe Finance and its fork Sure**
- The Maybe repository was archived on 27 July 2025. **CORROBORATED**, https://github.com/maybe-finance/maybe
- The community fork "Sure" is AGPLv3 and self-hosted with Docker. **CORROBORATED**, https://github.com/we-promise/sure
- Sure's maintenance level was not checked. **UNKNOWN**

**Money Manager Ex**
- The releases page showed v1.9.4 (31 August 2024) as the latest. **UNCERTAIN**: the page may have been truncated, and macOS build availability was not confirmed. https://github.com/moneymanagerex/moneymanagerex/releases

**hledger (plain-text accounting)**
- `balance --budget -M` produces monthly reports of actual vs budget per account, with the percentage of budget used. **VERIFIED**, https://hledger.org/budgeting.html
- It is command-line and text-file based. It is poor on "clean modern visuals" unless paired with a UI. **LIKELY**
- Licence, latest release and its CSV-rules feature were not checked. **UNKNOWN**

**Not investigated:** Beancount/Fava, KMyMoney, Skrooge, ezBookkeeping. Australian cloud apps (e.g. MoneyBrilliant, Frollo, WeMoney) are excluded by the local-only constraint and were not checked.

### Q2. Spreadsheet approach (not researched against sources)
- Google Sheets stores data on Google's servers, so it conflicts with the "data never leaves the computer" constraint. **LIKELY**, follows from how the product works.
- Apple Numbers is free on macOS. LibreOffice Calc is free and open source. **LIKELY**, not re-verified.
- Excel for Mac generally needs a paid Microsoft 365 or Office licence for full editing, which conflicts with the $0 budget. **UNCERTAIN**, not verified.
- Spreadsheet features look sufficient for the outcome: SUMIFS or pivot tables by category and month, conditional formatting for over-budget cells, charts. **LIKELY**
- The weak points are:
  - normalising different bank CSV layouts,
  - keyword category rules (lookup tables work, but are fragile),
  - duplicate detection,
  - a "fresh, modern" look.

  **LIKELY**

### Q3. Australian bank CSV and PDF formats

Main pattern: official bank help pages confirm which export formats exist and some limits, but almost never document the columns. Column details come from open-source parsers and community configurations (more credible) and from SEO-style converter-vendor blogs (less credible, possibly AI-generated). Before building parsers, all formats should be checked against a real sample file from the user.

| Bank | Export formats (official where noted) | Columns / sign convention | Header row | History / limits | Confidence |
|---|---|---|---|---|---|
| **CommBank** | CSV, OFX, QIF via NetBank desktop; PDF statements | Date (DD/MM/YYYY), signed Amount, Description, Balance | **None** | About 600 transactions per export, about 2 years; exports reportedly unreliable beyond about 12 months; PDF statements up to about 7 years | Columns and no header: **CORROBORATED** by the Firefly config (2022) and massyn/bankcsv. Limits: **UNCERTAIN** (vendor blogs only; the official CBA page did not render) |
| **ANZ** | CSV (OFX also reported) | Community code: headerless, date DD/MM/YYYY, **signed** amount, description, then extra columns (Firefly config lists 8 columns). Vendor blogs instead claim separate debit and credit columns plus balance | Community: none | About 24 months (vendor blogs) | **CONFLICTING**. The code-based sources are more credible. |
| **NAB** | Official: "spreadsheet, QIF file or PDF". View up to 731 days | Vendor blog: single signed Amount. Also claims personal accounts get no true CSV, only a spreadsheet file | UNKNOWN | 731 days, **VERIFIED** | Formats and history: **VERIFIED**, https://www.nab.com.au/personal/online-banking/nab-internet-banking/transaction-history. Columns and whether the "spreadsheet" is CSV or XLSX: **UNCERTAIN** |
| **Westpac** | Official: CSV, QBO, QIF, OFX from desktop Online Banking; you choose the date format; same steps for personal and business | Vendor blogs: date, narrative, separate debit and credit, balance. A commonly cited header is "Bank Account,Date,Narrative,Debit Amount,Credit Amount,Balance,Categories,Serial", but I could not confirm it from a primary source | Reported present | Transaction search up to 3 years (official); export reportedly about 18 months | Formats: **VERIFIED**, https://www.westpac.com.au/business-banking/online-banking/support-faqs/export-files/. History: **VERIFIED**, https://www.westpac.com.au/personal-banking/online-banking/making-the-most/transaction-history/. Columns: **UNCERTAIN** |
| **ING** | CSV (OFX and QFX also, per ing-categorizer) | Firefly config: Date (d/m/Y), Description, Credit, Debit | Yes | UNKNOWN | **LIKELY**. Single community config from 2022. |
| **Macquarie** | Official (business help): CSV and QIF; the personal help page says only transactions visible on screen are downloaded | Firefly config: Date ("d M Y" format), Description, Account, **Category**, …, Notes, Debit, Credit, … (10 columns) | Yes | Business: 30,000-transaction cap | Formats and caveat: **VERIFIED**, https://www.macquarie.com.au/help/personal/statements-and-reports/find-a-statement-or-report/viewing-and-downloading-past-transactions.html and the business export help page. Columns: **LIKELY** (2023 config) |
| **Bendigo** | Download icon on the Transactions tab; CSV reported; about 600-transaction batches reported | UNKNOWN | UNKNOWN | UNKNOWN | **UNCERTAIN**. The official page did not return content. |
| **St.George** | CSV or QIF from transaction history (community and accountant sources) | UNKNOWN | UNKNOWN | UNKNOWN | **UNCERTAIN** |
| **Up** | CSV export exists (Up blog, 31 October 2019) | UNKNOWN | UNKNOWN | UNKNOWN | Existence: **VERIFIED**, https://up.com.au/blog/csv/. Details: **UNKNOWN** |

Cross-bank conclusions:
- Formats differ materially between banks. The differences include:
  - whether there is a header row (CBA and ANZ have none; ING, Macquarie and Westpac have one),
  - a signed amount column vs separate debit and credit columns,
  - date formats (d/m/Y vs "d M Y"),
  - column count.

  **CORROBORATED**
- Australian date order is day/month/year throughout. A parser that assumes US month/day order would silently corrupt dates up to the 12th of each month. **CORROBORATED**
- Headerless files (CBA, ANZ) cannot be detected from column names. They need detection by column shape, or the user choosing the bank when importing. **LIKELY**, based on massyn/bankcsv's detection approach, https://github.com/massyn/bankcsv
- Several banks limit how much can be exported (CBA about 600 transactions; Macquarie personal only exports what is on screen). Pulling long periods of history may need several exports, which raises the importance of duplicate detection. **CORROBORATED** for CBA and Macquarie.
- CSV and OFX/QIF are not available from the mobile apps for CBA and Westpac, only from desktop browsers. **UNCERTAIN**, vendor blogs only.
- Many banks also offer OFX and QIF, which are more standardised than CSV. OFX may carry typed fields such as transaction IDs that help with duplicates. **LIKELY**; the ing-categorizer author prefers OFX for this reason, https://github.com/comozo/ing-categorizer

### Q4. Local, no-cost categorisation
- Merchant and keyword rules learned from user corrections are proven in production: Actual Budget creates a payee-to-category rule when the user categorises. **VERIFIED**, https://actualbudget.org/docs/budgeting/rules/
- Bank-provided categories: Macquarie's CSV includes a Category column. **LIKELY**, from the Firefly config. Westpac's reported header includes "Categories". **UNCERTAIN** Other banks: **UNKNOWN**. Bank categories would not match the user's 9–10 categories, so they would at most help with mapping. **LIKELY**
- Local machine learning or LLM: ing-categorizer is an existing local pipeline for ING Australia. It uses a scikit-learn TF-IDF plus logistic-regression classifier retrained on confirmed categorisations (needs at least 20 examples, confidence threshold 0.65). It falls back to Ollama `qwen2.5:3b`, sending only the description text, with fixed category choices. It claims no accuracy metrics. **VERIFIED as a description of that project**, https://github.com/comozo/ing-categorizer
- Accuracy evidence is weak and not Australia-specific:
  - An arXiv study on business-bank transactions reports 73.5% accuracy for a fine-tuned model, rising to 90.4% on high-confidence predictions. GPT-4o zero-shot reached 60.4%. The authors attribute the difficulty to heavily abbreviated descriptions. https://arxiv.org/html/2508.05425v1
  - Implication: zero-shot LLM categorisation of terse bank descriptions is not reliably accurate, and a rules-first approach with user confirmation is well supported. **UNCERTAIN**, since the evidence comes from one business-banking study.
  - No accuracy data was found for personal Australian transactions with a fixed set of 9–10 categories. **UNKNOWN**
- Ollama privacy: local inference reportedly sends no prompts off the machine, and network calls are limited to model downloads and update checks. However, models tagged `-cloud` (after `ollama signin`) run remotely. This is a real risk under the no-data-leaves constraint. **UNCERTAIN**: I only found third-party blogs and did not verify against Ollama's official docs, e.g. https://humla.team/blog/is-ollama-local
- Hardware: whether the user's Mac can run a 3B or larger model well enough is **UNKNOWN**.

### Q5. Keeping data safe locally
- Browser storage (IndexedDB, localStorage and so on), per MDN (https://developer.mozilla.org/en-US/docs/Web/API/Storage_API/Storage_quotas_and_eviction_criteria):
  - Storage is "best-effort" by default and can be evicted under storage pressure, least recently used first. **VERIFIED**
  - `navigator.storage.persist()` requests persistent storage, which is removed only by the user. **VERIFIED**
  - **Safari deletes all script-created storage for an origin with no user interaction in the last 7 days of browser use** (when tracking prevention is on). **VERIFIED**
  - Eviction deletes all of an origin's data at once. Clearing site data removes IndexedDB. **VERIFIED**
  - Implication: a browser-only app that keeps its data in browser storage risks silent total loss unless there is an export or backup mechanism. Safari is a particular risk. **LIKELY**
- A server-side SQLite file or plain files on disk are not subject to browser eviction and can be backed up by Time Machine. **LIKELY**, not researched.
- Encryption: FileVault full-disk encryption protects data at rest when the Mac is off or locked. Encrypted SQLite would need an extension (e.g. SQLCipher), which adds complexity. **LIKELY**, not researched.
- Localhost binding: a server must bind to 127.0.0.1, not 0.0.0.0, or it becomes reachable from the local network. Some frameworks listen on all interfaces by default (e.g. Node's `server.listen` with no host). **LIKELY**, not verified this session. The Actual docs mention exposing the desktop server through a reverse proxy or Ngrok, which shows that exposure happens through configuration choices. **VERIFIED** that the docs discuss it.
- Hidden network calls: a custom app that loads charting libraries, fonts or CSS from CDNs, e.g. Google Fonts, makes external requests. This leaks metadata, not statement data, but breaks a strict no-network posture. **LIKELY**
- A PDF statement contains the account number, name and address, so imported source files are sensitive in their own right. **ASSUMPTION**

### Q6. Technology options for a local app (not researched against sources)
All claims in this section are **LIKELY** from general knowledge and need verification.
- **Localhost web app** (Python or Node server, browser UI, SQLite): data lives on disk; the user must start the server; a Python or Node runtime and dependencies are needed.
- **Single-file HTML app with in-browser storage**: no install, but it carries the eviction risk above. Reading local files via file input or drag-and-drop works without a server. PDF parsing would need a JavaScript library such as PDF.js.
- **Electron**: bundles Chromium and Node, so the app is large. Without a paid Apple Developer ID ($0 budget), a distributed build is unsigned and hits Gatekeeper warnings. A build used only on the user's own Mac may be manageable.
- **Tauri**: uses the system WebView (WKWebView on macOS), so builds are smaller, but it needs the Rust toolchain.
- **Free charting libraries**: Chart.js (MIT), Apache ECharts (Apache-2.0), Recharts (MIT), uPlot (MIT). Licences not re-verified. They should be bundled locally rather than loaded from a CDN.
- **Reuse of Actual Budget code** is permitted by the MIT licence. **VERIFIED** licence; fitness for reuse is **UNKNOWN**.

### Q7. Setup and maintenance burden (inferred, not researched)

| Option | Burden for a non-specialist | Confidence |
|---|---|---|
| Actual desktop app | Low: download a signed or packaged .dmg and use it | **LIKELY**; signing status not checked |
| GnuCash | Low to install; medium to learn | **LIKELY** |
| HomeBank | Medium: needs Homebrew or MacPorts plus conversion of every bank CSV into its format | **LIKELY** |
| Firefly III, Sure | High: Docker plus a database plus a separate importer | **LIKELY** |
| Spreadsheet | Low setup; ongoing manual effort to paste and normalise each bank's CSV | **LIKELY** |
| Custom localhost app | Medium: runtime and dependency updates, server start-up, backups the user must own | **LIKELY** |
| Single-file HTML app | Low setup; high data-loss risk without disciplined export or backup | **LIKELY** |

### Q8. PDF-to-transactions extraction
- pdfplumber:
  - MIT licence, v0.11.10 (15 June 2026). **VERIFIED**, https://pypi.org/project/pdfplumber/
  - "Works best on machine-generated, rather than scanned, PDFs"; no OCR. **VERIFIED**, https://github.com/jsvine/pdfplumber
- Camelot:
  - MIT licence. Has lattice and stream modes (plus network, hybrid and ML modes). The default pdfium backend needs no system dependencies.
  - Built-in parsers need text-based PDFs; scanned files need the `[ml,ocr]` extras. **VERIFIED**, https://github.com/camelot-dev/camelot
  - Latest release date: **UNKNOWN**, the PyPI page failed to load.
- tabula-py: MIT licence, needs Java 8+ (extra install burden). **VERIFIED**, https://github.com/chezou/tabula-py
- Australia-specific: a gist exists for extracting CommBank PDF statements to CSV. **VERIFIED that it exists**, https://gist.github.com/nullableVoidPtr/b5193cca8a1b062a42ca229525a05d07. Its quality and currency are **UNKNOWN**.
- Reliability technique: some parsers check that opening balance plus transactions equals the closing balance, and check running balances. **VERIFIED as a feature** of boscorat/bank_statement_parser (UK banks), https://github.com/boscorat/bank_statement_parser. This is a relevant way to detect extraction errors.
- Whether Australian bank PDF e-statements are machine-generated text PDFs: **LIKELY** but not verified.
- Every bank's PDF layout differs and may change without notice. Multi-line descriptions, page breaks, and card vs transaction accounts are known failure points. PDF parsing needs per-bank templates. **LIKELY**; no Australian accuracy data was found.
- CSV as the primary input and PDF as a secondary input for history beyond the CSV window is supported by the evidence. CommBank's CSV reaches about 2 years while its PDF statements reach about 7 years (vendor-blog sourced). **LIKELY**

---

## Evidence and sources (main ones)
- Actual Budget: https://github.com/actualbudget/actual, https://github.com/actualbudget/actual/releases, https://actualbudget.org/docs/transactions/importing/, https://actualbudget.org/docs/budgeting/rules/, https://actualbudget.org/docs/getting-started/tracking-budget/, https://actualbudget.org/docs/reports/, https://actualbudget.org/docs/privacy-policy/, https://actualbudget.org/docs/install/desktop-app/
- Firefly III: https://github.com/firefly-iii/firefly-iii, https://github.com/firefly-iii/firefly-iii/releases, https://docs.firefly-iii.org/how-to/firefly-iii/installation/docker/, https://github.com/firefly-iii/import-configurations (AU configs: raw default.json for anz, commonwealth-bank, ing, macquarie), https://github.com/firefly-iii/firefly-iii/issues/5063
- GnuCash: https://www.gnucash.org/, https://github.com/Gnucash/gnucash/releases/tag/5.16, https://www.gnucash.org/docs/v5/C/gnucash-guide/budget_reporting1.html
- HomeBank: https://www.gethomebank.org/en/downloads.php, https://www.gethomebank.org/help/misc-csvformat.html
- Maybe/Sure: https://github.com/maybe-finance/maybe, https://github.com/we-promise/sure
- hledger: https://hledger.org/budgeting.html
- Banks (official): https://www.nab.com.au/personal/online-banking/nab-internet-banking/transaction-history, https://www.westpac.com.au/business-banking/online-banking/support-faqs/export-files/, https://www.westpac.com.au/personal-banking/online-banking/making-the-most/transaction-history/, https://www.macquarie.com.au/help/personal/statements-and-reports/find-a-statement-or-report/viewing-and-downloading-past-transactions.html, https://www.macquarie.com.au/help/business/manage-your-accounts/statements-and-transactions/export-transactions-as-csv-or-qif-files.html, https://up.com.au/blog/csv/
- Banks (community code): https://github.com/massyn/bankcsv
- Banks (vendor blogs, low weight): https://aussiebankstatements.com/blog/how-to-download-commbank-statement-csv, https://invoicedataextraction.com/blog/commonwealth-bank-statement-to-excel
- Categorisation: https://github.com/comozo/ing-categorizer, https://arxiv.org/html/2508.05425v1
- PDF: https://pypi.org/project/pdfplumber/, https://github.com/jsvine/pdfplumber, https://github.com/camelot-dev/camelot, https://github.com/chezou/tabula-py, https://github.com/boscorat/bank_statement_parser
- Browser storage: https://developer.mozilla.org/en-US/docs/Web/API/Storage_API/Storage_quotas_and_eviction_criteria

## Existing solutions (benchmark summary)
- **Actual Budget** comes closest to the outcome at $0 locally on a Mac:
  - MIT licence, active monthly releases, macOS desktop build.
  - Local-first, with a no-tracking privacy policy.
  - Flexible CSV mapping including debit/credit columns, learned payee rules, duplicate detection.
  - A tracking-budget mode with over and under indicators.

  Gaps: no PDF import; no standard multi-month budget-vs-actual trend chart per category (experimental only); network behaviour not independently audited.
- **GnuCash** meets budget vs actual with official Mac builds, but it is double-entry and dated-looking.
- **hledger** has strong budget reports but is text-based.
- **HomeBank, Firefly III and Sure** carry higher friction on a Mac: HomeBank because of its fixed CSV format and Homebrew-only install, Firefly III and Sure because of Docker.

## Relevant technologies
SQLite; IndexedDB with `navigator.storage.persist()`; pdfplumber and Camelot (Python, MIT); PDF.js (not researched); Chart.js, ECharts and uPlot (not researched); Ollama (local LLM, not officially verified); scikit-learn TF-IDF classifiers; OFX and QIF as alternative bank export formats.

## Important limitations
- Official bank documentation almost never specifies CSV columns. Formats must be checked against the user's real files.
- CommBank and Macquarie place limits on exports.
- Safari's 7-day eviction and browser best-effort storage threaten browser-only persistence.
- PDF extraction works only for text-based PDFs, needs per-bank layouts, and has no Australian accuracy evidence.
- LLM categorisation of terse descriptions is not reliably accurate on current evidence.

## Conflicting evidence
- **ANZ CSV layout.** Community code (Firefly config, bankcsv) says headerless with a signed amount. Converter-vendor blogs say separate debit and credit columns plus balance. The code-based sources are more credible, but ANZ may have changed format since the 2022 config. Unresolved.
- **CommBank export window.** "About 2 years / 600 transactions" vs "reliable only to about 12 months". Both come from vendor blogs, and the official page did not render.
- **NAB export type.** The official page says "spreadsheet". A vendor blog claims no true CSV for personal accounts but also describes "NAB's CSV". Unresolved.

## Unknowns
- Which banks the user actually uses. This is now the main driver of parser scope.
- Exact current CSV columns for every bank. Only CBA is CORROBORATED.
- Whether Australian PDF statements are text-based, and their layouts.
- Actual Budget's real network behaviour (update checks, external assets).
- Official Ollama network behaviour and whether the user's Mac can run local models well.
- Excel for Mac licensing at $0.
- Money Manager Ex current status; Beancount/Fava, KMyMoney and Sure maintenance.
- Accuracy of rules or ML categorisation on Australian personal transactions.

## Research gaps (validation required)
1. Get one anonymised sample CSV (and, if in scope, one PDF) from each of the user's banks. This is the most valuable single validation.
2. Monitor Actual Budget desktop network traffic, e.g. with Little Snitch or LuLu (free), to confirm local-only behaviour. This matters if Actual is used as a benchmark, a fallback, or a code source.
3. Verify Q5 and Q6 claims against primary docs: Node, Python and Flask default bind addresses; Tauri and Electron macOS requirements and code-signing at $0; chart library licences; SQLCipher availability.
4. Verify Ollama's official network, telemetry and `-cloud` model behaviour.
5. Check Camelot's release date, Beancount/Fava, and hledger CSV rules and licence.
6. Test pdfplumber on real Australian statements, with a balance-continuity check.

## Findings that materially affect architecture
- Bank CSV formats differ in header presence, amount-sign convention, date format and column count. At least two major banks (CBA, ANZ) have headerless CSVs. Per-bank import profiles, or a user-driven mapping step, are therefore needed. **CORROBORATED**
- Australian day/month/year dates must be parsed explicitly. **CORROBORATED**
- Export limits (CBA about 600 transactions; Macquarie on-screen-only) mean overlapping imports are likely. Duplicate detection moves from should-have towards necessary. **CORROBORATED** for the limits; the requirement consequence is **LIKELY**.
- Browser storage can be silently wiped (Safari's 7-day rule, least-recently-used eviction). Any browser-storage design needs persistence plus export or backup; disk-based storage avoids this class of risk. **VERIFIED** for the facts; the design implication is **LIKELY**.
- Rules learned from user corrections are a proven categorisation pattern (Actual). Zero-shot LLMs show weak accuracy on abbreviated transaction descriptions. **VERIFIED** / **UNCERTAIN**
- PDF parsing is feasible locally at $0 for text-based PDFs, but per-bank and fragile. Evidence favours CSV (or OFX) as the primary input. **LIKELY**
- Actual Budget's MIT code (CSV import, rules engine) is legally reusable. **VERIFIED** for the licence.

## Facts that could change direction
- If the user's banks all provide clean CSV or OFX, PDF parsing may be unnecessary. It would then only matter for older history.
- If Actual Budget's tracking-budget mode plus custom reports is found to meet the outcome, the custom app's added value narrows to presentation and PDF import. The user has stated a preference for their own app regardless.
- If Actual's desktop app is found to make unwanted network calls, the benchmark and fallback position weakens.
- If the user's Mac cannot run local models, or the user wants zero manual categorisation, categorisation strategy becomes a larger risk.
- If a spreadsheet is acceptable to the user, it is the lowest-effort $0 path, though it is weaker on the look and on multi-bank normalisation.

## Overall confidence
- **MEDIUM** for Q1 (existing tools) and Q8 (PDF libraries).
- **MEDIUM-LOW** for Q3 (bank formats): official sources confirm export formats and some limits only; columns rely on community code and are partly conflicting.
- **LOW-MEDIUM** for Q4.
- **LOW** for Q2, Q5 (except browser eviction, which is VERIFIED), Q6 and Q7, which were not researched against sources because research stopped early.
