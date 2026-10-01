"""Slice 4: accounts, atomic commit, duplicates, backups, transfers, coverage.

Nothing here logs or raises messages containing amounts or descriptions.
"""
import re
import sqlite3
from collections import Counter
from datetime import date, datetime, timedelta
from pathlib import Path

from . import categorise, db
from . import rules as rules_mod

ROLES = ("spending", "credit_card", "loan", "offset")
ROLE_LABELS = {"spending": "Spending", "credit_card": "Credit card", "loan": "Loan", "offset": "Offset"}
FLOW_TYPES = ("spend", "income", "transfer", "savings")
TRANSFER_WINDOW_DAYS = 3
DEFAULT_BACKUP_KEEP = 20
BACKUP_RE = re.compile(r"^budget-\d{8}-\d{6}-\d{6}\.db$")


class Blocked(Exception):
    """User-facing reason an import cannot proceed. Message never contains values."""


def parse_keep(raw):
    try:
        n = int(raw)
    except (TypeError, ValueError):
        return DEFAULT_BACKUP_KEEP
    return n if n >= 1 else DEFAULT_BACKUP_KEEP


# ---------- accounts ----------

def suggest_role(layout):
    if "credit card" in layout.lower():
        return "credit_card"
    if "offset" in layout.lower():
        return "offset"
    return "spending"


def list_accounts(conn):
    return conn.execute("SELECT id, label, role FROM accounts ORDER BY label COLLATE NOCASE").fetchall()


def validate_selection(conn, form):
    """Turn form fields into {'account_id', 'label', 'role'} or raise Blocked. Read-only."""
    role = (form.get("role") or "").strip()
    if role not in ROLES:
        raise Blocked("Choose the account role.")
    choice = (form.get("account") or "").strip()
    if choice == "new":
        label = " ".join((form.get("new_label") or "").split())
        if not label or len(label) > 60:
            raise Blocked("Enter a name for the new account (1 to 60 characters).")
        if re.search(r"\d{6,}", label.replace(" ", "")):
            raise Blocked("The account name looks like it contains an account number. Use a plain name such as 'Everyday'.")
        if conn.execute("SELECT 1 FROM accounts WHERE label = ? COLLATE NOCASE", (label,)).fetchone():
            raise Blocked("An account with that name already exists. Pick it from the list instead.")
        return {"account_id": None, "label": label, "role": role}
    if re.match(r"[0-9]{1,9}\Z", choice, re.ASCII):
        row = conn.execute("SELECT id, label, role FROM accounts WHERE id = ?", (int(choice),)).fetchone()
        if row:
            if row["role"] != role:
                raise Blocked("The role differs from the one saved for this account. Pick the matching role.")
            return {"account_id": row["id"], "label": row["label"], "role": row["role"]}
    raise Blocked("Choose an existing account or create a new one.")


def default_flow(role, amount_cents):
    """Default flow type from account role and sign. Editable later.
    Credit card credits default to transfer (card repayments); a refund can be overridden to spend.
    Offset accounts behave like spending accounts (out = spend, in = income); loans default to transfer."""
    if role == "loan":
        return "transfer"
    if role == "credit_card":
        return "spend" if amount_cents < 0 else "transfer"
    return "spend" if amount_cents < 0 else "income"


# ---------- duplicates ----------

def _iso(d):
    return d.isoformat()


def split_duplicates(conn, account_id, rows):
    """Per-account multiset matching on (date, cents, description) over the statement's date range.
    Returns a list of booleans aligned with rows: True = duplicate of an already saved row.
    Balance is never part of the key. Identical same-day rows survive unless the DB already holds
    that many of them (multiset, not set)."""
    if account_id is None or not rows:
        return [False] * len(rows)
    lo, hi = min(r.date for r in rows), max(r.date for r in rows)
    have = Counter()
    for t in conn.execute(
            "SELECT txn_date, amount_cents, description FROM transactions "
            "WHERE account_id = ? AND txn_date BETWEEN ? AND ?", (account_id, _iso(lo), _iso(hi))):
        have[(t["txn_date"], t["amount_cents"], t["description"])] += 1
    flags = []
    for r in rows:
        key = (_iso(r.date), r.amount_cents, r.description)
        if have[key] > 0:
            have[key] -= 1
            flags.append(True)
        else:
            flags.append(False)
    return flags


