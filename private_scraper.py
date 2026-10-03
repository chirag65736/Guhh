"""
Private Instagram Scraper — separate from the main scraper.
Uses curl_cffi (Chrome TLS impersonation) to fetch posts via the
web profile API. Tries direct connection first (faster, works better),
falls back to Tor. Handles carousel posts and cursor-based pagination
to find more images than the standard scraper.

Usage:
    from private_scraper import scrape_private_profile
    image_urls = scrape_private_profile('username', max_posts=60)
    # Returns dict: {post_id: image_url, ...}
"""

import os
import json
import time
import re


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


def _decode_url(url):
    try:
        from urllib.parse import unquote
        return unquote(url)
    except Exception:
        return url


def _extract_urls_from_edges(edges, urls):
    """Extract image URLs from timeline edges (handles carousels)."""
    for edge in edges:
        node = edge.get('node', {})
        shortcode = node.get('shortcode', '')
        display_url = node.get('display_url', '')
        if display_url and shortcode:
            urls[shortcode] = _decode_url(display_url)
        # Carousel posts (multiple images)
        sidecar = node.get('edge_sidecar_to_children', {})
        if sidecar:
            for se in sidecar.get('edges', []):
                child = se.get('node', {})
                child_url = child.get('display_url', '')
                if child_url:
                    idx = child.get('shortcode', '') or f"{shortcode}_{len(urls)}"
                    urls[idx] = _decode_url(child_url)
    return urls


def _try_api(username, proxies, max_posts):
    """Try the web_profile_info API with curl_cffi."""
    from curl_cffi import requests as cffi_req

    # Step 1: Get session cookies from home page
    try:
        r0 = cffi_req.get(
            'https://www.instagram.com/',
            impersonate='chrome',
            proxies=proxies,
            timeout=15,
        )
        if r0.status_code != 200:
            print(f"[-] private_scraper: home page {r0.status_code}", flush=True)
            return {}
        cookies = r0.cookies
        csrftoken = cookies.get('csrftoken', '')
    except Exception as e:
        print(f"[-] private_scraper: cookie fetch failed: {e}", flush=True)
        return {}

    # Step 2: Query web profile API
    try:
        r = cffi_req.get(
            f'https://www.instagram.com/api/v1/users/web_profile_info/?username={username}',
            impersonate='chrome',
            proxies=proxies,
            headers={
                'x-ig-app-id': '936619743392459',
                'x-csrftoken': csrftoken,
                'accept': '*/*',
                'referer': f'https://www.instagram.com/{username}/',
            },
            cookies=cookies,
            timeout=15,
        )
        if r.status_code != 200:
            print(f"[-] private_scraper: API returned {r.status_code}", flush=True)
            return {}

        data = r.json()
        # Response can be {"data": {"user": {...}}} or {"user": {...}}
        user = data.get('data', {}).get('user') or data.get('user')
        if not user:
            print("[-] private_scraper: no user data in response", flush=True)
            return {}

        print(f"[✓] private_scraper: {user.get('username')} | "
              f"private={user.get('is_private')} | "
              f"followers={user.get('edge_followed_by', {}).get('count', '?')}", flush=True)

        timeline = user.get('edge_owner_to_timeline_media', {})
        total_count = timeline.get('count', 0)
        edges = timeline.get('edges', [])
        page_info = timeline.get('page_info', {})

        print(f"[*] private_scraper: {total_count} total posts, {len(edges)} in first page", flush=True)

        urls = {}
        urls = _extract_urls_from_edges(edges, urls)
        print(f"[*] private_scraper: page 1 → {len(urls)} image URLs", flush=True)

        # Try pagination if more pages exist
        has_next = page_info.get('has_next_page', False)
        end_cursor = page_info.get('end_cursor', '')
        user_id = user.get('id')

        if has_next and end_cursor and user_id:
            urls = _paginate(username, user_id, end_cursor, cookies, csrftoken, proxies, urls, max_posts)

        if len(urls) > max_posts:
            urls = dict(list(urls.items())[:max_posts])

        return urls

    except Exception as e:
        print(f"[-] private_scraper: API request failed: {e}", flush=True)
        return {}


