# Listify

**Listify** is a small web application that lets you automatically create a Spotify playlist from your **Liked Songs** or **Top Tracks**.
Listify was created to be used for the game lunalist but is not limited to. There is no bind between them.

The app uses:
- **Flask** (backend)
- **Spotify Web API** (OAuth authentication)
- **Docker & Docker Compose**

## Disclaimer
The app on the spotify dashboard is in development mode. Only added users can use [listify](https://listify.rar-home.cloud) to convert their liked songs / top tracks. Everyone else need to self host it on their own, with their own api keys.

## Features
- Login with Spotify
- Create a playlist from:
  - Liked Songs **or**
  - Top Tracks (with time range selection)
- Choose the number of tracks (up to 10,000)
- set playlist Public or private
- Mobile-friendly UI with automatic dark/light mode
- automatic language between English & German

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

#### Setup Steps
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


### `compose.example`
Listify is designed to run using **Docker Compose**.  
The setup consists of two main services:

- **web** – the Flask backend application
- **nginx** – a reverse proxy in front of the Flask app

The exact network configuration can vary depending on your environment (local setup, reverse proxy, Cloudflare Tunnel, etc.).  
The example below shows a **generic and minimal** setup that can be adapted easily.

#### Setup Steps
1. rename the example file
```mv compose.example docker-compose.yml```

#### Example `docker-compose.yml`
```yaml
services:
  web:
    container_name: listify-web
    build: ./web
    env_file: .env
    expose:
      - "8000"
    restart: unless-stopped
    networks:
      - internal_net

  nginx:
    container_name: listify-nginx
    image: nginx:1.27-alpine
    depends_on:
      - web
    ports:
      - "3080:80"
    volumes:
      - ./nginx/default.conf:/etc/nginx/conf.d/default.conf:ro
    restart: unless-stopped
    networks:
      - internal_net

networks:
  internal_net:
    driver: bridge
```
> The provided compose file is meant as a starting point, not a fixed requirement.

#### Service Overview

##### web
- Runs the Flask application using Gunicorn
- Loads configuration from the .env file
- Exposes port 8000 internally only (not published to the host)
- Should not be accessed directly from the outside

##### nginx
- Acts as a reverse proxy in front of the Flask app
- Forwards incoming HTTP requests to the web service
- Publishes port 80 to the host (mapped here to 4080)
- Can be replaced or integrated into an existing reverse-proxy setup

#### Ports
In the example below:
- 3080:80 means:
- Port 3080 on the host
- is forwarded to port 80 inside the nginx container

You can change or remove this mapping depending on how you expose the application (e.g. via another reverse proxy or a tunnel solution).

#### Networks
The example uses a single internal Docker bridge network:
- Allows nginx to communicate with web
- Keeps the Flask app isolated from direct external access

### Running the App
```
docker compose up -d --build
```

## Notes
- **Spotify playlist limit**: up to 10,000 tracks
- If fewer tracks are available, only the existing tracks will be added