def find_prior_import(conn, sha):
    return conn.execute("SELECT id, imported_at FROM imports WHERE file_sha256 = ?", (sha,)).fetchone()


def prior_import_message(row):
    when = datetime.fromisoformat(row["imported_at"]).strftime("%d/%m/%Y")
    return f"This exact file was already imported as batch {row['id']} on {when}. Nothing imported."


# ---------- transfers ----------

def match_transfers(conn, account_id, items):
    """items: [(key, date, cents)] for rows of one account. Returns [(key, partner_id, days)].
    Equal and opposite amount, different account, within 3 days, partner not already in an open pair.
    Each partner used once; nearest date first."""
    used, out = set(), []
    for key, d, cents in sorted(items, key=lambda x: (x[1], str(x[0]))):
        if cents == 0:
            continue
        lo, hi = d - timedelta(days=TRANSFER_WINDOW_DAYS), d + timedelta(days=TRANSFER_WINDOW_DAYS)
        cands = conn.execute(
            "SELECT t.id, t.txn_date FROM transactions t WHERE t.account_id != ? AND t.amount_cents = ? "
            "AND t.txn_date BETWEEN ? AND ? AND t.id NOT IN ("
            " SELECT txn_a FROM transfer_candidates WHERE status != 'rejected' "
            " UNION SELECT txn_b FROM transfer_candidates WHERE status != 'rejected')",
            (account_id if account_id is not None else -1, -cents, _iso(lo), _iso(hi))).fetchall()
        cands = [c for c in cands if c["id"] not in used]
        if not cands:
            continue
        best = min(cands, key=lambda c: (abs((date.fromisoformat(c["txn_date"]) - d).days), c["id"]))
        used.add(best["id"])
        out.append((key, best["id"], abs((date.fromisoformat(best["txn_date"]) - d).days)))
    return out


def _record_pairs(conn, account_id, new_ids_items):
    """new_ids_items: [(txn_id, date, cents)]. Writes candidates; exact same-day pairs are auto-marked."""
    auto = suggested = 0
    for tid, partner, days in match_transfers(conn, account_id, new_ids_items):
        flags = conn.execute("SELECT flow_user_set FROM transactions WHERE id IN (?, ?)", (tid, partner)).fetchall()
        is_auto = days == 0 and all(f["flow_user_set"] == 0 for f in flags)
        conn.execute("INSERT INTO transfer_candidates(txn_a, txn_b, status) VALUES (?,?,?)",
                     (partner, tid, "auto" if is_auto else "suggested"))
        if is_auto:
            conn.execute("UPDATE transactions SET flow_type='transfer' WHERE id IN (?, ?)", (tid, partner))
            auto += 1
        else:
            suggested += 1
    return auto, suggested


def confirm_candidate(conn, cid):
    row = conn.execute("SELECT txn_a, txn_b FROM transfer_candidates WHERE id=?", (cid,)).fetchone()
    if not row:
        return False
    with conn:
        conn.execute("UPDATE transactions SET flow_type='transfer', flow_user_set=1 WHERE id IN (?,?)",
                     (row["txn_a"], row["txn_b"]))
        conn.execute("UPDATE transfer_candidates SET status='confirmed' WHERE id=?", (cid,))
    return True


def reject_candidate(conn, cid):
    row = conn.execute("SELECT txn_a, txn_b FROM transfer_candidates WHERE id=?", (cid,)).fetchone()
    if not row:
        return False
    with conn:
        conn.execute("UPDATE transfer_candidates SET status='rejected' WHERE id=?", (cid,))
        for tid in (row["txn_a"], row["txn_b"]):
            t = conn.execute("SELECT t.amount_cents, t.flow_user_set, a.role FROM transactions t "
                             "JOIN accounts a ON a.id=t.account_id WHERE t.id=?", (tid,)).fetchone()
            if t and not t["flow_user_set"]:   # undo an auto-mark; keep anything the user set
                conn.execute("UPDATE transactions SET flow_type=? WHERE id=?",
                             (default_flow(t["role"], t["amount_cents"]), tid))
    return True


def set_flow(conn, txn_id, flow):
    if flow not in FLOW_TYPES:
        return False
    with conn:
        n = conn.execute("UPDATE transactions SET flow_type=?, flow_user_set=1 WHERE id=?", (flow, txn_id)).rowcount
    return n == 1


