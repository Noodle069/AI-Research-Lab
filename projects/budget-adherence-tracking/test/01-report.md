# Test 01: tester report

Saved as returned by the tester subagent, 2026-10-01 (second message after a turn-limit stop). Main-agent verification appended at the end.

### Verdict
**PASS WITH RISKS.** MUST 1 (nothing leaves the computer) is proven with real evidence. MUST 2-10 pass on fake data. No BLOCKER and no gate, rollback or duplicate-handling failure. One MAJOR robustness defect and three MINOR ones, all in input handling. None touches the data or offline guarantees. Fix T-3 before release.

Suite result: `182 passed, 4 xfailed`. The 4 xfails are strict tests that pin defects T-1, T-3 and T-4. They turn red when the defect is fixed, so the xfail markers must then be removed.

### MUST 1 evidence (nothing leaves the computer)

| Check | Method | Result |
|---|---|---|
| a. Full flow under a network-denied sandbox | `sandbox-exec` with `(allow default)(deny network*)` plus loopback-only allows. Proven first: a probe could not connect to 1.1.1.1 or 93.184.216.34, could not resolve DNS, could not send UDP to 8.8.8.8, and could use loopback. | Pass. The real `run.py` server started inside the sandbox. `tests/live_driver.py`, also sandboxed, made 75 HTTP requests with 0 failures: all 5 fake layouts through preview, account creation and commit, a duplicate-file block, an altered-amount rejection and a discard, then every GET and POST route (categorise, rules, transfers, month, bleeding, trends, coverage). Reconciliation line OK. |
| b. Sockets of the running server (unsandboxed) | `lsof -nP -a -p PID -i` sampled during the same 75-request run (16 samples). `nettop -p PID` in tcp and udp modes for 40 s. | Only socket: the listener on `127.0.0.1:5072` plus loopback clients. nettop: one row, `tcp4 127.0.0.1:5072<->*:* on lo0`. UDP: zero rows, so no DNS or UDP 53. No non-loopback socket or listener. |
| c1. Static scan | `test_no_external_urls_scripts_or_inline_styles_in_templates_and_static`, `test_only_local_assets_referenced`, `test_no_networking_imports_in_app_code` | Pass. No http(s) or protocol-relative URL, `<script>`, `<style>`, inline `style=`, inline handlers, `@import`, CSS `url()`, iframe or `javascript:` in any template or static file. No socket, urllib, requests, http.client, smtplib or ssl import in app code. Every href and src is a `url_for`. |
| c2. Headers on every route | `test_every_get_route_has_security_headers_including_errors` | Pass on all GET routes from `app.url_map`, plus static, 404 and error pages. CSP has `default-src 'self'`, `connect-src 'self'` and `script-src 'self'`, no `unsafe`. Also `Cache-Control: no-store`, `Referrer-Policy: no-referrer`, nosniff, X-Frame-Options DENY. |
| c3. Host, Origin, CSRF and cookie on all 14 POST routes | `test_every_post_route_rejects_missing_or_bad_credentials` | Pass. Each fails (403, or 400 for a bad Host) with no Origin, a foreign, `null`, https, wrong-port or look-alike Origin, no CSRF, a wrong or upper-cased CSRF, a wrong Host, or no session cookie. CSRF in the query string is refused, GET cannot change state, and every GET route needs the cookie and Host. |
| Bind | `test_run_py_binds_loopback_and_debug_off` | Pass. Binds `127.0.0.1`, `debug=False`, no reloader, no `0.0.0.0` anywhere. |

Wi-Fi was not turned off and did not need to be: a sandbox that denies the network is stricter evidence.

### Requirement coverage

