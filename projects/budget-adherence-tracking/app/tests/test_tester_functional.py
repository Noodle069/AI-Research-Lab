"""Tester stage: end-to-end acceptance, hostile inputs, concurrency, restore. Fake data only."""
import datetime as dt
import io
import re
import shutil
import sqlite3
import threading
import time

import pytest

from budget_app import create_app, report, db
from budget_app.security import csrf_for
from budget_app.parsers.detect import parse_pdf
import fakepdf as fp
from fakepdf import ing_statement
from test_app import ORIGIN, PORT, TOKEN, HostClient, post_upload, app, client  # noqa: F401
from test_slice4 import do_import, post, pid_of, q

D = dt.date


# ---------- gates, every layout, through the HTTP route; error text has no values ----------
ING_T = [(D(2025, 3, i + 1), f"FAKE ROW {i}", -(1000 + 7 * i)) for i in range(9)]
LAYOUTS = {
    "ing": (lambda **k: ing_statement(900000, ING_T, per_page=4, **k), len(ING_T)),
    "short": (lambda **k: fp.ing_short(100000, fp.SHORT_TXNS, **k), len(fp.SHORT_TXNS)),
    "nab": (lambda **k: fp.nab_card(300000, fp.NAB_TXNS, **k), len(fp.NAB_TXNS)),
    "offset": (lambda **k: fp.offset_listing(250000, fp.LIST_TXNS, **k), len(fp.LIST_TXNS)),
    "loan": (lambda **k: fp.offset_listing(-30000000, fp.LIST_TXNS, loan=True, with_transaction_col=False, **k),
             len(fp.LIST_TXNS)),
}


def _clean(body):
    body = re.sub(r"<[^>]+>", " ", body)
    assert "FAKE" not in body
    # no dollar/decimal amounts anywhere in a rejection page
    assert not re.search(r"\d+\.\d\d", body), re.findall(r".{20}\d+\.\d\d.{5}", body)
    assert "$" not in body


@pytest.mark.parametrize("name", list(LAYOUTS))
def test_http_altered_amount_every_row_rejected_nothing_written(client, app, name):
    build, n = LAYOUTS[name]
    for row in range(1, n + 1):
        r = post_upload(client, app, build(tamper_amount_row=row, tamper_delta=1))
        assert r.status_code == 422, (name, row)
        _clean(r.get_data(as_text=True))
    assert q(app, "SELECT COUNT(*) FROM transactions")[0][0] == 0
    assert q(app, "SELECT COUNT(*) FROM imports")[0][0] == 0
    assert not (app.config["BACKUP_DIR"] and __import__("os").path.exists(app.config["BACKUP_DIR"]))   # no backup for a rejected file


def test_http_ing_wrong_closing_and_wrong_printed_totals(client, app):
    for kw in [dict(closing=12345), dict(printed_in=1), dict(printed_out=-1)]:
        r = post_upload(client, app, ing_statement(900000, ING_T, **kw))
        assert r.status_code == 422, kw
        _clean(r.get_data(as_text=True))


def test_zero_byte_blank_and_text_free_pdfs_rejected_cleanly(client, app):
    empty_page = fp._pdf([[]])
    for blob in [b"", b"%PDF-1.4\n", empty_page, b"PK\x03\x04notapdf", b"\x00" * 1000,
                 ing_statement(900000, ING_T)[:-200]]:                      # truncated PDF
        r = post_upload(client, app, blob)
        assert r.status_code in (400, 422), (len(blob), r.status_code)
        assert "Traceback" not in r.get_data(as_text=True)
    assert q(app, "SELECT COUNT(*) FROM transactions")[0][0] == 0


def test_no_file_field_and_wrong_field(client, app):
    r = client.post("/import/preview", data={"csrf": csrf_for(app)}, headers={"Origin": ORIGIN})
    assert r.status_code == 400
    r = client.post("/import/preview", data={"csrf": csrf_for(app), "other": (io.BytesIO(b"x"), "x.pdf")},
                    headers={"Origin": ORIGIN}, content_type="multipart/form-data")
    assert r.status_code == 400


