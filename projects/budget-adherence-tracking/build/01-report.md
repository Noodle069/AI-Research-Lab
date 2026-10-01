# Build 01: slices 1-2 (builder report)

Saved as returned by the builder subagent, 2026-09-30. Main-agent verification appended at the end.

Slices 1 and 2 are built and stopped there. All 17 tests pass, and the parser passes both gates on the 6 real ING statement files in the folder. Approve and save is not built.

### Built
All paths are under `projects/budget-adherence-tracking/app/`.

| File | What it does | MUST |
|---|---|---|
| `budget_app/__init__.py` | Flask app factory with routes `/`, `/import/preview`, `/import/<id>` and discard. Upload and preview are held in memory only. | 4, 5 |
| `budget_app/security.py` | Host allow-list, per-launch token (cookie set via `/enter?t=`), CSRF token plus Origin check on POST, CSP `default-src 'self'; connect-src 'self'`, no-store, no-referrer. | 1, Security |
| `budget_app/schema.sql`, `db.py` | SQLite schema in integer cents. Seeds categories and budgets from the config. | 6 |
| `config/budget_config.json` | 10 categories with Regular and Sinking amounts in cents. Categories 9 and 10 are null. Transcribed from `budget-categories.md`. | 6, 7b |
| `budget_app/datadir.py` | Refuses a data folder under `~/Documents`, `~/Desktop` or iCloud. | Handoff stack |
| `budget_app/parsers/common.py` | Integer cents, explicit dd/mm/yyyy parsing, line grouping. | Parsing rules |
| `budget_app/parsers/ing_statement.py` | ING Orange Everyday parser with both hard gates. | 3, 4 |
| `budget_app/templates/`, `static/app.css` | Home page, rejected page, preview screen. No inline script and no external URLs. | 5, 9 |
| `run.py`, `run.sh`, `README.md`, `.env.example`, `requirements*.txt`, `.gitignore` | Launcher and setup. | Release |
| `tests/` | Tests using fake data only. `fakepdf.py` builds synthetic PDFs. | Acceptance |

**Parser details**
- Column positions come from each page's header row.
- Money out is read as negative. Continuation lines are skipped.
- The statement gate has four checks: opening + printed in + printed out = closing; the sum of in rows equals the printed total in; the sum of out rows equals the printed total out; opening + all rows = closing.
- The row gate chains each row's balance from the printed opening balance, so the first row is checked too.
- Any failure rejects the whole file. Error messages carry only the row number, page and field type.

**Preview screen** shows: date range; counts and totals in and out; opening and closing balance; gate results; an Uncategorised count (all rows for now); a transaction table.

**Real-file check (counts only, nothing copied into the workspace)**
- All 6 ING statement PDFs pass both gates, including the seeded first row. Row counts are 103, 80, 341, 316, 40 and 40. The last two are the byte-identical duplicate pair.
- The 5 non-ING PDFs are rejected as an unrecognised layout. That is correct, because they belong to slice 3.

### How to run
```
cd "/Users/alphakings/Documents/AI Research Lab/projects/budget-adherence-tracking/app"
export BUDGET_DATA_DIR="$HOME/BudgetTrackerData"   # must be outside Documents, Desktop and iCloud
./run.sh                                           # prints http://127.0.0.1:5055/enter?t=<token>
```
Open the printed link in a browser. Tests: `.venv/bin/python -m pytest -q` gives `17 passed in 0.47s`.

The builder also started the real server on 127.0.0.1:5061 and checked it with curl. No token gave 403, `/enter` with the token gave 302, and `/` with the cookie gave 200. `lsof` showed it listening only on 127.0.0.1:5061.

Tests cover: altered amount in every row position fails and names the row; error text contains no amounts or descriptions; wrong closing balance and wrong printed totals fail; unknown layout and corrupt PDF are rejected; the parser makes no network connection (socket connect patched to fail); token, Host, CSRF and Origin checks; CSP present; zero rows in the database after a preview; the data-folder guard.

### Installs / system changes
All installs are in `app/.venv` (created with `/usr/bin/python3` 3.9.6). Nothing was installed system-wide.

| Package | Version |
|---|---|
| Flask | 3.0.3 |
| pdfplumber | 0.11.8 |
| pytest (dev only) | 8.3.5 |

Dependencies pulled in automatically: blinker 1.9.0, cffi 2.0.0, charset-normalizer 3.5.2, click 8.1.8, cryptography 50.0.1, exceptiongroup 1.3.1, importlib_metadata 8.7.1, iniconfig 2.1.0, itsdangerous 2.2.0, Jinja2 3.1.6, MarkupSafe 3.0.3, packaging 26.3, pdfminer.six 20251107, pillow 11.3.0, pluggy 1.6.0, pycparser 2.23, pypdfium2 5.13.0, tomli 2.4.1, typing_extensions 4.16.0, Werkzeug 3.1.9, zipp 3.23.1.

Other changes: temporary scripts and a test data folder are in the session scratchpad only. Remove with `rm -rf app/.venv`.

### Deviations / blockers
- **Source total typo.** `budget-categories.md` prints a Sinking total of 3,096.93, but its category rows sum to 3,095.93. Only 3,095.93 makes Regular + Sinking equal the printed 13,361.74. The builder used the rows (309593 cents) and noted this in the config file. Needs user confirmation.
- **Date order is not a gate.** The handoff says rows are oldest-first, but one real file has a row dated a day earlier than the row above. Its balance chain still passes. Date order is a non-blocking warning on the preview; the balance chain is the ordering authority.
- **Approve and save is a disabled button.** Commit belongs to slice 4, so nothing is written to the database yet. Discard works.
- **Hashes not pinned.** `requirements.txt` has exact versions but no hashes, although the handoff asks for hashes. Doing that needs a wheel download.
- **Chart.js not bundled.** Not needed until slice 6.
- **Preview shows only** the first-line description (continuation lines skipped per spec); "Transfers / duplicates: not checked yet" (slice 4); all rows as Uncategorised (slice 5).
- **Flask 3.0.3 has no TRUSTED_HOSTS.** Implemented the equivalent as a Host check.
- **Data folder is required.** `BUDGET_DATA_DIR` must be set. There is no default, because the handoff says the user chooses it.

### Not tested
- A real browser session: the upload form, the preview layout and the visual design.
- The upload and preview flow with a real statement through the running server. Real files were parsed at the parser level only.
- Offline behaviour under a network monitor, including whether pdfplumber makes outbound connections. Only a socket-patch unit test exists.
- Very large files near the 50 MB limit.
- The 33-page listing runtimes.
- Descriptions on refunds and foreign-currency rows, which the spike also left untested.
- `run.sh` first-run venv creation: it installs from PyPI, so it needs a network connection once.

---
## Main-agent verification (2026-09-30)
- Re-ran `pytest`: 17 passed.
- Sinking rows sum to 3,095.93 and Regular rows to 10,265.81; together 13,361.74, confirming the typo is in the user's source PDF total (3,096.93), not the builder's transcription.
- No external URLs in `budget_app/`, `run.py`, `run.sh` or the README other than 127.0.0.1. No PDFs, databases or real data files inside `app/`.
- Not verified by the main agent: the running app in a browser; the real-file gate results (builder's counts only).