| MUST | Test | Result |
|---|---|---|
| 1 Offline | Sandbox run, lsof/nettop, static scan, existing socket-patch test | PASS |
| 2 Text PDF import | Live flow, 5 fake layouts | PASS |
| 3 Layouts | Each layout through HTTP preview and commit (live driver, `test_layouts.py`) | PASS |
| 4 Gates | Altered amount in every row position rejected for each layout, nothing written. Wrong closing and wrong printed totals. Unknown layout, corrupt, zero-byte, truncated and blank-page PDFs rejected (422/400). | PASS. Error text has no `FAKE` and no `\d+\.\d\d`. A rejected file leaves 0 rows, 0 imports and no backup. |
| 5 Preview before commit | Existing tests plus live run. Nothing written until commit. | PASS |
| 6 Categories | Seed config totals 1,026,581 regular and 309,593 sinking (cents). User-set rows survive rerun and reimport. | PASS |
| 7 / 7a / 7b | Independent-oracle month maths: over at budget+1c, within at budget-1c, uncategorised counted in overall, income excluded, reconciliation OK. Existing tests for sinking balance, ranking, pace. | PASS |
| 8 Stats and trends | Live `/trends`; existing slice 6 tests | PASS |
| 9 Readable, AUD, dd/mm/yyyy | Transactions page shows dd/mm/yyyy and no ISO dates. Browser rendering not tested. | PASS (rendering not tested) |
| 10 $0 | pip-audit installed only in a throwaway venv; no paid tools. Claude usage assumed covered by an existing subscription. | PASS |
| SHOULD: duplicates | Three identical same-day rows all survive. Re-exported file with same rows but different bytes blocked (409). Overlap dedupe per account. | PASS |
| SHOULD: atomic rollback | Existing test, plus 2 concurrent commits of the same preview save once. Two overlapping files committed concurrently leave no duplicates; integrity check OK. | PASS |
| SHOULD: backups and restore | README `cp` restore procedure run on a fake DB: rows 3 to 2, pages work, re-import of the undone file works. `integrity_check` ok, backups mode 600, folder 700. | PASS |
| SHOULD: transfers and coverage | Existing tests; live confirm, reject and flow routes | PASS |
| Escaping | `<script>`, `<img onerror>`, SQL, `{{7*7}}` and an HTML account label via PDF description and form fields: tables intact, output escaped on every page, templates not evaluated. | PASS |
| Month URLs | 11 odd values (`9999-99`, `2025-13`, `' OR 1=1`, `%00`, CRLF payload) all give 404, never 500 | PASS |

### Defects

| ID | Severity | Steps | Expected / actual |
|---|---|---|---|
| T-3 | MAJOR | With any data present, open `/month/9999-12`. `report.ym_add("9999-12", 1)` returns `"10000-01"`, which string-compares below `"9999-12"`, so `ym_range` never ends. Not run for real (would exhaust memory); a unit test pins the cause. `/month/2999-12` works. | Expected 404 or an empty month. Actual: infinite loop with unbounded memory growth in `sinking_balances`. Requires the user to open the URL (cookie is SameSite Strict). Fix: cap the year to the data range plus or minus N, or 404 outside it. |
| T-2 | MINOR | Upload a malformed PDF-like file of about 49 MB (`%PDF-1.4` plus junk). | Expected quick rejection. Actual: parse time grows faster than file size (4 MB 0.4 s, 8 MB 1.5 s, 16 MB 4.7 s, 49 MB still not finished after 200 s). The 50 MB limit does not bound time, and the parser thread is stuck. Fix: page or time cap, or lower the limit. Real statements are small. |
| T-1 | MINOR | `GET /enter?t=caf%C3%A9`, or a non-ASCII `budget_session` cookie. | Expected 403. Actual 500 (`hmac.compare_digest` TypeError, `security.py` lines 30 and 35). No data exposed. Fix: compare `.encode()` bytes. |
| T-4 | MINOR | `POST /transactions/1/category` with `category=999999999999999999999`; `GET /transactions?page=99999999999999999999` and `?cat=999999999999999999999`. | Expected 400 or clamped. Actual 500 (SQLite OverflowError). Fix: bound the integers. |

Observations, not defects:
- A user-authored regex rule such as `(a+)+$` could stall a rules re-run on a long description. Self-inflicted; not demonstrated. Descriptions longer than about 25 characters overrun the fixed columns, so the gate safely rejects those PDFs.
- `budget.db` is mode 0644, but the parent data folder is 0700, so it is protected.

