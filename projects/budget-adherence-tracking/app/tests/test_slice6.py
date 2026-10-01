"""Slice 6 tests: month dashboard, overspend view, trends, sinking balances, coverage, reconciliation.
Fake data only; rows are inserted directly into the test database."""
import datetime as dt
import logging
import re
import sqlite3

import pytest

from budget_app import categorise, db, report, rules as R
from budget_app.security import csrf_for
from test_app import ORIGIN, app, client  # noqa: F401 (fixtures)

D = dt.date


class Seed:
    """Direct inserts. One account with one full-month import per month it is told about."""

    def __init__(self, app):
        self.path = app.config["DB_PATH"]
        self.c = sqlite3.connect(self.path)
        self.imp = {}

    def account(self, label="Everyday", role="spending"):
        return self.c.execute("INSERT INTO accounts(label, role) VALUES (?,?)", (label, role)).lastrowid

    def statement(self, acct, start, end):
        i = self.c.execute(
            "INSERT INTO imports(account_id, file_sha256, layout, period_start, period_end, row_count, imported_at) "
            "VALUES (?,?,?,?,?,0,'2025-01-01')", (acct, f"h{self.c.execute('SELECT COUNT(*) FROM imports').fetchone()[0]}",
                                                   "x", start, end)).lastrowid
        self.imp[acct] = i
        self.c.commit()
        return i

    def txn(self, acct, date, desc, cents, cat=None, pool="regular", flow="spend"):
        self.c.execute(
            "INSERT INTO transactions(import_id, account_id, txn_date, description, amount_cents, category_id, pool, "
            "flow_type, payee_key) VALUES (?,?,?,?,?,?,?,?,?)",
            (self.imp[acct], acct, date, desc, cents, cat, pool, flow, R.payee_key(desc)))
        self.c.commit()


@pytest.fixture
def seed(app):
    s = Seed(app)
    yield s
    s.c.close()


def full_months(seed, *months, label="Everyday"):
    a = seed.account(label)
    first, last = months[0], months[-1]
    y, m = map(int, last.split("-"))
    end = (D(y + (m == 12), m % 12 + 1, 1) - dt.timedelta(days=1)).isoformat()
    seed.statement(a, f"{first}-01", end)
    return a


def view(app, ym):
    conn = db.connect(app.config["DB_PATH"])
    try:
        return report.month_view(conn, ym)
    finally:
        conn.close()


def row(v, cid):
    return next(r for r in v["rows"] if r["id"] == cid)


# ---------- budget vs actual maths ----------

def test_regular_sinking_split_and_difference(app, seed):
    a = full_months(seed, "2025-03")
    seed.txn(a, "2025-03-02", "FAKE GROCER", -50000, 2)
    seed.txn(a, "2025-03-03", "FAKE RATES", -30000, 1, "sinking")
    seed.txn(a, "2025-03-04", "FAKE POWER", -100000, 1)
    v = view(app, "2025-03")
    assert row(v, 2)["actual"] == 50000 and row(v, 2)["budget"] == 110000
    assert row(v, 2)["left"] == 60000 and row(v, 2)["pct"] == 45 and row(v, 2)["status"] == "within"
    assert row(v, 1)["actual"] == 100000          # sinking spend is not Regular actual
    assert v["overall"]["actual"] == 150000 and v["overall"]["budget"] == 1026581
    s1 = next(s for s in v["sinking"] if s["id"] == 1)
    assert s1["monthly"] == 88834 and s1["month_spend"] == 30000


def test_uncategorised_counted_in_overall_not_sinking(app, seed):
    a = full_months(seed, "2025-03")
    seed.txn(a, "2025-03-02", "FAKE GROCER", -10000, 2)
    seed.txn(a, "2025-03-03", "FAKE MYSTERY", -7777)
    seed.txn(a, "2025-03-04", "FAKE FLIGHT", -20000, 6, "sinking")
    v = view(app, "2025-03")
    assert v["uncategorised"]["total_cents"] == 7777
    assert v["overall"]["actual"] == 10000 + 7777        # sinking excluded from overall
    assert v["recon"]["direct"] == 37777 and v["recon"]["ok"]


