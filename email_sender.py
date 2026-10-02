"""
Email sender — sends invoice emails via Gmail SMTP.
Uses GMAIL_USER and GMAIL_APP_PASSWORD environment variables.
"""

import smtplib
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


def send_invoice_email(to_email, invoice_number, amount, details, user_name):
    """Send an invoice notification email via Gmail. Returns True on success."""
    gmail_user = os.environ.get('GMAIL_USER')
    gmail_pass = os.environ.get('GMAIL_APP_PASSWORD')

    if not gmail_user or not gmail_pass:
        print('[!] Gmail credentials not set — skipping invoice email', flush=True)
        return False

    html_body = f"""\
<div style="background:#05060a;padding:40px 20px;font-family:'Inter',Arial,sans-serif;">
  <div style="max-width:560px;margin:0 auto;background:rgba(10,13,20,.9);border:1px solid rgba(0,229,255,.2);border-radius:16px;padding:36px 32px;">
    <div style="text-align:center;margin-bottom:28px;">
      <h1 style="font-size:1.8rem;letter-spacing:4px;margin:0;background:linear-gradient(90deg,#00e5ff,#ff2bd6);-webkit-background-clip:text;background-clip:text;-webkit-text-fill-color:transparent;">CIPHER</h1>
      <p style="color:#7a8aa3;font-size:.72rem;letter-spacing:4px;text-transform:uppercase;margin-top:4px;">Private Access Engine</p>
    </div>
    <p style="color:#e6f1ff;font-size:1rem;">Hi {user_name},</p>
    <p style="color:#7a8aa3;font-size:.9rem;line-height:1.6;">Your payment has been processed successfully. Here are your invoice details:</p>
    <table style="width:100%;margin:20px 0;border-collapse:collapse;">
      <tr><td style="padding:10px 0;color:#7a8aa3;font-size:.82rem;border-bottom:1px solid rgba(0,229,255,.1);">Invoice #</td><td style="padding:10px 0;color:#00e5ff;font-size:.82rem;text-align:right;border-bottom:1px solid rgba(0,229,255,.1);">{invoice_number}</td></tr>
      <tr><td style="padding:10px 0;color:#7a8aa3;font-size:.82rem;border-bottom:1px solid rgba(0,229,255,.1);">Description</td><td style="padding:10px 0;color:#e6f1ff;font-size:.82rem;text-align:right;border-bottom:1px solid rgba(0,229,255,.1);">{details}</td></tr>
      <tr><td style="padding:10px 0;color:#7a8aa3;font-size:.82rem;border-bottom:1px solid rgba(0,229,255,.1);">Status</td><td style="padding:10px 0;color:#00ff9c;font-size:.82rem;text-align:right;border-bottom:1px solid rgba(0,229,255,.1);">✓ Paid</td></tr>
      <tr><td style="padding:14px 0;color:#e6f1ff;font-size:1rem;font-weight:700;">Total</td><td style="padding:14px 0;color:#00ff9c;font-size:1.4rem;font-weight:800;text-align:right;">₹{amount}</td></tr>
    </table>
    <div style="text-align:right;margin-top:30px;padding-top:20px;border-top:1px dashed rgba(0,229,255,.15);">
      <p style="color:#7a8aa3;font-size:.68rem;letter-spacing:2px;text-transform:uppercase;margin:0;">Authorized Signature</p>
      <p style="font-family:'Sacramento',cursive;font-size:2rem;color:#00e5ff;margin:4px 0;">chirag</p>
      <p style="color:#7a8aa3;font-size:.68rem;margin:0;">CIPHER · ADMIN</p>
    </div>
    <p style="color:#7a8aa3;font-size:.72rem;text-align:center;margin-top:28px;">This is an automated email from Cipher. Do not reply.</p>
  </div>
</div>"""

    msg = MIMEMultipart('alternative')
    msg['From'] = f'Cipher <{gmail_user}>'
    msg['To'] = to_email
    msg['Subject'] = f'Invoice {invoice_number} — Cipher'
    msg.attach(MIMEText(html_body, 'html'))

    try:
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login(gmail_user, gmail_pass)
            server.send_message(msg)
        print(f'[✓] Invoice email sent to {to_email}', flush=True)
        return True
    except Exception as e:
        print(f'[!] Failed to send invoice email: {e}', flush=True)
        return False
