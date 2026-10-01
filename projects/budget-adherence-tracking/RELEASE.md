# RELEASE: Budget tracker 0.1.2

**Status: READY (0.1.2)**. Update 2026-10-01 later: relaunching while an old copy held the port gave "Forbidden" on every page; fixed in 0.1.2 (the app refuses to start and prints no link if the port is taken). Update 2026-10-01: 0.1.0 had a blocker found by the user in Safari: uploads gave "Forbidden" (browser sent `Origin: null` because of the no-referrer policy). Fixed in 0.1.1 and verified in real Chrome with all 12 statements through upload, preview, save and every page (see CHANGELOG.md). Not yet verified in Safari itself. Original status line follows:

**Status: READY** (local use only, dry run; nothing published).

## Release
| Item | Value |
|---|---|
| Version | 0.1.2, set once in `app/budget_app/__init__.py` (`__version__`), shown in the page footer |
| Target | Local: runs on the user's own Mac at 127.0.0.1. No publishing |
| Artifact | The folder `projects/budget-adherence-tracking/app/` (run via `Start Budget Tracker.command` or `./run.sh`; guide in `app/README.md`) |
| Dependencies | `app/requirements.lock` (hash-pinned, 18 packages), `app/requirements.txt` (same pins) |
| Python | `/usr/bin/python3` 3.9.6 |

## Checks
| Check | Result |
|---|---|
| Full test suite in the project venv | PASS: 193 passed (192 + 1 new footer-version test) |
| Clean build: fresh venv on /usr/bin/python3 from requirements-dev.txt, copy of app, `pip check`, suite | PASS: 193 passed, no broken requirements. Note: the "no secrets" test scans the whole folder, so the venv must be named `.venv` (as run.sh does) |
| Smoke start of run.py with a temp data folder | PASS: link printed, `/` without cookie 403, token link 302, page shows v0.1.0, `/month` 200, only listener 127.0.0.1:port, `budget.db` created. Temp folder deleted |
| Hash-pinned lock (`requirements.lock`) | PASS: fresh venv installed with `--require-hashes --only-binary=:all:`; versions identical to requirements.txt; `pip check` clean; app started from it. A tampered hash was refused. Covers macOS and platform-independent wheels for Python 3.9 to 3.14; no source builds. Kept |
| Launcher `Start Budget Tracker.command` (scratch run, HOME redirected, `open` stubbed) | PASS: built venv from the lock on first run, data folder `BudgetTrackerData` created (mode 700), link with token passed to `open`, loopback listener only, token link 302. Real browser opening and Terminal double-click NOT tested (needs the user's Mac UI) |
| Control+C stop | NOT DONE: a background shell ignores SIGINT; the stop path is the standard Flask/Python KeyboardInterrupt. Process was stopped with SIGTERM |
| No real data in project folder | PASS: 75 files scanned. No PDF/db/csv/key/.env files. 0 card-number patterns, 0 emails, 0 token patterns. 18 long digit runs, all benign (2147483647 int limit, 99999999999999999999 test values, a forum thread id, "123456789" and a FAKE PayPal number in tests); 1 NNN-NNN hit is a code constant. 15 hits for the home path `/Users/alphakings` in notes/reports (a username in paths, no statements/accounts); `.env.example` uses `/Users/you`. File names only, no account numbers or names of people found. One stray backup file: `app/requirements.txt.bak-pre-upgrade` (intentional rollback file) |
| No external URLs, scripts, networking imports in app code | PASS: no socket/urllib/http.client/requests imports; only URL strings are the loopback link and the Origin check; no `<script>`, `<link>` to other hosts or `url()` in templates/CSS; sole stylesheet is local. Only `subprocess` use is the bounded PDF parse worker |
| Data-folder guard | PASS: refuses Documents, Desktop, Library/Mobile Documents, a symlink into Documents, and an unset variable; nothing created in Documents |
| Dependency audit | 20 known vulnerabilities remain (click 1, pdfminer.six 1, pillow 18); fixes need Python 3.10+. Not re-run by me (builder's pip-audit figures) |
| Real-file import through the web pages | NOT DONE by anyone but the builder's harness |

## Changelog
User-visible changes by slice are in `app/CHANGELOG.md`: importing with statement and row balance checks for 5 layouts, preview, duplicates, pre-import backups, accounts and transfers, categorising and rules, month / overspend / trends, security and offline behaviour, limits (10 MB, 150 pages, 30 s per file).

## Rollback plan
Nothing is installed outside `app/` and the data folder, so rollback is local.
1. Stop the app (Control+C in its Terminal window).
2. Bad import or bad data: copy the newest file in `~/BudgetTrackerData/backups/` over `~/BudgetTrackerData/budget.db`, or restore a copy of the whole folder from the external drive. Confirm: start the app, open Coverage and Month; the date ranges and totals match what you had before the import.
3. Bad dependency change: `cd app; cp requirements.txt.bak-pre-upgrade requirements.txt` (Flask 3.0.3; this also needs the matching lock, so also delete `requirements.lock`), `rm -rf .venv`, then start with `./run.sh` to rebuild. Confirm: `.venv/bin/pip list` shows Flask 3.0.3 and `.venv/bin/python -m pytest -q` passes.
4. Bad app version: keep the previous `app` folder when updating; start it against the restored data. Confirm: footer shows the older version.
5. Broken environment only: `rm -rf app/.venv` and start again (rebuilds from `requirements.lock`; needs internet once). Confirm: app starts and prints a link.

## Known risks
- 20 vulnerabilities in click, pdfminer.six and pillow need Python 3.10+; low exposure (local, files chosen by the user). Fix: install a newer Python and re-pin.
- The user has not yet tried the app in a browser; the real-file end-to-end import via the web pages has only been run by the builder's harness (parsers passed 11 of 11 real files).
- Descriptions-based categorisation coverage is about 40% with the seed rules; expect manual categorising and rule-building at first.
- Launcher untested with a real double-click: macOS may ask for permission or show a Gatekeeper prompt for a `.command` file (documented in README; not automated).
- Control+C stop not exercised by me (see Checks).
- The first run needs internet once for pip.

## Approval needed
None for local use. Not done (no approval requested or given): pushing, tagging, publishing, deploying, DNS, anything outside `projects/budget-adherence-tracking/` other than scratchpad throwaways.

## Installs / system changes
- In the project: `app/requirements.lock`, `app/CHANGELOG.md`, `app/Start Budget Tracker.command` (executable), `app/run.sh` (now installs from the lock), README Quick start, footer/version code and one test, this file.
- Scratchpad throwaway venvs (Python 3.9.6, deleted after use): clean-build venv (Flask 3.1.3, pdfplumber 0.11.8, pytest 8.3.5 and the pinned transitive packages; pip 21.2.4, setuptools 58.0.4), lock venv, tampered-lock venv (nothing installed), launcher-test venv. Installed from PyPI via pip only.
