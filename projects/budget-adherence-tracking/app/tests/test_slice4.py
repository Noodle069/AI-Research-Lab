"""Slice 4 tests: accounts, commit, duplicates, backups, transfers, coverage. Fake data only."""
import datetime as dt
import io
import sqlite3

import pytest

from budget_app import create_app, store
from budget_app.security import csrf_for
from test_app import ORIGIN, PORT, TOKEN, HostClient, post_upload, app, client  # noqa: F401 (fixtures)
from fakepdf import ing_statement, nab_card

D = dt.date


def q(app, sql, *a):
    with sqlite3.connect(app.config["DB_PATH"]) as c:
        return c.execute(sql, a).fetchall()


def post(client, app, path, data=None):
    d = {"csrf": csrf_for(app)}
    d.update(data or {})
    return client.post(path, data=d, headers={"Origin": ORIGIN})


def pid_of(resp):
    assert resp.status_code == 302, resp.status_code
    return resp.headers["Location"].rsplit("/", 1)[1]


def do_import(client, app, pdf, account="new", label="Everyday", role="spending"):
    """Upload, choose account, check, approve. Returns the commit response."""
    pid = pid_of(post_upload(client, app, pdf))
    form = {"account": account, "new_label": label, "role": role}
    assert post(client, app, f"/import/{pid}/check", form).status_code == 302
    return post(client, app, f"/import/{pid}/commit", form)


MAR = [
    (D(2025, 3, 1), "FAKE SHOP ONE", -1250),
    (D(2025, 3, 2), "FAKE SALARY", 250000),
    (D(2025, 3, 3), "FAKE CAFE", -675),
    (D(2025, 3, 3), "FAKE CAFE", -675),      # legitimate identical same-day pair
    (D(2025, 3, 5), "FAKE UTILITY", -12345),
]


def test_approve_disabled_until_account_chosen_and_nothing_written(client, app):
    pid = pid_of(post_upload(client, app, ing_statement(500000, MAR)))
    page = client.get(f"/import/{pid}").get_data(as_text=True)
    assert "Approve and save" in page and "disabled>Approve" in page.replace(" >", ">").replace("disabled >", "disabled>")
    assert q(app, "SELECT COUNT(*) FROM transactions")[0][0] == 0
    # committing straight away (selection not yet checked) writes nothing
    r = post(client, app, f"/import/{pid}/commit", {"account": "new", "new_label": "Everyday", "role": "spending"})
    assert r.status_code == 302
    assert q(app, "SELECT COUNT(*) FROM transactions")[0][0] == 0


def test_commit_saves_rows_with_flow_and_batch(client, app):
    r = do_import(client, app, ing_statement(500000, MAR))
    assert r.status_code == 302
    assert q(app, "SELECT label, role FROM accounts") == [("Everyday", "spending")]
    rows = q(app, "SELECT txn_date, amount_cents, description, flow_type, import_id FROM transactions ORDER BY id")
    assert len(rows) == 5 and {x[4] for x in rows} == {1}
    assert rows[0] == ("2025-03-01", -1250, "FAKE SHOP ONE", "spend", 1)
    assert rows[1][3] == "income"
    assert all(isinstance(x[1], int) for x in rows)
    page = client.get(r.headers["Location"]).get_data(as_text=True)
    assert "Saved as batch 1" in page


def test_account_label_rules(client, app):
    pid = pid_of(post_upload(client, app, ing_statement(500000, MAR)))
    bad = post(client, app, f"/import/{pid}/check", {"account": "new", "new_label": "123456789", "role": "spending"})
    assert bad.status_code == 400 and "account number" in bad.get_data(as_text=True)
    assert q(app, "SELECT COUNT(*) FROM accounts")[0][0] == 0
    bad = post(client, app, f"/import/{pid}/check", {"account": "new", "new_label": "X", "role": "nope"})
    assert bad.status_code == 400


def test_existing_account_role_must_match(client, app):
    do_import(client, app, ing_statement(500000, MAR))
    pid = pid_of(post_upload(client, app, ing_statement(0, [(D(2025, 4, 1), "FAKE X", -100)])))
    r = post(client, app, f"/import/{pid}/check", {"account": "1", "role": "credit_card"})
    assert r.status_code == 400


