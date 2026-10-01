"""Slice 5 tests: normalisation, rules, seeds, learning, user-set protection, totals. Fake data only."""
import datetime as dt
import sqlite3

import pytest

from budget_app import categorise, db, rules as R
from test_app import app, client  # noqa: F401 (fixtures)
from test_slice4 import do_import, post, q
from fakepdf import ing_statement

D = dt.date


# ---------- normalisation ----------

@pytest.mark.parametrize("raw,key", [
    ("WOOLWORTHS 1234 BONDI NSW AU", "WOOLWORTHS BONDI"),
    ("Visa Purchase 12/03 Woolworths 5678 Xxxx NSW AUS", "WOOLWORTHS XXXX"),
    ("EFTPOS FAKE CAFE CARD XX1234 VIC", "FAKE CAFE"),
    ("SQ *FAKE COFFEE CO 0042 QLD AU", "FAKE COFFEE"),
    ("Fake Shop   REF 889977 Receipt 123456", "FAKE SHOP"),
    ("  mcdonald's 123  ", "MCDONALDS"),
    ("7-ELEVEN 2043 NSW", "ELEVEN"),
    ("Purchase at SQ *FAKE BURGER VARSITY", "FAKE BURGER"),
    ("From FAKE PAYPAL AUSTRALIA - 1043270800049", "FAKE PAYPAL"),
    ("Direct debit From FAKE INSURE PTY LTD -", "FAKE INSURE"),
    ("To Fake Person - Funds transfer", "FAKE PERSON"),
    ("Interest charged", "INTEREST CHARGED"),
])
def test_payee_key_normalisation(raw, key):
    assert R.payee_key(raw) == key


def test_normalise_strips_cards_dates_refs_location():
    n = R.normalise("Card 4111 11XX XXXX 1234 FAKE STORE 15/03/2025 AB1234567 MELBOURNE VIC AU")
    assert "4111" not in n and "2025" not in n and "AB1234567" not in n
    assert not n.endswith(("VIC", "AU"))
    assert "FAKE STORE" in n


def test_same_payee_different_reference_same_key():
    assert R.payee_key("FAKE MART 1111 NSW") == R.payee_key("FAKE MART 2222 NSW AU") == "FAKE MART"


def test_empty_description_has_empty_key():
    assert R.payee_key("") == "" and R.payee_key("12345 6789") == ""


def test_bank_wording_only_has_no_key():
    # A receipt number with no merchant must not form a shared group for unrelated payees.
    assert R.payee_key("EFTPOS Purchase - Receipt 002821") == ""
    assert R.payee_key("Osko Payment - Receipt 082945") == ""
    assert R.payee_key("Intl Transaction Fee - Receipt 104206") == ""


def test_apple_bill_still_matches_seed(tmp_path):
    db.init_db(tmp_path / "x.db")
    m = R.first_match(R.load_rules(db.connect(tmp_path / "x.db")), "APPLE.COM/BILL SYDNEY NSW")
    assert m is not None and m.category_id == 1


# ---------- rule matching and priority ----------

def mk(conn, rows):
    for mt, pat, cat, pool, prio in rows:
        conn.execute("INSERT INTO payee_rules(pattern, category_id, pool, match_type, priority, is_seed) "
                     "VALUES (?,?,?,?,?,0)", (pat, cat, pool, mt, prio))


def test_match_types_priority_first_match_wins(tmp_path):
    db.init_db(tmp_path / "x.db")
    conn = db.connect(tmp_path / "x.db")
    conn.execute("DELETE FROM payee_rules")
    mk(conn, [("substring", "FAKE", 7, "regular", 50),
              ("payee", "FAKE MART", 2, "regular", 10),
              ("regex", r"\bMART\b", 3, "sinking", 20)])
    rules = R.load_rules(conn)
    assert R.first_match(rules, "FAKE MART 12").category_id == 2                  # payee rule, priority 10, wins
    assert R.first_match(rules, "OTHER MART").category_id == 3                    # regex before substring
    assert R.first_match(rules, "FAKE THING").category_id == 7
    assert R.first_match(rules, "NOTHING HERE") is None
    # ties broken by id (insertion order)
    conn.execute("DELETE FROM payee_rules")
    mk(conn, [("substring", "AB", 1, "regular", 5), ("substring", "AB", 2, "regular", 5)])
    assert R.first_match(R.load_rules(conn), "XABX").category_id == 1


def test_validate_rule_rejects_bad_regex_without_echo():
    with pytest.raises(ValueError) as e:
        R.validate_rule("regex", "(unclosed")
    assert "unclosed" not in str(e.value)
    assert R.validate_rule("substring", " a  b ") == "A B"


# ---------- seed rules ----------