def test_transfer_income_savings_excluded(app, seed):
    a = full_months(seed, "2025-03")
    seed.txn(a, "2025-03-02", "FAKE GROCER", -10000, 2)
    seed.txn(a, "2025-03-03", "FAKE TRANSFER", -90000, 2, flow="transfer")
    seed.txn(a, "2025-03-04", "FAKE SALARY", 500000, None, flow="income")
    seed.txn(a, "2025-03-05", "FAKE SAVE", -40000, 2, flow="savings")
    v = view(app, "2025-03")
    assert row(v, 2)["actual"] == 10000 and v["overall"]["actual"] == 10000
    assert v["recon"]["direct"] == 10000


@pytest.mark.parametrize("actual,status,pct", [
    (0, "within", 0), (35999, "within", 90), (36000, "near", 90), (40000, "near", 100),
    (40001, "over", 100), (44000, "over", 110)])
def test_status_thresholds_category_3(actual, status, pct):
    # category 3 budget is 40000
    got_status, got_pct = report.status_of(actual, 40000)
    assert got_status == status and got_pct == pct


def test_status_zero_budget_and_buffer_rows(app, seed):
    assert report.status_of(0, 0) == ("within", None) and report.status_of(1, 0) == ("over", None)
    a = full_months(seed, "2025-03")
    seed.txn(a, "2025-03-02", "FAKE REPAIR", -25000, 9)
    seed.txn(a, "2025-03-02", "FAKE HOLIDAY", -100, 6)          # category 6 regular budget is 0 -> over
    v = view(app, "2025-03")
    assert [o["id"] for o in v["other"]] == [9] and v["other"][0]["actual"] == 25000
    assert 9 not in [r["id"] for r in v["rows"]] and 10 not in [r["id"] for r in v["rows"]]
    assert row(v, 6)["status"] == "over" and row(v, 6)["pct"] is None
    assert v["overall"]["actual"] == 25100            # buffer spend counts in the overall actual


def test_buffer_and_spare_rows_hidden_when_no_spend(app, seed):
    a = full_months(seed, "2025-03")
    seed.txn(a, "2025-03-02", "FAKE GROCER", -100, 2)
    assert view(app, "2025-03")["other"] == []


# ---------- sinking balance ----------

def test_sinking_balance_default_start_is_earliest_month(app, seed):
    a = full_months(seed, "2025-01", "2025-02", "2025-03")
    seed.txn(a, "2025-01-10", "FAKE X", -1000, 8)
    seed.txn(a, "2025-02-10", "FAKE RATES", -50000, 1, "sinking")
    v = view(app, "2025-03")
    s1 = next(s for s in v["sinking"] if s["id"] == 1)
    assert v["sink_start"] == "2025-01" and v["sink_start_default"]
    assert s1["set_aside"] == 3 * 88834 and s1["spent"] == 50000 and s1["balance"] == 3 * 88834 - 50000
    assert s1["month_spend"] == 0
    s8 = next(s for s in v["sinking"] if s["id"] == 8)
    assert s8["balance"] == 3 * 27500


def test_sinking_start_month_user_set(app, client, seed):
    a = full_months(seed, "2025-01", "2025-02", "2025-03")
    seed.txn(a, "2025-01-10", "FAKE RATES", -99999, 1, "sinking")     # before start: ignored
    seed.txn(a, "2025-03-10", "FAKE RATES", -10000, 1, "sinking")
    r = client.post("/month/sinking-start", data={"csrf": csrf_for(app), "start": "2025-03", "back": "2025-03"},
                    headers={"Origin": ORIGIN})
    assert r.status_code == 302
    v = view(app, "2025-03")
    s1 = next(s for s in v["sinking"] if s["id"] == 1)
    assert v["sink_start"] == "2025-03" and not v["sink_start_default"]
    assert s1["set_aside"] == 88834 and s1["spent"] == 10000 and s1["balance"] == 78834
    page = client.get("/month/2025-03").get_data(as_text=True)
    assert "Sinking start month saved." in page
    # a month before the start shows nothing set aside
    s1b = next(s for s in view(app, "2025-02")["sinking"] if s["id"] == 1)
    assert s1b["set_aside"] == 0 and s1b["balance"] == 0
    # blank = back to default
    client.post("/month/sinking-start", data={"csrf": csrf_for(app), "start": "", "back": "2025-03"},
                headers={"Origin": ORIGIN})
    assert view(app, "2025-03")["sink_start_default"]