def _paginate(username, user_id, end_cursor, cookies, csrftoken, proxies, urls, max_posts):
    """Try GraphQL pagination to get more posts."""
    from curl_cffi import requests as cffi_req

    page_num = 2
    while len(urls) < max_posts and page_num <= 8:
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
                    'x-ig-app-id': '936619743392459',
                    'x-csrftoken': csrftoken,
                    'accept': '*/*',
                    'referer': f'https://www.instagram.com/{username}/',
                },
                cookies=cookies,
                timeout=15,
            )
            if r.status_code != 200:
                print(f"[-] private_scraper: page {page_num} returned {r.status_code}", flush=True)
                break

            pdata = r.json()
            media = pdata.get('data', {}).get('user', {}).get(
                'edge_owner_to_timeline_media', {})
            edges = media.get('edges', [])
            page_info = media.get('page_info', {})

            before = len(urls)
            urls = _extract_urls_from_edges(edges, urls)
            added = len(urls) - before
            print(f"[*] private_scraper: page {page_num} → +{added} URLs ({len(urls)} total)", flush=True)

            if added == 0:
                break

            has_next = page_info.get('has_next_page', False)
            end_cursor = page_info.get('end_cursor', '')
            if not has_next or not end_cursor:
                break
            page_num += 1
        except Exception as e:
            print(f"[-] private_scraper: page {page_num} error: {e}", flush=True)
            break

    return urls


def _try_html_fallback(username, proxies):
    """Fallback: fetch profile HTML and extract from embedded JSON."""
    from curl_cffi import requests as cffi_req
    from igscrapper import extract_timeline_data, extract_highest_resolution_urls

    try:
        r = cffi_req.get(
            f'https://www.instagram.com/{username}/',
            impersonate='chrome',
            proxies=proxies,
            timeout=15,
        )
        if r.status_code != 200 or not r.text:
            return {}

        td = extract_timeline_data(r.text)
        if td:
            urls = extract_highest_resolution_urls(td)
            if urls:
                print(f"[✓] private_scraper: HTML fallback → {len(urls)} URLs", flush=True)
                return urls
    except Exception as e:
        print(f"[-] private_scraper: HTML fallback failed: {e}", flush=True)
    return {}


def scrape_private_profile(username, max_posts=60):
    """
    Scrape Instagram profile using the private scraper engine.
    Tries direct connection first (faster), falls back to Tor.
    Returns dict of {post_id: image_url}.
    """
    print(f"[*] private_scraper: @{username} | max={max_posts}", flush=True)

    # Strategy 1: Direct connection (no proxy) — fastest, often works
    print(f"[*] private_scraper: trying direct (no proxy)...", flush=True)
    urls = _try_api(username, None, max_posts)
    if urls:
        print(f"[✓] private_scraper: DONE (direct) — {len(urls)} image URLs", flush=True)
        return urls

    # Strategy 2: Tor proxy
    proxies = _get_proxies()
    if proxies:
        proxy_str = proxies.get('https', '')
        print(f"[*] private_scraper: trying via proxy ({proxy_str})...", flush=True)
        urls = _try_api(username, proxies, max_posts)
        if urls:
            print(f"[✓] private_scraper: DONE (proxy) — {len(urls)} image URLs", flush=True)
            return urls

    # Strategy 3: HTML fallback (direct)
    print(f"[*] private_scraper: trying HTML fallback...", flush=True)
    urls = _try_html_fallback(username, None)
    if urls:
        print(f"[✓] private_scraper: DONE (HTML) — {len(urls)} image URLs", flush=True)
        return urls

    # Strategy 4: HTML fallback (Tor)
    if proxies:
        urls = _try_html_fallback(username, proxies)
        if urls:
            print(f"[✓] private_scraper: DONE (HTML+proxy) — {len(urls)} image URLs", flush=True)
            return urls

    print(f"[-] private_scraper: all strategies failed", flush=True)
    return {}


if __name__ == '__main__':
    import sys
    target = sys.argv[1] if len(sys.argv) > 1 else 'official_paul_7814'
    max_p = int(sys.argv[2]) if len(sys.argv) > 2 else 60
    print(f"\n=== Private Scraper (Deep Scan) ===")
    print(f"Target: @{target} | Max posts: {max_p}\n")
    urls = scrape_private_profile(target, max_posts=max_p)
    print(f"\nResults: {len(urls)} posts")
    for pid, url in list(urls.items())[:10]:
        print(f"  {pid}: {url[:80]}...")
