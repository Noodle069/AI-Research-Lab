# Research 05: PDF parsing spike (R-a)

Main-agent test, 2026-09-30, on the user's real statements (user-approved). Tool: pdfplumber 0.11.8 in a throwaway virtual environment in the session scratchpad (see INSTALLED.md). Output was limited to counts and pass/fail, plus six rows of amounts and balances (no descriptions) to diagnose one sign issue. Nothing was written to the project except this note. Amounts below are not recorded except where noted.

## Bottom line
Coordinate-based parsing (option P1) reconciles on every real file tested, for all five layouts. Feasibility is VERIFIED for amounts, dates and balances. Not tested: descriptions, multi-line descriptions, refunds and foreign currency.

## Results

| Layout | Files | Rows parsed | Check | Result |
|---|---|---|---|---|
| ING Orange Everyday statement | 5 | 103 + 80 + 341 + 316 + 40 = 880 | Per-row running balance (previous balance + signed amount = this balance) | 875 of 875 pass. First row of each file (5) has no previous balance, so it is unchecked. |
| ING short report | 1 | 8 | Per-row chain, seeded by the printed opening balance | 8 of 8 pass |
| Offset account listing | 1 (33 pages) | 878 transactions (+10 month headings) | Per-row chain, seeded by the printed opening balance | 878 of 878 pass |
| Offset home loan listing | 2 (3 and 13 pages) | 24 and 429 transactions (+8 and +14 headings) | Per-row chain, seeded by the printed opening balance | 24 of 24 and 429 of 429 pass |
| NAB credit card | 1 | 11 transactions | Statement-level: sum of CR rows = "Payments & other credits"; sum of DR rows = "Purchases"; opening − payments + purchases = closing | All three pass exactly |

Total per-row balance checks passed: 875 + 8 + 878 + 24 + 429 = 2,214 of 2,214, with 0 failures.

## Facts established (VERIFIED from the user's files)
- **ING statement:** money-out amounts are printed as negative numbers; money-in as positive. Rows are oldest-first (dates never decrease). Every row has exactly one amount and a balance. Dates are dd/mm/yyyy. Continuation lines ("Card ####") have no date and are skipped. My first attempt failed because I treated the printed negative as positive; the per-row check caught it immediately, which shows the gate works.
- **Offset and home loan listings:** columns are right-aligned and match header right edges. Balance is followed by a separate CR or DR token (loan balances are DR, i.e. owed). Row dates are "Mon dd" with no year. A month-and-year heading line (four-digit year) precedes each month's rows, so the year comes from the heading. No statement-period lookup is needed. Rows carry a single amount (never both columns).
- **ING short report:** header Deposit, Withdrawal, Balance; dates "dd Mon yyyy". Small file.
- **NAB card:** no per-row balance. pdfplumber's default word spacing already worked; removing whitespace inside amounts is enough. No special spacing tuning was needed (the garbling seen earlier was PDFKit's extraction, not the file).
- The pdfplumber word coordinates gave stable column assignment across all files with header-derived x positions.

## Not tested (still UNKNOWN)
- Description text: multi-line descriptions, payee extraction, foreign currency, refunds, pending items. Not read or parsed.
- NAB beyond one statement (11 rows); other NAB card and other-bank layouts.
- The first row of each ING file (no prior balance) and cross-file overlap between statements.
- Whether the offset and home loan reports are Macquarie (bank name not printed on inspected lines).
- pdfplumber's outbound network behaviour (R-d): not monitored.
- Runtime with 33-page files was a few seconds (informal); not benchmarked.

## Effect on the decision
- P1 is feasible on the user's real layouts; the largest unknown flagged in architecture/02 is retired for amounts and dates.
- P2 (text-only) is not needed as the primary path, and P3 (Actual plus converter) loses its main advantage of avoiding the parser, since the parser is the shared work.
- The two-gate design (statement-level and per-row) is justified. It caught a real sign error during the spike.
- The parser must treat printed sign per layout (ING negative out; offset uses separate columns; NAB uses CR/DR suffix).
