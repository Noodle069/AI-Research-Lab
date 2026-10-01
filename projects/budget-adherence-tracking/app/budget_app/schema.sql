-- Budget adherence tracker. All money is integer cents (AUD). Dates are ISO yyyy-mm-dd text.
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS meta (
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS categories (
  id INTEGER PRIMARY KEY,
  name TEXT NOT NULL UNIQUE,
  sort_order INTEGER NOT NULL
);

-- Regular = routine monthly spend judged against actual spending.
-- Sinking = monthly amount set aside for irregular bills (tracked as a separate pool).
-- NULL = no monthly amount (categories 9 and 10).
CREATE TABLE IF NOT EXISTS category_budgets (
  category_id INTEGER PRIMARY KEY REFERENCES categories(id),
  regular_cents INTEGER CHECK (regular_cents IS NULL OR regular_cents >= 0),
  sinking_cents INTEGER CHECK (sinking_cents IS NULL OR sinking_cents >= 0)
);

CREATE TABLE IF NOT EXISTS accounts (
  id INTEGER PRIMARY KEY,
  label TEXT NOT NULL,                      -- user-chosen label, never a bank account number
  role TEXT NOT NULL CHECK (role IN ('spending','credit_card','loan','offset'))
);
CREATE UNIQUE INDEX IF NOT EXISTS ux_accounts_label ON accounts(label COLLATE NOCASE);

CREATE TABLE IF NOT EXISTS imports (
  id INTEGER PRIMARY KEY,
  account_id INTEGER NOT NULL REFERENCES accounts(id),
  file_sha256 TEXT NOT NULL UNIQUE,         -- duplicate-file protection
  layout TEXT NOT NULL,
  period_start TEXT NOT NULL,
  period_end TEXT NOT NULL,
  row_count INTEGER NOT NULL,               -- rows actually saved
  rows_in_file INTEGER NOT NULL DEFAULT 0,
  duplicates_skipped INTEGER NOT NULL DEFAULT 0,
  imported_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS transactions (
  id INTEGER PRIMARY KEY,
  import_id INTEGER NOT NULL REFERENCES imports(id) ON DELETE CASCADE,
  account_id INTEGER NOT NULL REFERENCES accounts(id),
  txn_date TEXT NOT NULL,
  description TEXT NOT NULL,
  amount_cents INTEGER NOT NULL,            -- signed: negative = money out
  balance_cents INTEGER,                    -- kept for the row gate only; never part of identity
  category_id INTEGER REFERENCES categories(id),   -- NULL = Uncategorised
  pool TEXT NOT NULL DEFAULT 'regular' CHECK (pool IN ('regular','sinking')),
  -- Category spending counts flow_type = 'spend' only. Default comes from sign and account role.
  flow_type TEXT NOT NULL DEFAULT 'spend' CHECK (flow_type IN ('spend','income','transfer','savings')),
  flow_user_set INTEGER NOT NULL DEFAULT 0, -- 1 = the user confirmed or overrode the flow type
  category_user_set INTEGER NOT NULL DEFAULT 0, -- 1 = the user set category/pool; rules and re-imports never change it
  payee_key TEXT                            -- normalised grouping key derived from the description
);
CREATE INDEX IF NOT EXISTS idx_txn_date ON transactions(txn_date);
CREATE INDEX IF NOT EXISTS idx_txn_dedupe ON transactions(account_id, txn_date, amount_cents, description);

CREATE TABLE IF NOT EXISTS payee_rules (
  id INTEGER PRIMARY KEY,
  pattern TEXT NOT NULL,
  category_id INTEGER NOT NULL REFERENCES categories(id),
  pool TEXT NOT NULL DEFAULT 'regular' CHECK (pool IN ('regular','sinking')),
  match_type TEXT NOT NULL DEFAULT 'payee',  -- payee (equals payee key) | substring | regex
  priority INTEGER NOT NULL DEFAULT 100,     -- lower number is tried first; first match wins
  is_seed INTEGER NOT NULL DEFAULT 0
);

-- Suggested inter-account transfer pairs (equal and opposite amounts, different accounts, within 3 days).
-- auto = exact opposite same-day pair, marked as transfer but always shown; suggested = needs the user.
CREATE TABLE IF NOT EXISTS transfer_candidates (
  id INTEGER PRIMARY KEY,
  txn_a INTEGER NOT NULL REFERENCES transactions(id) ON DELETE CASCADE,
  txn_b INTEGER NOT NULL REFERENCES transactions(id) ON DELETE CASCADE,
  status TEXT NOT NULL CHECK (status IN ('auto','suggested','confirmed','rejected')),
  UNIQUE (txn_a, txn_b)
);
