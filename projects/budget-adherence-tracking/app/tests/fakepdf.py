"""Builds FAKE ING-style statement PDFs (invented data) for tests. No real data here."""
import datetime as dt


def _pdf(pages):
    """pages: list of lists of (x, top, text). Returns PDF bytes (Helvetica 9pt, Letter)."""
    objs = []

    def add(b):
        objs.append(b)
        return len(objs)

    add(b"<< /Type /Catalog /Pages 2 0 R >>")
    add(None)  # pages, filled later
    font = add(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
    kids = []
    for texts in pages:
        stream = "BT /F1 9 Tf\n"
        for x, top, t in texts:
            t = t.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
            stream += f"1 0 0 1 {x} {792 - top - 9} Tm ({t}) Tj\n"
        stream += "ET"
        sb = stream.encode("latin-1")
        cid = add(b"<< /Length %d >>\nstream\n" % len(sb) + sb + b"\nendstream")
        pid = add(("<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents %d 0 R "
                   "/Resources << /Font << /F1 %d 0 R >> >> >>" % (cid, font)).encode())
        kids.append(pid)
    objs[1] = ("<< /Type /Pages /Count %d /Kids [%s] >>" % (len(kids), " ".join(f"{k} 0 R" for k in kids))).encode()
    out = b"%PDF-1.4\n"
    offs = []
    for i, o in enumerate(objs, start=1):
        offs.append(len(out))
        out += b"%d 0 obj\n" % i + o + b"\nendobj\n"
    xref = len(out)
    out += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objs) + 1)
    for o in offs:
        out += b"%010d 00000 n \n" % o
    out += b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (len(objs) + 1, xref)
    return out


def money(c):
    s = f"{abs(c) // 100:,}.{abs(c) % 100:02d}"
    return f"$-{s}" if c < 0 else f"${s}"


def bare(c):
    s = f"{abs(c) // 100:,}.{abs(c) % 100:02d}"
    return f"-{s}" if c < 0 else s


def ing_statement(opening, txns, closing=None, printed_in=None, printed_out=None,
                  per_page=6, tamper_amount_row=None, tamper_delta=100, header=True):
    """txns: list of (date, description, signed_cents). Balances are computed correctly,
    then the PRINTED amount of `tamper_amount_row` (1-based) is altered by tamper_delta cents
    while its printed balance is left untouched (simulates a misread/altered amount)."""
    bal = opening
    computed = []
    for d, desc, amt in txns:
        bal += amt
        computed.append((d, desc, amt, bal))
    tin = sum(a for _, _, a in txns if a > 0)
    tout = sum(a for _, _, a in txns if a < 0)
    closing = bal if closing is None else closing
    printed_in = tin if printed_in is None else printed_in
    printed_out = tout if printed_out is None else printed_out

    pages = []
    chunks = [computed[i:i + per_page] for i in range(0, len(computed), per_page)] or [[]]
    n = 0
    for pi, chunk in enumerate(chunks):
        t = []
        if pi == 0:
            t += [(38, 100, "Opening"), (78, 100, "balance"), (181, 100, "Total"), (207, 100, "money"), (241, 100, "in"),
                  (323, 100, "Total"), (348, 100, "money"), (383, 100, "out"), (471, 100, "Closing"), (505, 100, "balance")]
            t += [(38, 120, money(opening)), (181, 120, money(printed_in)),
                  (323, 120, money(printed_out)), (471, 120, money(closing))]
        top = 160
        if header:
            t += [(38, top, "Date"), (103, top, "Details"), (294, top, "Money"), (328, top, "out"), (346, top, "$"),
                  (390, top, "Money"), (424, top, "in"), (435, top, "$"), (478, top, "Balance"), (517, top, "$")]
        top += 20
        for d, desc, amt, b in chunk:
            n += 1
            shown = amt + tamper_delta if n == tamper_amount_row else amt
            t.append((38, top, d.strftime("%d/%m/%Y")))
            first, *conts = desc if isinstance(desc, (list, tuple)) else [desc]
            t.append((103, top, first))
            t.append((294 if amt < 0 else 390, top, bare(shown)))
            t.append((478, top, bare(b)))
            for c in conts:  # merchant continuation lines (a list description = first line + these)
                top += 10.3
                t.append((103, top, c))
            top += 10.3
            card = f"Date {d.strftime('%d/%m/%y')} Card 1234" if conts else "Card 1234"
            t.append((103, top, card))  # card-detail line, never part of the description
            top += 14
        pages.append(t)
    return _pdf(pages)


DEFAULT_TXNS = [
    (dt.date(2025, 3, 1), "FAKE SHOP ONE", -1250),
    (dt.date(2025, 3, 2), "FAKE SALARY", 250000),
    (dt.date(2025, 3, 2), "FAKE CAFE", -675),
    (dt.date(2025, 3, 5), "FAKE UTILITY", -12345),
    (dt.date(2025, 3, 7), "FAKE REFUND", 999),
    (dt.date(2025, 3, 9), "FAKE SHOP TWO", -100000),
    (dt.date(2025, 3, 10), "FAKE SHOP THREE", -5),
    (dt.date(2025, 3, 11), "FAKE BIG PAYMENT", -123456),
]


