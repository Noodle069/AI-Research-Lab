import json
import re
import sqlite3
from pathlib import Path

HERE = Path(__file__).resolve().parent
CONFIG_PATH = HERE.parent / "config" / "budget_config.json"
SEED_RULES_PATH = HERE.parent / "config" / "seed_rules.json"
SCHEMA_VERSION = "1"


def load_config(path=CONFIG_PATH):
    with open(path, encoding="utf-8") as f:
        cfg = json.load(f)
    cats = cfg["categories"]
    # Consistency check against the planned totals in the source table.
    reg = sum(c["regular_cents"] or 0 for c in cats)
    sink = sum(c["sinking_cents"] or 0 for c in cats)
    pt = cfg["planned_totals"]
    if reg != pt["regular_cents"] or sink != pt["sinking_cents"]:
        raise ValueError("budget_config.json: category amounts do not add up to planned_totals")
    return cfg


def connect(db_path):
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


_LATE_COLUMNS = [
    ("transactions", "flow_type", "TEXT NOT NULL DEFAULT 'spend'"),
    ("transactions", "flow_user_set", "INTEGER NOT NULL DEFAULT 0"),
    ("transactions", "category_user_set", "INTEGER NOT NULL DEFAULT 0"),
    ("transactions", "payee_key", "TEXT"),
    ("payee_rules", "match_type", "TEXT NOT NULL DEFAULT 'payee'"),
    ("payee_rules", "priority", "INTEGER NOT NULL DEFAULT 100"),
    ("payee_rules", "is_seed", "INTEGER NOT NULL DEFAULT 0"),
    ("imports", "rows_in_file", "INTEGER NOT NULL DEFAULT 0"),
    ("imports", "duplicates_skipped", "INTEGER NOT NULL DEFAULT 0"),
]


def _add_missing_columns(conn):
    """Databases created by slices 1-3 lack the slice 4 columns."""
    for table, col, decl in _LATE_COLUMNS:
        have = {r["name"] for r in conn.execute(f"PRAGMA table_info({table})")}
        if col not in have:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {col} {decl}")


def _rederive_offset_flows(conn):
    """One-off (meta flag): offset rows saved under the old default (transfer) become spend/income,
    unless the user set the flow or the row is in an auto-marked or confirmed transfer pair."""
    if conn.execute("SELECT 1 FROM meta WHERE key='offset_flow_rederived'").fetchone():
        return
    conn.execute(
        "UPDATE transactions SET flow_type = CASE WHEN amount_cents < 0 THEN 'spend' ELSE 'income' END "
        "WHERE flow_user_set = 0 AND flow_type = 'transfer' "
        "AND account_id IN (SELECT id FROM accounts WHERE role = 'offset') "
        "AND id NOT IN (SELECT txn_a FROM transfer_candidates WHERE status IN ('auto','confirmed') "
        "UNION SELECT txn_b FROM transfer_candidates WHERE status IN ('auto','confirmed'))")
    conn.execute("INSERT INTO meta(key, value) VALUES ('offset_flow_rederived', '1')")


def load_seed_rules(path=SEED_RULES_PATH):
    """Expand seed groups to (pattern, category_id, pool, priority) whole-word regex rules."""
    with open(path, encoding="utf-8") as f:
        groups = json.load(f)["groups"]
    return [(r"\b" + re.escape(w.upper()) + r"\b", g["category"], g["pool"], g["priority"])
            for g in groups for w in g["words"]]


def _seed_rules(conn):
    """Insert the generic seed rules once (meta flag). Rules the user deletes are not re-added."""
    if conn.execute("SELECT 1 FROM meta WHERE key='seed_rules_v1'").fetchone():
        return
    for pattern, cat, pool, prio in load_seed_rules():
        conn.execute("INSERT INTO payee_rules(pattern, category_id, pool, match_type, priority, is_seed) "
                     "VALUES (?,?,?,'regex',?,1)", (pattern, cat, pool, prio))
    conn.execute("INSERT INTO meta(key, value) VALUES ('seed_rules_v1', '1')")


def _backfill_payee_keys(conn):
    from .rules import payee_key
    rows = conn.execute("SELECT id, description FROM transactions WHERE payee_key IS NULL").fetchall()
    conn.executemany("UPDATE transactions SET payee_key=? WHERE id=?",
                     [(payee_key(r["description"]), r["id"]) for r in rows])


def init_db(db_path, config=None):
    """Create schema and seed categories/budgets from config (idempotent)."""
    cfg = config or load_config()
    conn = connect(db_path)
    try:
        conn.executescript((HERE / "schema.sql").read_text(encoding="utf-8"))
        _add_missing_columns(conn)
        conn.execute("INSERT OR IGNORE INTO meta(key, value) VALUES ('schema_version', ?)", (SCHEMA_VERSION,))
        _rederive_offset_flows(conn)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_txn_payee ON transactions(payee_key)")
        for i, c in enumerate(cfg["categories"], start=1):
            conn.execute(
                "INSERT INTO categories(id, name, sort_order) VALUES (?,?,?) "
                "ON CONFLICT(id) DO UPDATE SET name=excluded.name, sort_order=excluded.sort_order",
                (c["id"], c["name"], i))
            conn.execute(
                "INSERT INTO category_budgets(category_id, regular_cents, sinking_cents) VALUES (?,?,?) "
                "ON CONFLICT(category_id) DO UPDATE SET regular_cents=excluded.regular_cents, "
                "sinking_cents=excluded.sinking_cents",
                (c["id"], c["regular_cents"], c["sinking_cents"]))
        _seed_rules(conn)          # after categories exist (foreign key)
        _backfill_payee_keys(conn)
        conn.commit()
    finally:
        conn.close()