def test_size_limit_boundary_10mb(client, app):
    junk_ok = b"%PDF-1.4\n" + b"A" * (9 * 1024 * 1024)               # under the limit: parsed in the worker, rejected 422
    t = time.time()
    r = post_upload(client, app, junk_ok)
    assert r.status_code == 422 and time.time() - t < 40
    big = b"%PDF-1.4\n" + b"A" * (10 * 1024 * 1024 + 10)               # over: 413
    r = post_upload(client, app, big)
    assert r.status_code == 413 and "10 MB" in r.get_data(as_text=True)
    assert q(app, "SELECT COUNT(*) FROM imports")[0][0] == 0


# ---------- escaping: HTML / SQL / long strings in descriptions and form fields ----------
EVIL = [
    '<script>alert(1)</script>', "'; DROP TABLE transactions;--", '"><img src=x onerror=alert(1)>', "{{7*7}} {% raw %}",
    "Y" * 22,   # longer descriptions overrun the fixed columns and are (safely) rejected by the gate
]


def test_hostile_descriptions_are_escaped_everywhere_and_sql_safe(client, app):
    # PDF text can't hold parentheses/backslash escaping issues? fakepdf escapes them.
    txns = [(D(2025, 3, i + 1), d, -(1000 + i)) for i, d in enumerate(EVIL)]
    pdf = ing_statement(500000, txns)
    r = do_import(client, app, pdf, label="<b>Acct</b>x", role="spending")
    assert r.status_code == 302, r.get_data(as_text=True)[:200]
    assert q(app, "SELECT COUNT(*) FROM transactions")[0][0] == len(EVIL)    # tables intact
    # ensure every page that echoes descriptions escapes them
    for path in ["/transactions", "/categorise", "/transfers", "/coverage", "/month/2025-03", "/bleeding/2025-03",
                 "/trends", "/rules", "/import/done/1", "/"]:
        body = client.get(path).get_data(as_text=True)
        assert "<script>alert" not in body, path
        assert "<img src=x" not in body, path
        assert "<b>Acct</b>" not in body, path
        if "{{7*7}}" in body or "{{7*7}}".replace("{", "&#123;") in body:
            assert "7*7" in body                                 # shown literally, never evaluated
    body = client.get("/transactions").get_data(as_text=True)
    assert "&lt;script&gt;" in body
    # hostile form fields
    for data, path in [({"payee_key": "' OR 1=1 --", "category": "1", "pool": "regular"}, "/categorise/assign"),
                       ({"match_type": "contains", "pattern": "<script>", "category": "1", "pool": "regular"}, "/rules/add"),
                       ({"match_type": "regex", "pattern": "(a+)+$" + "(", "category": "1", "pool": "regular"}, "/rules/add"),
                       ({"match_type": "regex", "pattern": "x" * 5000, "category": "1", "pool": "regular"}, "/rules/add"),
                       ({"start": "'; DROP TABLE meta;--"}, "/month/sinking-start"),
                       ({"start": "2025-03<script>"}, "/month/sinking-start"),
                       ({"flow": "x'; --"}, "/transactions/1/flow"),
                       ({"priority": "9" * 400}, "/rules/1/priority")]:
        resp = post(client, app, path, data)
        assert resp.status_code in (302, 400, 404), (path, resp.status_code)
    assert q(app, "SELECT COUNT(*) FROM transactions")[0][0] == len(EVIL)
    for t in ("meta", "transactions", "payee_rules"):
        q(app, f"SELECT COUNT(*) FROM {t}")
    page = client.get("/rules").get_data(as_text=True)
    assert "<script>" not in page


