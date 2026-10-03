"""
Alternative Instagram scraper using curl_cffi (browser TLS impersonation) + Tor.
This is a separate, independent scraper — different technique from igscrapper.py.

curl_cffi impersonates Chrome's exact TLS fingerprint (JA3/JA4), which helps
bypass bot detection that blocks standard requests/curl. Combined with Tor,
it provides a different approach from the instagrapi-based main scraper.

Usage:
    from alt_scraper import scrape_profile
    image_urls = scrape_profile('username')
    # Returns dict: {post_id: highest_res_url, ...}
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
    """Decode Instagram CDN URL."""
    try:
        from urllib.parse import unquote
        return unquote(url)
    except Exception:
        return url


def scrape_profile(username, amount=20):
    """
    Scrape Instagram profile using curl_cffi + Tor.
    Returns dict of {post_id: image_url} or empty dict on failure.
    """
    from curl_cffi import requests as cffi_req

    proxies = _get_proxies()
    print(f"[*] alt_scraper: @{username} | proxy={'Tor' if proxies else 'direct'}")

    # Step 1: Get session cookies from Instagram home page
    try:
        r = cffi_req.get(
            'https://www.instagram.com/',
            impersonate='chrome',
            proxies=proxies,
            timeout=20,
        )
        if r.status_code != 200:
            print(f"[-] alt_scraper: home page returned {r.status_code}")
            return {}
        cookies = r.cookies
        csrftoken = cookies.get('csrftoken', '')
        print(f"[✓] alt_scraper: got cookies ({len(cookies)} keys)")
    except Exception as e:
        print(f"[-] alt_scraper: cookie fetch failed: {e}")
        return {}

    time.sleep(1)

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
            timeout=20,
        )
        if r.status_code != 200:
            print(f"[-] alt_scraper: API returned {r.status_code}")
            return {}

        data = r.json()
        user = data.get('user', {})
        if not user:
            print("[-] alt_scraper: no user data in response")
            return {}

        print(f"[✓] alt_scraper: {user.get('username')} | "
              f"private={user.get('is_private')} | "
              f"followers={user.get('edge_followed_by', {}).get('count', '?')}")

        # Extract image URLs from timeline
        timeline = user.get('edge_owner_to_timeline_media', {})
        edges = timeline.get('edges', [])
        print(f"[*] alt_scraper: {timeline.get('count', 0)} posts, {len(edges)} edges")

        urls = {}
        for edge in edges:
            node = edge.get('node', {})
            shortcode = node.get('shortcode', '')
            display_url = node.get('display_url', '')
            if display_url and shortcode:
                urls[shortcode] = _decode_url(display_url)
            # Handle carousel posts (multiple images)
            sidecar = node.get('edge_sidecar_to_children', {})
            if sidecar:
                for se in sidecar.get('edges', []):
                    child = se.get('node', {})
                    child_url = child.get('display_url', '')
                    if child_url:
                        idx = child.get('shortcode', '') or f"{shortcode}_{len(urls)}"
                        urls[idx] = _decode_url(child_url)

        print(f"[✓] alt_scraper: extracted {len(urls)} image URLs")
        return urls

    except Exception as e:
        print(f"[-] alt_scraper: API request failed: {e}")
        return {}


def scrape_profile_html(username):
    """
    Alternative: scrape profile page HTML directly with curl_cffi.
    Extracts image URLs from og:meta tags and embedded JSON.
    Returns dict of {post_id: image_url} or empty dict on failure.
    """
    from curl_cffi import requests as cffi_req

    proxies = _get_proxies()
    print(f"[*] alt_scraper (HTML): @{username} | proxy={'Tor' if proxies else 'direct'}")

    try:
        r = cffi_req.get(
            f'https://www.instagram.com/{username}/?__d=dis',
            impersonate='chrome',
            proxies=proxies,
            timeout=20,
        )
        if r.status_code != 200:
            print(f"[-] alt_scraper (HTML): {r.status_code}")
            return {}

        html = r.text
        urls = {}

        # Extract from og:image meta tag (profile picture)
        og = re.search(r'property="og:image"[^>]*content="([^"]+)"', html)
        if og:
            urls['profile_pic'] = _decode_url(og.group(1))

        # Extract from embedded JSON script tags
        scripts = re.findall(
            r'<script type="application/json"[^>]*>(.*?)</script>',
            html, re.DOTALL
        )
        for script in scripts:
            if 'image_versions2' in script or 'display_url' in script:
                try:
                    data = json.loads(script)
                    # Recursive search for display_url
                    def find_urls(obj):
                        if isinstance(obj, dict):
                            if 'display_url' in obj and 'shortcode' in obj:
                                urls[obj['shortcode']] = _decode_url(obj['display_url'])
                            for v in obj.values():
                                find_urls(v)
                        elif isinstance(obj, list):
                            for item in obj:
                                find_urls(item)
                    find_urls(data)
                except json.JSONDecodeError:
                    continue

        print(f"[✓] alt_scraper (HTML): extracted {len(urls)} URLs")
        return urls

    except Exception as e:
        print(f"[-] alt_scraper (HTML): {e}")
        return {}


if __name__ == '__main__':
    import sys
    target = sys.argv[1] if len(sys.argv) > 1 else 'official_paul_7814'
    print(f"\n=== Alternative Scraper Test ===")
    print(f"Target: @{target}\n")

    # Method 1: API approach
    print("--- Method 1: API + curl_cffi ---")
    urls1 = scrape_profile(target)
    if urls1:
        for pid, url in list(urls1.items())[:5]:
            print(f"  {pid}: {url[:100]}")
    else:
        print("  (no results)")

    # Method 2: HTML approach
    print("\n--- Method 2: HTML + curl_cffi ---")
    urls2 = scrape_profile_html(target)
    if urls2:
        for pid, url in list(urls2.items())[:5]:
            print(f"  {pid}: {url[:100]}")
    else:
        print("  (no results)")
