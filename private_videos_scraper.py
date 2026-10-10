"""
Private Videos Scraper — extracts VIDEO URLs from an Instagram
profile (including PRIVATE accounts) without login.

Technique (based on InstagramPrivSniffer + GraphQL post query):
  1. Get post shortcodes from the web_profile_info API (works for
     private accounts without login).
  2. For each shortcode, use the GraphQL query with doc_id
     27128499623469141 to fetch full media data.
  3. Extract video URLs from `video_versions` — these are the actual
     playable/downloadable MP4 URLs at the highest resolution available.
  4. Also extract video thumbnails and captions for display.

This scraper is focused on VIDEOS only (Reels, video posts, video
carousel items). For images, use private_posts_scraper.py.

Usage:
    from private_videos_scraper import scrape_private_videos
    videos = scrape_private_videos('username', max_posts=30)
    # Returns list of dicts: {url, thumbnail, caption, shortcode, is_reel}
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
            print(f"[-] private_videos: web_profile_info → {r.status_code}", flush=True)
            return [], session, csrftoken

        data = r.json()
        user = data.get('data', {}).get('user') or data.get('user')
        if not user:
            print("[-] private_videos: no user data in response", flush=True)
            return [], session, csrftoken

        media = user.get('edge_owner_to_timeline_media', {})
        edges = media.get('edges', [])
        total = media.get('count', 0)
        is_private = user.get('is_private', False)

        # Collect shortcodes + whether each post is a video
        shortcodes = []
        for e in edges:
            node = e.get('node', {})
            sc = node.get('shortcode', '')
            is_video = node.get('is_video', False)
            if sc:
                shortcodes.append((sc, is_video))

        # Prioritize video posts first, but still check all (carousel may contain videos)
        video_first = [sc for sc, is_vid in shortcodes if is_vid]
        other = [sc for sc, is_vid in shortcodes if not is_vid]
        ordered = video_first + other

        print(f"[*] private_videos: {'private' if is_private else 'public'} account, "
              f"{total} total posts, {len(video_first)} known videos, {len(other)} other posts", flush=True)

        return ordered, session, csrftoken

    except Exception as e:
        print(f"[-] private_videos: get_shortcodes error: {e}", flush=True)
        return [], None, ''


def _get_shortcodes_from_profile_page(username, proxies):
    """
    Get post shortcodes by scraping the profile page HTML.

    Instagram's logged-out profile page embeds Relay/GraphQL data in
    <script data-sjs> tags. The 'polaris_ordered_timeline_connection'
    field contains the first page of posts with codes and media types.

    This approach works through Tor even when the web_profile_info API
    returns 401, because the profile page itself is served to logged-out
    users (unlike the API which requires authentication).

    Returns: (shortcodes_list, session, csrftoken)
    shortcodes_list is ordered: video posts first, then others.
    """
    from curl_cffi import requests as cffi_req

    try:
        session = cffi_req.Session()
        # Get cookies from home page
        session.get('https://www.instagram.com/', impersonate='chrome',
                     proxies=proxies, timeout=15)
        csrftoken = session.cookies.get('csrftoken', '')

        # Fetch profile page
        r = session.get(
            f'https://www.instagram.com/{username}/',
            impersonate='chrome',
            proxies=proxies,
            timeout=15,
        )
        if r.status_code != 200:
            print(f"[-] private_videos: profile page → {r.status_code}", flush=True)
            return [], session, csrftoken

        # Check for login redirect
        if '/accounts/login/' in r.url:
            print("[-] private_videos: profile page redirected to login", flush=True)
            return [], session, csrftoken

        page = r.text

        # Extract data-sjs scripts and find polaris_ordered_timeline_connection
        sjs_scripts = re.findall(r'data-sjs[^>]*>(.*?)</script>', page, re.DOTALL)

        video_codes = []
        other_codes = []

        for script in sjs_scripts:
            if 'polaris_ordered_timeline_connection' not in script:
                continue

            # Try to parse as JSON
            try:
                data = json.loads(script)
            except Exception:
                # Fall back to regex extraction of codes and media types
                # Pattern: "code":"XXXXX" ... "media_type":N ... "username":"YYY"
                # Extract all nodes with code + media_type + username
                node_pattern = re.compile(
                    r'"code"\s*:\s*"([^"]{5,})"[^}]*?"media_type"\s*:\s*(\d+)[^}]*?"username"\s*:\s*"([^"]+)"',
                    re.DOTALL,
                )
                for m in node_pattern.finditer(script):
                    code, media_type, owner = m.group(1), int(m.group(2)), m.group(3)
                    if owner != username:
                        continue
                    if media_type == 2:
                        video_codes.append(code)
                    else:
                        other_codes.append(code)
                continue

            # Navigate the JSON structure to find edges
            def _find_edges(obj):
                """Recursively find 'edges' lists in the JSON."""
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
                code = node.get('code', '')
                media_type = node.get('media_type', 0)
                user_info = node.get('user', {})
                owner = user_info.get('username', '') if isinstance(user_info, dict) else ''

                if not code or owner != username:
                    continue

                if media_type == 2:
                    video_codes.append(code)
                else:
                    other_codes.append(code)

        # Deduplicate while preserving order
        seen = set()
        ordered = []
        for code in video_codes + other_codes:
            if code not in seen:
                seen.add(code)
                ordered.append(code)

        if ordered:
            print(f"[*] private_videos: profile page → {len(video_codes)} video posts, "
                  f"{len(other_codes)} other posts (via embedded Relay data)", flush=True)
        else:
            print("[-] private_videos: profile page — no posts found in Relay data", flush=True)

        return ordered, session, csrftoken

    except Exception as e:
        print(f"[-] private_videos: profile page error: {e}", flush=True)
        return [], None, ''


def _fetch_post_video_graphql(shortcode, session, csrftoken, proxies):
    """Fetch video URLs for a single post via GraphQL query.

    Returns list of dicts: {url, thumbnail, width, height}
    (Multiple entries if carousel contains multiple videos.)
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

        videos = []

        def _extract_video_urls(item):
            """Extract all video URLs from a media item."""
            result = []
            # Video versions — pick the highest resolution
            vv = item.get('video_versions', [])
            if vv:
                # Sort by width descending, pick the best
                best = max(vv, key=lambda v: v.get('width', 0))
                thumb = item.get('image_versions2', {}).get('candidates', [{}])
                thumb_url = thumb[0].get('url', '') if thumb else ''
                result.append({
                    'url': _clean_url(best.get('url', '')),
                    'thumbnail': _clean_url(thumb_url),
                    'width': best.get('width', 0),
                    'height': best.get('height', 0),
                })
            return result

        item = items[0]

        # Carousel post — check all items for videos
        carousel = item.get('carousel_media', [])
        if carousel:
            for ci in carousel:
                videos.extend(_extract_video_urls(ci))
        else:
            # Single post
            videos.extend(_extract_video_urls(item))

        return [v for v in videos if v.get('url')]

    except Exception as e:
        print(f"  [-] private_videos: GraphQL error for {shortcode}: {e}", flush=True)
        return []


