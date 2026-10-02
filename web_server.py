"""
Cipher Web Server — full-featured app with auth, payments, gift cards,
invoices, admin panel, and Instagram scraping (unchanged).
"""

import http.server
import socketserver
import urllib.parse
import json

import database as db
import email_sender
from templates import (
    landing_page, login_page, signup_page, dashboard_page,
    payment_page, invoice_page, admin_page,
)
from igscrapper import (
    fetch_instagram_profile,
    extract_timeline_data,
    extract_highest_resolution_urls,
    generate_gallery_html,
    generate_unsuccessful_html,
)

PORT = 8080

BACK_BUTTON = """
<div style="position:fixed;bottom:24px;left:50%;transform:translateX(-50%);z-index:9999;">
  <a href="/dashboard" style="display:inline-flex;align-items:center;gap:8px;padding:14px 30px;background:linear-gradient(135deg,#00e5ff,#ff2bd6);color:#05060a;font-family:'JetBrains Mono',monospace;font-size:.85rem;font-weight:800;letter-spacing:2px;text-transform:uppercase;text-decoration:none;border-radius:12px;box-shadow:0 6px 24px rgba(0,229,255,.35);transition:all .3s;">← Back to Dashboard</a>
</div>
"""


def inject_back_button(html):
    """Inject a floating back button before </body>."""
    if '</body>' in html:
        return html.replace('</body>', BACK_BUTTON + '</body>', 1)
    return html + BACK_BUTTON


# ── Scraping pipeline (unchanged) ─────────────────────────────

def run_scrape(username):
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


# ── Handler ───────────────────────────────────────────────────

