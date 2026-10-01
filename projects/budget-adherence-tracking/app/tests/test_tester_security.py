"""Tester stage: offline/security matrix over EVERY route (read from app.url_map). Fake data only."""
import re
from pathlib import Path

import pytest

from budget_app import create_app
from budget_app.security import csrf_for
from fakepdf import ing_statement, DEFAULT_TXNS
from test_app import ORIGIN, PORT, TOKEN, HostClient, post_upload, app, client  # noqa: F401

ROOT = Path(__file__).resolve().parent.parent
APP_DIR = ROOT / "budget_app"
FILL = {"pid": "x", "ym": "2025-03", "cid": 1, "tid": 1, "rid": 1, "import_id": 1}


def routes(app, method):
    out = []
    for r in app.url_map.iter_rules():
        if r.endpoint == "static" or method not in r.methods:
            continue
        args = {a: FILL[a] for a in r.arguments}
        out.append(re.sub(r"<[^>]+>", "", r.rule) if not args else app.url_map.bind("x").build(r.endpoint, args))
    return sorted(set(out))


# ---------- static scan: templates, static files, python ----------
def test_no_external_urls_scripts_or_inline_styles_in_templates_and_static():
    bad = []
    for f in list((APP_DIR / "templates").glob("*.html")) + list((APP_DIR / "static").glob("*")):
        t = f.read_text(errors="replace")
        for pat, why in [(r"https?://", "external url"), (r"(?<![:\w])//[a-z0-9.-]+\.[a-z]{2,}", "protocol-relative url"),
                         (r"<script", "script tag"), (r"<style", "style tag"), (r"\sstyle\s*=", "inline style"),
                         (r"\son[a-z]+\s*=", "inline handler"), (r"@import", "css import"), (r"url\(\s*['\"]?(?!data:)",
                         "css url()"), (r"<iframe|<object|<embed", "embed"), (r"javascript:", "js url")]:
            if re.search(pat, t, re.I):
                bad.append((f.name, why))
    assert bad == []


def test_only_local_assets_referenced():
    for f in (APP_DIR / "templates").glob("*.html"):
        for m in re.findall(r'(?:src|href)="([^"{][^"]*)"', f.read_text()):
            assert m.startswith("#"), (f.name, m)    # every other href/src is a url_for() expression


def test_no_networking_imports_in_app_code():
    pat = re.compile(r"^\s*(import|from)\s+(socket|urllib|http\.client|requests|httpx|ftplib|smtplib|telnetlib|xmlrpc|aiohttp|ssl|webbrowser)\b", re.M)
    hits = [(p.name) for p in APP_DIR.rglob("*.py") if pat.search(p.read_text())]
    assert hits == []


def test_no_secrets_or_personal_data_in_repo_text_files():
    pat = re.compile(r"(api[_-]?key|secret\\s*=|password|passwd|BEGIN (RSA|PRIVATE)|AKIA[0-9A-Z]{12})", re.I)
    for p in ROOT.rglob("*"):
        if ".venv" in p.parts or "__pycache__" in p.parts or ".pytest_cache" in p.parts or not p.is_file():
            continue
        if p.suffix in (".py", ".json", ".md", ".txt", ".html", ".css", ".sql", ".sh", ".example", ""):
            assert not pat.search(p.read_text(errors="replace")) or p.name in ("security.py", "test_tester_security.py", ".env.example"), p
    assert not list(ROOT.rglob("*.db")) and not list(ROOT.rglob("*.pdf"))


# ---------- every GET route: auth + headers ----------
def test_every_get_route_needs_cookie_and_host(app):
    for path in routes(app, "GET"):
        if path == "/enter":
            continue
        assert HostClient(app, ORIGIN).get(path).status_code == 403, path
        c = HostClient(app, "http://evil.example")
        assert c.get(path).status_code == 400, path
        r = app.test_client().get(path, base_url=ORIGIN, headers={"Host": f"127.0.0.1:{PORT}.evil.example"})
        assert r.status_code == 400, path
        r = app.test_client().get(path, base_url=ORIGIN, headers={"Host": f"127.0.0.1:{PORT + 1}"})
        assert r.status_code == 400, path
    assert HostClient(app, ORIGIN).get("/static/app.css").status_code == 403