def test_sinking_start_rejects_junk(app, client, seed):
    full_months(seed, "2025-03")
    client.post("/month/sinking-start", data={"csrf": csrf_for(app), "start": "2025-13", "back": "x"},
                headers={"Origin": ORIGIN})
    assert view(app, "2025-03")["sink_start_default"]
    assert "Enter the start month" in client.get("/month/2025-03").get_data(as_text=True)


# ---------- pace ----------

def pace(app, ym, today):
    conn = db.connect(app.config["DB_PATH"])
    try:
        return report.pace_view(conn, ym, today)
    finally:
        conn.close()


def test_pace_calculation_current_month_only(app, seed):
    a = full_months(seed, "2025-03")
    seed.txn(a, "2025-03-03", "FAKE CAFE", -15000, 3)
    seed.txn(a, "2025-03-20", "FAKE CAFE", -9000, 3)      # after "today": not counted in the pace
    p = pace(app, "2025-03", D(2025, 3, 10))
    r3 = next(r for r in p["rows"] if r["name"].startswith("Eating"))
    assert p["elapsed"] == 10 and p["days"] == 31
    assert r3["expected"] == 12903 and r3["spent"] == 15000 and r3["diff"] == 2097 and r3["ahead"]
    assert p["overall"]["expected"] == (1026581 * 10 * 2 + 31) // 62 and p["overall"]["spent"] == 15000
    assert not p["overall"]["ahead"]
    assert pace(app, "2025-02", D(2025, 3, 10)) is None


def test_pace_on_last_day_equals_budget(app, seed):
    full_months(seed, "2025-03")
    p = pace(app, "2025-03", D(2025, 3, 31))
    assert next(r for r in p["rows"] if r["budget"] == 40000)["expected"] == 40000


def test_pace_wording_on_page(app, client, seed, monkeypatch):
    a = full_months(seed, "2025-03")
    seed.txn(a, "2025-03-03", "FAKE CAFE", -15000, 3)
    monkeypatch.setattr(report, "today", lambda: D(2025, 3, 10))
    page = client.get("/bleeding/2025-03").get_data(as_text=True)
    assert "a pace, not a verdict" in page and "Ahead of pace" in page
    monkeypatch.setattr(report, "today", lambda: D(2025, 4, 10))
    assert "Month-to-date pace" not in client.get("/bleeding/2025-03").get_data(as_text=True)


# ---------- overspend view ----------

def bleed(app, ym):
    conn = db.connect(app.config["DB_PATH"])
    try:
        return report.bleeding(conn, ym)
    finally:
        conn.close()


def test_overspend_ranking_merchants_and_largest(app, seed):
    a = full_months(seed, "2025-03")
    seed.txn(a, "2025-03-02", "FAKE BURGERS 1111", -30000, 3)       # cat 3 budget 40000
    seed.txn(a, "2025-03-05", "FAKE BURGERS 2222", -20000, 3)
    seed.txn(a, "2025-03-06", "FAKE SUSHI", -5000, 3)
    seed.txn(a, "2025-03-07", "FAKE SUSHI", -2500, 3)
    seed.txn(a, "2025-03-08", "FAKE BARBER", -60000, 7)             # cat 7 budget 47300 -> over 12700
    seed.txn(a, "2025-03-09", "FAKE GROCER", -10000, 2)             # within
    seed.txn(a, "2025-03-10", "FAKE TRAVEL", -900000, 6, "sinking")  # sinking: never an overspend
    b = bleed(app, "2025-03")
    assert [o["id"] for o in b["over"]] == [3, 7]                    # 17500 over, then 12700
    o3 = b["over"][0]
    assert o3["over"] == 17500 and o3["over_pct"] == 44 and o3["actual"] == 57500   # 17500/40000 = 43.75
    assert [(m["payee"], m["total"], m["n"]) for m in o3["merchants"]] == [
        ("FAKE BURGERS", 50000, 2), ("FAKE SUSHI", 7500, 2)]
    assert [t["amount"] for t in b["txns"]] == [60000, 30000, 20000, 5000, 2500]
    assert {t["category"] for t in b["txns"]} == {"Eating Out + Convenience", "Personal + Fun"}


