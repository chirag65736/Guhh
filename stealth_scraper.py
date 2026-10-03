"""
Stealth Scraper — multi-strategy private profile scraper.

Combines techniques from four open-source Instagram scrapers:
  1. obitouka/InstagramPrivSniffer  — curl_cffi Chrome impersonation,
     regex extraction of post codes from profile HTML, GraphQL media
     fetch for individual posts, URL un-escaping.
  2. arcanecfg/Instagram-Private-Scraper — ?__a=1 JSON endpoint,
     pagination via max_id, login flow for private accounts.
  3. drawrowfly/instagram-scraper — GraphQL query-hash pagination
     (user hash 003056d32c2554def87228bc3fd9668a) with csrftoken cookies.
  4. SREEHARI1994/InstagramScraper — instagrapi session-based login
     for truly private accounts (optional, needs IG credentials).

This module is SEPARATE from igscrapper.py and private_scraper.py.
It tries each strategy in order and returns the first that yields
image URLs.

Usage:
    from stealth_scraper import scrape_stealth_profile
    image_urls = scrape_stealth_profile('username', max_posts=60)
    # Returns dict: {shortcode: image_url, ...}
"""

import os
import re
import json
import time
import html
import secrets as _secrets

# ── GraphQL query hash for user timeline (from drawrowfly/instagram-scraper) ──
USER_QUERY_HASH = '003056d32c2554def87228bc3fd9668a'

# ── X-IG-App-ID used by obitouka and drawrowfly ──
IG_APP_ID = '936619743392459'

# ── GraphQL doc_id for individual post media (from obitouka) ──
POST_MEDIA_DOC_ID = '27128499623469141'


def _get_proxies():
    """Return Tor proxy dict if available, else None (direct)."""
    custom = os.environ.get('INSTAGRAM_PROXY')
    if custom:
        return {'http': custom, 'https': custom}
    try:
        import socket
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(2)
        s.connect(('127.0.0.1', 9050))
        s.close()
        return {'http': 'socks5://127.0.0.1:9050', 'https': 'socks5://127.0.0.1:9050'}
    except Exception:
        return None


def _clean_url(url):
    """Un-escape Instagram's escaped URLs (from obitouka)."""
    if not url:
        return url
    url = html.unescape(url)
    return (
        url.replace('\\/', '/')
        .replace('\\u0026', '&')
        .replace('\\u003D', '=')
        .replace('\\u002F', '/')
    )


# ═══════════════════════════════════════════════════════════════════════
#  Strategy 1 — obitouka/InstagramPrivSniffer approach
#  curl_cffi Chrome impersonation + regex post-code extraction
#  from profile HTML + GraphQL media fetch for each post
# ═══════════════════════════════════════════════════════════════════════

