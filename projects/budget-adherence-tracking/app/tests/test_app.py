import sqlite3

import pytest

from budget_app import create_app
from budget_app.datadir import resolve_data_dir
from budget_app.db import load_config
from budget_app.security import csrf_for
from fakepdf import DEFAULT_TXNS, ing_statement

class HostClient:
    """Test client that sends a chosen Host (Flask 3.0's test_client has no base_url)."""

    def __init__(self, app, base_url):
        self._c, self._base = app.test_client(), base_url

    def _call(self, method, *a, **k):
        k.setdefault("base_url", self._base)
        return getattr(self._c, method)(*a, **k)

    def get(self, *a, **k):
        return self._call("get", *a, **k)

    def post(self, *a, **k):
        return self._call("post", *a, **k)


PORT = 5099
TOKEN = "test-token"
ORIGIN = f"http://127.0.0.1:{PORT}"


@pytest.fixture
def app(tmp_path):
    return create_app(tmp_path, port=PORT, token=TOKEN)


@pytest.fixture
def client(app):
    c = HostClient(app, ORIGIN)
    assert c.get(f"/enter?t={TOKEN}").status_code == 302
    return c


def post_upload(client, app, pdf):
    return client.post("/import/preview", data={"csrf": csrf_for(app), "statement": (__import__("io").BytesIO(pdf), "x.pdf")},
                       headers={"Origin": ORIGIN}, content_type="multipart/form-data")


def txn_count(app):
    with sqlite3.connect(app.config["DB_PATH"]) as c:
        return c.execute("SELECT COUNT(*) FROM transactions").fetchone()[0]


def test_config_totals_and_seeded_db(app):
    cfg = load_config()
    assert len(cfg["categories"]) == 10
    with sqlite3.connect(app.config["DB_PATH"]) as c:
        rows = c.execute("SELECT c.id,b.regular_cents,b.sinking_cents FROM categories c JOIN category_budgets b ON b.category_id=c.id ORDER BY c.id").fetchall()
    assert len(rows) == 10
    assert sum(r[1] or 0 for r in rows) == 1026581 and sum(r[2] or 0 for r in rows) == 309593
    assert rows[8][1:] == (None, None) and rows[9][1:] == (None, None)   # Buffer, Spare
    assert rows[0][1:] == (669891, 88834)                                # Regular vs Sinking split kept


def test_requires_token_and_host(app):
    c = HostClient(app, ORIGIN)
    assert c.get("/").status_code == 403
    assert c.get("/enter?t=wrong").status_code == 403
    bad = HostClient(app, "http://evil.example:80")
    assert bad.get(f"/enter?t={TOKEN}").status_code == 400


def test_security_headers_and_no_external_assets(client):
    r = client.get("/")
    assert r.status_code == 200
    csp = r.headers["Content-Security-Policy"]
    assert "default-src 'self'" in csp and "connect-src 'self'" in csp
    html = r.get_data(as_text=True)
    assert "http://" not in html and "https://" not in html and "<script" not in html
    assert "Regular" in html and "Sinking" in html


def test_post_needs_origin_and_csrf(client, app):
    pdf = ing_statement(500000, DEFAULT_TXNS)
    r = client.post("/import/preview", data={"csrf": csrf_for(app), "statement": (__import__("io").BytesIO(pdf), "x.pdf")},
                    content_type="multipart/form-data")
    assert r.status_code == 403                                      # no Origin
    r = client.post("/import/preview", data={"csrf": "bad", "statement": (__import__("io").BytesIO(pdf), "x.pdf")},
                    headers={"Origin": ORIGIN}, content_type="multipart/form-data")
    assert r.status_code == 403                                      # bad CSRF
    r = client.post("/import/preview", data={"csrf": csrf_for(app), "statement": (__import__("io").BytesIO(pdf), "x.pdf")},
                    headers={"Origin": "http://evil.example"}, content_type="multipart/form-data")
    assert r.status_code == 403                                      # foreign Origin


def test_preview_then_nothing_written(client, app):
    r = post_upload(client, app, ing_statement(500000, DEFAULT_TXNS))
    assert r.status_code == 302
    page = client.get(r.headers["Location"]).get_data(as_text=True)
    assert "Preview (nothing saved yet)" in page and "PASS" in page and "FAIL" not in page
    assert "01/03/2025 to 11/03/2025" in page
    assert f"{len(DEFAULT_TXNS)} (" in page
    assert txn_count(app) == 0                                       # nothing committed
    assert "/import/" not in page.split("<title>")[1].split("</title>")[0]


def test_altered_amount_rejected_whole_file(client, app):
    r = post_upload(client, app, ing_statement(500000, DEFAULT_TXNS, tamper_amount_row=3))
    assert r.status_code == 422
    body = r.get_data(as_text=True)
    assert "File rejected" in body and "Row 3" in body and "FAKE" not in body
    assert txn_count(app) == 0


def test_unknown_layout_and_corrupt(client, app):
    assert post_upload(client, app, ing_statement(0, DEFAULT_TXNS, header=False)).status_code == 422
    assert post_upload(client, app, b"garbage").status_code == 422


def test_data_dir_guard(tmp_path, monkeypatch):
    from pathlib import Path
    with pytest.raises(SystemExit):
        resolve_data_dir("")
    with pytest.raises(SystemExit):
        resolve_data_dir(str(Path.home() / "Documents" / "budget-data-test"))
    assert resolve_data_dir(str(tmp_path / "ok")).exists()
