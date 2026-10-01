"""Black-box driver for a RUNNING app (not collected by pytest). FAKE data only.

Usage: python tests/live_driver.py <port> <token>
Imports one fake PDF per layout, then exercises every route over real HTTP on 127.0.0.1.
Prints status counts only (never page bodies). Exit code 0 when every expectation held.
"""
import datetime as dt
import http.client
import re
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fakepdf as fp  # noqa: E402

D = dt.date
PORT, TOKEN = int(sys.argv[1]), sys.argv[2]
HOST = f"127.0.0.1:{PORT}"
cookie = {}
fails = []
log = []


def req(method, path, fields=None, files=None, headers=None, host=HOST):
    h = {"Host": host}
    if cookie:
        h["Cookie"] = "; ".join(f"{k}={v}" for k, v in cookie.items())
    h.update(headers or {})
    body = None
    if method == "POST":
        h.setdefault("Origin", f"http://{HOST}")
        b = uuid.uuid4().hex
        parts = []
        for k, v in (fields or {}).items():
            parts.append(f'--{b}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode())
        for k, (fn, data) in (files or {}).items():
            parts.append(f'--{b}\r\nContent-Disposition: form-data; name="{k}"; filename="{fn}"\r\n'
                         f'Content-Type: application/pdf\r\n\r\n'.encode() + data + b"\r\n")
        parts.append(f"--{b}--\r\n".encode())
        body = b"".join(parts)
        h["Content-Type"] = f"multipart/form-data; boundary={b}"
    c = http.client.HTTPConnection("127.0.0.1", PORT, timeout=60)
    c.request(method, path, body=body, headers=h)
    r = c.getresponse()
    data = r.read().decode("utf-8", "replace")
    for sc in r.headers.get_all("Set-Cookie") or []:
        k, _, v = sc.split(";")[0].partition("=")
        cookie[k] = v
    hd = {k: v for k, v in r.getheaders()}
    c.close()
    log.append((method, path.split("?")[0], r.status))
    return r.status, hd, data


def expect(name, cond):
    if not cond:
        fails.append(name)
        print("FAIL", name)


def csrf():
    s, h, d = req("GET", "/")
    return re.search(r'name="csrf" value="([0-9a-f]+)"', d).group(1)


def do_import(pdf, label, role):
    tok = csrf()
    s, h, d = req("POST", "/import/preview", {"csrf": tok}, {"statement": ("s.pdf", pdf)})
    expect(f"preview {label} -> 302 (got {s})", s == 302)
    if s != 302:
        return None
    loc = h["Location"]
    s, h2, d = req("GET", loc)
    expect(f"preview page {label}", s == 200 and "nothing saved yet" in d.lower())
    pid = loc.rsplit("/", 1)[1]
    form = {"csrf": tok, "account": "new", "new_label": label, "role": role}
    s, _, d = req("POST", f"/import/{pid}/check", form)
    expect(f"check {label}", s == 302)
    s, _, d = req("POST", f"/import/{pid}/commit", form)
    expect(f"commit {label} (got {s})", s == 302)
    return pid


def main():
    s, h, _ = req("GET", f"/enter?t={TOKEN}")
    expect("enter", s == 302 and "budget_session" in cookie)
    # one fake PDF per layout
    ing = fp.ing_statement(500000, [
        (D(2025, 3, 1), "FAKE SHOP ONE", -1250), (D(2025, 3, 2), "FAKE SALARY", 250000),
        (D(2025, 3, 3), "FAKE CAFE", -675), (D(2025, 3, 3), "FAKE CAFE", -675),
        (D(2025, 3, 5), "FAKE TRANSFER OUT", -50000), (D(2025, 4, 2), "FAKE UTILITY", -12345)])
    do_import(ing, "Everyday", "spending")
    do_import(fp.ing_short(100000, fp.SHORT_TXNS), "Short", "spending")
    do_import(fp.nab_card(100000, fp.NAB_TXNS), "Card", "credit_card")
    do_import(fp.offset_listing(0, fp.LIST_TXNS), "Offset", "offset")
    do_import(fp.offset_listing(-30000000, fp.LIST_TXNS, loan=True), "Loan", "loan")
    # a duplicate file and a rejected file
    s, _, d = req("POST", "/import/preview", {"csrf": csrf()}, {"statement": ("s.pdf", ing)})
    expect("dup file 409", s == 409)
    bad = fp.ing_statement(500000, [(D(2025, 3, 1), "FAKE X", -100)], tamper_amount_row=1)
    s, _, d = req("POST", "/import/preview", {"csrf": csrf()}, {"statement": ("s.pdf", bad)})
    expect("altered 422", s == 422 and "FAKE" not in d)
    # discard path
    pdf2 = fp.ing_statement(1000, [(D(2024, 1, 1), "FAKE D", -100)])
    s, h, _ = req("POST", "/import/preview", {"csrf": csrf()}, {"statement": ("s.pdf", pdf2)})
    pid = h["Location"].rsplit("/", 1)[1]
    s, _, _ = req("POST", f"/import/{pid}/discard", {"csrf": csrf()})
    expect("discard", s == 302)

    # read routes
    for p in ["/", "/coverage", "/transfers", "/categorise", "/rules", "/transactions", "/transactions?cat=none&ym=2025-03",
              "/month", "/month/2025-03", "/month/2026-08", "/bleeding", "/bleeding/2025-03", "/trends",
              "/static/app.css", "/import/done/1"]:
        s, h, d = req("GET", p, headers={})
        expect(f"GET {p} {s}", s in (200, 302))
        if s == 302:
            s, h, d = req("GET", h["Location"])
            expect(f"GET follow {p} {s}", s == 200)
    for p, code in [("/month/9999-99", 404), ("/month/abc", 404), ("/bleeding/2025-13", 404), ("/import/nope", 404),
                    ("/import/done/999", 404), ("/nonexistent", 404)]:
        s, _, _ = req("GET", p)
        expect(f"GET {p} -> {code} (got {s})", s == code)

    # write routes
    t = csrf()
    s, _, _ = req("POST", "/categorise/assign", {"csrf": t, "payee_key": "FAKE CAFE", "category": "1", "pool": "regular", "remember": "1"})
    expect("assign", s == 302)
    s, _, _ = req("POST", "/rules/add", {"csrf": t, "match_type": "contains", "pattern": "FAKE SHOP", "category": "2", "pool": "regular", "priority": "50"})
    expect("rules add", s == 302)
    s, _, _ = req("POST", "/rules/rerun", {"csrf": t})
    expect("rerun", s == 302)
    s, _, _ = req("POST", "/transactions/1/category", {"csrf": t, "category": "3", "pool": "regular", "similar": "1", "remember": "1"})
    expect("txn category", s == 302)
    s, _, _ = req("POST", "/transactions/2/flow", {"csrf": t, "flow": "transfer"})
    expect("txn flow", s == 302)
    s, _, d = req("GET", "/transfers")
    ids = re.findall(r"/transfers/(\d+)/confirm", d)
    if ids:
        s, _, _ = req("POST", f"/transfers/{ids[0]}/confirm", {"csrf": t})
        expect("confirm", s == 302)
    s, _, _ = req("POST", "/transfers/999/reject", {"csrf": t})
    expect("reject", s == 302)
    s, _, _ = req("POST", "/month/sinking-start", {"csrf": t, "start": "2025-03", "back": "2025-03"})
    expect("sinking", s == 302)
    s, _, _ = req("POST", "/rules/1/priority", {"csrf": t, "priority": "5"})
    expect("rule prio", s == 302)
    s, _, _ = req("POST", "/rules/1/delete", {"csrf": t})
    expect("rule del", s == 302)
    for p in ["/month/2025-03", "/bleeding/2025-03", "/trends", "/rules", "/transactions", "/coverage"]:
        s, _, d = req("GET", p)
        expect(f"re-GET {p}", s == 200)
    s, _, d = req("GET", "/month/2025-03")
    expect("reconciliation OK", "OK" in d and "MISMATCH" not in d)
    print(f"requests={len(log)} failures={len(fails)}")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
