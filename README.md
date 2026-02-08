# Listify

**Listify** is a small web application that lets you automatically create a Spotify playlist from your **Liked Songs** or **Top Tracks**.

The app uses:
- **Flask** (backend)
- **Spotify Web API** (OAuth authentication)
- **Docker & Docker Compose**
- optionally **Cloudflare Tunnel** for secure hosting without exposing ports

## Features
- Login with Spotify
- Create a playlist from:
  - Liked Songs **or**
  - Top Tracks (with time range selection)
- Choose the number of tracks (up to 10,000)
- Public or private playlists
- Mobile-friendly UI with automatic dark/light mode

## Requirements
- Docker & Docker Compose
- Spotify Premium account
- Spotify Developer App  
  https://developer.spotify.com/dashboard

## Configuration
The application is configured using environment variables.  
A template file is included in the repository.

### `.env.example`

```env
# Flask
FLASK_SECRET_KEY=CHANGE_ME_USE_RANDOM_SECRET

# Spotify Developer App
SPOTIFY_CLIENT_ID=YOUR_SPOTIFY_CLIENT_ID
SPOTIFY_CLIENT_SECRET=YOUR_SPOTIFY_CLIENT_SECRET

# Spotify Redirect URL - must also be set in the Spotify Dashboard
SPOTIFY_REDIRECT_URI=https://YOUR_DOMAIN/callback

# Optional: default playlist visibility (true / false)
DEFAULT_PLAYLIST_PUBLIC=false
```
### Setup Steps
1. Copy the example file
```cp .env.example .env```

2.	Edit .env and fill in your values:
- FLASK_SECRET_KEY
(generate one with `python -c "import secrets; print(secrets.token_hex(32))"`)
- SPOTIFY_CLIENT_ID
- SPOTIFY_CLIENT_SECRET
- SPOTIFY_REDIRECT_URI (Example: `https://listify.example.com/callback`)

3.	Important:
The redirect URL must match exactly the value configured in the Spotify Developer Dashboard.

### Running the App
```
docker compose up -d --build
```

Notes
- Spotify playlist limit: up to 10,000 tracks
- If fewer tracks are available, only the existing tracks will be added
- Some external services may require the playlist to be public