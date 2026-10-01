"""Fix round: bounded integers on every route, worker timeout, parse pre-checks. Fake data only."""
import sys
import time

import pytest

from budget_app.parsers import detect
from budget_app.parsers.common import ParseRejected
from test_app import ORIGIN, post_upload, app, client  # noqa: F401
from test_slice4 import do_import, post
from test_tester_functional import ING_T
from fakepdf import ing_statement, _pdf

HUGE = "9" * 25
UNI = "٢"      # Arabic-indic digit: str.isdigit() is True, int() accepts it, SQLite does not like it


def test_every_int_field_is_bounded(client, app):
    do_import(client, app, ing_statement(500000, ING_T))
    for path in ["/transfers/%s/confirm", "/transfers/%s/reject", "/transactions/%s/flow",
                 "/transactions/%s/category", "/rules/%s/priority", "/rules/%s/delete"]:
        for v in (HUGE, "0", "-1"):
            r = post(client, app, path % v, {"category": "1", "pool": "regular", "priority": "5", "flow": "spend"})
            assert r.status_code in (302, 400, 404), (path, v, r.status_code)
    assert client.get(f"/import/done/{HUGE}").status_code == 404
    for field in ("category", "cat_filter", "priority", "account"):
        for v in (HUGE, UNI, "-" + HUGE, "1e3", " "):
            for path in ("/transactions/1/category", "/rules/add", "/rules/1/priority", "/categorise/assign"):
                r = post(client, app, path, {field: v, "category": v if field == "category" else "1",
                                             "pool": "regular", "match_type": "contains", "pattern": "x"})
                assert r.status_code < 500, (path, field, v, r.status_code)
    for qs in (f"page={HUGE}", f"cat={HUGE}", f"cat={UNI}", f"page=-{HUGE}", "page=%D9%A2"):
        for base in ("/transactions?", "/transfers?"):
            assert client.get(base + qs).status_code == 200, (base, qs)


def test_import_account_choice_huge_or_unicode(client, app):
    r = post_upload(client, app, ing_statement(500000, ING_T))
    pid = r.headers["Location"].rsplit("/", 1)[1]
    for v in (HUGE, UNI):
        r = post(client, app, f"/import/{pid}/check", {"account": v, "role": "spending"})
        assert r.status_code == 400


def test_junk_file_rejected_quickly(client, app):
    t = time.time()
    r = post_upload(client, app, b"%PDF-1.4\n" + b"\x00A" * 2_000_000)
    assert r.status_code == 422 and time.time() - t < 20
    r = post_upload(client, app, b"not a pdf at all" * 100)
    assert r.status_code == 422 and "not a PDF" in r.get_data(as_text=True)


def test_worker_timeout_kills_and_gives_clean_error():
    t = time.time()
    with pytest.raises(ParseRejected) as e:
        detect._run_worker([sys.executable, "-c", "import time; time.sleep(60)"], b"x", 1)
    assert time.time() - t < 10 and "took longer" in e.value.errors[0]


def test_page_cap_checked_before_extraction(monkeypatch):
    import io
    monkeypatch.setattr(detect, "MAX_PAGES", 2)
    pdf = _pdf([[], [], []])
    with pytest.raises(ParseRejected) as e:
        detect.parse_pdf(io.BytesIO(pdf))
    assert "pages" in e.value.errors[0]


def test_footer_shows_version(tmp_path):
    from budget_app import __version__, create_app
    app = create_app(tmp_path, token="t" * 20)
    c = app.test_client()
    c.set_cookie("budget_session", "t" * 20, domain="127.0.0.1")
    r = c.get("/", headers={"Host": "127.0.0.1:5055"})
    assert r.status_code == 200 and f"v{__version__}".encode() in r.data
