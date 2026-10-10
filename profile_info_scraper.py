"""
Profile Info Scraper — extracts Instagram private account information
like followers, following, total posts, bio, profile picture, etc.

Separate from the post scrapers. Uses multiple strategies:
  1. Web Profile Info API (curl_cffi Chrome impersonation)
  2. HTML meta tag extraction (og:description)
  3. instaloader Profile (if available)
  4. Session-based API (if IG_SESSION_ID is set)

Usage:
    from profile_info_scraper import scrape_profile_info
    info = scrape_profile_info('username')
    # Returns dict with followers, following, posts, bio, etc.
"""

import os
import re
import json

IG_APP_ID = '936619743392459'


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


def _try_web_profile_info(username, proxies):
    """Strategy 1: Use Instagram web_profile_info API with curl_cffi."""
    from curl_cffi import requests as cffi_req

    try:
        # Get session cookies
        r0 = cffi_req.get(
            'https://www.instagram.com/',
            impersonate='chrome',
            proxies=proxies,
            timeout=15,
        )
        cookies = r0.cookies
        csrftoken = cookies.get('csrftoken', '')

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
            print(f"[-] profile_info: web_profile_info → {r.status_code}", flush=True)
            return None

        data = r.json()
        user = data.get('data', {}).get('user') or data.get('user')
        if not user:
            return None

        return _parse_user_json(user)

    except Exception as e:
        print(f"[-] profile_info: web_profile_info error: {e}", flush=True)
        return None


def _try_html_meta(username, proxies):
    """Strategy 2: Extract profile info from HTML meta tags (og:description)."""
    from curl_cffi import requests as cffi_req

    try:
        r = cffi_req.get(
            f'https://www.instagram.com/{username}/',
            impersonate='chrome',
            proxies=proxies,
            timeout=15,
        )
        if r.status_code != 200:
            print(f"[-] profile_info: HTML meta → {r.status_code}", flush=True)
            return None

        page = r.text

        # Extract from og:description meta tag: "123 Followers, 456 Following, 789 Posts -..."
        desc_match = re.search(
            r'<meta\s+property="og:description"\s+content="([^"]+)"',
            page,
        )
        # Extract from og:title: "Username (@username) • Instagram photos and videos"
        title_match = re.search(
            r'<meta\s+property="og:title"\s+content="([^"]+)"',
            page,
        )
        # Extract profile image
        img_match = re.search(
            r'<meta\s+property="og:image"\s+content="([^"]+)"',
            page,
        )

        info = {}
        if desc_match:
            desc = desc_match.group(1)
            # Parse "12 Followers, 34 Following, 56 Posts - ..."
            followers_match = re.search(r'([\d,.]+)\s+Followers', desc)
            following_match = re.search(r'([\d,.]+)\s+Following', desc)
            posts_match = re.search(r'([\d,.]+)\s+Posts', desc)

            if followers_match:
                info['followers'] = int(followers_match.group(1).replace(',', ''))
            if following_match:
                info['following'] = int(following_match.group(1).replace(',', ''))
            if posts_match:
                info['posts'] = int(posts_match.group(1).replace(',', ''))
            info['bio'] = desc.split(' - ', 1)[-1] if ' - ' in desc else ''

        if title_match:
            title = title_match.group(1)
            # "Full Name (@username) • Instagram photos and videos"
            name_match = re.match(r'^(.+?)\s*\(@(.+?)\)', title)
            if name_match:
                info['full_name'] = name_match.group(1).strip()
                info['username'] = name_match.group(2).strip()

        if img_match:
            info['profile_pic_url'] = img_match.group(1)

        # Try to extract is_private from embedded JSON
        if '"is_private":true' in page:
            info['is_private'] = True
        elif '"is_private":false' in page:
            info['is_private'] = False

        # Try to extract is_verified
        if '"is_verified":true' in page:
            info['is_verified'] = True
        elif '"is_verified":false' in page:
            info['is_verified'] = False

        if not info:
            print("[-] profile_info: HTML meta — no data found", flush=True)
            return None

        info.setdefault('username', username)
        print(f"[✓] profile_info: HTML meta → followers={info.get('followers', '?')}", flush=True)
        return info

    except Exception as e:
        print(f"[-] profile_info: HTML meta error: {e}", flush=True)
        return None


