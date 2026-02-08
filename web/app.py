import os
import secrets
import time

from flask import Flask, jsonify, redirect, render_template, request, session, url_for
from dotenv import load_dotenv
from werkzeug.middleware.proxy_fix import ProxyFix

import spotify as sp

load_dotenv()

app = Flask(__name__)

app.config.update(
    SESSION_COOKIE_SECURE=True,     # only use HTTPS
    SESSION_COOKIE_HTTPONLY=True,   # no JS-access
    SESSION_COOKIE_SAMESITE="Lax",  # OAuth
)

app.wsgi_app = ProxyFix(
    app.wsgi_app,
    x_for=1,
    x_proto=1,
    x_host=1,
)

app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-secret-change-me")

DEFAULT_PLAYLIST_PUBLIC = os.environ.get("DEFAULT_PLAYLIST_PUBLIC", "false").lower() == "true"
MAX_LIMIT = 10000


def _is_logged_in() -> bool:
    return "spotify_token" in session


def _get_valid_access_token() -> str:
    """
    Returns a valid access token; refreshes if needed.
    Stored in Flask session cookie (signed). For production, prefer server-side sessions.
    """
    token = session.get("spotify_token")
    if not token:
        raise sp.SpotifyError("Not authenticated")

    expires_at = int(token.get("expires_at", 0))
    # refresh a bit early
    if time.time() > (expires_at - 60):
        refreshed = sp.refresh_access_token(token["refresh_token"])
        session["spotify_token"] = refreshed
        token = refreshed

    return token["access_token"]


@app.get("/")
def index():
    logged_in = _is_logged_in()
    me = None
    if logged_in:
        try:
            access = _get_valid_access_token()
            me = sp.get_me(access)
        except Exception:
            # If token is invalid, force logout
            session.clear()
            logged_in = False
            me = None

    return render_template("index.html", logged_in=logged_in, me=me)


@app.get("/login")
def login():
    state = secrets.token_urlsafe(24)
    session["oauth_state"] = state
    return redirect(sp.build_login_url(state))


@app.get("/callback")
def callback():
    err = request.args.get("error")
    if err:
        return f"Spotify login error: {err}", 400

    code = request.args.get("code")
    state = request.args.get("state")

    if not code or not state or state != session.get("oauth_state"):
        return "Invalid OAuth state", 400

    token = sp.exchange_code_for_token(code)
    session["spotify_token"] = token
    session.pop("oauth_state", None)
    return redirect(url_for("index"))


@app.post("/api/create_playlist")
def api_create_playlist():
    if not _is_logged_in():
        return jsonify({"error": "not_logged_in"}), 401

    payload = request.get_json(force=True) or {}

    source = payload.get("source", "liked")  # "liked" oder "top"
    time_range = payload.get("time_range", "short_term")
    limit = int(payload.get("limit", 50))
    playlist_name = payload.get("name", "Meine Lieblingssongs")
    public = bool(payload.get("public", DEFAULT_PLAYLIST_PUBLIC))
    description = payload.get(
        "description",
        "Automatisch erstellt aus deinen Spotify Liked Songs" if source == "liked"
        else "Automatisch erstellt aus deinen Spotify Top Tracks"
    )

    if source not in {"liked", "top"}:
        return jsonify({"error": "invalid_source"}), 400

    # time_range nur prüfen, wenn Top Tracks gewählt sind
    if source == "top" and time_range not in {"short_term", "medium_term", "long_term"}:
        return jsonify({"error": "invalid_time_range"}), 400

    if limit < 1 or limit > MAX_LIMIT:
        return jsonify({"error": "invalid_limit"}), 400

    if not playlist_name or len(playlist_name) > 100:
        return jsonify({"error": "invalid_name"}), 400

    try:
        access = _get_valid_access_token()
        me = sp.get_me(access)
        user_id = me["id"]

        if source == "liked":
            uris = sp.get_liked_tracks(access, limit=limit)
        else:
            uris = sp.get_top_tracks(access, time_range=time_range, limit=limit)

        if not uris:
            return jsonify({"error": "no_tracks_found"}), 400

        pl = sp.create_playlist(
            access_token=access,
            user_id=user_id,
            name=playlist_name,
            public=public,
            description=description,
        )
        sp.add_tracks_to_playlist(access, pl["id"], uris)

        return jsonify({
            "ok": True,
            "source": source,
            "time_range": time_range if source == "top" else None,
            "playlist_id": pl["id"],
            "playlist_url": pl.get("external_urls", {}).get("spotify"),
            "tracks_added": len(uris),
        })

    except sp.SpotifyError as e:
        return jsonify({"error": "spotify_error", "details": str(e)}), 500


@app.post("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))