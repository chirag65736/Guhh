"""
Web wrapper for igscrapper.py — serves the Instagram scraping tool as a
web app on port 3000 so it can be used in a browser instead of the CLI.
"""

import http.server
import socketserver
import urllib.parse

from igscrapper import (
    fetch_instagram_profile,
    extract_timeline_data,
    extract_highest_resolution_urls,
    generate_gallery_html,
    generate_unsuccessful_html,
)

PORT = 8080

LANDING_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Cɪᴘʜᴇʀ · Instagram Private Access</title>
    <link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600;800&family=Inter:wght@400;600;800&display=swap" rel="stylesheet">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        :root {
            --bg-0: #05060a;
            --bg-1: #0a0d14;
            --line: rgba(0, 255, 255, 0.15);
            --cyan: #00e5ff;
            --magenta: #ff2bd6;
            --green: #00ff9c;
            --text: #e6f1ff;
            --dim: #7a8aa3;
        }
        html, body { height: 100%; }
        body {
            font-family: 'Inter', sans-serif;
            background: var(--bg-0);
            color: var(--text);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 24px;
            background-image:
                radial-gradient(circle at 15% 10%, rgba(0, 229, 255, 0.10), transparent 45%),
                radial-gradient(circle at 85% 90%, rgba(255, 43, 214, 0.10), transparent 45%);
            background-attachment: fixed;
        }
        body::before {
            content: '';
            position: fixed;
            inset: 0;
            background-image:
                linear-gradient(rgba(0, 229, 255, 0.035) 1px, transparent 1px),
                linear-gradient(90deg, rgba(0, 229, 255, 0.035) 1px, transparent 1px);
            background-size: 40px 40px;
            pointer-events: none;
            z-index: 0;
        }
        .container {
            position: relative;
            z-index: 1;
            max-width: 560px;
            width: 100%;
            background: rgba(10, 13, 20, 0.75);
            border: 1px solid var(--line);
            border-radius: 20px;
            padding: 50px 40px;
            backdrop-filter: blur(14px);
            box-shadow: 0 0 0 1px rgba(0, 229, 255, 0.05), 0 30px 80px rgba(0, 0, 0, 0.7);
        }
        .header { text-align: center; margin-bottom: 36px; }
        .brand {
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
        }
        .brand-sub {
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.75rem;
            color: var(--dim);
            letter-spacing: 6px;
            text-transform: uppercase;
            margin-bottom: 16px;
        }
        .tool-by {
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.85rem;
            color: var(--magenta);
            letter-spacing: 1px;
        }
        .badges {
            display: flex;
            justify-content: center;
            gap: 10px;
            margin-top: 20px;
        }
        .badge {
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.72rem;
            letter-spacing: 1px;
            padding: 7px 14px;
            border-radius: 30px;
            text-transform: uppercase;
            font-weight: 600;
        }
        .badge.ok {
            color: var(--green);
            border: 1px solid rgba(0, 255, 156, 0.5);
            background: rgba(0, 255, 156, 0.08);
        }
        form { display: flex; flex-direction: column; gap: 14px; }
        input[type="text"] {
            width: 100%;
            padding: 16px 18px;
            background: rgba(5, 6, 10, 0.8);
            border: 1px solid var(--line);
            border-radius: 12px;
            color: var(--text);
            font-family: 'JetBrains Mono', monospace;
            font-size: 1rem;
            outline: none;
            transition: border-color 0.3s, box-shadow 0.3s;
        }
        input[type="text"]::placeholder { color: var(--dim); }
        input[type="text"]:focus {
            border-color: var(--cyan);
            box-shadow: 0 0 0 3px rgba(0, 229, 255, 0.12);
        }
        button[type="submit"] {
            padding: 16px;
            background: linear-gradient(135deg, var(--cyan), var(--magenta));
            color: #05060a;
            border: none;
            border-radius: 12px;
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.9rem;
            font-weight: 800;
            letter-spacing: 2px;
            text-transform: uppercase;
            cursor: pointer;
            transition: all 0.3s;
        }
        button[type="submit"]:hover {
            filter: brightness(1.15);
            box-shadow: 0 0 30px rgba(0, 229, 255, 0.4);
            transform: translateY(-1px);
        }
        .footer {
            text-align: center;
            margin-top: 34px;
            padding-top: 22px;
            border-top: 1px solid var(--line);
            color: var(--dim);
            font-size: 0.78rem;
        }
        .footer .mini {
            font-family: 'JetBrains Mono', monospace;
            color: var(--cyan);
            letter-spacing: 3px;
            font-weight: 700;
            margin-bottom: 6px;
        }
        @media (max-width: 768px) {
            .brand { font-size: 2rem; letter-spacing: 2px; }
            .container { padding: 30px 20px; }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div class="brand">Cɪᴘʜᴇʀ</div>
            <div class="brand-sub">Private Access Engine v2.0</div>
            <div class="tool-by">◈ Made by Ryon · CipherXPortal ◈</div>
            <div class="badges">
                <span class="badge ok">✓ Ready</span>
            </div>
        </div>
        <form action="/" method="get">
            <input type="text" name="username" placeholder="Enter Instagram username..." required autocomplete="off">
            <button type="submit">⚡ Extract Posts</button>
        </form>
        <div class="footer">
            <div class="mini">Cɪᴘʜᴇʀ</div>
            <div>Instagram Private Post Monitor — POC</div>
        </div>
    </div>
</body>
</html>"""


def run_scrape(username):
    """Run the scraping pipeline and return resulting HTML."""
    response = fetch_instagram_profile(username)
    if not response:
        return generate_unsuccessful_html(username)

    timeline_data = extract_timeline_data(response.text)
    if not timeline_data:
        return generate_unsuccessful_html(username)

    image_urls = extract_highest_resolution_urls(timeline_data)
    if not image_urls:
        return generate_unsuccessful_html(username)

    return generate_gallery_html(image_urls, username)


class CipherHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)

        if parsed.path == "/" and "username" in params:
            username = params["username"][0].strip()
            if username:
                print(f"[*] Scraping requested for @{username}")
                html = run_scrape(username)
                self._serve_html(html)
                return

        # Default: landing page
        self._serve_html(LANDING_HTML)

    def _serve_html(self, html):
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(html.encode("utf-8"))

    def log_message(self, *args, **kwargs):
        pass


class ReusableTCPServer(socketserver.TCPServer):
    allow_reuse_address = True


if __name__ == "__main__":
    with ReusableTCPServer(("0.0.0.0", PORT), CipherHandler) as httpd:
        print(f"Cɪᴘʜᴇʀ web server listening on 0.0.0.0:{PORT}")
        httpd.serve_forever()