def _fetch_post_video_ogvideo(shortcode, proxies):
    """Fallback: fetch post page HTML and extract og:video meta tag."""
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
        videos = []

        # og:video tag
        ogv = re.search(
            r'<meta[^>]+property=["\']og:video["\'][^>]+content=["\']([^"\']+)',
            page,
        )
        if ogv:
            videos.append({
                'url': _clean_url(ogv.group(1)),
                'thumbnail': '',
                'width': 0,
                'height': 0,
            })

        # Also try og:video:url and og:video:secure_url
        for prop in ['og:video:url', 'og:video:secure_url']:
            m = re.search(
                r'<meta[^>]+property=["\']' + prop + r'["\'][^>]+content=["\']([^"\']+)',
                page,
            )
            if m:
                videos.append({
                    'url': _clean_url(m.group(1)),
                    'thumbnail': '',
                    'width': 0,
                    'height': 0,
                })

        # Deduplicate
        seen = set()
        unique = []
        for v in videos:
            if v['url'] not in seen:
                seen.add(v['url'])
                unique.append(v)

        return unique

    except Exception as e:
        print(f"  [-] private_videos: og:video fallback error: {e}", flush=True)
        return []


def scrape_private_videos(username, max_posts=30, shortcodes=None):
    """
    Scrape VIDEO URLs from an Instagram profile (including private accounts).

    Uses web_profile_info API to get post shortcodes, then GraphQL query
    to fetch video data for each post. Extracts actual playable MP4 URLs
    at the highest resolution available.

    If `shortcodes` is provided (list of shortcode strings), skips the
    web_profile_info API call and uses those shortcodes directly.

    Returns list of dicts: {url, thumbnail, shortcode}
    """
    username = username.lstrip('@').strip()
    if not username:
        return []

    print(f"[*] private_videos: starting video scrape for @{username} (max {max_posts} posts)", flush=True)

    session = None
    csrftoken = ''
    proxies = None

    if shortcodes:
        # Reuse pre-fetched shortcodes (avoids duplicate API call)
        print(f"[*] private_videos: using {len(shortcodes)} pre-fetched shortcodes", flush=True)
        from curl_cffi import requests as cffi_req
        try:
            proxies = _get_proxies()
            session = cffi_req.Session()
            session.get('https://www.instagram.com/', impersonate='chrome',
                         proxies=proxies, timeout=15)
            csrftoken = session.cookies.get('csrftoken', '')
        except Exception:
            session = None
    else:
        # Strategy 1: Profile page HTML (works through Tor, most reliable)
        for proxy_label, proxies in [('tor', _get_proxies()), ('direct', None)]:
            if proxies is None and proxy_label == 'tor':
                continue

            print(f"[*] private_videos: trying {proxy_label} profile page for shortcodes", flush=True)
            shortcodes, session, csrftoken = _get_shortcodes_from_profile_page(username, proxies)
            if shortcodes:
                break

            # Strategy 2: web_profile_info API (fallback)
            print(f"[*] private_videos: trying {proxy_label} web_profile_info for shortcodes", flush=True)
            shortcodes, session, csrftoken = _get_shortcodes(username, proxies)
            if shortcodes:
                break

            if proxy_label == 'tor':
                print("[*] private_videos: Tor failed, trying direct...", flush=True)
                time.sleep(0.5)

    if not shortcodes:
        print(f"[-] private_videos: could not get shortcodes for @{username}", flush=True)
        return []

    shortcodes = shortcodes[:max_posts]
    print(f"[*] private_videos: fetching video data for {len(shortcodes)} posts...", flush=True)

    all_videos = []

    for i, sc in enumerate(shortcodes):
        print(f"  [{i+1}/{len(shortcodes)}] {sc}:", end=' ', flush=True)

        videos = []
        if session and csrftoken:
            videos = _fetch_post_video_graphql(sc, session, csrftoken, proxies)

        if videos:
            for v in videos:
                v['shortcode'] = sc
            all_videos.extend(videos)
            print(f"{len(videos)} video(s)" + (" (carousel)" if len(videos) > 1 else ""))
        else:
            print("no GraphQL video, trying og:video...", end=' ', flush=True)
            videos = _fetch_post_video_ogvideo(sc, proxies)
            if videos:
                for v in videos:
                    v['shortcode'] = sc
                all_videos.extend(videos)
                print(f"{len(videos)} video(s) (og:video)")
            else:
                print("no video")

        time.sleep(0.2)

    # Deduplicate by URL
    seen = set()
    unique_videos = []
    for v in all_videos:
        if v.get('url') and v['url'] not in seen:
            seen.add(v['url'])
            unique_videos.append(v)

    print(f"[✓] private_videos: {len(unique_videos)} unique video URLs from {len(shortcodes)} posts", flush=True)
    return unique_videos


if __name__ == '__main__':
    import sys
    target = sys.argv[1] if len(sys.argv) > 1 else ''
    if not target:
        print("Usage: python private_videos_scraper.py <username>")
        sys.exit(1)
    print(f"\n=== Private Videos Scraper ===")
    print(f"Target: @{target}\n")
    videos = scrape_private_videos(target, max_posts=30)
    if videos:
        print(f"\nFound {len(videos)} videos:")
        for v in videos:
            print(f"  -> {v['url'][:100]}...")
            if v.get('thumbnail'):
                print(f"     thumb: {v['thumbnail'][:80]}...")
    else:
        print(f"\nNo videos found for @{target}")