def pending_candidates(conn):
    return conn.execute(
        "SELECT c.id, c.status, ta.txn_date AS date_a, ta.amount_cents AS cents_a, ta.description AS desc_a, aa.label AS acct_a, "
        "tb.txn_date AS date_b, tb.description AS desc_b, ab.label AS acct_b "
        "FROM transfer_candidates c JOIN transactions ta ON ta.id=c.txn_a JOIN transactions tb ON tb.id=c.txn_b "
        "JOIN accounts aa ON aa.id=ta.account_id JOIN accounts ab ON ab.id=tb.account_id "
        "WHERE c.status IN ('auto','suggested') ORDER BY (c.status='suggested') DESC, ta.txn_date, c.id").fetchall()


def flow_review(conn, limit=100, offset=0):
    rows = conn.execute(
        "SELECT t.id, t.txn_date, t.description, t.amount_cents, t.flow_type, t.flow_user_set, a.label AS account "
        "FROM transactions t JOIN accounts a ON a.id=t.account_id WHERE t.flow_type != 'spend' "
        "ORDER BY t.txn_date DESC, t.id DESC LIMIT ? OFFSET ?", (limit + 1, offset)).fetchall()
    return rows[:limit], len(rows) > limit


# ---------- backups ----------

def make_backup(db_path, backups_dir, keep):
    """Copy the SQLite file (via SQLite's online backup) into backups_dir, then keep the newest `keep`."""
    backups_dir = Path(backups_dir)
    backups_dir.mkdir(parents=True, exist_ok=True)
    backups_dir.chmod(0o700)
    dest = backups_dir / f"budget-{datetime.now().strftime('%Y%m%d-%H%M%S-%f')}.db"
    src = sqlite3.connect(str(db_path))
    try:
        out = sqlite3.connect(str(dest))
        try:
            src.backup(out)
        finally:
            out.close()
    finally:
        src.close()
    dest.chmod(0o600)
    files = sorted(p for p in backups_dir.iterdir() if BACKUP_RE.match(p.name))
    for old in files[:-keep] if len(files) > keep else []:
        old.unlink()
    return dest


# ---------- commit ----------

def _insert_txn(conn, import_id, account_id, role, r, rules):
    """New rows are auto-categorised by the rules at commit (not user-set, so later rule runs may change them)."""
    key, cat, pool = categorise.classify(rules, r.description)
    cur = conn.execute(
        "INSERT INTO transactions(import_id, account_id, txn_date, description, amount_cents, balance_cents, "
        "flow_type, category_id, pool, payee_key) VALUES (?,?,?,?,?,?,?,?,?,?)",
        (import_id, account_id, _iso(r.date), r.description, r.amount_cents, r.balance_cents,
         default_flow(role, r.amount_cents), cat, pool, key))
    return cur.lastrowid


def commit_import(db_path, backups_dir, keep, parsed, sha, sel):
    """Save a fully gated statement. All rows or none. Returns a counts dict. Raises Blocked."""
    if not parsed.passed:
        raise Blocked("Only a statement that passed every check can be saved.")
    conn = db.connect(db_path)
    conn.isolation_level = None   # explicit transaction control
    try:
        prior = find_prior_import(conn, sha)
        if prior:
            raise Blocked(prior_import_message(prior))
        sel = validate_selection(conn, {"account": str(sel["account_id"]) if sel["account_id"] else "new",
                                        "new_label": sel["label"], "role": sel["role"]})
        if not any(not d for d in split_duplicates(conn, sel["account_id"], parsed.rows)):
            raise Blocked("Every row in this statement is already saved. Nothing imported.")
        make_backup(db_path, backups_dir, keep)     # before every import; failure aborts the import
        conn.execute("BEGIN IMMEDIATE")
        try:
            if sel["account_id"] is None:
                account_id = conn.execute("INSERT INTO accounts(label, role) VALUES (?,?)",
                                          (sel["label"], sel["role"])).lastrowid
            else:
                account_id = sel["account_id"]
            flags = split_duplicates(conn, account_id, parsed.rows)
            fresh = [r for r, dup in zip(parsed.rows, flags) if not dup]
            cur = conn.execute(
                "INSERT INTO imports(account_id, file_sha256, layout, period_start, period_end, row_count, "
                "rows_in_file, duplicates_skipped, imported_at) VALUES (?,?,?,?,?,?,?,?,?)",
                (account_id, sha, parsed.layout, _iso(min(r.date for r in parsed.rows)),
                 _iso(max(r.date for r in parsed.rows)), len(fresh), len(parsed.rows),
                 len(parsed.rows) - len(fresh), datetime.now().isoformat(timespec="seconds")))
            import_id = cur.lastrowid
            items = []
            rules = rules_mod.load_rules(conn)
            for r in fresh:
                items.append((_insert_txn(conn, import_id, account_id, sel["role"], r, rules), r.date, r.amount_cents))
            auto, suggested = _record_pairs(conn, account_id, items)
            conn.execute("COMMIT")
        except Exception:
            conn.execute("ROLLBACK")
            raise
        return {"import_id": import_id, "saved": len(fresh), "duplicates": len(parsed.rows) - len(fresh),
                "auto_transfers": auto, "suggested_transfers": suggested}
    except Blocked:
        raise
    except sqlite3.IntegrityError:
        raise Blocked("The file or account conflicts with saved data. Nothing was saved.")
    except Exception:
        raise Blocked("Saving failed and was rolled back. Nothing was saved.")
    finally:
        conn.close()