class CipherHandler(http.server.BaseHTTPRequestHandler):

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        params = urllib.parse.parse_qs(parsed.query)
        user = self._current_user()

        # ── Public routes ──
        if path == '/':
            self._serve_html(landing_page(user))
            return

        if path == '/login':
            if user:
                self._redirect('/dashboard')
                return
            self._serve_html(login_page())
            return

        if path == '/signup':
            if user:
                self._redirect('/dashboard')
                return
            self._serve_html(signup_page())
            return

        if path == '/logout':
            token = self._cookie_token()
            if token:
                db.delete_session(token)
            self.send_response(302)
            self.send_header('Set-Cookie', 'session=; Path=/; Max-Age=0')
            self.send_header('Location', '/')
            self.end_headers()
            return

        # ── Auth required ──
        if path == '/dashboard':
            if not user:
                self._redirect('/login')
                return
            flash = params.get('flash', [None])[0]
            self._serve_html(dashboard_page(user, flash))
            return

        if path == '/scrape':
            if not user:
                self._redirect('/login')
                return
            username = params.get('username', [''])[0].strip()
            if not username:
                self._redirect('/dashboard')
                return
            if not db.deduct_credit(user['id']):
                self._redirect('/dashboard?flash=error:' + urllib.parse.quote('No credits! Buy credits first.'))
                return
            print(f"[*] Scraping requested for @{username} by {user['email']}")
            html = run_scrape(username)
            html = inject_back_button(html)
            self._serve_html(html)
            return

        if path == '/payment':
            if not user:
                self._redirect('/login')
                return
            ptype = params.get('type', [''])[0]
            plan_key = params.get('plan', [None])[0]
            self._serve_html(payment_page(user, ptype, plan_key, db.get_payment_methods()))
            return

        if path == '/invoice':
            if not user:
                self._redirect('/login')
                return
            inv_id = params.get('id', [''])[0]
            try:
                inv_id = int(inv_id)
            except ValueError:
                inv_id = 0
            invoice = db.get_invoice(inv_id)
            if invoice and invoice['user_id'] != user['id'] and not user['is_admin']:
                invoice = None
            self._serve_html(invoice_page(user, invoice))
            return

        # ── Admin ──
        if path == '/admin':
            if not user or not user['is_admin']:
                self._redirect('/login')
                return
            flash = params.get('flash', [None])[0]
            self._serve_html(admin_page(
                user, db.get_stats(), db.get_all_users(),
                db.get_all_payments(), db.get_all_gift_cards(),
                db.get_all_invoices(), db.get_all_payment_methods(), flash
            ))
            return

        # ── 404 ──
        self._serve_html(landing_page(user))

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        body = self._parse_post_body()
        user = self._current_user()

        if path == '/login':
            email = body.get('email', [''])[0].strip()
            password = body.get('password', [''])[0]
            u = db.get_user_by_email(email)
            if u and db.verify_password(password, u['password_hash']):
                token = db.create_session(u['id'])
                self._redirect('/dashboard', cookie=f'session={token}; Path=/; HttpOnly')
            else:
                self._serve_html(login_page('Invalid email or password.'))
            return

        if path == '/signup':
            name = body.get('name', [''])[0].strip()
            email = body.get('email', [''])[0].strip()
            password = body.get('password', [''])[0]
            if not name or not email or not password:
                self._serve_html(signup_page('All fields are required.'))
                return
            if db.create_user(email, password, name):
                u = db.get_user_by_email(email)
                token = db.create_session(u['id'])
                self._redirect('/dashboard', cookie=f'session={token}; Path=/; HttpOnly')
            else:
                self._serve_html(signup_page('Email already registered.'))
            return

        if path == '/redeem':
            if not user:
                self._redirect('/login')
                return
            code = body.get('code', [''])[0].strip().upper()
            value = db.redeem_gift_card(code, user['id'])
            if value:
                self._redirect(f'/dashboard?flash=ok:' + urllib.parse.quote(f'Gift card redeemed! +{value} credits.'))
            else:
                self._redirect(f'/dashboard?flash=error:' + urllib.parse.quote('Invalid or already redeemed gift card.'))
            return

        if path == '/process-payment':
            if not user:
                self._redirect('/login')
                return
            ptype = body.get('payment_type', [''])[0]
            plan_key = body.get('plan_key', [''])[0] or None
            try:
                amount = float(body.get('amount', ['0'])[0])
                credits = int(body.get('credits', ['0'])[0])
            except ValueError:
                self._redirect('/dashboard')
                return

            # Record payment
            payment_id = db.create_payment(user['id'], amount, ptype, plan_key, credits)
            # Add credits
            db.add_credits(user['id'], credits)

            # Build invoice description
            if ptype == 'per_post':
                desc = f'1 Post Credit'
            elif ptype == 'plan' and plan_key in db.PLANS:
                plan = db.PLANS[plan_key]
                credits_label = 'Unlimited' if plan['credits'] >= 999 else f"{plan['credits']} Credits"
                desc = f'{plan["name"]} Plan — {credits_label} ({plan["duration"]})'
            else:
                desc = f'Credits Purchase'

            inv_id, inv_num = db.create_invoice(user['id'], payment_id, amount, desc)

            # Send invoice email automatically
            email_sender.send_invoice_email(
                user['email'], inv_num, amount, desc, user['name']
            )

            self._redirect(f'/invoice?id={inv_id}')
            return

        if path == '/admin/create-giftcard':
            if not user or not user['is_admin']:
                self._redirect('/login')
                return
            try:
                value = int(body.get('value', ['0'])[0])
            except ValueError:
                value = 0
            if value > 0:
                code = db.create_gift_card(value)
                self._redirect(f'/admin?flash=ok:' + urllib.parse.quote(f'Gift card created: {code}'))
            else:
                self._redirect('/admin?flash=error:Invalid value.')
            return

        if path == '/admin/add-credits':
            if not user or not user['is_admin']:
                self._redirect('/login')
                return
            try:
                target_id = int(body.get('user_id', ['0'])[0])
                amount = int(body.get('amount', ['0'])[0])
            except ValueError:
                self._redirect('/admin?flash=error:Invalid input.')
                return
            if amount > 0 and target_id > 0:
                db.add_credits(target_id, amount)
                target = db.get_user_by_id(target_id)
                name = target['name'] if target else 'User'
                self._redirect(f'/admin?flash=ok:' + urllib.parse.quote(f'Added {amount} credits to {name}.'))
            else:
                self._redirect('/admin?flash=error:Invalid amount.')
            return

        if path == '/admin/add-payment-method':
            if not user or not user['is_admin']:
                self._redirect('/login')
                return
            name = body.get('name', [''])[0].strip()
            details = body.get('details', [''])[0].strip()
            icon = body.get('icon', ['💳'])[0].strip() or '💳'
            if name and details:
                db.add_payment_method(name, details, icon)
                self._redirect(f'/admin?flash=ok:' + urllib.parse.quote(f'Payment method "{name}" added.'))
            else:
                self._redirect('/admin?flash=error:Name and details required.')
            return

        if path == '/admin/delete-payment-method':
            if not user or not user['is_admin']:
                self._redirect('/login')
                return
            try:
                method_id = int(body.get('method_id', ['0'])[0])
            except ValueError:
                method_id = 0
            if method_id > 0:
                db.delete_payment_method(method_id)
                self._redirect('/admin?flash=ok:' + urllib.parse.quote('Payment method removed.'))
            else:
                self._redirect('/admin?flash=error:Invalid method.')
            return

        self._redirect('/')

    # ── Helpers ──────────────────────────────────────────────

    def _serve_html(self, html):
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.end_headers()
        self.wfile.write(html.encode('utf-8'))

    def _redirect(self, location, cookie=None):
        self.send_response(302)
        if cookie:
            self.send_header('Set-Cookie', cookie)
        self.send_header('Location', location)
        self.end_headers()

    def _parse_post_body(self):
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length).decode('utf-8')
        return urllib.parse.parse_qs(body)

    def _cookie_token(self):
        cookie_header = self.headers.get('Cookie', '')
        for cookie in cookie_header.split(';'):
            parts = cookie.strip().split('=', 1)
            if len(parts) == 2 and parts[0] == 'session':
                return parts[1]
        return None

    def _current_user(self):
        token = self._cookie_token()
        return db.get_session_user(token) if token else None

    def log_message(self, *args, **kwargs):
        pass


class ReusableTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    allow_reuse_address = True
    daemon_threads = True


if __name__ == '__main__':
    db.init_db()
    with ReusableTCPServer(('0.0.0.0', PORT), CipherHandler) as httpd:
        print(f"Cipher web server listening on 0.0.0.0:{PORT}")
        httpd.serve_forever()
