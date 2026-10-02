# AGENTS.md

## Project Overview
Single-file Python CLI tool (`igscrapper.py`) that scrapes an Instagram
profile, extracts highest-resolution image URLs from embedded JSON, generates
a cyberpunk-themed HTML gallery, and serves it via Python's built-in HTTP server.

## Architecture
- **Original entry point**: `igscrapper.py` — interactive CLI (`input()` for username).
- **Web entry point**: `web_server.py` — wraps the scraping functions as a web app
  on port 3000 (landing form → scrape → gallery HTML).
- **parascode.py** — shim module providing `render`, `cprint`, `link` no-ops so
  `igscrapper.py` imports cleanly in a non-terminal/server context.

## Dependencies
`requests`, `beautifulsoup4`, `lxml`, `html5lib` (see `requirements.txt`).
Installed at container startup via pip (no prebuilt image).

## Running
```
docker compose -f docker-compose.base44.yml up -d --build
```
App listens on port 3000. Health check: `GET /`.

## Notes
- Instagram may block scraping from datacenter IPs; the app will show an
  "Unsuccessful" page if the profile fetch fails or no timeline data is found.
- No external secrets required.
- No live-reload dev server; call `reload_preview` after code changes.