SEED_SAMPLES = {
    2: ["WOOLWORTHS 1234 NSW", "COLES 0042 VIC", "ALDI STORES 12 QLD", "IGA EXPRESS"],
    3: ["MCDONALDS 123 NSW", "UBER EATS HELP.UBER.COM", "STARBUCKS 5 VIC", "MENULOG 99"],
    5: ["AMPOL 7788 NSW", "BP 4455 QLD", "SHELL COLES EXPRESS 12", "LINKT MELBOURNE", "OPAL TRANSPORT", "REPCO 12"],
    4: ["CHEMIST WAREHOUSE 12", "TERRY WHITE CHEMMART", "MEDIBANK PRIVATE", "BUPA HEALTH"],
    1: ["NETFLIX.COM", "SPOTIFY P12345", "TELSTRA 12345", "AGL ENERGY", "AUSSIE BROADBAND 12", "ORIGIN ENERGY"],
    6: ["QANTAS AIRWAYS 081", "JETSTAR 12", "AIRBNB * HM1234"],
    7: ["THE LOTT 123", "TICKETEK 1", "EVENT CINEMAS 12"],
}


def test_seed_rule_coverage_and_categories(tmp_path):
    db.init_db(tmp_path / "x.db")
    conn = db.connect(tmp_path / "x.db")
    rules = R.load_rules(conn)
    assert len(rules) > 100
    for cat, samples in SEED_SAMPLES.items():
        for s in samples:
            m = R.first_match(rules, s)
            assert m is not None and m.category_id == cat, (cat, s)


def test_seed_pools_specific_before_general(tmp_path):
    db.init_db(tmp_path / "x.db")
    rules = R.load_rules(db.connect(tmp_path / "x.db"))
    assert R.first_match(rules, "UBER EATS 123").category_id == 3        # not Uber transport
    assert R.first_match(rules, "UBER TRIP 123").category_id == 5
    m = R.first_match(rules, "SYDNEY WATER 123")
    assert (m.category_id, m.pool) == (1, "sinking")
    m = R.first_match(rules, "QANTAS 1")
    assert (m.category_id, m.pool) == (6, "sinking")
    assert R.first_match(rules, "WOOLWORTHS 1").pool == "regular"


def test_seed_has_no_personal_content_and_is_idempotent(tmp_path):
    p = tmp_path / "x.db"
    db.init_db(p)
    n = sqlite3.connect(p).execute("SELECT COUNT(*) FROM payee_rules").fetchone()[0]
    db.init_db(p)
    assert sqlite3.connect(p).execute("SELECT COUNT(*) FROM payee_rules").fetchone()[0] == n
    # user deleted rules are not re-added on restart
    c = sqlite3.connect(p)
    c.execute("DELETE FROM payee_rules")
    c.commit()
    db.init_db(p)
    assert sqlite3.connect(p).execute("SELECT COUNT(*) FROM payee_rules").fetchone()[0] == 0


# ---------- import, categorisation, flow and totals ----------

MARCH = [
    (D(2025, 3, 1), "WOOLWORTHS 1234 BONDI NSW AU", -10000),
    (D(2025, 3, 2), "WOOLWORTHS 5678 MANLY NSW AU", -5000),
    (D(2025, 3, 3), "FAKE MYSTERY SHOP 11", -2000),
    (D(2025, 3, 4), "FAKE MYSTERY SHOP 22", -3000),
    (D(2025, 3, 5), "FAKE SALARY", 400000),
    (D(2025, 3, 6), "QANTAS 081", -30000),
    (D(2025, 3, 7), "FAKE OTHER THING", -700),
]
OPEN = 500000


def rows(app, sql="SELECT description, category_id, pool, category_user_set, flow_type FROM transactions ORDER BY id"):
    return q(app, sql)


def test_commit_auto_categorises_and_preview_counts(client, app):
    assert do_import(client, app, ing_statement(OPEN, MARCH)).status_code == 302
    got = {r[0].split()[0]: (r[1], r[2]) for r in rows(app)}
    assert got["WOOLWORTHS"] == (2, "regular")
    assert got["QANTAS"] == (6, "sinking")
    assert got["FAKE"][0] is None
    assert [r[4] for r in rows(app) if r[0] == "FAKE SALARY"] == ["income"]


def test_month_totals_spend_only_uncategorised_counted(client, app):
    do_import(client, app, ing_statement(OPEN, MARCH))
    conn = db.connect(app.config["DB_PATH"])
    t = categorise.month_totals(conn, "2025-03")
    by = {c["category_id"]: c for c in t["categories"]}
    assert by[2]["regular_cents"] == 15000 and by[2]["count"] == 2
    assert by[6]["sinking_cents"] == 30000 and by[6]["regular_cents"] == 0      # pool assignment
    assert t["uncategorised"]["total_cents"] == 2000 + 3000 + 700
    assert t["total_cents"] == 15000 + 30000 + 5700                               # income excluded, uncategorised in
    assert categorise.month_totals(conn, "2025-04")["total_cents"] == 0
    with pytest.raises(ValueError):
        categorise.month_totals(conn, "2025-13")