# ---------------------------------------------------------------------------
# Layouts added in slice 3. All data is invented. Right-aligned amounts are placed so their
# right edge matches the header's right edge, like the real layouts.
# ---------------------------------------------------------------------------
MON = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
_W = {"digit": 5.004, ".": 2.502, ",": 2.502, "$": 5.004, "-": 3.0}


def _tw(text):
    return sum(_W["digit"] if c.isdigit() else _W.get(c, 5.5) for c in text)


def rt(right, top, text):
    """Right-aligned text item."""
    return (round(right - _tw(text), 1), top, text)


def usd(c):
    s = f"${abs(c) // 100:,}.{abs(c) % 100:02d}"
    return f"-{s}" if c < 0 else s


def plain(c):
    return f"{abs(c) // 100:,}.{abs(c) % 100:02d}"


def _tamper(shown, n, row, delta):
    return shown + delta if n == row else shown


def ing_short(opening, txns, closing=None, per_page=5, tamper_amount_row=None, tamper_delta=100, header=True):
    """ING short report. txns: (date, description, signed_cents); withdrawals print as -$x."""
    bal, comp = opening, []
    for d, desc, a in txns:
        bal += a
        comp.append((d, desc, a, bal))
    closing = bal if closing is None else closing
    pages, n = [], 0
    chunks = [comp[i:i + per_page] for i in range(0, len(comp), per_page)] or [[]]
    for pi, chunk in enumerate(chunks):
        t, top = [], 100
        if pi == 0:
            t += [(36, 60, "Account Type Orange Everyday")]
        if header:
            t += [(42, top, "Date"), (136, top, "Description"), (349, top, "Deposit($)"),
                  (404, top, "Withdrawal($)"), (510, top, "Balance($)")]
        top += 16
        if pi == 0:
            t += [(386, top, "Brought Forward"), rt(553, top, usd(opening))]
            top += 14
        for d, desc, a, b in chunk:
            n += 1
            shown = _tamper(a, n, tamper_amount_row, tamper_delta)
            t += [(42, top, f"{d.day:02d} {MON[d.month - 1]} {d.year}"), (136, top, desc),
                  rt(459 if a < 0 else 391, top, usd(shown)), rt(553, top, usd(b))]
            top += 14
        if pi == len(chunks) - 1:
            t += [(389, top, "Closing Balance"), rt(553, top, usd(closing))]
        pages.append(t)
    return _pdf(pages)


def nab_card(opening_owed, txns, printed_payments=None, printed_purchases=None, closing_owed=None,
             charges=0, per_page=5, tamper_amount_row=None, tamper_delta=100, split_amount_row=None):
    """NAB card. txns: (date, description, signed_cents): purchases negative (DR), credits positive (CR).
    Balances are 'owed' amounts (positive = owed, printed DR). Dates print dd/mm/yy twice."""
    pay = sum(a for _, _, a in txns if a > 0)
    pur = -sum(a for _, _, a in txns if a < 0)
    printed_payments = pay if printed_payments is None else printed_payments
    printed_purchases = pur if printed_purchases is None else printed_purchases
    closing_owed = opening_owed - pay + pur + charges if closing_owed is None else closing_owed
    p1 = [(302, 40, "Statement Summary"),
          (43, 100, "-"), (53, 100, "Opening balance"), rt(270, 100, usd(opening_owed)), (275, 100, "DR"),
          (43, 114, "+"), (53, 114, "Payments & other credits received"), rt(270, 114, usd(printed_payments)), (275, 114, "CR"),
          (43, 128, "-"), (53, 128, "Purchases, cash advances"), rt(270, 128, usd(printed_purchases)), (275, 128, "DR"),
          (43, 142, "-"), (53, 142, "Interest / & other charges"), rt(270, 142, usd(charges)),
          (43, 156, "="), (53, 156, "Closing balance"), rt(270, 156, usd(closing_owed))]
    pages = [p1]
    chunks = [txns[i:i + per_page] for i in range(0, len(txns), per_page)]
    n = 0
    for chunk in chunks:
        t = [(48, 64, "Date"), (123, 64, "Date"), (148, 64, "of"), (212, 64, "Card"),
             (250, 71, "Details"), (484, 71, "Amount"), rt(537, 71, "A$")]
        top = 98
        for d, desc, a in chunk:
            n += 1
            shown = _tamper(abs(a), n, tamper_amount_row, tamper_delta)
            ds = f"{d.day:02d}/{d.month:02d}/{d.year % 100:02d}"
            t += [(48, top, ds), (123, top, ds), (209, top, "x1234"), (250, top, desc)]
            text = plain(shown)
            if n == split_amount_row:   # PDF kerning splits the amount into two words
                cut = 2
                a1, a2 = text[:cut], text[cut:]
                t += [rt(537 - _tw(a2) - 4, top, a1), rt(537, top, a2)]
            else:
                t.append(rt(537, top, text))
            if a > 0:
                t.append((539.5, top, "CR"))
            top += 14
        pages.append(t)
    return _pdf(pages)


