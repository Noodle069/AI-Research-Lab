# Release 01: local release prep (releaser report)

Saved as returned by the releaser subagent, 2026-10-01 (second message after a turn-limit stop). Dry run; nothing published. Main-agent verification appended at the end.

**READY (local, dry run).** All four deliverables and all pre-release checks are done, with two exceptions: the Control+C stop and a real double-click of the launcher were not tested.

### Release
- Version 0.1.0 is set once, in `app/budget_app/__init__.py` (`__version__`). The page footer shows "Budget tracker v0.1.0". One test was added; the suite is now 193 tests.
- Target is local only. The artifact is the `app/` folder.
- Nothing was published, pushed or tagged. Nothing was touched outside the project folder except scratchpad throwaways.

### Checks

| Check | Result |
|---|---|
| Full suite | PASS, 193 passed |
| Clean build: fresh venv on /usr/bin/python3 from requirements-dev.txt, `pip check`, suite, smoke start of run.py with a temp data folder | PASS. 193 passed. Smoke start: no-cookie request 403, token link 302, page shows v0.1.0, /month 200, only listener 127.0.0.1:port, budget.db created. Temp folder deleted. |
| Hash-pinned lock | PASS, kept as `app/requirements.lock`. A fresh venv installed from it with `--require-hashes --only-binary=:all:`. Versions match requirements.txt; `pip check` clean. A tampered hash was refused. The app started from that venv. The lock covers macOS and platform-independent wheels for Python 3.9 to 3.14, no source builds. |
| Launcher scratch test (HOME redirected, `open` stubbed) | PASS. Built the venv from the lock, created the data folder with mode 700, passed the token link to `open`, token link returned 302. Only a loopback listener was open. |
| Launcher in real use | NOT DONE: a real double-click and real browser open need the Mac's UI; macOS may show a Gatekeeper prompt. |
| Control+C stop | NOT DONE. A background shell ignores SIGINT, so the process was stopped with SIGTERM. |
| No real data in the project folder | PASS. 75 files scanned. No pdf, db, csv, key or .env files. 0 card-number patterns, 0 emails, 0 token patterns. 18 long digit runs, all benign (int limit, test values, a forum thread id, a FAKE PayPal number). 1 NNN-NNN hit, a code constant. 15 hits for the home-directory username in paths (budget-categories.md, research/04, architecture/01, build/01-03, critique/01). The only backup file is the intentional `app/requirements.txt.bak-pre-upgrade`. |
| No external URLs, scripts or networking imports in app code | PASS. Only URL strings are the loopback link and the Origin check. Only `subprocess` use is the PDF parse worker. |
| Data-folder guard | PASS. Refuses Documents, Desktop, Library/Mobile Documents, a symlink into Documents, and an unset variable. |
| Dependency audit | 20 known vulnerabilities remain (click 1, pdfminer.six 1, pillow 18). Builder's figures; not re-run by the releaser. They need Python 3.10+ to fix. |

### Notes
- The clean-build venv must be named `.venv`: the "no secrets" test scans the whole folder, so a venv named `v` failed it with a false positive. `run.sh` already uses `.venv`.
- `run.sh` now installs from `requirements.lock` when it is present.

### Changelog
`app/CHANGELOG.md` lists user-visible changes by slice: imports and balance checks for 5 layouts, preview, duplicates, backups, transfers, categorising and rules, month, overspend and trends, security and offline behaviour, and the limits (10 MB, 150 pages, 30 s per file).

### Rollback plan (full steps in RELEASE.md)
1. Stop the app.
2. Restore the newest file in `~/BudgetTrackerData/backups` over `budget.db`, or restore a copy of the whole folder.
3. For a dependency change: restore `requirements.txt.bak-pre-upgrade`, delete `requirements.lock`, `rm -rf .venv`, rebuild.
4. For a bad app version: start the previous `app` folder.
5. For a broken environment: `rm -rf app/.venv` and start again.
Each step has a way to confirm it worked.

### Known risks
- 20 vulnerabilities in click, pdfminer.six and pillow need Python 3.10+; exposure is low because the app is local.
- The user has not tried the app in a browser. A real-file import through the web pages has only been run by the builder's harness; the parsers passed 11 of 11 real files.
- About 40% categorisation coverage on the seed rules.
- The first run needs internet once for pip.

### Approval needed
None for local use. Nothing was pushed, tagged, published or deployed.

### Installs / system changes
All throwaway venvs in the scratchpad (Python 3.9.6, from PyPI via pip), deleted except a `cb/` source copy; small scripts and logs remain in the scratchpad.
- Clean-build venv: Flask 3.1.3, pdfplumber 0.11.8, pytest 8.3.5, blinker 1.9.0, cffi 2.0.0, charset-normalizer 3.5.2, click 8.1.8, cryptography 50.0.1, exceptiongroup 1.3.1, importlib_metadata 8.7.1, iniconfig 2.1.0, itsdangerous 2.2.0, Jinja2 3.1.6, MarkupSafe 3.0.3, packaging 26.3, pdfminer.six 20251107, pillow 11.3.0, pluggy 1.6.0, pycparser 2.23, pypdfium2 5.13.0, tomli 2.4.1, typing_extensions 4.16.0, Werkzeug 3.1.9, zipp 3.23.1 (pip 21.2.4 and setuptools 58.0.4 came with the venv).
- Lock-install venv and launcher-test venv: the 18 runtime packages above, from the lock. Tampered-lock venv: nothing installed (pip refused).
- In the project (no installs): `app/requirements.lock`, `app/CHANGELOG.md`, `app/Start Budget Tracker.command` (executable), a rewritten `app/run.sh`, the README Quick start, the version and footer code change plus one test, and RELEASE.md.

Files, under `projects/budget-adherence-tracking/`: RELEASE.md; app/CHANGELOG.md; app/README.md; app/requirements.lock; app/run.sh; app/Start Budget Tracker.command; app/budget_app/__init__.py; app/budget_app/templates/base.html; app/tests/test_fixround.py.

---
## Main-agent verification (2026-10-01)
- Re-ran `pytest`: 193 passed.
- Read `Start Budget Tracker.command` and `run.sh`: local only; builds `.venv` from the hash-pinned lock, sets `BUDGET_DATA_DIR` to `~/BudgetTrackerData`, starts the app on 127.0.0.1 and opens the one-time link in the default browser. Needs the internet once for pip. No other side effects.
- `requirements.lock` has 72 hash entries; pinned versions match `requirements.txt`. RELEASE.md and CHANGELOG.md exist.
- Not verified by the main agent: the clean-build smoke start; the personal-data scan; a real double-click.
