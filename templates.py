"""
HTML templates for Cipher — landing, auth, dashboard, payment,
invoice, and admin pages.  Keeps the existing cyberpunk theme.
"""

import urllib.parse
from database import PLANS, PER_POST_PRICE
from upi_payment import UPI_ID

# ── Shared CSS (regular string — no f-string brace issues) ────

SHARED_CSS = """
* { margin: 0; padding: 0; box-sizing: border-box; }
:root {
    --bg-0: #05060a; --bg-1: #0a0d14; --bg-2: #111624;
    --line: rgba(0,255,255,.15);
    --cyan: #00e5ff; --magenta: #ff2bd6; --green: #00ff9c;
    --red: #ff3860; --gold: #ffd700;
    --text: #e6f1ff; --dim: #7a8aa3;
}
html, body { height: 100%; }
body {
    font-family: 'Inter', sans-serif;
    background: var(--bg-0); color: var(--text); min-height: 100vh;
    padding: 0;
    background-image:
        radial-gradient(circle at 15% 10%, rgba(0,229,255,.10), transparent 45%),
        radial-gradient(circle at 85% 90%, rgba(255,43,214,.10), transparent 45%);
    background-attachment: fixed;
}
/* animated background orbs */
.bg-orbs { position: fixed; inset: 0; z-index: 0; pointer-events: none; overflow: hidden; }
.bg-orbs .orb {
    position: absolute; border-radius: 50%; filter: blur(60px); opacity: .35;
    animation: orbFloat 18s ease-in-out infinite;
}
.bg-orbs .orb:nth-child(1) { width: 320px; height: 320px; background: var(--cyan); top: -60px; left: -40px; animation-duration: 16s; }
.bg-orbs .orb:nth-child(2) { width: 280px; height: 280px; background: var(--magenta); bottom: -50px; right: -30px; animation-duration: 20s; animation-delay: -4s; }
.bg-orbs .orb:nth-child(3) { width: 220px; height: 220px; background: #7c3aed; top: 40%; left: 50%; animation-duration: 24s; animation-delay: -8s; }
@keyframes orbFloat {
    0%, 100% { transform: translate(0, 0) scale(1); }
    25% { transform: translate(60px, -40px) scale(1.1); }
    50% { transform: translate(-30px, 50px) scale(.95); }
    75% { transform: translate(40px, 30px) scale(1.05); }
}
body::before {
    content: ''; position: fixed; inset: 0; z-index: 0; pointer-events: none;
    background-image:
        linear-gradient(rgba(0,229,255,.035) 1px, transparent 1px),
        linear-gradient(90deg, rgba(0,229,255,.035) 1px, transparent 1px);
    background-size: 40px 40px;
}
/* made-by footer */
.made-by {
    position: relative; z-index: 1; text-align: center; padding: 24px 16px;
    font-family: 'JetBrains Mono', monospace; font-size: .72rem;
    color: var(--dim); letter-spacing: 2px;
}
.made-by .mb-name {
    font-family: 'Sacramento', cursive; font-size: 1.4rem;
    background: linear-gradient(90deg, var(--cyan), var(--magenta));
    -webkit-background-clip: text; background-clip: text; -webkit-text-fill-color: transparent;
    letter-spacing: 0;
}
/* nav */
.nav {
    position: relative; z-index: 10;
    display: flex; align-items: center; justify-content: space-between;
    padding: 16px 28px; border-bottom: 1px solid var(--line);
    background: rgba(5,6,10,.7); backdrop-filter: blur(14px);
}
.nav-brand { display: flex; align-items: center; gap: 12px; text-decoration: none; }
.nav-brand .logo { width: 38px; height: 38px; }
.nav-brand .name {
    font-family: 'JetBrains Mono', monospace; font-size: 1.4rem; font-weight: 800;
    letter-spacing: 3px;
    background: linear-gradient(90deg, var(--cyan), var(--magenta));
    -webkit-background-clip: text; background-clip: text; -webkit-text-fill-color: transparent;
}
.nav-links { display: flex; align-items: center; gap: 18px; }
.nav-links a, .nav-links span {
    font-family: 'JetBrains Mono', monospace; font-size: .82rem;
    color: var(--dim); text-decoration: none; letter-spacing: 1px;
    transition: color .25s;
}
.nav-links a:hover { color: var(--cyan); }
.nav-credits {
    font-family: 'JetBrains Mono', monospace; font-size: .78rem;
    color: var(--green); border: 1px solid rgba(0,255,156,.4);
    background: rgba(0,255,156,.08); padding: 5px 12px; border-radius: 20px;
    letter-spacing: 1px;
}
.nav-logout {
    color: var(--red) !important; border: 1px solid rgba(255,56,96,.3);
    padding: 5px 12px; border-radius: 8px;
}
/* page wrapper */
.page { position: relative; z-index: 1; padding: 40px 20px; max-width: 900px; margin: 0 auto; }
/* cards */
.card {
    background: rgba(10,13,20,.75); border: 1px solid var(--line);
    border-radius: 18px; padding: 36px 32px; backdrop-filter: blur(14px);
    box-shadow: 0 0 0 1px rgba(0,229,255,.05), 0 30px 80px rgba(0,0,0,.7);
    margin-bottom: 24px;
}
.card h2 {
    font-family: 'JetBrains Mono', monospace; font-size: 1.1rem;
    letter-spacing: 2px; text-transform: uppercase; margin-bottom: 20px;
    color: var(--cyan);
}
/* form inputs */
.field { display: flex; flex-direction: column; gap: 6px; margin-bottom: 16px; }
.field label {
    font-family: 'JetBrains Mono', monospace; font-size: .72rem;
    color: var(--dim); letter-spacing: 2px; text-transform: uppercase;
}
input[type="text"], input[type="email"], input[type="password"], input[type="number"] {
    width: 100%; padding: 14px 16px;
    background: rgba(5,6,10,.8); border: 1px solid var(--line);
    border-radius: 10px; color: var(--text);
    font-family: 'JetBrains Mono', monospace; font-size: .95rem;
    outline: none; transition: border-color .3s, box-shadow .3s;
}
input[type="text"]:focus, input[type="email"]:focus, input[type="password"]:focus, input[type="number"]:focus {
    border-color: var(--cyan); box-shadow: 0 0 0 3px rgba(0,229,255,.12);
}
/* buttons */
.btn {
    display: inline-block; padding: 14px 28px; border: none; border-radius: 10px;
    font-family: 'JetBrains Mono', monospace; font-size: .85rem; font-weight: 800;
    letter-spacing: 2px; text-transform: uppercase; cursor: pointer;
    text-decoration: none; text-align: center; transition: all .3s;
}
.btn-primary {
    background: linear-gradient(135deg, var(--cyan), var(--magenta)); color: #05060a;
}
.btn-primary:hover { filter: brightness(1.15); box-shadow: 0 0 30px rgba(0,229,255,.4); transform: translateY(-1px); }
.btn-outline {
    background: transparent; color: var(--cyan); border: 1px solid var(--cyan);
}
.btn-outline:hover { background: rgba(0,229,255,.1); }
.btn-green {
    background: linear-gradient(135deg, var(--green), #00c97d); color: #05060a;
}
.btn-green:hover { filter: brightness(1.15); box-shadow: 0 0 30px rgba(0,255,156,.4); }
.btn-sm { padding: 8px 16px; font-size: .72rem; }
.btn-block { display: block; width: 100%; }
/* flash / error */
.flash {
    padding: 12px 18px; border-radius: 10px; margin-bottom: 20px;
    font-family: 'JetBrains Mono', monospace; font-size: .82rem; letter-spacing: 1px;
}
.flash-error { background: rgba(255,56,96,.12); border: 1px solid rgba(255,56,96,.4); color: var(--red); }
.flash-ok { background: rgba(0,255,156,.12); border: 1px solid rgba(0,255,156,.4); color: var(--green); }
/* plan cards */
.plans-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 18px; }
.plan-card {
    background: rgba(17,22,36,.8); border: 1px solid var(--line); border-radius: 16px;
    padding: 28px 22px; text-align: center; transition: all .3s;
}
.plan-card:hover { border-color: var(--cyan); transform: translateY(-3px); box-shadow: 0 10px 40px rgba(0,229,255,.15); }
.plan-card .plan-name {
    font-family: 'JetBrains Mono', monospace; font-size: 1rem; font-weight: 800;
    letter-spacing: 2px; text-transform: uppercase; color: var(--cyan); margin-bottom: 8px;
}
.plan-card .plan-price {
    font-family: 'JetBrains Mono', monospace; font-size: 2.2rem; font-weight: 800;
    color: var(--text); margin-bottom: 4px;
}
.plan-card .plan-price span { font-size: .9rem; color: var(--dim); }
.plan-card .plan-credits {
    font-family: 'JetBrains Mono', monospace; font-size: .8rem; color: var(--green);
    margin-bottom: 16px; letter-spacing: 1px;
}
.plan-card ul { list-style: none; text-align: left; margin-bottom: 20px; }
.plan-card li {
    font-size: .82rem; color: var(--dim); padding: 5px 0;
    padding-left: 22px; position: relative;
}
.plan-card li::before { content: '✓'; position: absolute; left: 0; color: var(--green); font-weight: 700; }
/* stat cards (admin) */
.stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 16px; margin-bottom: 28px; }
.stat-card {
    background: rgba(17,22,36,.8); border: 1px solid var(--line); border-radius: 14px;
    padding: 22px 18px; text-align: center;
}
.stat-card .stat-label {
    font-family: 'JetBrains Mono', monospace; font-size: .68rem; color: var(--dim);
    letter-spacing: 2px; text-transform: uppercase; margin-bottom: 8px;
}
.stat-card .stat-value {
    font-family: 'JetBrains Mono', monospace; font-size: 1.8rem; font-weight: 800;
}
.stat-card.green .stat-value { color: var(--green); }
.stat-card.cyan .stat-value { color: var(--cyan); }
.stat-card.magenta .stat-value { color: var(--magenta); }
.stat-card.gold .stat-value { color: var(--gold); }
/* tables */
.table-wrap { overflow-x: auto; }
table { width: 100%; border-collapse: collapse; font-size: .8rem; }
th, td { padding: 10px 12px; text-align: left; border-bottom: 1px solid var(--line); }
th {
    font-family: 'JetBrains Mono', monospace; font-size: .68rem;
    color: var(--dim); letter-spacing: 2px; text-transform: uppercase;
}
td { font-family: 'JetBrains Mono', monospace; color: var(--text); }
tr:hover td { background: rgba(0,229,255,.04); }
.tag { padding: 3px 10px; border-radius: 20px; font-size: .68rem; letter-spacing: 1px; }
.tag-active { background: rgba(0,255,156,.12); border: 1px solid rgba(0,255,156,.4); color: var(--green); }
.tag-redeemed { background: rgba(122,138,163,.12); border: 1px solid rgba(122,138,163,.3); color: var(--dim); }
/* payment animation overlay */
.pay-overlay {
    position: fixed; inset: 0; z-index: 999; display: none;
    align-items: center; justify-content: center;
    background: rgba(5,6,10,.92); backdrop-filter: blur(20px);
}
.pay-overlay.active { display: flex; }
.pay-card-3d {
    width: 320px; height: 200px; border-radius: 16px; position: relative;
    background: linear-gradient(135deg, #0a0d14, #111624);
    border: 1px solid var(--line); padding: 24px;
    box-shadow: 0 30px 80px rgba(0,229,255,.2);
    animation: cardFlip 1.2s ease;
}
.pay-card-3d .chip {
    width: 44px; height: 34px; border-radius: 6px; margin-bottom: 30px;
    background: linear-gradient(135deg, #ffd700, #b8860b);
}
.pay-card-3d .card-num {
    font-family: 'JetBrains Mono', monospace; font-size: 1.1rem; letter-spacing: 3px;
    color: var(--text); margin-bottom: 20px;
}
.pay-card-3d .card-name {
    font-family: 'JetBrains Mono', monospace; font-size: .75rem; color: var(--dim);
}
.pay-spinner {
    width: 60px; height: 60px; margin: 30px auto;
    border: 3px solid rgba(0,229,255,.2); border-top-color: var(--cyan);
    border-radius: 50%; animation: spin 1s linear infinite;
}
.pay-check {
    width: 80px; height: 80px; margin: 20px auto;
    border-radius: 50%; background: rgba(0,255,156,.15);
    border: 3px solid var(--green); display: none;
    align-items: center; justify-content: center;
    animation: popIn .5s ease;
}
.pay-check svg { width: 40px; height: 40px; }
.pay-check .check-path {
    stroke: var(--green); stroke-width: 4; fill: none;
    stroke-dasharray: 50; stroke-dashoffset: 50;
    animation: drawCheck .5s ease .2s forwards;
}
.pay-status {
    text-align: center; font-family: 'JetBrains Mono', monospace;
    font-size: .85rem; letter-spacing: 2px; color: var(--cyan);
}
@keyframes spin { to { transform: rotate(360deg); } }
@keyframes cardFlip {
    0% { transform: perspective(800px) rotateY(90deg); opacity: 0; }
    100% { transform: perspective(800px) rotateY(0); opacity: 1; }
}
@keyframes popIn { 0% { transform: scale(0); } 70% { transform: scale(1.1); } 100% { transform: scale(1); } }
@keyframes drawCheck { to { stroke-dashoffset: 0; } }
/* invoice */
.invoice {
    max-width: 680px; margin: 0 auto;
    background: rgba(10,13,20,.85); border: 1px solid var(--line);
    border-radius: 18px; padding: 48px 42px; backdrop-filter: blur(14px);
    box-shadow: 0 30px 80px rgba(0,0,0,.7);
}
.invoice-head { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 36px; }
.invoice-head .inv-brand {
    font-family: 'JetBrains Mono', monospace; font-size: 1.8rem; font-weight: 800;
    letter-spacing: 3px;
    background: linear-gradient(90deg, var(--cyan), var(--magenta));
    -webkit-background-clip: text; background-clip: text; -webkit-text-fill-color: transparent;
}
.invoice-head .inv-meta { text-align: right; }
.invoice-head .inv-meta div {
    font-family: 'JetBrains Mono', monospace; font-size: .75rem; color: var(--dim);
    letter-spacing: 1px; margin-bottom: 4px;
}
.invoice-head .inv-meta .inv-num { color: var(--cyan); font-weight: 700; }
.invoice-section { margin-bottom: 24px; }
.invoice-section .label {
    font-family: 'JetBrains Mono', monospace; font-size: .68rem; color: var(--dim);
    letter-spacing: 2px; text-transform: uppercase; margin-bottom: 6px;
}
.invoice-section .value {
    font-family: 'JetBrains Mono', monospace; font-size: .9rem; color: var(--text);
}
.invoice-table { width: 100%; margin: 20px 0; }
.invoice-table th { font-size: .68rem; }
.invoice-table td { font-size: .82rem; padding: 12px; }
.invoice-total {
    display: flex; justify-content: flex-end; align-items: center; gap: 12px;
    padding-top: 16px; border-top: 1px solid var(--line);
}
.invoice-total .total-label {
    font-family: 'JetBrains Mono', monospace; font-size: .8rem; color: var(--dim);
    letter-spacing: 2px; text-transform: uppercase;
}
.invoice-total .total-amount {
    font-family: 'JetBrains Mono', monospace; font-size: 1.6rem; font-weight: 800; color: var(--green);
}
.invoice-paid {
    display: inline-block; padding: 6px 18px; border-radius: 20px;
    font-family: 'JetBrains Mono', monospace; font-size: .72rem; letter-spacing: 2px;
    background: rgba(0,255,156,.12); border: 1px solid rgba(0,255,156,.4); color: var(--green);
    margin-bottom: 24px;
}
.invoice-sign {
    margin-top: 40px; padding-top: 20px; border-top: 1px dashed var(--line);
    text-align: right;
}
.invoice-sign .sign-label {
    font-family: 'JetBrains Mono', monospace; font-size: .68rem; color: var(--dim);
    letter-spacing: 2px; text-transform: uppercase; margin-bottom: 8px;
}
.invoice-sign .sign-name {
    font-family: 'Sacramento', cursive; font-size: 2.4rem; color: var(--cyan);
    text-shadow: 0 0 20px rgba(0,229,255,.3);
}
.invoice-sign .sign-title {
    font-family: 'JetBrains Mono', monospace; font-size: .68rem; color: var(--dim);
    letter-spacing: 1px; margin-top: 4px;
}
/* responsive */
@media (max-width: 600px) {
    .nav { padding: 12px 16px; }
    .nav-brand .name { font-size: 1.1rem; }
    .nav-links { gap: 10px; }
    .page { padding: 24px 14px; }
    .card { padding: 24px 18px; }
    .invoice { padding: 28px 20px; }
    .invoice-head { flex-direction: column; gap: 16px; }
    .invoice-head .inv-meta { text-align: left; }
}
"""

