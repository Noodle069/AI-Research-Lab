"""Slice 3 parsers: ING short, NAB card, offset account / home loan. Fake data only."""
import io

import pytest

from budget_app.parsers.common import ParseRejected
from budget_app.parsers.detect import parse_pdf
from fakepdf import (LIST_TXNS, NAB_TXNS, SHORT_TXNS, DEFAULT_TXNS, ing_short, ing_statement,
                     nab_card, offset_listing)
from test_app import ORIGIN, app, client, post_upload, txn_count  # noqa: F401


def parse(pdf):
    return parse_pdf(io.BytesIO(pdf))


def errors_text(s):
    return " ".join(e for g in s.gates for e in g.errors)


def no_leaks(text):
    for leak in ("FAKE", "$", "1,234", "12345", "4599", "500000", "5,000", "180000", "1,800"):
        assert leak not in text, leak


# ---- (name, builder, txns, ok kwargs) -------------------------------------------------
CASES = {
    "ing_short": (lambda **k: ing_short(100000, SHORT_TXNS, **k), SHORT_TXNS, 100000, 2),
    "nab": (lambda **k: nab_card(300000, NAB_TXNS, **k), NAB_TXNS, None, 1),
    "offset_account": (lambda **k: offset_listing(250000, LIST_TXNS, **k), LIST_TXNS, 250000, 2),
    "offset_loan": (lambda **k: offset_listing(-30000000, LIST_TXNS, loan=True, with_transaction_col=False, **k),
                    LIST_TXNS, -30000000, 2),
}


@pytest.mark.parametrize("name", list(CASES))
def test_valid_passes_all_gates_and_integer_cents(name):
    build, txns, _, ngates = CASES[name]
    s = parse(build())
    assert s.passed and len(s.gates) == ngates
    assert [r.amount_cents for r in s.rows] == [a for _, _, a in txns]
    assert [r.date for r in s.rows] == [d for d, _, _ in txns]
    assert all(r.description.endswith(x) for r, (_, x, _) in zip(s.rows, txns))   # continuation lines skipped
    assert not any('continuation' in r.description for r in s.rows)
    assert all(isinstance(r.amount_cents, int) for r in s.rows)


@pytest.mark.parametrize("name", list(CASES))
def test_altered_amount_in_every_row_fails_and_names_row_only(name):
    build, txns, _, _ = CASES[name]
    for row in range(1, len(txns) + 1):
        s = parse(build(tamper_amount_row=row, tamper_delta=1))
        assert not s.passed, (name, row)
        text = errors_text(s)
        if name != "nab":                 # NAB has no per-row balance; only the statement gate can fail
            assert f"Row {row} " in text, (name, row)
        no_leaks(text)


@pytest.mark.parametrize("name", list(CASES))
def test_wrong_closing_fails_statement_gate(name):
    build, txns, opening, _ = CASES[name]
    if name == "nab":
        s = parse(build(closing_owed=1))
    elif name == "ing_short":
        s = parse(build(closing=1))
    else:
        s = parse(build(closing=12345))
    assert not s.gates[0].passed and not s.passed
    no_leaks(errors_text(s))


def test_wrong_printed_totals_fail():
    assert not parse(nab_card(300000, NAB_TXNS, printed_payments=1)).passed
    assert not parse(nab_card(300000, NAB_TXNS, printed_purchases=1)).passed
    assert not parse(offset_listing(250000, LIST_TXNS, printed_debits=1)).gates[0].passed
    assert not parse(offset_listing(250000, LIST_TXNS, printed_credits=1)).gates[0].passed


# ---- layout-specific facts ---------------------------------------------------------------
def test_ing_short_withdrawals_are_negative_and_opening_seeds_row_gate():
    s = parse(ing_short(100000, SHORT_TXNS))
    assert s.opening_cents == 100000 and s.rows[0].balance_cents == 300000
    assert s.rows[1].amount_cents == -4599
    # a wrong opening breaks the seeded first row
    bad = parse(ing_short(100000, SHORT_TXNS, closing=None))
    assert bad.passed
    from budget_app.parsers.common import chain_gate
    assert "Row 1 " in " ".join(chain_gate(s.rows, 99999).errors)


