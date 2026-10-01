# Research 03: validation of disputed facts and bank CSV layouts

Saved in full as returned by the researcher subagent, 2026-09-30. All URLs checked 2026-09-30.

Outcome for bank layouts: no official page for NAB, ING or Macquarie personal gives header, column order, date format or sign convention. Only community and secondary sources exist, and they conflict in places. Get the user's real export header rows before writing any bank profile.

### Decision-changing findings

**1. Bank CSV layouts: official sources give no column spec (UNKNOWN); community evidence below is hints only.**

| Bank | Official (VERIFIED) | Community layout (UNCERTAIN) | Gaps and conflicts |
|---|---|---|---|
| NAB personal | Export "in a spreadsheet, QIF file or PDF"; up to 731 days; no column, pending or size detail. Sources: https://www.nab.com.au/personal/online-banking/nab-internet-banking/transaction-history and https://www.nab.com.au/personal/banking/nab-internet-banking/faqs/transaction-history-faqs | Third-party converter blogs say Date, Description, Debit, Credit, Balance, and elsewhere a single signed Amount column with debits negative. These conflict, and I found no repo or importer config that confirms either. | Whether personal "spreadsheet" is CSV or XLSX: one aggregator says personal has no CSV and CSV is business-only. That is unverified, but it keeps the risk alive. A NAB help page says "CSV" for NAB Connect (business). CONFLICTING. |
| ING AU | Help pages found do not describe the export columns (only the FAQ page title "How to export transactional Information"; the fetch returned nothing useful). The path is Transaction history, then Export, as CSV or QIF (per secondary sources). | Firefly III import config (https://github.com/firefly-iii/import-configurations/blob/main/au/ing/default.json): header row present, comma-delimited, date `d/m/Y`, order date, description, credit, debit, then one ignored column (presumably balance). An older 2012 repo (https://github.com/robdmoore/IngCsvParser) gives Date, Description, Debit, Credit, Balance, with debits shown as negative numbers and dd/mm/yyyy dates. | The two sources disagree on Credit/Debit column order, and the old repo is 2012. Description is one verbose combined string (payee plus type plus reference). CONFLICTING. |
| Macquarie personal | Download is CSV or QIF and covers **only the transactions loaded on screen**, so the user must scroll to load more rows before downloading (https://www.macquarie.com.au/help/personal/payments-transfers-and-deposits/transaction-information/searching-your-transactions.html). The 30,000-row cap and the two sort options (credit-debit or chronological) come from the business export page and may not apply to personal (https://www.macquarie.com.au/help/business/manage-your-accounts/statements-and-transactions/export-transactions-as-csv-or-qif-files.html). No column, date or pending detail. | Firefly config (https://github.com/firefly-iii/import-configurations/blob/main/au/macquarie/default.json): header row, comma-delimited, date `d M Y`. Ten columns in the order date, description, account, category, (unused), note, debit, credit, (unused), (unused). massyn/bankcsv (https://github.com/massyn/bankcsv) reads `Transaction Date` as `DD Mon YYYY`, `Details`, `Account`, `Balance`, `Debit`/`Credit` with signed amount as credit minus debit, and identifies Macquarie files by Debit/Credit plus 2 or more of Category, Subcategory, Original Description. | The files look like separate Debit and Credit columns with text-month dates. Both are unconfirmed for the user's account types. The export includes a bank-assigned Category column. |

- Sign convention: ING appears to be separate Debit and Credit columns, and Macquarie likely the same. NAB is UNKNOWN. Credit card sign conventions for the three banks are UNKNOWN.
- Pending items and running-balance stability between exports: UNKNOWN for all three banks. No official statement was found.
- Whether Macquarie or ING balance columns are stable across overlapping exports is therefore UNKNOWN. This supports the critic's H4 (do not put balance in the duplicate key).
- Why it matters: profiles must not be written from these hints. The date format differs by bank (`dd/mm/yyyy` vs `dd Mon yyyy`). Debit/Credit column order is disputed. Text-month dates need a locale-safe parser (for example `%b` depends on the locale, and September may appear as "Sept").
- Validation needed: the user's header row plus 2-3 rows per account type (transaction, savings, card). Under the user's approval, whole statements are already allowed. Ask for one export per account type, including any card. Also confirm from the files whether the NAB export is `.csv` or `.xlsx`.

**2. Actual Budget per-category spent figures: source-confirmed. Status changes from LIKELY to CORROBORATED.**
- The `api/budget-month` handler in loot-core returns, per expense category, `budgeted`, `spent`, `balance` and `carryover`. Income categories return `received`.
- Source: https://raw.githubusercontent.com/actualbudget/actual/master/packages/loot-core/src/server/api.ts, read via fetch summary, so it was not read directly (LIKELY-to-CORROBORATED).
- The public `getBudgetMonth` wrapper has no declared return type (https://raw.githubusercontent.com/actualbudget/actual/master/packages/api/methods.ts). The API reference page also does not document it (https://actualbudget.org/docs/api/reference/).
- Local mode: `init()` with no config is documented as local-only (VERIFIED, API reference). The main docs still show the flow needing a sync ID and a server (https://actualbudget.org/docs/api/). Opening the desktop app's own budget directly, and concurrent use with the running desktop app, remain UNKNOWN. Nothing in the docs addresses concurrent use.
- Why it matters: D2 is viable on the read side. Use of the API is still gated on the local-access and concurrency questions.

**3. Actual custom themes: CSS pasting is documented as standard, not experimental (VERIFIED), under Settings > Themes > Custom theme > "Additional CSS overrides".**
- Source: https://actualbudget.org/docs/custom-themes/. No network call is needed for pasted CSS (inferred, not verified).
- The catalog does fetch themes from GitHub when selected (VERIFIED). The exact requests are UNKNOWN.
- Why it matters: this is benchmark and fallback information only, since the user chose a custom app.

**4. Chrome Local Network Access covers less than the critique assumed.**
- The permission prompt gates `fetch()`, subresource loads and subframe navigation. WebSockets, WebTransport and WebRTC are not yet gated. Loopback (127.0.0.0/8 and ::1) is explicitly included.
- Chrome 138 was opt-in; the article says it launches in Chrome 142. Source: https://developer.chrome.com/blog/local-network-access (VERIFIED).
- Top-level navigation and form POSTs are not listed as gated (the article does not list them). A classic cross-site form POST to `127.0.0.1` therefore may not be blocked by LNA. That is UNCERTAIN.
- A Safari equivalent was not established (UNKNOWN). Sources found were forum posts only.
- Why it matters: LNA is not a substitute for app-side protection. It does not cover top-level form POSTs or WebSockets. The `TRUSTED_HOSTS`, CSRF and Origin checks the critique listed remain required.

**5. Claude Code can block file reads by path, but only for its own file tools and recognised Bash file commands.**
- Read deny rules (for example `Read(//Users/<name>/BudgetData/**)`) block the built-in file tools and Bash commands it recognises (`cat`, `head`, `tail`, `sed`, `tee`, and redirects).
- They do not block "arbitrary subprocesses that read or write files indirectly, like a Python or Node script that opens files itself", and not `grep -r` run from the directory that holds the files.
- The docs say to enable the sandbox for OS-level enforcement. Read rules are best-effort for Grep and Glob. Deny rules are checked before allow rules.
- Source: https://code.claude.com/docs/en/permissions (VERIFIED).
- Why it matters: if the AI builder runs the app or tests, a Python script can open the data folder regardless of deny rules, and the output lands in the AI's context. Sandboxing (https://code.claude.com/docs/en/sandboxing, not opened) is the only OS-level control mentioned. Whether the sandbox can deny a specific read path on macOS is UNKNOWN. Data retention terms of the AI tool were not researched.

**6. macOS Python route at $0.**
- Official recommendation: python.org installer, universal2, signed and notarised, macOS 11+. Current release is Python 3.14.7 (released 2026-08-05).
- After install, run `Install Certificates.command` once from `/Applications/Python 3.14/`.
- The python.org installer coexists with Apple's `/usr/bin/python3`, which the docs say never to modify.
- Sources: https://docs.python.org/3/using/mac.html and https://www.python.org/downloads/macos/ (VERIFIED). Note that these two pages cite different macOS minimums (10.15 vs 11); the downloads page is more recent.
- Homebrew route: works but auto-upgrades Python when other packages are installed, which can break virtual environments (CORROBORATED from secondary guides such as https://snyk.io/articles/how-to-install-python-on-macos/). The Xcode Command Line Tools Python is 3.9.6 (secondary source), older than the current release, and not needed.
- Beginner impact: the graphical installer plus `python3 -m venv` is the lowest-friction route. Running scripts by double-click in Finder may not inherit shell environment variables (VERIFIED, docs page above).

### Viable existing solutions (benchmark or fallback only)
- Actual Budget (MIT): the API exposes per-category budgeted, spent and balance. Its CSV import maps fields and offers duplicate detection (previously verified in research/01). Limit: it has no PDF import (previously verified). Gaps in what I could establish: desktop-app local API access and concurrency (UNKNOWN), and Mac notarisation and outbound connections (not researched, UNKNOWN).
- Firefly III has import configs for ING and Macquarie. It needs Docker and a database (research/01), so it is out of scope for the local-only, $0 beginner route.

### Unknowns / validation required
- Real export headers, column order, date format and sign convention for NAB, ING, Macquarie, plus any credit card products. Ask the user for one export per account type.
- Whether the NAB personal "spreadsheet" is CSV or XLSX.
- Pending or authorisation items in each export, and whether balances or descriptions change between overlapping exports. Test by exporting the same date range twice on different days (needs the user).
- Macquarie personal: how many rows the on-screen download holds and whether it can cover a whole month. This is a practical import limit, and the user must scroll to load older rows before downloading.
- ING help pages for column spec and date-range limits: not retrieved.
- Chrome/Safari history sync of `127.0.0.1` URLs: UNCERTAIN. I found only a forensics blog claiming Chrome syncs typed URLs only, which is weak and possibly dated (https://www.foxtonforensics.com/blog/post/analysing-synchronised-browser-history, not opened). Design rule stays: no transaction data in URLs or page titles.
- Safari loopback protection: UNKNOWN.
- Not researched (lower priority or out of scope): LuLu, Streamlit listen address, Beancount/Fava, Actual Mac notarisation and outbound calls, CBA/Bendigo/St.George (not the user's banks now).

### Architecture implications
- Per-bank profiles must be data-driven and validated against real files. Include per-profile date format (`dd/mm/yyyy` vs `dd Mon yyyy`), decimal and BOM handling, and support both separate Debit/Credit columns and a single signed Amount.
- Do not use the balance column for identity. Use it only for reconciliation, given that stability is unverified.
- Macquarie's export includes the bank's own Category and Original Description fields, which can seed or cross-check rules. Descriptions from ING are a single verbose string, so payee extraction needs bank-specific logic.
- A user-side download step matters for Macquarie: the file contains only what was loaded on screen, so the coverage panel should show date ranges per account. A short export would otherwise look like under-spending.
- If the AI builder runs the app or tests against real data, Read deny rules alone will not protect the data. A Python script opens files directly. The exposure is already approved, but the boundary must be a sandbox or an explicit approval, not path rules alone.
- The localhost app still needs app-side Host, Origin and CSRF controls. Chrome's LNA does not cover top-level form POSTs or WebSockets, and Safari's equivalent is unknown.

### Overall confidence
- MEDIUM on Actual API, Python route and Claude Code permission facts (official docs read directly, apart from api.ts, which was read as a fetch summary).
- LOW on bank export layouts, sign conventions, pending items and NAB file type, because official sources are silent and community sources conflict.
- LOW-MEDIUM on browser history and Safari loopback behaviour.
