"""
Private Posts Scraper — extracts ALL post images from an Instagram
profile (including PRIVATE accounts) without login.

Technique (based on InstagramPrivSniffer + GraphQL post query):
  1. Get post shortcodes from the web_profile_info API (works for
     private accounts without login, intermittent on datacenter IPs).
  2. For each shortcode, use the GraphQL query with doc_id
     27128499623469141 to fetch full media data:
     - All carousel images (not just the first)
     - Highest resolution image_versions2 candidates
     - Video URLs
  3. Fallback: fetch the post page HTML and extract og:image meta tag.

This scraper gets ALL images from ALL posts, including multi-image
carousel posts — something the existing stealth_scraper cannot do.

Usage:
    from private_posts_scraper import scrape_private_posts
    urls = scrape_private_posts('username', max_posts=20)
    # Returns list of image URL strings
"""

import os
import re
import json
import time
import html as html_mod

IG_APP_ID = '936619743392459'

# GraphQL doc_id for fetching individual post media (InstagramPrivSniffer technique)
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
    """Unescape URL from JSON encoding."""
    if not url:
        return ''
    return (
        html_mod.unescape(url)
        .replace('\\/', '/')
        .replace('\\u0026', '&')
        .replace('\\u003D', '=')
        .replace('\\u002F', '/')
    )


def _get_shortcodes(username, proxies):
    """Get post shortcodes from web_profile_info API."""
    from curl_cffi import requests as cffi_req

    cookies = {}
    session_id = os.environ.get('IG_SESSION_ID', '')
    if session_id:
        cookies['sessionid'] = session_id

    try:
        session = cffi_req.Session()
        session.get('https://www.instagram.com/', impersonate='chrome',
                     proxies=proxies, timeout=15)
        cookies.update(session.cookies)
        csrftoken = cookies.get('csrftoken', '')

        r = session.get(
            f'https://www.instagram.com/api/v1/users/web_profile_info/?username={username}',
            impersonate='chrome',
            proxies=proxies,
            headers={
                'x-ig-app-id': IG_APP_ID,
                'x-csrftoken': csrftoken,
                'x-requested-with': 'XMLHttpRequest',
                'accept': '*/*',
                'referer': f'https://www.instagram.com/{username}/',
            },
            cookies=cookies,
            timeout=15,
        )
        if r.status_code != 200:
            print(f"[-] private_posts: web_profile_info → {r.status_code}", flush=True)
            return [], session, csrftoken

        data = r.json()
        user = data.get('data', {}).get('user') or data.get('user')
        if not user:
            print("[-] private_posts: no user data in response", flush=True)
            return [], session, csrftoken

        media = user.get('edge_owner_to_timeline_media', {})
        edges = media.get('edges', [])
        total = media.get('count', 0)
        is_private = user.get('is_private', False)

        shortcodes = []
        for e in edges:
            sc = e.get('node', {}).get('shortcode', '')
            if sc:
                shortcodes.append(sc)

        print(f"[*] private_posts: {'private' if is_private else 'public'} account, "
              f"{total} total posts, {len(shortcodes)} shortcodes retrieved", flush=True)

        return shortcodes, session, csrftoken

    except Exception as e:
        print(f"[-] private_posts: get_shortcodes error: {e}", flush=True)
        return [], None, ''


def _fetch_post_media_graphql(shortcode, session, csrftoken, proxies):
    """Fetch full media data for a single post via GraphQL query.

    Returns list of image/video URL strings (all carousel items + highest res).
    """
    try:
        variables = {
            'shortcode': shortcode,
            '__relay_internal__pv__PolarisAIGMMediaWebLabelEnabledrelayprovider': False,
        }
        resp = session.post(
            'https://www.instagram.com/graphql/query',
            data={
                'variables': json.dumps(variables, separators=(',', ':')),
                'doc_id': POST_MEDIA_DOC_ID,
                'server_timestamps': 'true',
            },
            headers={
                'X-CSRFToken': csrftoken,
                'Referer': f'https://www.instagram.com/p/{shortcode}/',
            },
            impersonate='chrome',
            proxies=proxies,
            timeout=15,
        )

        if resp.status_code != 200:
            return []

        data = resp.json()
        items = (
            data.get('data', {})
            .get('xdt_api__v1__media__shortcode__web_info', {})
            .get('items', [])
        )

        if not items:
            return []

        item = items[0]
        urls = []

        # Carousel post — get all images
        carousel = item.get('carousel_media', [])
        if carousel:
            for ci in carousel:
                iv2 = ci.get('image_versions2', {})
                candidates = iv2.get('candidates', [])
                if candidates:
                    urls.append(_clean_url(candidates[-1].get('url', '')))
                vv = ci.get('video_versions', [])
                if vv:
                    urls.append(_clean_url(vv[0].get('url', '')))
        else:
            # Single image/video post
            iv2 = item.get('image_versions2', {})
            candidates = iv2.get('candidates', [])
            if candidates:
                urls.append(_clean_url(candidates[-1].get('url', '')))
            vv = item.get('video_versions', [])
            if vv:
                urls.append(_clean_url(vv[0].get('url', '')))

        return [u for u in urls if u]

    except Exception as e:
        print(f"  [-] private_posts: GraphQL error for {shortcode}: {e}", flush=True)
        return []


