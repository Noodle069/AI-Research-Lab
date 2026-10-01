# Build 02: slice 3 (builder report)

Saved as returned by the builder subagent, 2026-10-01. Main-agent verification appended at the end.

Slice 3 is built and stopped there. Approve/commit (slice 4) is not built. All 46 tests pass (`46 passed in 1.64s`), and all 11 real statement files pass both hard gates where the layout allows.

### Built
All paths are under `projects/budget-adherence-tracking/app/`.

| File | What it does |
|---|---|
| `budget_app/parsers/ing_short.py` | ING short report parser. Two gates: statement (opening + rows = closing) and row gate seeded by the "Brought Forward" opening balance. Columns matched by header right edge (12 pt). |
| `budget_app/parsers/nab_card.py` | NAB card parser. Statement gate only (no per-row balance). Whitespace inside amounts removed. |
| `budget_app/parsers/offset_listing.py` | One parser for the offset account and offset home loan listing. Handles both header orders. Two gates: statement gate and row gate seeded by the printed opening balance. Year from month-year headings. |
| `budget_app/parsers/detect.py` | Layout auto-detection. Reads the PDF once; each layout tests its own header. No match gives "Unrecognised layout"; more than one match is rejected as ambiguous. |
| `budget_app/parsers/common.py` | Shared `Row`, `Gate`, `ParsedStatement`, `nearest_edge`, `chain_gate`, and a month map. `Row.balance_cents` can now be None. |
| `budget_app/parsers/ing_statement.py` | Imports shared types from `common.py`; has a `detect()` function. Behaviour unchanged. |
| `budget_app/__init__.py` | Uses `detect.parse_pdf`. |
| `budget_app/templates/preview.html` | Balance cell can be blank; "Inferred years" says when the year came from month headings. |
| `tests/fakepdf.py`, `tests/test_layouts.py` | New fake-data builders and 29 new tests. |

Rules across all parsers: any failure rejects the whole file; errors name only row number, page and field type; all amounts are integer cents; month-year headings are never treated as transactions.

Tests per layout (ING short, NAB, offset account, offset loan): valid file passes all gates; altered amount in every row position fails (error text contains no amounts or descriptions); wrong closing balance fails; wrong printed totals fail; preview screen works with 0 database rows after preview; whole-file rejection through the app; no network connection.

### How to run
```
cd "/Users/alphakings/Documents/AI Research Lab/projects/budget-adherence-tracking/app"
.venv/bin/python -m pytest -q
export BUDGET_DATA_DIR="$HOME/BudgetTrackerData"
./run.sh
```

### Installs / system changes
None. No packages were installed. Temporary scripts are in the session scratchpad only.

### Real-file results (counts and pass/fail only)
Detection was correct for all 11 files. Via the Flask preview route, 11 of 11 returned a redirect to a preview showing PASS and no FAIL.

| Layout | Files | Rows | Result |
|---|---|---|---|
| ING statement (regression) | 6 | 103, 80, 341, 316, 40, 40 | 6 of 6 pass both gates |
| ING short report | 1 | 8 | both gates pass |
| NAB card | 1 | 11 | statement gate passes; no row gate on this layout |
| Offset home loan | 2 | 24 and 429 | 2 of 2 pass both gates |
| Offset account | 1 | 878 | both gates pass |

- **ING short report:** withdrawals printed negative, deposits positive (same as the ING statement). No printed in/out totals, so the statement gate is opening + rows = closing.
- **NAB card:** CR rows equal printed payments; DR rows reconcile with printed purchases; opening and closing reconcile. The gate also includes the printed "Interest / & other charges" line (DR rows = purchases plus charges). This file passed.

### Deviations / blockers (differences from research/05)
- **Offset opening balance has no CR/DR suffix.** Sign is taken from the operator printed before "Total debits": "+" means owed (loan, DR), "-" means held (CR). The in-listing opening line is also checked against the summary. Wrong inference would fail the gates, not guess. Held on all 3 real listings; inferred from 3 files.
- **A zero balance prints with no CR/DR marker.** The parser accepts an unmarked balance only when it equals 0. Any other missing marker rejects the file.
- **NAB amounts:** many rows have no suffix. No suffix is read as DR (purchase); only an explicit CR is a credit. Reconciled on the real file.
- **NAB summary layout:** two "Closing balance" texts; the parser reads the "=" line in the summary block.
- **Offset Description column:** on the account layout the Transaction column text is part of the stored description.
- **ING short report:** row dates are three words, "dd Mon yyyy" (research/04 said not inspected).
- **Date order** stays a non-blocking warning.

### Not tested
- A real browser session and the look of the preview page for the new layouts.
- Runtime on the 33-page listing through the running server.
- Refunds, foreign currency and multi-line descriptions beyond skipping continuation lines. Descriptions were not compared with the real files.
- NAB statements other than the one 11-row file. Non-zero interest line covered only by a fake-data test.
- A listing whose printed opening balance is unmarked and flipped relative to the operator rule.
- Offline behaviour under a network monitor. Only the socket-patch unit test exists.

---
## Main-agent verification (2026-10-01)
- Re-ran `pytest`: 46 passed.
- No external URLs in `budget_app/`, `run.py`, `run.sh` other than 127.0.0.1. No PDFs or databases inside `app/`. Parsers present: ing_statement, ing_short, nab_card, offset_listing, detect.
- Not verified by the main agent: real-file results (builder's counts only); running app in a browser.