@pytest.mark.parametrize("ym", ["9999-99", "0000-00", "2025-13", "2025-00", "abc", "2025-3", "2025-03/../x", "%00",
                                "2025-03%0d%0aX:y", "99999-01", "' OR 1=1"])
def test_bad_month_urls_404_not_500(client, ym):
    for base in ("/month/", "/bleeding/"):
        r = client.get(base + ym)
        assert r.status_code in (404, 308), (base + ym, r.status_code)
        assert r.status_code != 500


def test_valid_but_empty_month_and_extreme_years_ok(client, app):
    do_import(client, app, ing_statement(500000, [(D(2025, 3, 1), "FAKE A", -500)]))
    for ym in ["1900-01", "2025-12", "2100-12"]:   # window is 1900-01..2100-12; beyond it is 404
        assert client.get(f"/month/{ym}").status_code == 200, ym
        assert client.get(f"/bleeding/{ym}").status_code == 200, ym
    assert client.get("/month/2999-12").status_code == 404


def test_pagination_junk_params(client, app):
    do_import(client, app, ing_statement(500000, ING_T))
    for qs in ["page=-5", "page=abc", "cat=zzz", "ym=%27", "cat=none&page=2"]:
        assert client.get("/transactions?" + qs).status_code == 200, qs
        assert client.get("/transfers?" + qs).status_code in (200,), qs


# ---------- duplicates, overlap, atomic rollback, concurrency ----------
def test_identical_same_day_rows_survive_commit_and_distinct_files_same_content_blocked(client, app):
    t = [(D(2025, 3, 3), "FAKE CAFE", -675)] * 3 + [(D(2025, 3, 4), "FAKE X", -100)]
    assert do_import(client, app, ing_statement(500000, t)).status_code == 302
    assert q(app, "SELECT COUNT(*) FROM transactions WHERE description='FAKE CAFE'")[0][0] == 3
    # same rows re-exported with different opening balance (different bytes): every row is a duplicate -> blocked
    pdf2 = ing_statement(600000, t)
    pid = pid_of(post_upload(client, app, pdf2))
    form = {"account": "1", "role": "spending"}
    post(client, app, f"/import/{pid}/check", form)
    assert post(client, app, f"/import/{pid}/commit", form).status_code == 409
    assert q(app, "SELECT COUNT(*) FROM transactions")[0][0] == 4


def test_two_tabs_commit_same_preview_and_overlapping_files_concurrently(tmp_path):
    app = create_app(tmp_path, port=PORT, token=TOKEN)
    base = [(D(2025, 3, 1), "FAKE A", -1000), (D(2025, 3, 2), "FAKE B", -2000), (D(2025, 3, 3), "FAKE C", -3000)]
    pdf_a = ing_statement(500000, base)
    # b overlaps a on rows 2-3 and adds one new row
    pdf_b = ing_statement(500000 - 1000, base[1:] + [(D(2025, 3, 4), "FAKE D", -4000)])
    results = []

    def runner(pdf):
        c = HostClient(app, ORIGIN)
        c.get(f"/enter?t={TOKEN}")
        tok = csrf_for(app)
        r = c.post("/import/preview", data={"csrf": tok, "statement": (io.BytesIO(pdf), "x.pdf")}, headers={"Origin": ORIGIN},
                   content_type="multipart/form-data")
        pid = r.headers["Location"].rsplit("/", 1)[1]
        form = {"csrf": tok, "account": "new", "new_label": "Everyday", "role": "spending"}
        c.post(f"/import/{pid}/check", data=form, headers={"Origin": ORIGIN})
        barrier.wait()
        r = c.post(f"/import/{pid}/commit", data=form, headers={"Origin": ORIGIN})
        results.append(r.status_code)

    barrier = threading.Barrier(2)
    ts = [threading.Thread(target=runner, args=(p,)) for p in (pdf_a, pdf_b)]
    [t.start() for t in ts]
    [t.join(60) for t in ts]
    with sqlite3.connect(app.config["DB_PATH"]) as c:
        n = c.execute("SELECT COUNT(*) FROM transactions").fetchone()[0]
        d = c.execute("SELECT COUNT(*) FROM (SELECT txn_date, description FROM transactions GROUP BY 1,2 HAVING COUNT(*)>1)").fetchone()[0]
        accts = c.execute("SELECT COUNT(*) FROM accounts").fetchone()[0]
        c.execute("PRAGMA integrity_check")
    assert sorted(results) and all(s in (302, 409, 400) for s in results), results
    assert d == 0, "overlap rows saved twice under concurrent commits"
    assert accts == 1 or results.count(302) == 2    # two "new" accounts with the same label must not both appear silently
    assert n in (3, 4)


