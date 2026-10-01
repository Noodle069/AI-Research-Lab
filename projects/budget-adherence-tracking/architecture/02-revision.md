# Architecture 02: revision for PDF-only input

Saved in full as returned by the architect subagent, 2026-09-30. Revises architecture/01-options.md.

### Bottom line

Option P1 is the technically preferred one: a Flask/SQLite custom app that reads PDFs with pdfplumber's word coordinates. Its parser output must pass two checks before it can be committed: a balance reconciliation and a per-row running-balance check. P2 (text-only) is a lower-dependency fallback. P3 (Actual Budget plus a converter) is viable but only partly satisfies "my own app". Confidence is MEDIUM, because no transaction row has been parsed yet. This revises architecture/01. The architect read all the files listed and read no raw statements or transaction data.

### Dropped from architecture/01

| Dropped | Reason |
|---|---|
| CSV-first pipeline, profile mapping UI | No CSV is available (user decision, 2026-09-30) |
| B (browser-only) | Weak PDF path and evictable storage (architecture/01, research/01) |
| C1/C2 (Electron/Tauri), D1 fork | Toolchain or fork burden with no PDF benefit |
| E (Actual as-is) and F (spreadsheet) | Fail PDF-only or fail "my own app". Actual is still a fallback |
| OCR or cloud PDF services | The files are text PDFs (research/04). Cloud services break the local-only and $0 constraints |

### Shared design (all options)

This changes architecture/01. Phases 0 to 2 now start with PDF, and the earlier "PDF later" phase is removed.