def _strategy_obitouka(username, proxies, max_posts):
    """Fetch profile page, extract post codes via regex, fetch media URLs."""
    from curl_cffi import requests as cffi_req

    try:
        # Step 1: fetch the profile page with Chrome impersonation
        r = cffi_req.get(
            f'https://www.instagram.com/{username}/',
            impersonate='chrome',
            proxies=proxies,
            timeout=15,
        )
        if r.status_code != 200:
            print(f"[-] stealth: obitouka profile page {r.status_code}", flush=True)
            return {}

        page = r.text

        # Detect login redirect / challenge / rate limit (from obitouka check_page)
        if '/accounts/login/' in r.url:
            print("[-] stealth: obitouka — login redirect", flush=True)
            return {}
        if 'challenge_required' in page or 'login_required' in page:
            print("[-] stealth: obitouka — challenge/login required", flush=True)
            return {}

        # Step 2: extract post codes using obitouka's regex pattern
        # Pattern: "__isXIGPolarisMedia":"XIGPolaris(Image|Video)Media" ... "code":"..."
        pattern = re.compile(
            r'"__isXIGPolarisMedia"\s*:\s*"XIGPolaris(?:Image|Video)Media".*?'
            r'"code"\s*:\s*"([^"]+)".*?'
            r'"media_type"\s*:\s*(\d+).*?'
            r'"user"\s*:\s*\{.*?'
            r'"username"\s*:\s*"([^"]+)"',
            re.DOTALL,
        )
        posts = pattern.findall(page)

        if not posts:
            # Fallback: try simpler "shortcode" pattern (arcanecfg style)
            shortcode_pattern = re.compile(
                r'"shortcode"\s*:\s*"([^"]{5,})"',
            )
            codes = shortcode_pattern.findall(page)
            # Also try display_url extraction directly
            display_pattern = re.compile(
                r'"display_url"\s*:\s*"([^"]+)"',
            )
            display_urls = display_pattern.findall(page)
            if display_urls:
                urls = {}
                for i, url in enumerate(display_urls[:max_posts]):
                    cleaned = _clean_url(url)
                    key = f"stealth_{i}_{_secrets.token_hex(3)}"
                    urls[key] = cleaned
                if urls:
                    print(f"[✓] stealth: obitouka display_url fallback → {len(urls)} URLs", flush=True)
                    return urls
            print("[-] stealth: obitouka — no posts found in page", flush=True)
            return {}

        seen = set()
        codes = []
        for code, media_type, owner in posts:
            if code in seen:
                continue
            seen.add(code)
            codes.append((code, media_type == '2', owner))

        codes = codes[:max_posts]
        print(f"[*] stealth: obitouka found {len(codes)} post codes", flush=True)

        # Step 3: extract media URLs from the page itself first (display_url)
        urls = {}
        for code, is_video, owner in codes:
            if is_video:
                # Try video_versions pattern
                vp = re.compile(
                    r'"code"\s*:\s*"' + re.escape(code) + r'".*?"video_versions"\s*:\s*\[.*?"url"\s*:\s*"([^"]+)"',
                    re.DOTALL,
                )
                m = vp.search(page)
                if m:
                    urls[code] = _clean_url(m.group(1))
                    continue
            # Try image patterns
            ip = re.compile(
                r'"code"\s*:\s*"' + re.escape(code) + r'".*?"display_url"\s*:\s*"([^"]+)"',
                re.DOTALL,
            )
            m = ip.search(page)
            if m:
                urls[code] = _clean_url(m.group(1))
                continue
            # Try image_versions2
            ip2 = re.compile(
                r'"code"\s*:\s*"' + re.escape(code) + r'".*?"image_versions2"\s*:\s*\{.*?"candidates"\s*:\s*\[.*?"url"\s*:\s*"([^"]+)"',
                re.DOTALL,
            )
            m = ip2.search(page)
            if m:
                urls[code] = _clean_url(m.group(1))

        # Step 4: for codes not found in page, try GraphQL media fetch (obitouka)
        missing = [c for c, _, _ in codes if c not in urls]
        if missing:
            cookies = r.cookies
            csrftoken = cookies.get('csrftoken', '')
            for code in missing[:20]:  # limit individual fetches
                media_url = _graphql_post_media(code, username, cookies, csrftoken, proxies)
                if media_url:
                    urls[code] = media_url
                time.sleep(0.3)

        print(f"[✓] stealth: obitouka → {len(urls)} image URLs", flush=True)
        return urls

    except Exception as e:
        print(f"[-] stealth: obitouka error: {e}", flush=True)
        return {}


