# Build 05: slice 5, categorisation (builder report)

Saved as returned by the builder subagent, 2026-10-01. Main-agent verification appended at the end.

### Slice 5 built: categorisation, rules, learning, correction UI. 102 tests pass (67 existing + 35 new). Stopped after slice 5.

**Headline finding (real files):** the ING Orange Everyday parser keeps only the first line of each row. For card purchases that line is bank wording only (for example "EFTPOS Purchase - Receipt NNNNNN"). The merchant is on the continuation line, which the parser skips per the handoff rule. Because of this, 749 of the 1,751 real spend rows (43%) have no payee at all (743 on ING spending, 6 on offset). No rule set can categorise them. Decision needed: capture the continuation line in the ING parsers (a slice 2 change that also affects the duplicate key, since description is part of it). The builder did not change parsers.

### Built
| File (all under `app/`) | What | MUST / SHOULD |
|---|---|---|
| `budget_app/rules.py` (new) | Payee normalisation and rule matching. First match wins. Match types: payee key, substring, regex | 6, SHOULD (remember rules) |
| `budget_app/categorise.py` (new) | Corrections, apply-to-similar, remember, bulk assign from queue, rules CRUD, re-run, Uncategorised queue, transaction listing, `month_totals(conn, 'YYYY-MM')` for slice 6 | 6, 7b, 7 (data side) |
| `config/seed_rules.json` (new) | About 250 generic Australian brand words in 12 groups. No personal data | 6 |
| `budget_app/db.py`, `schema.sql` | New columns: `transactions.category_user_set`, `transactions.payee_key`, `payee_rules.match_type/priority/is_seed`. Existing databases upgraded automatically. Seed rules copied into the user's database once (meta flag); deleted rules not re-added. Payee keys back-filled | 6, 7b |
| `budget_app/store.py` | New imports auto-categorised by rules at commit. Preview "Uncategorised" now means "no rule matches". Duplicate and transfer logic unchanged | 5, 6 |
| `budget_app/__init__.py`, templates `categorise.html`, `rules.html`, `transactions.html`, `_macros.html`, nav in `base.html`, `app.css` | Uncategorised queue by payee (count and total, assign all, Remember checkbox). Rules page (view, edit priority, delete, add, re-run). Per-transaction correction with Apply to similar and Remember. No inline script, CSP unchanged | SHOULD |
| `tests/test_slice5.py` (new), README note | Tests on fake data only | Acceptance |

**Behaviour:**
- Seed rules are whole-word regexes at priority 400 to 500. User rules start at priority 10 and win over seeds.
- Sinking pool is used for water and rates, rego and CTP, home insurance, Shannons, and flights and holidays (category 6 has no regular amount).
- A correction sets `category_user_set=1`. Rule re-runs and re-imports never touch user-set rows. Apply to similar and the queue's group assign also skip rows already user-set.
- Bank-wording-only descriptions get an empty payee key. They cannot be grouped or remembered, so they appear as an "unnamed" count with a link to the Transactions page.
- Payee key is the first 2 words after stripping card numbers, dates, reference digits, payment-method and bank words, company suffixes, and trailing state or country.
- Only `flow_type='spend'` counts. `month_totals` returns per category `regular_cents`, `sinking_cents`, `total_cents` and `count`, plus an Uncategorised entry and an overall total that includes it.
- Errors and flash messages carry counts only. Category and pool values are not placed in URLs, except the category and month filters on the Transactions page (ids, not transaction values).

### How to run
- Tests: `cd "projects/budget-adherence-tracking/app" && .venv/bin/pytest -q`
- App: `BUDGET_DATA_DIR=<folder outside Documents/Desktop/iCloud> ./run.sh`
- New pages: `/categorise`, `/transactions`, `/rules`.

### Installs / system changes
None. No new packages. The temporary real-data folder and scripts in the scratchpad were deleted.

### Real-file coverage (10 of 11 PDFs imported into a temporary database; counts only)
- The 11th file parsed and passed the gates but the builder's harness did not save it (probably the all-duplicates block; not investigated).
- 2,230 rows: 1,751 spend, 355 income, 124 transfer.
- Seed rules categorise 310 of 1,751 spend rows (17.7%). 1,441 remain Uncategorised.
- By category (rows): 1 has 39, 2 has 68, 3 has 85, 4 has 6, 5 has 53, 6 has 2, 7 has 56, 8 has 1. Pools: 297 regular, 13 sinking.
- Of the 1,002 spend rows that have a payee, 310 (31%) are categorised.

| Role | Spend rows | Categorised |
|---|---|---|
| ING spending | 762 | 5 |
| Offset | 981 | 302 |
| Credit card | 8 | 3 |

- By value, 96.7% of spend cents remain uncategorised. The large items are mostly loan, property, insurance and person-to-person payments. Those are user-specific, so they were not seeded.
- The queue has 194 payee groups. After the seed rules the largest groups have 65, 64, 36, 34, 33, 31, 27 and 26 rows, so a few dozen bulk assignments cover most of the named rows.
- Remaining payee keys are mostly people, a property manager, insurers, a lender, PayPal and ATM operators.

### Description-format findings (generic)
- **ING statement:** the first line is the bank wording and receipt number only. The merchant sits on a continuation line, followed by a "Date ... Card ####" line.
- **Offset listing:** descriptions carry the merchant inline after "Purchase at", "From", "To" or "Transfer To", sometimes with a trailing reference number. These normalise well.
- **Refunds:** 26 rows mention refund or reversal, and 3 credit card rows are positive (default to transfer). A refund from ING or offset arrives as income, so it is not netted against the category. A refund needs the user to set its flow to spend.
- **Foreign currency:** 59 rows mention international transactions ("Intl Transaction Fee", "Intl Atmpurchase"). They are on the same receipt as the purchase, with no foreign amount in the first line. Fees are separate spend rows with no payee.
- **Payment wording:** PayPal and "PYPL" appear as payees, which hides the real merchant. ATM withdrawals are cash with no category.
- **Descriptions:** no empty descriptions and no multi-line descriptions in stored rows (first line only).

### Deviations / blockers
- **ING merchant lost (above).** Needs a decision before category coverage on the main spending account is useful.
- Person-to-person payments ("To <person>") are counted as spend by default. The user may want to route them as transfers, or set them by rule. Judgement call for the main agent.
- The budget-vs-actual readout was not built (slice 6), as instructed.

### Not tested
- Browser rendering and layout of the new pages (only HTTP status, CSP and "no script" checks).
- Performance of re-running rules on a large database (2,230 rows was fine, not timed).
- Regex rules typed by the user are validated for syntax only. No timeout guard against pathological patterns.
- Seed rules against real descriptions beyond the aggregate coverage above. False positives such as "TOLL", "GYM" or "BWS" in unrelated descriptions were not audited.

---
## Main-agent verification (2026-10-01)
- Re-ran `pytest`: 102 passed.
- Read `config/seed_rules.json`: about 250 generic Australian brand and category words; no personal names or account numbers.
- No database files in the workspace; the temporary data folder is gone.
- Not verified by the main agent: the real-file coverage figures (builder's counts only); browser rendering.
