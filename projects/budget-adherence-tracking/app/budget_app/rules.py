"""Slice 5: payee normalisation and rule matching. Pure functions; no database access, no logging."""
import re

STATES = {"NSW", "VIC", "QLD", "SA", "WA", "TAS", "NT", "ACT"}
TRAILING_NOISE = STATES | {"AU", "AUS", "AUSTRALIA", "AUD"}
# Payment-method words that say how the card was used, not who was paid.
LEADING_NOISE = {"VISA", "MASTERCARD", "DEBIT", "CREDIT", "PURCHASE", "CARD", "EFTPOS", "CONTACTLESS",
                 "PAYWAVE", "PAYPASS", "POS", "TAP", "AND", "PAY",
                 # bank transaction-type words (ING and offset listings) and connectives
                 "AT", "FROM", "TO", "ONLINE", "DIRECT", "TRANSFER", "FUNDS", "RECURRING", "PAYMENT", "OSKO",
                 "WITHDRAWAL", "DEPOSIT", "INTL", "ANYONE", "RECEIPT", "TRANSACTION", "FEE", "ATMPURCHASE"}
COMPANY_SUFFIX = {"PTY", "LTD", "LIMITED", "INC"}
PROCESSOR_PREFIX = re.compile(r"\b(?:SQ|SP|PP|PAYPAL|SUMUP|ZLR|LS|TM|EZI|GOOGLE|APPLE)\s*\*\s*")
CARD_NUMBER = re.compile(r"(?:[X*]{2,}\s*\d{2,4}|\b\d{4}[ -][X*\d]{2,4}[ -][X*\d]{2,4}[ -]?\d{0,4}\b)")
DATE_LIKE = re.compile(r"\b\d{1,2}[/.-]\d{1,2}(?:[/.-]\d{2,4})?\b")
PAYEE_TOKENS = 2
MATCH_TYPES = ("payee", "substring", "regex")
MAX_PATTERN = 200


def _is_reference(tok):
    """Reference noise: all-digit tokens and anything with three or more digits (receipts, store and
    card fragments). Brand tokens with one or two digits, such as 7ELEVEN, are kept."""
    digits = sum(c.isdigit() for c in tok)
    return digits >= 3 or (digits > 0 and digits == len(tok))


def normalise(description):
    """Upper-case text with card numbers, dates, reference numbers, payment-method words and trailing
    location (state/country) removed. Returns a single-spaced string (may be empty)."""
    s = (description or "").upper().strip()
    s = PROCESSOR_PREFIX.sub("", s)
    s = CARD_NUMBER.sub(" ", s)
    s = DATE_LIKE.sub(" ", s)
    s = s.replace("'", "").replace("’", "")
    s = re.sub(r"[^A-Z0-9&]+", " ", s)
    toks = [t for t in s.split() if not _is_reference(t)]
    while toks and toks[0] in LEADING_NOISE:
        toks.pop(0)
    toks = [t for t in toks if t not in COMPANY_SUFFIX]
    while toks and toks[-1] in TRAILING_NOISE:
        toks.pop()
    return " ".join(toks)


def payee_key(description):
    """Stable grouping key: the first two meaningful words of the normalised description."""
    return _key(normalise(description))


def _key(norm):
    """Key from an already normalised string. Descriptions that hold only bank wording (for example a
    receipt number with no merchant) have no key: grouping them would mix unrelated payees."""
    toks = [t for t in norm.split() if len(t) > 1 or t == "&"]
    if all(t in LEADING_NOISE for t in toks):
        return ""
    return " ".join(toks[:PAYEE_TOKENS])


def validate_rule(match_type, pattern):
    """Return the cleaned pattern or raise ValueError (message never echoes user text)."""
    if match_type not in MATCH_TYPES:
        raise ValueError("Unknown rule type.")
    p = " ".join((pattern or "").split())
    if not p or len(p) > MAX_PATTERN:
        raise ValueError("Enter a pattern of 1 to 200 characters.")
    if match_type == "regex":
        try:
            re.compile(p, re.I)
        except re.error:
            raise ValueError("That regular expression is not valid.")
        return p
    return p.upper()


class Rule:
    __slots__ = ("id", "match_type", "pattern", "category_id", "pool", "_re")

    def __init__(self, id, match_type, pattern, category_id, pool):
        self.id, self.match_type, self.pattern = id, match_type, pattern
        self.category_id, self.pool = category_id, pool
        self._re = re.compile(pattern, re.I) if match_type == "regex" else None

    def matches(self, key, norm):
        if self.match_type == "payee":
            return key == self.pattern
        if self.match_type == "substring":
            return self.pattern in norm
        return self._re.search(norm) is not None


def load_rules(conn):
    """Rules in evaluation order: priority ascending (lower number wins), then id. Bad rows are skipped."""
    out = []
    for r in conn.execute("SELECT id, match_type, pattern, category_id, pool FROM payee_rules "
                          "ORDER BY priority, id"):
        try:
            out.append(Rule(r["id"], r["match_type"], r["pattern"], r["category_id"], r["pool"]))
        except re.error:
            continue
    return out


def first_match(rules, description):
    """First matching rule or None (first match wins)."""
    norm = normalise(description)
    key = _key(norm)
    for r in rules:
        if r.matches(key, norm):
            return r
    return None
