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

## UPI Payment System
- **upi_payment.py** — multipart form parser, screenshot saving, UPI ID (gk29052005@ptaxis).
- **ai_verifier.py** — OpenAI GPT-4o Vision integration; analyzes screenshots and
  suggests verified/suspicious/rejected. Falls back to 'manual' without OPENAI_API_KEY.
- UPI is the primary payment method on the payment page (QR code + copy UPI ID).
- After paying, users submit: sender name, UTR number, payment screenshot.
- AI analyzes the screenshot and suggests approve/reject; admin makes final call.
- Screenshots are stored privately in `data/screenshots/` (admin-only via /screenshot).
- Admin panel shows UPI Payment Verifications section with AI recommendation + approve/reject.

## Scraper System
- **igscrapper.py** — main scraper with 3 strategies (tried in order):
  1. `instagrapi` (private mobile API) — most robust, needs non-flagged IP
  2. Web API with session cookies — `instagram.com/api/v1/users/web_profile_info/`
  3. Direct HTML request — original approach, extracts JSON from `<script>` tags
- All strategies use Tor SOCKS5 proxy (127.0.0.1:9050) if available.
- `INSTAGRAM_PROXY` env var overrides Tor with a custom proxy (residential recommended).
- `extract_timeline_data` handles both API JSON and embedded HTML JSON formats.
- `extract_highest_resolution_urls` handles `image_versions2`, `display_url`, and carousel posts.
- **alt_scraper.py** — separate alternative scraper using `curl_cffi` (Chrome TLS impersonation) + Tor.
  Uses a different technique: browser fingerprint impersonation for API + HTML scraping.
  Run standalone: `python alt_scraper.py official_paul_7814`
- Instagram blocks datacenter IPs (429/login redirect); success depends on Tor exit node.
- Scrape takes ~30-40s due to multiple strategy attempts through Tor.

## Stealth Scraper
- **stealth_scraper.py** — multi-strategy private profile scraper, SEPARATE from
  igscrapper.py and private_scraper.py. Combines techniques from 7 strategies:
  1. obitouka/InstagramPrivSniffer — curl_cffi Chrome impersonation + regex post-code
     extraction from profile HTML + GraphQL media fetch for individual posts.
  2. arcanecfg/Instagram-Private-Scraper — ?__a=1 JSON endpoint + max_id pagination.
  3. drawrowfly/instagram-scraper — GraphQL query-hash pagination (user hash
     003056d32c2554def87228bc3fd9668a) with csrftoken cookies.
  4. SREEHARI1994/InstagramScraper — instagrapi session-based login for truly private
     accounts (needs IG_SESSION_USER and IG_SESSION_PASS env vars).
  5. instaloader/instaloader — iterates ALL posts via Profile.get_posts() lazy iterator.
     Gets the most posts (no hard limit). Best for extracting every single post.
  6. web_profile_info API — uses Instagram's web_profile_info API + GraphQL pagination
     (same approach as private_scraper.py). Most reliable for direct connection.
  7. kevmaindev/Instagram-Followers-Scraper_Suite — session-based API using IG_SESSION_ID
     cookie + friendships endpoint for private accounts.
- Tries ALL strategies and returns the result from whichever scraper found the MOST posts
  (not first-success-wins). Skips Tor if direct already found >=5 posts.
- Costs 3 credits per scan, finds up to 80 posts.
- Route: /scrape-stealth (deducts 3 credits) → /scrape-stealth-result (executes scrape)
- Optional env vars: IG_SESSION_USER, IG_SESSION_PASS, IG_SESSION_ID

## Profile Info Scraper
- **profile_info_scraper.py** — separate scraper for Instagram private account info.
  Extracts: followers, following, total posts, bio, profile picture URL, is_private,
  is_verified, full_name, external_url, category.
- Uses 4 strategies: web_profile_info API, HTML meta tags, instaloader Profile, session API.
- Costs 1 credit per scan.
- Route: /scrape-profile-info (deducts 1 credit) → /scrape-profile-info-result (executes)
- Displays results in a dedicated profile info HTML page with stats cards.

## Followers Scraper
- **followers_scraper.py** — extracts follower USERNAMES (not just count) from any
  Instagram profile.
- **Primary strategy: Playwright + picuki/tikvib** — uses headless Chromium to load
  picuki.com/followers/{username}, a public IG viewer that shows follower lists
  without Instagram login. Playwright handles Cloudflare's JS challenge automatically.
  Returns ~30 usernames per scan. Works for PUBLIC accounts without any credentials.
- Fallback strategies (require IG credentials): friendships API (IG_SESSION_ID),
  instaloader get_followers() (IG_SESSION_USER/PASS), GraphQL pagination (IG_SESSION_ID).
- For PRIVATE accounts, IG_SESSION_ID or IG_SESSION_USER + IG_SESSION_PASS must be set.
- Returns up to 200 usernames per scan. Costs 2 credits.
- Route: /scrape-followers (deducts 2 credits) → /scrape-followers-result (executes)
- Results page shows clickable list of follower usernames linking to their IG profiles.
- Playwright + Chromium are installed via Dockerfile.base44 (build step, not per-start).

## Notes
- Instagram blocks datacenter IPs; scraper relies on Tor exit nodes (may fail if flagged).
- Set `INSTAGRAM_PROXY` to a residential proxy for reliable scraping.
- OPENAI_API_KEY is optional — without it, UPI submissions default to manual admin review.
- No live-reload dev server; call `reload_preview` after code changes.
