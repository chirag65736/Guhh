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
    padding: 0; font-weight: bold; font-style: italic;
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
.plan-card li::before { content: '✔'; position: absolute; left: 0; color: var(--green); font-weight: 700; }
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
/* reviews */
.reviews-grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(250px,1fr)); gap:18px; }
.review-card {
    background:rgba(17,22,36,.8); border:1px solid var(--line); border-radius:14px;
    padding:22px 18px; transition:all .3s;
}
.review-card:hover { border-color:var(--cyan); transform:translateY(-3px); box-shadow:0 10px 40px rgba(0,229,255,.12); }
.review-stars { font-size:.8rem; letter-spacing:2px; margin-bottom:12px; }
.review-text { color:var(--text); font-size:.82rem; line-height:1.6; margin-bottom:16px; }
.review-user { display:flex; align-items:center; gap:10px; }
.review-avatar {
    width:36px; height:36px; border-radius:50%; display:flex; align-items:center; justify-content:center;
    font-family:'JetBrains Mono',monospace; font-size:.85rem; font-weight:800; color:#05060a;
}
.review-name { font-family:'JetBrains Mono',monospace; font-size:.78rem; color:var(--cyan); letter-spacing:1px; }
/* star rating picker */
.star-rating { display:flex; gap:6px; font-size:1.8rem; }
.star-rating .star { cursor:pointer; color:var(--dim); transition:color .2s,transform .2s; user-select:none; }
.star-rating .star.active { color:var(--gold); text-shadow:0 0 10px rgba(255,215,0,.4); }
.star-rating .star:hover { transform:scale(1.2); }
textarea { width:100%; padding:14px 16px; background:rgba(5,6,10,.8); border:1px solid var(--line); border-radius:10px; color:var(--text); font-family:'JetBrains Mono',monospace; font-size:.9rem; outline:none; transition:border-color .3s,box-shadow .3s; resize:vertical; }
textarea:focus { border-color:var(--cyan); box-shadow:0 0 0 3px rgba(0,229,255,.12); }
/* mobile nav toggle */
.nav-toggle {
    display: none; background: none; border: none; cursor: pointer;
    padding: 6px; z-index: 11;
}
.nav-toggle span {
    display: block; width: 24px; height: 2px; background: var(--cyan);
    border-radius: 2px; transition: all .3s;
}
.nav-toggle span + span { margin-top: 5px; }
.nav-toggle.open span:nth-child(1) { transform: rotate(45deg) translate(5px, 5px); }
.nav-toggle.open span:nth-child(2) { opacity: 0; }
.nav-toggle.open span:nth-child(3) { transform: rotate(-45deg) translate(6px, -6px); }
/* responsive */
@media (max-width: 768px) {
    .nav { padding: 12px 16px; flex-wrap: wrap; }
    .nav-brand .name { font-size: 1.1rem; letter-spacing: 2px; }
    .nav-brand .logo { width: 32px; height: 32px; }
    .nav-toggle { display: block; }
    .nav-links {
        display: none; flex-direction: column; width: 100%;
        gap: 0; padding: 8px 0 0; margin-top: 10px;
        border-top: 1px solid var(--line);
    }
    .nav-links.open { display: flex; }
    .nav-links a, .nav-links span {
        padding: 12px 4px; font-size: .82rem; border-bottom: 1px solid rgba(0,229,255,.06);
    }
    .nav-credits { align-self: flex-start; }
    .nav-logout { align-self: flex-start; }
    .page { padding: 16px 12px; }
    .card { padding: 20px 16px; border-radius: 14px; margin-bottom: 16px; }
    .card h2 { font-size: 1rem; }
    .btn { padding: 12px 20px; font-size: .78rem; letter-spacing: 1px; }
    .btn-block { width: 100%; }
    .plans-grid { grid-template-columns: 1fr; gap: 14px; }
    .plan-card { padding: 22px 18px; }
    .plan-card .plan-price { font-size: 1.8rem; }
    .stats-grid { grid-template-columns: repeat(2, 1fr); gap: 12px; }
    .stat-card { padding: 16px 12px; }
    .stat-card .stat-value { font-size: 1.4rem; }
    .invoice { padding: 24px 16px; border-radius: 14px; }
    .invoice-head { flex-direction: column; gap: 14px; }
    .invoice-head .inv-meta { text-align: left; }
    .invoice-sign .sign-name { font-size: 2rem; }
    .invoice-total .total-amount { font-size: 1.3rem; }
    form { width: 100%; }
    form[style*="display:flex"] { flex-direction: column; }
    form[style*="display:flex"] > * { width: 100% !important; }
    form[style*="display:flex"] .btn { margin-top: 8px; }
    .field { width: 100%; }
    input[type="text"], input[type="email"], input[type="password"], input[type="number"] {
        font-size: .9rem; padding: 12px 14px;
    }
    table { font-size: .72rem; }
    th, td { padding: 8px 6px; }
    .made-by { padding: 16px 12px; font-size: .68rem; }
    .reviews-grid { grid-template-columns: 1fr; gap: 14px; }
    .review-card { padding: 18px 14px; }
    .pay-card-3d { width: 280px; height: 180px; }
    .upi-qr-frame { width: 180px; height: 180px; }
    .upi-qr-inner { width: 150px; height: 150px; }
    .upi-pulse-ring { width: 180px; height: 180px; }
    .upi-coin-path { max-width: 80px; }
    .scan-steps { max-width: 100%; }
    .radar { width: 170px; height: 170px; }
}
@media (max-width: 380px) {
    .nav-brand .name { font-size: 1rem; }
    .card { padding: 16px 12px; }
    .btn { padding: 10px 16px; font-size: .72rem; }
    .stats-grid { grid-template-columns: 1fr; }
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

# ── Custom Credit Icons (unique to CIPHER) ─────────────────────

CREDIT_ICON = '<svg viewBox="0 0 24 24" width="1em" height="1em" fill="none" xmlns="http://www.w3.org/2000/svg" style="display:inline-block;vertical-align:middle;"><defs><linearGradient id="cgrd1" x1="0" y1="0" x2="24" y2="24"><stop offset="0" stop-color="#00e5ff"/><stop offset="1" stop-color="#ff2bd6"/></linearGradient></defs><circle cx="12" cy="12" r="11" fill="rgba(0,229,255,.08)" stroke="url(#cgrd1)" stroke-width="1.5"/><path d="M12 5 L17 8.5 V15.5 L12 19 L7 15.5 V8.5 Z" fill="none" stroke="url(#cgrd1)" stroke-width="1.2"/><path d="M14.5 9 A3.5 3.5 0 1 0 14.5 15" stroke="url(#cgrd1)" stroke-width="1.8" stroke-linecap="round" fill="none"/><circle cx="12" cy="12" r="1.5" fill="url(#cgrd1)"/></svg>'

SCAN_ICON = '<svg viewBox="0 0 24 24" width="1em" height="1em" fill="none" xmlns="http://www.w3.org/2000/svg" style="display:inline-block;vertical-align:middle;"><defs><linearGradient id="sgrd1" x1="0" y1="0" x2="24" y2="24"><stop offset="0" stop-color="#00e5ff"/><stop offset="1" stop-color="#00ff9c"/></linearGradient></defs><circle cx="12" cy="12" r="11" fill="rgba(0,255,156,.06)" stroke="url(#sgrd1)" stroke-width="1.5"/><path d="M12 5 L17 8.5 V15.5 L12 19 L7 15.5 V8.5 Z" fill="none" stroke="url(#sgrd1)" stroke-width="1.2"/><circle cx="12" cy="12" r="4.5" fill="none" stroke="url(#sgrd1)" stroke-width="1.2" stroke-dasharray="2 2"/><path d="M12 7.5 V12 L15 14" stroke="url(#sgrd1)" stroke-width="1.6" stroke-linecap="round" fill="none"/></svg>'

DEEP_ICON = '<svg viewBox="0 0 24 24" width="1em" height="1em" fill="none" xmlns="http://www.w3.org/2000/svg" style="display:inline-block;vertical-align:middle;"><defs><linearGradient id="dgrd1" x1="0" y1="0" x2="24" y2="24"><stop offset="0" stop-color="#ff2bd6"/><stop offset="1" stop-color="#7c3aed"/></linearGradient></defs><circle cx="12" cy="12" r="11" fill="rgba(255,43,214,.06)" stroke="url(#dgrd1)" stroke-width="1.5"/><path d="M12 5 L17 8.5 V15.5 L12 19 L7 15.5 V8.5 Z" fill="none" stroke="url(#dgrd1)" stroke-width="1.2"/><circle cx="10" cy="10" r="3.5" fill="none" stroke="url(#dgrd1)" stroke-width="1.6"/><path d="M12.5 12.5 L16 16" stroke="url(#dgrd1)" stroke-width="1.8" stroke-linecap="round"/></svg>'

# ── Reviews section (reusable, shown at bottom of pages) ──────

REVIEW_JS = """
<script>
(function() {
    var stars = document.querySelectorAll('#starRating .star');
    var ratingValue = document.getElementById('ratingValue');
    if (!stars.length) return;
    stars.forEach(function(s) { s.classList.add('active'); });
    stars.forEach(function(s) {
        s.addEventListener('click', function() {
            var val = parseInt(this.getAttribute('data-val'));
            ratingValue.value = val;
            stars.forEach(function(s2) {
                if (parseInt(s2.getAttribute('data-val')) <= val) { s2.classList.add('active'); }
                else { s2.classList.remove('active'); }
            });
        });
    });
})();
</script>"""


def reviews_section(reviews, user=None):
    cards = ''
    for r in reviews:
        stars_filled = '\u2605' * r['rating']
        stars_empty = '\u2606' * (5 - r['rating'])
        initial = (r['name'] or 'U')[0].upper()
        cards += f"""
            <div class="review-card">
                <div class="review-stars">{stars_filled}{stars_empty}</div>
                <p class="review-text">"{r['text']}"</p>
                <div class="review-user"><span class="review-avatar" style="background:linear-gradient(135deg,#00e5ff,#7c3aed);">{initial}</span><span class="review-name">@{r['name']}</span></div>
            </div>"""
    default_name = user['name'] if user else ''
    return f"""
    <div class="card" style="margin-top:24px;">
        <h2 style="text-align:center;">\U0001F4AC User Reviews</h2>
        <p style="text-align:center;color:var(--dim);font-size:.82rem;margin-bottom:24px;">\u2B50\u2B50\u2B50\u2B50\u2B50 Trusted by 2,400+ users</p>
        <div style="text-align:center;margin-bottom:24px;">
            <button class="btn btn-outline" onclick="var f=document.getElementById('reviewForm');f.style.display=f.style.display=='none'?'block':'none';">\u270D Add Review</button>
        </div>
        <form id="reviewForm" action="/submit-review" method="post" style="display:none;max-width:440px;margin:0 auto 28px;background:rgba(17,22,36,.8);border:1px solid var(--line);border-radius:14px;padding:22px 18px;">
            <div class="field"><label>Your Name</label><input type="text" name="name" required placeholder="Your name" value="{default_name}"></div>
            <div class="field"><label>Rating</label>
                <div class="star-rating" id="starRating">
                    <span class="star" data-val="1">\u2605</span>
                    <span class="star" data-val="2">\u2605</span>
                    <span class="star" data-val="3">\u2605</span>
                    <span class="star" data-val="4">\u2605</span>
                    <span class="star" data-val="5">\u2605</span>
                    <input type="hidden" name="rating" id="ratingValue" value="5">
                </div>
            </div>
            <div class="field"><label>Review</label><textarea name="text" required placeholder="Write your review..." rows="3"></textarea></div>
            <button type="submit" class="btn btn-primary btn-block">Submit Review</button>
        </form>
        <div class="reviews-grid">{cards}</div>
    </div>
    {REVIEW_JS}"""


# ── Nav bar ───────────────────────────────────────────────────

def nav_bar(user=None):
    if user:
        links = f'<a href="/dashboard">Dashboard</a>'
        if user['is_admin']:
            links += '<a href="/admin">Admin Panel</a>'
            links += '<a href="/analytics">Analytics</a>'
        links += f'<span class="nav-credits">{CREDIT_ICON} {user["credits"]} Credits</span>'
        links += '<a href="/logout" class="nav-logout">Logout</a>'
    else:
        links = '<a href="/login">Login</a><a href="/signup">Sign Up</a>'
    return f"""
    <nav class="nav">
        <a href="/" class="nav-brand">
            <div class="logo">{LOGO_SVG}</div>
            <span class="name">CIPHER</span>
        </a>
        <button class="nav-toggle" onclick="var n=this.parentElement.querySelector('.nav-links');n.classList.toggle('open');this.classList.toggle('open');"><span></span><span></span><span></span></button>
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
    <div class="made-by">Made with 💖 by <span class="mb-name">ii_silkroad_ii</span> · <a href="/terms" style="color:var(--dim);text-decoration:none;font-style:normal;font-weight:normal;">Terms &amp; Conditions</a></div>
</body>
</html>"""


# ── Landing page ──────────────────────────────────────────────

def landing_page(user=None, reviews=None):
    if user:
        return dashboard_page(user, reviews=reviews)
    body = f"""
    <div class="card" style="text-align:center;">
        <div style="margin:0 auto 20px;width:80px;height:80px;">{LOGO_SVG}</div>
        <h1 style="font-family:'JetBrains Mono',monospace;font-size:2.4rem;font-weight:800;letter-spacing:4px;background:linear-gradient(90deg,var(--cyan),var(--magenta));-webkit-background-clip:text;background-clip:text;-webkit-text-fill-color:transparent;margin-bottom:8px;">CIPHER</h1>
        <p style="font-family:'JetBrains Mono',monospace;font-size:.78rem;color:var(--dim);letter-spacing:6px;text-transform:uppercase;margin-bottom:24px;">Private Access Engine v2.0</p>
        <p style="color:var(--dim);font-size:.95rem;margin-bottom:32px;max-width:420px;margin-left:auto;margin-right:auto;">Extract high-resolution Instagram post images. Pay per username or choose a monthly plan. Premium access, premium results.</p>
        <div style="display:flex;gap:14px;justify-content:center;flex-wrap:wrap;">
            <a href="/login" class="btn btn-primary">💠 Login</a>
            <a href="/signup" class="btn btn-outline">Sign Up</a>
        </div>
        <div style="margin-top:32px;padding-top:24px;border-top:1px solid var(--line);">
            <div style="display:flex;gap:20px;justify-content:center;flex-wrap:wrap;">
                <span style="font-family:'JetBrains Mono',monospace;font-size:.72rem;color:var(--green);letter-spacing:1px;">✔ ₹15 / Post</span>
                <span style="font-family:'JetBrains Mono',monospace;font-size:.72rem;color:var(--green);letter-spacing:1px;">✔ Monthly Plans</span>
                <span style="font-family:'JetBrains Mono',monospace;font-size:.72rem;color:var(--green);letter-spacing:1px;">✔ Gift Cards</span>
                <span style="font-family:'JetBrains Mono',monospace;font-size:.72rem;color:var(--green);letter-spacing:1px;">✔ Invoices</span>
            </div>
        </div>
    </div>

    {reviews_section(reviews or [])}"""
    return base_page("Cipher · Private Access", body, user)


# ── Login ─────────────────────────────────────────────────────

def login_page(error=None):
    flash = f'<div class="flash flash-error">{error}</div>' if error else ''
    body = f"""
    <div class="card" style="max-width:440px;margin:0 auto;">
        <h2>💠 Login</h2>
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


# ── Terms & Conditions ────────────────────────────────────────

def terms_page(user=None):
    body = """
    <div class="card" style="max-width:720px;margin:0 auto;">
        <h2>📖 Terms &amp; Conditions</h2>
        <div style="color:var(--text);font-size:.88rem;line-height:1.8;">
            <p style="margin-bottom:16px;"><b><i>Welcome to CIPHER.</i></b> By using this website you agree to the following terms and conditions. Please read them carefully.</p>

            <p style="margin-bottom:12px;"><b><i>1. Service Description.</i></b> CIPHER is a private access engine that allows users to extract and view high-resolution Instagram post images. Credits are required for each scan.</p>

            <p style="margin-bottom:12px;"><b><i>2. Credits &amp; Payments.</i></b> Quick Scan costs 1 credit per execution. Private Deep Scan costs 2 credits per execution. Credits can be purchased individually or via monthly plans. All payments are non-refundable once credits are added to your account.</p>

            <p style="margin-bottom:12px;"><b><i>3. Acceptable Use.</i></b> You agree to use this service for lawful purposes only. You must not misuse the service to harass, stalk, or harm any individual. You are solely responsible for how you use the extracted content.</p>

            <p style="margin-bottom:12px;"><b><i>4. No Guarantee of Results.</i></b> Instagram actively blocks automated access. Some profiles may not be accessible due to privacy settings, rate limiting, or IP restrictions. CIPHER does not guarantee successful extraction for every profile.</p>

            <p style="margin-bottom:12px;"><b><i>5. Privacy.</i></b> Your email and payment information are stored securely. Payment screenshots are kept private and accessible only to administrators for verification purposes.</p>

            <p style="margin-bottom:12px;"><b><i>6. Account Security.</i></b> You are responsible for keeping your account credentials safe. Do not share your login with others. CIPHER is not liable for unauthorized access to your account.</p>

            <p style="margin-bottom:12px;"><b><i>7. UPI Payments.</i></b> UPI payments are verified using AI-assisted analysis and/or manual admin review. Submitting false or fraudulent payment proof will result in account suspension.</p>

            <p style="margin-bottom:12px;"><b><i>8. Modification of Terms.</i></b> CIPHER reserves the right to update these terms at any time. Continued use of the service after changes constitutes acceptance of the updated terms.</p>

            <p style="margin-bottom:12px;"><b><i>9. Limitation of Liability.</i></b> CIPHER and its operators are not liable for any damages arising from the use or inability to use this service. The service is provided "as is" without warranties of any kind.</p>

            <p style="margin-bottom:12px;"><b><i>10. Contact.</i></b> For any questions regarding these terms, reach out via Instagram: <a href="https://instagram.com/ii_silkroad_ii" target="_blank" style="color:var(--cyan);">@ii_silkroad_ii</a></p>

            <p style="margin-top:20px;color:var(--dim);font-size:.78rem;">Last updated: October 2026</p>
        </div>
        <div style="margin-top:24px;text-align:center;">
            <a href="/dashboard" class="btn btn-primary">Back to Dashboard</a>
        </div>
    </div>"""
    return base_page("Cipher · Terms & Conditions", body, user)


# ── Welcome intro (shown after signup) ─────────────────────────

INTRO_CSS = """
.intro-wrap { max-width:480px; margin:0 auto; position:relative; overflow:hidden; }
.intro-track { display:flex; transition:transform .5s cubic-bezier(.4,0,.2,1); }
.intro-slide {
    min-width:100%; padding:8px 4px; text-align:center;
    opacity:0; transition:opacity .4s ease;
}
.intro-slide.active { opacity:1; }
.intro-icon-wrap {
    width:100px; height:100px; margin:0 auto 24px;
    display:flex; align-items:center; justify-content:center;
    border-radius:50%; border:1px solid var(--line);
    background:rgba(17,22,36,.8); position:relative;
}
.intro-icon-wrap::after {
    content:''; position:absolute; inset:-4px; border-radius:50%;
    border:1px solid rgba(0,229,255,.15); animation:introPulse 2s ease infinite;
}
@keyframes introPulse { 0%,100%{transform:scale(1);opacity:.6;} 50%{transform:scale(1.1);opacity:0;} }
.intro-icon-wrap svg { width:48px; height:48px; }
.intro-icon-emoji { font-size:2.8rem; }
.intro-step-num {
    font-family:'JetBrains Mono',monospace; font-size:.68rem; color:var(--dim);
    letter-spacing:4px; text-transform:uppercase; margin-bottom:10px;
}
.intro-title {
    font-family:'JetBrains Mono',monospace; font-size:1.4rem; font-weight:800;
    letter-spacing:2px; margin-bottom:14px;
}
.intro-desc {
    color:var(--dim); font-size:.88rem; line-height:1.7; max-width:340px; margin:0 auto 20px;
}
.intro-desc b { color:var(--text); }
.intro-dots { display:flex; gap:8px; justify-content:center; margin:24px 0; }
.intro-dot {
    width:8px; height:8px; border-radius:50%; background:rgba(0,229,255,.2);
    cursor:pointer; transition:all .3s;
}
.intro-dot.active { width:28px; border-radius:4px; background:var(--cyan); box-shadow:0 0 10px rgba(0,229,255,.4); }
.intro-nav { display:flex; gap:12px; justify-content:center; align-items:center; }
.intro-link {
    font-family:'JetBrains Mono',monospace; font-size:.78rem; color:var(--dim);
    text-decoration:none; letter-spacing:1px; cursor:pointer; transition:color .3s;
}
.intro-link:hover { color:var(--cyan); }
"""

INTRO_JS = """
<script>
(function() {
    var slides = document.querySelectorAll('.intro-slide');
    var dots = document.querySelectorAll('.intro-dot');
    var track = document.getElementById('introTrack');
    var btnNext = document.getElementById('introNext');
    var btnPrev = document.getElementById('introPrev');
    var btnSkip = document.getElementById('introSkip');
    var btnFinish = document.getElementById('introFinish');
    var current = 0;
    var total = slides.length;

    function go(idx) {
        current = Math.max(0, Math.min(idx, total - 1));
        track.style.transform = 'translateX(-' + (current * 100) + '%)';
        slides.forEach(function(s, i) { s.classList.toggle('active', i === current); });
        dots.forEach(function(d, i) { d.classList.toggle('active', i === current); });
        btnPrev.style.visibility = current === 0 ? 'hidden' : 'visible';
        if (current === total - 1) {
            btnNext.style.display = 'none';
            btnFinish.style.display = 'inline-block';
        } else {
            btnNext.style.display = 'inline-block';
            btnFinish.style.display = 'none';
        }
    }

    btnNext.addEventListener('click', function() { go(current + 1); });
    btnPrev.addEventListener('click', function() { go(current - 1); });
    dots.forEach(function(d, i) { d.addEventListener('click', function() { go(i); }); });
    btnSkip.addEventListener('click', function() { window.location.href = '/dashboard'; });
    btnFinish.addEventListener('click', function() { window.location.href = '/dashboard'; });

    go(0);
})();
</script>"""


def welcome_page(user):
    name = user['name']
    body = f"""
    <div class="card" style="max-width:520px;margin:0 auto;">
        <div class="intro-wrap">
            <div class="intro-track" id="introTrack">

                <!-- Slide 1: Welcome -->
                <div class="intro-slide active">
                    <div class="intro-icon-wrap">{LOGO_SVG}</div>
                    <div class="intro-step-num">Step 1 of 5</div>
                    <div class="intro-title" style="background:linear-gradient(90deg,var(--cyan),var(--magenta));-webkit-background-clip:text;background-clip:text;-webkit-text-fill-color:transparent;">Welcome, {name}!</div>
                    <p class="intro-desc">Your <b>CIPHER</b> account is ready. This quick tour will show you how everything works in under a minute.</p>
                </div>

                <!-- Slide 2: Quick Scan -->
                <div class="intro-slide">
                    <div class="intro-icon-wrap"><span class="intro-icon-emoji" style="font-size:1.6rem;display:flex;align-items:center;justify-content:center;">{SCAN_ICON}</span></div>
                    <div class="intro-step-num">Step 2 of 5</div>
                    <div class="intro-title" style="color:var(--cyan);">Quick Scan</div>
                    <p class="intro-desc">Enter any <b>Instagram username</b> on your dashboard and hit Quick Scan. CIPHER extracts their posts in seconds. Costs <b style="color:var(--green);">1 credit</b> per scan.</p>
                </div>

                <!-- Slide 3: Deep Scan -->
                <div class="intro-slide">
                    <div class="intro-icon-wrap"><span class="intro-icon-emoji" style="font-size:1.6rem;display:flex;align-items:center;justify-content:center;">{DEEP_ICON}</span></div>
                    <div class="intro-step-num">Step 3 of 5</div>
                    <div class="intro-title" style="color:var(--magenta);">Private Deep Scan</div>
                    <p class="intro-desc">Need <b>more posts</b>? Deep Scan uses a separate engine with pagination to find up to <b>60 posts</b>. Costs <b style="color:var(--magenta);">2 credits</b> per scan.</p>
                </div>

                <!-- Slide 4: Buy Credits -->
                <div class="intro-slide">
                    <div class="intro-icon-wrap"><span class="intro-icon-emoji" style="font-size:1.6rem;display:flex;align-items:center;justify-content:center;">{CREDIT_ICON}</span></div>
                    <div class="intro-step-num">Step 4 of 5</div>
                    <div class="intro-title" style="color:var(--green);">Buy Credits</div>
                    <p class="intro-desc">Pay <b style="color:var(--green);">\u20B915 per post</b> or pick a <b>monthly plan</b> (Basic \u20B9199, Pro \u20B9499, Elite \u20B9999). <b>UPI &amp; card</b> both accepted. Invoices auto-generated.</p>
                </div>

                <!-- Slide 5: Ready -->
                <div class="intro-slide">
                    <div class="intro-icon-wrap"><span class="intro-icon-emoji">\U0001F6F8</span></div>
                    <div class="intro-step-num">Step 5 of 5</div>
                    <div class="intro-title" style="background:linear-gradient(90deg,var(--cyan),var(--magenta));-webkit-background-clip:text;background-clip:text;-webkit-text-fill-color:transparent;">You're All Set!</div>
                    <p class="intro-desc">You can also <b style="color:var(--gold);">redeem gift cards</b> for free credits. By continuing, you agree to our <a href="/terms" style="color:var(--cyan);">Terms &amp; Conditions</a>.</p>
                </div>

            </div>

            <!-- Progress dots -->
            <div class="intro-dots">
                <span class="intro-dot active"></span>
                <span class="intro-dot"></span>
                <span class="intro-dot"></span>
                <span class="intro-dot"></span>
                <span class="intro-dot"></span>
            </div>

            <!-- Navigation -->
            <div class="intro-nav">
                <span class="intro-link" id="introPrev" style="visibility:hidden;">\u2190 Previous</span>
                <a href="/dashboard" class="btn btn-primary" id="introFinish" style="display:none;font-size:.85rem;padding:12px 24px;">\U0001F6F8 Enter Dashboard</a>
                <button class="btn btn-outline" id="introNext" style="font-size:.85rem;padding:12px 24px;">Next \u2192</button>
                <span class="intro-link" id="introSkip">Skip</span>
            </div>
        </div>
    </div>
    {INTRO_JS}"""
    return base_page("Cipher · Welcome", body, user, extra_head=f"<style>{INTRO_CSS}</style>")


# ── Dashboard ─────────────────────────────────────────────────

def dashboard_page(user, flash=None, reviews=None):
    flash_html = ''
    if flash:
        cls = 'flash-ok' if flash.startswith('ok:') else 'flash-error'
        flash_html = f'<div class="flash {cls}">{flash[3:] if flash[3:] else flash}</div>'

    # Scrape form
    scrape_section = f"""
    <div class="card">
        <h2>{CREDIT_ICON} Extract Posts</h2>
        <p style="color:var(--dim);font-size:.85rem;margin-bottom:18px;">Enter an Instagram username. <b style="color:var(--green);">1 credit</b> per scrape. You have <b style="color:var(--green);">{user['credits']}</b> credits.</p>
        <form action="/scrape" method="get" style="display:flex;gap:12px;flex-wrap:wrap;">
            <input type="text" name="username" placeholder="Instagram username..." required style="flex:1;min-width:200px;" autocomplete="off">
            <button type="submit" class="btn btn-primary">{SCAN_ICON} Quick Scan</button>
        </form>
        <div style="margin-top:16px;padding-top:16px;border-top:1px solid var(--line);">
            <p style="color:var(--dim);font-size:.78rem;margin-bottom:12px;">🛰 <b style="color:var(--magenta);">Private Deep Scan</b> — finds <b>more posts</b> using pagination (up to 60). <b style="color:var(--magenta);">2 credits</b> per scan. Separate scraper engine.</p>
            <form action="/scrape-private" method="get" style="display:flex;gap:12px;flex-wrap:wrap;">
                <input type="text" name="username" placeholder="Instagram username..." required style="flex:1;min-width:200px;" autocomplete="off">
                <button type="submit" class="btn btn-outline" style="border-color:var(--magenta);color:var(--magenta);">{DEEP_ICON} Deep Scan</button>
            </form>
        </div>
    </div>"""

    # Per-post payment
    per_post = f"""
    <div class="card" style="text-align:center;">
        <h2>💰 Pay Per Post</h2>
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
        <h2>🗓 Monthly Plans</h2>
        <div class="plans-grid">{plans_html}</div>
    </div>"""

    # Gift card
    gift_section = f"""
    <div class="card">
        <h2>🎟 Gift Card</h2>
        <p style="color:var(--dim);font-size:.85rem;margin-bottom:18px;">Have a gift card code? Redeem it for credits.</p>
        <form action="/redeem" method="post" style="display:flex;gap:12px;flex-wrap:wrap;">
            <input type="text" name="code" placeholder="GIFT-XXXXXXXX" required style="flex:1;min-width:200px;">
            <button type="submit" class="btn btn-outline">Redeem</button>
        </form>
    </div>"""

    body = flash_html + scrape_section + per_post + plans_section + gift_section + reviews_section(reviews or [], user)
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
        <h2 style="color:{mode_color};">{SCAN_ICON if mode == 'quick' else DEEP_ICON} {mode_label}</h2>
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
        <a href="/dashboard" class="btn btn-outline btn-sm" style="margin-top:16px;display:none;" id="backBtn">⟵ Back to Dashboard</a>
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
.scan-step.done .step-icon {{ content:'✔';color:var(--green); }}
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
            steps[stepIdx - 1].querySelector('.step-icon').textContent = '✔';
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
        btn.textContent = '✔ Copied!';
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
    var coinPhase = document.getElementById('upiCoinPhase');
    var scanPhase = document.getElementById('upiScanPhase');
    var successPhase = document.getElementById('upiSuccessPhase');
    var s1 = document.getElementById('vstep1');
    var s2 = document.getElementById('vstep2');
    var s3 = document.getElementById('vstep3');
    var s4 = document.getElementById('vstep4');

    function resetSteps() { [s1,s2,s3,s4].forEach(function(s){ s.classList.remove('active'); s.style.color=''; }); }

    overlay.classList.add('active');
    coinPhase.style.display = 'block';
    scanPhase.style.display = 'none';
    successPhase.style.display = 'none';
    resetSteps();

    // Phase 1: Coin transfer + upload
    setTimeout(function() { s1.classList.add('active'); }, 200);

    // Phase 2: AI scan
    setTimeout(function() {
        s1.classList.remove('active');
        coinPhase.style.display = 'none';
        scanPhase.style.display = 'block';
        s2.classList.add('active');
    }, 1800);

    // Phase 3: Verifying
    setTimeout(function() {
        s2.classList.remove('active');
        s3.classList.add('active');
    }, 3200);

    // Phase 4: Success
    setTimeout(function() {
        s3.classList.remove('active');
        scanPhase.style.display = 'none';
        successPhase.style.display = 'block';
        s4.classList.add('active');
        s4.style.color = 'var(--green)';
    }, 4200);

    setTimeout(function() { form.submit(); }, 5500);
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
        <h2>💰 {title_text}</h2>
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
            <div style="font-family:'JetBrains Mono',monospace;font-size:.72rem;color:var(--cyan);letter-spacing:4px;text-transform:uppercase;margin-bottom:14px;">💠 Pay via UPI</div>
            <div style="display:flex;align-items:center;justify-content:center;gap:10px;margin-bottom:16px;flex-wrap:wrap;">
                <span style="font-family:'JetBrains Mono',monospace;font-size:1.05rem;font-weight:800;color:var(--cyan);letter-spacing:1px;text-shadow:0 0 20px rgba(0,229,255,.4);">{UPI_ID}</span>
                <button class="copy-btn" onclick="copyUpi()" style="background:rgba(0,229,255,.15);border:1px solid rgba(0,229,255,.4);color:var(--cyan);padding:5px 12px;border-radius:8px;font-family:'JetBrains Mono',monospace;font-size:.7rem;cursor:pointer;transition:all .3s;">📝 Copy</button>
            </div>
            <div class="upi-qr-frame">
                <div class="upi-qr-glow"></div>
                <div class="upi-qr-corner tl"></div>
                <div class="upi-qr-corner tr"></div>
                <div class="upi-qr-corner bl"></div>
                <div class="upi-qr-corner br"></div>
                <div class="upi-qr-inner">
                    <img src="{qr_url}" alt="UPI QR Code" style="width:100%;height:100%;border-radius:8px;">
                    <div class="upi-qr-scanline"></div>
                </div>
                <div class="upi-pulse-ring r1"></div>
                <div class="upi-pulse-ring r2"></div>
                <div class="upi-pulse-ring r3"></div>
            </div>
            <div class="upi-amt-badge"><b style="color:var(--green);">₹{amount}</b></div>
            <p style="color:var(--dim);font-size:.78rem;margin-bottom:16px;">Scan QR or copy UPI ID · Pay <b style="color:var(--green);">₹{amount}</b></p>
            <button class="btn btn-green btn-block" onclick="showUpload()" style="animation:pulse 2s infinite;">✔ I've Paid — Submit Proof</button>
        </div>

        <!-- UPI Upload Form (hidden) -->
        <div id="upiUploadForm" style="display:none;margin-bottom:20px;">
            <form id="upiForm" action="/verify-upi" method="post" enctype="multipart/form-data" style="background:rgba(17,22,36,.6);border:1px solid var(--line);border-radius:14px;padding:22px 18px;">
                <div style="font-family:'JetBrains Mono',monospace;font-size:.82rem;color:var(--cyan);letter-spacing:2px;text-transform:uppercase;margin-bottom:16px;">📩 Submit Payment Proof</div>
                <input type="hidden" name="payment_type" value="{payment_type}">
                <input type="hidden" name="plan_key" value="{plan_key or ''}">
                <input type="hidden" name="amount" value="{amount}">
                <input type="hidden" name="credits" value="{credits}">
                <div class="field"><label>Your Name / UPI Sender Name</label><input type="text" name="sender_name" required placeholder="Name shown in UPI app"></div>
                <div class="field"><label>UTR Number (Transaction Ref)</label><input type="text" name="utr" required placeholder="e.g. 452178963012" maxlength="22"></div>
                <div class="field"><label>Payment Screenshot</label><input type="file" name="screenshot" accept="image/*" required onchange="previewSS(this)" style="padding:10px;"><img id="ssPreview" style="display:none;max-width:100%;border-radius:10px;margin-top:10px;border:1px solid var(--line);"></div>
                <button type="submit" class="btn btn-primary btn-block" onclick="return startUpiVerify()">🧠 Submit & AI Verify</button>
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
        <div class="upi-pay-anim">
            <!-- Phase 1: Coin transfer animation -->
            <div class="upi-coin-phase" id="upiCoinPhase">
                <div class="upi-coin-track">
                    <div class="upi-coin-sender">
                        <div class="upi-coin-icon">₹</div>
                        <div class="upi-coin-label">YOU</div>
                    </div>
                    <div class="upi-coin-path">
                        <div class="upi-coin-dot d1"></div>
                        <div class="upi-coin-dot d2"></div>
                        <div class="upi-coin-dot d3"></div>
                        <div class="upi-coin-dot d4"></div>
                        <div class="upi-coin-dot d5"></div>
                    </div>
                    <div class="upi-coin-receiver">
                        <div class="upi-coin-icon" style="background:linear-gradient(135deg,var(--magenta),#7c3aed);">◈</div>
                        <div class="upi-coin-label">CIPHER</div>
                    </div>
                </div>
                <div class="upi-amt-fly" id="upiAmtFly">₹{amount}</div>
            </div>
            <!-- Phase 2: AI scan animation -->
            <div class="upi-scan-phase" id="upiScanPhase" style="display:none;">
                <div class="upi-ai-orb">
                    <div class="upi-ai-ring r1"></div>
                    <div class="upi-ai-ring r2"></div>
                    <div class="upi-ai-ring r3"></div>
                    <div class="upi-ai-core">🧠</div>
                </div>
            </div>
            <!-- Phase 3: Success -->
            <div class="upi-success-phase" id="upiSuccessPhase" style="display:none;">
                <div class="upi-success-burst">
                    <div class="upi-burst-ray" style="transform:rotate(0deg);"></div>
                    <div class="upi-burst-ray" style="transform:rotate(45deg);"></div>
                    <div class="upi-burst-ray" style="transform:rotate(90deg);"></div>
                    <div class="upi-burst-ray" style="transform:rotate(135deg);"></div>
                    <div class="upi-burst-ray" style="transform:rotate(180deg);"></div>
                    <div class="upi-burst-ray" style="transform:rotate(225deg);"></div>
                    <div class="upi-burst-ray" style="transform:rotate(270deg);"></div>
                    <div class="upi-burst-ray" style="transform:rotate(315deg);"></div>
                </div>
                <div class="upi-success-check">
                    <svg viewBox="0 0 52 52" style="width:44px;height:44px;"><path d="M14 27 L22 35 L38 17" style="stroke:var(--green);stroke-width:5;fill:none;stroke-linecap:round;stroke-linejoin:round;stroke-dasharray:50;stroke-dashoffset:50;animation:drawCheck .5s ease .2s forwards;"/></svg>
                </div>
            </div>
            <!-- Steps text -->
            <div class="verify-step" id="vstep1">🛰 Uploading Screenshot...</div>
            <div class="verify-step" id="vstep2">🧠 AI Analyzing Payment...</div>
            <div class="verify-step" id="vstep3">✔ Verifying Transaction...</div>
            <div class="verify-step" id="vstep4">☑ Verification Complete!</div>
        </div>
    </div>"""

    extra = f"""<style>
@keyframes qrScan {{ 0%,100% {{ top:0; }} 50% {{ top:calc(100% - 3px); }} }}
@keyframes pulse {{ 0%,100% {{ box-shadow:0 0 0 0 rgba(0,255,156,.4); }} 50% {{ box-shadow:0 0 0 8px rgba(0,255,156,0); }} }}
.pay-overlay,.upi-verify-overlay {{ position:fixed;inset:0;z-index:999;display:none;align-items:center;justify-content:center;background:rgba(5,6,10,.95);backdrop-filter:blur(20px); }}
.pay-overlay.active,.upi-verify-overlay.active {{ display:flex; }}
.verify-step {{ font-family:'JetBrains Mono',monospace;font-size:.85rem;letter-spacing:2px;color:var(--cyan);margin-top:14px;opacity:0;transition:opacity .4s; }}
.verify-step.active {{ opacity:1 !important; }}

/* ── New UPI QR animation ── */
.upi-qr-frame {{
    position:relative;width:200px;height:200px;margin:0 auto 14px;
    display:flex;align-items:center;justify-content:center;
}}
.upi-qr-glow {{
    position:absolute;inset:-20px;border-radius:50%;
    background:radial-gradient(circle,rgba(0,229,255,.15),transparent 70%);
    animation:upiGlow 3s ease-in-out infinite;
}}
@keyframes upiGlow {{ 0%,100%{{opacity:.5;transform:scale(1);}} 50%{{opacity:1;transform:scale(1.1);}} }}
.upi-qr-corner {{
    position:absolute;width:28px;height:28px;border:3px solid var(--cyan);
    box-shadow:0 0 12px rgba(0,229,255,.4);
}}
.upi-qr-corner.tl {{ top:0;left:0;border-right:none;border-bottom:none;border-radius:8px 0 0 0; }}
.upi-qr-corner.tr {{ top:0;right:0;border-left:none;border-bottom:none;border-radius:0 8px 0 0; }}
.upi-qr-corner.bl {{ bottom:0;left:0;border-right:none;border-top:none;border-radius:0 0 0 8px; }}
.upi-qr-corner.br {{ bottom:0;right:0;border-left:none;border-top:none;border-radius:0 0 8px 0; }}
.upi-qr-inner {{
    width:170px;height:170px;border-radius:10px;overflow:hidden;
    border:1px solid rgba(0,229,255,.2);position:relative;
    background:#fff;
}}
.upi-qr-scanline {{
    position:absolute;left:0;right:0;height:3px;
    background:linear-gradient(90deg,transparent,var(--cyan),var(--magenta),transparent);
    box-shadow:0 0 15px var(--cyan);
    animation:qrScan 2.5s ease-in-out infinite;
}}
.upi-pulse-ring {{
    position:absolute;border-radius:50%;border:2px solid rgba(0,229,255,.3);
    width:200px;height:200px;opacity:0;
}}
.upi-pulse-ring.r1 {{ animation:upiPulse 2s ease-out infinite; }}
.upi-pulse-ring.r2 {{ animation:upiPulse 2s ease-out infinite .6s; }}
.upi-pulse-ring.r3 {{ animation:upiPulse 2s ease-out infinite 1.2s; }}
@keyframes upiPulse {{
    0% {{ transform:scale(1);opacity:.6; }}
    100% {{ transform:scale(1.6);opacity:0; }}
}}
.upi-amt-badge {{
    display:inline-block;margin-top:8px;padding:4px 16px;border-radius:20px;
    background:rgba(0,255,156,.1);border:1px solid rgba(0,255,156,.3);
    font-family:'JetBrains Mono',monospace;font-size:1rem;letter-spacing:1px;
    animation:upiGlow 2s ease-in-out infinite;
}}

/* ── New UPI payment submit animation ── */
.upi-pay-anim {{ text-align:center;max-width:320px; }}
.upi-coin-phase {{ padding:20px 0; }}
.upi-coin-track {{ display:flex;align-items:center;justify-content:center;gap:0; }}
.upi-coin-sender,.upi-coin-receiver {{
    display:flex;flex-direction:column;align-items:center;gap:6px;z-index:2;
}}
.upi-coin-icon {{
    width:52px;height:52px;border-radius:50%;display:flex;align-items:center;justify-content:center;
    font-family:'JetBrains Mono',monospace;font-size:1.4rem;font-weight:800;color:#05060a;
    background:linear-gradient(135deg,var(--cyan),var(--green));
    box-shadow:0 0 20px rgba(0,229,255,.4);
}}
.upi-coin-label {{
    font-family:'JetBrains Mono',monospace;font-size:.62rem;letter-spacing:2px;color:var(--dim);
}}
.upi-coin-path {{
    flex:1;height:2px;position:relative;margin:0 -6px;max-width:120px;
    background:linear-gradient(90deg,rgba(0,229,255,.2),rgba(255,43,214,.2));
}}
.upi-coin-dot {{
    position:absolute;top:50%;width:8px;height:8px;border-radius:50%;
    background:var(--cyan);box-shadow:0 0 10px var(--cyan);
    transform:translateY(-50%);
}}
.upi-coin-dot.d1 {{ animation:coinFly 1.2s linear infinite; animation-delay:0s; }}
.upi-coin-dot.d2 {{ animation:coinFly 1.2s linear infinite; animation-delay:.24s; }}
.upi-coin-dot.d3 {{ animation:coinFly 1.2s linear infinite; animation-delay:.48s; }}
.upi-coin-dot.d4 {{ animation:coinFly 1.2s linear infinite; animation-delay:.72s; }}
.upi-coin-dot.d5 {{ animation:coinFly 1.2s linear infinite; animation-delay:.96s; }}
@keyframes coinFly {{
    0% {{ left:0;opacity:0;transform:translateY(-50%) scale(.5); }}
    15% {{ opacity:1;transform:translateY(-50%) scale(1); }}
    85% {{ opacity:1; }}
    100% {{ left:100%;opacity:0;transform:translateY(-50%) scale(.5); }}
}}
.upi-amt-fly {{
    margin-top:18px;font-family:'JetBrains Mono',monospace;font-size:1.6rem;font-weight:800;
    color:var(--green);text-shadow:0 0 20px rgba(0,255,156,.4);
    animation:amtPulse 1s ease-in-out infinite;
}}
@keyframes amtPulse {{ 0%,100%{{transform:scale(1);}} 50%{{transform:scale(1.08);}} }}

/* AI orb phase */
.upi-scan-phase {{ padding:20px 0; }}
.upi-ai-orb {{
    width:120px;height:120px;margin:0 auto;position:relative;
    display:flex;align-items:center;justify-content:center;
}}
.upi-ai-ring {{
    position:absolute;border-radius:50%;border:2px solid transparent;
    border-top-color:var(--cyan);border-right-color:var(--magenta);
}}
.upi-ai-ring.r1 {{ width:120px;height:120px;animation:aiSpin 1.5s linear infinite; }}
.upi-ai-ring.r2 {{ width:90px;height:90px;border-top-color:var(--magenta);border-right-color:var(--cyan);animation:aiSpin 1.2s linear infinite reverse; }}
.upi-ai-ring.r3 {{ width:60px;height:60px;border-top-color:var(--green);animation:aiSpin 1s linear infinite; }}
@keyframes aiSpin {{ to {{ transform:rotate(360deg); }} }}
.upi-ai-core {{ font-size:2rem;animation:aiCorePulse 1s ease-in-out infinite; }}
@keyframes aiCorePulse {{ 0%,100%{{transform:scale(1);}} 50%{{transform:scale(1.2);}} }}

/* Success phase */
.upi-success-phase {{ padding:20px 0;position:relative; }}
.upi-success-burst {{
    position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);
    width:120px;height:120px;pointer-events:none;
}}
.upi-burst-ray {{
    position:absolute;top:50%;left:50%;width:60px;height:3px;
    background:linear-gradient(90deg,var(--green),transparent);
    transform-origin:left center;
    animation:burstRay .6s ease-out forwards;opacity:0;
}}
@keyframes burstRay {{
    0% {{ opacity:0;transform:translateY(-50%) scaleX(0); }}
    50% {{ opacity:1;transform:translateY(-50%) scaleX(1); }}
    100% {{ opacity:0;transform:translateY(-50%) scaleX(1.3); }}
}}
.upi-success-check {{
    width:80px;height:80px;margin:0 auto;border-radius:50%;
    background:rgba(0,255,156,.15);border:3px solid var(--green);
    display:flex;align-items:center;justify-content:center;
    animation:popIn .5s ease;position:relative;z-index:2;
}}
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
        <span class="invoice-paid">✔ PAID</span>
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
            <div class="sign-name">ii_silkroad_ii</div>
            <div class="sign-title">CIPHER · ADMIN</div>
        </div>
        <div style="text-align:center;margin-top:28px;">
            <button onclick="window.print()" class="btn btn-outline btn-sm">📄 Print / Save PDF</button>
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
        <h2>🎟 Create Gift Card</h2>
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
            ai_badge = f'<span style="color:var(--green);font-weight:700;">✔ Verified ({up["ai_confidence"]}%)</span>'
        elif ai == 'suspicious':
            ai_badge = f'<span style="color:var(--gold);font-weight:700;">❗ Suspicious ({up["ai_confidence"]}%)</span>'
        elif ai == 'rejected':
            ai_badge = f'<span style="color:var(--red);font-weight:700;">✖ Rejected</span>'
        else:
            ai_badge = '<span style="color:var(--dim);">Manual review</span>'

        if up['status'] == 'pending':
            status_badge = '<span class="tag tag-active" style="background:rgba(255,215,0,.12);border:1px solid rgba(255,215,0,.4);color:var(--gold);">Pending</span>'
            actions = f"""
                <form action="/admin/verify-upi" method="post" style="display:inline;">
                    <input type="hidden" name="payment_id" value="{up['id']}">
                    <button type="submit" class="btn btn-sm btn-green" style="padding:6px 12px;font-size:.68rem;">✔ Approve</button>
                </form>
                <form action="/admin/reject-upi" method="post" style="display:inline;margin-left:4px;">
                    <input type="hidden" name="payment_id" value="{up['id']}">
                    <button type="submit" class="btn btn-sm" style="padding:6px 12px;font-size:.68rem;background:rgba(255,56,96,.15);color:var(--red);border:1px solid rgba(255,56,96,.3);">✖ Reject</button>
                </form>"""
        elif up['status'] == 'verified':
            status_badge = '<span class="tag tag-active">Verified</span>'
            actions = ''
        else:
            status_badge = '<span class="tag tag-redeemed">Rejected</span>'
            actions = ''

        ss_link = f'<a href="/screenshot?name={up["screenshot_path"]}" target="_blank" style="color:var(--cyan);">📸 View</a>' if up['screenshot_path'] else '—'
        ai_reason = f'<br><span style="font-size:.68rem;color:var(--dim);">{up["ai_reason"][:60]}</span>' if up['ai_reason'] else ''
        review_flag = f'<br><span style="font-size:.62rem;color:var(--green);font-weight:700;letter-spacing:1px;">⏳ AWAITING REVIEW</span>' if (ai == 'verified' and up['status'] == 'pending') else ''
        row_highlight = ' style="background:rgba(0,255,156,.06);"' if (ai == 'verified' and up['status'] == 'pending') else ''

        upi_rows += f"""<tr{row_highlight}>
            <td style="font-size:.75rem;">{up['user_name'] or up['email']}<br><span style="font-size:.68rem;color:var(--dim);">{up['sender_name']}</span></td>
            <td>₹{up['amount']}<br><span style="font-size:.68rem;color:var(--cyan);">{up['credits']} cr</span></td>
            <td style="font-size:.72rem;">{up['utr']}</td>
            <td>{ss_link}</td>
            <td style="font-size:.72rem;">{ai_badge}{ai_reason}{review_flag}</td>
            <td>{status_badge}</td>
            <td>{actions}</td>
        </tr>"""

    upi_section = f"""
    <div class="card">
        <h2>🧠 UPI Payment Verifications</h2>
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
        <h2>{CREDIT_ICON} Add Credits to User</h2>
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
        <h2>💰 Payment Methods</h2>
        <p style="color:var(--dim);font-size:.82rem;margin-bottom:18px;">Add any payment method you want — UPI, bank transfer, crypto, etc. Users will see these on the payment page.</p>
        <form action="/admin/add-payment-method" method="post" style="display:flex;gap:12px;flex-wrap:wrap;align-items:flex-end;margin-bottom:20px;">
            <div class="field" style="flex:1;min-width:100px;margin-bottom:0;">
                <label>Icon</label>
                <input type="text" name="icon" placeholder="💰" maxlength="4" value="💰" style="text-align:center;">
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
        <h2>🎟 Gift Cards</h2>
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
        <h2>🧑‍💼 Users</h2>
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
        <h2>💰 Payments</h2>
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
        <h2>📑 Invoices</h2>
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
        <h2>📈 Per-User Activity</h2>
        <div class="table-wrap"><table>
            <thead><tr><th>User</th><th>Email</th><th>Searches</th><th>Downloads</th><th>Total</th></tr></thead>
            <tbody>{user_rows_html if user_rows_html else '<tr><td colspan="5" style="text-align:center;color:var(--dim);">No activity recorded yet</td></tr>'}</tbody>
        </table></div>
    </div>"""

    body = stats_html + table_html
    return base_page("Cipher · Analytics", body, user)
