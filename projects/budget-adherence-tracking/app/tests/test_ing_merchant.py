"""ING statement merchant continuation lines. FAKE data only."""
import datetime as dt
import io

import pytest

from budget_app import rules as R
from budget_app.parsers.common import ParseRejected
from budget_app.parsers.ing_statement import parse_pdf
from fakepdf import ing_statement
from test_app import app, client  # noqa: F401 (fixtures)
from test_slice4 import do_import, q

D = dt.date
OPEN = 500000
TXNS = [
    (D(2025, 3, 1), ["EFTPOS Purchase - Receipt 123456", "FAKE CAFE BONDI NSW AU"], -1250),
    (D(2025, 3, 2), "Osko Payment - Receipt 654321", -5000),                      # no merchant line
    (D(2025, 3, 3), ["EFTPOS Purchase - Receipt 222222", "FAKE LONG NAME", "SECOND   LINE"], -700),
    (D(2025, 3, 4), "FAKE SALARY", 250000),
    (D(2025, 3, 5), ["Visa Purchase - Receipt 333333", "FAKE SHOP"], -300),
]


def parse(pdf):
    return parse_pdf(io.BytesIO(pdf))


def test_merchant_lines_joined_card_line_excluded_no_row_merge():
    s = parse(ing_statement(OPEN, TXNS))
    assert s.passed and len(s.rows) == 5
    d = [r.description for r in s.rows]
    assert d[0] == "EFTPOS Purchase - Receipt 123456 FAKE CAFE BONDI NSW AU"   # one continuation line
    assert d[1] == "Osko Payment - Receipt 654321"                              # zero
    assert d[2] == "EFTPOS Purchase - Receipt 222222 FAKE LONG NAME SECOND LINE"  # two, space normalised
    assert d[3] == "FAKE SALARY"                                                # legacy "Card ####" line only
    assert d[4] == "Visa Purchase - Receipt 333333 FAKE SHOP"
    assert not any("Card" in x or "Date" in x or "03/2025" in x for x in d)


def test_gates_unchanged_and_altered_amount_still_fails():
    bad = parse(ing_statement(OPEN, TXNS, tamper_amount_row=1, tamper_delta=1))
    assert not bad.passed
    assert [g.passed for g in bad.gates] == [False, False]
    assert all("FAKE" not in e for g in bad.gates for e in g.errors)


@pytest.mark.parametrize("desc,key", [
    ("EFTPOS Purchase - Receipt 123456 FAKE CAFE BONDI NSW AU", "FAKE CAFE"),
    ("Visa Purchase - Receipt 333333 FAKE SHOP", "FAKE SHOP"),
    ("EFTPOS Purchase - Receipt 222222 FAKE LONG NAME SECOND LINE", "FAKE LONG"),
    ("Osko Payment - Receipt 654321", ""),                       # no merchant: no key, not grouped
    ("Direct Debit - Receipt 009988 FAKE INSURE PTY LTD", "FAKE INSURE"),
])
def test_payee_key_for_merged_ing_descriptions(desc, key):
    assert R.payee_key(desc) == key


def test_identical_same_day_purchases_survive_and_overlap_dedupes(client, app):
    same = [(D(2025, 3, 3), ["EFTPOS Purchase - Receipt 111111", "FAKE CAFE"], -675)] * 2
    a = [(D(2025, 3, 1), ["EFTPOS Purchase - Receipt 100000", "FAKE SHOP ONE"], -1250)] + same
    assert do_import(client, app, ing_statement(OPEN, a)).status_code == 302
    assert q(app, "SELECT COUNT(*) FROM transactions")[0][0] == 3   # identical pair both kept
    # overlapping statement: 3 rows seen, plus 1 new
    b = a + [(D(2025, 3, 6), ["EFTPOS Purchase - Receipt 100001", "FAKE NEW"], -100)]
    assert do_import(client, app, ing_statement(OPEN, b), account="1").status_code == 302
    assert q(app, "SELECT COUNT(*) FROM transactions")[0][0] == 4


def test_old_first_line_only_rows_do_not_dedupe_against_new_descriptions(client, app):
    """Documented behaviour (README): rows saved under the old description re-import as new rows."""
    old = [(D(2025, 3, 1), "EFTPOS Purchase - Receipt 100000", -1250)]
    new = [(D(2025, 3, 1), ["EFTPOS Purchase - Receipt 100000", "FAKE SHOP ONE"], -1250)]
    assert do_import(client, app, ing_statement(OPEN, old)).status_code == 302
    do_import(client, app, ing_statement(OPEN, new), account="1")
    assert q(app, "SELECT COUNT(*) FROM transactions")[0][0] == 2


def test_card_detail_line_with_two_digit_or_four_digit_year_is_excluded():
    """Real files print the card-detail date as dd/mm/yy (fake files use the same); dd/mm/yyyy also accepted."""
    from budget_app.parsers.ing_statement import _CARD_LINE
    assert _CARD_LINE.match("Date 03/03/25 Card 1234")
    assert _CARD_LINE.match("Date 03/03/2025 Card 1234")
    assert _CARD_LINE.match("Card 1234")
    assert not _CARD_LINE.match("FAKE SHOP 03/03/25")
