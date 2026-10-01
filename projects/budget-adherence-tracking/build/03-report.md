# Build 03: slice 4 (builder report)

Saved as returned by the builder subagent, 2026-10-01. Main-agent verification appended at the end.

Slice 4 is built and stopped there. `.venv/bin/python -m pytest -q` gives `64 passed in 2.23s` (46 earlier plus 18 new in `tests/test_slice4.py`). Not run in a browser.

### Built
All paths are under `projects/budget-adherence-tracking/app/`.

| File | What changed | Serves |
|---|---|---|
| `budget_app/store.py` (new) | Accounts, duplicate matching, atomic commit, backups, transfer detection, coverage | MUST 5; SHOULD items |
| `budget_app/schema.sql`, `db.py` | Adds `transactions.flow_type` (spend, income, transfer, savings) and `flow_user_set`. Adds `imports.rows_in_file` and `duplicates_skipped`, a `transfer_candidates` table and a unique account name. `db.py` adds missing columns to a slice 1-3 database. The unused `is_excluded` column is gone from new databases. | MUST 5; SHOULD items |
| `budget_app/__init__.py` | New routes: `/import/<pid>/check`, `/commit`, `/import/done/<id>`, `/coverage`, `/transfers`, plus confirm, reject and flow override. File hash checked at upload. `create_app(..., backup_keep)` sets the backup count. | MUST 5; SHOULD items |
| `templates/preview.html`, `done.html`, `coverage.html`, `transfers.html`, `base.html`, `home.html`; `static/app.css` | Account picker, duplicate and transfer counts, per-row "duplicate, skipped" status, coverage table, transfer review lists, nav links | MUST 5; SHOULD items |
| `run.py`, `.env.example` | `BUDGET_BACKUP_KEEP` (default 20; invalid or below 1 falls back to 20) | Backups |
| `README.md` | Run instructions, import flow, restore steps | Backups |
| `tests/test_slice4.py` | Fake-data tests | Acceptance |

**How each item works**
- **Accounts:** the user picks an existing account or creates one, and confirms the role (defaulted from the layout). A role that differs from the saved one is refused. A new name with 6 or more digits is refused as a possible account number.
- **Commit:** "Approve and save" is enabled only after "Update preview" with an account chosen. If the account choice changed since the last preview, the commit redirects back and writes nothing. Only a statement that passed every check can be saved. One transaction covers the account, the import, every row and the transfer candidates; any failure rolls back everything, and the user sees only a generic message.
- Flow defaults: Spending: out = spend, in = income. Credit card: out = spend, in = transfer (card repayment). Loan: out = transfer, in = transfer. Offset: out = transfer, in = transfer.
- **Duplicates:** a file whose hash was already imported is blocked at upload (batch number and date only). Otherwise matching is per account on date + cents + description over the statement's date range, as a multiset. Balance is never in the key. The preview shows duplicate count, new-row count and per-row status. A statement with no new rows cannot be committed.
- **Backups:** before every write, SQLite's online backup copies the database to `BUDGET_DATA_DIR/backups/budget-<timestamp>.db` (mode 0600). Newest N kept. Blocked imports make no backup. If the backup fails, the import is aborted.
- **Transfers:** a pair is equal and opposite amounts in different accounts within 3 days, matched nearest date first, each row used once. An exact same-day pair is auto-marked as transfer and listed on `/transfers`. Anything else is only a suggestion and stays counted as spend until confirmed. The user can confirm, or reject (a rejected auto-mark returns to the role default). Any row's flow can be changed in the "Rows not counted as spending" list. Category spending is intended to count `flow_type = 'spend'` only; category and budget views are later slices, so nothing reads this yet.
- **Coverage (`/coverage`):** per month and account, the first and last date covered, the transaction count, and "part of month" when the dates do not span the month. No descriptions shown.

### How to run
```
cd "/Users/alphakings/Documents/AI Research Lab/projects/budget-adherence-tracking/app"
export BUDGET_DATA_DIR="$HOME/BudgetTrackerData"
./run.sh
.venv/bin/python -m pytest -q
```

### Tests
Fake data only. Commit and accounts (integer cents, flow type, batch id; nothing written before approval; account-number-like name and role mismatch refused; manual flow override sticks). Duplicates (byte-identical file blocked with batch number and date, no contents; overlap dedupe skips 3 rows and keeps two identical same-day rows plus a new third; fully overlapping statement blocked; dedupe is per account). Atomic rollback (failure on the 3rd row leaves 0 rows in transactions, imports and accounts; error shows no descriptions). Backups (exists before the write and holds 0 transactions; pruning keeps newest N; blocked import makes no backup; setting default and invalid handling). Transfers (same-day pair auto-marked; 2-day pair suggestion; 4-day pair not matched; same-account rows never paired; confirm/reject; role defaults). Coverage (dates, "part of month", "No data", no descriptions).

**Real-file run:** temporary folder outside the workspace, deleted afterwards, counts only. All 11 real files went through the running app's upload, check and commit. The 6 ING files and the short report saved as 8, 103, 80, 341, 316 and 40 rows. The seventh ING file was refused at commit because all 40 rows were already saved (the two 40-row files were not byte-identical, so the hash block did not fire, but every row matched). NAB saved 11 rows, the two loan listings 24 and 429, the offset account 878. Total 2,230 transactions in 10 batches, 10 backups. 62 same-day transfer pairs auto-marked and 15 suggestions. Flow counts: 770 spend, 67 income, 1,393 transfer. `/coverage` and `/transfers` both returned 200.

### Installs / system changes
None. No packages installed. The scratch run script is in the session scratchpad only.

### Deviations / blockers
- **Offset and loan rows default to transfer.** Followed the brief literally. In the real run the offset account and loan listings account for most of the 1,393 transfer rows. If the user pays bills directly from the offset, those rows are hidden from spending until overridden on `/transfers` (100 rows per page). Decision for the user: keep that default, or make offset accounts sign-based like spending.
- **Credit card credits default to transfer.** A card refund is excluded until overridden to spend on `/transfers`.
- **Coverage is date-based.** Uses each statement's first and last transaction dates because the parsers do not read a printed statement period. A statement with a quiet last few days shows as "part of month".
- **The preview needs a second click.** Duplicate and transfer counts appear after "Update preview" (no client-side script; CSP unchanged).
- **The transfer count on the preview is only against saved data.** A same-day pair counted as auto-marked can end up a suggestion at commit if the other side was already set by the user.
- **A zero-new-row statement makes no import record**, so its file hash is not stored.

### Not tested
- A real browser session and the look of the new pages.
- The hash block against a real byte-identical file (fake-data test only).
- The DB upgrade from a slice 1-3 database.
- Concurrent imports from two browser tabs.
- Offline behaviour under a network monitor.
- The restore procedure in the README, end to end.

---
## Main-agent verification (2026-10-01)
- Re-ran `pytest`: 64 passed.
- No database, backup or PDF files inside the workspace. `~/BudgetTrackerData` does not exist (the temp folder was deleted). No external URLs in app code other than 127.0.0.1.
- Not verified by the main agent: the real-file counts (builder's figures only); the app in a browser.