# ── Logo SVG ──────────────────────────────────────────────────

LOGO_SVG = """
<svg viewBox="0 0 48 48" fill="none" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <linearGradient id="lg1" x1="0" y1="0" x2="48" y2="48">
      <stop offset="0" stop-color="#00e5ff"/>
      <stop offset="1" stop-color="#ff2bd6"/>
    </linearGradient>
  </defs>
  <path d="M24 2 L42 12 V36 L24 46 L6 36 V12 Z" stroke="url(#lg1)" stroke-width="2.5" fill="rgba(0,229,255,.06)"/>
  <path d="M30 18 A8 8 0 1 0 30 30 L33 33 A12 12 0 1 1 33 15 Z" fill="url(#lg1)"/>
  <circle cx="24" cy="24" r="3" fill="#05060a" stroke="url(#lg1)" stroke-width="1.5"/>
</svg>
"""

# ── Nav bar ───────────────────────────────────────────────────

def nav_bar(user=None):
    if user:
        links = f'<a href="/dashboard">Dashboard</a>'
        if user['is_admin']:
            links += '<a href="/admin">Admin Panel</a>'
            links += '<a href="/analytics">Analytics</a>'
        links += f'<span class="nav-credits">⚡ {user["credits"]} Credits</span>'
        links += '<a href="/logout" class="nav-logout">Logout</a>'
    else:
        links = '<a href="/login">Login</a><a href="/signup">Sign Up</a>'
    return f"""
    <nav class="nav">
        <a href="/" class="nav-brand">
            <div class="logo">{LOGO_SVG}</div>
            <span class="name">CIPHER</span>
        </a>
        <div class="nav-links">{links}</div>
    </nav>"""