def test_overspend_none_and_unnamed_payee(app, seed):
    a = full_months(seed, "2025-03")
    seed.txn(a, "2025-03-02", "EFTPOS Purchase - Receipt 123456", -50000, 3)
    b = bleed(app, "2025-03")
    assert b["over"][0]["merchants"][0]["payee"] == "(no payee name)"
    seed.c.execute("DELETE FROM transactions")
    seed.c.commit()
    assert bleed(app, "2025-03")["over"] == []


def test_bleeding_page_renders_payees_but_not_in_urls(app, client, seed):
    a = full_months(seed, "2025-03")
    seed.txn(a, "2025-03-02", "ZZQ BURGERS", -50000, 3)
    page = client.get("/bleeding/2025-03").get_data(as_text=True)
    assert "ZZQ BURGERS" in page and "Percent over" in page and "$100.00" in page and "25%" in page
    assert not [h for h in re.findall(r'href="([^"]*)"', page) if "ZZQ" in h]
    assert "No category is over" not in page


# ---------- trends ----------

def test_trends_table_chart_and_sinking(app, client, seed):
    a = full_months(seed, "2025-01", "2025-02", "2025-03")
    seed.txn(a, "2025-01-05", "FAKE CAFE", -10000, 3)
    seed.txn(a, "2025-02-05", "FAKE CAFE", -45000, 3)
    seed.txn(a, "2025-03-05", "FAKE RATES", -20000, 1, "sinking")
    conn = db.connect(app.config["DB_PATH"])
    t = report.trends(conn)
    conn.close()
    assert t["months"] == ["2025-01", "2025-02", "2025-03"]
    c3 = next(c for c in t["cats"] if c["id"] == 3)
    assert [(r["actual"], r["status"]) for r in c3["rows"]] == [(10000, "within"), (45000, "over"), (0, "within")]
    assert [r["actual"] for r in t["overall"]["rows"]] == [10000, 45000, 0]
    assert [b["over"] for b in c3["chart"]["bars"]] == [False, True, False]
    s1 = next(s for s in t["sinks"] if s["id"] == 1)
    assert [r["balance"] for r in s1["rows"]] == [88834, 2 * 88834, 3 * 88834 - 20000]
    page = client.get("/trends").get_data(as_text=True)
    assert page.count("<svg") >= len(t["cats"]) + 1 + len(t["sinks"])
    assert "01/2025" in page and "03/2025" in page and "<polyline" in page
    assert "<script" not in page and "http://" not in page.replace("http://www.w3.org", "")


def test_trends_and_pages_empty_database(client):
    for path in ("/trends", "/month", "/bleeding"):
        r = client.get(path)
        assert r.status_code == 200 and "No transactions yet" in r.get_data(as_text=True)


# ---------- coverage warning ----------

def test_coverage_warning_partial_and_missing(app, client, seed):
    a = seed.account("Everyday")
    seed.statement(a, "2025-02-01", "2025-03-31")
    b = seed.account("Card", "credit_card")
    seed.statement(b, "2025-03-01", "2025-03-15")             # March partial, February missing
    seed.txn(a, "2025-02-05", "FAKE CAFE", -100, 3)
    seed.txn(a, "2025-03-05", "FAKE CAFE", -100, 3)
    feb = client.get("/month/2025-02").get_data(as_text=True)
    mar = client.get("/month/2025-03").get_data(as_text=True)
    assert "Coverage warning" in feb and "Card (no data)" in feb
    assert "Coverage warning" in mar and "Card (part of the month)" in mar and "Everyday" not in mar.split("Coverage warning")[1].split("</div>")[0]
    t = client.get("/trends").get_data(as_text=True)
    assert "Coverage warning" in t and "Partial coverage" in t


def test_no_coverage_warning_when_full(app, client, seed):
    a = full_months(seed, "2025-03")
    seed.txn(a, "2025-03-05", "FAKE CAFE", -100, 3)
    assert "Coverage warning" not in client.get("/month/2025-03").get_data(as_text=True)
    assert "Coverage warning" not in client.get("/trends").get_data(as_text=True)


# ---------- reconciliation ----------