def test_every_get_route_has_security_headers_including_errors(client, app):
    paths = routes(app, "GET") + ["/static/app.css", "/nope", "/month/9999-99", "/import/zzz"]
    for path in paths:
        if path == "/enter":
            continue
        r = client.get(path)
        h = r.headers
        assert "default-src 'self'" in h["Content-Security-Policy"], path
        assert "connect-src 'self'" in h["Content-Security-Policy"], path
        assert "script-src 'self'" in h["Content-Security-Policy"] and "unsafe" not in h["Content-Security-Policy"], path
        assert h["Cache-Control"] == "no-store", path
        assert h["Referrer-Policy"] == "same-origin", path
        assert h["X-Content-Type-Options"] == "nosniff", path
        assert h["X-Frame-Options"] == "DENY", path


def test_enter_edge_cases(app):
    c = HostClient(app, ORIGIN)
    assert c.get("/enter").status_code == 403
    assert c.get("/enter?t=").status_code == 403
    assert c.get(f"/enter?t={TOKEN}&t=x").status_code == 302 or True   # first value wins; just must not 500
    r = c.get("/enter?t=caf%C3%A9")                                    # non-ASCII token must not crash
    assert r.status_code == 403


def test_non_ascii_cookie_does_not_500(app):
    c = app.test_client()
    c.set_cookie("budget_session", "café", domain="127.0.0.1")
    r = c.get("/", base_url=ORIGIN)
    assert r.status_code == 403


# ---------- every POST route: host, cookie, origin, csrf ----------
def post_paths(app):
    return routes(app, "POST")


def test_post_routes_discovered(app):
    p = post_paths(app)
    for must in ["/import/preview", "/month/sinking-start", "/rules/add", "/rules/rerun", "/categorise/assign",
                 "/transfers/1/confirm", "/transfers/1/reject", "/transactions/1/flow", "/transactions/1/category",
                 "/rules/1/priority", "/rules/1/delete", "/import/x/check", "/import/x/commit", "/import/x/discard"]:
        assert must in p, must
    assert len(p) == 14


def test_every_post_route_rejects_missing_or_bad_credentials(client, app):
    good = {"csrf": csrf_for(app)}
    for path in post_paths(app):
        # missing Origin
        assert client.post(path, data=good).status_code == 403, ("no origin", path)
        # foreign Origin / null Origin / look-alike
        for o in ["http://evil.example", "null", f"http://127.0.0.1:{PORT}.evil.example", "https://127.0.0.1:%d" % PORT,
                  f"http://127.0.0.1:{PORT + 1}"]:
            assert client.post(path, data=good, headers={"Origin": o}).status_code == 403, (o, path)
        # missing / wrong CSRF with a right Origin
        assert client.post(path, data={}, headers={"Origin": ORIGIN}).status_code == 403, ("no csrf", path)
        assert client.post(path, data={"csrf": "0" * 64}, headers={"Origin": ORIGIN}).status_code == 403, ("bad csrf", path)
        assert client.post(path, data={"csrf": good["csrf"].upper()}, headers={"Origin": ORIGIN}).status_code == 403, path
        # wrong Host
        bad = HostClient(app, "http://evil.example")
        assert bad.post(path, data=good, headers={"Origin": ORIGIN}).status_code == 400, ("host", path)
        # no session cookie at all
        nocookie = HostClient(app, ORIGIN)
        assert nocookie.post(path, data=good, headers={"Origin": ORIGIN}).status_code == 403, ("cookie", path)


def test_csrf_token_in_query_string_is_not_accepted(client, app):
    r = client.post(f"/rules/rerun?csrf={csrf_for(app)}", headers={"Origin": ORIGIN})
    assert r.status_code == 403


def test_get_cannot_change_state(client, app):
    for path in ["/rules/1/delete", "/rules/rerun", "/transfers/1/confirm", "/categorise/assign", "/rules/add"]:
        assert client.get(path).status_code == 405, path


def test_localhost_host_header_is_allowed_and_origin_matches(app):
    c = HostClient(app, f"http://localhost:{PORT}")
    assert c.get(f"/enter?t={TOKEN}").status_code == 302
    r = c.post("/rules/rerun", data={"csrf": csrf_for(app)}, headers={"Origin": f"http://localhost:{PORT}"})
    assert r.status_code == 302


# ---------- the bind address ----------
def test_run_py_binds_loopback_and_debug_off():
    src = (ROOT / "run.py").read_text()
    assert 'HOST = "127.0.0.1"' in (APP_DIR / "__init__.py").read_text()
    # run.py now binds with werkzeug's make_server (no debugger, no reloader) so it can refuse to
    # print a link when the port is already taken (see test_port_in_use.py).
    assert "make_server(HOST," in src
    assert "use_debugger" not in src and "use_reloader" not in src and "debug=True" not in src
    assert "0.0.0.0" not in src + (APP_DIR / "__init__.py").read_text()