def base_page(title, body, user=None, extra_head=""):
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600;800&family=Inter:wght@400;600;800&family=Sacramento&display=swap" rel="stylesheet">
    <style>{SHARED_CSS}</style>
    {extra_head}
</head>
<body>
    <div class="bg-orbs"><div class="orb"></div><div class="orb"></div><div class="orb"></div></div>
    {nav_bar(user)}
    <div class="page">{body}</div>
    <div class="made-by">Made with ❤ by <span class="mb-name">Chirag</span></div>
</body>
</html>"""


# ── Landing page ──────────────────────────────────────────────

def landing_page(user=None):
    if user:
        return dashboard_page(user)
    body = f"""
    <div class="card" style="text-align:center;">
        <div style="margin:0 auto 20px;width:80px;height:80px;">{LOGO_SVG}</div>
        <h1 style="font-family:'JetBrains Mono',monospace;font-size:2.4rem;font-weight:800;letter-spacing:4px;background:linear-gradient(90deg,var(--cyan),var(--magenta));-webkit-background-clip:text;background-clip:text;-webkit-text-fill-color:transparent;margin-bottom:8px;">CIPHER</h1>
        <p style="font-family:'JetBrains Mono',monospace;font-size:.78rem;color:var(--dim);letter-spacing:6px;text-transform:uppercase;margin-bottom:24px;">Private Access Engine v2.0</p>
        <p style="color:var(--dim);font-size:.95rem;margin-bottom:32px;max-width:420px;margin-left:auto;margin-right:auto;">Extract high-resolution Instagram post images. Pay per username or choose a monthly plan. Premium access, premium results.</p>
        <div style="display:flex;gap:14px;justify-content:center;flex-wrap:wrap;">
            <a href="/login" class="btn btn-primary">⚡ Login</a>
            <a href="/signup" class="btn btn-outline">Sign Up</a>
        </div>
        <div style="margin-top:32px;padding-top:24px;border-top:1px solid var(--line);">
            <div style="display:flex;gap:20px;justify-content:center;flex-wrap:wrap;">
                <span style="font-family:'JetBrains Mono',monospace;font-size:.72rem;color:var(--green);letter-spacing:1px;">✓ ₹15 / Post</span>
                <span style="font-family:'JetBrains Mono',monospace;font-size:.72rem;color:var(--green);letter-spacing:1px;">✓ Monthly Plans</span>
                <span style="font-family:'JetBrains Mono',monospace;font-size:.72rem;color:var(--green);letter-spacing:1px;">✓ Gift Cards</span>
                <span style="font-family:'JetBrains Mono',monospace;font-size:.72rem;color:var(--green);letter-spacing:1px;">✓ Invoices</span>
            </div>
        </div>
    </div>"""
    return base_page("Cipher · Private Access", body, user)


# ── Login ─────────────────────────────────────────────────────

def login_page(error=None):
    flash = f'<div class="flash flash-error">{error}</div>' if error else ''
    body = f"""
    <div class="card" style="max-width:440px;margin:0 auto;">
        <h2>⚡ Login</h2>
        {flash}
        <form action="/login" method="post">
            <div class="field"><label>Email</label><input type="email" name="email" required placeholder="you@email.com"></div>
            <div class="field"><label>Password</label><input type="password" name="password" required placeholder="••••••••"></div>
            <button type="submit" class="btn btn-primary btn-block">Login</button>
        </form>
        <p style="text-align:center;margin-top:18px;font-family:'JetBrains Mono',monospace;font-size:.78rem;color:var(--dim);">
            No account? <a href="/signup" style="color:var(--cyan);">Sign up</a>
        </p>
    </div>"""
    return base_page("Cipher · Login", body)


# ── Signup ────────────────────────────────────────────────────

def signup_page(error=None):
    flash = f'<div class="flash flash-error">{error}</div>' if error else ''
    body = f"""
    <div class="card" style="max-width:440px;margin:0 auto;">
        <h2>◈ Sign Up</h2>
        {flash}
        <form action="/signup" method="post">
            <div class="field"><label>Name</label><input type="text" name="name" required placeholder="Your name"></div>
            <div class="field"><label>Email</label><input type="email" name="email" required placeholder="you@email.com"></div>
            <div class="field"><label>Password</label><input type="password" name="password" required placeholder="••••••••"></div>
            <button type="submit" class="btn btn-primary btn-block">Create Account</button>
        </form>
        <p style="text-align:center;margin-top:18px;font-family:'JetBrains Mono',monospace;font-size:.78rem;color:var(--dim);">
            Already have an account? <a href="/login" style="color:var(--cyan);">Login</a>
        </p>
    </div>"""
    return base_page("Cipher · Sign Up", body)


# ── Dashboard ─────────────────────────────────────────────────

def dashboard_page(user, flash=None):
    flash_html = ''
    if flash:
        cls = 'flash-ok' if flash.startswith('ok:') else 'flash-error'
        flash_html = f'<div class="flash {cls}">{flash[3:] if flash[3:] else flash}</div>'

    # Scrape form
    scrape_section = f"""
    <div class="card">
        <h2>⚡ Extract Posts</h2>
        <p style="color:var(--dim);font-size:.85rem;margin-bottom:18px;">Enter an Instagram username. <b style="color:var(--green);">1 credit</b> per scrape. You have <b style="color:var(--green);">{user['credits']}</b> credits.</p>
        <form action="/scrape" method="get" style="display:flex;gap:12px;flex-wrap:wrap;">
            <input type="text" name="username" placeholder="Instagram username..." required style="flex:1;min-width:200px;" autocomplete="off">
            <button type="submit" class="btn btn-primary">⚡ Quick Scan</button>
        </form>
        <div style="margin-top:16px;padding-top:16px;border-top:1px solid var(--line);">
            <p style="color:var(--dim);font-size:.78rem;margin-bottom:12px;">🔍 <b style="color:var(--magenta);">Private Deep Scan</b> — finds <b>more posts</b> using pagination (up to 60). Separate scraper engine.</p>
            <form action="/scrape-private" method="get" style="display:flex;gap:12px;flex-wrap:wrap;">
                <input type="text" name="username" placeholder="Instagram username..." required style="flex:1;min-width:200px;" autocomplete="off">
                <button type="submit" class="btn btn-outline" style="border-color:var(--magenta);color:var(--magenta);">🔍 Deep Scan</button>
            </form>
        </div>
    </div>"""

    # Per-post payment
    per_post = f"""
    <div class="card" style="text-align:center;">
        <h2>💳 Pay Per Post</h2>
        <p style="color:var(--dim);font-size:.85rem;margin-bottom:18px;">Buy 1 credit for ₹{PER_POST_PRICE}. Use it to extract any profile.</p>
        <a href="/payment?type=per_post" class="btn btn-green">Buy 1 Credit · ₹{PER_POST_PRICE}</a>
    </div>"""

    # Plans
    plans_html = ''
    for key, plan in PLANS.items():
        credits_label = 'Unlimited' if plan['credits'] >= 999 else f"{plan['credits']} Credits"
        features = [
            f"{credits_label}",
            "High-Res Images",
            "Priority Support",
        ]
        if key == 'elite':
            features += ["Batch Download", "API Access"]
        features_html = ''.join(f'<li>{f}</li>' for f in features)
        plans_html += f"""
        <div class="plan-card">
            <div class="plan-name">{plan['name']}</div>
            <div class="plan-price">₹{plan['price']}<span> / {plan['duration']}</span></div>
            <div class="plan-credits">{credits_label}</div>
            <ul>{features_html}</ul>
            <a href="/payment?type=plan&plan={key}" class="btn btn-outline btn-block">Choose {plan['name']}</a>
        </div>"""

    plans_section = f"""
    <div class="card">
        <h2>📅 Monthly Plans</h2>
        <div class="plans-grid">{plans_html}</div>
    </div>"""

    # Gift card
    gift_section = f"""
    <div class="card">
        <h2>🎁 Gift Card</h2>
        <p style="color:var(--dim);font-size:.85rem;margin-bottom:18px;">Have a gift card code? Redeem it for credits.</p>
        <form action="/redeem" method="post" style="display:flex;gap:12px;flex-wrap:wrap;">
            <input type="text" name="code" placeholder="GIFT-XXXXXXXX" required style="flex:1;min-width:200px;">
            <button type="submit" class="btn btn-outline">Redeem</button>
        </form>
    </div>"""

    body = flash_html + scrape_section + per_post + plans_section + gift_section
    return base_page("Cipher · Dashboard", body, user)


# ── Scrape loading page (animated) ─────────────────────────────

def scrape_loading_page(user, username, mode='quick'):
    """Animated loading page shown while the scraper works.
    JS fetches the actual result from /scrape-result or /scrape-private-result
    and swaps the page content when done."""
    api_url = f"/scrape-result?username={urllib.parse.quote(username)}" if mode == 'quick' \
        else f"/scrape-private-result?username={urllib.parse.quote(username)}"
    mode_label = 'Quick Scan' if mode == 'quick' else 'Private Deep Scan'
    mode_color = 'var(--cyan)' if mode == 'quick' else 'var(--magenta)'

    body = f"""
    <div class="card" style="text-align:center;max-width:520px;margin:0 auto;">
        <h2 style="color:{mode_color};">⚡ {mode_label}</h2>
        <p style="color:var(--dim);font-size:.85rem;margin-bottom:24px;">Target: <b style="color:{mode_color};">@{username}</b></p>

        <!-- Radar scanner animation -->
        <div class="radar-wrap">
            <div class="radar">
                <div class="radar-ring"></div>
                <div class="radar-ring r2"></div>
                <div class="radar-ring r3"></div>
                <div class="radar-sweep"></div>
                <div class="radar-center"></div>
                <div class="radar-dot d1"></div>
                <div class="radar-dot d2"></div>
                <div class="radar-dot d3"></div>
            </div>
        </div>

        <!-- Progress steps -->
        <div class="scan-steps" style="margin:28px 0;">
            <div class="scan-step" id="step1">
                <span class="step-icon">○</span> Connecting to Instagram...
            </div>
            <div class="scan-step" id="step2">
                <span class="step-icon">○</span> Fetching profile data...
            </div>
            <div class="scan-step" id="step3">
                <span class="step-icon">○</span> Finding posts{'...' if mode == 'quick' else ' (paginating)...'}
            </div>
            <div class="scan-step" id="step4">
                <span class="step-icon">○</span> Building gallery...
            </div>
        </div>

        <!-- Post counter -->
        <div class="post-counter" id="postCounter" style="display:none;">
            <span class="counter-num" id="counterNum">0</span>
            <span class="counter-lbl">posts found</span>
        </div>

        <p style="color:var(--dim);font-size:.78rem;margin-top:20px;" id="loadingMsg">Scanning... please wait</p>
        <p style="color:var(--red);font-size:.78rem;margin-top:12px;display:none;" id="errorMsg"></p>
        <a href="/dashboard" class="btn btn-outline btn-sm" style="margin-top:16px;display:none;" id="backBtn">← Back to Dashboard</a>
    </div>"""

    extra = f"""<style>
