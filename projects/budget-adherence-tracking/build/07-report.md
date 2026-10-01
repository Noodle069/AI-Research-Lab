# Build 07: slice 6, month dashboard, overspend view, trends (builder report)

Saved as returned by the builder subagent, 2026-10-01. Main-agent verification appended at the end.

Slice 6 is built and stopped there. The full suite passes: `142 passed in 3.73s` (112 existing plus 30 new). No styling pass was done; only a few functional CSS rules were added.

### Built
All paths are under `projects/budget-adherence-tracking/app/`.

| File | What | Serves |
|---|---|---|
| `budget_app/report.py` (new) | All slice 6 logic: budget maths and status, sinking balances and start month, pace, overspend, trends, SVG geometry, coverage issues. Integer cents throughout. | 7, 7a, 7b, 8 |
| `budget_app/__init__.py` | Routes `/month[/<ym>]`, `POST /month/sinking-start`, `/bleeding[/<ym>]`, `/trends`. Two display filters. Invalid `ym` returns 404. | 7, 7a, 8, 9 |
| `budget_app/store.py` | Added a `ym` key to each coverage month (one line). | coverage warning |
| `templates/month.html`, `bleeding.html`, `trends.html`, `_macros.html`, `base.html` | Server-rendered pages and nav links (Month, Overspend, Trends). No script, no inline styles, no external assets. | 7, 7a, 8, 9 |
| `static/app.css` | A few rules for warning box, status colours and SVG chart classes. | 9 |
| `tests/test_slice6.py` (new, 30 tests) | Fake data only. | Acceptance |
| `README.md` | Short note on the new pages. | |

**Definitions, as shown on the pages**
- Regular actual is Regular-pool spend only. Only `flow_type='spend'` counts.
- Overall actual is Regular spend in every category (including 9 and 10) plus all Uncategorised spend. It is compared with the total Regular budget of $10,265.81. Sinking spend is shown separately.
- Status is within under 90%, near 90% to 100%, over above the budget. A zero budget (category 6) with any Regular spend counts as over, and its percent shows "n/a".
- Sinking balance is the monthly set-aside times the months from the start month to this month, minus Sinking-pool spend from the start month. The start month is stored in `meta` under `sinking_start_month` and defaults to the earliest month with data. A blank entry resets it to the default.
- Pace is spent so far (up to today) against budget x days elapsed / days in month. It appears only for the current month, labelled "a pace, not a verdict".
- Reconciliation checks that category lines (regular plus sinking) plus Uncategorised equal a separate direct SUM of the month's spend. Shows OK or MISMATCH; a test confirms it flags a deliberately broken total.
- Coverage warning appears on a month when any account is partial or has no data. A month outside every statement period counts as no data for all accounts. The same warning and a per-month "Partial coverage" tag appear on `/trends`.

**Trends:** months run contiguously from the first to the last month with data. One table plus an SVG bar chart per category and for overall (red bar = over budget, short line = budget). Each category with a sinking pool has a balance table and an SVG line chart. Charts use presentation attributes only, so the CSP is unchanged.

**Overspend view:** `/bleeding/<ym>` shows categories ranked by dollars over, with percent over, the top 5 payees (key, total, count) and the 10 largest single transactions in overspent categories. Payees and descriptions appear on the page only, never in URLs, logs or errors. Uncategorised spend is a line below the ranking, not ranked.

### How to run
- Tests: `cd "projects/budget-adherence-tracking/app" && .venv/bin/pytest -q`
- App: `BUDGET_DATA_DIR=<folder outside Documents/Desktop/iCloud> ./run.sh`, then open the launcher link.

### How to use the new pages
1. **Month:** click "Month" in the nav. It opens the latest month; the arrows move between months that have data. Read the Regular table (budget, actual, budget left, used, status). Rows for categories 9 and 10 appear only when they have spend.
2. **Sinking funds:** below the Regular table. Type a start month such as `2025-03` and Save to change when the running balances begin. Leave blank for the default.
3. **Reconciliation:** the box at the bottom should say OK. If MISMATCH, the month's figures do not add up.
4. **Coverage warning:** if it appears, treat low spending as possibly missing statements. The link goes to the Coverage page.
5. **Overspend:** "Overspend" in the nav, or the link on the Month page. Biggest overspends first, with payees and large transactions. In the current month it also shows the pace table.
6. **Trends:** "Trends" in the nav. Jump to a category from the list at the top. Sinking balances are at the bottom.
7. **Uncategorised:** the "categorise" link on the Month page goes to the Uncategorised queue.

### Real-file sanity run
Temporary database outside the workspace, deleted afterwards. Counts only.
- The folder holds 11 PDFs. 10 imported and 1 was blocked as the known whole-file duplicate. None were rejected. One account per role.
- Months covered: 21 (2025-01 to 2026-09), every month has spend rows.
- Reconciliation held for all 21 months.
- Over-budget categories per month: 0 in 9 months (2025-01 to 2025-06 and 2026-04 to 2026-06), 1 in 9 months, 2 in 1 month and 3 in 1 month. Busiest: 2025-12 (3) and 2026-02 (2). Many come from the 1,055 uncategorised rows plus items not yet routed to Sinking, so not yet meaningful.
- Coverage warnings fired in all 21 of 21 months. Expected with one account per role (statement periods do not span every month). Shows the warning works but has not been checked against the user's real account setup.
- Dashboard query time for all 21 months: month views 0.043 s, overspend views 0.045 s, trends 0.004 s.

### Installs / system changes
None. No new packages. Temporary database and backups deleted; scratch script in the session scratchpad.

### Deviations / blockers
- Charts are inline SVG, not bundled Chart.js (the main agent's instruction).
- Overall actual includes Regular spend in categories 9 and 10, which have no budget. The alternative is to exclude them. Stated on the page.
- Uncategorised spend counts entirely toward the overall Regular figure, even if a row's pool is sinking (Uncategorised rows are always pool regular by default).
- Months with no data between the first and last month are shown as zero rows (flagged by the coverage warning) rather than skipped.
- A new `meta` key `sinking_start_month` is created only when the user sets a start month. No schema change.
- The `/month/sinking-start` form accepts only a `YYYY-MM` value or blank.

### Not tested
- Browser rendering and layout (tests checked HTTP status, CSP, "no script", "no style=", structure).
- The real-file run did not load the pages over HTTP; only the report functions were run.
- Whether the real over-budget counts are right, since 1,055 spend rows are still uncategorised.
- The coverage warning against the user's actual account setup.
- Pace on a real current month (tested only with a patched date).
- Very large databases (trends recomputes balances per month; fine at 21 months).

---
## Main-agent verification (2026-10-01)
- Re-ran `pytest` (see session message; 142 expected).
- No `<script>`, inline `style=` or external URLs in templates or app code other than 127.0.0.1. No database files in the workspace.
- Not verified by the main agent: real-file figures (builder's counts only); browser rendering.