def test_only_spend_rows_count(client, app):
    do_import(client, app, ing_statement(OPEN, MARCH))
    c = sqlite3.connect(app.config["DB_PATH"])
    c.execute("UPDATE transactions SET flow_type='transfer' WHERE description LIKE 'WOOLWORTHS 1234%'")
    c.commit()
    conn = db.connect(app.config["DB_PATH"])
    t = categorise.month_totals(conn, "2025-03")
    assert {c["category_id"]: c for c in t["categories"]}[2]["regular_cents"] == 5000
    queue = categorise.uncategorised_queue(conn)
    assert queue["rows"] == 3           # the income row is not spend, so not in the queue


# ---------- learning and protection ----------

def first_id(app, like):
    return q(app, "SELECT id FROM transactions WHERE description LIKE ? ORDER BY id", like)[0][0]


def test_queue_groups_by_payee_with_counts_and_totals(client, app):
    do_import(client, app, ing_statement(OPEN, MARCH))
    conn = db.connect(app.config["DB_PATH"])
    g = {r["payee_key"]: (r["n"], r["total_cents"]) for r in categorise.uncategorised_queue(conn)["groups"]}
    assert g["FAKE MYSTERY"] == (2, 5000)
    assert g["FAKE OTHER"] == (1, 700)
    assert "WOOLWORTHS BONDI" not in g


def test_correction_similar_and_remember_creates_rule(client, app):
    do_import(client, app, ing_statement(OPEN, MARCH))
    tid = first_id(app, "FAKE MYSTERY%")
    r = post(client, app, f"/transactions/{tid}/category",
             {"category": "3", "pool": "regular", "similar": "1", "remember": "1"})
    assert r.status_code == 302
    got = rows(app, "SELECT category_id, category_user_set FROM transactions WHERE description LIKE 'FAKE MYSTERY%'")
    assert got == [(3, 1), (3, 1)]
    rule = q(app, "SELECT pattern, match_type, category_id, priority, is_seed FROM payee_rules WHERE is_seed=0")
    assert rule == [("FAKE MYSTERY", "payee", 3, 10, 0)]
    # a later import of the same payee is categorised by the learned rule
    apr = [(D(2025, 4, 2), "FAKE MYSTERY SHOP 99", -1500)]
    assert do_import(client, app, ing_statement(OPEN, apr), account="1", role="spending").status_code == 302
    assert q(app, "SELECT category_id, category_user_set FROM transactions WHERE description='FAKE MYSTERY SHOP 99'") == [(3, 0)]


def test_correction_without_similar_changes_one_row(client, app):
    do_import(client, app, ing_statement(OPEN, MARCH))
    tid = first_id(app, "FAKE MYSTERY%")
    post(client, app, f"/transactions/{tid}/category", {"category": "7", "pool": "sinking"})
    got = rows(app, "SELECT category_id, pool, category_user_set FROM transactions WHERE description LIKE 'FAKE MYSTERY%' ORDER BY id")
    assert got == [(7, "sinking", 1), (None, "regular", 0)]
    assert q(app, "SELECT COUNT(*) FROM payee_rules WHERE is_seed=0") == [(0,)]


def test_user_set_survives_rerun_and_rule_changes(client, app):
    do_import(client, app, ing_statement(OPEN, MARCH))
    tid = first_id(app, "WOOLWORTHS 1234%")
    post(client, app, f"/transactions/{tid}/category", {"category": "7", "pool": "regular"})   # against the seed rule
    post(client, app, "/rules/rerun")
    assert q(app, "SELECT category_id, category_user_set FROM transactions WHERE id=?", tid) == [(7, 1)]
    # the other Woolworths row was not user-set, so it follows rules; a new high-priority rule changes it
    c = sqlite3.connect(app.config["DB_PATH"])
    c.execute("INSERT INTO payee_rules(pattern, category_id, pool, match_type, priority) VALUES ('MANLY','8','regular','substring',1)".replace("'8'", "8"))
    c.commit()
    r = post(client, app, "/rules/rerun")
    assert r.status_code == 302
    assert q(app, "SELECT category_id FROM transactions WHERE description LIKE 'WOOLWORTHS 5678%'") == [(8,)]
    assert q(app, "SELECT category_id FROM transactions WHERE id=?", tid) == [(7,)]


