# Budget adherence tracker (local only)

Flask + SQLite on 127.0.0.1. No network calls. Data lives in `BUDGET_DATA_DIR`, which must be outside
`~/Documents`, `~/Desktop` and iCloud.

## Run
```
export BUDGET_DATA_DIR="$HOME/BudgetTrackerData"
export BUDGET_BACKUP_KEEP=20      # optional, default 20
./run.sh                           # prints a link with a per-launch token
```
Dependencies are installed from `requirements.lock` (exact versions with hashes, `--require-hashes`) on first run;
`requirements.txt` holds the same pins without hashes.

Tests: `.venv/bin/python -m pytest -q`

## Import flow
Upload a PDF, choose or create an account (your own name, never an account number) and confirm its role,
press "Update preview" to see duplicate and transfer counts, then "Approve and save". Nothing is written before that.

Limits: uploads up to 10 MB, PDFs up to 150 pages, and each file is read in a separate worker process that is
stopped after 30 seconds (the file is then rejected, nothing imported). Months are accepted from 1900-01 to 2100-12;
anything else gives "not found". Real statements are well under 1 MB.

Roll back the Flask upgrade: `requirements.txt.bak-pre-upgrade` holds the previous pins (Flask 3.0.3).

## Backups and restore
Before every import the app copies `budget.db` to `BUDGET_DATA_DIR/backups/budget-<timestamp>.db`
and keeps the newest `BUDGET_BACKUP_KEEP` copies. There is no cloud backup. For an external copy, copy that folder yourself.

To undo an import or restore:
1. Stop the app (Ctrl+C).
2. Pick a backup (the newest one is the state just before the last import).
3. `cp "$BUDGET_DATA_DIR/backups/<chosen file>" "$BUDGET_DATA_DIR/budget.db"`
4. Start the app again.

## Categorisation (slice 5)
- Uncategorised: spending with no category, grouped by payee; categorise a whole group and optionally remember it as a rule.
- Transactions: correct one row (category, pool), optionally apply to similar rows and remember the merchant.
- Rules: view, re-prioritise (lower number first, first match wins), delete, add, re-run on rows you have not set by hand.
- Built-in generic rules come from `config/seed_rules.json` and are copied into your database once. Your corrections are never overwritten.
- For slice 6: `budget_app.categorise.month_totals(conn, 'YYYY-MM')` returns spend per category and pool plus the overall total.

## ING descriptions now include the merchant
The ING Orange Everyday statement parser keeps the merchant line under each row (description = first line + merchant line(s);
the "Date ... Card ####" line is left out). The description is part of the duplicate key (date + amount + description), so
rows saved by an older build (first line only) do NOT match the same rows re-imported now: they would be saved a second time.
If your database already holds ING rows from an older build:
1. Stop the app and copy `budget.db` somewhere safe (a backup is also made before each import).
2. Delete `budget.db` (and the old backups if you want a clean start), start the app and re-import the ING statements. Nothing is lost
   because the PDFs are the source; only category corrections and hand-set flows on those rows are redone.
3. Do not re-import on top of old ING rows without step 2, or spending is counted twice.

Checked against real files: the card-detail line prints its date as dd/mm/yy (two-digit year), not dd/mm/yyyy; the parser now
excludes both forms. Real line pitch is about 10.3 points (well inside the 16-point limit).

## Slice 6 pages (function first, plain layout)
- `/month` (latest month with data) and `/month/YYYY-MM`: Regular budget vs actual, Sinking balances, Uncategorised line, reconciliation line, coverage warning. Set the sinking start month on this page.
- `/bleeding` and `/bleeding/YYYY-MM`: overspent categories ranked, top payees, largest transactions, month-to-date pace (current month only).
- `/trends`: monthly actual vs budget per category and overall (inline SVG, no libraries), sinking balance per category.
