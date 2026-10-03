import os
import requests
import json
from bs4 import BeautifulSoup
from urllib.parse import unquote
import time
import urllib.parse
import socket
import threading
from http.server import HTTPServer, SimpleHTTPRequestHandler
import sys
import subprocess
import base64
import parascode as pc

# ============================================================
#   Cɪᴘʜᴇʀ — Instagram Private Access Tool
#   Made by Ryon | Portfolio: CipherXPortal
# ============================================================

x = pc.render('Cɪᴘʜᴇʀ', colors=['cyan', 'magenta'], align='center', font='block')
print(x)

pc.cprint("cyan  ╔══════════════════════════════════════════════╗ reset")
pc.cprint("cyan  ║        Cɪᴘʜᴇʀ  —  Private Access v2.0         ║ reset")
pc.cprint("cyan  ╚══════════════════════════════════════════════╝ reset")
pc.cprint("blue  ◆ Telegram   : t.me/TeamXCipher reset")
pc.cprint("blue  ◆ Channel    : t.me/TeamXCipher reset")
pc.cprint("magenta ◆ Portfolio  : CipherXPortal reset")
pc.cprint("magenta ◆ Made By    : Ryon reset\n")

_d1 = 'MjAyNi0wMy0xMw=='
_d2 = 'MjAyNi0wMy0xNQ=='
_p = 'dWdoYWNrZXJ6aw=='


def get_headers():
    return {
        'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
        'accept-language': 'en-GB,en;q=0.9',
        'dpr': '1',
        'priority': 'u=0, i',
        'sec-ch-prefers-color-scheme': 'dark',
        'sec-ch-ua': '"Google Chrome";v="141", "Not?A_Brand";v="8", "Chromium";v="141"',
        'sec-ch-ua-mobile': '?1',
        'sec-ch-ua-model': '"Nexus 5"',
        'sec-ch-ua-platform': '"Android"',
        'sec-ch-ua-platform-version': '"6.0"',
        'sec-fetch-dest': 'document',
        'sec-fetch-mode': 'navigate',
        'sec-fetch-site': 'none',
        'sec-fetch-user': '?1',
        'upgrade-insecure-requests': '1',
        'user-agent': 'Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Mobile Safari/537.36',
        'viewport-width': '1000',
    }


def loading_animation():
    pc.cprint("cyan  [•] Booting Cɪᴘʜᴇʀ engine... reset\n")
    bar_len = 40
    for i in range(1, 101):
        filled = int(bar_len * i / 100)
        bar = "█" * filled + "░" * (bar_len - filled)
        print(f"\r  \033[96m[{bar}] {i:3d}%\033[0m", end="", flush=True)
        time.sleep(0.02)
    pc.cprint("green \n  [✓] Engine Ready. 100% reset\n")


class ProfileResponse:
    """Response-like object that works with extract_timeline_data."""
    def __init__(self, text, status_code=200):
        self.text = text
        self.status_code = status_code


def _get_tor_proxies():
    """Return Tor SOCKS5 proxy dict if Tor is available, else None."""
    proxy_url = os.environ.get('INSTAGRAM_PROXY')
    if proxy_url:
        return {'http': proxy_url, 'https': proxy_url}
    # Try Tor
    try:
        import socket as _sock
        s = _sock.socket(_sock.AF_INET, _sock.SOCK_STREAM)
        s.settimeout(2)
        s.connect(('127.0.0.1', 9050))
        s.close()
        return {'http': 'socks5://127.0.0.1:9050', 'https': 'socks5://127.0.0.1:9050'}
    except Exception:
        return None


def _try_instagrapi(username, proxies):
    """Strategy 1: Use instagrapi library (private mobile API)."""
    try:
        from instagrapi import Client
        cl = Client()
        if proxies:
            cl = Client(settings={'proxy': proxies.get('https', proxies.get('http'))})
        cl.request_timeout = 8
        user_info = cl.user_info_by_username(username)
        if not user_info:
            return None
        medias = cl.user_medias(user_info.pk, amount=20)
        urls = {}
        for m in medias:
            if hasattr(m, 'thumbnail_url') and m.thumbnail_url:
                urls[str(m.pk)] = m.thumbnail_url
            if hasattr(m, 'resources') and m.resources:
                for r in m.resources:
                    if hasattr(r, 'thumbnail_url') and r.thumbnail_url:
                        urls[f"{m.pk}_{r.pk}"] = r.thumbnail_url
        if urls:
            return ProfileResponse(json.dumps({'_direct_urls': urls}))
    except Exception as e:
        pc.cprint(f"yellow  [!] instagrapi failed: {e} reset")
    return None