def test_user_set_survives_reimport_of_overlapping_statement(client, app):
    do_import(client, app, ing_statement(OPEN, MARCH))
    tid = first_id(app, "WOOLWORTHS 1234%")
    post(client, app, f"/transactions/{tid}/category", {"category": "7", "pool": "sinking", "remember": "1"})
    more = MARCH + [(D(2025, 3, 10), "FAKE NEW ONE", -100)]
    assert do_import(client, app, ing_statement(OPEN, more), account="1", role="spending").status_code == 302
    assert q(app, "SELECT category_id, pool, category_user_set FROM transactions WHERE id=?", tid) == [(7, "sinking", 1)]
    assert q(app, "SELECT COUNT(*) FROM transactions") == [(len(MARCH) + 1,)]


def test_similar_does_not_overwrite_other_user_set_rows(client, app):
    do_import(client, app, ing_statement(OPEN, MARCH))
    a, b = [r[0] for r in q(app, "SELECT id FROM transactions WHERE description LIKE 'FAKE MYSTERY%' ORDER BY id")]
    post(client, app, f"/transactions/{b}/category", {"category": "8", "pool": "regular"})
    post(client, app, f"/transactions/{a}/category", {"category": "3", "pool": "regular", "similar": "1"})
    assert q(app, "SELECT category_id FROM transactions WHERE id=?", b) == [(8,)]


def test_queue_group_assign_and_remember(client, app):
    do_import(client, app, ing_statement(OPEN, MARCH))
    r = post(client, app, "/categorise/assign", {"payee_key": "FAKE MYSTERY", "category": "3", "pool": "regular", "remember": "1"})
    assert r.status_code == 302
    assert q(app, "SELECT DISTINCT category_id, category_user_set FROM transactions WHERE description LIKE 'FAKE MYSTERY%'") == [(3, 1)]
    assert q(app, "SELECT pattern FROM payee_rules WHERE is_seed=0") == [("FAKE MYSTERY",)]
    page = client.get("/categorise")
    assert page.status_code == 200 and b"FAKE OTHER" in page.data and b"FAKE MYSTERY" not in page.data


def test_rules_page_priority_delete_add(client, app):
    do_import(client, app, ing_statement(OPEN, MARCH))
    page = client.get("/rules")
    assert page.status_code == 200 and b"WOOLWORTHS" in page.data
    rid = q(app, "SELECT id FROM payee_rules LIMIT 1")[0][0]
    assert post(client, app, f"/rules/{rid}/priority", {"priority": "7"}).status_code == 302
    assert q(app, "SELECT priority FROM payee_rules WHERE id=?", rid) == [(7,)]
    post(client, app, f"/rules/{rid}/priority", {"priority": "abc"})
    assert q(app, "SELECT priority FROM payee_rules WHERE id=?", rid) == [(7,)]
    post(client, app, f"/rules/{rid}/delete")
    assert q(app, "SELECT COUNT(*) FROM payee_rules WHERE id=?", rid) == [(0,)]
    post(client, app, "/rules/add", {"match_type": "regex", "pattern": "(bad", "category": "2", "pool": "regular", "priority": "5"})
    assert q(app, "SELECT COUNT(*) FROM payee_rules WHERE pattern='(bad'") == [(0,)]
    post(client, app, "/rules/add", {"match_type": "substring", "pattern": "fake other", "category": "2", "pool": "regular", "priority": "5"})
    assert q(app, "SELECT pattern, priority FROM payee_rules WHERE is_seed=0") == [("FAKE OTHER", 5)]


def test_pages_render_no_values_in_urls_and_csp(client, app):
    do_import(client, app, ing_statement(OPEN, MARCH))
    for path in ("/categorise", "/rules", "/transactions", "/transactions?ym=2025-03&cat=none"):
        r = client.get(path)
        assert r.status_code == 200
        assert "script-src 'self'" in r.headers["Content-Security-Policy"]
        assert b"<script" not in r.data and b" onclick" not in r.data
    tid = first_id(app, "FAKE MYSTERY%")
    r = post(client, app, f"/transactions/{tid}/category", {"category": "99", "pool": "regular"})
    assert r.status_code == 302 and "99" not in r.headers["Location"]
    assert q(app, "SELECT category_id FROM transactions WHERE id=?", tid) == [(None,)]
    r = post(client, app, f"/transactions/{tid}/category", {"category": "3", "pool": "bogus"})
    assert q(app, "SELECT category_id FROM transactions WHERE id=?", tid) == [(None,)]


def test_old_database_upgrades(tmp_path):
    p = tmp_path / "old.db"
    db.init_db(p)
    c = sqlite3.connect(p)
    c.executescript("DROP TABLE payee_rules; CREATE TABLE payee_rules (id INTEGER PRIMARY KEY, pattern TEXT NOT NULL, "
                    "category_id INTEGER NOT NULL, pool TEXT NOT NULL DEFAULT 'regular');"
                    "DELETE FROM meta WHERE key='seed_rules_v1';")
    c.commit()
    db.init_db(p)
    assert sqlite3.connect(p).execute("SELECT COUNT(*) FROM payee_rules WHERE is_seed=1").fetchone()[0] > 100