.radar-wrap {{ display:flex;justify-content:center;margin:10px 0; }}
.radar {{
    width:200px;height:200px;position:relative;border-radius:50%;
    background:radial-gradient(circle,rgba(0,229,255,.03),rgba(5,6,10,.8));
    border:1px solid rgba(0,229,255,.2);overflow:hidden;
}}
.radar-ring {{
    position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);
    width:60%;height:60%;border-radius:50%;border:1px solid rgba(0,229,255,.1);
}}
.radar-ring.r2 {{ width:80%;height:80%; }}
.radar-ring.r3 {{ width:100%;height:100%; }}
.radar-sweep {{
    position:absolute;top:50%;left:50%;width:50%;height:2px;
    transform-origin:left center;
    background:linear-gradient(90deg,transparent,{mode_color});
    box-shadow:0 0 12px {mode_color};
    animation:radarSweep 2s linear infinite;
}}
@keyframes radarSweep {{ from {{ transform:rotate(0deg); }} to {{ transform:rotate(360deg); }} }}
.radar-center {{
    position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);
    width:10px;height:10px;border-radius:50%;background:{mode_color};
    box-shadow:0 0 15px {mode_color};animation:radarPulse 1.5s ease infinite;
}}
@keyframes radarPulse {{ 0%,100%{{opacity:1;}}50%{{opacity:.4;}} }}
.radar-dot {{
    position:absolute;width:6px;height:6px;border-radius:50%;
    background:var(--green);box-shadow:0 0 8px var(--green);
    animation:dotBlink 1.5s ease infinite;
}}
.radar-dot.d1 {{ top:30%;left:60%;animation-delay:.3s; }}
.radar-dot.d2 {{ top:65%;left:35%;animation-delay:.7s; }}
.radar-dot.d3 {{ top:45%;left:70%;animation-delay:1.1s; }}
@keyframes dotBlink {{ 0%,100%{{opacity:0;}}50%{{opacity:1;}} }}
.scan-steps {{ text-align:left;max-width:300px;margin:0 auto; }}
.scan-step {{
    font-family:'JetBrains Mono',monospace;font-size:.82rem;color:var(--dim);
    padding:8px 0;transition:color .3s;letter-spacing:1px;
}}
.scan-step.active {{ color:var(--cyan); }}
.scan-step.active .step-icon {{ color:var(--cyan);animation:spin 1s linear infinite;display:inline-block; }}
.scan-step.done {{ color:var(--green); }}
.scan-step.done .step-icon {{ content:'✓';color:var(--green); }}
.scan-step .step-icon {{ display:inline-block;width:20px;text-align:center; }}
.post-counter {{
    display:flex;align-items:baseline;justify-content:center;gap:8px;
    padding:16px;border-radius:12px;background:rgba(0,255,156,.06);
    border:1px solid rgba(0,255,156,.2);
}}
.counter-num {{ font-family:'JetBrains Mono',monospace;font-size:2rem;font-weight:800;color:var(--green); }}
.counter-lbl {{ font-family:'JetBrains Mono',monospace;font-size:.78rem;color:var(--dim);letter-spacing:2px;text-transform:uppercase; }}
</style>
<script>
(function() {{
    var steps = [
        document.getElementById('step1'),
        document.getElementById('step2'),
        document.getElementById('step3'),
        document.getElementById('step4')
    ];
    var stepIdx = 0;
    var counter = document.getElementById('postCounter');
    var counterNum = document.getElementById('counterNum');
    var loadingMsg = document.getElementById('loadingMsg');
    var errorMsg = document.getElementById('errorMsg');
    var backBtn = document.getElementById('backBtn');

    // Animate steps progressively
    var stepInterval = setInterval(function() {{
        if (stepIdx > 0) {{
            steps[stepIdx - 1].classList.remove('active');
            steps[stepIdx - 1].classList.add('done');
            steps[stepIdx - 1].querySelector('.step-icon').textContent = '✓';
        }}
        if (stepIdx < steps.length) {{
            steps[stepIdx].classList.add('active');
            steps[stepIdx].querySelector('.step-icon').textContent = '◉';
            stepIdx++;
        }} else {{
            stepIdx = 1; // loop back to keep "finding posts" active
            steps[3].classList.remove('done');
            steps[3].classList.add('active');
            steps[3].querySelector('.step-icon').textContent = '◉';
        }}
    }}, 2500);

    // Animate post counter after a delay
    setTimeout(function() {{
        counter.style.display = 'flex';
        var n = 0;
        var cInt = setInterval(function() {{
            n += Math.floor(Math.random() * 3) + 1;
            counterNum.textContent = n;
        }}, 800);
        window._cInt = cInt;
    }}, 4000);

    // Fetch the actual scrape result
    fetch('{api_url}')
        .then(function(r) {{ return r.text(); }})
        .then(function(html) {{
            clearInterval(stepInterval);
            if (window._cInt) clearInterval(window._cInt);
            // Replace entire page with gallery HTML
            document.open();
            document.write(html);
            document.close();
        }})
        .catch(function(err) {{
            clearInterval(stepInterval);
            if (window._cInt) clearInterval(window._cInt);
            loadingMsg.style.display = 'none';
            errorMsg.style.display = 'block';
            errorMsg.textContent = 'Scan failed: ' + err.message;
            backBtn.style.display = 'inline-block';
        }});
}})();
</script>"""

    return base_page(f"Cipher · Scanning @{username}", body, user, extra)


# ── Payment page ──────────────────────────────────────────────

PAYMENT_JS = """
function startPayment() {
    const overlay = document.getElementById('payOverlay');
    const form = document.getElementById('payForm');
    overlay.classList.add('active');
    const status = document.getElementById('payStatus');
    const spinner = document.getElementById('paySpinner');
    const check = document.getElementById('payCheck');
    const card = document.getElementById('payCard');

    setTimeout(() => {
        card.style.display = 'none';
        spinner.style.display = 'block';
        status.textContent = 'Processing Payment...';
    }, 1300);

    setTimeout(() => {
        spinner.style.display = 'none';
        check.style.display = 'flex';
        status.textContent = 'Payment Successful!';
        status.style.color = 'var(--green)';
    }, 3000);

    setTimeout(() => {
        form.submit();
    }, 4200);
    return false;
}