def test_hash_duplicate_blocked_with_batch_and_date(client, app):
    pdf = ing_statement(500000, MAR)
    do_import(client, app, pdf)
    r = post_upload(client, app, pdf)
    assert r.status_code == 409
    body = r.get_data(as_text=True)
    assert "batch 1" in body and dt.date.today().strftime("%d/%m/%Y") in body
    assert "FAKE" not in body and "12345" not in body
    assert q(app, "SELECT COUNT(*) FROM transactions")[0][0] == 5


def test_overlap_dedupe_keeps_legit_same_day_identical(client, app):
    # Statement A: 1-5 Mar (contains two identical same-day rows).
    do_import(client, app, ing_statement(500000, MAR))
    bal_after_a = 500000 + sum(t[2] for t in MAR)
    # Statement B overlaps: repeats 3-5 Mar rows and adds new ones, including a THIRD identical cafe row.
    b = [MAR[2], MAR[3], (D(2025, 3, 3), "FAKE CAFE", -675), MAR[4], (D(2025, 3, 8), "FAKE NEW", -999)]
    opening_b = bal_after_a - (MAR[0][2] + MAR[1][2])
    pid = pid_of(post_upload(client, app, ing_statement(opening_b, b)))
    form = {"account": "1", "role": "spending"}
    post(client, app, f"/import/{pid}/check", form)
    page = client.get(f"/import/{pid}").get_data(as_text=True)
    assert "Duplicates (already saved, skipped)</dt><dd>3<" in page
    assert "Will be saved</dt><dd>2<" in page
    assert post(client, app, f"/import/{pid}/commit", form).status_code == 302
    cafes = q(app, "SELECT COUNT(*) FROM transactions WHERE description='FAKE CAFE'")[0][0]
    assert cafes == 3                                   # 2 original + the genuinely new third
    assert q(app, "SELECT COUNT(*) FROM transactions")[0][0] == 7
    assert q(app, "SELECT duplicates_skipped, row_count FROM imports WHERE id=2") == [(3, 2)]


def test_fully_overlapping_statement_blocked(client, app):
    do_import(client, app, ing_statement(500000, MAR))
    sub = MAR[2:]
    opening = 500000 + MAR[0][2] + MAR[1][2]
    pid = pid_of(post_upload(client, app, ing_statement(opening, sub)))
    form = {"account": "1", "role": "spending"}
    post(client, app, f"/import/{pid}/check", form)
    r = post(client, app, f"/import/{pid}/commit", form)
    assert r.status_code == 409
    assert q(app, "SELECT COUNT(*) FROM transactions")[0][0] == 5


def test_dedupe_is_per_account(client, app):
    do_import(client, app, ing_statement(500000, MAR), label="A")
    other = ing_statement(700000, MAR)                  # different bytes, same rows, other account
    r = do_import(client, app, other, label="B")
    assert r.status_code == 302
    assert q(app, "SELECT COUNT(*) FROM transactions")[0][0] == 10


def test_atomic_rollback_on_failure(client, app, monkeypatch):
    calls = {"n": 0}
    real = store._insert_txn

    def boom(*a, **k):
        calls["n"] += 1
        if calls["n"] == 3:
            raise RuntimeError("disk exploded FAKE SHOP 1250")
        return real(*a, **k)

    monkeypatch.setattr(store, "_insert_txn", boom)
    r = do_import(client, app, ing_statement(500000, MAR))
    assert r.status_code == 409
    body = r.get_data(as_text=True)
    assert "rolled back" in body and "exploded" not in body and "FAKE" not in body.split("<h2>Transactions")[0].split("rolled back")[1]
    for t in ("transactions", "imports", "accounts"):
        assert q(app, f"SELECT COUNT(*) FROM {t}")[0][0] == 0


def test_backup_created_before_import_and_pruned(tmp_path):
    app = create_app(tmp_path, port=PORT, token=TOKEN, backup_keep=2)
    c = HostClient(app, ORIGIN)
    c.get(f"/enter?t={TOKEN}")
    bdir = tmp_path / "backups"
    assert not bdir.exists()
    do_import(c, app, ing_statement(500000, MAR), label="A")
    files = sorted(bdir.iterdir())
    assert len(files) == 1
    # the first backup was taken BEFORE the write: it holds no transactions
    with sqlite3.connect(files[0]) as b:
        assert b.execute("SELECT COUNT(*) FROM transactions").fetchone()[0] == 0
    do_import(c, app, ing_statement(1, MAR), label="B")
    do_import(c, app, ing_statement(2, MAR), label="C")
    files = sorted(bdir.iterdir())
    assert len(files) == 2                               # keep last N
    with sqlite3.connect(files[-1]) as b:
        assert b.execute("SELECT COUNT(*) FROM transactions").fetchone()[0] == 10