def test_nab_signs_whitespace_and_summary():
    s = parse(nab_card(300000, NAB_TXNS, split_amount_row=6))
    assert s.passed
    assert s.rows[5].amount_cents == -489406            # "4,8 94.06" style split repaired
    assert s.opening_cents == -300000                    # DR = owed = negative signed balance
    assert s.printed_in_cents == 150999
    assert all(r.balance_cents is None for r in s.rows)
    assert s.warnings                                    # says the row gate does not apply


def test_nab_interest_charge_row_is_reconciled_with_printed_charges():
    txns = NAB_TXNS + [(NAB_TXNS[-1][0], "FAKE INTEREST", -100)]
    pur = -sum(a for _, _, a in txns if a < 0)
    pay = sum(a for _, _, a in txns if a > 0)
    ok = nab_card(300000, txns, printed_purchases=pur - 100, charges=100, closing_owed=300000 - pay + pur)
    assert parse(ok).passed
    bad = nab_card(300000, txns, printed_purchases=pur - 100, charges=0, closing_owed=300000 - pay + pur)
    assert not parse(bad).passed


def test_offset_account_and_loan_signs_and_years():
    a = parse(offset_listing(250000, LIST_TXNS))
    assert a.opening_cents == 250000 and a.years_from_headings
    assert a.rows[0].date.isoformat() == "2025-12-29" and a.rows[3].date.isoformat() == "2026-01-02"
    assert a.rows[1].balance_cents == 250000 + 500000 - 180000
    loan = parse(offset_listing(-30000000, LIST_TXNS, loan=True, with_transaction_col=False))
    assert loan.opening_cents == -30000000
    assert loan.rows[0].balance_cents == -30000000 + 500000        # DR balance is negative signed
    assert loan.rows[-1].balance_cents == loan.closing_cents
    # month-year headings were not turned into transactions
    assert len(loan.rows) == len(LIST_TXNS)


def test_offset_balance_crossing_zero_and_dr_account():
    s = parse(offset_listing(10000, LIST_TXNS))     # goes overdrawn: DR marker on later rows
    assert s.passed and any(r.balance_cents < 0 for r in s.rows)


def test_offset_missing_heading_and_bad_year_rejected():
    with pytest.raises(ParseRejected):
        parse(offset_listing(250000, LIST_TXNS, header=False))


def test_detection_all_layouts_and_unknown():
    assert parse(ing_statement(500000, DEFAULT_TXNS)).layout.startswith("ING Orange Everyday statement")
    assert parse(ing_short(100000, SHORT_TXNS)).layout.startswith("ING Orange Everyday short")
    assert parse(nab_card(300000, NAB_TXNS)).layout.startswith("NAB")
    assert parse(offset_listing(250000, LIST_TXNS)).layout.startswith("Offset")
    with pytest.raises(ParseRejected) as e:
        parse(ing_short(100000, SHORT_TXNS, header=False))
    assert "Unrecognised layout" in e.value.errors[0]


# ---- through the app: preview works for every layout, nothing written ------------------------
@pytest.mark.parametrize("name", list(CASES))
def test_preview_screen_for_each_layout(client, app, name):
    r = post_upload(client, app, CASES[name][0]())
    assert r.status_code == 302
    page = client.get(r.headers["Location"]).get_data(as_text=True)
    assert "Preview (nothing saved yet)" in page and "PASS" in page and "FAIL" not in page
    assert txn_count(app) == 0


@pytest.mark.parametrize("name", list(CASES))
def test_altered_amount_rejected_whole_file_in_app(client, app, name):
    r = post_upload(client, app, CASES[name][0](tamper_amount_row=2))
    assert r.status_code == 422
    body = r.get_data(as_text=True)
    assert "File rejected" in body and "FAKE" not in body
    assert txn_count(app) == 0


def test_layout_parsers_make_no_network_connection(monkeypatch):
    import socket

    def boom(*a, **k):
        raise AssertionError("network access attempted")
    monkeypatch.setattr(socket.socket, "connect", boom)
    monkeypatch.setattr(socket, "create_connection", boom)
    for build, *_ in CASES.values():
        assert parse(build()).passed
