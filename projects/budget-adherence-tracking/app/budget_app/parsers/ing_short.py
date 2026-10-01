"""ING Orange Everyday short report parser.

Layout (VERIFIED against the user's real file): header Date, Description, Deposit($),
Withdrawal($), Balance($). Dates "dd Mon yyyy" (three words). Withdrawals are printed
NEGATIVE ("-$12.34"); deposits positive. A "Brought Forward" line carries the opening
balance and a "Closing Balance" line the closing balance. No printed in/out totals.
Amounts are assigned to columns by the header's right edge (12 point tolerance).

Errors carry only row number, page and field type.
"""
from .common import (MONTHS, Gate, ParsedStatement, ParseRejected, Row, chain_gate,
                     group_lines, make_date, nearest_edge, parse_cents)

LAYOUT_NAME = "ING Orange Everyday short report"
DATE_COL_TOL = 25.0
_FIELD = {"dep": "deposit", "wd": "withdrawal", "bal": "balance"}


def _find_header(lines):
    for i, ws in enumerate(lines):
        t = {w["text"]: w for w in ws}
        if all(k in t for k in ("Date", "Description", "Deposit($)", "Withdrawal($)", "Balance($)")):
            return i, {"date_x": t["Date"]["x0"],
                       "edges": {"dep": t["Deposit($)"]["x1"], "wd": t["Withdrawal($)"]["x1"],
                                 "bal": t["Balance($)"]["x1"]}}
    return None


def detect(pages_words):
    return any(_find_header(group_lines(w)) for w in pages_words)


def _row_date(ws):
    if len(ws) < 3 or not (ws[0]["text"].isdigit() and len(ws[0]["text"]) == 2
                           and ws[2]["text"].isdigit() and len(ws[2]["text"]) == 4):
        return None
    m = MONTHS.get(ws[1]["text"])
    return make_date(int(ws[2]["text"]), m, int(ws[0]["text"])) if m else None


def _last_amount(ws):
    vals = [parse_cents(w["text"]) for w in ws]
    vals = [v for v in vals if v is not None]
    return vals[-1] if vals else None


def parse_pages(pages_words):
    rows, errors = [], []
    cols, opening, closing, n = None, None, None, 0
    for pageno, words in enumerate(pages_words, start=1):
        lines = group_lines(words)
        hdr = _find_header(lines)
        start = 0
        if hdr:
            idx, cols = hdr
            start = idx + 1
        if cols is None:
            continue
        for ws in lines[start:]:
            texts = [w["text"] for w in ws]
            d = _row_date(ws) if abs(ws[0]["x0"] - cols["date_x"]) <= DATE_COL_TOL else None
            if d is None:
                if texts[:2] == ["Brought", "Forward"] and opening is None:
                    opening = _last_amount(ws[2:])
                elif texts[:2] == ["Closing", "Balance"]:
                    closing = _last_amount(ws[2:])
                continue
            n += 1
            rec = {"dep": None, "wd": None, "bal": None}
            bad, desc = [], []
            for w in ws[3:]:
                amt = parse_cents(w["text"])
                key = nearest_edge(w["x1"], cols["edges"]) if amt is not None else None
                if key is None:
                    desc.append(w["text"])
                    continue
                if rec[key] is not None:
                    bad.append(key)
                rec[key] = amt
            for k in bad:
                errors.append(f"Row {n} (page {pageno}): duplicate {_FIELD[k]} value")
            if rec["bal"] is None:
                errors.append(f"Row {n} (page {pageno}): balance missing")
            if (rec["dep"] is None) == (rec["wd"] is None):
                errors.append(f"Row {n} (page {pageno}): expected exactly one of deposit or withdrawal")
                continue
            if rec["wd"] is not None:
                if rec["wd"] > 0:
                    errors.append(f"Row {n} (page {pageno}): withdrawal is not negative as expected")
                    continue
                amount = rec["wd"]
            else:
                if rec["dep"] < 0:
                    errors.append(f"Row {n} (page {pageno}): deposit is negative")
                    continue
                amount = rec["dep"]
            if rec["bal"] is not None:
                rows.append(Row(n, pageno, d, " ".join(desc), amount, rec["bal"]))
    if cols is None:
        raise ParseRejected([f"Unrecognised layout: the {LAYOUT_NAME} header row was not found. Nothing imported."])
    if opening is None or closing is None:
        raise ParseRejected(["Opening (Brought Forward) or Closing Balance line not found. Nothing imported."])
    if n == 0:
        raise ParseRejected(["No transaction rows found. Nothing imported."])
    if errors:
        raise ParseRejected(errors + ["Nothing imported."])
    sg_errs = []
    if opening + sum(r.amount_cents for r in rows) != closing:
        sg_errs.append("Statement summary: opening balance plus all parsed rows does not equal closing balance")
    return ParsedStatement(
        layout=LAYOUT_NAME, rows=rows, opening_cents=opening, closing_cents=closing,
        printed_in_cents=None, printed_out_cents=None,
        gates=[Gate("Statement gate (opening + rows = closing)", not sg_errs, sg_errs),
               chain_gate(rows, opening)])
