# AGENTS.md

## Project Overview
Instagram profile image scraping tool with a full web app: user auth,
per-post payments (₹15), monthly plans, gift cards, invoices, and an
admin panel.  Cyberpunk-themed UI served by Python's built-in HTTP server.

## Architecture
- **web_server.py** — main entry point; routes all GET/POST endpoints,
  handles sessions via cookies, auth checks, payment processing.
- **database.py** — SQLite backend (`data/cipher.db`): users, sessions,
  payments, gift_cards, invoices.  Auto-creates admin user on first boot.
- **templates.py** — all HTML pages (landing, login, signup, dashboard,
  payment with animation, invoice with "chirag" signature, admin panel).
  Includes inline SVG logo and shared CSS.
- **igscrapper.py** — original CLI scraper; functions imported by
  web_server.py for the scraping pipeline (unchanged).
- **parascode.py** — shim module for igscrapper.py imports.

## Key Features
- **Auth**: signup/login with session cookies. Admin: chiragkashyap201@gmail.com / chirag2009
- **Payments**: ₹15 per post credit, or monthly plans (Basic ₹199, Pro ₹499, Elite ₹999).
  Simulated payment with premium CSS/JS animation (card flip → spinner → checkmark).
- **Gift Cards**: admin generates codes (GIFT-XXXXXXXX); users redeem for credits.
- **Invoices**: auto-generated per payment, with "chirag" signature in Sacramento font.
- **Admin Panel**: stats (users, revenue, payments, active cards), user/payment/invoice tables.
- **Logo**: inline SVG hexagon with stylized "C", cyan-magenta gradient.

## Dependencies
`requests`, `beautifulsoup4`, `lxml`, `html5lib`, `parascode`, `PySocks`
(see `requirements.txt`).  SQLite is stdlib (no extra dep).

## Running
```
docker compose -f docker-compose.base44.yml up -d --build
```
App listens on port 3000 (maps to 8080 inside container). Health check: `GET /`.
SQLite DB persists in a named Docker volume (`cipher_data`).

## Notes
- Instagram may block scraping from datacenter IPs; the app shows an
  "Unsuccessful" page if the profile fetch fails.
- No external secrets required.
- No live-reload dev server; call `reload_preview` after code changes.
