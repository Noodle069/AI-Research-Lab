"""NAB credit card statement parser.

Layout (VERIFIED against the user's real file): rows carry two dates (dd/mm/yy), a card
reference, a description and an amount with an optional CR suffix (no suffix = DR, a
purchase). No per-row balance, so only the statement gate applies. Amount text can carry
inner whitespace, so the contiguous numeric tail of each row is joined before parsing.

Summary block: "- Opening balance $x DR", "+ Payments & other credits received $x CR",
"- Purchases, cash advances $x DR", "- Interest / & other charges $x", "= Closing balance $x".
Balances are signed: negative = owed. Row amounts: purchases negative, credits positive.
Gate: sum of CR rows = payments; sum of DR rows = purchases + interest/charges;
owed opening - payments + purchases + charges = owed closing.

Errors carry only row number, page and field type.
"""
import re

from .common import (Gate, ParsedStatement, ParseRejected, Row, group_lines, make_date, parse_cents)

LAYOUT_NAME = "NAB credit card statement"
DATE_RE = re.compile(r"^(\d{2})/(\d{2})/(\d{2})$")
NUM_TAIL_RE = re.compile(r"^[\d,.$]+$")
EDGE_TOL = 12.0
GAP_MAX = 8.0


def _short_date(text):
    m = DATE_RE.match(text)
    if not m:
        return None
    return make_date(2000 + int(m.group(3)), int(m.group(2)), int(m.group(1)))


def _find_header(lines):
    """Return (index, cols) where the header block is 'Date Date ...' then 'Details ... Amount A$'."""
    for i, ws in enumerate(lines):
        dates = [w for w in ws if w["text"] == "Date"]
        if len(dates) >= 2:
            for nxt in lines[i + 1:i + 3]:
                det = [w for w in nxt if w["text"] == "Details"]
                amt = [w for w in nxt if w["text"].endswith("$") and w["x0"] > 400]
                if det and amt:
                    return i + 2, {"date_x": dates[0]["x0"], "details_x": det[0]["x0"],
                                   "amt_x1": max(w["x1"] for w in amt)}
    return None


def _has_summary(lines):
    return any(ws[0]["text"] in ("-", "+", "=") and len(ws) > 2 and ws[1]["text"] in ("Opening", "Payments", "Closing")
               for ws in lines)


def detect(pages_words):
    ls = [group_lines(w) for w in pages_words]
    return any(_find_header(x) for x in ls) and any(_has_summary(x) for x in ls)


def _summary_value(ws, label_end):
    """Joined numeric tail after the label, plus a DR/CR suffix. -> (cents or None, suffix)."""
    rest = [w for w in ws[label_end:]]
    suffix = None
    if rest and rest[-1]["text"] in ("CR", "DR"):
        suffix = rest[-1]["text"]
        rest = rest[:-1]
    tail = []
    for w in reversed(rest):
        if NUM_TAIL_RE.match(w["text"]):
            tail.insert(0, w["text"])
        else:
            break
    return (parse_cents("".join(tail)) if tail else None), suffix


def _find_summary(lines):
    out = {}
    for ws in lines:
        t = [w["text"] for w in ws]
        if not t or t[0] not in ("-", "+", "="):
            continue
        if t[1:3] == ["Opening", "balance"]:
            key, end = "opening", 3
        elif t[1] == "Payments":
            key, end = "payments", 2
        elif t[1] == "Purchases,":
            key, end = "purchases", 2
        elif t[1] == "Interest":
            key, end = "charges", 2
        elif t[1:3] == ["Closing", "balance"]:
            key, end = "closing", 3
        else:
            continue
        # skip the remaining label words: numeric tail is taken from the right
        val, suf = _summary_value(ws, end)
        if val is not None and key not in out:
            out[key] = (val, suf)
    return out


def _row(ws, cols):
    """-> (date, description, cents, kind) or a string naming the failed field type."""
    d1 = _short_date(ws[0]["text"]) if len(ws) > 2 else None
    if d1 is None:
        return None
    if _short_date(ws[1]["text"]) is None:
        return "second date"
    rest = ws[2:]
    suffix = None
    if rest and rest[-1]["text"] in ("CR", "DR"):
        suffix = rest[-1]["text"]
        rest = rest[:-1]
    tail = []
    for w in reversed(rest):
        if not NUM_TAIL_RE.match(w["text"]):
            break
        if tail and tail[0]["x0"] - w["x1"] > GAP_MAX:
            break
        tail.insert(0, w)
    if not tail:
        return "amount"
    if abs(tail[-1]["x1"] - cols["amt_x1"]) > EDGE_TOL:
        return "amount position"
    cents = parse_cents("".join(w["text"] for w in tail))
    if cents is None or cents < 0:
        return "amount"
    desc = " ".join(w["text"] for w in rest[:len(rest) - len(tail)] if w["x0"] >= cols["details_x"] - 2)
    return d1, desc, cents, ("CR" if suffix == "CR" else "DR")


def parse_pages(pages_words):
    rows, errors, cols, summary, n = [], [], None, {}, 0
    for pageno, words in enumerate(pages_words, start=1):
        lines = group_lines(words)
        for k, v in _find_summary(lines).items():
            summary.setdefault(k, v)
        hdr = _find_header(lines)
        start = 0
        if hdr:
            start, cols = hdr
        if cols is None:
            continue
        for ws in lines[start:]:
            if abs(ws[0]["x0"] - cols["date_x"]) > 25 or _short_date(ws[0]["text"]) is None:
                continue
            n += 1
            r = _row(ws, cols)
            if isinstance(r, str) or r is None:
                errors.append(f"Row {n} (page {pageno}): unreadable {r or 'date'} value")
                continue
            d, desc, cents, kind = r
            rows.append(Row(n, pageno, d, desc, cents if kind == "CR" else -cents, None))
    if cols is None:
        raise ParseRejected([f"Unrecognised layout: the {LAYOUT_NAME} header row was not found. Nothing imported."])
    missing = [k for k in ("opening", "payments", "purchases", "closing") if k not in summary]
    if missing:
        raise ParseRejected(["Statement summary block (opening, payments, purchases or closing) not found. Nothing imported."])
    if n == 0:
        raise ParseRejected(["No transaction rows found. Nothing imported."])
    if errors:
        raise ParseRejected(errors + ["Nothing imported."])

    def owed(key):  # signed: negative = owed. No suffix means DR (owed).
        v, suf = summary[key]
        return v if suf == "CR" else -v

    opening, closing = owed("opening"), owed("closing")
    payments = summary["payments"][0]
    purchases = summary["purchases"][0]
    charges = summary.get("charges", (0, None))[0]
    errs = []
    if sum(r.amount_cents for r in rows if r.amount_cents > 0) != payments:
        errs.append("Statement summary: sum of CR rows does not match printed payments and other credits")
    if -sum(r.amount_cents for r in rows if r.amount_cents < 0) != purchases + charges:
        errs.append("Statement summary: sum of DR rows does not match printed purchases (plus printed charges)")
    if opening + payments - purchases - charges != closing:
        errs.append("Statement summary: opening balance - payments + purchases does not equal closing balance")
    return ParsedStatement(
        layout=LAYOUT_NAME, rows=rows, opening_cents=opening, closing_cents=closing,
        printed_in_cents=payments, printed_out_cents=-(purchases + charges),
        gates=[Gate("Statement gate (payments, purchases, opening/closing)", not errs, errs)],
        warnings=["No per-row balance is printed on this layout, so the row gate does not apply."])
