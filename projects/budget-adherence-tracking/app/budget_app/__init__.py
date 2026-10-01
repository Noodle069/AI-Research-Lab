import hashlib
import logging
import re
import secrets
import time
from pathlib import Path

from flask import Flask, abort, redirect, render_template, request, url_for

from . import categorise, db, report, security, store
from . import rules as rules_mod
from .parsers.common import ParseRejected, fmt_cents
from .parsers.detect import parse_pdf_bounded

__version__ = "0.1.2"   # the single place the version is set
HOST = "127.0.0.1"
MAX_UPLOAD_BYTES = 10 * 1024 * 1024
PREVIEW_TTL_S = 30 * 60
PREVIEW_MAX = 5


def create_app(data_dir, port=5055, token=None, config=None, backup_keep=None):
    app = Flask(__name__)
    app.config.update(
        LAUNCH_TOKEN=token or security.new_token(),
        ALLOWED_HOSTS={f"{HOST}:{port}", f"localhost:{port}"},
        MAX_CONTENT_LENGTH=MAX_UPLOAD_BYTES,
        DB_PATH=str(Path(data_dir) / "budget.db"),
        BACKUP_DIR=str(Path(data_dir) / "backups"),
        BACKUP_KEEP=store.parse_keep(backup_keep if backup_keep is not None else store.DEFAULT_BACKUP_KEEP),
        DEBUG=False,
    )
    # Request logs carry URLs (including the launch token); keep them off.
    logging.getLogger("werkzeug").setLevel(logging.ERROR)
    db.init_db(app.config["DB_PATH"], config)
    security.install(app)
    flashes = []  # one-shot notices (counts only, never descriptions or amounts)
    done = {}  # counts for the post-save summary (in memory)
    previews = {}  # in memory only: nothing is written to disk or the DB before approval

    app.jinja_env.globals["app_version"] = __version__
    app.jinja_env.filters["money"] = fmt_cents
    app.jinja_env.filters["dmy"] = lambda d: d.strftime("%d/%m/%Y")
    app.jinja_env.filters["ymlabel"] = report.ym_label
    app.jinja_env.filters["dmy_iso"] = lambda s: f"{s[8:10]}/{s[5:7]}/{s[:4]}"

    def prune():
        now = time.time()
        for k in [k for k, v in previews.items() if now - v["at"] > PREVIEW_TTL_S]:
            del previews[k]
        while len(previews) > PREVIEW_MAX:
            del previews[min(previews, key=lambda k: previews[k]["at"])]

    @app.get("/")
    def home():
        conn = db.connect(app.config["DB_PATH"])
        try:
            cats = conn.execute(
                "SELECT c.id, c.name, b.regular_cents, b.sinking_cents FROM categories c "
                "JOIN category_budgets b ON b.category_id=c.id ORDER BY c.sort_order").fetchall()
        finally:
            conn.close()
        return render_template("home.html", cats=cats,
                               tot_reg=sum(c["regular_cents"] or 0 for c in cats),
                               tot_sink=sum(c["sinking_cents"] or 0 for c in cats))

    @app.post("/import/preview")
    def import_preview():
        f = request.files.get("statement")
        if not f or not f.filename:
            return render_template("rejected.html", errors=["No file was chosen."]), 400
        data = f.read()
        sha = hashlib.sha256(data).hexdigest()
        conn = db.connect(app.config["DB_PATH"])
        try:
            prior = store.find_prior_import(conn, sha)
        finally:
            conn.close()
        if prior:
            return render_template("rejected.html", errors=[store.prior_import_message(prior)]), 409
        try:
            parsed = parse_pdf_bounded(data)
        except ParseRejected as e:
            return render_template("rejected.html", errors=e.errors), 422
        if not parsed.passed:
            errs = [m for g in parsed.gates for m in g.errors] + ["Nothing imported."]
            return render_template("rejected.html", errors=errs), 422
        prune()
        pid = secrets.token_urlsafe(16)
        previews[pid] = {"parsed": parsed, "sha": sha, "sel": None, "note": None, "at": time.time()}
        return redirect(url_for("import_show", pid=pid))

    def render_preview(pid, item, error=None):
        p = item["parsed"]
        conn = db.connect(app.config["DB_PATH"])
        try:
            stats = store.preview_stats(conn, p, item["sel"])
            accounts = store.list_accounts(conn)
        finally:
            conn.close()
        note, item["note"] = item["note"], None
        return render_template(
            "preview.html", p=p, pid=pid,
            start=min(r.date for r in p.rows), end=max(r.date for r in p.rows),
            n_in=sum(1 for r in p.rows if r.amount_cents > 0),
            n_out=sum(1 for r in p.rows if r.amount_cents < 0),
            stats=stats, sel=item["sel"], accounts=accounts,
            roles=store.ROLE_LABELS, suggested_role=store.suggest_role(p.layout),
            error=error, note=note)

    @app.get("/import/<pid>")
    def import_show(pid):
        item = previews.get(pid)
        if not item:
            abort(404)
        return render_preview(pid, item)

    def read_selection(item):
        conn = db.connect(app.config["DB_PATH"])
        try:
            return store.validate_selection(conn, request.form), None
        except store.Blocked as e:
            return None, str(e)
        finally:
            conn.close()

    @app.post("/import/<pid>/check")
    def import_check(pid):
        item = previews.get(pid)
        if not item:
            abort(404)
        sel, err = read_selection(item)
        item["sel"] = sel
        if err:
            return render_preview(pid, item, error=err), 400
        return redirect(url_for("import_show", pid=pid))

    @app.post("/import/<pid>/commit")
    def import_commit(pid):
        item = previews.get(pid)
        if not item:
            abort(404)
        sel, err = read_selection(item)
        if err:
            item["sel"] = None
            return render_preview(pid, item, error=err), 400
        if sel != item["sel"]:      # the user has not yet seen counts for this choice
            item["sel"] = sel
            item["note"] = "Account choice updated. Check the duplicate and transfer counts, then approve."
            return redirect(url_for("import_show", pid=pid))
        try:
            result = store.commit_import(app.config["DB_PATH"], app.config["BACKUP_DIR"],
                                         app.config["BACKUP_KEEP"], item["parsed"], item["sha"], sel)
        except store.Blocked as e:
            return render_preview(pid, item, error=str(e)), 409
        previews.pop(pid, None)
        done[result["import_id"]] = result
        return redirect(url_for("import_done", import_id=result["import_id"]))

    @app.get("/import/done/<int(min=1, max=2147483647):import_id>")
    def import_done(import_id):
        conn = db.connect(app.config["DB_PATH"])
        try:
            row = conn.execute("SELECT i.*, a.label, a.role FROM imports i JOIN accounts a ON a.id=i.account_id "
                               "WHERE i.id=?", (import_id,)).fetchone()
        finally:
            conn.close()
        if not row:
            abort(404)
        return render_template("done.html", i=row, r=done.get(import_id), roles=store.ROLE_LABELS)

    @app.get("/coverage")
    def coverage_page():
        conn = db.connect(app.config["DB_PATH"])
        try:
            cov = store.coverage(conn)
        finally:
            conn.close()
        return render_template("coverage.html", cov=cov, roles=store.ROLE_LABELS)

    def _page():
        return min(max(request.args.get("page", 1, type=int), 1), 100000)

    @app.get("/transfers")
    def transfers_page():
        page = _page()
        conn = db.connect(app.config["DB_PATH"])
        try:
            cands = store.pending_candidates(conn)
            review, more = store.flow_review(conn, 100, (page - 1) * 100)
        finally:
            conn.close()
        return render_template("transfers.html", cands=cands, review=review, more=more, page=page,
                               flows=store.FLOW_TYPES)

    def _with_conn(fn, *a):
        conn = db.connect(app.config["DB_PATH"])
        try:
            return fn(conn, *a)
        finally:
            conn.close()

    @app.post("/transfers/<int(min=1, max=2147483647):cid>/confirm")
    def transfer_confirm(cid):
        _with_conn(store.confirm_candidate, cid)
        return redirect(url_for("transfers_page"))

    @app.post("/transfers/<int(min=1, max=2147483647):cid>/reject")
    def transfer_reject(cid):
        _with_conn(store.reject_candidate, cid)
        return redirect(url_for("transfers_page"))

    @app.post("/transactions/<int(min=1, max=2147483647):tid>/flow")
    def transaction_flow(tid):
        _with_conn(store.set_flow, tid, request.form.get("flow", ""))
        return redirect(url_for("transfers_page"))

    # ---------- slice 5: categorisation ----------

    def _flash_redirect(endpoint, msg=None, **kw):
        if msg:
            flashes.append(msg)
        return redirect(url_for(endpoint, **kw))

    def _take_flash():
        out = list(flashes)
        flashes.clear()
        return out

    def _int(name, default=None):
        raw = (request.form.get(name) or "").strip()
        return int(raw) if re.match(r"-?[0-9]{1,9}\Z", raw, re.ASCII) else default

    @app.get("/categorise")
    def categorise_page():
        conn = db.connect(app.config["DB_PATH"])
        try:
            queue = categorise.uncategorised_queue(conn)
            cats = categorise.list_categories(conn)
        finally:
            conn.close()
        return render_template("categorise.html", q=queue, cats=cats, pools=categorise.POOLS, msgs=_take_flash())

    @app.post("/categorise/assign")
    def categorise_assign():
        key = (request.form.get("payee_key") or "")[:200]
        try:
            cat = categorise.parse_category(request.form.get("category"))
            conn = db.connect(app.config["DB_PATH"])
            try:
                res = categorise.assign_group(conn, key, cat, request.form.get("pool", ""),
                                              bool(request.form.get("remember")))
            finally:
                conn.close()
        except categorise.Invalid as e:
            return _flash_redirect("categorise_page", str(e))
        msg = f"Categorised {res['rows']} transaction(s)." + (" Merchant remembered." if res["rule_id"] else "")
        return _flash_redirect("categorise_page", msg)

    @app.get("/rules")
    def rules_page():
        conn = db.connect(app.config["DB_PATH"])
        try:
            rows = categorise.list_rules(conn)
            cats = categorise.list_categories(conn)
        finally:
            conn.close()
        return render_template("rules.html", rules=rows, cats=cats, pools=categorise.POOLS,
                               types=rules_mod.MATCH_TYPES, msgs=_take_flash())

    @app.post("/rules/add")
    def rules_add():
        try:
            conn = db.connect(app.config["DB_PATH"])
            try:
                categorise.add_rule(conn, request.form.get("match_type", ""), request.form.get("pattern", ""),
                                    categorise.parse_category(request.form.get("category")),
                                    request.form.get("pool", ""), _int("priority", 100))
            finally:
                conn.close()
        except (categorise.Invalid, ValueError) as e:
            return _flash_redirect("rules_page", str(e))
        return _flash_redirect("rules_page", "Rule added. Use Re-run rules to apply it to existing rows.")

    @app.post("/rules/<int(min=1, max=2147483647):rid>/priority")
    def rules_priority(rid):
        try:
            _with_conn(categorise.set_priority, rid, _int("priority", -1))
        except categorise.Invalid as e:
            return _flash_redirect("rules_page", str(e))
        return redirect(url_for("rules_page"))

    @app.post("/rules/<int(min=1, max=2147483647):rid>/delete")
    def rules_delete(rid):
        _with_conn(categorise.delete_rule, rid)
        return redirect(url_for("rules_page"))

    @app.post("/rules/rerun")
    def rules_rerun():
        res = _with_conn(categorise.rerun_rules)
        return _flash_redirect("rules_page", f"Re-ran rules on {res['considered']} rows you have not set by hand; "
                                             f"{res['changed']} changed. Your own corrections were not touched.")

    @app.get("/transactions")
    def transactions_page():
        ym = request.args.get("ym", "")
        ym = ym if categorise.YM_RE.match(ym) else ""
        raw = request.args.get("cat", "")
        cat = "none" if raw == "none" else (int(raw) if categorise.ID_RE.match(raw) else None)
        page = _page()
        conn = db.connect(app.config["DB_PATH"])
        try:
            rows, more = categorise.transactions_page(conn, ym or None, cat, 100, (page - 1) * 100)
            cats = categorise.list_categories(conn)
        finally:
            conn.close()
        return render_template("transactions.html", rows=rows, more=more, page=page, cats=cats, ym=ym,
                               cat=raw if cat is not None else "", pools=categorise.POOLS, msgs=_take_flash())

    @app.post("/transactions/<int(min=1, max=2147483647):tid>/category")
    def transaction_category(tid):
        ym = request.form.get("ym", "")
        back = {"ym": ym} if categorise.YM_RE.match(ym) else {}
        cat_filter = request.form.get("cat_filter", "")
        if cat_filter == "none" or categorise.ID_RE.match(cat_filter):
            back["cat"] = cat_filter
        try:
            cat = categorise.parse_category(request.form.get("category"))
            res = _with_conn(lambda c: categorise.set_category(
                c, tid, cat, request.form.get("pool", ""), bool(request.form.get("similar")),
                bool(request.form.get("remember"))))
        except categorise.Invalid as e:
            return _flash_redirect("transactions_page", str(e), **back)
        msg = "Saved."
        if res["similar"]:
            msg += f" Applied to {res['similar']} similar transaction(s)."
        if res["rule_id"]:
            msg += " Merchant remembered."
        return _flash_redirect("transactions_page", msg, **back)

    # ---------- slice 6: month dashboard, overspend view, trends ----------

    def _month_nav(conn, ym):
        first, last = report.data_months(conn)
        prev_ym = report.ym_add(ym, -1) if ym > report.YM_MIN else None
        next_ym = report.ym_add(ym, 1) if ym < report.YM_MAX else None
        return {"prev": prev_ym if first and prev_ym and prev_ym >= first else None,
                "next": next_ym if last and next_ym and next_ym <= last else None, "label": report.ym_label(ym)}

    def _valid_ym(ym):
        if not report.ym_ok(ym):
            abort(404)

    @app.get("/month")
    @app.get("/month/<ym>")
    def month_page(ym=None):
        conn = db.connect(app.config["DB_PATH"])
        try:
            if ym is None:
                ym = report.data_months(conn)[1]
                if ym is None:
                    return render_template("month.html", v=None, msgs=_take_flash())
                return redirect(url_for("month_page", ym=ym))
            _valid_ym(ym)
            v = report.month_view(conn, ym)
            nav = _month_nav(conn, ym)
        finally:
            conn.close()
        return render_template("month.html", v=v, nav=nav, ym=ym, msgs=_take_flash())

    @app.post("/month/sinking-start")
    def month_sinking_start():
        back = request.form.get("back", "")
        back = back if report.ym_ok(back) else None
        try:
            _with_conn(report.set_sinking_start, request.form.get("start", ""))
        except categorise.Invalid as e:
            flashes.append(str(e))
        else:
            flashes.append("Sinking start month saved.")
        return redirect(url_for("month_page", ym=back) if back else url_for("month_page"))

    @app.get("/bleeding")
    @app.get("/bleeding/<ym>")
    def bleeding_page(ym=None):
        conn = db.connect(app.config["DB_PATH"])
        try:
            if ym is None:
                ym = report.data_months(conn)[1]
                if ym is None:
                    return render_template("bleeding.html", b=None)
                return redirect(url_for("bleeding_page", ym=ym))
            _valid_ym(ym)
            b = report.bleeding(conn, ym)
            nav = _month_nav(conn, ym)
        finally:
            conn.close()
        return render_template("bleeding.html", b=b, nav=nav, ym=ym)

    @app.get("/trends")
    def trends_page():
        t = _with_conn(report.trends)
        return render_template("trends.html", t=t)

    @app.post("/import/<pid>/discard")
    def import_discard(pid):
        previews.pop(pid, None)
        return redirect(url_for("home"))

    @app.errorhandler(403)
    def _403(e):
        return "Forbidden. Open the app using the link printed by the launcher.", 403

    @app.errorhandler(OverflowError)
    def _overflow(e):       # safety net: an out-of-range number is a bad request, never a 500
        return render_template("rejected.html", errors=["A number was out of range. Nothing changed."]), 400

    @app.errorhandler(413)
    def _413(e):
        return render_template("rejected.html", errors=["File is too large (limit 10 MB). Nothing imported."]), 413

    return app
