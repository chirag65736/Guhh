"""
Web wrapper for the Cipher Instagram tool.
Serves a form on port 3000; on submit, reuses the scraping
functions from igscrapper.py and returns the gallery HTML.
"""

import html
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import parse_qs

import igscrapper as ig

PORT = 3000


LANDING_PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Cɪᴘʜᴇʀ · Private Access Engine</title>
    <link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600;800&family=Inter:wght@400;600;800&display=swap" rel="stylesheet">
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        :root {{
            --bg-0: #05060a;
            --bg-1: #0a0d14;
            --line: rgba(0, 255, 255, 0.15);
            --cyan: #00e5ff;
            --magenta: #ff2bd6;
            --green: #00ff9c;
            --text: #e6f1ff;
            --dim: #7a8aa3;
        }}
        html, body {{ height: 100%; }}
        body {{
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
                radial-gradient(circle at 85% 90%, rgba(255, 43, 214, 0.10), transparent 45%),
                linear-gradient(180deg, #05060a 0%, #0a0d14 100%);
            background-attachment: fixed;
        }}
        body::before {{
            content: '';
            position: fixed; inset: 0;
            background-image:
                linear-gradient(rgba(0, 229, 255, 0.035) 1px, transparent 1px),
                linear-gradient(90deg, rgba(0, 229, 255, 0.035) 1px, transparent 1px);
            background-size: 40px 40px;
            pointer-events: none;
            z-index: 0;
        }}
        .container {{
            position: relative; z-index: 1;
            max-width: 560px; width: 100%;
            background: rgba(10, 13, 20, 0.75);
            border: 1px solid var(--line);
            border-radius: 20px;
            padding: 44px 36px;
            backdrop-filter: blur(14px);
            box-shadow: 0 0 0 1px rgba(0, 229, 255, 0.05), 0 30px 80px rgba(0, 0, 0, 0.7);
        }}
        .brand {{
            font-family: 'JetBrains Mono', monospace;
            font-size: 2.6rem; font-weight: 800; letter-spacing: 4px;
            background: linear-gradient(90deg, var(--cyan), var(--magenta));
            -webkit-background-clip: text; background-clip: text;
            -webkit-text-fill-color: transparent;
            text-shadow: 0 0 40px rgba(0, 229, 255, 0.35);
            text-align: center; margin-bottom: 6px;
        }}
        .brand-sub {{
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.72rem; color: var(--dim);
            letter-spacing: 6px; text-transform: uppercase;
            text-align: center; margin-bottom: 30px;
        }}
        form {{ display: flex; flex-direction: column; gap: 16px; }}
        label {{
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.8rem; color: var(--cyan);
            letter-spacing: 1px;
        }}
        input[type=text] {{
            background: rgba(5, 6, 10, 0.8);
            border: 1px solid var(--line);
            border-radius: 10px;
            padding: 14px 16px;
            color: var(--text);
            font-family: 'JetBrains Mono', monospace;
            font-size: 1rem;
            outline: none;
            transition: border-color 0.3s, box-shadow 0.3s;
        }}
        input[type=text]:focus {{
            border-color: var(--cyan);
            box-shadow: 0 0 20px rgba(0, 229, 255, 0.2);
        }}
        input[type=text]::placeholder {{ color: rgba(122, 138, 163, 0.5); }}
        button {{
            padding: 14px 24px;
            background: linear-gradient(135deg, var(--cyan), var(--magenta));
            color: #05060a;
            border: none; border-radius: 10px;
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.85rem; font-weight: 800;
            letter-spacing: 2px; text-transform: uppercase;
            cursor: pointer;
            transition: filter 0.3s, transform 0.2s, box-shadow 0.3s;
        }}
        button:hover {{
            filter: brightness(1.15);
            box-shadow: 0 0 24px rgba(0, 229, 255, 0.4);
            transform: translateY(-1px);
        }}
        .footer {{
            text-align: center; margin-top: 30px;
            padding-top: 22px; border-top: 1px solid var(--line);
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.75rem; color: var(--dim);
        }}
        .footer .made {{ color: var(--magenta); margin-top: 6px; }}
        .status {{
            position: fixed; top: 20px; right: 20px;
            background: rgba(5, 6, 10, 0.9); color: var(--green);
            padding: 10px 18px; border-radius: 30px;
            font-family: 'JetBrains Mono', monospace; font-size: 0.78rem;
            border: 1px solid var(--green); z-index: 1001;
            backdrop-filter: blur(8px);
            box-shadow: 0 0 20px rgba(0, 255, 156, 0.25);
        }}
        .status::before {{
            content: ''; display: inline-block;
            width: 8px; height: 8px; background: var(--green);
            border-radius: 50%; margin-right: 8px;
            box-shadow: 0 0 10px var(--green);
            animation: pulse 1.6s infinite;
        }}
        @keyframes pulse {{ 0%,100% {{ opacity: 1; }} 50% {{ opacity: 0.35; }} }}
    </style>
</head>
<body>
    <div class="status">PORT 3000 · ACTIVE</div>
    <div class="container">
        <div class="brand">Cɪᴘʜᴇʀ</div>
        <div class="brand-sub">Private Access Engine v2.0</div>
        <form action="/scrape" method="POST">
            <label for="username">Instagram Username</label>
            <input type="text" id="username" name="username" placeholder="e.g. cristiano" required autofocus>
            <button type="submit">⚡ Extract Posts</button>
        </form>
        <div class="footer">
            Instagram Private Post Monitor — POC<br>
            <span class="made">◈ Made by Ryon · CipherXPortal ◈</span>
        </div>
    </div>
</body>
</html>"""


class CipherHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(LANDING_PAGE.encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length).decode("utf-8")
        fields = parse_qs(body)
        username = fields.get("username", [""])[0].strip()

        if not username:
            self.send_response(400)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(b"<h1>Username required</h1>")
            return

        print(f"[*] Scraping Instagram profile: @{username}")

        response = ig.fetch_instagram_profile(username)

        if not response:
            print(f"[-] Could not fetch profile for @{username}")
            html_content = ig.generate_unsuccessful_html(username)
        else:
            timeline_data = ig.extract_timeline_data(response.text)
            if not timeline_data:
                print(f"[-] No timeline data found for @{username}")
                html_content = ig.generate_unsuccessful_html(username)
            else:
                image_urls = ig.extract_highest_resolution_urls(timeline_data)
                if not image_urls:
                    print(f"[-] No image URLs extracted for @{username}")
                    html_content = ig.generate_unsuccessful_html(username)
                else:
                    print(f"[+] Found {len(image_urls)} posts for @{username}")
                    html_content = ig.generate_gallery_html(image_urls, username)

        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(html_content.encode("utf-8"))

    def log_message(self, *args, **kwargs):
        pass


def main():
    server = HTTPServer(("0.0.0.0", PORT), CipherHandler)
    print(f"[*] Cipher web server listening on 0.0.0.0:{PORT}")
    server.serve_forever()


if __name__ == "__main__":
    main()
