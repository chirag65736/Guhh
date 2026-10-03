"""
Followers Scraper — extracts follower USERNAMES from an Instagram profile.

Strategies (all tried, best result wins):
  0. Playwright headless browser — renders the profile page, opens the
     followers modal, scrolls to load more, extracts usernames from DOM.
     Works for PUBLIC accounts WITHOUT Instagram login.
  1. Web friendships API  — /api/v1/friendships/{user_id}/followers/ with
     IG_SESSION_ID cookie + max_id pagination (fastest, most complete).
  2. instaloader Profile.get_followers() — iterates follower objects,
     each exposing .username. Works for private accounts if logged in.
  3. GraphQL edge_followed_by pagination (requires IG_SESSION_ID).

Usage:
    from followers_scraper import scrape_followers
    usernames = scrape_followers('target_username', max_followers=200)
    # Returns list of username strings: ['user1', 'user2', ...]
"""

import os
import re
import json
import time

IG_APP_ID = '936619743392459'


# ═══════════════════════════════════════════════════════════════════════
#  Strategy 0 — Playwright headless browser (NO login needed for public)
#  Opens the profile page, clicks "followers", scrolls the modal,
#  extracts usernames from the rendered DOM.
# ═══════════════════════════════════════════════════════════════════════

def _strategy_playwright(username, max_followers):
    """Use Playwright headless Chromium to scrape followers via picuki.com.

    Picuki/tikvib is a public Instagram viewer that shows follower lists
    without requiring Instagram login. Playwright (a real browser) handles
    Cloudflare's JS challenge automatically.
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("[-] followers: playwright — not installed, skipping", flush=True)
        return []

    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True, args=[
                '--no-sandbox', '--disable-gpu', '--disable-dev-shm-usage',
                '--disable-blink-features=AutomationControlled',
            ])
            context = browser.new_context(
                user_agent='Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 '
                           '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                viewport={'width': 1280, 'height': 900},
                locale='en-US',
            )
            context.add_init_script('''
                Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                window.chrome = { runtime: {} };
            ''')
            page = context.new_page()

            url = f'https://www.picuki.com/followers/{username}'
            print(f"[*] followers: playwright — loading {url}", flush=True)

            page.goto(url, timeout=30000, wait_until='networkidle')
            page.wait_for_timeout(3000)

            # Handle Cloudflare "Just a moment" challenge
            for _ in range(3):
                title = page.title()
                if 'Just a moment' not in title:
                    break
                print("[*] followers: playwright — Cloudflare challenge, waiting...", flush=True)
                page.wait_for_timeout(8000)

            html = page.content()
            browser.close()

            # Extract usernames from /profile/{username} links
            import re as _re
            raw = _re.findall(r'/profile/([a-zA-Z0-9._]+)', html)
            # Deduplicate, filter out the target and non-user paths
            skip = {username, 'picuki', 'tikvib', 'page', 'about', 'contact_us',
                    'remove', 'privacy', 'terms', 'copyright'}
            usernames = []
            seen = set()
            for u in raw:
                if u not in seen and u not in skip:
                    seen.add(u)
                    usernames.append(u)

            if len(usernames) > max_followers:
                usernames = usernames[:max_followers]

            print(f"[✓] followers: playwright → {len(usernames)} usernames", flush=True)
            return usernames

    except Exception as e:
        print(f"[-] followers: playwright error: {e}", flush=True)
        return []


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


def _get_user_id(username, proxies, session_id=None):
    """Resolve a username to its numeric IG user ID via web_profile_info."""
    from curl_cffi import requests as cffi_req

    cookies = {}
    if session_id:
        cookies['sessionid'] = session_id

    try:
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
            cookies=cookies,
            timeout=15,
        )
        if r.status_code != 200:
            print(f"[-] followers: web_profile_info → {r.status_code}", flush=True)
            return None
        data = r.json()
        user = data.get('data', {}).get('user') or data.get('user')
        if user:
            return user.get('id')
    except Exception as e:
        print(f"[-] followers: get_user_id error: {e}", flush=True)
    return None


# ═══════════════════════════════════════════════════════════════════════
#  Strategy 1 — Web friendships API (IG_SESSION_ID)
#  GET /api/v1/friendships/{user_id}/followers/?max_id=...
#  Each item has a "username" field. Paginate until exhausted.
# ═══════════════════════════════════════════════════════════════════════

def _strategy_friendships_api(username, proxies, max_followers):
    """Use IG_SESSION_ID cookie + friendships endpoint to get follower usernames."""
    session_id = os.environ.get('IG_SESSION_ID', '')
    if not session_id:
        print("[-] followers: friendships_api — no IG_SESSION_ID set, skipping", flush=True)
        return []

    try:
        from curl_cffi import requests as cffi_req

        user_id = _get_user_id(username, proxies, session_id)
        if not user_id:
            print("[-] followers: friendships_api — could not resolve user ID", flush=True)
            return []

        print(f"[*] followers: friendships_api — user_id={user_id}", flush=True)

        usernames = []
        max_id = None
        page = 0

        while len(usernames) < max_followers and page < 50:
            page += 1
            url = f'https://i.instagram.com/api/v1/friendships/{user_id}/followers/'
            if max_id:
                url += f'?max_id={max_id}&count=50'
            else:
                url += '?count=50'

            r = cffi_req.get(
                url,
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
                print(f"[-] followers: friendships_api page {page} → {r.status_code}", flush=True)
                break

            try:
                data = r.json()
            except Exception:
                print(f"[-] followers: friendships_api page {page} — no JSON", flush=True)
                break

            users = data.get('users', [])
            if not users:
                break

            before = len(usernames)
            for u in users:
                uname = u.get('username', '')
                if uname and uname not in usernames:
                    usernames.append(uname)

            added = len(usernames) - before
            print(f"[*] followers: friendships_api page {page} → +{added} ({len(usernames)} total)", flush=True)

            if added == 0:
                break

            max_id = data.get('next_max_id') or data.get('next_max_id_str')
            if not max_id:
                break
            time.sleep(0.5)

        if len(usernames) > max_followers:
            usernames = usernames[:max_followers]

        print(f"[✓] followers: friendships_api → {len(usernames)} usernames", flush=True)
        return usernames

    except Exception as e:
        print(f"[-] followers: friendships_api error: {e}", flush=True)
        return []


# ═══════════════════════════════════════════════════════════════════════
#  Strategy 2 — instaloader Profile.get_followers()
#  Iterates follower objects, each exposing .username.
#  Works for private accounts if logged in (IG_SESSION_USER + IG_SESSION_PASS).
# ═══════════════════════════════════════════════════════════════════════

def _strategy_instaloader(username, max_followers):
    """Use instaloader to get follower usernames (requires login for private)."""
    try:
        import instaloader
    except ImportError:
        print("[-] followers: instaloader — not installed, skipping", flush=True)
        return []

    try:
        L = instaloader.Instaloader(quiet=True)
        L.context.max_connection_attempts = 1
        L.context.request_timeout = 10

        ig_user = os.environ.get('IG_SESSION_USER', '')
        if ig_user:
            session_file = os.environ.get('IG_SESSION_FILE', '/tmp/ig_session.json')
            try:
                if os.path.exists(session_file):
                    L.load_session_from_file(ig_user, session_file)
                    print("[*] followers: instaloader session loaded", flush=True)
                else:
                    L.login(ig_user, os.environ.get('IG_SESSION_PASS', ''))
                    L.save_session_to_file(session_file)
                    print("[*] followers: instaloader logged in", flush=True)
            except Exception as e:
                print(f"[-] followers: instaloader login failed: {e}", flush=True)
                return []
        else:
            print("[-] followers: instaloader — no IG_SESSION_USER set, private followers need login", flush=True)
            return []

        profile = instaloader.Profile.from_username(L.context, username)
        print(f"[*] followers: instaloader — profile found, fetching followers...", flush=True)

        usernames = []
        count = 0
        for follower in profile.get_followers():
            if count >= max_followers:
                break
            uname = follower.username
            if uname and uname not in usernames:
                usernames.append(uname)
            count += 1
            if count % 50 == 0:
                print(f"[*] followers: instaloader — {count} followers fetched", flush=True)

        print(f"[✓] followers: instaloader → {len(usernames)} usernames", flush=True)
        return usernames

    except Exception as e:
        print(f"[-] followers: instaloader error: {e}", flush=True)
        return []


# ═══════════════════════════════════════════════════════════════════════
#  Strategy 3 — GraphQL edge_followed_by pagination
#  Uses the profile page's embedded JSON to get follower nodes via
#  GraphQL cursor pagination. Requires IG_SESSION_ID for private accounts.
# ═══════════════════════════════════════════════════════════════════════

def _strategy_graphql(username, proxies, max_followers):
    """Use GraphQL edge_followed_by pagination to get follower usernames."""
    session_id = os.environ.get('IG_SESSION_ID', '')
    if not session_id:
        print("[-] followers: graphql — no IG_SESSION_ID set, skipping", flush=True)
        return []

    try:
        from curl_cffi import requests as cffi_req

        cookies = {'sessionid': session_id}

        # Get user ID + initial follower edges from profile page
        r0 = cffi_req.get(
            f'https://www.instagram.com/{username}/',
            impersonate='chrome',
            proxies=proxies,
            cookies=cookies,
            timeout=15,
        )
        if r0.status_code != 200:
            print(f"[-] followers: graphql profile page → {r0.status_code}", flush=True)
            return []

        page = r0.text
        csrftoken = r0.cookies.get('csrftoken', '')

        # Extract user ID
        id_match = re.search(r'"id"\s*:\s*"(\d+)"', page)
        if not id_match:
            print("[-] followers: graphql — could not find user ID", flush=True)
            return []
        user_id = id_match.group(1)

        # GraphQL query hash for followers (edge_followed_by)
        FOLLOWERS_HASH = '374e6a3b4d3d3d3d3d3d3d3d3d3d3d3d'  # placeholder

        usernames = []
        end_cursor = None
        page_num = 0

        while len(usernames) < max_followers and page_num < 50:
            page_num += 1
            variables = json.dumps({
                'id': user_id,
                'include_reel': True,
                'first': 50,
                **({'after': end_cursor} if end_cursor else {}),
            })

            r = cffi_req.get(
                f'https://www.instagram.com/graphql/query/?query_hash={FOLLOWERS_HASH}&variables={variables}',
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
                print(f"[-] followers: graphql page {page_num} → {r.status_code}", flush=True)
                break

            try:
                data = r.json()
            except Exception:
                break

            followed_by = (
                data.get('data', {})
                .get('user', {})
                .get('edge_followed_by', {})
            )
            edges = followed_by.get('edges', [])

            if not edges:
                break

            before = len(usernames)
            for edge in edges:
                node = edge.get('node', {})
                uname = node.get('username', '')
                if uname and uname not in usernames:
                    usernames.append(uname)

            added = len(usernames) - before
            print(f"[*] followers: graphql page {page_num} → +{added} ({len(usernames)} total)", flush=True)

            if added == 0:
                break

            page_info = followed_by.get('page_info', {})
            has_next = page_info.get('has_next_page', False)
            end_cursor = page_info.get('end_cursor', '')
            if not has_next or not end_cursor:
                break
            time.sleep(0.5)

        if len(usernames) > max_followers:
            usernames = usernames[:max_followers]

        print(f"[✓] followers: graphql → {len(usernames)} usernames", flush=True)
        return usernames

    except Exception as e:
        print(f"[-] followers: graphql error: {e}", flush=True)
        return []


# ═══════════════════════════════════════════════════════════════════════
#  Main entry point
# ═══════════════════════════════════════════════════════════════════════

def scrape_followers(username, max_followers=200):
    """
    Scrape follower USERNAMES from an Instagram profile.

    For private accounts, IG_SESSION_ID or IG_SESSION_USER + IG_SESSION_PASS
    must be set. Without authentication, Instagram will not reveal the
    follower list.

    Returns list of username strings: ['user1', 'user2', ...]
    Or empty list if all strategies fail.
    """
    username = username.lstrip('@').strip()
    if not username:
        return []

    print(f"[*] followers: starting scrape for @{username} (max {max_followers})", flush=True)

    all_results = {}

    # Strategy 0: Playwright headless browser (works for public accounts without login)
    names = _strategy_playwright(username, max_followers)
    if names:
        all_results['playwright'] = names

    # If Playwright already found enough, return early
    if all_results and max(len(v) for v in all_results.values()) >= 5:
        best = max(all_results, key=lambda k: len(all_results[k]))
        print(f"[✓] followers: playwright got {len(all_results[best])} — skipping API strategies", flush=True)
        return all_results[best]

    # ── Try direct first, then Tor ──
    for proxy_label, proxies in [('direct', None), ('tor', _get_proxies())]:
        if proxies is None and proxy_label == 'tor':
            continue

        print(f"[*] followers: trying {proxy_label} connection", flush=True)

        # Strategy 1: friendships API (fastest)
        names = _strategy_friendships_api(username, proxies, max_followers)
        if names:
            all_results['friendships_api'] = names

        # Strategy 3: GraphQL pagination
        if proxy_label == 'direct':
            names = _strategy_graphql(username, proxies, max_followers)
            if names:
                all_results['graphql'] = names

        if all_results and max(len(v) for v in all_results.values()) >= 5:
            break

    # Strategy 2: instaloader (uses its own connection)
    names = _strategy_instaloader(username, max_followers)
    if names:
        all_results['instaloader'] = names

    if not all_results:
        print(f"[-] followers: all strategies failed for @{username}", flush=True)
        return []

    # Return whichever strategy found the most usernames
    best = max(all_results, key=lambda k: len(all_results[k]))
    best_names = all_results[best]

    print(f"[*] followers: strategy results:", flush=True)
    for name, names in sorted(all_results.items(), key=lambda x: -len(x[1])):
        print(f"    {name}: {len(names)} usernames", flush=True)
    print(f"[✓] followers: BEST → {best} with {len(best_names)} usernames", flush=True)

    return best_names


if __name__ == '__main__':
    import sys
    target = sys.argv[1] if len(sys.argv) > 1 else ''
    if not target:
        print("Usage: python followers_scraper.py <username>")
        sys.exit(1)
    print(f"\n=== Followers Scraper ===")
    print(f"Target: @{target}\n")
    names = scrape_followers(target, max_followers=200)
    if names:
        print(f"\nFound {len(names)} followers:")
        for n in names:
            print(f"  @{n}")
    else:
        print(f"\nNo followers found. Make sure IG_SESSION_ID or IG_SESSION_USER/PASS is set.")
