# Base44 Dev Environment

## Project Overview
Cipher is a Python CLI tool that scrapes Instagram profiles for image URLs and
serves an HTML gallery. The original entry point (`igscrapper.py`) is interactive
(uses `input()` for the username prompt) and serves on port 8080.

## Running in the Preview
A web wrapper (`web_server.py`) adapts the tool for the browser preview:
- Serves a landing page with a username form on **port 3000**
- On submit, reuses the scraping functions from `igscrapper.py`
- Returns the gallery HTML (or the "unsuccessful" page if Instagram blocks the request)

### Start
```bash
docker compose -f docker-compose.base44.yml up -d --build
```

### Dependencies
`requests`, `beautifulsoup4`, `lxml`, `parascode` — installed in the Dockerfile.

### Notes
- Instagram blocks datacenter IPs, so scraping from the sandbox will usually return
  the "unsuccessful" page. This is expected, not a bug.
- `igscrapper.py` is unchanged; `web_server.py` imports its functions.
- No live-reload (plain `http.server`); restart the container after code changes:
  `docker compose -f docker-compose.base44.yml restart web`
- No external secrets required.