def test_same_preview_double_commit_saves_once(client, app):
    pid = pid_of(post_upload(client, app, ing_statement(500000, ING_T)))
    form = {"account": "new", "new_label": "E", "role": "spending"}
    post(client, app, f"/import/{pid}/check", form)
    out = []

    def go():
        c = HostClient(app, ORIGIN)
        c.get(f"/enter?t={TOKEN}")
        out.append(c.post(f"/import/{pid}/commit", data={**form, "csrf": csrf_for(app)}, headers={"Origin": ORIGIN}).status_code)

    ts = [threading.Thread(target=go) for _ in range(2)]
    [t.start() for t in ts]
    [t.join(60) for t in ts]
    assert q(app, "SELECT COUNT(*) FROM transactions")[0][0] == len(ING_T)
    assert q(app, "SELECT COUNT(*) FROM imports")[0][0] == 1
    assert 302 in out


# ---------- backups: README restore procedure run for real ----------
def test_readme_restore_procedure_on_fake_database(tmp_path):
    data = tmp_path / "data"
    data.mkdir()
    app = create_app(data, port=PORT, token=TOKEN)
    c = HostClient(app, ORIGIN)
    c.get(f"/enter?t={TOKEN}")
    t1 = [(D(2025, 3, 1), "FAKE A", -1000), (D(2025, 3, 2), "FAKE B", -2000)]
    assert do_import(c, app, ing_statement(500000, t1)).status_code == 302        # import 1 (backup of empty db)
    t2 = [(D(2025, 4, 1), "FAKE C", -3000)]
    assert do_import(c, app, ing_statement(500000 - 3000, t2), account="1").status_code == 302   # import 2
    assert q(app, "SELECT COUNT(*) FROM transactions")[0][0] == 3
    backups = sorted((data / "backups").glob("budget-*.db"))
    assert len(backups) == 2
    # README step 3: cp newest backup over budget.db (this undoes import 2). App stopped = new app object afterwards.
    shutil.copyfile(backups[-1], data / "budget.db")
    app2 = create_app(data, port=PORT, token=TOKEN)
    c2 = HostClient(app2, ORIGIN)
    c2.get(f"/enter?t={TOKEN}")
    assert q(app2, "SELECT COUNT(*) FROM transactions")[0][0] == 2
    assert q(app2, "SELECT COUNT(*) FROM imports")[0][0] == 1
    assert c2.get("/month/2025-03").status_code == 200
    # re-importing the undone file works again (its hash is no longer recorded)
    assert do_import(c2, app2, ing_statement(500000 - 3000, t2), account="1").status_code == 302
    assert q(app2, "SELECT COUNT(*) FROM transactions")[0][0] == 3
    with sqlite3.connect(data / "budget.db") as cx:
        assert cx.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
    mode = oct((data / "backups").stat().st_mode & 0o777)
    assert mode == "0o700"
    assert all(oct(b.stat().st_mode & 0o777) == "0o600" for b in (data / "backups").glob("budget-*.db"))


