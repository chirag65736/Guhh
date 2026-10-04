"""
Stealth Scraper — multi-strategy private profile scraper.

Combines techniques from six open-source Instagram scrapers:
  1. obitouka/InstagramPrivSniffer  — curl_cffi Chrome impersonation,
     regex extraction of post codes from profile HTML, GraphQL media
     fetch for individual posts, URL un-escaping.
  2. arcanecfg/Instagram-Private-Scraper — ?__a=1 JSON endpoint,
     pagination via max_id, login flow for private accounts.
  3. drawrowfly/instagram-scraper — GraphQL query-hash pagination
     (user hash 003056d32c2554def87228bc3fd9668a) with csrftoken cookies.
  4. SREEHARI1994/InstagramScraper — instagrapi session-based login
     for truly private accounts (optional, needs IG credentials).
  5. instaloader/instaloader — iterates ALL posts via Profile.get_posts()
     lazy iterator. Gets the most posts (no hard limit). Best for
     extracting every single post from a profile.
  6. kevmaindev/Instagram-Followers-Scraper_Suite — session-based API
     using IG_SESSION_ID cookie + friendships endpoint for private
     accounts. Optional, needs IG_SESSION_ID env var.

This module is SEPARATE from igscrapper.py and private_scraper.py.
It tries ALL strategies, then returns the result from whichever
scraper found the MOST posts.

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

# ── GraphQL doc_ID for individual post media (from obitouka) ──
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
#  Strategy 0 — Profile page Relay data extraction (FASTEST)
#  Fetches the logged-out profile page HTML through Tor and extracts
#  post image URLs from embedded Relay/GraphQL data in <script data-sjs>
#  tags. The 'polaris_ordered_timeline_connection' field contains the
#  first page of posts with display_uri (image URLs).
#  This is the fastest strategy — single HTTP request, no API calls.
# ═══════════════════════════════════════════════════════════════════════

def _strategy_profile_page(username, proxies, max_posts):
    """Extract image URLs from profile page embedded Relay data."""
    from curl_cffi import requests as cffi_req

    try:
        session = cffi_req.Session()
        session.get('https://www.instagram.com/', impersonate='chrome',
                     proxies=proxies, timeout=12)

        r = session.get(
            f'https://www.instagram.com/{username}/',
            impersonate='chrome',
            proxies=proxies,
            timeout=12,
        )
        if r.status_code != 200 or '/accounts/login/' in r.url:
            print(f"[-] stealth: profile_page → {r.status_code} (login redirect)", flush=True)
            return {}

        page = r.text
        sjs_scripts = re.findall(r'data-sjs[^>]*>(.*?)</script>', page, re.DOTALL)

        urls = {}
        for script in sjs_scripts:
            if 'polaris_ordered_timeline_connection' not in script:
                continue

            # Try JSON parse first
            try:
                data = json.loads(script)
            except Exception:
                # Regex fallback: extract display_uri + code + username
                node_pattern = re.compile(
                    r'"display_uri"\s*:\s*"([^"]+)"[^}]*?"media_type"\s*:\s*(\d+)[^}]*?"username"\s*:\s*"([^"]+)"',
                    re.DOTALL,
                )
                for m in node_pattern.finditer(script):
                    uri, media_type, owner = m.group(1), int(m.group(2)), m.group(3)
                    if owner != username:
                        continue
                    cleaned = _clean_url(uri)
                    if cleaned:
                        key = f"pp_{len(urls)}_{_secrets.token_hex(3)}"
                        urls[key] = cleaned
                continue

            # Navigate JSON to find edges
            def _find_edges(obj):
                results = []
                if isinstance(obj, dict):
                    if 'edges' in obj and isinstance(obj['edges'], list):
                        results.extend(obj['edges'])
                    for v in obj.values():
                        results.extend(_find_edges(v))
                elif isinstance(obj, list):
                    for item in obj:
                        results.extend(_find_edges(item))
                return results

            edges = _find_edges(data)
            for edge in edges:
                if not isinstance(edge, dict):
                    continue
                node = edge.get('node', edge)
                if not isinstance(node, dict):
                    continue
                owner = node.get('user', {}).get('username', '') if isinstance(node.get('user'), dict) else ''
                if owner != username:
                    continue
                uri = node.get('display_uri', '')
                code = node.get('code', '') or node.get('pk', '')
                if uri:
                    cleaned = _clean_url(uri)
                    if cleaned:
                        key = code if code else f"pp_{len(urls)}_{_secrets.token_hex(3)}"
                        urls[key] = cleaned

            if urls:
                break

        if len(urls) > max_posts:
            urls = dict(list(urls.items())[:max_posts])

        print(f"[✓] stealth: profile_page → {len(urls)} image URLs", flush=True)
        return urls

    except Exception as e:
        print(f"[-] stealth: profile_page error: {e}", flush=True)
        return {}


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
#  Strategy 5 — instaloader/instaloader approach
#  Iterates ALL posts via Profile.get_posts() lazy iterator.
#  Gets the most posts (no hard limit). Best for extracting every
#  single post from a profile.
# ═══════════════════════════════════════════════════════════════════════

def _strategy_instaloader(username, max_posts):
    """Use instaloader to iterate through ALL posts of a profile."""
    try:
        import instaloader
    except ImportError:
        print("[-] stealth: instaloader — not installed, skipping", flush=True)
        return {}

    try:
        L = instaloader.Instaloader(
            download_videos=False,
            download_video_thumbnails=False,
            download_comments=False,
            save_metadata=False,
            post_metadata_txt_pattern='',
            quiet=True,
        )
        # Fail fast on rate limits instead of retrying for 10+ minutes
        L.context.max_connection_attempts = 1
        L.context.request_timeout = 10

        # Optional: load session if IG_SESSION_USER is set
        ig_user = os.environ.get('IG_SESSION_USER', '')
        if ig_user:
            session_file = os.environ.get('IG_SESSION_FILE', '/tmp/ig_session.json')
            try:
                if os.path.exists(session_file):
                    L.load_session_from_file(ig_user, session_file)
                    print("[*] stealth: instaloader session loaded", flush=True)
                else:
                    L.login(ig_user, os.environ.get('IG_SESSION_PASS', ''))
                    L.save_session_to_file(session_file)
                    print("[*] stealth: instaloader logged in", flush=True)
            except Exception as e:
                print(f"[-] stealth: instaloader session failed: {e}, continuing anonymous", flush=True)

        # Get profile
        try:
            profile = instaloader.Profile.from_username(L.context, username)
        except Exception as e:
            print(f"[-] stealth: instaloader — profile not found: {e}", flush=True)
            return {}

        total_posts = profile.mediacount
        print(f"[*] stealth: instaloader — {total_posts} total posts on profile", flush=True)

        urls = {}
        count = 0
        for post in profile.get_posts():
            if count >= max_posts:
                break
            count += 1

            # Get the highest resolution URL
            try:
                # post.url is the display URL (highest res for images)
                url = post.url
                if url:
                    shortcode = post.shortcode or f"stealth_{count}"
                    urls[shortcode] = url
            except Exception:
                pass

            # Handle carousel (multiple images)
            try:
                if post.mediacount > 1:
                    for i, sidecar in enumerate(post.get_sidecar_posts()):
                        try:
                            child_url = sidecar.url
                            if child_url:
                                idx = f"{post.shortcode}_{i}" if post.shortcode else f"stealth_{len(urls)}"
                                urls[idx] = child_url
                        except Exception:
                            pass
            except Exception:
                pass

            if count % 20 == 0:
                print(f"[*] stealth: instaloader — {count}/{min(max_posts, total_posts)} posts processed", flush=True)

        print(f"[✓] stealth: instaloader → {len(urls)} image URLs (from {count} posts)", flush=True)
        return urls

    except Exception as e:
        print(f"[-] stealth: instaloader error: {e}", flush=True)
        return {}


# ═══════════════════════════════════════════════════════════════════════
#  Strategy 6 — web_profile_info API + GraphQL pagination
#  Uses Instagram's web_profile_info API (same as private_scraper.py)
#  with cursor-based pagination to get ALL posts. This is the most
#  reliable approach for public + private profiles via direct connection.
# ═══════════════════════════════════════════════════════════════════════

def _strategy_web_api(username, proxies, max_posts):
    """Use web_profile_info API + GraphQL pagination (most reliable)."""
    from curl_cffi import requests as cffi_req

    try:
        # Step 1: Get session cookies from home page
        r0 = cffi_req.get(
            'https://www.instagram.com/',
            impersonate='chrome',
            proxies=proxies,
            timeout=15,
        )
        if r0.status_code != 200:
            print(f"[-] stealth: web_api home {r0.status_code}", flush=True)
            return {}
        cookies = r0.cookies
        csrftoken = cookies.get('csrftoken', '')

        # Step 2: Query web profile API
        r = cffi_req.get(
            f'https://www.instagram.com/api/v1/users/web_profile_info/?username={username}',
            impersonate='chrome',
            proxies=proxies,
            headers={
                'x-ig-app-id': IG_APP_ID,
                'x-csrftoken': csrftoken,
                'accept': '*/*',
                'referer': f'https://www.instagram.com/{username}/',
            },
            cookies=cookies,
            timeout=15,
        )
        if r.status_code != 200:
            print(f"[-] stealth: web_api profile_info {r.status_code}", flush=True)
            return {}

        data = r.json()
        user = data.get('data', {}).get('user') or data.get('user')
        if not user:
            print("[-] stealth: web_api — no user data", flush=True)
            return {}

        is_private = user.get('is_private', False)
        followers = user.get('edge_followed_by', {}).get('count', '?')
        print(f"[*] stealth: web_api — {user.get('username')} | private={is_private} | followers={followers}", flush=True)

        timeline = user.get('edge_owner_to_timeline_media', {})
        total_count = timeline.get('count', 0)
        edges = timeline.get('edges', [])
        page_info = timeline.get('page_info', {})

        print(f"[*] stealth: web_api — {total_count} total posts, {len(edges)} in first page", flush=True)

        urls = {}
        urls = _extract_urls_from_edges(edges, urls)
        print(f"[*] stealth: web_api page 1 → {len(urls)} image URLs", flush=True)

        # Step 3: Paginate if more pages exist
        has_next = page_info.get('has_next_page', False)
        end_cursor = page_info.get('end_cursor', '')
        user_id = user.get('id')

        if has_next and end_cursor and user_id:
            urls = _paginate_web_api(username, user_id, end_cursor, cookies, csrftoken, proxies, urls, max_posts)

        if len(urls) > max_posts:
            urls = dict(list(urls.items())[:max_posts])

        print(f"[✓] stealth: web_api → {len(urls)} image URLs", flush=True)
        return urls

    except Exception as e:
        print(f"[-] stealth: web_api error: {e}", flush=True)
        return {}


def _extract_urls_from_edges(edges, urls):
    """Extract image URLs from timeline edges (handles carousels)."""
    for edge in edges:
        node = edge.get('node', {})
        shortcode = node.get('shortcode', '')
        display_url = node.get('display_url', '')
        if display_url and shortcode:
            urls[shortcode] = _clean_url(display_url)
        # Carousel posts (multiple images)
        sidecar = node.get('edge_sidecar_to_children', {})
        if sidecar:
            for se in sidecar.get('edges', []):
                child = se.get('node', {})
                child_url = child.get('display_url', '')
                if child_url:
                    idx = child.get('shortcode', '') or f"{shortcode}_{len(urls)}"
                    urls[idx] = _clean_url(child_url)
    return urls


def _paginate_web_api(username, user_id, end_cursor, cookies, csrftoken, proxies, urls, max_posts):
    """GraphQL pagination to get more posts (same as private_scraper)."""
    from curl_cffi import requests as cffi_req

    page_num = 2
    while len(urls) < max_posts and page_num <= 10:
        time.sleep(0.5)
        try:
            variables = json.dumps({
                'id': user_id,
                'first': 50,
                'after': end_cursor,
            })
            r = cffi_req.get(
                f'https://www.instagram.com/graphql/query/?query_hash=69cba40317214236af40e7efa6978&variables={variables}',
                impersonate='chrome',
                proxies=proxies,
                headers={
                    'x-ig-app-id': IG_APP_ID,
                    'x-csrftoken': csrftoken,
                    'accept': '*/*',
                    'referer': f'https://www.instagram.com/{username}/',
                },
                cookies=cookies,
                timeout=15,
            )
            if r.status_code != 200:
                print(f"[-] stealth: web_api page {page_num} → {r.status_code}", flush=True)
                break

            pdata = r.json()
            media = pdata.get('data', {}).get('user', {}).get(
                'edge_owner_to_timeline_media', {})
            edges = media.get('edges', [])
            page_info = media.get('page_info', {})

            before = len(urls)
            urls = _extract_urls_from_edges(edges, urls)
            added = len(urls) - before
            print(f"[*] stealth: web_api page {page_num} → +{added} URLs ({len(urls)} total)", flush=True)

            if added == 0:
                break

            has_next = page_info.get('has_next_page', False)
            end_cursor = page_info.get('end_cursor', '')
            if not has_next or not end_cursor:
                break
            page_num += 1
        except Exception as e:
            print(f"[-] stealth: web_api page {page_num} error: {e}", flush=True)
            break

    return urls


# ═══════════════════════════════════════════════════════════════════════
#  Strategy 7 — kevmaindev/Instagram-Followers-Scraper_Suite approach
#  Session-based API using IG_SESSION_ID cookie + friendships endpoint.
#  Can access private account data if the session user follows the target.
# ═══════════════════════════════════════════════════════════════════════

def _strategy_session_api(username, proxies, max_posts):
    """Use IG_SESSION_ID cookie to access private account posts via API."""
    session_id = os.environ.get('IG_SESSION_ID', '')
    if not session_id:
        print("[-] stealth: session_api — no IG_SESSION_ID set, skipping", flush=True)
        return {}

    try:
        from curl_cffi import requests as cffi_req

        # Step 1: Get user ID from web_profile_info
        r0 = cffi_req.get(
            f'https://www.instagram.com/api/v1/users/web_profile_info/?username={username}',
            impersonate='chrome',
            proxies=proxies,
            headers={
                'x-ig-app-id': IG_APP_ID,
                'x-requested-with': 'XMLHttpRequest',
                'accept': '*/*',
                'referer': f'https://www.instagram.com/{username}/',
            },
            cookies={'sessionid': session_id},
            timeout=15,
        )
        if r0.status_code != 200:
            print(f"[-] stealth: session_api — web_profile_info {r0.status_code}", flush=True)
            return {}

        data = r0.json()
        user = data.get('data', {}).get('user') or data.get('user')
        if not user:
            print("[-] stealth: session_api — no user data", flush=True)
            return {}

        user_id = user.get('id')
        if not user_id:
            print("[-] stealth: session_api — no user ID", flush=True)
            return {}

        is_private = user.get('is_private', False)
        print(f"[*] stealth: session_api — user_id={user_id}, private={is_private}", flush=True)

        # Step 2: Get user media via API
        urls = {}
        max_id = None
        page_num = 0

        while len(urls) < max_posts and page_num < 10:
            page_num += 1
            api_url = f'https://i.instagram.com/api/v1/feed/user/{user_id}/'
            if max_id:
                api_url += f'?max_id={max_id}'

            r = cffi_req.get(
                api_url,
                impersonate='chrome',
                proxies=proxies,
                headers={
                    'x-ig-app-id': IG_APP_ID,
                    'accept': '*/*',
                    'referer': f'https://www.instagram.com/{username}/',
                },
                cookies={'sessionid': session_id},
                timeout=15,
            )
            if r.status_code != 200:
                print(f"[-] stealth: session_api — feed page {page_num} → {r.status_code}", flush=True)
                break

            try:
                feed = r.json()
            except Exception:
                break

            items = feed.get('items', [])
            if not items:
                break

            before = len(urls)
            for item in items:
                # Image posts
                candidates = item.get('image_versions2', {}).get('candidates', [])
                if candidates:
                    best = max(candidates, key=lambda c: c.get('width', 0))
                    code = item.get('code', '') or item.get('id', '')
                    if best.get('url'):
                        urls[code] = _clean_url(best['url'])
                # Carousel posts
                carousel = item.get('carousel_media', [])
                if carousel:
                    for res in carousel:
                        candidates = res.get('image_versions2', {}).get('candidates', [])
                        if candidates:
                            best = max(candidates, key=lambda c: c.get('width', 0))
                            code = item.get('code', '') or item.get('id', '')
                            idx = f"{code}_{res.get('id', len(urls))}"
                            if best.get('url'):
                                urls[idx] = _clean_url(best['url'])
                # Video thumbnail
                if not candidates and not carousel:
                    video_versions = item.get('video_versions', [])
                    if video_versions:
                        code = item.get('code', '') or item.get('id', '')
                        urls[code] = _clean_url(video_versions[0].get('url', ''))

            added = len(urls) - before
            print(f"[*] stealth: session_api page {page_num} → +{added} ({len(urls)} total)", flush=True)

            if added == 0:
                break

            # Pagination
            next_max_id = feed.get('next_max_id') or feed.get('next_max_id_str')
            if not next_max_id:
                more_available = feed.get('more_available', False)
                if not more_available:
                    break
                break
            max_id = next_max_id
            time.sleep(0.5)

        if len(urls) > max_posts:
            urls = dict(list(urls.items())[:max_posts])

        print(f"[✓] stealth: session_api → {len(urls)} image URLs", flush=True)
        return urls

    except Exception as e:
        print(f"[-] stealth: session_api error: {e}", flush=True)
        return {}


# ═══════════════════════════════════════════════════════════════════════
#  Main entry point — tries ALL strategies, returns the one with MOST posts
# ═══════════════════════════════════════════════════════════════════════

def scrape_stealth_profile(username, max_posts=60):
    """
    Scrape Instagram profile using the stealth multi-strategy engine.
    Runs all curl_cffi strategies IN PARALLEL (ThreadPoolExecutor) for
    maximum speed, then returns the result from whichever scraper found
    the MOST posts. Uses early-exit: if any strategy returns >= 10 posts
    fast, the remaining futures are cancelled.

    Returns dict: {shortcode: image_url, ...}
    """
    from concurrent.futures import ThreadPoolExecutor, as_completed

    username = username.lstrip('@').strip()
    if not username:
        return {}

    print(f"[*] stealth: starting PARALLEL scrape for @{username} (max {max_posts} posts)", flush=True)

    all_results = {}
    proxies_direct = None  # direct connection
    proxies_tor = _get_proxies()

    # ── Build the list of strategy tasks to run in parallel ──
    # Each task is (name, callable) — callable takes no args
    tasks = []

    # Profile page strategy — FASTEST, single HTTP request through Tor
    # Try Tor first (direct usually gets 429), then direct as fallback
    if proxies_tor:
        tasks.append(('profile_page/tor', lambda: _strategy_profile_page(username, proxies_tor, max_posts)))
    tasks.append(('profile_page/direct', lambda: _strategy_profile_page(username, proxies_direct, max_posts)))

    # curl_cffi strategies — try direct first (fast), Tor as fallback
    for proxy_label, proxies in [('direct', proxies_direct), ('tor', proxies_tor)]:
        if proxies is None and proxy_label == 'tor':
            continue
        tag = '' if proxy_label == 'direct' else f'/{proxy_label}'
        tasks.append((f'web_api{tag}', lambda p=proxies: _strategy_web_api(username, p, max_posts)))
        tasks.append((f'obitouka{tag}', lambda p=proxies: _strategy_obitouka(username, p, max_posts)))
        tasks.append((f'arcanecfg{tag}', lambda p=proxies: _strategy_arcanecfg(username, p, max_posts)))
        tasks.append((f'drawrowfly{tag}', lambda p=proxies: _strategy_drawrowfly(username, p, max_posts)))

    # session_api only needs to run once (uses IG_SESSION_ID cookie, not proxy-dependent)
    ig_session_id = os.environ.get('IG_SESSION_ID', '')
    if ig_session_id:
        tasks.append(('session_api', lambda: _strategy_session_api(username, proxies_direct, max_posts)))

    # instagrapi/instaloader — only if credentials are configured
    ig_user = os.environ.get('IG_SESSION_USER', '')
    if ig_user:
        tasks.append(('instagrapi', lambda: _strategy_instagrapi(username, max_posts)))
        tasks.append(('instaloader', lambda: _strategy_instaloader(username, max_posts)))

    print(f"[*] stealth: launching {len(tasks)} strategies in parallel", flush=True)

    # ── Run all strategies concurrently with early exit ──
    # If any strategy returns >= 10 posts, we cancel remaining futures
    # and return immediately — no need to wait for slow strategies.
    EARLY_EXIT_THRESHOLD = 10

    with ThreadPoolExecutor(max_workers=len(tasks)) as executor:
        future_map = {}
        for name, fn in tasks:
            future_map[executor.submit(fn)] = name

        for future in as_completed(future_map):
            name = future_map[future]
            try:
                urls = future.result()
            except Exception as e:
                print(f"[-] stealth: {name} exception: {e}", flush=True)
                urls = {}
            if urls:
                all_results[name] = urls
                print(f"[+] stealth: {name} → {len(urls)} posts (parallel)", flush=True)

                # Early exit: if we have enough posts, cancel remaining futures
                if len(urls) >= EARLY_EXIT_THRESHOLD:
                    print(f"[*] stealth: early exit — {name} returned {len(urls)} posts (>= {EARLY_EXIT_THRESHOLD})", flush=True)
                    for f in future_map:
                        f.cancel()
                    break

    if not all_results:
        print(f"[-] stealth: all strategies failed for @{username}", flush=True)
        return {}

    # ── Return the result from whichever scraper found the MOST posts ──
    best_strategy = max(all_results, key=lambda k: len(all_results[k]))
    best_urls = all_results[best_strategy]

    print(f"[*] stealth: strategy results:", flush=True)
    for name, urls in sorted(all_results.items(), key=lambda x: -len(x[1])):
        print(f"    {name}: {len(urls)} posts", flush=True)
    print(f"[✓] stealth: BEST → {best_strategy} with {len(best_urls)} posts", flush=True)

    return best_urls