| Element | Design |
|---|---|
| Trigger and input | The user drops a PDF into the app. The account is chosen by the user, and each account has a role: spending, credit card, loan or offset. The layout ("layout profile") is auto-detected from header text and confirmed by the user. Known layouts: ING statement, ING short report, NAB card, home-loan listing, offset listing (research/04). |
| Extraction | Extract, repair whitespace (needed for NAB), read the printed opening and closing balances, and rebuild rows. Dates without a year (e.g. "Dec 17") take the year from the statement period, including across a Dec/Jan boundary. |
| Money direction | Read from a column (ING, offset), a CR/DR suffix (NAB), or a DR/CR balance suffix. The signs are normalised to integer cents. |
| Correctness gate (hard block) | Per statement: opening + in − out = closing, reconciled to the cent. Any mismatch rejects the whole file with no partial import. The error names the row number and field type only, never the values (critic H2). |
| Second gate | Where every row prints a balance (ING, offset), check each row: previous balance ± amount = this balance. This catches a single misread or swapped row that still nets out. NAB has no per-row balance, so only the statement-level gate applies. |
| Preview before commit | Shows the date range, counts, totals in and out, the reconciliation result, the year inferred per row, flagged transfers, duplicates, and Uncategorised. Nothing is written until the user approves. |
| Duplicates | Block a file whose hash was already imported. This is now justified, because two ING files are identical (research/04). Then match per account as a multiset on date, cents and description over the overlapping range. Balance is never in the identity key (critic H4). |
| Transfers and coverage | Each transaction gets a flow type: spend, income, transfer or savings. Inter-account pairs are matched across accounts. Card repayments and loan flows are excluded from spending. A coverage panel shows accounts and date ranges per month (critic H3, M7). |
| Store, backup, network | SQLite in a folder iCloud does not sync. Backups are pre-import copies plus manual copies to an external drive (user decision). The server binds explicitly to 127.0.0.1, with debug off, `TRUSTED_HOSTS`, a per-launch token and a CSP. There are no transaction values in URLs or logs. |
| AI-builder boundary | The user approved sharing whole statements with Claude for this project only. A Read deny rule does not stop a script the builder runs (research/03 #5). Keep the data folder outside the workspace. Real-data test runs happen on the user's machine, with output limited to pass/fail and counts unless the user approves more. |

### Viable options

#### P1: Custom app with coordinate-based PDF parsing (pdfplumber)

- **How it works:** pdfplumber extracts words with positions. Column x-ranges from each layout's header row assign each amount to Money out, Money in or Balance. Multi-line rows, such as the ING "Card 1234" continuation, are joined by y-position. For NAB, the word-level tolerance setting (`x_tolerance`) is tuned to fix the kerning.
- **Components:** Python (python.org installer), Flask, SQLite, pdfplumber and its dependencies, and bundled Chart.js.
- **Dependencies:** pdfplumber (MIT) on top of pdfminer.six (MIT). Its README says it also uses Pillow. The full dependency list is not confirmed.
- **Risks:**
  - Layout drift across banks silently breaks x-ranges. The gates make this loud rather than silent.
  - The 33-page and 18-page files put many rows behind the header-repeat logic.
  - A repair step for NAB text could change digits. The gate is the defence.
- **Cost and complexity:** medium. One parser per layout (five layouts), plus shared normalisation. Column positions come from the header row, not hard-coded, which reduces breakage. (RECOMMENDATION)
- **Unverified:**
  - NAB text repair on real transaction rows (untested; research/04 says LIKELY fixable)
  - multi-line descriptions and foreign-currency rows (never inspected)
  - whether the offset or home-loan lists are really Macquarie (UNVERIFIED)

#### P2: Custom app with text-only parsing (pdfminer.six or pypdf plus regex)

- **How it works:** it extracts plain text lines and parses them with per-layout regexes. It has no coordinates, so it cannot tell "Money out" from "Money in" by position. Direction comes from the running-balance change (ING, offset), from the CR/DR suffix (NAB), or from the DR/CR balance suffix.
- **Components:** the same as P1, but with pdfminer.six or pypdf instead of pdfplumber.
- **Dependencies:** pypdf is pure Python and needs no other packages, and pdfminer.six is also pure Python. This is the smallest supply chain.
- **Risks:**
  - It relies on the balance column being present on every row. Any row without one falls through to guesswork.
  - The kerning and spacing in the NAB text is worse without coordinates.
  - Text order for columns can vary between extractors.
- **Cost and complexity:** medium-low to build, but more fragile per layout. Its main appeal is fewer dependencies.
- **Unverified:** pypdf layout-preserving mode (the page fetched did not confirm it), and whether either library reproduces the NAB text well.

#### P3: Hybrid with Actual Budget as store and UI, plus a custom PDF-to-import converter

- **How it works:** a local converter parses the PDF. It runs the reconciliation gates and writes a CSV, then the user imports it into Actual. Actual provides rules, transfers, duplicate detection and budget-vs-actual. Actual's CSV import and duplicate detection are VERIFIED (research/01). Its custom CSS themes are VERIFIED (research/03 #3).
- **Components:** the converter (Python plus P1 or P2 parsing) and the Actual desktop app (MIT).
- **Dependencies:** Actual's import flow. Its trend view is experimental only, and its network behaviour is unaudited.
- **Risks:**
  - The fixed decision was a custom app, so this only partly satisfies it (critic H1).
  - Preview happens in two places, and Actual's preview would not show the reconciliation result. The converter would have to show it.
  - Actual's real per-account roles for offset and loan accounts are unverified.
  - The multi-month category trend is still missing, so it still needs a custom part.
- **Cost and complexity:** lowest to a working month view. The converter is the same parsing work as P1, without the UI or database.
- **Unverified:** whether Actual handles a loan or offset account cleanly, and whether it preserves DR/CR semantics through CSV.

### PDF libraries: free, local, no network calls

Checked 2026-09-30. None of the sources states "makes no network calls". That is an absence of evidence, not verification. Confirm with an outbound-connection monitor before any real file is used.

| Library | Licence | Free and local? | Evidence |
|---|---|---|---|
| pdfplumber 0.11.10 (2026-06-15) | MIT | Free and local. No network use described. Text-based PDFs only, no OCR. | https://pypi.org/project/pdfplumber/ ; https://github.com/jsvine/pdfplumber |
| pdfminer.six 20260107 | MIT | Free and local. Python 3.10 or later. No network use described. | https://pypi.org/project/pdfminer.six/ |
| pypdf 6.19.0 (2026-09-16) | BSD-3-Clause | Free, pure Python and local. AES needs the optional crypto extra. Text extraction via `extract_text()`. | https://pypi.org/project/pypdf/ |
| PyMuPDF | AGPL or paid commercial | Free under AGPL, processes locally. Whether AGPL terms suit the user is UNKNOWN. Not needed, so avoid. | https://pymupdf.readthedocs.io/en/latest/about.html |
| Camelot | UNKNOWN | The PyPI page failed to load, so licence and dependencies could not be verified. Earlier research/01 says MIT. UNKNOWN. | https://pypi.org/project/camelot-py/ |
| tabula-py | n/a | Needs Java (research/01). Excluded. | |
| macOS PDFKit | Apple, built in | Used for research/04. Apple's page returned only a title, so network behaviour is UNKNOWN. Usable from Python only through PyObjC, which is UNVERIFIED. | https://developer.apple.com/documentation/pdfkit/pdfdocument |

### Comparison (decision-relevant only)

| | P1 pdfplumber | P2 text-only | P3 Actual hybrid |
|---|---|---|---|
| "My own app" | Full | Full | Partial |
| PDF and $0/local | Meets | Meets | Meets |
| Direction detection | Column position plus balance check | Balance change or suffix only | Same as P1 or P2 in the converter |
| Dependencies | Most (pdfminer.six, Pillow) | Fewest | P1 or P2, plus Actual |
| NAB robustness | Best (word-level tolerance) | Weakest | Same as parser |
| Reconciliation and preview | In-app, one place | In-app, one place | Split across converter and Actual |
| Build effort | Highest (parser plus UI) | Highest, more fragile | Lowest |
| Trend view | Own | Own | Still a custom gap |

### Research required (unresolved)

| # | Item | Changes |
|---|---|---|
| R-a | Spike on one real file per layout (run locally, output pass/fail only). Test the reconciliation and per-row balance check, NAB repair, multi-line rows and year inference. | P1 vs P2, and whether any option is feasible |
| R-b | Multi-line descriptions, foreign currency, refunds and pending rows. Never inspected (research/04). | Parser scope |
| R-c | Whether the home-loan and offset reports are Macquarie, and whether they are stable across overlapping periods. | Duplicate logic and profiles |
| R-d | pdfplumber's full dependency list at pinning time, and an outbound-monitor run showing zero calls. LuLu itself is unverified (research/03). | The no-network claim |
| R-e | pypdf layout mode, and Camelot's licence and dependencies. Only needed if P2 or Camelot is pursued. | P2 viability |
| R-f | Actual's handling of offset or loan accounts and DR/CR through CSV. | P3 only |
| R-g | Whether the Claude Code sandbox can deny one folder on macOS (research/03 #5, UNKNOWN). | AI-builder boundary |

### Preferred architectural option

**P1**, with P2's balance-change direction check kept as an independent cross-check inside P1. Reasons:
- Coordinates are the only way to assign an amount to the right column without inference, which the two ING layouts and the offset listings need.
- The word-level tolerance is the most direct fix for NAB's badly spaced text (LIKELY, untested).
- It satisfies "my own app" fully, unlike P3.
- The gates apply to any extractor, so P1 can be downgraded to P2 or upgraded without redesign.

Change to P3 if the spike (R-a) shows PDF parsing is reliable, and the user would rather trade the custom UI for a mature engine. Change to P2 if pdfplumber's dependencies prove unacceptable.

### Confidence

**MEDIUM.** The libraries, licences and design controls are established. Whether parsing reconciles on real rows has not been tested, and that spike (R-a) is the highest-value next step. This blocks the option choice but not the shared design.