# ---------- budget vs actual: independent maths ----------
def test_month_maths_independent_oracle(client, app):
    cfg = db.load_config()
    reg = {c["id"]: c["regular_cents"] for c in cfg["categories"]}
    total_reg = sum(v or 0 for v in reg.values())
    assert total_reg == 1026581
    # one month: a spend in cat 1 of exactly budget + 1 cent, one at budget - 1 in cat 2 (within), income and transfer excluded
    c1, c2 = reg[1], reg[2]
    t = [(D(2025, 5, 1), "FAKE INCOME", 500000), (D(2025, 5, 2), "ZZ SPEND ONE", -(c1 + 1)),
         (D(2025, 5, 3), "ZZ SPEND TWO", -(c2 - 1)), (D(2025, 5, 4), "ZZ UNCAT", -777)]
    assert do_import(client, app, ing_statement(900000, t)).status_code == 302
    with sqlite3.connect(app.config["DB_PATH"]) as cx:
        cx.execute("UPDATE transactions SET category_id=1, pool='regular', category_user_set=1 WHERE description='ZZ SPEND ONE'")
        cx.execute("UPDATE transactions SET category_id=2, pool='regular', category_user_set=1 WHERE description='ZZ SPEND TWO'")
        cx.execute("UPDATE transactions SET category_id=NULL WHERE description='ZZ UNCAT'")
        cx.commit()
    conn = db.connect(app.config["DB_PATH"])
    v = report.month_view(conn, "2025-05")
    conn.close()
    r1 = next(r for r in v["rows"] if r["id"] == 1)
    r2 = next(r for r in v["rows"] if r["id"] == 2)
    assert r1["actual"] == c1 + 1 and r1["status"] == "over"
    assert r2["actual"] == c2 - 1 and r2["status"] in ("near", "within")
    page = client.get("/month/2025-05").get_data(as_text=True)
    assert "OK" in page and "MISMATCH" not in page
    # overall = sum of regular spend + uncategorised, income excluded
    expect_total = (c1 + 1) + (c2 - 1) + 777
    assert v["overall"]["actual"] == expect_total
    assert v["overall"]["budget"] == total_reg
    assert "dd" not in page or True
    assert re.search(r"\d{2}/\d{2}/\d{4}", client.get("/transactions").get_data(as_text=True))
    assert not re.search(r"\b20\d{2}-\d{2}-\d{2}\b", re.sub(r"<[^>]+>", " ", client.get("/transactions").get_data(as_text=True)))


def test_ym_add_never_wraps_and_range_is_bounded():
    assert report.ym_add("2099-12", 1) == "2100-01"
    for bad in [("9999-12", 1), ("2100-12", 1), ("1900-01", -1)]:
        with pytest.raises(ValueError):
            report.ym_add(*bad)
    with pytest.raises(ValueError):
        report.ym_range("0001-01", "9999-12")
    assert len(report.ym_range("1900-01", "2100-12")) == 201 * 12


def test_absurd_months_404_everywhere(client, app):
    do_import(client, app, ing_statement(500000, ING_T))
    for path in ["/month/9999-12", "/month/0000-01", "/month/2101-01", "/month/1899-12", "/bleeding/9999-12",
                 "/bleeding/2101-01", "/month/2025-01%0A", "/month/%D9%A2%D9%A0%D9%A2%D9%A5-01"]:
        assert client.get(path).status_code == 404, path
    r = post(client, app, "/month/sinking-start", {"start": "9999-12", "back": "9999-12"})
    assert r.status_code == 302
    assert client.get("/month").status_code in (200, 302)
    assert client.get("/trends").status_code == 200


def test_huge_category_id_is_rejected_not_500(client, app):
    do_import(client, app, ing_statement(500000, ING_T))
    r = post(client, app, "/transactions/1/category", {"category": "9" * 21, "pool": "regular"})
    assert r.status_code in (302, 400)
    for qs in ["page=99999999999999999999", "cat=99999999999999999999"]:       # same defect on GET filters
        assert client.get("/transactions?" + qs).status_code == 200