function copyUpi() {
    navigator.clipboard.writeText('""" + UPI_ID + """').then(function() {
        var btn = document.querySelector('.copy-btn');
        var orig = btn.textContent;
        btn.textContent = '✓ Copied!';
        btn.style.color = 'var(--green)';
        btn.style.borderColor = 'rgba(0,255,156,.4)';
        setTimeout(function() { btn.textContent = orig; btn.style.color = ''; btn.style.borderColor = ''; }, 2000);
    });
}

function showUpload() {
    var form = document.getElementById('upiUploadForm');
    form.style.display = 'block';
    form.scrollIntoView({ behavior: 'smooth', block: 'center' });
}

function previewSS(input) {
    if (input.files && input.files[0]) {
        var reader = new FileReader();
        reader.onload = function(e) {
            var img = document.getElementById('ssPreview');
            img.src = e.target.result;
            img.style.display = 'block';
        };
        reader.readAsDataURL(input.files[0]);
    }
}

function startUpiVerify() {
    var form = document.getElementById('upiForm');
    if (!form.checkValidity()) { form.reportValidity(); return false; }

    var overlay = document.getElementById('upiVerifyOverlay');
    var scanner = document.getElementById('verifyScanner');
    var check = document.getElementById('verifyCheck');
    var steps = document.querySelectorAll('.verify-step');
    overlay.classList.add('active');
    scanner.style.display = 'block';
    check.classList.remove('show');
    steps.forEach(function(s) { s.classList.remove('active'); s.style.color = ''; });

    setTimeout(function() { steps[0].classList.add('active'); }, 300);
    setTimeout(function() { steps[0].classList.remove('active'); steps[1].classList.add('active'); }, 1600);
    setTimeout(function() { steps[1].classList.remove('active'); steps[2].classList.add('active'); }, 2900);
    setTimeout(function() {
        steps[2].classList.remove('active');
        scanner.style.display = 'none';
        check.classList.add('show');
        steps[3].classList.add('active');
        steps[3].style.color = 'var(--green)';
    }, 4000);
    setTimeout(function() { form.submit(); }, 5000);
    return false;
}
"""


def payment_page(user, payment_type, plan_key=None, payment_methods=None):
    if payment_type == 'per_post':
        amount = PER_POST_PRICE
        title_text = "Pay Per Post"
        desc = f"1 Credit · ₹{amount}"
        credits = 1
    elif payment_type == 'plan' and plan_key in PLANS:
        plan = PLANS[plan_key]
        amount = plan['price']
        title_text = f"{plan['name']} Plan"
        credits_label = 'Unlimited' if plan['credits'] >= 999 else f"{plan['credits']} Credits"
        desc = f"{credits_label} · ₹{amount} / {plan['duration']}"
        credits = plan['credits']
    else:
        return base_page("Cipher · Error", '<div class="card"><div class="flash flash-error">Invalid payment option.</div><a href="/dashboard" class="btn btn-outline">Back to Dashboard</a></div>', user)

    # UPI deep link + QR code
    upi_link = f"upi://pay?pa={UPI_ID}&pn=CIPHER&am={amount}&cu=INR&tn=Cipher Credits"
    qr_url = f"https://api.qrserver.com/v1/create-qr-code/?size=200x200&data={urllib.parse.quote(upi_link)}"

    # Custom payment methods section
    pm_html = ''
    if payment_methods:
        pm_cards = ''
        for pm in payment_methods:
            pm_cards += f"""
            <div style="background:rgba(17,22,36,.8);border:1px solid var(--line);border-radius:12px;padding:18px;margin-bottom:12px;">
                <div style="display:flex;align-items:center;gap:12px;margin-bottom:8px;">
                    <span style="font-size:1.5rem;">{pm['icon']}</span>
                    <span style="font-family:'JetBrains Mono',monospace;font-size:.95rem;font-weight:800;color:var(--cyan);letter-spacing:1px;">{pm['name']}</span>
                </div>
                <div style="font-family:'JetBrains Mono',monospace;font-size:.85rem;color:var(--text);word-break:break-all;">{pm['details']}</div>
            </div>"""
        pm_html = f"""
        <div style="margin-top:24px;padding-top:20px;border-top:1px solid var(--line);">
            <div style="font-family:'JetBrains Mono',monospace;font-size:.78rem;color:var(--dim);letter-spacing:2px;text-transform:uppercase;margin-bottom:14px;">Other Methods</div>
            {pm_cards}
        </div>"""

    body = f"""
    <div class="card" style="max-width:480px;margin:0 auto;">
        <h2>💳 {title_text}</h2>
        <p style="color:var(--dim);font-size:.85rem;margin-bottom:20px;">{desc}</p>
        <div style="background:rgba(17,22,36,.8);border:1px solid var(--line);border-radius:12px;padding:20px;margin-bottom:24px;">
            <div style="display:flex;justify-content:space-between;margin-bottom:12px;">
                <span style="font-family:'JetBrains Mono',monospace;font-size:.78rem;color:var(--dim);letter-spacing:1px;">Amount</span>
                <span style="font-family:'JetBrains Mono',monospace;font-size:1.2rem;font-weight:800;color:var(--green);">₹{amount}</span>
            </div>
            <div style="display:flex;justify-content:space-between;">
                <span style="font-family:'JetBrains Mono',monospace;font-size:.78rem;color:var(--dim);letter-spacing:1px;">Credits</span>
                <span style="font-family:'JetBrains Mono',monospace;font-size:.9rem;color:var(--cyan);">{credits}</span>
            </div>
        </div>

        <!-- UPI Section (Primary) -->
        <div style="background:linear-gradient(135deg,rgba(0,229,255,.08),rgba(124,58,237,.08));border:1px solid rgba(0,229,255,.25);border-radius:16px;padding:28px 22px;margin-bottom:20px;text-align:center;">
            <div style="font-family:'JetBrains Mono',monospace;font-size:.72rem;color:var(--cyan);letter-spacing:4px;text-transform:uppercase;margin-bottom:14px;">⚡ Pay via UPI</div>
            <div style="display:flex;align-items:center;justify-content:center;gap:10px;margin-bottom:16px;flex-wrap:wrap;">
                <span style="font-family:'JetBrains Mono',monospace;font-size:1.05rem;font-weight:800;color:var(--cyan);letter-spacing:1px;text-shadow:0 0 20px rgba(0,229,255,.4);">{UPI_ID}</span>
                <button class="copy-btn" onclick="copyUpi()" style="background:rgba(0,229,255,.15);border:1px solid rgba(0,229,255,.4);color:var(--cyan);padding:5px 12px;border-radius:8px;font-family:'JetBrains Mono',monospace;font-size:.7rem;cursor:pointer;transition:all .3s;">📋 Copy</button>
            </div>
            <div style="position:relative;width:180px;height:180px;margin:0 auto 14px;border-radius:14px;overflow:hidden;border:2px solid rgba(0,229,255,.3);">
                <img src="{qr_url}" alt="UPI QR Code" style="width:100%;height:100%;">
                <div style="position:absolute;left:0;right:0;height:3px;background:linear-gradient(90deg,transparent,var(--cyan),transparent);box-shadow:0 0 15px var(--cyan);animation:qrScan 2.5s ease-in-out infinite;"></div>
            </div>
            <p style="color:var(--dim);font-size:.78rem;margin-bottom:16px;">Scan QR or copy UPI ID · Pay <b style="color:var(--green);">₹{amount}</b></p>
            <button class="btn btn-green btn-block" onclick="showUpload()" style="animation:pulse 2s infinite;">✓ I've Paid — Submit Proof</button>
        </div>

        <!-- UPI Upload Form (hidden) -->
        <div id="upiUploadForm" style="display:none;margin-bottom:20px;">
            <form id="upiForm" action="/verify-upi" method="post" enctype="multipart/form-data" style="background:rgba(17,22,36,.6);border:1px solid var(--line);border-radius:14px;padding:22px 18px;">
                <div style="font-family:'JetBrains Mono',monospace;font-size:.82rem;color:var(--cyan);letter-spacing:2px;text-transform:uppercase;margin-bottom:16px;">📤 Submit Payment Proof</div>
                <input type="hidden" name="payment_type" value="{payment_type}">
                <input type="hidden" name="plan_key" value="{plan_key or ''}">
                <input type="hidden" name="amount" value="{amount}">
                <input type="hidden" name="credits" value="{credits}">
                <div class="field"><label>Your Name / UPI Sender Name</label><input type="text" name="sender_name" required placeholder="Name shown in UPI app"></div>
                <div class="field"><label>UTR Number (Transaction Ref)</label><input type="text" name="utr" required placeholder="e.g. 452178963012" maxlength="22"></div>
                <div class="field"><label>Payment Screenshot</label><input type="file" name="screenshot" accept="image/*" required onchange="previewSS(this)" style="padding:10px;"><img id="ssPreview" style="display:none;max-width:100%;border-radius:10px;margin-top:10px;border:1px solid var(--line);"></div>
                <button type="submit" class="btn btn-primary btn-block" onclick="return startUpiVerify()">🤖 Submit & AI Verify</button>
            </form>
        </div>

        <!-- Divider -->
        <div style="text-align:center;margin:24px 0;font-family:'JetBrains Mono',monospace;font-size:.68rem;color:var(--dim);letter-spacing:3px;text-transform:uppercase;position:relative;">
            <span style="background:rgba(10,13,20,.75);padding:0 16px;position:relative;z-index:1;">Or Pay by Card</span>
            <div style="position:absolute;top:50%;left:0;right:0;height:1px;background:var(--line);"></div>
        </div>

        <!-- Card Payment (secondary) -->
        <form id="payForm" action="/process-payment" method="post">
            <input type="hidden" name="payment_type" value="{payment_type}">
            <input type="hidden" name="plan_key" value="{plan_key or ''}">
            <input type="hidden" name="amount" value="{amount}">
            <input type="hidden" name="credits" value="{credits}">
            <div class="field"><label>Card Number</label><input type="text" name="card_number" placeholder="4242 4242 4242 4242" maxlength="19"></div>
            <div style="display:flex;gap:12px;">
                <div class="field" style="flex:1;"><label>Expiry</label><input type="text" name="expiry" placeholder="MM/YY" maxlength="5"></div>
                <div class="field" style="flex:1;"><label>CVV</label><input type="text" name="cvv" placeholder="123" maxlength="4"></div>
            </div>
            <button type="submit" class="btn btn-outline btn-block" onclick="return startPayment()">Pay ₹{amount} by Card</button>
        </form>
        {pm_html}
        <a href="/dashboard" style="display:block;text-align:center;margin-top:14px;font-family:'JetBrains Mono',monospace;font-size:.78rem;color:var(--dim);">Cancel</a>
    </div>

    <!-- Card Payment Animation -->
    <div class="pay-overlay" id="payOverlay">
        <div style="text-align:center;">
            <div class="pay-card-3d" id="payCard">
                <div class="chip"></div>
                <div class="card-num">4242 •••• •••• 4242</div>
                <div class="card-name">CIPHER SECURE PAY</div>
            </div>
            <div class="pay-spinner" id="paySpinner" style="display:none;"></div>
            <div class="pay-check" id="payCheck">
                <svg viewBox="0 0 52 52"><path class="check-path" d="M14 27 L22 35 L38 17"/></svg>
            </div>
            <div class="pay-status" id="payStatus">Authenticating...</div>
        </div>
    </div>

    <!-- UPI AI Verification Animation -->
    <div class="upi-verify-overlay" id="upiVerifyOverlay">
        <div style="text-align:center;">
            <div class="verify-scanner" id="verifyScanner" style="display:none;">
                <div class="scan-grid"></div>
            </div>
            <div class="verify-check" id="verifyCheck" style="display:none;width:80px;height:80px;margin:20px auto;border-radius:50%;background:rgba(0,255,156,.15);border:3px solid var(--green);align-items:center;justify-content:center;">
                <svg viewBox="0 0 52 52" style="width:40px;height:40px;"><path class="check-path" d="M14 27 L22 35 L38 17" style="stroke:var(--green);stroke-width:4;fill:none;stroke-dasharray:50;stroke-dashoffset:50;animation:drawCheck .5s ease .2s forwards;"/></svg>
            </div>
            <div class="verify-step" style="font-family:'JetBrains Mono',monospace;font-size:.85rem;letter-spacing:2px;color:var(--cyan);margin-top:16px;opacity:0;transition:opacity .3s;">🔍 Scanning Screenshot...</div>
            <div class="verify-step" style="font-family:'JetBrains Mono',monospace;font-size:.85rem;letter-spacing:2px;color:var(--cyan);margin-top:16px;opacity:0;transition:opacity .3s;">📋 Extracting UTR Number...</div>
            <div class="verify-step" style="font-family:'JetBrains Mono',monospace;font-size:.85rem;letter-spacing:2px;color:var(--cyan);margin-top:16px;opacity:0;transition:opacity .3s;">✓ Verifying Transaction...</div>
            <div class="verify-step" style="font-family:'JetBrains Mono',monospace;font-size:.85rem;letter-spacing:2px;color:var(--cyan);margin-top:16px;opacity:0;transition:opacity .3s;">✅ AI Verification Complete!</div>
        </div>
    </div>"""

    extra = f"""<style>
