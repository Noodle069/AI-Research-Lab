"""Shared parsing helpers: integer cents, explicit dates, line grouping."""
import re
from dataclasses import dataclass, field
from datetime import date
from typing import List, Optional

AMOUNT_RE = re.compile(r"^(-?)\$?(-?)(\d{1,3}(?:,\d{3})*|\d+)\.(\d{2})$")
DATE_DMY4_RE = re.compile(r"^(\d{2})/(\d{2})/(\d{4})$")


class ParseRejected(Exception):
    """The file is rejected as a whole. `errors` holds safe messages (no values)."""

    def __init__(self, errors):
        self.errors = list(errors)
        super().__init__("; ".join(self.errors))


def parse_cents(text):
    """'$-1,234.50' / '-1,234.50' / '$1,234.50' -> integer cents. None if not an amount."""
    m = AMOUNT_RE.match(text)
    if not m:
        return None
    if m.group(1) and m.group(2):  # double minus is malformed
        return None
    neg = bool(m.group(1) or m.group(2))
    cents = int(m.group(3).replace(",", "")) * 100 + int(m.group(4))
    return -cents if neg else cents


def parse_dmy4(text):
    """dd/mm/yyyy -> date, explicit (no locale). None if not a valid date."""
    m = DATE_DMY4_RE.match(text)
    if not m:
        return None
    d, mo, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
    try:
        return date(y, mo, d)
    except ValueError:
        return None


def group_lines(words, tol=2.0):
    """Cluster pdfplumber words into visual lines by 'top'; each line sorted left to right."""
    lines = []
    for w in sorted(words, key=lambda w: (w["top"], w["x0"])):
        if lines and abs(w["top"] - lines[-1][0]) <= tol:
            lines[-1][1].append(w)
        else:
            lines.append([w["top"], [w]])
    return [sorted(ws, key=lambda w: w["x0"]) for _, ws in lines]


def fmt_cents(c):
    sign = "-" if c < 0 else ""
    c = abs(c)
    return f"{sign}${c // 100:,}.{c % 100:02d}"


MONTHS = {m: i for i, m in enumerate(
    ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"], start=1)}


def make_date(y, m, d):
    try:
        return date(y, m, d)
    except ValueError:
        return None


def nearest_edge(x1, edges, tol=12.0):
    """Name of the header right edge closest to x1 (within tol points), else None.
    edges: dict name -> right-edge x."""
    best = None
    for name, ex in edges.items():
        dist = abs(x1 - ex)
        if dist <= tol and (best is None or dist < best[0]):
            best = (dist, name)
    return best[1] if best else None


@dataclass
class Row:
    number: int          # 1-based order of transaction rows in the file
    page: int
    date: object         # datetime.date
    description: str     # first line only (continuation lines are skipped)
    amount_cents: int    # signed: negative = money out / debit / purchase
    balance_cents: Optional[int]  # signed running balance; None where the layout prints none


@dataclass
class Gate:
    name: str
    passed: bool
    errors: List[str] = field(default_factory=list)


@dataclass
class ParsedStatement:
    layout: str
    rows: List[Row]
    opening_cents: int       # signed: negative = owed (DR)
    closing_cents: int
    printed_in_cents: Optional[int]
    printed_out_cents: Optional[int]   # normalised to negative
    gates: List[Gate]
    warnings: List[str] = field(default_factory=list)
    years_from_headings: bool = False

    @property
    def passed(self):
        return all(g.passed for g in self.gates)

    @property
    def total_in_cents(self):
        return sum(r.amount_cents for r in self.rows if r.amount_cents > 0)

    @property
    def total_out_cents(self):
        return sum(r.amount_cents for r in self.rows if r.amount_cents < 0)


def chain_gate(rows, opening, name="Row gate (running balance per row)"):
    """Per-row running balance, seeded by the printed opening balance."""
    errs = []
    prev = opening
    for r in rows:
        if prev + r.amount_cents != r.balance_cents:
            errs.append(f"Row {r.number} (page {r.page}): balance does not follow from the previous balance and this row's amount")
        prev = r.balance_cents  # resync so one bad row does not flag every later row
    return Gate(name, not errs, errs)