def test_reconciliation_line_ok_and_detects_mismatch(app, client, seed, monkeypatch):
    a = full_months(seed, "2025-03")
    seed.txn(a, "2025-03-02", "FAKE GROCER", -10000, 2)
    seed.txn(a, "2025-03-03", "FAKE RATES", -3000, 1, "sinking")
    seed.txn(a, "2025-03-04", "FAKE MYSTERY", -500)
    page = client.get("/month/2025-03").get_data(as_text=True)
    assert "OK:" in page and "$135.00" in page and "MISMATCH" not in page
    real = categorise.month_totals

    def broken(conn, ym):
        d = real(conn, ym)
        d["categories"] = d["categories"][1:]          # drop a category line
        return d

    monkeypatch.setattr(categorise, "month_totals", broken)
    assert "MISMATCH" in client.get("/month/2025-03").get_data(as_text=True)


# ---------- navigation ----------

def test_month_navigation(app, client, seed):
    a = full_months(seed, "2025-01", "2025-02", "2025-03")
    seed.txn(a, "2025-01-05", "FAKE CAFE", -100, 3)
    seed.txn(a, "2025-03-05", "FAKE CAFE", -100, 3)
    r = client.get("/month")
    assert r.status_code == 302 and r.headers["Location"].endswith("/month/2025-03")
    assert client.get("/bleeding").headers["Location"].endswith("/bleeding/2025-03")
    last = client.get("/month/2025-03").get_data(as_text=True)
    assert 'href="/month/2025-02"' in last and 'href="/month/2025-04"' not in last
    mid = client.get("/month/2025-02").get_data(as_text=True)
    assert 'href="/month/2025-01"' in mid and 'href="/month/2025-03"' in mid
    first = client.get("/month/2025-01").get_data(as_text=True)
    assert 'href="/month/2024-12"' not in first
    assert client.get("/month/2025-13").status_code == 404 and client.get("/month/abc").status_code == 404
    nav = client.get("/").get_data(as_text=True)
    for p in ("/month", "/bleeding", "/trends"):
        assert f'href="{p}"' in nav


def test_ym_helpers():
    assert report.ym_add("2025-12", 1) == "2026-01" and report.ym_add("2025-01", -1) == "2024-12"
    assert report.ym_range("2024-11", "2025-02") == ["2024-11", "2024-12", "2025-01", "2025-02"]
    assert report.ym_label("2025-03") == "03/2025"


# ---------- privacy and security ----------

def test_no_merchants_or_amounts_in_logs_or_errors(app, client, seed, caplog):
    a = full_months(seed, "2025-03")
    seed.txn(a, "2025-03-02", "ZZQ BURGERS", -54321, 3)
    caplog.set_level(logging.DEBUG)
    client.get("/month/2025-03")
    client.get("/bleeding/2025-03")
    client.get("/trends")
    bad = client.get("/month/ZZQ")
    client.post("/month/sinking-start", data={"csrf": csrf_for(app), "start": "ZZQ", "back": "ZZQ"},
                headers={"Origin": ORIGIN})
    text = caplog.text + bad.get_data(as_text=True)
    assert "ZZQ BURGERS" not in text and "543.21" not in text and "54321" not in text
    # the flash for a bad start month names neither the value nor any amount
    page = client.get("/month/2025-03").get_data(as_text=True)
    assert "Enter the start month" in page and "ZZQ" not in page


def test_new_pages_csp_and_no_inline_script(app, client, seed):
    a = full_months(seed, "2025-03")
    seed.txn(a, "2025-03-02", "FAKE CAFE", -50000, 3)
    for path in ("/month/2025-03", "/bleeding/2025-03", "/trends"):
        r = client.get(path)
        assert r.status_code == 200
        assert "default-src 'self'" in r.headers["Content-Security-Policy"]
        body = r.get_data(as_text=True)
        assert "<script" not in body and "style=" not in body and "onclick" not in body
        assert "http://" not in body.replace("http://www.w3.org", "") and "https://" not in body


def test_sinking_start_post_needs_csrf(app, client, seed):
    full_months(seed, "2025-03")
    r = client.post("/month/sinking-start", data={"start": "2025-03"}, headers={"Origin": ORIGIN})
    assert r.status_code == 403