@keyframes qrScan {{ 0%,100% {{ top:0; }} 50% {{ top:calc(100% - 3px); }} }}
@keyframes pulse {{ 0%,100% {{ box-shadow:0 0 0 0 rgba(0,255,156,.4); }} 50% {{ box-shadow:0 0 0 8px rgba(0,255,156,0); }} }}
.pay-overlay,.upi-verify-overlay {{ position:fixed;inset:0;z-index:999;display:none;align-items:center;justify-content:center;background:rgba(5,6,10,.95);backdrop-filter:blur(20px); }}
.pay-overlay.active,.upi-verify-overlay.active {{ display:flex; }}
.verify-scanner {{ width:240px;height:240px;margin:0 auto 20px;position:relative;border-radius:16px;overflow:hidden;border:2px solid var(--cyan);background:rgba(0,229,255,.05); }}
.verify-scanner::before {{ content:'';position:absolute;left:0;right:0;height:4px;background:linear-gradient(90deg,transparent,var(--cyan),var(--magenta),transparent);box-shadow:0 0 20px var(--cyan);animation:qrScan 1.5s ease-in-out infinite; }}
.scan-grid {{ position:absolute;inset:0;background-image:linear-gradient(rgba(0,229,255,.1) 1px,transparent 1px),linear-gradient(90deg,rgba(0,229,255,.1) 1px,transparent 1px);background-size:20px 20px; }}
.verify-step.active {{ opacity:1 !important; }}
</style>
<script>{PAYMENT_JS}</script>"""
    return base_page(f"Cipher · Payment · ₹{amount}", body, user, extra)


# ── Invoice page ──────────────────────────────────────────────

def invoice_page(user, invoice):
    if not invoice:
        return base_page("Cipher · Error", '<div class="card"><div class="flash flash-error">Invoice not found.</div><a href="/dashboard" class="btn btn-outline">Back</a></div>', user)

    date_str = invoice['created_at']
    body = f"""
    <div class="invoice">
        <div class="invoice-head">
            <div>
                <div style="width:48px;height:48px;margin-bottom:10px;">{LOGO_SVG}</div>
                <div class="inv-brand">CIPHER</div>
                <div style="font-family:'JetBrains Mono',monospace;font-size:.68rem;color:var(--dim);letter-spacing:2px;margin-top:4px;">PRIVATE ACCESS ENGINE</div>
            </div>
            <div class="inv-meta">
                <div class="inv-num">{invoice['invoice_number']}</div>
                <div>{date_str}</div>
            </div>
        </div>
        <span class="invoice-paid">✓ PAID</span>
        <div class="invoice-section">
            <div class="label">Bill To</div>
            <div class="value">{invoice['user_name'] or invoice['email']}</div>
            <div class="value" style="color:var(--dim);font-size:.78rem;">{invoice['email']}</div>
        </div>
        <table class="invoice-table">
            <thead><tr><th>Description</th><th style="text-align:right;">Amount</th></tr></thead>
            <tbody><tr><td>{invoice['details']}</td><td style="text-align:right;color:var(--green);font-weight:700;">₹{invoice['amount']}</td></tr></tbody>
        </table>
        <div class="invoice-total">
            <span class="total-label">Total Paid</span>
            <span class="total-amount">₹{invoice['amount']}</span>
        </div>
        <div class="invoice-sign">
            <div class="sign-label">Authorized Signature</div>
            <div class="sign-name">chirag</div>
            <div class="sign-title">CIPHER · ADMIN</div>
        </div>
        <div style="text-align:center;margin-top:28px;">
            <button onclick="window.print()" class="btn btn-outline btn-sm">🖨 Print / Save PDF</button>
            <a href="/dashboard" class="btn btn-outline btn-sm" style="margin-left:8px;">Back to Dashboard</a>
        </div>
    </div>"""
    return base_page(f"Cipher · Invoice · {invoice['invoice_number']}", body, user)


# ── Admin panel ───────────────────────────────────────────────

def admin_page(user, stats, users, payments, gift_cards, invoices, payment_methods, upi_payments, flash=None):
    flash_html = ''
    if flash:
        cls = 'flash-ok' if flash.startswith('ok:') else 'flash-error'
        flash_html = f'<div class="flash {cls}">{flash[3:] if flash[3:] else flash}</div>'

    # Stats
    stats_html = f"""
    <div class="stats-grid">
        <div class="stat-card cyan"><div class="stat-label">Users</div><div class="stat-value">{stats['users']}</div></div>
        <div class="stat-card green"><div class="stat-label">Revenue</div><div class="stat-value">₹{stats['revenue']}</div></div>
        <div class="stat-card magenta"><div class="stat-label">Payments</div><div class="stat-value">{stats['payments']}</div></div>
        <div class="stat-card gold"><div class="stat-label">Active Cards</div><div class="stat-value">{stats['active_cards']}</div></div>
    </div>"""

    # Gift card creation
    gift_create = f"""
    <div class="card">
        <h2>🎁 Create Gift Card</h2>
        {flash_html}
        <form action="/admin/create-giftcard" method="post" style="display:flex;gap:12px;flex-wrap:wrap;align-items:flex-end;">
            <div class="field" style="flex:1;min-width:160px;margin-bottom:0;">
                <label>Credit Value</label>
                <input type="number" name="value" placeholder="e.g. 10" min="1" max="999" required>
            </div>
            <button type="submit" class="btn btn-green">Generate</button>
        </form>
    </div>"""

    # UPI Payment Verifications
    upi_rows = ''
    for up in upi_payments:
        ai = up['ai_recommendation']
        if ai == 'verified':
            ai_badge = f'<span style="color:var(--green);font-weight:700;">✓ Verified ({up["ai_confidence"]}%)</span>'
        elif ai == 'suspicious':
            ai_badge = f'<span style="color:var(--gold);font-weight:700;">⚠ Suspicious ({up["ai_confidence"]}%)</span>'
        elif ai == 'rejected':
            ai_badge = f'<span style="color:var(--red);font-weight:700;">✕ Rejected</span>'
        else:
            ai_badge = '<span style="color:var(--dim);">Manual review</span>'

        if up['status'] == 'pending':
            status_badge = '<span class="tag tag-active" style="background:rgba(255,215,0,.12);border:1px solid rgba(255,215,0,.4);color:var(--gold);">Pending</span>'
            actions = f"""
                <form action="/admin/verify-upi" method="post" style="display:inline;">
                    <input type="hidden" name="payment_id" value="{up['id']}">
                    <button type="submit" class="btn btn-sm btn-green" style="padding:6px 12px;font-size:.68rem;">✓ Approve</button>
                </form>
                <form action="/admin/reject-upi" method="post" style="display:inline;margin-left:4px;">
                    <input type="hidden" name="payment_id" value="{up['id']}">
                    <button type="submit" class="btn btn-sm" style="padding:6px 12px;font-size:.68rem;background:rgba(255,56,96,.15);color:var(--red);border:1px solid rgba(255,56,96,.3);">✕ Reject</button>
                </form>"""
        elif up['status'] == 'verified':
            status_badge = '<span class="tag tag-active">Verified</span>'
            actions = ''
        else:
            status_badge = '<span class="tag tag-redeemed">Rejected</span>'
            actions = ''

        ss_link = f'<a href="/screenshot?name={up["screenshot_path"]}" target="_blank" style="color:var(--cyan);">📷 View</a>' if up['screenshot_path'] else '—'
        ai_reason = f'<br><span style="font-size:.68rem;color:var(--dim);">{up["ai_reason"][:60]}</span>' if up['ai_reason'] else ''

        upi_rows += f"""<tr>
            <td style="font-size:.75rem;">{up['user_name'] or up['email']}<br><span style="font-size:.68rem;color:var(--dim);">{up['sender_name']}</span></td>
            <td>₹{up['amount']}<br><span style="font-size:.68rem;color:var(--cyan);">{up['credits']} cr</span></td>
            <td style="font-size:.72rem;">{up['utr']}</td>
            <td>{ss_link}</td>
            <td style="font-size:.72rem;">{ai_badge}{ai_reason}</td>
            <td>{status_badge}</td>
            <td>{actions}</td>
        </tr>"""

    upi_section = f"""
    <div class="card">
        <h2>🤖 UPI Payment Verifications</h2>
        <p style="color:var(--dim);font-size:.82rem;margin-bottom:18px;">AI analyzes each screenshot and suggests approve/reject. Admin makes the final call.</p>
        <div class="table-wrap"><table>
            <thead><tr><th>User / Sender</th><th>Amount</th><th>UTR</th><th>SS</th><th>AI Analysis</th><th>Status</th><th>Action</th></tr></thead>
            <tbody>{upi_rows if upi_rows else '<tr><td colspan="7" style="text-align:center;color:var(--dim);">No UPI payments yet</td></tr>'}</tbody>
        </table></div>
    </div>"""

    # Add credits to user
    user_options = ''
    for u in users:
        user_options += f'<option value="{u["id"]}">{u["name"]} — {u["email"]} ({u["credits"]} cr)</option>'

    add_credits = f"""
    <div class="card">
        <h2>⚡ Add Credits to User</h2>
        <form action="/admin/add-credits" method="post" style="display:flex;gap:12px;flex-wrap:wrap;align-items:flex-end;">
            <div class="field" style="flex:2;min-width:200px;margin-bottom:0;">
                <label>Select User</label>
                <select name="user_id" required style="width:100%;padding:14px 16px;background:rgba(5,6,10,.8);border:1px solid var(--line);border-radius:10px;color:var(--text);font-family:'JetBrains Mono',monospace;font-size:.85rem;">
                    {user_options}
                </select>
            </div>
            <div class="field" style="flex:1;min-width:120px;margin-bottom:0;">
                <label>Credits</label>
                <input type="number" name="amount" placeholder="e.g. 50" min="1" required>
            </div>
            <button type="submit" class="btn btn-primary">Add Credits</button>
        </form>
    </div>"""

    # Payment methods management
    pm_rows = ''
    for pm in payment_methods:
        pm_rows += f"""<tr>
            <td>{pm['icon']} {pm['name']}</td>
            <td style="font-size:.75rem;color:var(--dim);">{pm['details']}</td>
            <td>{pm['created_at']}</td>
            <td>
                <form action="/admin/delete-payment-method" method="post" style="display:inline;">
                    <input type="hidden" name="method_id" value="{pm['id']}">
                    <button type="submit" class="btn btn-sm" style="background:rgba(255,56,96,.15);color:var(--red);border:1px solid rgba(255,56,96,.3);">Delete</button>
                </form>
            </td>
        </tr>"""

    payment_methods_section = f"""
    <div class="card">
        <h2>💳 Payment Methods</h2>
        <p style="color:var(--dim);font-size:.82rem;margin-bottom:18px;">Add any payment method you want — UPI, bank transfer, crypto, etc. Users will see these on the payment page.</p>
        <form action="/admin/add-payment-method" method="post" style="display:flex;gap:12px;flex-wrap:wrap;align-items:flex-end;margin-bottom:20px;">
            <div class="field" style="flex:1;min-width:100px;margin-bottom:0;">
                <label>Icon</label>
                <input type="text" name="icon" placeholder="💳" maxlength="4" value="💳" style="text-align:center;">
            </div>
            <div class="field" style="flex:2;min-width:140px;margin-bottom:0;">
                <label>Method Name</label>
                <input type="text" name="name" placeholder="e.g. UPI / PhonePe" required>
            </div>
            <div class="field" style="flex:3;min-width:200px;margin-bottom:0;">
                <label>Details (UPI ID / Number / Link)</label>
                <input type="text" name="details" placeholder="e.g. chirag@upi" required>
            </div>
            <button type="submit" class="btn btn-green">Add Method</button>
        </form>
        <div class="table-wrap"><table>
            <thead><tr><th>Method</th><th>Details</th><th>Added</th><th></th></tr></thead>
            <tbody>{pm_rows if pm_rows else '<tr><td colspan="4" style="text-align:center;color:var(--dim);">No custom payment methods yet. Add UPI, bank transfer, etc.</td></tr>'}</tbody>
        </table></div>
    </div>"""

    # Gift cards table
    cards_rows = ''
    for gc in gift_cards:
        tag = '<span class="tag tag-active">Active</span>' if gc['status'] == 'active' else '<span class="tag tag-redeemed">Redeemed</span>'
        cards_rows += f"<tr><td>{gc['code']}</td><td>{gc['value']}</td><td>{tag}</td><td>{gc['created_at']}</td></tr>"

    gift_table = f"""
    <div class="card">
        <h2>🎁 Gift Cards</h2>
        <div class="table-wrap"><table>
            <thead><tr><th>Code</th><th>Credits</th><th>Status</th><th>Created</th></tr></thead>
            <tbody>{cards_rows if cards_rows else '<tr><td colspan="4" style="text-align:center;color:var(--dim);">No gift cards yet</td></tr>'}</tbody>
        </table></div>
    </div>"""

    # Users table
    users_rows = ''
    for u in users:
        role = '<span class="tag tag-active">Admin</span>' if u['is_admin'] else '<span class="tag tag-redeemed">User</span>'
        users_rows += f"<tr><td>{u['name']}</td><td>{u['email']}</td><td>{u['credits']}</td><td>{role}</td><td>{u['created_at']}</td></tr>"

    users_table = f"""
    <div class="card">
        <h2>👥 Users</h2>
        <div class="table-wrap"><table>
            <thead><tr><th>Name</th><th>Email</th><th>Credits</th><th>Role</th><th>Joined</th></tr></thead>
            <tbody>{users_rows}</tbody>
        </table></div>
    </div>"""

    # Payments table
    pay_rows = ''
    for p in payments:
        pay_rows += f"<tr><td>{p['email']}</td><td>₹{p['amount']}</td><td>{p['payment_type']}</td><td>{p['credits']} cr</td><td>{p['created_at']}</td></tr>"

    pay_table = f"""
    <div class="card">
        <h2>💳 Payments</h2>
        <div class="table-wrap"><table>
            <thead><tr><th>User</th><th>Amount</th><th>Type</th><th>Credits</th><th>Date</th></tr></thead>
            <tbody>{pay_rows if pay_rows else '<tr><td colspan="5" style="text-align:center;color:var(--dim);">No payments yet</td></tr>'}</tbody>
        </table></div>
    </div>"""

    # Invoices table
    inv_rows = ''
    for inv in invoices:
        inv_rows += f"<tr><td>{inv['invoice_number']}</td><td>{inv['email']}</td><td>₹{inv['amount']}</td><td>{inv['created_at']}</td></tr>"

    inv_table = f"""
    <div class="card">
        <h2>🧾 Invoices</h2>
        <div class="table-wrap"><table>
            <thead><tr><th>Invoice #</th><th>User</th><th>Amount</th><th>Date</th></tr></thead>
            <tbody>{inv_rows if inv_rows else '<tr><td colspan="4" style="text-align:center;color:var(--dim);">No invoices yet</td></tr>'}</tbody>
        </table></div>
    </div>"""

    body = stats_html + upi_section + add_credits + payment_methods_section + gift_create + gift_table + users_table + pay_table + inv_table
    return base_page("Cipher · Admin Panel", body, user)


# ── Analytics dashboard ──────────────────────────────────────

def analytics_page(user, summary, rows):
    # Overall stat cards
    stats_html = f"""
    <div class="stats-grid">
        <div class="stat-card cyan"><div class="stat-label">Total Searches</div><div class="stat-value">{summary['searches']}</div></div>
        <div class="stat-card magenta"><div class="stat-label">Total Downloads</div><div class="stat-value">{summary['downloads']}</div></div>
        <div class="stat-card green"><div class="stat-label">Active Users</div><div class="stat-value">{summary['active_users']}</div></div>
    </div>"""

    # Per-user table
    user_rows_html = ''
    for r in rows:
        total = r['searches'] + r['downloads']
        user_rows_html += f"""<tr>
            <td>{r['name']}</td>
            <td style="font-size:.75rem;color:var(--dim);">{r['email']}</td>
            <td style="color:var(--cyan);font-weight:700;">{r['searches']}</td>
            <td style="color:var(--magenta);font-weight:700;">{r['downloads']}</td>
            <td style="color:var(--green);font-weight:700;">{total}</td>
        </tr>"""

    table_html = f"""
    <div class="card">
        <h2>📊 Per-User Activity</h2>
        <div class="table-wrap"><table>
            <thead><tr><th>User</th><th>Email</th><th>Searches</th><th>Downloads</th><th>Total</th></tr></thead>
            <tbody>{user_rows_html if user_rows_html else '<tr><td colspan="5" style="text-align:center;color:var(--dim);">No activity recorded yet</td></tr>'}</tbody>
        </table></div>
    </div>"""

    body = stats_html + table_html
    return base_page("Cipher · Analytics", body, user)