# ---------- preview helpers ----------

def preview_stats(conn, parsed, sel):
    """Duplicate and transfer counts for the preview. Read-only."""
    rules = rules_mod.load_rules(conn)
    unmatched = sum(1 for r in parsed.rows if rules_mod.first_match(rules, r.description) is None)
    if not sel:
        return {"flags": [False] * len(parsed.rows), "dups": None, "new": None, "pairs": None,
                "auto_pairs": None, "role_transfers": None, "uncategorised": unmatched}
    aid = sel["account_id"]
    flags = split_duplicates(conn, aid, parsed.rows)
    fresh = [r for r, d in zip(parsed.rows, flags) if not d]
    pairs = match_transfers(conn, aid, [(r.number, r.date, r.amount_cents) for r in fresh])
    auto = sum(1 for _k, _p, days in pairs if days == 0)
    return {"flags": flags, "dups": len(parsed.rows) - len(fresh), "new": len(fresh), "pairs": len(pairs),
            "auto_pairs": auto, "uncategorised": unmatched,
            "role_transfers": sum(1 for r in fresh if default_flow(sel["role"], r.amount_cents) == "transfer")}


# ---------- coverage ----------

def _month_iter(first, last):
    y, m = first.year, first.month
    while (y, m) <= (last.year, last.month):
        yield y, m
        m += 1
        if m == 13:
            y, m = y + 1, 1


def coverage(conn):
    """Per month, per account: first/last date covered by imported statements and transaction count.
    Coverage comes from each import's statement period, so a short export shows as partial."""
    accounts = list_accounts(conn)
    imps = conn.execute("SELECT account_id, period_start, period_end FROM imports").fetchall()
    if not imps:
        return {"accounts": accounts, "months": []}
    first = min(date.fromisoformat(i["period_start"]) for i in imps)
    last = max(date.fromisoformat(i["period_end"]) for i in imps)
    counts = {(r["ym"], r["account_id"]): r["n"] for r in conn.execute(
        "SELECT substr(txn_date,1,7) AS ym, account_id, COUNT(*) AS n FROM transactions GROUP BY 1,2")}
    months = []
    for y, m in _month_iter(first, last):
        ms = date(y, m, 1)
        me = (date(y + (m == 12), (m % 12) + 1, 1)) - timedelta(days=1)
        cells = []
        for a in accounts:
            lo = hi = None
            for i in imps:
                if i["account_id"] != a["id"]:
                    continue
                s, e = date.fromisoformat(i["period_start"]), date.fromisoformat(i["period_end"])
                s, e = max(s, ms), min(e, me)
                if s <= e:
                    lo = s if lo is None else min(lo, s)
                    hi = e if hi is None else max(hi, e)
            n = counts.get((f"{y:04d}-{m:02d}", a["id"]), 0)
            cells.append({"account": a, "first": lo, "last": hi, "count": n,
                          "state": "none" if lo is None else ("full" if (lo, hi) == (ms, me) else "partial")})
        months.append({"label": ms.strftime("%m/%Y"), "ym": f"{y:04d}-{m:02d}", "cells": cells})
    return {"accounts": accounts, "months": months}