def _fetch_post_media_ogimage(shortcode, proxies):
    """Fallback: fetch post page HTML and extract og:image meta tag."""
    from curl_cffi import requests as cffi_req

    try:
        url = f'https://www.instagram.com/p/{shortcode}/'
        r = cffi_req.get(
            url,
            headers={'User-Agent': 'Mozilla/5.0'},
            impersonate='chrome',
            proxies=proxies,
            timeout=15,
        )

        if r.status_code != 200:
            return []

        page = r.text
        urls = []

        og = re.search(
            r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)',
            page,
        )
        if og:
            urls.append(_clean_url(og.group(1)))

        ogv = re.search(
            r'<meta[^>]+property=["\']og:video["\'][^>]+content=["\']([^"\']+)',
            page,
        )
        if ogv:
            urls.append(_clean_url(ogv.group(1)))

        return urls

    except Exception as e:
        print(f"  [-] private_posts: og:image fallback error: {e}", flush=True)
        return []


def scrape_private_posts(username, max_posts=20, shortcodes=None):
    """
    Scrape ALL post images from an Instagram profile (including private accounts).

    Uses web_profile_info API to get post shortcodes, then GraphQL query
    to fetch full media data for each post (all carousel images, highest res,
    videos). Falls back to og:image meta tag if GraphQL fails.

    If `shortcodes` is provided (list of shortcode strings), skips the
    web_profile_info API call and uses those shortcodes directly. This avoids
    duplicate API calls when shortcodes are already available from another
    scraper (e.g. post_engagement_scraper).

    Returns list of image URL strings.
    """
    username = username.lstrip('@').strip()
    if not username:
        return []

    print(f"[*] private_posts: starting scrape for @{username} (max {max_posts} posts)", flush=True)

    session = None
    csrftoken = ''

    if shortcodes:
        # Reuse pre-fetched shortcodes (avoids duplicate API call)
        print(f"[*] private_posts: using {len(shortcodes)} pre-fetched shortcodes", flush=True)
        # Still need a session for GraphQL queries
        from curl_cffi import requests as cffi_req
        try:
            session = cffi_req.Session()
            session.get('https://www.instagram.com/', impersonate='chrome', timeout=15)
            csrftoken = session.cookies.get('csrftoken', '')
        except Exception:
            session = None
        proxies = None  # Use direct for GraphQL (works reliably)
    else:
        # Fetch shortcodes from web_profile_info API
        for proxy_label, proxies in [('direct', None), ('tor', _get_proxies())]:
            if proxies is None and proxy_label == 'tor':
                continue

            print(f"[*] private_posts: trying {proxy_label} for shortcodes", flush=True)
            shortcodes, session, csrftoken = _get_shortcodes(username, proxies)

            if shortcodes:
                break

            if proxy_label == 'direct':
                print("[*] private_posts: direct failed, trying Tor...", flush=True)
                time.sleep(1)

    if not shortcodes:
        print(f"[-] private_posts: could not get shortcodes for @{username}", flush=True)
        return []

    shortcodes = shortcodes[:max_posts]
    print(f"[*] private_posts: fetching media for {len(shortcodes)} posts...", flush=True)

    all_urls = []

    for i, sc in enumerate(shortcodes):
        print(f"  [{i+1}/{len(shortcodes)}] {sc}:", end=' ', flush=True)

        urls = []
        if session and csrftoken:
            urls = _fetch_post_media_graphql(sc, session, csrftoken, proxies)

        if urls:
            all_urls.extend(urls)
            print(f"{len(urls)} images" + (" (carousel)" if len(urls) > 1 else ""))
        else:
            print("GraphQL failed, trying og:image...", end=' ', flush=True)
            urls = _fetch_post_media_ogimage(sc, proxies)
            if urls:
                all_urls.extend(urls)
                print(f"{len(urls)} images (og:image)")
            else:
                print("failed")

        time.sleep(0.3)

    seen = set()
    unique_urls = []
    for u in all_urls:
        if u not in seen:
            seen.add(u)
            unique_urls.append(u)

    print(f"[✓] private_posts: {len(unique_urls)} unique image URLs from {len(shortcodes)} posts", flush=True)
    return unique_urls


if __name__ == '__main__':
    import sys
    target = sys.argv[1] if len(sys.argv) > 1 else ''
    if not target:
        print("Usage: python private_posts_scraper.py <username>")
        sys.exit(1)
    print(f"\n=== Private Posts Scraper ===")
    print(f"Target: @{target}\n")
    urls = scrape_private_posts(target, max_posts=20)
    if urls:
        print(f"\nFound {len(urls)} image URLs:")
        for u in urls:
            print(f"  -> {u[:100]}...")
    else:
        print(f"\nNo images found for @{target}")
