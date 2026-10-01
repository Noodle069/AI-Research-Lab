"""Slice 5: categories, pools, rules, corrections, month totals.

Category spending counts flow_type = 'spend' rows only. Uncategorised (category_id NULL) spend still
counts in the overall total. Nothing here logs or raises messages containing descriptions or amounts.
"""
import re

from . import rules as R

POOLS = ("regular", "sinking")
USER_RULE_PRIORITY = 10          # user rules are tried before seed rules (400-500)
ID_RE = re.compile(r"[0-9]{1,9}\Z", re.ASCII)   # ids and counts: bounded, ASCII digits only
YM_RE = re.compile(r"[0-9]{4}-(0[1-9]|1[0-2])\Z", re.ASCII)


class Invalid(Exception):
    """User-facing reason for a rejected change. Never contains descriptions or amounts."""


def _check(conn, category_id, pool):
    if pool not in POOLS:
        raise Invalid("Choose Regular or Sinking.")
    if category_id is None:
        return None
    if not conn.execute("SELECT 1 FROM categories WHERE id=?", (category_id,)).fetchone():
        raise Invalid("Choose one of the listed categories.")
    return category_id


def parse_category(raw):
    """Form value -> category id or None for Uncategorised. Raises Invalid on junk."""
    raw = (raw or "").strip()
    if raw in ("", "none"):
        return None
    if ID_RE.match(raw):
        return int(raw)
    raise Invalid("Choose one of the listed categories.")


def list_categories(conn):
    return conn.execute("SELECT id, name FROM categories ORDER BY sort_order").fetchall()


# ---------- applying rules ----------

def classify(rules, description):
    """(payee_key, category_id, pool) for a description. Unmatched = (key, None, 'regular')."""
    key = R.payee_key(description)
    m = R.first_match(rules, description)
    return (key, m.category_id, m.pool) if m else (key, None, "regular")


def rerun_rules(conn):
    """Re-apply rules to every row the user has not set. Returns {'changed', 'considered'}."""
    rules = R.load_rules(conn)
    rows = conn.execute("SELECT id, description, category_id, pool FROM transactions "
                        "WHERE category_user_set = 0").fetchall()
    changed = 0
    with conn:
        for r in rows:
            key, cat, pool = classify(rules, r["description"])
            conn.execute("UPDATE transactions SET payee_key=? WHERE id=?", (key, r["id"]))
            if cat != r["category_id"] or pool != r["pool"]:
                conn.execute("UPDATE transactions SET category_id=?, pool=? WHERE id=? AND category_user_set=0",
                             (cat, pool, r["id"]))
                changed += 1
    return {"changed": changed, "considered": len(rows)}


# ---------- corrections and learning ----------

def _remember(conn, key, category_id, pool):
    """Create (or update) the user's payee rule for this key. Returns the rule id."""
    if category_id is None:
        raise Invalid("Pick a category to remember a merchant.")
    row = conn.execute("SELECT id FROM payee_rules WHERE match_type='payee' AND pattern=? AND is_seed=0",
                       (key,)).fetchone()
    if row:
        conn.execute("UPDATE payee_rules SET category_id=?, pool=?, priority=? WHERE id=?",
                     (category_id, pool, USER_RULE_PRIORITY, row["id"]))
        return row["id"]
    return conn.execute("INSERT INTO payee_rules(pattern, category_id, pool, match_type, priority, is_seed) "
                        "VALUES (?,?,?,'payee',?,0)", (key, category_id, pool, USER_RULE_PRIORITY)).lastrowid


def apply_to_key(conn, key, category_id, pool, only_uncategorised=False):
    """Set category/pool (user-set) on every row with this payee key that is not already user-set."""
    sql = "UPDATE transactions SET category_id=?, pool=?, category_user_set=1 WHERE payee_key=? AND category_user_set=0"
    if only_uncategorised:
        sql += " AND category_id IS NULL"
    return conn.execute(sql, (category_id, pool, key)).rowcount


def set_category(conn, txn_id, category_id, pool, apply_similar=False, remember=False):
    """Manual correction of one transaction. The row becomes user-set. Optionally also apply to all
    similar rows (same payee key, not already user-set) and/or create a rule for the payee key.
    Returns {'similar': n, 'rule_id': id|None}."""
    row = conn.execute("SELECT payee_key FROM transactions WHERE id=?", (txn_id,)).fetchone()
    if not row:
        raise Invalid("That transaction no longer exists.")
    category_id = _check(conn, category_id, pool)
    key = row["payee_key"] or ""
    if (apply_similar or remember) and not key:
        raise Invalid("This transaction has no usable payee name, so it cannot be applied to similar rows or remembered.")
    with conn:
        conn.execute("UPDATE transactions SET category_id=?, pool=?, category_user_set=1 WHERE id=?",
                     (category_id, pool, txn_id))
        similar = apply_to_key(conn, key, category_id, pool) if apply_similar else 0
        rule_id = _remember(conn, key, category_id, pool) if remember else None
    return {"similar": similar, "rule_id": rule_id}


def assign_group(conn, key, category_id, pool, remember):
    """Queue action: categorise every uncategorised, not-user-set row of a payee key at once."""
    if not key:
        raise Invalid("This group has no usable payee name.")
    category_id = _check(conn, category_id, pool)
    if category_id is None:
        raise Invalid("Pick a category.")
    with conn:
        n = apply_to_key(conn, key, category_id, pool, only_uncategorised=True)
        rule_id = _remember(conn, key, category_id, pool) if remember else None
    return {"rows": n, "rule_id": rule_id}


# ---------- rules management ----------

