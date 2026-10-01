# Research 04: shape of the user's real statements

Main-agent observation, 2026-09-30, from the files in `/Users/alphakings/Documents/AI Research Lab/Budget Statements` (user-approved read, 2026-09-30). Only bank identifiers, table headers and file structure were extracted. No names, addresses, account numbers or transactions are recorded here. Evidence label for everything below: VERIFIED (read from the user's own files) unless marked.

## Bottom line
All 11 files are PDFs. There are no CSVs. All are text-based (extractable without OCR). So PDF import is required, not deferred, unless the user can also download CSVs from the banks. Requirement change: PROJECT_STATE said "CSV-first, PDF deferred".

## Files by layout

| Layout | Files | Columns | Dates | Notes |
|---|---|---|---|---|
| ING Orange Everyday, statement | 5 multi-page files (4 to 18 pages) | Date, Details, Money out $, Money in $, Balance $ | dd/mm/yy | Card transactions have a continuation line ("Card <last 4>") after the date row. Spans roughly 30 Dec 2024 to Jan 2026 across files. |
| ING Orange Everyday, short report | 1 file (1 page, 1 Jul to 22 Sep 2026) | Date, Description, Deposit($), Withdrawal($), Balance($) | dd Mon yyyy in header (rows not inspected) | A second ING layout with different column names and order. |
| NAB credit card statement | 1 file (2 pages, 28 Jul to 26 Aug 2026) | Date, Date (processed), reference, description, amount with CR/DR suffix | dd/mm/yy | Text extraction is badly spaced by the PDF's kerning ("Pa ge 1/ 2", "4,8 94.06 CR"). Needs whitespace repair before parsing. Two dates per row. |
| Offset Home Loan Transaction Listing | 2 files (3 and 13 pages) | Date, Description, Debits, Credits, Balance | not inspected | Balance has DR/CR suffix. Header repeats on every page. Bank is not printed on the lines I sampled (LIKELY Macquarie, from the product name; UNVERIFIED). |
| Offset Account Transaction Listing | 1 file (33 pages) | Date, Transaction, Description, Debits, Credits, Balance | "Dec 17" (month-day, no year on the row) | Different header order to the home loan reports. Year must come from the statement period. Includes transfers between the user's own accounts. |

## Design-relevant facts
- Duplicate file: two ING files (`A432…` and `C0B0…`) have identical size and identical first-page content. VERIFIED (same byte size, same page 1 text). Confirms duplicate import protection is needed.
- Statement periods differ (one page to 33 pages; multi-month ranges). Overlaps are likely.
- Balance conventions differ: plain, or suffixed DR/CR. Debits/credits can be separate columns (ING, offset) or a single amount with CR/DR (NAB card).
- Internal transfers between the user's own accounts exist (offset account report). They must be excluded from category spending.
- Home loan offset reports and card payments are not "spending". Account types need a per-account role (spending, credit card, loan, offset).
- Opening and closing balances are printed, so a reconciliation check (opening + in − out = closing) is possible per statement.
- The NAB PDF text is degraded. LIKELY fixable with whitespace-tolerant parsing. Not tested on transaction rows.

## Unknowns
- Whether the banks also offer CSV for these accounts (the user said "csv and pdf" on 2026-09-24). Would remove most PDF parsing risk.
- Whether "Transaction_report" files are Macquarie (product names suggest so; bank name not confirmed).
- Transaction row content and edge cases (multi-line descriptions, foreign currency, refunds): not read.

## Data exposure note
The folder is under `~/Documents`. Critique R1 (VERIFIED, Apple support) says that if iCloud "Desktop & Documents Folders" is on, these files sync to iCloud. Whether it is on for this Mac is UNKNOWN. Not checked.

## Tooling note
No PDF tools are installed on this Mac. Parsing used macOS's built-in PDFKit through a script in the session scratchpad. Nothing was installed.