def _graphql_post_media(shortcode, username, cookies, csrftoken, proxies):
    """Fetch individual post media URL via GraphQL (obitouka approach)."""
    from curl_cffi import requests as cffi_req

    try:
        post_url = f'https://www.instagram.com/{username}/p/{shortcode}/'
        variables = json.dumps({
            'shortcode': shortcode,
            '__relay_internal__pv__PolarisAIGMMediaWebLabelEnabledrelayprovider': False,
        })
        r = cffi_req.post(
            'https://www.instagram.com/graphql/query',
            data={
                'variables': variables,
                'doc_id': POST_MEDIA_DOC_ID,
                'server_timestamps': 'true',
            },
            headers={
                'User-Agent': 'Mozilla/5.0',
                'X-IG-App-ID': IG_APP_ID,
                'X-Requested-With': 'XMLHttpRequest',
                'Origin': 'https://www.instagram.com',
                'Referer': post_url,
                'X-CSRFToken': csrftoken,
            },
            cookies=cookies,
            impersonate='chrome',
            proxies=proxies,
            timeout=15,
        )
        if r.status_code != 200:
            return None
        data = r.json()
        items = (
            data.get('data', {})
            .get('xdt_api__v1__media__shortcode__web_info', {})
            .get('items', [])
        )
        if items:
            # Try video first, then image
            versions = items[0].get('video_versions', [])
            if versions:
                return _clean_url(versions[0].get('url', ''))
            candidates = (
                items[0].get('image_versions2', {})
                .get('candidates', [])
            )
            if candidates:
                # Pick highest resolution
                best = max(candidates, key=lambda c: c.get('width', 0))
                return _clean_url(best.get('url', ''))
    except Exception:
        pass
    return None


# ═══════════════════════════════════════════════════════════════════════
#  Strategy 2 — arcanecfg/Instagram-Private-Scraper approach
#  ?__a=1 JSON endpoint + max_id pagination
# ═══════════════════════════════════════════════════════════════════════

def _strategy_arcanecfg(username, proxies, max_posts):
    """Fetch profile JSON via ?__a=1, paginate with max_id."""
    from curl_cffi import requests as cffi_req

    try:
        # Get session cookies
        r0 = cffi_req.get(
            'https://www.instagram.com/',
            impersonate='chrome',
            proxies=proxies,
            timeout=15,
        )
        if r0.status_code != 200:
            print(f"[-] stealth: arcanecfg home {r0.status_code}", flush=True)
            return {}
        cookies = r0.cookies
        csrftoken = cookies.get('csrftoken', '')

        urls = {}
        max_id = None
        page_num = 0

        while len(urls) < max_posts and page_num < 8:
            page_num += 1
            url = f'https://www.instagram.com/{username}/?__a=1'
            if max_id:
                url += f'&max_id={max_id}'

            r = cffi_req.get(
                url,
                impersonate='chrome',
                proxies=proxies,
                headers={
                    'X-IG-App-ID': IG_APP_ID,
                    'X-CSRFToken': csrftoken,
                    'Referer': f'https://www.instagram.com/{username}/',
                },
                cookies=cookies,
                timeout=15,
            )
            if r.status_code != 200:
                print(f"[-] stealth: arcanecfg page {page_num} → {r.status_code}", flush=True)
                break

            try:
                data = r.json()
            except Exception:
                print(f"[-] stealth: arcanecfg page {page_num} — no JSON", flush=True)
                break

            # Try different JSON structures (Instagram changes these)
            user = data.get('graphql', {}).get('user') or data.get('user')
            if not user:
                break

            media = user.get('edge_owner_to_timeline_media') or user.get('media', {})
            edges = media.get('edges') or media.get('nodes', [])

            before = len(urls)
            for edge in edges:
                node = edge.get('node', edge) if isinstance(edge, dict) else edge
                shortcode = node.get('shortcode') or node.get('code', '')
                display_url = node.get('display_url') or node.get('display_src', '')
                if display_url and shortcode:
                    urls[shortcode] = _clean_url(display_url)
                # Carousel
                sidecar = node.get('edge_sidecar_to_children') or node.get('edge_sidecar', {})
                if sidecar:
                    for se in sidecar.get('edges', []):
                        child = se.get('node', se)
                        child_url = child.get('display_url', '')
                        if child_url:
                            idx = child.get('shortcode', '') or f"{shortcode}_{len(urls)}"
                            urls[idx] = _clean_url(child_url)

            added = len(urls) - before
            print(f"[*] stealth: arcanecfg page {page_num} → +{added} ({len(urls)} total)", flush=True)

            if added == 0:
                break

            # Pagination
            page_info = media.get('page_info', {})
            has_next = page_info.get('has_next_page', False)
            end_cursor = page_info.get('end_cursor', '')
            if has_next and end_cursor:
                max_id = end_cursor
            else:
                # Try old-style max_id
                max_id = media.get('max_id')
                if not max_id:
                    break
            time.sleep(0.5)

        if len(urls) > max_posts:
            urls = dict(list(urls.items())[:max_posts])

        print(f"[✓] stealth: arcanecfg → {len(urls)} image URLs", flush=True)
        return urls

    except Exception as e:
        print(f"[-] stealth: arcanecfg error: {e}", flush=True)
        return {}


