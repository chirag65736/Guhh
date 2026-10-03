"""
Database management for Cipher — SQLite backend for users, sessions,
payments, gift cards, and invoices.
"""

import sqlite3
import hashlib
import secrets
import os

DB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
DB_PATH = os.path.join(DB_DIR, 'cipher.db')

ADMIN_EMAIL = 'chiragkashyap201@gmail.com'
ADMIN_PASSWORD = 'chirag2009'

PER_POST_PRICE = 15

PLANS = {
    'basic':  {'name': 'Basic',  'price': 199, 'credits': 15,  'duration': '1 Month'},
    'pro':    {'name': 'Pro',    'price': 499, 'credits': 50,  'duration': '1 Month'},
    'elite':  {'name': 'Elite',  'price': 999, 'credits': 999, 'duration': '1 Month'},
}


def get_db():
    os.makedirs(DB_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    c = conn.cursor()
    c.executescript('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            name TEXT NOT NULL,
            is_admin INTEGER DEFAULT 0,
            credits INTEGER DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS sessions (
            token TEXT PRIMARY KEY,
            user_id INTEGER NOT NULL,
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (user_id) REFERENCES users(id)
        );
        CREATE TABLE IF NOT EXISTS payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            amount REAL NOT NULL,
            payment_type TEXT NOT NULL,
            plan_key TEXT,
            credits INTEGER DEFAULT 0,
            status TEXT DEFAULT 'completed',
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (user_id) REFERENCES users(id)
        );
        CREATE TABLE IF NOT EXISTS gift_cards (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE NOT NULL,
            value INTEGER NOT NULL,
            status TEXT DEFAULT 'active',
            created_at TEXT DEFAULT (datetime('now')),
            redeemed_by INTEGER,
            redeemed_at TEXT,
            FOREIGN KEY (redeemed_by) REFERENCES users(id)
        );
        CREATE TABLE IF NOT EXISTS invoices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            invoice_number TEXT UNIQUE NOT NULL,
            user_id INTEGER NOT NULL,
            payment_id INTEGER,
            amount REAL NOT NULL,
            details TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (payment_id) REFERENCES payments(id)
        );
        CREATE TABLE IF NOT EXISTS payment_methods (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            details TEXT NOT NULL,
            icon TEXT DEFAULT '💳',
            is_active INTEGER DEFAULT 1,
            created_at TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS activity (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            action TEXT NOT NULL,
            target TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (user_id) REFERENCES users(id)
        );
    ''')

    # Create admin user if not exists
    c.execute('SELECT id FROM users WHERE email = ?', (ADMIN_EMAIL,))
    if not c.fetchone():
        c.execute(
            'INSERT INTO users (email, password_hash, name, is_admin, credits) VALUES (?, ?, ?, 1, 999999)',
            (ADMIN_EMAIL, hash_password(ADMIN_PASSWORD), 'Chirag (Admin)')
        )

    conn.commit()
    conn.close()


# ── Password helpers ──────────────────────────────────────────

def hash_password(password):
    salt = secrets.token_hex(16)
    h = hashlib.sha256((salt + password).encode()).hexdigest()
    return f"{salt}:{h}"


def verify_password(password, stored_hash):
    salt, h = stored_hash.split(':')
    return hashlib.sha256((salt + password).encode()).hexdigest() == h


# ── Users ──────────────────────────────────────────────────────

def create_user(email, password, name):
    conn = get_db()
    try:
        conn.execute(
            'INSERT INTO users (email, password_hash, name) VALUES (?, ?, ?)',
            (email, hash_password(password), name)
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()


def get_user_by_email(email):
    conn = get_db()
    user = conn.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()
    conn.close()
    return user


def get_user_by_id(user_id):
    conn = get_db()
    user = conn.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
    conn.close()
    return user


# ── Sessions ──────────────────────────────────────────────────

def create_session(user_id):
    token = secrets.token_hex(32)
    conn = get_db()
    conn.execute('INSERT INTO sessions (token, user_id) VALUES (?, ?)', (token, user_id))
    conn.commit()
    conn.close()
    return token


def get_session_user(token):
    if not token:
        return None
    conn = get_db()
    row = conn.execute('SELECT user_id FROM sessions WHERE token = ?', (token,)).fetchone()
    conn.close()
    if row:
        return get_user_by_id(row['user_id'])
    return None


def delete_session(token):
    conn = get_db()
    conn.execute('DELETE FROM sessions WHERE token = ?', (token,))
    conn.commit()
    conn.close()


# ── Credits ───────────────────────────────────────────────────

def add_credits(user_id, amount):
    conn = get_db()
    conn.execute('UPDATE users SET credits = credits + ? WHERE id = ?', (amount, user_id))
    conn.commit()
    conn.close()


def deduct_credit(user_id):
    conn = get_db()
    user = conn.execute('SELECT credits FROM users WHERE id = ?', (user_id,)).fetchone()
    if user and user['credits'] >= 1:
        conn.execute('UPDATE users SET credits = credits - 1 WHERE id = ?', (user_id,))
        conn.commit()
        conn.close()
        return True
    conn.close()
    return False


# ── Payments & Invoices ───────────────────────────────────────

def create_payment(user_id, amount, payment_type, plan_key=None, credits=0):
    conn = get_db()
    c = conn.execute(
        'INSERT INTO payments (user_id, amount, payment_type, plan_key, credits) VALUES (?, ?, ?, ?, ?)',
        (user_id, amount, payment_type, plan_key, credits)
    )
    payment_id = c.lastrowid
    conn.commit()
    conn.close()
    return payment_id


def create_invoice(user_id, payment_id, amount, details):
    invoice_number = f"INV-{secrets.token_hex(4).upper()}"
    conn = get_db()
    c = conn.execute(
        'INSERT INTO invoices (invoice_number, user_id, payment_id, amount, details) VALUES (?, ?, ?, ?, ?)',
        (invoice_number, user_id, payment_id, amount, details)
    )
    invoice_id = c.lastrowid
    conn.commit()
    conn.close()
    return invoice_id, invoice_number


def get_invoice(invoice_id):
    conn = get_db()
    invoice = conn.execute(
        '''SELECT i.*, u.email, u.name AS user_name
           FROM invoices i JOIN users u ON i.user_id = u.id
           WHERE i.id = ?''',
        (invoice_id,)
    ).fetchone()
    conn.close()
    return invoice


# ── Gift Cards ────────────────────────────────────────────────

def create_gift_card(value):
    code = f"GIFT-{secrets.token_hex(4).upper()}"
    conn = get_db()
    conn.execute('INSERT INTO gift_cards (code, value) VALUES (?, ?)', (code, value))
    conn.commit()
    conn.close()
    return code


def redeem_gift_card(code, user_id):
    conn = get_db()
    card = conn.execute(
        'SELECT * FROM gift_cards WHERE code = ? AND status = "active"', (code,)
    ).fetchone()
    if card:
        conn.execute(
            'UPDATE gift_cards SET status = "redeemed", redeemed_by = ?, redeemed_at = datetime("now") WHERE id = ?',
            (user_id, card['id'])
        )
        conn.execute('UPDATE users SET credits = credits + ? WHERE id = ?', (card['value'], user_id))
        conn.commit()
        conn.close()
        return card['value']
    conn.close()
    return None


def get_all_gift_cards():
    conn = get_db()
    cards = conn.execute('SELECT * FROM gift_cards ORDER BY created_at DESC').fetchall()
    conn.close()
    return cards


# ── Admin queries ─────────────────────────────────────────────

def get_all_users():
    conn = get_db()
    users = conn.execute('SELECT * FROM users ORDER BY created_at DESC').fetchall()
    conn.close()
    return users


def get_all_payments():
    conn = get_db()
    payments = conn.execute(
        '''SELECT p.*, u.email FROM payments p
           JOIN users u ON p.user_id = u.id
           ORDER BY p.created_at DESC''').fetchall()
    conn.close()
    return payments


def get_all_invoices():
    conn = get_db()
    invoices = conn.execute(
        '''SELECT i.*, u.email FROM invoices i
           JOIN users u ON i.user_id = u.id
           ORDER BY i.created_at DESC''').fetchall()
    conn.close()
    return invoices


def get_stats():
    conn = get_db()
    total_users = conn.execute('SELECT COUNT(*) AS c FROM users WHERE is_admin = 0').fetchone()['c']
    total_revenue = conn.execute('SELECT COALESCE(SUM(amount), 0) AS s FROM payments').fetchone()['s']
    total_payments = conn.execute('SELECT COUNT(*) AS c FROM payments').fetchone()['c']
    active_cards = conn.execute('SELECT COUNT(*) AS c FROM gift_cards WHERE status = "active"').fetchone()['c']
    conn.close()
    return {
        'users': total_users,
        'revenue': total_revenue,
        'payments': total_payments,
        'active_cards': active_cards,
    }


# ── Payment Methods (admin-managed) ──────────────────────────

def add_payment_method(name, details, icon='💳'):
    conn = get_db()
    conn.execute(
        'INSERT INTO payment_methods (name, details, icon) VALUES (?, ?, ?)',
        (name, details, icon)
    )
    conn.commit()
    conn.close()


def get_payment_methods():
    conn = get_db()
    methods = conn.execute(
        'SELECT * FROM payment_methods WHERE is_active = 1 ORDER BY created_at DESC'
    ).fetchall()
    conn.close()
    return methods


def get_all_payment_methods():
    conn = get_db()
    methods = conn.execute(
        'SELECT * FROM payment_methods ORDER BY created_at DESC'
    ).fetchall()
    conn.close()
    return methods


def delete_payment_method(method_id):
    conn = get_db()
    conn.execute('DELETE FROM payment_methods WHERE id = ?', (method_id,))
    conn.commit()
    conn.close()


# ── Activity / Analytics ──────────────────────────────────────

def log_activity(user_id, action, target=None):
    conn = get_db()
    conn.execute(
        'INSERT INTO activity (user_id, action, target) VALUES (?, ?, ?)',
        (user_id, action, target)
    )
    conn.commit()
    conn.close()


def get_analytics():
    """Per-user search and download counts, heaviest users first."""
    conn = get_db()
    rows = conn.execute('''
        SELECT u.id, u.name, u.email,
            COUNT(CASE WHEN a.action = 'search'   THEN 1 END) AS searches,
            COUNT(CASE WHEN a.action = 'download' THEN 1 END) AS downloads
        FROM users u
        LEFT JOIN activity a ON u.id = a.user_id
        WHERE u.is_admin = 0
        GROUP BY u.id
        ORDER BY (searches + downloads) DESC, searches DESC
    ''').fetchall()
    conn.close()
    return rows


def get_analytics_summary():
    """Overall totals for the analytics dashboard."""
    conn = get_db()
    total_searches = conn.execute(
        "SELECT COUNT(*) AS c FROM activity WHERE action = 'search'"
    ).fetchone()['c']
    total_downloads = conn.execute(
        "SELECT COUNT(*) AS c FROM activity WHERE action = 'download'"
    ).fetchone()['c']
    active_users = conn.execute('''
        SELECT COUNT(DISTINCT user_id) AS c
        FROM activity
    ''').fetchone()['c']
    conn.close()
    return {
        'searches': total_searches,
        'downloads': total_downloads,
        'active_users': active_users,
    }
