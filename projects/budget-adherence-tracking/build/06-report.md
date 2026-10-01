# Build 06: ING merchant line (builder reports, two runs)

Saved as returned by the builder subagent, 2026-10-01. Two runs: (1) parser change and tests, (2) real-file check after the main agent supplied the approved folder path. Main-agent verification appended.

## Run 1: parser change (no real-file check; run blocked by the safety check after a wide folder scan)
- `budget_app/parsers/ing_statement.py`: description = first line + merchant continuation line(s), joined by single spaces, whitespace normalised. The "Date dd/mm/yyyy Card ####" line, or a bare "Card ####", is excluded and ends that row's continuation lines. The next dated row starts a new row. Gates unchanged. 16-point gap limit assumed.
- `ing_short.py`, `rules.py`: not changed.
- `tests/test_ing_merchant.py` (new, 9 tests): merchant line, no merchant line, two continuation lines, Card line excluded, no merging of next row, gates, altered amount fails with no description in errors, payee keys, identical same-day purchases kept, overlap dedupe, old first-line-only rows re-imported as new rows (documented mismatch).
- `README.md`: section "ING descriptions now include the merchant" (re-importing over old-description rows saves them twice; safe path: back up `budget.db`, delete it, re-import ING PDFs; nothing real saved, so no migration).
- 111 tests passed. No installs. The first scan listed one file name in Downloads (`ING.pdf`) and printed no content.

## Run 2: real-file check (folder: Budget Statements only; counts only)

### Result
The real files showed one wrong parser assumption, which was fixed. The 16-point gap is fine: real line pitch is about 10.3 points. The wrong assumption was the card-detail line: real files print it as "Date dd/mm/yy Card ####" with a two-digit year. The old pattern only accepted dd/mm/yyyy, so that line was absorbed into the description of every row that has one. Before the fix, 69 of 103 rows in file 1 carried the card text; the other ING files were similar. The gates still passed, because they ignore descriptions. After the fix, no row carries card-detail text.

### Built
- `app/budget_app/parsers/ing_statement.py`: `_CARD_LINE` now accepts a 2- or 4-digit year.
- `tests/fakepdf.py`: fake card line prints dd/mm/yy; line pitch 10.3.
- `tests/test_ing_merchant.py`: new test for both year forms and for not matching merchant text.
- `README.md`: two-line note on the real card-line format.
- Test run: 112 passed.

### Findings (counts only)
1. ING statement files after the fix:

| file | rows | both gates | rows with 0 / 1 / 2+ cont lines |
|---|---|---|---|
| 1 | 103 | pass | 11 / 91 / 1 |
| 2 | 80 | pass | 17 / 63 / 0 |
| 3 | 341 | pass | 22 / 304 / 15 |
| 4 | 316 | pass | 22 / 288 / 6 |
| 5 | 40 | pass | 2 / 38 / 0 |
| 6 | 40 | pass | 2 / 38 / 0 |

Absorbed text: none found. Description length is 53-58 at the median, 73 at the maximum; none over 100 characters; none contains statement boilerplate words, "Card" or "Date". The 22 rows with 2+ continuation lines have lengths 65-73.

2. ING short report (1 file, 8 rows, both gates pass): every row and description is on a single line; no two-line problem; nothing changed. Only 8 rows available.
3. The two 40-row ING files: all 40 rows match on date, amount and description, so they are fully identical. Importing the second is blocked with "Every row already saved" (rejected as a whole-file duplicate, not skipped row by row).
4. After importing all 11 PDFs (one account per layout role, via `store.commit_import`): one file blocked as above; every other file imported with no duplicates skipped (8-row short report, statements 1-5, NAB card 11 rows, offset listings 24, 429 and 878).

| metric | previous | now |
|---|---|---|
| spend rows | 1,751 | 1,751 |
| spend rows with a payee key | 1,002 (derived) | 1,692 |
| spend rows with no payee | 749 | 59 |
| categorised spend rows | 310 (17.7%) | 696 (39.7%) |
| Uncategorised payee groups | 194 | 292 |

| role | spend rows | with payee key | categorised |
|---|---|---|---|
| spending | 762 | 709 | 391 (51.3%) |
| offset | 981 | 975 | 302 (30.8%) |
| credit_card | 8 | 8 | 3 (37.5%) |

Queue: 1,055 spend rows uncategorised, in 292 payee groups plus 59 rows with no payee. More groups because far more rows now have a key.

### Installs / system changes
None. The temporary database and backups were deleted. Throwaway analysis scripts removed. No real text stored anywhere.

### Not tested
- Whether the assignment of real files to accounts matches the user's (by-role figures assume one account per role).
- Cross-file row overlap between different ING statements (none skipped, so none detected).
- The web import UI with the real files.
- Whether the new descriptions make the seed rules match better or worse (only coverage counts measured).

---
## Main-agent verification (2026-10-01)
- Re-ran `pytest`: 112 expected (see session message).
- No database files in the workspace.
- Not verified by the main agent: the real-file counts (builder's figures only).