def test_backup_keep_config():
    assert store.parse_keep(None) == 20 and store.parse_keep("abc") == 20 and store.parse_keep("0") == 20
    assert store.parse_keep("5") == 5


def test_blocked_import_makes_no_backup(client, app, tmp_path):
    pdf = ing_statement(500000, MAR)
    do_import(client, app, pdf)
    n = len(list((tmp_path / "backups").iterdir()))
    post_upload(client, app, pdf)                        # hash duplicate
    assert len(list((tmp_path / "backups").iterdir())) == n


def card(txns, opening=300000):
    return nab_card(opening, txns)


def test_transfer_pair_detection_and_flows(client, app):
    # Spending account pays the card; card shows the credit. Same day => auto. Other row 2 days apart => suggestion.
    do_import(client, app, ing_statement(500000, [
        (D(2025, 3, 10), "FAKE CARD PAYMENT", -20000),
        (D(2025, 3, 12), "FAKE MOVE", -5000),
        (D(2025, 3, 13), "FAKE SHOP", -700)]), label="Everyday")
    r = do_import(client, app, card([
        (D(2025, 3, 10), "FAKE PAYMENT THANKS", 20000),
        (D(2025, 3, 14), "FAKE RECEIVED", 5000),
        (D(2025, 3, 15), "FAKE COFFEE", -450)]), label="Card", role="credit_card")
    assert r.status_code == 302
    st = dict(q(app, "SELECT status, COUNT(*) FROM transfer_candidates GROUP BY status"))
    assert st == {"auto": 1, "suggested": 1}
    flows = dict(q(app, "SELECT description, flow_type FROM transactions"))
    assert flows["FAKE CARD PAYMENT"] == "transfer" and flows["FAKE PAYMENT THANKS"] == "transfer"
    assert flows["FAKE MOVE"] == "spend"                  # suggestion is not applied silently
    assert flows["FAKE COFFEE"] == "spend" and flows["FAKE SHOP"] == "spend"
    page = client.get("/transfers").get_data(as_text=True)
    assert "Auto-marked" in page and "Suggested" in page
    cid = q(app, "SELECT id FROM transfer_candidates WHERE status='suggested'")[0][0]
    assert post(client, app, f"/transfers/{cid}/confirm").status_code == 302
    assert dict(q(app, "SELECT description, flow_type FROM transactions"))["FAKE MOVE"] == "transfer"
    # reject the auto pair: returns to role defaults (spend on spending side)
    aid = q(app, "SELECT id FROM transfer_candidates WHERE status='auto'")[0][0]
    post(client, app, f"/transfers/{aid}/reject")
    assert dict(q(app, "SELECT description, flow_type FROM transactions"))["FAKE CARD PAYMENT"] == "spend"


def test_transfer_window_limits(client, app):
    do_import(client, app, ing_statement(500000, [(D(2025, 3, 10), "FAKE OUT", -3000),
                                                   (D(2025, 3, 11), "FAKE OUT2", -4000)]), label="A")
    do_import(client, app, ing_statement(0, [(D(2025, 3, 14), "FAKE IN", 3000),      # 4 days: no
                                              (D(2025, 3, 12), "FAKE IN2", 4000)]), label="B")  # 1 day: yes
    rows = q(app, "SELECT status FROM transfer_candidates")
    assert rows == [("suggested",)]


def test_same_account_never_paired(client, app):
    do_import(client, app, ing_statement(500000, [(D(2025, 3, 10), "FAKE OUT", -3000),
                                                   (D(2025, 3, 10), "FAKE IN", 3000)]))
    assert q(app, "SELECT COUNT(*) FROM transfer_candidates")[0][0] == 0


def test_role_defaults():
    assert store.default_flow("spending", -1) == "spend" and store.default_flow("spending", 1) == "income"
    assert store.default_flow("credit_card", -1) == "spend" and store.default_flow("credit_card", 1) == "transfer"
    assert store.default_flow("loan", -1) == "transfer" and store.default_flow("offset", 1) == "income"
    assert store.default_flow("offset", -1) == "spend" and store.default_flow("loan", 1) == "transfer"


