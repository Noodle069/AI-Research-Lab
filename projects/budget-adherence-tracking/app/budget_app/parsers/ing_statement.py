"""ING Orange Everyday statement parser (PDF text, coordinate based).

Layout (VERIFIED in research/05): columns Date, Details, Money out, Money in, Balance.
Dates dd/mm/yyyy. Money out is printed NEGATIVE. Rows oldest-first. Column positions come
from each page's header row. All money is integer cents.

Description = the row's first line + its merchant continuation line(s), joined by single
spaces. A continuation line follows a dated row, has no date in the date column, carries no
amount, sits in the details column and is at most CONT_GAP points below the line above. The
card-detail line ("Date dd/mm/yyyy Card ####", or a bare "Card ####") is never part of the
description and ends the row's continuation lines. Other dateless text is ignored.

Errors never contain amounts or descriptions: only page/row numbers and field types.
"""
import re
from typing import List

from .common import (Gate, ParsedStatement, ParseRejected, Row, group_lines,  # noqa: F401
                     parse_cents, parse_dmy4)

LAYOUT_NAME = "ING Orange Everyday statement"
DATE_COL_TOL = 25.0  # a row date must start near the header's "Date" x position
CONT_GAP = 16.0      # max vertical distance (points) between a row line and its continuation line
_CARD_LINE = re.compile(r"^(?:Date\s+\d{2}/\d{2}/\d{2}(?:\d{2})?\b.*|Card\s+\S+)$")


def detect(pages_words):
    return any(_find_header(group_lines(w)) for w in pages_words)


def _find_header(lines):
    """Return (index, columns) for a header line, or None."""
    for i, ws in enumerate(lines):
        texts = [w["text"] for w in ws]
        if "Date" in texts and "Details" in texts and "Balance" in texts and texts.count("Money") >= 2:
            money = [w for w in ws if w["text"] == "Money"]
            bal = [w for w in ws if w["text"] == "Balance"][0]
            date_w = [w for w in ws if w["text"] == "Date"][0]
            details_w = [w for w in ws if w["text"] == "Details"][0]
            m_out, m_in = money[0], money[1]
            return i, {
                "date_x": date_w["x0"],
                "details_x": details_w["x0"] - 2,
                "out": (m_out["x0"] - 6, m_in["x0"] - 6),
                "in": (m_in["x0"] - 6, bal["x0"] - 6),
                "bal": (bal["x0"] - 6, float("inf")),
            }
    return None


def _find_summary(lines):
    """Opening balance / Total money in / Total money out / Closing balance line pair."""
    for i, ws in enumerate(lines):
        texts = [w["text"] for w in ws]
        if "Opening" in texts and "Closing" in texts and "Total" in texts:
            for nxt in lines[i + 1:i + 3]:
                vals = [parse_cents(w["text"]) for w in nxt]
                vals = [v for v in vals if v is not None]
                if len(vals) == 4:
                    return vals
            return None
    return None


