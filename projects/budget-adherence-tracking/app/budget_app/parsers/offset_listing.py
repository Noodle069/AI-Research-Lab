"""Offset account and offset home loan transaction listing parser.

Layout (VERIFIED against the user's real files): header Date, [Transaction,] Description,
Debits, Credits, Balance (two header orders). Amounts are right-aligned and are assigned to
columns by the header's right edge (12 point tolerance). The balance is followed by a
separate CR or DR token; a DR balance is a NEGATIVE signed balance (a zero balance has no marker). Rows start "Mon dd";
the year comes from the latest "Mon yyyy" heading line (never a transaction).

Summary block: "Opening balance", "Total debits", "Total credits", "Closing balance" with
operators (+/-) between them. The printed opening balance has no CR/DR suffix; its sign is
taken from the operator in front of "Total debits": "+" means the balance is owed (DR),
"-" means it is held (CR). If that inference is wrong the gates fail rather than guess.

Errors carry only row number, page and field type.
"""
import re

from .common import (MONTHS, Gate, ParsedStatement, ParseRejected, Row, chain_gate,
                     group_lines, make_date, nearest_edge, parse_cents)

LAYOUT_NAME = "Offset account / home loan transaction listing"
DATE_COL_TOL = 25.0
_FIELD = {"debit": "debits", "credit": "credits", "bal": "balance"}
YEAR_RE = re.compile(r"^\d{4}$")


def _find_header(lines):
    for i, ws in enumerate(lines):
        t = {w["text"]: w for w in ws}
        if all(k in t for k in ("Date", "Description", "Debits", "Credits", "Balance")):
            return i, {"date_x": t["Date"]["x0"],
                       "edges": {"debit": t["Debits"]["x1"], "credit": t["Credits"]["x1"],
                                 "bal": t["Balance"]["x1"]}}
    return None


def detect(pages_words):
    return any(_find_header(group_lines(w)) for w in pages_words)


def _find_summary(lines):
    """-> dict opening/debits/credits/closing (cents, suffix) and 'debit_op' ('+' or '-'), or None."""
    for i, ws in enumerate(lines):
        t = [w["text"] for w in ws]
        if t[:2] == ["Opening", "balance"] and "Closing" in t and t.count("Total") == 2:
            op = None
            for j, w in enumerate(ws):
                if w["text"] == "Total" and j > 0 and ws[j - 1]["text"] in ("+", "-") \
                        and j + 1 < len(ws) and ws[j + 1]["text"] == "debits":
                    op = ws[j - 1]["text"]
            order = []  # label order left to right
            for j, w in enumerate(ws):
                if w["text"] == "Opening":
                    order.append("opening")
                elif w["text"] == "Total" and j + 1 < len(ws):
                    order.append("debits" if ws[j + 1]["text"] == "debits" else "credits")
                elif w["text"] == "Closing":
                    order.append("closing")
            for nxt in lines[i + 1:i + 3]:
                groups = []
                for w in nxt:
                    c = parse_cents(w["text"])
                    if c is not None:
                        groups.append([c, None])
                    elif w["text"] in ("CR", "DR") and groups:
                        groups[-1][1] = w["text"]
                if len(groups) == 4 and op and len(order) == 4:
                    out = {k: tuple(g) for k, g in zip(order, groups)}
                    out["debit_op"] = op
                    return out
            return None
    return None


