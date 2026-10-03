"""
Private Instagram Scraper — separate from the main scraper.
Uses curl_cffi (Chrome TLS impersonation) + pagination to find MORE posts
than the standard scraper (which only gets the first page ~12 posts).

This scraper fetches multiple pages using cursor-based pagination,
extracting up to `max_posts` images from the profile timeline.

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
    """Return proxy dict: custom proxy > Tor > none."""
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


def scrape_private_profile(username, max_posts=60):
    """
    Scrape Instagram profile with PAGINATION to find more posts.
    Uses curl_cffi for TLS impersonation + cursor-based pagination.
    Returns dict of {post_id: image_url}.
    """
    from curl_cffi import requests as cffi_req

    proxies = _get_proxies()
    print(f"[*] private_scraper: @{username} | max={max_posts} | proxy={'Tor' if proxies else 'direct'}", flush=True)

    # Step 1: Get session cookies
    try:
        r = cffi_req.get(
            'https://www.instagram.com/',
            impersonate='chrome',
            proxies=proxies,
            timeout=15,
        )
        if r.status_code != 200:
            print(f"[-] private_scraper: home page returned {r.status_code}", flush=True)
            return {}
        cookies = r.cookies
        csrftoken = cookies.get('csrftoken', '')
        print(f"[✓] private_scraper: got session cookies", flush=True)
    except Exception as e:
        print(f"[-] private_scraper: cookie fetch failed: {e}", flush=True)
        return {}

    # Step 2: Get user ID + first page of posts via web profile API
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
            print(f"[-] private_scraper: profile API returned {r.status_code}", flush=True)
            return {}

        data = r.json()
        user = data.get('user', {})
        if not user:
            print("[-] private_scraper: no user data", flush=True)
            return {}

        user_id = user.get('id')
        timeline = user.get('edge_owner_to_timeline_media', {})
        total_count = timeline.get('count', 0)
        edges = timeline.get('edges', [])
        page_info = timeline.get('page_info', {})

        print(f"[✓] private_scraper: {user.get('username')} | "
              f"private={user.get('is_private')} | "
              f"total_posts={total_count} | first_page={len(edges)}", flush=True)

        urls = {}
        urls = _extract_urls_from_edges(edges, urls)
        print(f"[*] private_scraper: page 1 → {len(urls)} URLs so far", flush=True)

        # Step 3: Paginate through remaining posts using cursor
        page_num = 2
        has_next = page_info.get('has_next_page', False)
        end_cursor = page_info.get('end_cursor', '')

        while has_next and len(urls) < max_posts and page_num <= 10:
            time.sleep(0.5)  # small delay between pages
            try:
                query_hash = '69cba40317214236af40e7efa6978'  # timeline query
                variables = json.dumps({
                    'id': user_id,
                    'first': 50,
                    'after': end_cursor,
                })
                r = cffi_req.get(
                    f'https://www.instagram.com/graphql/query/?query_hash={query_hash}&variables={variables}',
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

                before_count = len(urls)
                urls = _extract_urls_from_edges(edges, urls)
                added = len(urls) - before_count
                print(f"[*] private_scraper: page {page_num} → +{added} URLs ({len(urls)} total)", flush=True)

                if added == 0:
                    break

                has_next = page_info.get('has_next_page', False)
                end_cursor = page_info.get('end_cursor', '')
                page_num += 1
            except Exception as e:
                print(f"[-] private_scraper: page {page_num} error: {e}", flush=True)
                break

        # Trim to max_posts
        if len(urls) > max_posts:
            urls = dict(list(urls.items())[:max_posts])

        print(f"[✓] private_scraper: DONE — {len(urls)} total image URLs extracted", flush=True)
        return urls

    except Exception as e:
        print(f"[-] private_scraper: API request failed: {e}", flush=True)
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