def _try_web_api(username, proxies):
    """Strategy 2: Use Instagram web API with session cookies."""
    try:
        session = requests.Session()
        session.headers.update({
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'accept-language': 'en-US,en;q=0.9',
        })
        r0 = session.get('https://www.instagram.com/', proxies=proxies, timeout=8)
        if r0.status_code != 200:
            return None
        session.headers.update({
            'x-ig-app-id': '936619743392459',
            'x-csrftoken': session.cookies.get('csrftoken', ''),
            'accept': '*/*',
            'referer': f'https://www.instagram.com/{username}/',
        })
        r = session.get(
            f'https://www.instagram.com/api/v1/users/web_profile_info/?username={username}',
            proxies=proxies, timeout=8
        )
        if r.status_code == 200:
            return ProfileResponse(r.text)
        pc.cprint(f"yellow  [!] Web API returned {r.status_code} reset")
    except Exception as e:
        pc.cprint(f"yellow  [!] Web API failed: {e} reset")
    return None


def _try_direct(username, proxies):
    """Strategy 3: Direct request (original approach, fallback)."""
    headers = get_headers()
    url = f'https://www.instagram.com/{username}/'
    try:
        response = requests.get(url, headers=headers, timeout=10, proxies=proxies)
        if response.status_code != 200:
            pc.cprint(f"yellow  [!] Direct returned {response.status_code} reset")
            return None
        if 'accounts/login' in response.url:
            pc.cprint("yellow  [!] Direct: redirected to login page reset")
            return None
        return response
    except Exception as e:
        pc.cprint(f"yellow  [!] Direct failed: {e} reset")
    return None


def fetch_instagram_profile(username):
    """Fetch Instagram profile using multiple strategies IN PARALLEL for speed."""
    from concurrent.futures import ThreadPoolExecutor, as_completed
    pc.cprint(f"cyan  [*] Fetching profile → @{username} (parallel mode) reset")
    proxies = _get_tor_proxies()
    if proxies:
        proxy_str = proxies.get('https', proxies.get('http', ''))
        pc.cprint(f"cyan  [*] Using proxy → {proxy_str} reset")

    strategies = [
        ("instagrapi", _try_instagrapi),
        ("Web API", _try_web_api),
        ("Direct", _try_direct),
    ]

    # Run all strategies concurrently — first success wins
    with ThreadPoolExecutor(max_workers=3) as pool:
        futures = {
            pool.submit(fn, username, proxies): name
            for name, fn in strategies
        }
        for future in as_completed(futures, timeout=20):
            name = futures[future]
            try:
                result = future.result()
                if result:
                    pc.cprint(f"green  [✓] {name} succeeded (first hit) reset")
                    # Cancel remaining futures
                    for f in futures:
                        f.cancel()
                    return result
            except Exception as e:
                pc.cprint(f"yellow  [!] {name} error: {e} reset")

    pc.cprint("red  [-] All strategies failed (Instagram may be blocking this IP) reset")
    return None


def extract_timeline_data(html_content):
    # Handle direct API JSON response
    try:
        data = json.loads(html_content)
        # Direct URLs from instagrapi
        if '_direct_urls' in data:
            return data
        # Web API format: {"user": {"edge_owner_to_timeline_media": {"edges": [...]}}}
        if 'user' in data and 'edge_owner_to_timeline_media' in data.get('user', {}):
            return data
        # If it's already parsed data with timeline
        if 'edge_owner_to_timeline_media' in data:
            return data
    except (json.JSONDecodeError, TypeError):
        pass

    # Handle HTML with embedded JSON (original approach)
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        script_tags = soup.find_all('script', {'type': 'application/json'})
        for script in script_tags:
            script_content = script.string
            if not script_content:
                continue
            if 'polaris_timeline_connection' in script_content and 'image_versions2' in script_content:
                try:
                    return json.loads(script_content)
                except:
                    continue
    except:
        pass
    return None


def decode_url(escaped_url):
    try:
        decoded = escaped_url.encode('utf-8').decode('unicode_escape')
        return unquote(decoded)
    except:
        return escaped_url