### Dependency check
- `.venv` holds Flask 3.0.3, pdfplumber 0.11.8, pdfminer.six 20251107, pillow 11.3.0, Werkzeug 3.1.9, Jinja2 3.1.6, click 8.1.8 and pytest 8.3.5; all packages pinned in `requirements.txt` (18 pins, plus dev pins).
- Flask and pdfplumber pinned exactly (`==`). No hashes pinned (0 `--hash` entries).
- `pip-audit -r requirements.txt --no-deps` (throwaway venv; sends package names and versions only) found **21 known vulnerabilities in 4 packages**:
  - flask 3.0.3: PYSEC-2026-2151, fixed in 3.1.3.
  - click 8.1.8: PYSEC-2026-2132, fixed in 8.3.3.
  - pdfminer.six 20251107: PYSEC-2026-1761, fixed in 20251230.
  - pillow 11.3.0: 18 advisories, fixed in 12.1.1 to 12.3.0.
- Exploitability not triaged. The app is localhost-only and the tests did not exercise Pillow image paths.
- Upgrades may be constrained by Python 3.9.6 (for example Pillow 12 may need Python 3.10 or later; not verified). Revisit pins before release.

### Real-file regression (counts only)
11 PDFs from the Budget Statements folder, parsed through `parse_pdf` only (no commit, no data written): **11 passed both gates, 0 rejected.** Layouts: ING statement 6, ING short 1, NAB 1, offset/loan 3.

### Not covered
- Browser rendering and visual checks (charts are inline SVG, not Chart.js).
- Whether the real files import and commit end to end, and the real-data category counts (only parse and gates run).
- Wi-Fi off, DNS or mDNSResponder logs, and a third-party monitor such as LuLu; the sandbox plus lsof and nettop were used instead. lsof samples are periodic, so a very short-lived socket could be missed outside the sandbox; the sandbox run closes that gap.
- Pace on a real current date; a real two-browser-tab test (concurrency simulated with threads on the Flask test client).
- Exploitability of the audited vulnerabilities.
- `run.sh` first-run `pip install`, which needs the internet once by design.

### Installs / system changes
- pip-audit and its 29 dependencies, in the throwaway venv `scratchpad/auditenv`. Remove with `rm -rf` of that venv.
- Scratch folders in the scratchpad; data folders deleted.
- No application code, system settings or `app/.venv` changes.

### Files written
- `app/tests/test_tester_security.py`
- `app/tests/test_tester_functional.py`
- `app/tests/live_driver.py` (not collected by pytest; run against a live server)

### Commands run
- `cd app && .venv/bin/python -m pytest -q`: 182 passed, 4 xfailed in about 9 s (142 existing plus 40 new).
- Sandbox profile `deny.sb`: `(version 1)(allow default)(deny network*)(allow network-bind (local ip "localhost:*"))(allow network-inbound (local ip "localhost:*"))(allow network-outbound (remote ip "localhost:*"))`. A broader `network*` loopback allow turned out to allow everything, so it was tightened.
- `sandbox-exec -f deny.sb .venv/bin/python run.py`, then `sandbox-exec -f deny.sb .venv/bin/python tests/live_driver.py 5071 <token>`: requests=75 failures=0.
- Unsandboxed: `run.py` on port 5072, `lsof -nP -a -p PID -i` in a loop, `nettop -p PID -L 40 -s 1 -m tcp` and `-m udp`, then `tests/live_driver.py 5072 <token>`: requests=75 failures=0.
- `auditenv/bin/pip-audit -r requirements.txt --no-deps --disable-pip`: 21 vulnerabilities in 4 packages.
- Real-file regression script (scratchpad only): {'pass': 11, 'rejected': 0}.
- Hang risk: the near-50 MB junk upload (T-2) blocks for many minutes; excluded from the suite (a 12 MB file is used instead).

---
## Main-agent verification (2026-10-01)
- Re-ran `pytest`: 182 passed, 4 xfailed.
- No database files in the workspace. Found and removed a stray empty `budget.db` (0 transactions, 0 imports, 0 accounts) in the session scratchpad.
- Not verified by the main agent: the sandbox and socket results (tester's evidence only); real-file figures; vulnerability triage.
