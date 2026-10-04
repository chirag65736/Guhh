"""
Post Engagement Scraper — extracts per-post engagement data from an
Instagram profile: like count, comment count, caption, timestamp, and
(optionally) actual comment text + liker usernames via Playwright.

Uses the web_profile_info API (no login needed, works for public AND
private accounts) to get the post list with engagement counts, then
optionally loads each post page with Playwright to extract comment text
and liker usernames.

Usage:
    from post_engagement_scraper import scrape_post_engagement
    posts = scrape_post_engagement('username', max_posts=12)
    # Returns list of dicts:
    #   { shortcode, caption, like_count, comment_count, timestamp,
    #     display_url, is_video, comments: [{username, text}],
    #     likers: [username, ...] }
"""

import os
import re
import json
import time
from datetime import datetime

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


def _fetch_profile_data(username, proxies):
    """Fetch the raw user JSON from web_profile_info API."""
    from curl_cffi import requests as cffi_req

    cookies = {}
    session_id = os.environ.get('IG_SESSION_ID', '')
    if session_id:
        cookies['sessionid'] = session_id

    try:
        # Get session cookies first
        r0 = cffi_req.get(
            'https://www.instagram.com/',
            impersonate='chrome',
            proxies=proxies,
            timeout=15,
        )
        cookies.update(r0.cookies)
        csrftoken = cookies.get('csrftoken', '')

        r = cffi_req.get(
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
            print(f"[-] post_engagement: web_profile_info → {r.status_code}", flush=True)
            return None

        data = r.json()
        user = data.get('data', {}).get('user') or data.get('user')
        if not user:
            print("[-] post_engagement: no user data in response", flush=True)
            return None

        return user

    except Exception as e:
        print(f"[-] post_engagement: API error: {e}", flush=True)
        return None


def _parse_post_node(node):
    """Parse a single timeline media node into a clean engagement dict."""
    shortcode = node.get('shortcode', '')
    is_video = node.get('is_video', False)

    # Like count
    likes = node.get('edge_media_preview_like', {})
    like_count = likes.get('count', 0) if isinstance(likes, dict) else 0

    # Comment count
    comments_obj = node.get('edge_media_to_comment', {})
    comment_count = comments_obj.get('count', 0) if isinstance(comments_obj, dict) else 0

    # Caption
    caption = ''
    caption_obj = node.get('edge_media_to_caption', {})
    if isinstance(caption_obj, dict):
        edges = caption_obj.get('edges', [])
        if edges:
            caption = edges[0].get('node', {}).get('text', '')

    # Display URL
    display_url = node.get('display_url', '') or node.get('thumbnail_src', '')

    # Timestamp
    ts = node.get('taken_at_timestamp', 0)
    timestamp_str = ''
    if ts:
        try:
            timestamp_str = datetime.utcfromtimestamp(ts).strftime('%Y-%m-%d %H:%M')
        except Exception:
            timestamp_str = str(ts)

    # Accessibility caption (alt text)
    accessibility = node.get('accessibility_caption', '')

    return {
        'shortcode': shortcode,
        'caption': caption,
        'like_count': like_count,
        'comment_count': comment_count,
        'timestamp': timestamp_str,
        'display_url': display_url,
        'is_video': is_video,
        'comments': [],
        'likers': [],
    }


def _enrich_with_playwright(posts, username, max_posts_to_enrich=8):
    """Load each post page with Playwright to extract comment text and likers.

    Only enriches a limited number of posts to keep scan time reasonable.
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("[-] post_engagement: playwright not installed, skipping enrichment", flush=True)
        return

    _NON_USERNAMES = {
        'p', 'reel', 'reels', 'explore', 'accounts', 'www', 'static', 'i',
        'api', 'graphql', 'instagram', 'about', 'privacy', 'terms', 'blog',
        'rsrc.php', 'v', 'popular', 'direct', 'stories', 'highlights',
        'channel', 'tv', 'live', 'shop', 'threads', 'meta',
    }

    to_enrich = posts[:max_posts_to_enrich]

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

            for i, post in enumerate(to_enrich):
                sc = post['shortcode']
                if not sc:
                    continue

                page = context.new_page()
                url = f'https://www.instagram.com/p/{sc}/'
                print(f"[*] post_engagement: enriching post {i+1}/{len(to_enrich)}: {sc}", flush=True)

                try:
                    page.goto(url, timeout=20000, wait_until='domcontentloaded')
                    page.wait_for_timeout(3000)

                    final_url = page.url
                    if 'login' in final_url or 'accounts/login' in final_url:
                        print(f"  [-] redirected to login, skipping", flush=True)
                        page.close()
                        continue

                    html = page.content()

                    # Extract comments from embedded JSON
                    # Look for edge_media_to_parent_comment or edge_media_to_comment
                    comments = []
                    comment_patterns = [
                        # Standard comment format in embedded JSON
                        r'"text"\s*:\s*"((?:[^"\\]|\\.)*)"[^}]*?"owner"\s*:\s*\{[^}]*?"username"\s*:\s*"([a-zA-Z0-9._]+)"',
                        r'"owner"\s*:\s*\{[^}]*?"username"\s*:\s*"([a-zA-Z0-9._]+)"[^}]*\}[^}]*?"text"\s*:\s*"((?:[^"\\]|\\.)*)"',
                    ]
                    for pattern in comment_patterns:
                        matches = re.findall(pattern, html)
                        for m in matches:
                            if len(m) == 2:
                                # Determine which group is text vs username
                                if pattern.startswith('"text"'):
                                    text, uname = m
                                else:
                                    uname, text = m
                                if uname and uname not in _NON_USERNAMES and uname != username:
                                    # Decode unicode escapes
                                    try:
                                        text = text.encode().decode('unicode_escape')
                                    except Exception:
                                        pass
                                    comments.append({'username': uname, 'text': text})

                    # Deduplicate comments
                    seen = set()
                    unique_comments = []
                    for c in comments:
                        key = (c['username'], c['text'][:50])
                        if key not in seen:
                            seen.add(key)
                            unique_comments.append(c)
                    post['comments'] = unique_comments[:20]  # Limit to 20 comments per post

                    # Extract likers from embedded JSON (usernames in the page)
                    all_names = set(re.findall(r'"username"\s*:\s*"([a-zA-Z0-9._]+)"', html))
                    all_names.update(re.findall(r'instagram\.com/([a-zA-Z0-9._]+)/', html))
                    all_names -= _NON_USERNAMES
                    all_names.discard(username)
                    post['likers'] = sorted(all_names)[:30]  # Limit to 30 likers

                    print(f"  [+] {len(post['comments'])} comments, {len(post['likers'])} likers", flush=True)

                except Exception as e:
                    print(f"  [-] error enriching post: {e}", flush=True)

                page.close()

            browser.close()

    except Exception as e:
        print(f"[-] post_engagement: playwright enrichment error: {e}", flush=True)


def scrape_post_engagement(username, max_posts=12, enrich_comments=True):
    """
    Scrape per-post engagement data from an Instagram profile.

    Returns list of dicts, each with:
        shortcode, caption, like_count, comment_count, timestamp,
        display_url, is_video, comments (list of {username, text}),
        likers (list of username strings)

    Returns empty list if all strategies fail.
    """
    username = username.lstrip('@').strip()
    if not username:
        return []

    print(f"[*] post_engagement: starting scrape for @{username} (max {max_posts} posts)", flush=True)

    # Try direct first, then Tor
    user_data = None
    for proxy_label, proxies in [('direct', None), ('tor', _get_proxies())]:
        if proxies is None and proxy_label == 'tor':
            continue

        print(f"[*] post_engagement: trying {proxy_label} connection", flush=True)
        user_data = _fetch_profile_data(username, proxies)
        if user_data:
            break

    if not user_data:
        print(f"[-] post_engagement: could not fetch profile data for @{username}", flush=True)
        return []

    # Extract posts from timeline media
    media = user_data.get('edge_owner_to_timeline_media', {})
    edges = media.get('edges', [])

    if not edges:
        print(f"[-] post_engagement: no posts found in profile data", flush=True)
        return []

    total_posts = media.get('count', len(edges))
    print(f"[*] post_engagement: found {total_posts} total posts, parsing first {min(len(edges), max_posts)}", flush=True)

    posts = []
    for e in edges[:max_posts]:
        node = e.get('node', {})
        post = _parse_post_node(node)
        if post['shortcode']:
            posts.append(post)

    print(f"[✓] post_engagement: parsed {len(posts)} posts with engagement data", flush=True)

    # Enrich with comment text and likers via Playwright
    if enrich_comments and posts:
        print(f"[*] post_engagement: enriching with comment text + likers via Playwright...", flush=True)
        _enrich_with_playwright(posts, username, max_posts_to_enrich=min(8, len(posts)))

    # Print summary
    for p in posts:
        cmt = f", {len(p['comments'])} comment-texts" if p['comments'] else ''
        lik = f", {len(p['likers'])} likers" if p['likers'] else ''
        print(f"    {p['shortcode']}: {p['like_count']} likes, {p['comment_count']} comments{cmt}{lik}", flush=True)

    return posts


if __name__ == '__main__':
    import sys
    target = sys.argv[1] if len(sys.argv) > 1 else ''
    if not target:
        print("Usage: python post_engagement_scraper.py <username>")
        sys.exit(1)
    print(f"\n=== Post Engagement Scraper ===")
    print(f"Target: @{target}\n")
    posts = scrape_post_engagement(target, max_posts=12)
    if posts:
        print(f"\nFound {len(posts)} posts with engagement data:\n")
        for p in posts:
            print(f"  Post {p['shortcode']} ({p['timestamp']})")
            print(f"    Likes: {p['like_count']}  Comments: {p['comment_count']}")
            print(f"    Caption: {p['caption'][:80]}...")
            if p['comments']:
                print(f"    Comment texts:")
                for c in p['comments'][:5]:
                    print(f"      @{c['username']}: {c['text'][:60]}")
            if p['likers']:
                print(f"    Likers: {', '.join(p['likers'][:10])}")
            print()
    else:
        print(f"\nNo posts found for @{target}")