def offset_listing(opening, txns, closing=None, printed_debits=None, printed_credits=None,
                   loan=False, with_transaction_col=True, per_page=5, tamper_amount_row=None,
                   tamper_delta=100, header=True):
    """Offset account / home loan listing. txns: (date, description, signed_cents), credit +, debit -.
    Balances are SIGNED (negative prints as DR). `opening` is signed. `loan=True` uses the loan
    summary order (+ debits, - credits) and the loan column positions."""
    bal, comp = opening, []
    for d, desc, a in txns:
        bal += a
        comp.append((d, desc, a, bal))
    closing = bal if closing is None else closing
    debits = -sum(a for _, _, a in txns if a < 0)
    credits = sum(a for _, _, a in txns if a > 0)
    printed_debits = debits if printed_debits is None else printed_debits
    printed_credits = credits if printed_credits is None else printed_credits
    dcol, ccol, bcol = (394, 468, 541) if not with_transaction_col else (431, 488, 546)
    desc_x = 205 if with_transaction_col else 105

    def mark(c):
        return "CR" if c >= 0 else "DR"

    op_d, op_c = ("+", "-") if loan else ("-", "+")
    p1 = [(32, 60, "Opening balance"), (166, 60, op_d), (174, 60, "Total debits"), (300, 60, op_c),
          (308, 60, "Total credits"), (433, 60, "="), (441, 60, "Closing balance"),
          rt(61, 74, usd(abs(opening))), rt(231, 74, usd(printed_debits)), rt(365, 74, usd(printed_credits)),
          rt(492, 74, usd(abs(closing))), (494, 74, mark(closing))]
    pages = [p1]
    chunks = [comp[i:i + per_page] for i in range(0, len(comp), per_page)] or [[]]
    n, cur = 0, None
    for pi, chunk in enumerate(chunks):
        t, top = [], 100
        if header:
            t += [(32, top, "Date")]
            if with_transaction_col:
                t += [(90, top, "Transaction")]
            t += [(desc_x, top, "Description"), rt(dcol, top, "Debits"), rt(ccol, top, "Credits"),
                  rt(bcol, top, "Balance")]
        top += 16
        for d, desc, a, b in chunk:
            n += 1
            if cur != (d.year, d.month):
                cur = (d.year, d.month)
                t += [(32, top, MON[d.month - 1]), (52, top, str(d.year))]   # month-year heading
                top += 14
                if n == 1:
                    t += [(desc_x, top, "Opening balance"), rt(bcol, top, plain(abs(opening)))]
                    top += 14
            shown = _tamper(abs(a), n, tamper_amount_row, tamper_delta)
            t += [(32, top, MON[d.month - 1]), (52, top, f"{d.day:02d}")]
            if with_transaction_col:
                t += [(90, top, "Payment")]
            t += [(desc_x, top, desc), rt(dcol if a < 0 else ccol, top, plain(shown)),
                  rt(bcol, top, plain(abs(b))), (bcol + 4, top, mark(b))]
            top += 14
            t.append((desc_x, top, "continuation line"))   # must be skipped
            top += 14
        if pi == len(chunks) - 1:
            t += [(desc_x, top, "Closing balance"), rt(bcol, top, plain(abs(closing))), (bcol + 4, top, mark(closing))]
        pages.append(t)
    return _pdf(pages)


SHORT_TXNS = [
    (dt.date(2026, 7, 1), "FAKE PAY", 200000),
    (dt.date(2026, 7, 3), "FAKE SHOP", -4599),
    (dt.date(2026, 7, 9), "FAKE CAFE", -675),
    (dt.date(2026, 8, 2), "FAKE REFUND", 1250),
    (dt.date(2026, 8, 20), "FAKE BILL", -12345),
    (dt.date(2026, 9, 5), "FAKE SHOP TWO", -100),
    (dt.date(2026, 9, 6), "FAKE SHOP THREE", -5),
]
NAB_TXNS = [
    (dt.date(2026, 7, 29), "FAKE STORE A", -4599),
    (dt.date(2026, 7, 30), "FAKE STORE B", -12050),
    (dt.date(2026, 8, 2), "FAKE PAYMENT", 150000),
    (dt.date(2026, 8, 5), "FAKE STORE C", -105),
    (dt.date(2026, 8, 9), "FAKE REFUND", 999),
    (dt.date(2026, 8, 12), "FAKE BIG STORE", -489406),
    (dt.date(2026, 8, 20), "FAKE STORE D", -2500),
]
LIST_TXNS = [
    (dt.date(2025, 12, 29), "FAKE DEPOSIT", 500000),
    (dt.date(2025, 12, 30), "FAKE RENT", -180000),
    (dt.date(2025, 12, 31), "FAKE SHOP", -2350),
    (dt.date(2026, 1, 2), "FAKE INTEREST", 1234),
    (dt.date(2026, 1, 15), "FAKE BIG BILL", -450000),
    (dt.date(2026, 1, 16), "FAKE SHOP TWO", -5),
    (dt.date(2026, 2, 1), "FAKE TRANSFER", 250000),
]
