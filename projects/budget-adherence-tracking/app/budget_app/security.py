"""Localhost-only hardening: Host check, per-launch token, CSRF, Origin, CSP."""
import hashlib
import hmac
import secrets

from flask import abort, g, make_response, redirect, request

COOKIE = "budget_session"
CSP = ("default-src 'self'; connect-src 'self'; img-src 'self'; style-src 'self'; script-src 'self'; "
       "font-src 'self'; object-src 'none'; base-uri 'none'; form-action 'self'; frame-ancestors 'none'")


def new_token():
    return secrets.token_urlsafe(32)


def same(a, b):
    """Constant-time string compare on bytes (compare_digest raises on non-ASCII str)."""
    return hmac.compare_digest((a or "").encode("utf-8", "replace"), (b or "").encode("utf-8", "replace"))


def csrf_for(app):
    return hmac.new(app.config["LAUNCH_TOKEN"].encode(), b"csrf", hashlib.sha256).hexdigest()


def install(app):
    allowed_hosts = app.config["ALLOWED_HOSTS"]

    @app.before_request
    def guard():
        if request.host not in allowed_hosts:          # TRUSTED_HOSTS equivalent (Flask 3.0)
            abort(400)
        token = app.config["LAUNCH_TOKEN"]
        if request.path == "/enter":
            if not same(request.args.get("t", ""), token):
                abort(403)
            resp = make_response(redirect("/"))
            resp.set_cookie(COOKIE, token, httponly=True, samesite="Strict", path="/")
            return resp
        if not same(request.cookies.get(COOKIE, ""), token):
            abort(403)
        if request.method not in ("GET", "HEAD"):
            origin = request.headers.get("Origin")
            if origin is None or origin.rstrip("/") not in {f"http://{h}" for h in allowed_hosts}:
                abort(403)
            if not same(request.form.get("csrf", ""), csrf_for(app)):
                abort(403)
        g.csrf = csrf_for(app)

    @app.context_processor
    def inject():
        return {"csrf": getattr(g, "csrf", "")}

    @app.after_request
    def headers(resp):
        resp.headers["Content-Security-Policy"] = CSP
        resp.headers["X-Content-Type-Options"] = "nosniff"
        # "no-referrer" makes browsers send "Origin: null" on form POSTs (Fetch spec), which the Origin
        # check below rejects, so uploads failed in real browsers. same-origin keeps the real Origin
        # for our own forms and still sends no referrer to any other site.
        resp.headers["Referrer-Policy"] = "same-origin"
        resp.headers["Cache-Control"] = "no-store"
        resp.headers["X-Frame-Options"] = "DENY"
        return resp