def test_manual_flow_override(client, app):
    do_import(client, app, ing_statement(500000, MAR))
    assert post(client, app, "/transactions/1/flow", {"flow": "savings"}).status_code == 302
    assert q(app, "SELECT flow_type, flow_user_set FROM transactions WHERE id=1") == [("savings", 1)]
    post(client, app, "/transactions/1/flow", {"flow": "bogus"})
    assert q(app, "SELECT flow_type FROM transactions WHERE id=1") == [("savings",)]


def test_coverage_panel(client, app):
    assert "No statements imported yet" in client.get("/coverage").get_data(as_text=True)
    do_import(client, app, ing_statement(500000, [(D(2025, 3, 1), "FAKE A", -100), (D(2025, 3, 31), "FAKE B", -100)]),
              label="Everyday")
    do_import(client, app, ing_statement(0, [(D(2025, 4, 10), "FAKE C", -100), (D(2025, 4, 20), "FAKE D", -100)]),
              label="Second")
    page = client.get("/coverage").get_data(as_text=True)
    assert "03/2025" in page and "04/2025" in page
    assert "01/03/2025 to 31/03/2025" in page and "2 transactions" in page
    assert "10/04/2025 to 20/04/2025" in page and "part of month" in page
    assert "No data" in page                              # Second has nothing in March
    assert "FAKE" not in page                             # no descriptions on the panel


def test_offset_rows_default_spend_and_income(client, app):
    do_import(client, app, ing_statement(500000, [(D(2025, 3, 10), "FAKE OUT", -3000),
                                                   (D(2025, 3, 11), "FAKE IN", 4000)]), label="Off", role="offset")
    assert q(app, "SELECT amount_cents, flow_type FROM transactions ORDER BY id") == [(-3000, "spend"), (4000, "income")]


def test_offset_pair_with_spending_still_auto_transfer(client, app):
    do_import(client, app, ing_statement(500000, [(D(2025, 3, 10), "FAKE TO SPEND", -3000)]), label="Off", role="offset")
    do_import(client, app, ing_statement(0, [(D(2025, 3, 10), "FAKE FROM OFFSET", 3000)]), label="Every")
    assert q(app, "SELECT flow_type FROM transactions ORDER BY id") == [("transfer",), ("transfer",)]
    assert q(app, "SELECT status FROM transfer_candidates") == [("auto",)]


def test_old_offset_defaults_rederived_safely(app):
    from budget_app import db
    path = app.config["DB_PATH"]
    with sqlite3.connect(path) as c:
        c.execute("DELETE FROM meta WHERE key='offset_flow_rederived'")
        c.execute("INSERT INTO accounts(id,label,role) VALUES (1,'Off','offset'),(2,'Sp','spending')")
        c.execute("INSERT INTO imports(id,account_id,file_sha256,layout,period_start,period_end,row_count,imported_at) "
                  "VALUES (1,1,'x','l','2025-03-01','2025-03-31',4,'2025-04-01T00:00:00')")
        rows = [(1, 1, -100, "transfer", 0), (2, 1, 200, "transfer", 0), (3, 1, -300, "transfer", 1),
                (4, 1, -500, "transfer", 0)]   # 1,2 old default; 3 user-set; 4 auto-paired below
        for i, a, cents, f, u in rows:
            c.execute("INSERT INTO transactions(id,import_id,account_id,txn_date,description,amount_cents,flow_type,flow_user_set) "
                      "VALUES (?,1,?,'2025-03-10','FAKE',?,?,?)", (i, a, cents, f, u))
        c.execute("INSERT INTO transactions(id,import_id,account_id,txn_date,description,amount_cents,flow_type) "
                  "VALUES (5,1,2,'2025-03-10','FAKE',500,'transfer')")
        c.execute("INSERT INTO transfer_candidates(txn_a,txn_b,status) VALUES (5,4,'auto')")
    db.init_db(path)
    assert q(app, "SELECT id, flow_type FROM transactions ORDER BY id") == [
        (1, "spend"), (2, "income"), (3, "transfer"), (4, "transfer"), (5, "transfer")]