def parse_pages(pages_words):
    rows, errors = [], []
    cols, summary, year, n = None, None, None, 0
    listing_opening = None
    for pageno, words in enumerate(pages_words, start=1):
        lines = group_lines(words)
        if summary is None:
            summary = _find_summary(lines)
        hdr = _find_header(lines)
        start = 0
        if hdr:
            idx, cols = hdr
            start = idx + 1
        if cols is None:
            continue
        for ws in lines[start:]:
            texts = [w["text"] for w in ws]
            near_date = abs(ws[0]["x0"] - cols["date_x"]) <= DATE_COL_TOL
            mon = MONTHS.get(texts[0]) if near_date else None
            if mon and len(ws) == 2 and YEAR_RE.match(texts[1]):
                year = int(texts[1])  # month-year heading: never a transaction
                continue
            if texts[:2] == ["Opening", "balance"] and listing_opening is None:
                listing_opening = next((parse_cents(w["text"]) for w in ws if parse_cents(w["text"]) is not None), None)
                continue
            if not (mon and len(ws) >= 3 and texts[1].isdigit() and len(texts[1]) <= 2):
                continue
            n += 1
            if year is None:
                errors.append(f"Row {n} (page {pageno}): no month-year heading before this row")
                continue
            d = make_date(year, mon, int(texts[1]))
            if d is None:
                errors.append(f"Row {n} (page {pageno}): unreadable date value")
                continue
            rec = {"debit": None, "credit": None, "bal": None}
            bad, desc, suffix, bal_x1 = [], [], None, None
            for w in ws[2:]:
                amt = parse_cents(w["text"])
                key = nearest_edge(w["x1"], cols["edges"]) if amt is not None else None
                if key is None:
                    desc.append(w["text"])
                    continue
                if rec[key] is not None:
                    bad.append(key)
                rec[key] = amt
                if key == "bal":
                    bal_x1 = w["x1"]
            if bal_x1 is not None:
                for w in ws:
                    if w["text"] in ("CR", "DR") and w["x0"] >= bal_x1 - 1:
                        suffix = w["text"]
                        if desc and desc[-1] == w["text"]:
                            desc.pop()
            for k in bad:
                errors.append(f"Row {n} (page {pageno}): duplicate {_FIELD[k]} value")
            if rec["bal"] is None:
                errors.append(f"Row {n} (page {pageno}): balance missing")
            if suffix is None and rec["bal"] == 0:
                suffix = "CR"  # a zero balance is printed without a marker (seen in a real file)
            if suffix is None and rec["bal"] is not None:
                errors.append(f"Row {n} (page {pageno}): balance CR/DR marker missing")
            if (rec["debit"] is None) == (rec["credit"] is None):
                errors.append(f"Row {n} (page {pageno}): expected exactly one of debits or credits")
                continue
            if (rec["debit"] or 0) < 0 or (rec["credit"] or 0) < 0 or (rec["bal"] or 0) < 0:
                errors.append(f"Row {n} (page {pageno}): unexpected negative value")
                continue
            if rec["bal"] is None or suffix is None:
                continue
            amount = -rec["debit"] if rec["debit"] is not None else rec["credit"]
            rows.append(Row(n, pageno, d, " ".join(desc), amount,
                            rec["bal"] if suffix == "CR" else -rec["bal"]))
    if cols is None:
        raise ParseRejected([f"Unrecognised layout: the {LAYOUT_NAME} header row was not found. Nothing imported."])
    if summary is None:
        raise ParseRejected(["Statement summary (opening, totals, closing) not found. Nothing imported."])
    if n == 0:
        raise ParseRejected(["No transaction rows found. Nothing imported."])
    if errors:
        raise ParseRejected(errors + ["Nothing imported."])

    o_val, o_suf = summary["opening"]
    if o_suf is None:
        o_suf = "DR" if summary["debit_op"] == "+" else "CR"
    opening = o_val if o_suf == "CR" else -o_val
    c_val, c_suf = summary["closing"]
    closing = c_val if c_suf == "CR" else -c_val
    p_debits, p_credits = summary["debits"][0], summary["credits"][0]
    errs = []
    if opening + p_credits - p_debits != closing:
        errs.append("Statement summary: opening balance + credits - debits does not equal closing balance")
    if sum(r.amount_cents for r in rows if r.amount_cents < 0) != -p_debits:
        errs.append("Statement summary: sum of debit rows does not match printed total debits")
    if sum(r.amount_cents for r in rows if r.amount_cents > 0) != p_credits:
        errs.append("Statement summary: sum of credit rows does not match printed total credits")
    if opening + sum(r.amount_cents for r in rows) != closing:
        errs.append("Statement summary: opening balance plus all parsed rows does not equal closing balance")
    if listing_opening is not None and listing_opening != abs(opening):
        errs.append("Statement summary: opening balance line in the listing does not match the printed opening balance")
    return ParsedStatement(
        layout=LAYOUT_NAME, rows=rows, opening_cents=opening, closing_cents=closing,
        printed_in_cents=p_credits, printed_out_cents=-p_debits,
        gates=[Gate("Statement gate (opening/closing, total debits and credits)", not errs, errs),
               chain_gate(rows, opening)],
        years_from_headings=True)
