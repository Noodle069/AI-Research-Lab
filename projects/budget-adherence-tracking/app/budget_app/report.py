"""Slice 6: month dashboard, overspend view, trends, sinking balances, coverage warnings.

Definitions (shown on the pages):
- Regular actual = spend (flow_type 'spend') in the Regular pool, by transaction date.
- Overall actual = Regular-pool spend in every category + all Uncategorised spend. Compared with the
  total Regular budget. Sinking-pool spend is shown separately.
- Sinking balance = monthly set-aside x months from the start month to this month, minus cumulative
  Sinking-pool spend from the start month.
- Status: within (under 90%), near (90% to 100% of budget), over (above budget).
Nothing here logs or raises messages containing descriptions or amounts. Money is integer cents.
"""
import calendar
from datetime import date

from . import categorise, store

NEAR_PCT = 90
SINK_START_KEY = "sinking_start_month"


def today():
    """Wrapped so tests can set the date."""
    return date.today()


# ---------- month helpers ----------

YM_MIN, YM_MAX = "1900-01", "2100-12"   # sane window for every month the app accepts or shows
MAX_MONTHS = 12 * 201 + 1               # hard iteration guard for ym_range


def ym_ok(ym):
    return bool(categorise.YM_RE.match(ym or "")) and YM_MIN <= ym <= YM_MAX


def ym_add(ym, n):
    """Month arithmetic. Raises ValueError if the result leaves the 1900-2100 window."""
    y, m = int(ym[:4]), int(ym[5:7])
    i = y * 12 + (m - 1) + n
    out = f"{i // 12:04d}-{i % 12 + 1:02d}"
    if not (YM_MIN <= out <= YM_MAX) or len(out) != 7:
        raise ValueError("month outside supported range")
    return out


def ym_range(first, last):
    """Inclusive list of months; never more than MAX_MONTHS iterations; ValueError if out of window."""
    if not (ym_ok(first) and ym_ok(last)):
        raise ValueError("month outside supported range")
    out, cur = [], first
    while cur <= last:
        if len(out) >= MAX_MONTHS:
            raise ValueError("month range too long")
        out.append(cur)
        if cur == YM_MAX:
            break
        cur = ym_add(cur, 1)
    return out


def ym_label(ym):
    return f"{ym[5:7]}/{ym[:4]}"


def ym_bounds(ym):
    nxt = ym_add(ym, 1) if ym < YM_MAX else "2101-01"
    return f"{ym}-01", f"{nxt}-01"


def data_months(conn):
    """(first, last) 'YYYY-MM' over all transactions, or (None, None)."""
    r = conn.execute("SELECT MIN(substr(txn_date,1,7)), MAX(substr(txn_date,1,7)) FROM transactions "
                     "WHERE substr(txn_date,1,7) BETWEEN ? AND ?", (YM_MIN, YM_MAX)).fetchone()
    return (r[0], r[1]) if r[0] else (None, None)


# ---------- budget maths ----------

def status_of(actual, budget):
    """('within'|'near'|'over', percent or None). Budget 0: any spend is over, percent undefined."""
    if budget <= 0:
        return ("over" if actual > 0 else "within"), None
    pct = (actual * 200 + budget) // (2 * budget)
    if actual > budget:
        return "over", pct
    if actual * 100 >= NEAR_PCT * budget:
        return "near", pct
    return "within", pct


def _budgets(conn):
    return {r["id"]: (r["regular_cents"], r["sinking_cents"]) for r in conn.execute(
        "SELECT c.id, b.regular_cents, b.sinking_cents FROM categories c "
        "JOIN category_budgets b ON b.category_id=c.id")}


def _spend(conn, lo, hi, upto=None):
    """{(category_id or None, pool): cents spent} for lo <= date < hi (and <= upto if given)."""
    sql = ("SELECT category_id, pool, -SUM(amount_cents) AS c FROM transactions "
           "WHERE flow_type='spend' AND txn_date >= ? AND txn_date < ?")
    args = [lo, hi]
    if upto:
        sql += " AND txn_date <= ?"
        args.append(upto)
    sql += " GROUP BY category_id, pool"
    return {(r["category_id"], r["pool"]): r["c"] for r in conn.execute(sql, args)}