def list_rules(conn):
    return conn.execute(
        "SELECT r.id, r.match_type, r.pattern, r.priority, r.pool, r.is_seed, c.name AS category "
        "FROM payee_rules r JOIN categories c ON c.id=r.category_id ORDER BY r.priority, r.id").fetchall()


def add_rule(conn, match_type, pattern, category_id, pool, priority):
    pattern = R.validate_rule(match_type, pattern)
    category_id = _check(conn, category_id, pool)
    if category_id is None:
        raise Invalid("Pick a category.")
    if not (0 <= priority <= 9999):
        raise Invalid("Priority must be between 0 and 9999.")
    with conn:
        return conn.execute("INSERT INTO payee_rules(pattern, category_id, pool, match_type, priority, is_seed) "
                            "VALUES (?,?,?,?,?,0)", (pattern, category_id, pool, match_type, priority)).lastrowid


def set_priority(conn, rule_id, priority):
    if not (0 <= priority <= 9999):
        raise Invalid("Priority must be between 0 and 9999.")
    with conn:
        return conn.execute("UPDATE payee_rules SET priority=? WHERE id=?", (priority, rule_id)).rowcount == 1


def delete_rule(conn, rule_id):
    with conn:
        return conn.execute("DELETE FROM payee_rules WHERE id=?", (rule_id,)).rowcount == 1


# ---------- queue, lists, totals ----------

def uncategorised_queue(conn, limit=200):
    """Uncategorised spend grouped by payee key: count and total spent (positive cents)."""
    groups = conn.execute(
        "SELECT payee_key, COUNT(*) AS n, -SUM(amount_cents) AS total_cents FROM transactions "
        "WHERE flow_type='spend' AND category_id IS NULL AND COALESCE(payee_key,'') != '' "
        "GROUP BY payee_key ORDER BY total_cents DESC, payee_key LIMIT ?", (limit + 1,)).fetchall()
    unnamed = conn.execute("SELECT COUNT(*) FROM transactions WHERE flow_type='spend' AND category_id IS NULL "
                           "AND COALESCE(payee_key,'')=''").fetchone()[0]
    total = conn.execute("SELECT COUNT(*) AS n, COALESCE(-SUM(amount_cents),0) AS c FROM transactions "
                         "WHERE flow_type='spend' AND category_id IS NULL").fetchone()
    return {"groups": groups[:limit], "more": len(groups) > limit, "unnamed": unnamed,
            "rows": total["n"], "total_cents": total["c"]}


def transactions_page(conn, ym=None, cat=None, limit=100, offset=0):
    """Transactions for the correction screen. cat: None = all, 'none' = Uncategorised, int = category."""
    where, args = [], []
    if ym:
        where.append("t.txn_date >= ? AND t.txn_date < ?")
        y, m = int(ym[:4]), int(ym[5:7])
        args += [f"{ym}-01", f"{y + (m == 12):04d}-{(m % 12) + 1:02d}-01"]
    if cat == "none":
        where.append("t.category_id IS NULL")
    elif isinstance(cat, int):
        where.append("t.category_id = ?")
        args.append(cat)
    sql = ("SELECT t.id, t.txn_date, t.description, t.amount_cents, t.flow_type, t.category_id, t.pool, "
           "t.category_user_set, a.label AS account FROM transactions t JOIN accounts a ON a.id=t.account_id "
           + ("WHERE " + " AND ".join(where) + " " if where else "")
           + "ORDER BY t.txn_date DESC, t.id DESC LIMIT ? OFFSET ?")
    rows = conn.execute(sql, args + [limit + 1, offset]).fetchall()
    return rows[:limit], len(rows) > limit


def month_totals(conn, ym):
    """Spend per category for month ym ('YYYY-MM'), for the budget-vs-actual view (slice 6).

    Returns {'ym', 'categories': [{'category_id', 'name', 'regular_cents', 'sinking_cents', 'total_cents',
    'count'}], 'uncategorised': {...same keys, category_id None}, 'total_cents', 'count'}.
    Only flow_type = 'spend' rows count. Amounts are positive cents spent (a refund on a spend row
    reduces the total). Uncategorised spend is included in total_cents."""
    if not YM_RE.match(ym or ""):
        raise ValueError("ym must be YYYY-MM")
    y, m = int(ym[:4]), int(ym[5:7])
    lo, hi = f"{ym}-01", f"{y + (m == 12):04d}-{(m % 12) + 1:02d}-01"
    got = {}
    for r in conn.execute(
            "SELECT category_id, pool, -SUM(amount_cents) AS c, COUNT(*) AS n FROM transactions "
            "WHERE flow_type='spend' AND txn_date >= ? AND txn_date < ? GROUP BY category_id, pool", (lo, hi)):
        d = got.setdefault(r["category_id"], {"regular_cents": 0, "sinking_cents": 0, "count": 0})
        d[f"{r['pool']}_cents"] += r["c"]
        d["count"] += r["n"]

    def entry(cid, name):
        d = got.get(cid, {"regular_cents": 0, "sinking_cents": 0, "count": 0})
        return {"category_id": cid, "name": name, "regular_cents": d["regular_cents"],
                "sinking_cents": d["sinking_cents"], "total_cents": d["regular_cents"] + d["sinking_cents"],
                "count": d["count"]}

    cats = [entry(c["id"], c["name"]) for c in list_categories(conn)]
    unc = entry(None, "Uncategorised")
    return {"ym": ym, "categories": cats, "uncategorised": unc,
            "total_cents": sum(c["total_cents"] for c in cats) + unc["total_cents"],
            "count": sum(c["count"] for c in cats) + unc["count"]}
