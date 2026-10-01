# Build 04: offset flow default fix (builder report)

Saved as returned by the builder subagent, 2026-10-01. Change within slice 4, per the user's decision of 2026-10-01 (offset accounts treated like spending accounts).

### Built
Offset accounts now default like spending accounts: out = spend, in = income. Loans and credit card credits are unchanged. Offset-to-spending exact pairs on the same day are still auto-marked transfer on both sides.

- `app/budget_app/store.py`: `default_flow` now special-cases only `loan` as transfer. Offset falls through to spend/income.
- `app/budget_app/templates/transfers.html`: help text updated. The README had no text describing the defaults, so it is unchanged.
- `app/budget_app/db.py`: new `_rederive_offset_flows`, called from `init_db`.
- `app/tests/test_slice4.py`: `test_role_defaults` updated, plus 3 new tests (offset out = spend and in = income with loan credit unchanged; offset-to-spending same-day exact pair auto-marked transfer on both sides with candidate status `auto`; re-derive test).

### Existing saved databases
Rows saved under the old default are re-derived automatically. Non-destructive, runs once, guarded by the meta key `offset_flow_rederived`, the next time the app starts.
- **Changes:** offset-account rows with `flow_user_set=0` and `flow_type='transfer'` become spend (amount below 0) or income.
- **Skipped:** rows with `flow_user_set=1`, and rows in any `auto` or `confirmed` transfer pair. Rows in `suggested` pairs are re-derived and the suggestion stays so the user can still confirm it.
- No manual step needed. Real files not touched.

### Installs / system changes
None.

### Deviations / blockers
None.

### Not tested
- The re-derive against a real saved database (fake-data test only).
- The UI rendering of the changed help text.

Full suite: 67 passed in 2.47s, 0 failed.

---
## Main-agent verification (2026-10-01)
Re-ran `pytest`: see result in the session message (67 expected).
