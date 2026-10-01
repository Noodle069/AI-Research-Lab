# Build 08: fix round for tester defects T-1 to T-4 and dependency upgrade (builder report)

Saved as returned by the builder subagent, 2026-10-01. Main-agent verification appended at the end.

All six fix-round items are done except the dependency upgrade, where only Flask could move. Full suite: `192 passed` in about 27 s, no xfail left. It was 182 passed and 4 xfailed before.

### Built
- **T-3, month overflow:** `report.py` now has a 1900-01 to 2100-12 window (`YM_MIN`, `YM_MAX`) and a `ym_ok()` check. `ym_add` raises ValueError outside the window. `ym_range` has a hard guard of 2413 iterations and also raises ValueError outside the window. `ym_bounds` and month navigation are guarded at the window edges. `data_months` ignores out-of-window dates. `/month`, `/bleeding` and the sinking-start `back` field return 404 or redirect safely for any month outside the window. The sinking-start form rejects a month outside the window. `YM_RE` in `categorise.py` is now ASCII-only and uses `\Z` (before, a trailing newline or Unicode digits matched).
- **T-1, non-ASCII token or cookie:** `security.py` has a `same()` helper that compares UTF-8 bytes, used for the token, cookie and CSRF checks, so these now give 403.
- **T-4, bounded integers:** path ids use `<int(min=1,max=2147483647):...>` (oversized ids give 404). Form ints (`_int`, `categorise.parse_category`, the account choice in `store.validate_selection`) and `cat`, `cat_filter` accept only 1 to 9 ASCII digits. `page` is clamped to 1 to 100000 on `/transactions` and `/transfers`. A safety-net OverflowError handler returns 400. Every int-taking route was scanned.
- **T-2, parse time:** upload limit is now 10 MB. `detect.parse_pdf_bounded` checks size and the `%PDF-` header first, then parses in a subprocess (new file `parsers/worker.py`) with a 30 s wall-clock timeout; the worker is killed on timeout and the upload gets a clean 422. `parse_pdf` rejects PDFs over 150 pages before any text extraction. `__init__.py` calls `parse_pdf_bounded`.
- **Tests:** xfail markers for T-1, T-3, T-4 removed; T-3 split into a `ym_add` bounds test and a 404 test. `test_size_limit_boundary_10mb` replaces the near-50 MB test. `/month/2999-12` now expects 404 (intended). New `tests/test_fixround.py` covers every int field and path, a junk file, a non-PDF file, the worker timeout using a sleeping child process, and the page cap.
- **README:** limits documented, plus the rollback note for the Flask upgrade.

### How to run
```
cd "projects/budget-adherence-tracking/app"
./run.sh
.venv/bin/python -m pytest -q    # 192 passed, about 27 s
```
The suite is slower (9 s to 27 s) because every upload parse now starts a worker process.

### Installs / system changes (all inside `app/.venv`)

| Package | Old | New |
|---|---|---|
| Flask | 3.0.3 | 3.1.3 |

Nothing else changed. `pip check` is clean. `requirements.txt` pins `Flask==3.1.3`; the old file is saved as `app/requirements.txt.bak-pre-upgrade` for rollback.

Could not upgrade on Python 3.9.6 (fixed versions need Python >=3.10): click (8.3.3 unavailable; 8.1.8 is highest compatible), pdfminer.six (20251230 unavailable; 20251107 highest), pillow (12.1.1 to 12.3.0 unavailable; 11.3.0 highest). Werkzeug, Jinja2 and itsdangerous did not need to change. A newer Python (3.10 or later) would allow the other upgrades. pdfplumber 0.11.8 still works: all 11 real files pass and the suite is green.

**pip-audit** (throwaway venv, package names and versions only): 20 vulnerabilities remain in 3 packages, down from 21 in 4.

| Package | Version | Advisories |
|---|---|---|
| click | 8.1.8 | 1 (PYSEC-2026-2132, fix 8.3.3) |
| pdfminer.six | 20251107 | 1 (PYSEC-2026-1761, fix 20251230) |
| pillow | 11.3.0 | 18 |

The Flask advisory is gone. All three remaining packages need Python 3.10 or later to fix.

### Deviations / blockers
- The three Python 3.9 limits above.
- Timeout choices: the 30 s timeout is arbitrary (slowest real file parsed in 2.24 s). The worker has no memory cap (`RLIMIT_AS` is unreliable on macOS). The timeout test uses a sleeping child process rather than a hostile PDF. The 9 MB junk file is rejected well inside the limit.
- The month window rejects any data dated outside 1900 to 2100 from the dashboards.

### Not tested
- The tester's near-50 MB case: now a 413, not re-run.
- The sandboxed network-denied run and lsof checks were not repeated by the builder (the main agent repeated the sandbox run; see below).
- Browser rendering.
- A live full run of `./run.sh` with a real import, and a worker timeout against a genuinely hostile PDF.
- Real-file regression: only `detect.parse_pdf`, no database, on the 11 PDFs in `Budget Statements`: 11 of 11 passed both gates, 0 rejected. Nothing copied.
- A stray `statement.textClipping` sits in that folder; it was not read.

---
## Main-agent verification (2026-10-01)
- Re-ran `pytest`: 192 passed in 26.5 s.
- `pip list` confirms Flask 3.1.3, pdfplumber 0.11.8, click 8.1.8, pillow 11.3.0; `requirements.txt` pins match; backup file exists.
- Repeated the offline test: the real server started inside the network-denied `sandbox-exec` profile (loopback only) and `tests/live_driver.py` ran inside the same sandbox: 75 requests, 0 failures. The only socket of the server process was the listener on 127.0.0.1:5093. Temporary data folder deleted afterwards.
- Not verified by the main agent: the real-file regression (builder's figures only); vulnerability audit results.