def parse_pages(pages_words):
    """pages_words: list of word lists (pdfplumber extract_words output), one per page.

    Raises ParseRejected for structural problems. Otherwise returns ParsedStatement whose
    `gates` say whether the two hard gates passed.
    """
    pending = []  # description lists can still grow while later lines of the row are read
    errors: List[str] = []
    summary = None
    cols = None
    n = 0
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
        open_desc = None  # description parts of the row that may still take continuation lines
        prev_top = None
        for ws in lines[start:]:
            first = ws[0]
            top = min(w["top"] for w in ws)
            d = None
            if abs(first["x0"] - cols["date_x"]) <= DATE_COL_TOL:
                d = parse_dmy4(first["text"])
            if d is None:
                if open_desc is not None and prev_top is not None and top - prev_top <= CONT_GAP:
                    prev_top = top
                    text = " ".join(w["text"] for w in ws)
                    if _CARD_LINE.match(text):
                        open_desc = None  # card-detail line: excluded, and the row is complete
                    elif _is_continuation(ws, cols):
                        open_desc.extend(w["text"] for w in ws)
                    else:
                        open_desc = None
                else:
                    open_desc = None
                continue
            n += 1
            prev_top = top
            rec = {"out": None, "in": None, "bal": None}
            bad_fields = []
            desc = []
            open_desc = desc
            for w in ws[1:]:
                cx = (w["x0"] + w["x1"]) / 2
                amt = parse_cents(w["text"])
                placed = False
                for key in ("out", "in", "bal"):
                    lo, hi = cols[key]
                    if lo <= cx < hi:
                        if amt is not None:
                            if rec[key] is not None:
                                bad_fields.append(key)
                            rec[key] = amt
                            placed = True
                        break
                if not placed:
                    desc.append(w["text"])  # non-numeric text: part of the details
            for key in bad_fields:
                errors.append(f"Row {n} (page {pageno}): unreadable or duplicate {_FIELD[key]} value")
            if rec["bal"] is None:
                errors.append(f"Row {n} (page {pageno}): balance missing")
            if (rec["out"] is None) == (rec["in"] is None):
                errors.append(f"Row {n} (page {pageno}): expected exactly one of money out or money in")
                continue
            if rec["out"] is not None:
                if rec["out"] > 0:
                    errors.append(f"Row {n} (page {pageno}): money out is not negative as expected")
                    continue
                amount = rec["out"]
            else:
                if rec["in"] < 0:
                    errors.append(f"Row {n} (page {pageno}): money in is negative")
                    continue
                amount = rec["in"]
            if rec["bal"] is None:
                continue
            pending.append((n, pageno, d, desc, amount, rec["bal"]))

    rows: List[Row] = [Row(n_, pg, d_, " ".join(" ".join(dl).split()), a, b) for n_, pg, d_, dl, a, b in pending]
    if cols is None:
        raise ParseRejected([f"Unrecognised layout: the {LAYOUT_NAME} header row was not found. Nothing imported."])
    if summary is None:
        raise ParseRejected(["Statement summary (opening balance, totals, closing balance) not found. Nothing imported."])
    if n == 0:
        raise ParseRejected(["No transaction rows found. Nothing imported."])
    if errors:
        raise ParseRejected(errors + ["Nothing imported."])

    opening, p_in, p_out, closing = summary
    p_out = -abs(p_out)  # printed negative; normalise defensively
    return ParsedStatement(
        layout=LAYOUT_NAME, rows=rows, opening_cents=opening, closing_cents=closing,
        printed_in_cents=p_in, printed_out_cents=p_out,
        gates=[statement_gate(rows, opening, p_in, p_out, closing), row_gate(rows, opening)],
        warnings=date_order_warnings(rows),
    )


def _is_continuation(ws, cols):
    """Details-column text with no amount: every word starts at/after the details column and ends
    before the money-out column, and none of them reads as an amount."""
    for w in ws:
        if w["x0"] < cols["details_x"] - DATE_COL_TOL or (w["x0"] + w["x1"]) / 2 >= cols["out"][0]:
            return False
        if parse_cents(w["text"]) is not None:
            return False
    return True


_FIELD = {"out": "money out", "in": "money in", "bal": "balance"}


def statement_gate(rows, opening, p_in, p_out, closing) -> Gate:
    """opening + in - out = closing, using printed totals AND the parsed rows."""
    errs = []
    if opening + p_in + p_out != closing:
        errs.append("Statement summary: opening balance + total money in - total money out does not equal closing balance")
    if sum(r.amount_cents for r in rows if r.amount_cents > 0) != p_in:
        errs.append("Statement summary: sum of money in rows does not match printed total money in")
    if sum(r.amount_cents for r in rows if r.amount_cents < 0) != p_out:
        errs.append("Statement summary: sum of money out rows does not match printed total money out")
    if opening + sum(r.amount_cents for r in rows) != closing:
        errs.append("Statement summary: opening balance plus all parsed rows does not equal closing balance")
    return Gate("Statement gate (opening + in - out = closing)", not errs, errs)


def row_gate(rows, opening) -> Gate:
    """Per-row running balance, seeded by the printed opening balance."""
    errs = []
    prev = opening
    for r in rows:
        if prev + r.amount_cents != r.balance_cents:
            errs.append(f"Row {r.number} (page {r.page}): balance does not follow from the previous balance and this row's amount")
        prev = r.balance_cents  # resync so one bad row does not flag every later row
    return Gate("Row gate (running balance per row)", not errs, errs)


def date_order_warnings(rows):
    """Non-blocking. Real statements list rows in posting order, so a date can step back a
    day (observed in a real file where the balance chain still passed). The balance chain,
    not the date, is the ordering authority."""
    n = sum(1 for a, b in zip(rows, rows[1:]) if b.date < a.date)
    return [f"{n} row(s) have a date earlier than the row above (balance chain still verified)"] if n else []


def parse_pdf(fileobj) -> ParsedStatement:
    """fileobj: path or binary file-like. Raises ParseRejected on any failure."""
    import pdfplumber
    try:
        with pdfplumber.open(fileobj) as pdf:
            pages_words = [p.extract_words(x_tolerance=1.5) for p in pdf.pages]
    except Exception:
        raise ParseRejected(["Could not read the file as a PDF with selectable text. Nothing imported."])
    return parse_pages(pages_words)