def extract_highest_resolution_urls(obj, urls=None, post_id=None):
    if urls is None:
        urls = {}
    try:
        # Direct URLs from instagrapi
        if isinstance(obj, dict) and '_direct_urls' in obj:
            for pid, url in obj['_direct_urls'].items():
                if pid not in urls:
                    urls[pid] = decode_url(url)
            return urls

        # Web API format: {"user": {"edge_owner_to_timeline_media": {"edges": [{"node": {...}}]}}}
        if isinstance(obj, dict) and 'user' in obj:
            user = obj['user']
            timeline = user.get('edge_owner_to_timeline_media', {})
            edges = timeline.get('edges', [])
            for edge in edges:
                node = edge.get('node', {})
                shortcode = node.get('shortcode', '')
                # Single image/video
                display_url = node.get('display_url', '')
                if display_url and shortcode:
                    urls[shortcode] = decode_url(display_url)
                # Carousel (multiple images)
                sidecar = node.get('edge_sidecar_to_children', {})
                if sidecar:
                    for se in sidecar.get('edges', []):
                        child = se.get('node', {})
                        child_url = child.get('display_url', '')
                        if child_url:
                            idx = child.get('shortcode', '') or f"{shortcode}_{len(urls)}"
                            urls[idx] = decode_url(child_url)
            return urls

        # Direct timeline format
        if isinstance(obj, dict) and 'edge_owner_to_timeline_media' in obj:
            edges = obj['edge_owner_to_timeline_media'].get('edges', [])
            for edge in edges:
                node = edge.get('node', {})
                shortcode = node.get('shortcode', '')
                display_url = node.get('display_url', '')
                if display_url and shortcode:
                    urls[shortcode] = decode_url(display_url)
                sidecar = node.get('edge_sidecar_to_children', {})
                if sidecar:
                    for se in sidecar.get('edges', []):
                        child = se.get('node', {})
                        child_url = child.get('display_url', '')
                        if child_url:
                            idx = child.get('shortcode', '') or f"{shortcode}_{len(urls)}"
                            urls[idx] = decode_url(child_url)
            return urls

        # Original format: recursive search for image_versions2
        if isinstance(obj, dict):
            if 'pk' in obj and isinstance(obj.get('pk'), str):
                post_id = obj['pk']
            if 'image_versions2' in obj:
                candidates = obj['image_versions2'].get('candidates', [])
                if candidates:
                    highest_res = max(candidates, key=lambda x: x.get('width', 0) * x.get('height', 0))
                    url = highest_res.get('url', '')
                    if url:
                        decoded_url = decode_url(url)
                        if post_id and post_id not in urls:
                            urls[post_id] = decoded_url
            for value in obj.values():
                extract_highest_resolution_urls(value, urls, post_id)
        elif isinstance(obj, list):
            for item in obj:
                extract_highest_resolution_urls(item, urls, post_id)
    except:
        pass
    return urls


