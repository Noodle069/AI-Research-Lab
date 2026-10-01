import io

import pytest

from budget_app.parsers.common import ParseRejected, parse_cents, parse_dmy4
from budget_app.parsers.ing_statement import parse_pdf
from fakepdf import DEFAULT_TXNS, ing_statement

OPENING = 500000


def parse(pdf):
    return parse_pdf(io.BytesIO(pdf))


def test_cents_and_dates():
    assert parse_cents("$-1,234.50") == -123450
    assert parse_cents("-0.05") == -5
    assert parse_cents("1,000.00") == 100000
    assert parse_cents("12.5") is None and parse_cents("--1.00") is None and parse_cents("abc") is None
    assert parse_dmy4("31/12/2025").isoformat() == "2025-12-31"
    assert parse_dmy4("31/02/2025") is None and parse_dmy4("01/02/25") is None


def test_valid_statement_passes_both_gates_multipage():
    s = parse(ing_statement(OPENING, DEFAULT_TXNS))  # 8 rows over 2 pages, header repeated
    assert s.passed and [g.passed for g in s.gates] == [True, True]
    assert len(s.rows) == len(DEFAULT_TXNS)
    assert [r.amount_cents for r in s.rows] == [a for _, _, a in DEFAULT_TXNS]  # signed integer cents
    assert s.rows[0].description == "FAKE SHOP ONE"          # continuation line skipped
    assert not any("Card" in r.description for r in s.rows)
    assert s.opening_cents == OPENING
    assert s.closing_cents == OPENING + sum(a for _, _, a in DEFAULT_TXNS)


def test_altered_amount_fails_row_gate_and_names_row_only():
    s = parse(ing_statement(OPENING, DEFAULT_TXNS, tamper_amount_row=4, tamper_delta=100))
    assert not s.passed
    row_gate = s.gates[1]
    assert not row_gate.passed
    text = " ".join(e for g in s.gates for e in g.errors)
    assert "Row 4" in text
    # messages carry no values: no amounts, no descriptions
    for leak in ("123.45", "12345", "124.45", "FAKE", "$"):
        assert leak not in text
    # the statement gate also catches the altered row (sum of rows != printed totals)
    assert not s.gates[0].passed


def test_altered_amount_in_every_position_is_caught():
    for row in range(1, len(DEFAULT_TXNS) + 1):
        s = parse(ing_statement(OPENING, DEFAULT_TXNS, tamper_amount_row=row, tamper_delta=1))
        assert not s.passed, row
        assert f"Row {row}" in " ".join(e for g in s.gates for e in g.errors)


def test_wrong_closing_balance_fails_statement_gate():
    s = parse(ing_statement(OPENING, DEFAULT_TXNS, closing=OPENING + 1))
    assert not s.gates[0].passed and s.gates[1].passed


def test_wrong_printed_totals_fail_statement_gate():
    s = parse(ing_statement(OPENING, DEFAULT_TXNS, printed_in=1))
    assert not s.gates[0].passed


def test_unknown_layout_rejected():
    with pytest.raises(ParseRejected) as e:
        parse(ing_statement(OPENING, DEFAULT_TXNS, header=False))
    assert "Unrecognised layout" in e.value.errors[0]


def test_corrupt_pdf_rejected():
    with pytest.raises(ParseRejected):
        parse(b"%PDF-1.4 this is not a real pdf")
    with pytest.raises(ParseRejected):
        parse(b"")


def test_parser_makes_no_network_connection(monkeypatch):
    import socket

    def boom(*a, **k):
        raise AssertionError("network access attempted")
    monkeypatch.setattr(socket.socket, "connect", boom)
    monkeypatch.setattr(socket, "create_connection", boom)
    assert parse(ing_statement(OPENING, DEFAULT_TXNS)).passed
