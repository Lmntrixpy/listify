import base64
import os
import time
from urllib.parse import urlencode

import requests

SPOTIFY_AUTH_URL = "https://accounts.spotify.com/authorize"
SPOTIFY_TOKEN_URL = "https://accounts.spotify.com/api/token"
SPOTIFY_API_BASE = "https://api.spotify.com/v1"

SCOPES = [
    "user-top-read",
    "user-library-read",
    "playlist-modify-public",
    "playlist-modify-private",
]


class SpotifyError(RuntimeError):
    pass


def _basic_auth_header(client_id: str, client_secret: str) -> str:
    raw = f"{client_id}:{client_secret}".encode("utf-8")
    return base64.b64encode(raw).decode("utf-8")


def build_login_url(state: str) -> str:
    client_id = os.environ["SPOTIFY_CLIENT_ID"]
    redirect_uri = os.environ["SPOTIFY_REDIRECT_URI"]
    params = {
        "response_type": "code",
        "client_id": client_id,
        "scope": " ".join(SCOPES),
        "redirect_uri": redirect_uri,
        "state": state,
        "show_dialog": "false",
    }
    return f"{SPOTIFY_AUTH_URL}?{urlencode(params)}"


def exchange_code_for_token(code: str) -> dict:
    client_id = os.environ["SPOTIFY_CLIENT_ID"]
    client_secret = os.environ["SPOTIFY_CLIENT_SECRET"]
    redirect_uri = os.environ["SPOTIFY_REDIRECT_URI"]

    headers = {
        "Authorization": f"Basic {_basic_auth_header(client_id, client_secret)}",
        "Content-Type": "application/x-www-form-urlencoded",
    }
    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": redirect_uri,
    }

    r = requests.post(SPOTIFY_TOKEN_URL, headers=headers, data=data, timeout=20)
    if r.status_code != 200:
        raise SpotifyError(f"Token exchange failed: {r.status_code} {r.text}")

    token = r.json()
    # Normalize expires_at (epoch seconds)
    token["expires_at"] = int(time.time()) + int(token.get("expires_in", 3600))
    return token


def refresh_access_token(refresh_token: str) -> dict:
    client_id = os.environ["SPOTIFY_CLIENT_ID"]
    client_secret = os.environ["SPOTIFY_CLIENT_SECRET"]

    headers = {
        "Authorization": f"Basic {_basic_auth_header(client_id, client_secret)}",
        "Content-Type": "application/x-www-form-urlencoded",
    }
    data = {
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
    }

    r = requests.post(SPOTIFY_TOKEN_URL, headers=headers, data=data, timeout=20)
    if r.status_code != 200:
        raise SpotifyError(f"Token refresh failed: {r.status_code} {r.text}")

    token = r.json()
    token["expires_at"] = int(time.time()) + int(token.get("expires_in", 3600))

    # Spotify may omit refresh_token on refresh; keep old one
    token["refresh_token"] = token.get("refresh_token") or refresh_token
    return token


def api_get(access_token: str, path: str, params: dict | None = None) -> dict:
    headers = {"Authorization": f"Bearer {access_token}"}
    r = requests.get(f"{SPOTIFY_API_BASE}{path}", headers=headers, params=params, timeout=20)
    if r.status_code >= 400:
        raise SpotifyError(f"GET {path} failed: {r.status_code} {r.text}")
    return r.json()


def api_post(access_token: str, path: str, json: dict | None = None) -> dict:
    headers = {"Authorization": f"Bearer {access_token}"}
    r = requests.post(f"{SPOTIFY_API_BASE}{path}", headers=headers, json=json, timeout=20)
    if r.status_code >= 400:
        raise SpotifyError(f"POST {path} failed: {r.status_code} {r.text}")
    return r.json()


def get_me(access_token: str) -> dict:
    return api_get(access_token, "/me")


def get_top_tracks(access_token: str, time_range: str, limit: int) -> list[str]:
    """
    Returns track URIs.
    Spotify returns max 50 per request; we paginate.
    """
    uris: list[str] = []
    remaining = max(0, min(limit, 10_000))  # cap to keep it simple
    offset = 0

    while remaining > 0:
        batch = min(50, remaining)
        data = api_get(
            access_token,
            "/me/top/tracks",
            params={"time_range": time_range, "limit": batch, "offset": offset},
        )
        items = data.get("items", [])
        for t in items:
            uri = t.get("uri")
            if uri:
                uris.append(uri)
        got = len(items)
        if got == 0:
            break
        remaining -= got
        offset += got

    # Deduplicate while preserving order
    seen = set()
    out = []
    for u in uris:
        if u not in seen:
            seen.add(u)
            out.append(u)
    return out


def get_liked_tracks(access_token: str, limit: int) -> list[str]:
    """
    Returns track URIs from the user's 'Liked Songs' (saved tracks).
    Paginates until no more items or limit reached.
    """
    uris: list[str] = []
    remaining = max(0, min(limit, 10000))  # playlist cap
    offset = 0

    while remaining > 0:
        batch = min(50, remaining)
        data = api_get(
            access_token,
            "/me/tracks",
            params={"limit": batch, "offset": offset},
        )
        items = data.get("items", [])
        for item in items:
            track = item.get("track") or {}
            uri = track.get("uri")
            if uri:
                uris.append(uri)

        got = len(items)
        if got == 0:
            break

        remaining -= got
        offset += got

    # Deduplicate while preserving order
    seen = set()
    out = []
    for u in uris:
        if u not in seen:
            seen.add(u)
            out.append(u)
    return out


def create_playlist(access_token: str, user_id: str, name: str, public: bool, description: str) -> dict:
    return api_post(
        access_token,
        f"/users/{user_id}/playlists",
        json={"name": name, "public": public, "description": description},
    )


def add_tracks_to_playlist(access_token: str, playlist_id: str, uris: list[str]) -> None:
    for i in range(0, len(uris), 100):
        chunk = uris[i : i + 100]
        api_post(access_token, f"/playlists/{playlist_id}/tracks", json={"uris": chunk})