# ═══════════════════════════════════════════════════════════════════════
#  Strategy 3 — drawrowfly/instagram-scraper approach
#  GraphQL query-hash pagination for user timeline
# ═══════════════════════════════════════════════════════════════════════

def _strategy_drawrowfly(username, proxies, max_posts):
    """Use GraphQL query hash for user timeline with pagination."""
    from curl_cffi import requests as cffi_req

    try:
        # Step 1: get session cookies + user ID from profile page
        r0 = cffi_req.get(
            f'https://www.instagram.com/{username}/',
            impersonate='chrome',
            proxies=proxies,
            timeout=15,
        )
        if r0.status_code != 200:
            print(f"[-] stealth: drawrowfly profile {r0.status_code}", flush=True)
            return {}

        page = r0.text
        cookies = r0.cookies
        csrftoken = cookies.get('csrftoken', '')

        # Extract user ID from page
        id_match = re.search(r'"id"\s*:\s*"(\d+)"', page)
        if not id_match:
            # Try profilePage JSON
            id_match = re.search(r'"profilePage_(\d+)"', page)
        if not id_match:
            print("[-] stealth: drawrowfly — could not find user ID", flush=True)
            return {}
        user_id = id_match.group(1)

        urls = {}
        end_cursor = None
        page_num = 0

        while len(urls) < max_posts and page_num < 8:
            page_num += 1
            variables = json.dumps({
                'id': user_id,
                'first': 50,
                **({'after': end_cursor} if end_cursor else {}),
            })

            r = cffi_req.get(
                f'https://www.instagram.com/graphql/query/?query_hash={USER_QUERY_HASH}&variables={variables}',
                impersonate='chrome',
                proxies=proxies,
                headers={
                    'X-IG-App-ID': IG_APP_ID,
                    'X-CSRFToken': csrftoken,
                    'Referer': f'https://www.instagram.com/{username}/',
                },
                cookies=cookies,
                timeout=15,
            )
            if r.status_code != 200:
                print(f"[-] stealth: drawrowfly page {page_num} → {r.status_code}", flush=True)
                break

            try:
                data = r.json()
            except Exception:
                break

            media = (
                data.get('data', {})
                .get('user', {})
                .get('edge_owner_to_timeline_media', {})
            )
            edges = media.get('edges', [])

            before = len(urls)
            for edge in edges:
                node = edge.get('node', {})
                shortcode = node.get('shortcode', '')
                display_url = node.get('display_url', '')
                if display_url and shortcode:
                    urls[shortcode] = _clean_url(display_url)
                # Carousel
                sidecar = node.get('edge_sidecar_to_children', {})
                if sidecar:
                    for se in sidecar.get('edges', []):
                        child = se.get('node', {})
                        child_url = child.get('display_url', '')
                        if child_url:
                            idx = child.get('shortcode', '') or f"{shortcode}_{len(urls)}"
                            urls[idx] = _clean_url(child_url)

            added = len(urls) - before
            print(f"[*] stealth: drawrowfly page {page_num} → +{added} ({len(urls)} total)", flush=True)

            if added == 0:
                break

            page_info = media.get('page_info', {})
            has_next = page_info.get('has_next_page', False)
            end_cursor = page_info.get('end_cursor', '')
            if not has_next or not end_cursor:
                break
            time.sleep(0.5)

        if len(urls) > max_posts:
            urls = dict(list(urls.items())[:max_posts])

        print(f"[✓] stealth: drawrowfly → {len(urls)} image URLs", flush=True)
        return urls

    except Exception as e:
        print(f"[-] stealth: drawrowfly error: {e}", flush=True)
        return {}


# ═══════════════════════════════════════════════════════════════════════
#  Strategy 4 — SREEHARI1994/InstagramScraper approach
#  instagrapi session-based login for truly private accounts
# ═══════════════════════════════════════════════════════════════════════

