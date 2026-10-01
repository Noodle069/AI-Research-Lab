# Changelog

## 0.1.2 (fix: relaunching while an old copy was running showed "Forbidden" on every page)
- Fixed: starting the app while an older copy still held the port printed a link with a new key, but the old copy answered, so every page said "Forbidden". The app now binds the port first. If the port is taken it prints a plain message ("already running in another Terminal window... press Control+C") and exits without printing a link.
- If you see that message: find the other Terminal window, press Control+C in it, then start the app again.

## 0.1.1 (fix: uploads failed in real browsers)
- Fixed: choosing a PDF and uploading it gave "Forbidden" in a real browser. The page told browsers to send no referrer, so browsers sent `Origin: null` on the upload form and the app's own security check rejected it. The app now uses the `same-origin` referrer policy: forms inside the app work, and no referrer is sent to any other site.
- Found by a real-browser test (Chrome); earlier tests used scripted requests that set the Origin by hand. `tests/browser_check.py` is the browser check for this (needs Playwright and Chrome; not part of the normal test run).
- If you had the app open before updating, stop it (Control+C) and start it again.

## 0.1.0 (first local release)
Runs on your own Mac only. Nothing is sent over the internet while you use it.

### Importing statements
- Reads text PDF statements: ING Orange Everyday, ING short report, NAB credit card, and offset / home loan transaction listings.
- Two checks per file, or the whole file is rejected and nothing is saved:
  - Statement check: opening balance + money in - money out = closing balance, to the cent (NAB: the printed Payments and Purchases totals).
  - Row check: where each row prints a balance, the previous balance plus the amount equals that balance.
  Error messages give the row number and kind of field only, never amounts or descriptions.
- Unknown layouts are rejected, never guessed.
- Preview before saving: date range, counts, totals in and out, check results, inferred years, detected transfers, duplicates and the Uncategorised count. Nothing is written until you approve.
- Duplicates: the same file is blocked; overlapping statements are matched by date, amount and description so rows are not counted twice.
- ING rows now include the merchant line. Rows saved by a pre-release build with the shorter description would be saved again on re-import (see README).

### Backups
- A copy of your database is made before every import (newest 20 kept, changeable with BUDGET_BACKUP_KEEP). No cloud backup.

### Accounts and transfers
- Each account has a role (spending, credit card, loan, offset). Transfers between your own accounts, card repayments and loan flows are excluded from category spending; you confirm or reject suggestions on the Transfers page.
- Coverage page: which accounts and date ranges each month has.

### Categories and rules
- Uncategorised page: categorise a whole payee group at once, optionally remembering it as a rule.
- Transactions page: correct one row (category, sinking pool), apply to similar rows.
- Rules page: view, re-prioritise, add, delete, re-run (rows you set by hand are never overwritten). Built-in starter rules are copied in once.

### Month, overspend, trends
- Month page: Regular budget vs actual per category and overall (within / over), sinking-pool balances, an Uncategorised line, a reconciliation line, coverage warnings.
- Overspend page: categories ranked by amount and percent over, top payees and largest transactions, month-to-date pace for the current month.
- Trends page: monthly actual vs budget per category and overall, sinking balances (simple built-in charts, no libraries).
- Amounts in AUD, dates dd/mm/yyyy. The footer shows the version.

### Security and offline behaviour
- Listens on 127.0.0.1 only; debug off; a one-time link with a private token starts each session; forms are protected against forged requests; strict Content-Security-Policy; no CDN, fonts, analytics or telemetry.
- The data folder must be outside Documents, Desktop and iCloud; the app refuses otherwise.
- No transaction data in URLs, page titles or logs.

### Limits
- Uploads up to 10 MB; PDFs up to 150 pages; each file is read in a separate process stopped after 30 seconds.
- Months from 1900-01 to 2100-12; anything else shows "not found".
- Only text PDFs (no scans/OCR, no CSV).

### Known issues
- 20 known vulnerabilities remain in click, pdfminer.six and pillow; the fixes need Python 3.10 or later. The app only reads files you choose and listens on your own Mac.