def _try_instaloader(username):
    """Strategy 3: Use instaloader to get profile info."""
    try:
        import instaloader
    except ImportError:
        return None

    try:
        # Do not sleep for many minutes on Instagram 429 responses.
        L = instaloader.Instaloader(
            quiet=True, max_connection_attempts=1, request_timeout=10,
        )

        # Optional: load session
        ig_user = os.environ.get('IG_SESSION_USER', '')
        if ig_user:
            session_file = os.environ.get('IG_SESSION_FILE', '/tmp/ig_session.json')
            try:
                if os.path.exists(session_file):
                    L.load_session_from_file(ig_user, session_file)
                else:
                    L.login(ig_user, os.environ.get('IG_SESSION_PASS', ''))
                    L.save_session_to_file(session_file)
            except Exception:
                pass

        profile = instaloader.Profile.from_username(L.context, username)

        info = {
            'username': profile.username,
            'full_name': profile.full_name,
            'followers': profile.followers,
            'following': profile.followees,
            'posts': profile.mediacount,
            'bio': profile.biography,
            'profile_pic_url': profile.profile_pic_url,
            'is_private': profile.is_private,
            'is_verified': profile.is_verified,
            'external_url': profile.external_url if hasattr(profile, 'external_url') else '',
            'category': profile.business_category_name if hasattr(profile, 'business_category_name') else '',
        }

        print(f"[✓] profile_info: instaloader → followers={info['followers']}", flush=True)
        return info

    except Exception as e:
        print(f"[-] profile_info: instaloader error: {e}", flush=True)
        return None


def _try_session_api(username, proxies):
    """Strategy 4: Use IG_SESSION_ID cookie to get profile info."""
    session_id = os.environ.get('IG_SESSION_ID', '')
    if not session_id:
        return None

    try:
        from curl_cffi import requests as cffi_req

        r = cffi_req.get(
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
        if r.status_code != 200:
            return None

        data = r.json()
        user = data.get('data', {}).get('user') or data.get('user')
        if not user:
            return None

        info = _parse_user_json(user)
        print(f"[✓] profile_info: session_api → followers={info.get('followers', '?')}", flush=True)
        return info

    except Exception as e:
        print(f"[-] profile_info: session_api error: {e}", flush=True)
        return None


def _parse_user_json(user):
    """Parse user JSON from web_profile_info API into a clean dict."""
    def _get(obj, *keys, default=None):
        for key in keys:
            if isinstance(obj, dict) and key in obj:
                val = obj[key]
                if isinstance(val, dict):
                    obj = val
                else:
                    return val
            else:
                return default
        return obj

    return {
        'username': user.get('username', ''),
        'full_name': user.get('full_name', ''),
        'followers': _get(user, 'edge_followed_by', 'count', default=0),
        'following': _get(user, 'edge_follow', 'count', default=0),
        'posts': _get(user, 'edge_owner_to_timeline_media', 'count', default=0),
        'bio': user.get('biography', ''),
        'profile_pic_url': user.get('profile_pic_url_hd', user.get('profile_pic_url', '')),
        'is_private': user.get('is_private', False),
        'is_verified': user.get('is_verified', False),
        'external_url': user.get('external_url', ''),
        'category': user.get('category_name', user.get('business_category_name', '')),
    }


def scrape_profile_info(username):
    """
    Scrape Instagram profile info (followers, following, posts, bio, etc.)
    Tries multiple strategies, returns the first success.

    Returns dict with keys:
        username, full_name, followers, following, posts, bio,
        profile_pic_url, is_private, is_verified, external_url, category
    Or None if all strategies fail.
    """
    username = username.lstrip('@').strip()
    if not username:
        return None

    print(f"[*] profile_info: scraping info for @{username}", flush=True)

    # Public metadata is often available even when the API requires login.
    # Try both connections before Instaloader hits the same blocked API again.
    proxies = _get_proxies()
    connections = [None] + ([proxies] if proxies else [])
    for connection in connections:
        info = _try_html_meta(username, connection)
        if info:
            return info

    for connection in connections:
        info = _try_session_api(username, connection)
        if info:
            return info

        info = _try_web_profile_info(username, connection)
        if info:
            return info

    # Last resort only: avoid delaying a working HTML fallback with API retries.
    info = _try_instaloader(username)
    if info:
        return info

    print(f"[-] profile_info: all strategies failed for @{username}", flush=True)
    return None


if __name__ == '__main__':
    import sys
    target = sys.argv[1] if len(sys.argv) > 1 else 'official_paul_7814'
    print(f"\n=== Profile Info Scraper ===")
    print(f"Target: @{target}\n")
    info = scrape_profile_info(target)
    if info:
        print(f"\nResults:")
        for k, v in info.items():
            print(f"  {k}: {v}")
    else:
        print(f"\nFailed to get profile info for @{target}")