def _series(conn):
    """{ym: {(category_id, pool): cents}} for every month with spend rows."""
    out = {}
    for r in conn.execute(
            "SELECT substr(txn_date,1,7) AS ym, category_id, pool, -SUM(amount_cents) AS c FROM transactions "
            "WHERE flow_type='spend' GROUP BY 1,2,3"):
        out.setdefault(r["ym"], {})[(r["category_id"], r["pool"])] = r["c"]
    return out


def regular_actual_overall(spend):
    """Regular-pool spend in categories + all uncategorised spend (either pool)."""
    return sum(c for (cid, pool), c in spend.items() if (cid is not None and pool == "regular") or cid is None)


# ---------- sinking start month ----------

def get_sinking_start(conn):
    """(start_ym, is_default). Default = earliest month with data."""
    r = conn.execute("SELECT value FROM meta WHERE key=?", (SINK_START_KEY,)).fetchone()
    if r:
        return r["value"], False
    return data_months(conn)[0], True


def set_sinking_start(conn, ym):
    ym = (ym or "").strip()
    with conn:
        if ym == "":
            conn.execute("DELETE FROM meta WHERE key=?", (SINK_START_KEY,))
        elif ym_ok(ym):
            conn.execute("INSERT INTO meta(key, value) VALUES (?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                         (SINK_START_KEY, ym))
        else:
            raise categorise.Invalid("Enter the start month as a month between 1900-01 and 2100-12, for example 2025-03.")


def sinking_balances(conn, ym, start=None, series=None):
    """{category_id: {'set_aside', 'spent', 'balance', 'month_spend'}} for month ym.
    Months before the start month contribute nothing."""
    if start is None:
        start = get_sinking_start(conn)[0]
    series = series if series is not None else _series(conn)
    budgets = _budgets(conn)
    n = 0 if start is None or ym < start else len(ym_range(start, ym))
    out = {}
    for cid, (_reg, sink) in budgets.items():
        spent = sum(v for m, d in series.items() if start is not None and start <= m <= ym
                    for (c, pool), v in d.items() if c == cid and pool == "sinking")
        aside = (sink or 0) * n
        out[cid] = {"set_aside": aside, "spent": spent, "balance": aside - spent,
                    "month_spend": series.get(ym, {}).get((cid, "sinking"), 0)}
    return out


# ---------- coverage ----------

def coverage_issues(conn):
    """{ym: [(account label, 'partial'|'none')]} for months inside the imported range."""
    cov = store.coverage(conn)
    return {m["ym"]: [(c["account"]["label"], c["state"]) for c in m["cells"] if c["state"] != "full"]
            for m in cov["months"]}


def coverage_for_month(conn, ym, issues=None):
    issues = issues if issues is not None else coverage_issues(conn)
    if ym in issues:
        return issues[ym]
    # outside every statement period: each account is missing
    return [(a["label"], "none") for a in store.list_accounts(conn)]


# ---------- month dashboard ----------

def month_view(conn, ym):
    mt = categorise.month_totals(conn, ym)
    budgets = _budgets(conn)
    lo, hi = ym_bounds(ym)
    direct_total = conn.execute(
        "SELECT COALESCE(-SUM(amount_cents),0) FROM transactions WHERE flow_type='spend' "
        "AND txn_date >= ? AND txn_date < ?", (lo, hi)).fetchone()[0]
    rows, other, sinking = [], [], []
    series = _series(conn)
    start, start_default = get_sinking_start(conn)
    bal = sinking_balances(conn, ym, start, series)
    for c in mt["categories"]:
        reg_b, sink_b = budgets[c["category_id"]]
        if reg_b is not None:
            st, pct = status_of(c["regular_cents"], reg_b)
            rows.append({"id": c["category_id"], "name": c["name"], "budget": reg_b, "actual": c["regular_cents"],
                         "left": reg_b - c["regular_cents"], "pct": pct, "status": st, "count": c["count"]})
        elif c["regular_cents"]:
            other.append({"id": c["category_id"], "name": c["name"], "actual": c["regular_cents"]})
        if sink_b or c["sinking_cents"] or bal[c["category_id"]]["balance"]:
            sinking.append({"id": c["category_id"], "name": c["name"], "monthly": sink_b or 0,
                            **bal[c["category_id"]]})
    unc = mt["uncategorised"]
    budget_total = sum(r["budget"] for r in rows)
    overall_actual = sum(c["regular_cents"] for c in mt["categories"]) + unc["total_cents"]
    st, pct = status_of(overall_actual, budget_total)
    cat_reg = sum(c["regular_cents"] for c in mt["categories"])
    cat_sink = sum(c["sinking_cents"] for c in mt["categories"])
    line_sum = cat_reg + cat_sink + unc["total_cents"]
    return {
        "ym": ym, "rows": rows, "other": other, "uncategorised": unc, "sinking": sinking,
        "overall": {"budget": budget_total, "actual": overall_actual, "left": budget_total - overall_actual,
                    "pct": pct, "status": st},
        "sinking_totals": {k: sum(s[k] for s in sinking) for k in ("monthly", "month_spend", "balance")},
        "sink_start": start, "sink_start_default": start_default,
        "recon": {"cat_regular": cat_reg, "cat_sinking": cat_sink, "uncategorised": unc["total_cents"],
                  "lines": line_sum, "direct": direct_total, "ok": line_sum == direct_total},
        "coverage": coverage_for_month(conn, ym),
    }


def pace_view(conn, ym, now=None):
    """Month-to-date pace for the current month only: spent so far vs budget x days elapsed / days in month.
    Returns None for any other month."""
    now = now or today()
    if ym != f"{now.year:04d}-{now.month:02d}":
        return None
    dim = calendar.monthrange(now.year, now.month)[1]
    elapsed = now.day
    lo, hi = ym_bounds(ym)
    spend = _spend(conn, lo, hi, upto=now.isoformat())
    budgets = _budgets(conn)
    names = {c["id"]: c["name"] for c in categorise.list_categories(conn)}

    def expected(b):
        return (b * elapsed * 2 + dim) // (2 * dim)

    rows = []
    for cid, (reg_b, _s) in budgets.items():
        if reg_b is None:
            continue
        spent = spend.get((cid, "regular"), 0)
        e = expected(reg_b)
        rows.append({"name": names[cid], "spent": spent, "expected": e, "diff": spent - e,
                     "ahead": spent > e, "budget": reg_b})
    total_b = sum(r["budget"] for r in rows)
    spent_all = regular_actual_overall(spend)
    e_all = expected(total_b)
    return {"elapsed": elapsed, "days": dim, "rows": rows,
            "overall": {"spent": spent_all, "expected": e_all, "diff": spent_all - e_all,
                        "ahead": spent_all > e_all, "budget": total_b}}


# ---------- overspend view ----------

def bleeding(conn, ym, top_merchants=5, top_txns=10):
    view = month_view(conn, ym)
    lo, hi = ym_bounds(ym)
    over = []
    for r in view["rows"]:
        if r["status"] != "over":
            continue
        over_c = r["actual"] - r["budget"]
        merchants = [dict(m) for m in conn.execute(
            "SELECT COALESCE(NULLIF(payee_key,''), '(no payee name)') AS payee, -SUM(amount_cents) AS total, "
            "COUNT(*) AS n FROM transactions WHERE flow_type='spend' AND pool='regular' AND category_id=? "
            "AND txn_date >= ? AND txn_date < ? GROUP BY 1 ORDER BY total DESC, payee LIMIT ?",
            (r["id"], lo, hi, top_merchants))]
        over.append({**r, "over": over_c, "over_pct": (over_c * 100 * 2 + r["budget"]) // (2 * r["budget"])
                     if r["budget"] else None, "merchants": merchants})
    over.sort(key=lambda r: (-r["over"], r["id"]))
    ids = [r["id"] for r in over]
    txns = []
    if ids:
        marks = ",".join("?" * len(ids))
        txns = [dict(t) for t in conn.execute(
            f"SELECT t.txn_date, t.description, -t.amount_cents AS amount, c.name AS category FROM transactions t "
            f"JOIN categories c ON c.id=t.category_id WHERE t.flow_type='spend' AND t.pool='regular' "
            f"AND t.amount_cents < 0 AND t.category_id IN ({marks}) AND t.txn_date >= ? AND t.txn_date < ? "
            f"ORDER BY t.amount_cents ASC, t.id LIMIT ?", ids + [lo, hi, top_txns])]
    return {"ym": ym, "over": over, "txns": txns, "overall": view["overall"],
            "uncategorised": view["uncategorised"], "coverage": view["coverage"],
            "pace": pace_view(conn, ym)}


# ---------- trends ----------

def _bars(values, budgets, width=640, height=150):
    """Geometry for a plain SVG bar chart (actual bars, budget tick). Presentation attributes only."""
    n = len(values)
    top = max([1] + list(values) + [b for b in budgets if b])
    pad_l, pad_b = 4, 18
    ch = height - pad_b
    slot = (width - pad_l) / max(n, 1)
    bw = slot * 0.6
    out = []
    for i, (v, b) in enumerate(zip(values, budgets)):
        h = round(ch * max(v, 0) / top, 1)
        out.append({"x": round(pad_l + i * slot + (slot - bw) / 2, 1), "w": round(bw, 1),
                    "y": round(ch - h, 1), "h": h, "tx": round(pad_l + i * slot + slot / 2, 1),
                    "by": round(ch - ch * b / top, 1) if b else None,
                    "bx1": round(pad_l + i * slot, 1), "bx2": round(pad_l + (i + 1) * slot, 1),
                    "over": bool(b is not None and v > b)})
    return {"w": width, "h": height, "bars": out, "ty": height - 4}


def _line(values, width=640, height=150):
    n = len(values)
    lo, hi = min([0] + list(values)), max([0] + list(values))
    span = (hi - lo) or 1
    pad_b = 18
    ch = height - pad_b - 8

    def y(v):
        return round(4 + ch * (hi - v) / span, 1)

    step = (width - 20) / max(n - 1, 1)
    pts = [(round(10 + i * step, 1) if n > 1 else width / 2, y(v)) for i, v in enumerate(values)]
    return {"w": width, "h": height, "points": " ".join(f"{x},{yy}" for x, yy in pts),
            "zero": y(0), "xs": [p[0] for p in pts], "ty": height - 4}


def trends(conn):
    first, last = data_months(conn)
    if not first:
        return None
    months = ym_range(first, last)
    series = _series(conn)
    budgets = _budgets(conn)
    issues = coverage_issues(conn)
    start, start_default = get_sinking_start(conn)
    names = {c["id"]: c["name"] for c in categorise.list_categories(conn)}
    flags = {m: bool(coverage_for_month(conn, m, issues)) for m in months}

    overall_b = sum(b[0] or 0 for b in budgets.values())
    orows = []
    for m in months:
        a = regular_actual_overall(series.get(m, {}))
        st, pct = status_of(a, overall_b)
        orows.append({"ym": m, "budget": overall_b, "actual": a, "left": overall_b - a, "pct": pct,
                      "status": st, "cov": flags[m]})
    overall = {"rows": orows, "chart": _bars([r["actual"] for r in orows], [overall_b] * len(orows))}

    cats = []
    for cid, (reg_b, sink_b) in budgets.items():
        if reg_b is None:
            continue
        rows = []
        for m in months:
            a = series.get(m, {}).get((cid, "regular"), 0)
            st, pct = status_of(a, reg_b)
            rows.append({"ym": m, "budget": reg_b, "actual": a, "left": reg_b - a, "pct": pct, "status": st,
                         "cov": flags[m]})
        cats.append({"id": cid, "name": names[cid], "rows": rows,
                     "chart": _bars([r["actual"] for r in rows], [reg_b] * len(rows))})

    sinks = []
    bal_by_month = {m: sinking_balances(conn, m, start, series) for m in months}
    for cid, (reg_b, sink_b) in budgets.items():
        if not sink_b and not any(d.get((cid, "sinking")) for d in series.values()):
            continue
        rows = []
        for m in months:
            b = bal_by_month[m][cid]
            rows.append({"ym": m, "set_aside_month": (sink_b or 0) if start and m >= start else 0,
                         "spent_month": b["month_spend"], "balance": b["balance"], "cov": flags[m]})
        sinks.append({"id": cid, "name": names[cid], "rows": rows, "chart": _line([r["balance"] for r in rows])})
    return {"months": months, "overall": overall, "cats": cats, "sinks": sinks, "sink_start": start,
            "sink_start_default": start_default, "bad_months": [m for m in months if flags[m]],
            "issues": {m: coverage_for_month(conn, m, issues) for m in months if flags[m]}}