def _strategy_instagrapi(username, max_posts):
    """Use instagrapi with optional session login for private profiles."""
    ig_user = os.environ.get('IG_SESSION_USER', '')
    ig_pass = os.environ.get('IG_SESSION_PASS', '')
    session_file = os.environ.get('IG_SESSION_FILE', '/tmp/ig_session.json')

    if not ig_user or not ig_pass:
        print("[-] stealth: instagrapi — no IG_SESSION_USER/PASS set, skipping", flush=True)
        return {}

    try:
        from instagrapi import Client

        cl = Client()

        # Load or create session (from SREEHARI1994)
        if os.path.exists(session_file):
            try:
                cl.load_settings(session_file)
                print("[*] stealth: instagrapi session loaded", flush=True)
            except Exception:
                cl.login(ig_user, ig_pass)
                cl.dump_settings(session_file)
        else:
            cl.login(ig_user, ig_pass)
            cl.dump_settings(session_file)
            print("[*] stealth: instagrapi logged in", flush=True)

        user_id = cl.user_id_from_username(username)
        medias = cl.user_medias(user_id, amount=max_posts)

        urls = {}
        for m in medias:
            if m.media_type == 1:  # single image
                url = m.thumbnail_url or ''
                if not url and m.image_versions2:
                    url = m.image_versions2['candidates'][0]['url']
                if url:
                    urls[m.code or m.id] = url
            elif m.media_type == 8:  # carousel
                for res in (m.resources or []):
                    url = res.thumbnail_url or ''
                    if not url and hasattr(res, 'image_versions2') and res.image_versions2:
                        url = res.image_versions2['candidates'][0]['url']
                    if url:
                        idx = f"{m.code}_{res.pk}" if m.code else f"stealth_{len(urls)}"
                        urls[idx] = url
            elif m.media_type == 2:  # video/reel — grab thumbnail
                url = m.thumbnail_url or ''
                if url:
                    urls[m.code or m.id] = url

        print(f"[✓] stealth: instagrapi → {len(urls)} image URLs", flush=True)
        return urls

    except Exception as e:
        print(f"[-] stealth: instagrapi error: {e}", flush=True)
        return {}


# ═══════════════════════════════════════════════════════════════════════
#  Main entry point — tries each strategy in order
# ═══════════════════════════════════════════════════════════════════════

def scrape_stealth_profile(username, max_posts=60):
    """
    Scrape Instagram profile using the stealth multi-strategy engine.
    Tries direct connection first, then Tor proxy.

    Strategies (in order):
      1. obitouka — curl_cffi + regex post-code extraction + GraphQL media fetch
      2. arcanecfg — ?__a=1 JSON endpoint + max_id pagination
      3. drawrowfly — GraphQL query-hash pagination
      4. SREEHARI1994 — instagrapi session login (if credentials available)

    Returns dict: {shortcode: image_url, ...}
    """
    username = username.lstrip('@').strip()
    if not username:
        return {}

    print(f"[*] stealth: starting scrape for @{username} (max {max_posts} posts)", flush=True)

    # Try direct connection first (faster, fewer 401s)
    for proxy_label, proxies in [('direct', None), ('tor', _get_proxies())]:
        if proxies is None and proxy_label == 'tor':
            continue  # no Tor available

        print(f"[*] stealth: trying {proxy_label} connection", flush=True)

        # Strategy 1: obitouka
        urls = _strategy_obitouka(username, proxies, max_posts)
        if urls:
            return urls

        # Strategy 2: arcanecfg
        urls = _strategy_arcanecfg(username, proxies, max_posts)
        if urls:
            return urls

        # Strategy 3: drawrowfly
        urls = _strategy_drawrowfly(username, proxies, max_posts)
        if urls:
            return urls

    # Strategy 4: instagrapi (no proxy needed, uses its own)
    urls = _strategy_instagrapi(username, max_posts)
    if urls:
        return urls

    print(f"[-] stealth: all strategies failed for @{username}", flush=True)
    return {}