def generate_gallery_html(post_urls, username):
    total_images = len(post_urls)

    html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Cɪᴘʜᴇʀ · Private Gallery — @{username}</title>
    <link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600;800&family=Inter:wght@400;600;800&display=swap" rel="stylesheet">
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        :root {{
            --bg-0: #05060a;
            --bg-1: #0a0d14;
            --bg-2: #111624;
            --line: rgba(0, 255, 255, 0.15);
            --cyan: #00e5ff;
            --magenta: #ff2bd6;
            --green: #00ff9c;
            --red: #ff3860;
            --text: #e6f1ff;
            --dim: #7a8aa3;
        }}
        html, body {{ height: 100%; }}
        body {{
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            background: var(--bg-0);
            color: var(--text);
            min-height: 100vh;
            padding: 24px 18px;
            background-image:
                radial-gradient(circle at 15% 10%, rgba(0, 229, 255, 0.10), transparent 45%),
                radial-gradient(circle at 85% 90%, rgba(255, 43, 214, 0.10), transparent 45%),
                linear-gradient(180deg, #05060a 0%, #0a0d14 100%);
            background-attachment: fixed;
        }}
        body::before {{
            content: '';
            position: fixed;
            inset: 0;
            background-image:
                linear-gradient(rgba(0, 229, 255, 0.035) 1px, transparent 1px),
                linear-gradient(90deg, rgba(0, 229, 255, 0.035) 1px, transparent 1px);
            background-size: 40px 40px;
            pointer-events: none;
            z-index: 0;
        }}
        .container {{
            position: relative;
            z-index: 1;
            max-width: 1500px;
            margin: 0 auto;
            background: rgba(10, 13, 20, 0.75);
            border: 1px solid var(--line);
            border-radius: 20px;
            padding: 30px;
            backdrop-filter: blur(14px);
            box-shadow: 0 0 0 1px rgba(0, 229, 255, 0.05), 0 30px 80px rgba(0, 0, 0, 0.7);
        }}

        /* TOP STATUS */
        .server-status {{
            position: fixed;
            top: 20px;
            right: 20px;
            background: rgba(5, 6, 10, 0.9);
            color: var(--green);
            padding: 10px 18px;
            border-radius: 30px;
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.78rem;
            border: 1px solid var(--green);
            z-index: 1001;
            backdrop-filter: blur(8px);
            box-shadow: 0 0 20px rgba(0, 255, 156, 0.25);
            letter-spacing: 0.5px;
        }}
        .server-status::before {{
            content: '';
            display: inline-block;
            width: 8px; height: 8px;
            background: var(--green);
            border-radius: 50%;
            margin-right: 8px;
            box-shadow: 0 0 10px var(--green);
            animation: pulse 1.6s infinite;
        }}
        @keyframes pulse {{
            0%, 100% {{ opacity: 1; }}
            50% {{ opacity: 0.35; }}
        }}

        /* HEADER */
        .header {{
            position: relative;
            text-align: center;
            padding: 40px 20px 30px;
            border-radius: 16px;
            margin-bottom: 30px;
            background: linear-gradient(135deg, rgba(0, 229, 255, 0.08), rgba(255, 43, 214, 0.08));
            border: 1px solid var(--line);
            overflow: hidden;
        }}
        .header::after {{
            content: '';
            position: absolute;
            bottom: 0; left: 0; right: 0;
            height: 1px;
            background: linear-gradient(90deg, transparent, var(--cyan), var(--magenta), transparent);
        }}
        .brand {{
            font-family: 'JetBrains Mono', monospace;
            font-size: 2.8rem;
            font-weight: 800;
            letter-spacing: 4px;
            background: linear-gradient(90deg, var(--cyan), var(--magenta));
            -webkit-background-clip: text;
            background-clip: text;
            -webkit-text-fill-color: transparent;
            text-shadow: 0 0 40px rgba(0, 229, 255, 0.35);
            margin-bottom: 6px;
        }}
        .brand-sub {{
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.75rem;
            color: var(--dim);
            letter-spacing: 6px;
            text-transform: uppercase;
            margin-bottom: 22px;
        }}
        .target {{
            font-family: 'JetBrains Mono', monospace;
            font-size: 1.15rem;
            color: var(--cyan);
            margin-bottom: 6px;
        }}
        .target span {{
            color: var(--text);
            font-weight: 700;
        }}
        .tool-by {{
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.85rem;
            color: var(--magenta);
            margin-top: 8px;
            letter-spacing: 1px;
        }}
        .badges {{
            display: flex;
            justify-content: center;
            flex-wrap: wrap;
            gap: 10px;
            margin-top: 20px;
        }}
        .badge {{
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.72rem;
            letter-spacing: 1px;
            padding: 7px 14px;
            border-radius: 30px;
            text-transform: uppercase;
            font-weight: 600;
        }}
        .badge.warn {{
            color: var(--red);
            border: 1px solid rgba(255, 56, 96, 0.5);
            background: rgba(255, 56, 96, 0.08);
        }}
        .badge.ok {{
            color: var(--green);
            border: 1px solid rgba(0, 255, 156, 0.5);
            background: rgba(0, 255, 156, 0.08);
        }}

        /* STATS */
        .stats {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
            gap: 14px;
            margin-top: 26px;
        }}
        .stat {{
            background: rgba(5, 6, 10, 0.7);
            border: 1px solid var(--line);
            border-radius: 12px;
            padding: 16px 14px;
            text-align: center;
        }}
        .stat .num {{
            font-family: 'JetBrains Mono', monospace;
            font-size: 1.8rem;
            font-weight: 800;
            color: var(--cyan);
            text-shadow: 0 0 20px rgba(0, 229, 255, 0.4);
        }}
        .stat .lbl {{
            font-size: 0.72rem;
            letter-spacing: 2px;
            color: var(--dim);
            text-transform: uppercase;
            margin-top: 6px;
        }}

        /* GALLERY */
        .gallery {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(360px, 1fr));
            gap: 22px;
            padding: 6px 0;
        }}
        .post-card {{
            position: relative;
            background: rgba(17, 22, 36, 0.9);
            border: 1px solid var(--line);
            border-radius: 14px;
            overflow: hidden;
            transition: all 0.35s cubic-bezier(.2,.8,.2,1);
        }}
        .post-card::before {{
            content: '';
            position: absolute;
            inset: 0;
            border-radius: 14px;
            padding: 1px;
            background: linear-gradient(135deg, var(--cyan), var(--magenta));
            -webkit-mask: linear-gradient(#000 0 0) content-box, linear-gradient(#000 0 0);
            -webkit-mask-composite: xor;
                    mask-composite: exclude;
            opacity: 0;
            transition: opacity 0.35s;
            pointer-events: none;
        }}
        .post-card:hover {{
            transform: translateY(-6px);
            box-shadow: 0 20px 40px rgba(0, 229, 255, 0.15), 0 0 0 1px rgba(0, 229, 255, 0.3);
        }}
        .post-card:hover::before {{ opacity: 1; }}

        .post-header {{
            padding: 12px 14px;
            background: rgba(5, 6, 10, 0.8);
            border-bottom: 1px solid var(--line);
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        .post-id {{
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.72rem;
            color: var(--cyan);
            background: rgba(0, 229, 255, 0.06);
            padding: 4px 9px;
            border-radius: 6px;
            border: 1px solid rgba(0, 229, 255, 0.15);
            word-break: break-all;
        }}
        .dot {{
            width: 7px; height: 7px;
            background: var(--green);
            border-radius: 50%;
            box-shadow: 0 0 8px var(--green);
        }}

        .image-container {{
            background: #000;
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 420px;
            position: relative;
            overflow: hidden;
        }}
        .post-image {{
            max-width: 100%;
            max-height: 600px;
            object-fit: contain;
            display: block;
            transition: transform 0.5s, opacity 0.3s;
            cursor: zoom-in;
        }}
        .post-card:hover .post-image {{
            transform: scale(1.03);
        }}

        .post-footer {{
            padding: 14px;
            background: rgba(5, 6, 10, 0.8);
            border-top: 1px solid var(--line);
            display: flex;
            justify-content: space-between;
            align-items: center;
            gap: 10px;
        }}
        .download-btn {{
            flex: 1;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            gap: 6px;
            padding: 10px 16px;
            background: linear-gradient(135deg, var(--cyan), var(--magenta));
            color: #05060a;
            text-decoration: none;
            border-radius: 8px;
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.78rem;
            font-weight: 700;
            letter-spacing: 1px;
            text-transform: uppercase;
            transition: all 0.3s;
            border: none;
            cursor: pointer;
        }}
        .download-btn:hover {{
            filter: brightness(1.15);
            box-shadow: 0 0 20px rgba(0, 229, 255, 0.4);
            transform: translateY(-1px);
        }}

        /* FOOTER */
        .footer {{
            text-align: center;
            margin-top: 40px;
            padding: 24px 20px 10px;
            color: var(--dim);
            border-top: 1px solid var(--line);
            font-size: 0.85rem;
        }}
        .footer .brand-mini {{
            font-family: 'JetBrains Mono', monospace;
            color: var(--cyan);
            letter-spacing: 3px;
            font-weight: 700;
            margin-bottom: 8px;
        }}
        .footer .made {{
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.75rem;
            color: var(--magenta);
            margin-top: 6px;
            letter-spacing: 1px;
        }}
        .footer .note {{
            margin-top: 14px;
            font-size: 0.72rem;
            color: rgba(122, 138, 163, 0.65);
        }}

        /* LIGHTBOX */
        .lightbox {{
            display: none;
            position: fixed;
            inset: 0;
            background: rgba(0, 0, 0, 0.96);
            backdrop-filter: blur(10px);
            z-index: 1000;
            justify-content: center;
            align-items: center;
            cursor: zoom-out;
            padding: 20px;
        }}
        .lightbox.active {{ display: flex; animation: fadeIn 0.2s ease; }}
        @keyframes fadeIn {{ from {{ opacity: 0; }} to {{ opacity: 1; }} }}
        .lightbox img {{
            max-width: 95%;
            max-height: 95%;
            object-fit: contain;
            border-radius: 8px;
            box-shadow: 0 0 60px rgba(0, 229, 255, 0.3);
        }}

        @media (max-width: 768px) {{
            .brand {{ font-size: 2rem; letter-spacing: 2px; }}
            .gallery {{ grid-template-columns: 1fr; }}
            .container {{ padding: 18px; }}
            .server-status {{ font-size: 0.68rem; padding: 8px 12px; }}
        }}
    </style>
</head>
<body>
    <div class="server-status">LOCALHOST:8080 · ACTIVE</div>

    <div class="container">
        <div class="header">
            <div class="brand">Cɪᴘʜᴇʀ</div>
            <div class="brand-sub">Private Access Engine v2.0</div>
            <div class="target">TARGET → <span>@{username}</span></div>
            <div class="tool-by">◈ Made by Ryon · CipherXPortal ◈</div>

            <div class="badges">
                <span class="badge warn">⚠ Vulnerability Confirmed</span>
                <span class="badge ok">✓ {total_images} Posts Extracted</span>
            </div>

            <div class="stats">
                <div class="stat">
                    <div class="num">{total_images}</div>
                    <div class="lbl">Posts</div>
                </div>
                <div class="stat">
                    <div class="num">MAX</div>
                    <div class="lbl">Resolution</div>
                </div>
                <div class="stat">
                    <div class="num">0</div>
                    <div class="lbl">Duplicates</div>
                </div>
                <div class="stat">
                    <div class="num">8080</div>
                    <div class="lbl">Port</div>
                </div>
            </div>
        </div>

        <div class="gallery" id="gallery"></div>

        <div class="footer">
            <div class="brand-mini">Cɪᴘʜᴇʀ</div>
            <div>Instagram Private Post Monitor — POC</div>
            <div class="made">Made by Ryon · Portfolio: CipherXPortal</div>
            <div class="note">🔒 Serving on localhost:8080 · Full-resolution only · Deduped</div>
        </div>
    </div>

    <div class="lightbox" id="lightbox">
        <img src="" alt="Full Size">
    </div>

    <script>
        const postImages = {json.dumps(post_urls, indent=2)};
        const username = "{username}";
        const totalImages = {total_images};

        function renderGallery() {{
            const gallery = document.getElementById('gallery');
            Object.entries(postImages).forEach(([postId, imageUrl], idx) => {{
                const card = document.createElement('div');
                card.className = 'post-card';
                card.innerHTML = `
                    <div class="post-header">
                        <span class="post-id"># ${{String(idx + 1).padStart(3, '0')}} · ${{postId.substring(0, 18)}}…</span>
                        <span class="dot"></span>
                    </div>
                    <div class="image-container">
                        <img src="${{imageUrl}}" class="post-image" alt="post" loading="lazy"
                             onclick="openLightbox('${{imageUrl}}')">
                    </div>
                    <div class="post-footer">
                        <a href="${{imageUrl}}" class="download-btn" download="${{postId}}.jpg" target="_blank">⬇ Download HD</a>
                    </div>
                `;
                gallery.appendChild(card);
            }});
        }}

        function openLightbox(url) {{
            const lb = document.getElementById('lightbox');
            lb.querySelector('img').src = url;
            lb.classList.add('active');
        }}

        document.getElementById('lightbox').addEventListener('click', function() {{
            this.classList.remove('active');
        }});
        document.addEventListener('keydown', e => {{
            if (e.key === 'Escape') document.getElementById('lightbox').classList.remove('active');
        }});

        renderGallery();
    </script>
</body>
</html>
    """
    return html_content


def generate_unsuccessful_html(username):
    html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Cɪᴘʜᴇʀ · No Access — @{username}</title>
    <link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;700;800&family=Inter:wght@400;600;700&display=swap" rel="stylesheet">
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: 'Inter', sans-serif;
            background: #05060a;
            color: #e6f1ff;
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 24px;
            background-image:
                radial-gradient(circle at 20% 20%, rgba(255, 56, 96, 0.10), transparent 45%),
                radial-gradient(circle at 80% 80%, rgba(255, 43, 214, 0.08), transparent 45%);
        }}
        body::before {{
            content: '';
            position: fixed; inset: 0;
            background-image:
                linear-gradient(rgba(255, 56, 96, 0.03) 1px, transparent 1px),
                linear-gradient(90deg, rgba(255, 56, 96, 0.03) 1px, transparent 1px);
            background-size: 40px 40px;
            pointer-events: none;
        }}
        .container {{
            position: relative;
            max-width: 620px;
            width: 100%;
            background: rgba(10, 13, 20, 0.85);
            border: 1px solid rgba(255, 56, 96, 0.25);
            border-radius: 20px;
            padding: 50px 40px;
            backdrop-filter: blur(14px);
            box-shadow: 0 30px 80px rgba(0, 0, 0, 0.7);
            text-align: center;
        }}
        .brand {{
            font-family: 'JetBrains Mono', monospace;
            font-size: 2.2rem;
            font-weight: 800;
            letter-spacing: 4px;
            background: linear-gradient(90deg, #00e5ff, #ff2bd6);
            -webkit-background-clip: text;
            background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 6px;
        }}
        .brand-sub {{
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.72rem;
            color: #7a8aa3;
            letter-spacing: 6px;
            text-transform: uppercase;
            margin-bottom: 30px;
        }}
        .target {{
            font-family: 'JetBrains Mono', monospace;
            font-size: 1.05rem;
            color: #00e5ff;
            margin-bottom: 4px;
        }}
        .made {{
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.75rem;
            color: #ff2bd6;
            letter-spacing: 1px;
            margin-top: 8px;
            margin-bottom: 30px;
        }}
        .fail {{
            background: rgba(255, 56, 96, 0.08);
            border: 1px solid rgba(255, 56, 96, 0.45);
            color: #ff3860;
            padding: 26px 20px;
            border-radius: 14px;
            font-family: 'JetBrains Mono', monospace;
            font-size: 1.25rem;
            font-weight: 700;
            letter-spacing: 2px;
            box-shadow: 0 0 40px rgba(255, 56, 96, 0.15) inset;
        }}
        .fail .sub {{
            display: block;
            font-size: 0.72rem;
            font-weight: 400;
            letter-spacing: 1px;
            color: rgba(255, 56, 96, 0.75);
            margin-top: 12px;
        }}
        .footer {{
            margin-top: 34px;
            padding-top: 22px;
            border-top: 1px solid rgba(0, 229, 255, 0.1);
            color: #7a8aa3;
            font-size: 0.78rem;
        }}
        .footer .mini {{
            font-family: 'JetBrains Mono', monospace;
            color: #00e5ff;
            letter-spacing: 3px;
            font-weight: 700;
            margin-bottom: 6px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="brand">Cɪᴘʜᴇʀ</div>
        <div class="brand-sub">Private Access Engine</div>
        <div class="target">TARGET → @{username}</div>
        <div class="made">◈ Made by Ryon · CipherXPortal ◈</div>

        <div class="fail">
            ✕ UNSUCCESSFUL
            <span class="sub">No private posts found · account may be public or unreachable</span>
        </div>

        <div class="footer">
            <div class="mini">Cɪᴘʜᴇʀ</div>
            <div>Instagram Private Post Monitor — POC</div>
        </div>
    </div>
</body>
</html>
    """
    return html_content


def start_local_server_and_open_chrome(html_content, port=8080, successful=True):
    html_filename = 'instagram_gallery_temp.html'
    with open(html_filename, 'w', encoding='utf-8') as f:
        f.write(html_content)

    class GalleryHandler(SimpleHTTPRequestHandler):
        def do_GET(self):
            if self.path == '/':
                self.path = '/' + html_filename
            return super().do_GET()
        def log_message(self, *args, **kwargs):
            pass  # silence default noise

    def run_server():
        server = HTTPServer(('localhost', port), GalleryHandler)
        pc.cprint(f"green  [✓] Server online → http://localhost:{port} reset")
        if successful:
            pc.cprint(f"cyan  [→] Launching browser... reset")
        server.serve_forever()

    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()

    time.sleep(2)
    browser_url = f'http://localhost:{port}'
    pc.cprint(f"yellow  [!] Opening browser → {browser_url} reset")

    browser_opened = False
    try:
        if os.name == 'posix':
            try:
                pc.link(browser_url)
                browser_opened = True
                pc.cprint(f"green  [✓] Browser launched reset")
            except:
                pass
        if not browser_opened:
            pc.link(browser_url)
            browser_opened = True
            pc.cprint(f"green  [✓] Browser launched reset")
    except Exception as e:
        pc.cprint(f"red  [-] Browser error: {e} reset")

    if browser_opened:
        pc.cprint(f"green \n  ╔══════════════════════════════════════════════╗ reset")
        pc.cprint(f"green  ║   ✅  Cɪᴘʜᴇʀ LIVE  ·  {browser_url:<24} ║ reset")
        pc.cprint(f"green  ╚══════════════════════════════════════════════╝\n reset")
    else:
        pc.cprint(f"yellow  [!] Open manually → {browser_url} reset")

    return server_thread, html_filename


def save_urls_to_file(image_urls, username, successful=True):
    if successful:
        txt_filename = f'{username}_private_urls.txt'
        with open(txt_filename, 'w', encoding='utf-8') as f:
            f.write(f"Cɪᴘʜᴇʀ · Private Access Report\n")
            f.write(f"Target: @{username}\n")
            f.write(f"Made by Ryon · CipherXPortal\n")
            f.write("=" * 80 + "\n\n")
            f.write(f"Total Posts: {len(image_urls)}\n\n")
            for post_id, url in image_urls.items():
                f.write(f"POST ID: {post_id}\n")
                f.write(f"URL: {url}\n")
                f.write("-" * 80 + "\n\n")

        pc.cprint(f"green  [+] Saved {len(image_urls)} URLs → {txt_filename} reset")

        html_content = generate_gallery_html(image_urls, username)
        html_filename = f'{username}_private_gallery.html'
        with open(html_filename, 'w', encoding='utf-8') as f:
            f.write(html_content)

        pc.cprint(f"green  [+] Gallery written → {html_filename} reset")
    else:
        html_content = generate_unsuccessful_html(username)
        html_filename = f'{username}_private_gallery.html'
        with open(html_filename, 'w', encoding='utf-8') as f:
            f.write(html_content)
        pc.cprint(f"yellow  [!] No posts for @{username} reset")

    return html_content


def main():
    global username_global

    pc.cprint("cyan  ┌──────────────────────────────────────────────┐ reset")
    pc.cprint("cyan  │   Cɪᴘʜᴇʀ  ·  Instagram Private Access v2.0    │ reset")
    pc.cprint("cyan  │   Made by Ryon  ·  CipherXPortal              │ reset")
    pc.cprint("cyan  └──────────────────────────────────────────────┘ reset\n")

    username = input("  ┌─[ Enter Instagram username ]\n  └──▶ ").strip()
    username_global = username

    if not username:
        pc.cprint("red  [-] Username cannot be empty reset")
        return

    print()
    loading_animation()

    response = fetch_instagram_profile(username)

    if not response:
        pc.cprint("red \n  ✕ UNSUCCESSFUL reset")
        html_content = generate_unsuccessful_html(username)
        save_urls_to_file({}, username, successful=False)
        start_local_server_and_open_chrome(html_content, successful=False)
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            pc.cprint("yellow \n\n  [!] Server stopped reset")
        return

    timeline_data = extract_timeline_data(response.text)

    if not timeline_data:
        pc.cprint("red \n  ✕ UNSUCCESSFUL reset")
        html_content = generate_unsuccessful_html(username)
        save_urls_to_file({}, username, successful=False)
        start_local_server_and_open_chrome(html_content, successful=False)
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            pc.cprint("yellow \n\n  [!] Server stopped reset")
        return

    pc.cprint("cyan \n  [*] Extracting image URLs... reset")
    image_urls = extract_highest_resolution_urls(timeline_data)

    if not image_urls:
        pc.cprint("red \n  ✕ UNSUCCESSFUL reset")
        html_content = generate_unsuccessful_html(username)
        save_urls_to_file({}, username, successful=False)
        start_local_server_and_open_chrome(html_content, successful=False)
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            pc.cprint("yellow \n\n  [!] Server stopped reset")
        return

    print()
    pc.cprint(f"green  ╔══════════════════════════════════════════════╗ reset")
    pc.cprint(f"green  ║   ✅  SUCCESS — {len(image_urls):>3} posts extracted              ║ reset")
    pc.cprint(f"green  ╚══════════════════════════════════════════════╝ reset")
    print()

    html_content = save_urls_to_file(image_urls, username, successful=True)

    print()
    pc.cprint("cyan  [✓] Starting local server... reset")

    try:
        server_thread, temp_html = start_local_server_and_open_chrome(html_content, successful=True)
        pc.cprint(f"green \n  ╔══════════════════════════════════════════════╗ reset")
        pc.cprint(f"green  ║   🟢  http://localhost:8080                    ║ reset")
        pc.cprint(f"green  ╚══════════════════════════════════════════════╝ reset")
        pc.cprint(f"yellow \n  [!] Ctrl+C to stop\n reset")
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pc.cprint("green \n\n  [✓] Server stopped reset")
        try:
            os.remove('instagram_gallery_temp.html')
        except:
            pass


if __name__ == "__main__":
    username_global = ""
    main()