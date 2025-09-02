import sqlite3
from datetime import datetime

def init_db():
    conn = sqlite3.connect('messages.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS messages
                 (id INTEGER PRIMARY KEY, user_id INTEGER, username TEXT, message_text TEXT, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP, replied BOOLEAN DEFAULT FALSE)''')
    c.execute('''CREATE TABLE IF NOT EXISTS settings
                 (key TEXT PRIMARY KEY, value TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS blocked_users
                 (user_id INTEGER PRIMARY KEY)''')
    # Check if promo_codes table exists with expiration column
    c.execute("PRAGMA table_info(promo_codes)")
    columns = [row[1] for row in c.fetchall()]
    if 'expiration' not in columns:
        # Rename old table
        c.execute("ALTER TABLE promo_codes RENAME TO promo_codes_old")
        # Create new table with expiration column
        c.execute('''CREATE TABLE promo_codes
                     (code TEXT PRIMARY KEY, used BOOLEAN DEFAULT FALSE, expiration DATETIME DEFAULT NULL)''')
        # Copy data from old table
        c.execute("INSERT INTO promo_codes (code, used) SELECT code, used FROM promo_codes_old")
        # Drop old table
        c.execute("DROP TABLE promo_codes_old")
    else:
        c.execute('''CREATE TABLE IF NOT EXISTS promo_codes
                     (code TEXT PRIMARY KEY, used BOOLEAN DEFAULT FALSE, expiration DATETIME DEFAULT NULL)''')
    c.execute('''CREATE TABLE IF NOT EXISTS promoted_users
                 (user_id INTEGER PRIMARY KEY)''')
    conn.commit()
    conn.close()

def save_message(user_id, username, message_text):
    conn = sqlite3.connect('messages.db')
    c = conn.cursor()
    c.execute("INSERT INTO messages (user_id, username, message_text) VALUES (?, ?, ?)", (user_id, username, message_text))
    message_id = c.lastrowid
    conn.commit()
    conn.close()
    return message_id

def get_unreplied_messages():
    conn = sqlite3.connect('messages.db')
    c = conn.cursor()
    c.execute("SELECT id, user_id, username, message_text, timestamp FROM messages WHERE replied = FALSE ORDER BY timestamp DESC")
    rows = c.fetchall()
    conn.close()
    return rows

def mark_replied(message_id):
    conn = sqlite3.connect('messages.db')
    c = conn.cursor()
    c.execute("UPDATE messages SET replied = TRUE WHERE id = ?", (message_id,))
    conn.commit()
    conn.close()

def get_message_by_id(message_id):
    conn = sqlite3.connect('messages.db')
    c = conn.cursor()
    c.execute("SELECT user_id, username, message_text FROM messages WHERE id = ?", (message_id,))
    row = c.fetchone()
    conn.close()
    return row

def get_setting(key):
    conn = sqlite3.connect('messages.db')
    c = conn.cursor()
    c.execute("SELECT value FROM settings WHERE key = ?", (key,))
    row = c.fetchone()
    conn.close()
    return row[0] if row else None

def set_setting(key, value):
    conn = sqlite3.connect('messages.db')
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, value))
    conn.commit()
    conn.close()

def block_user(user_id):
    conn = sqlite3.connect('messages.db')
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO blocked_users (user_id) VALUES (?)", (user_id,))
    conn.commit()
    conn.close()

def unblock_user(user_id):
    conn = sqlite3.connect('messages.db')
    c = conn.cursor()
    c.execute("DELETE FROM blocked_users WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()

def is_blocked(user_id):
    conn = sqlite3.connect('messages.db')
    c = conn.cursor()
    c.execute("SELECT 1 FROM blocked_users WHERE user_id = ?", (user_id,))
    row = c.fetchone()
    conn.close()
    return row is not None

def get_stats():
    conn = sqlite3.connect('messages.db')
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM messages")
    total_messages = c.fetchone()[0]
    c.execute("SELECT COUNT(DISTINCT user_id) FROM messages")
    unique_users = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM messages WHERE replied = FALSE")
    unreplied = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM blocked_users")
    blocked = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM promoted_users")
    admins = c.fetchone()[0]
    conn.close()
    return total_messages, unique_users, unreplied, blocked, admins

def get_username(user_id):
    conn = sqlite3.connect('messages.db')
    c = conn.cursor()
    c.execute("SELECT username FROM messages WHERE user_id = ? ORDER BY id DESC LIMIT 1", (user_id,))
    row = c.fetchone()
    conn.close()
    return row[0] if row else None

def generate_promo_code(generator_id, owner_id, duration_days=None):
    try:
        import random
        import string
        from datetime import timedelta
        if generator_id == owner_id:
            prefix = "OWNER-"
        else:
            prefix = "ADMIN-"
        conn = sqlite3.connect('messages.db', timeout=10)
        c = conn.cursor()
        while True:
            code = prefix + ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
            c.execute("SELECT 1 FROM promo_codes WHERE code = ?", (code,))
            if not c.fetchone():
                break
        expiration = None
        if duration_days:
            expiration = datetime.now() + timedelta(days=duration_days)
        c.execute("INSERT INTO promo_codes (code, expiration) VALUES (?, ?)", (code, expiration))
        conn.commit()
        conn.close()
        return code
    except Exception as e:
        return f"Error: {str(e)}"

def redeem_promo_code(code, user_id):
    conn = sqlite3.connect('messages.db')
    c = conn.cursor()
    c.execute("SELECT used, expiration FROM promo_codes WHERE code = ?", (code,))
    row = c.fetchone()
    if not row or row[0]:
        conn.close()
        return False
    expiration = row[1]
    if expiration:
        try:
            exp_dt = datetime.strptime(expiration.split('.')[0], '%Y-%m-%d %H:%M:%S')
            if exp_dt < datetime.now():
                conn.close()
                return False
        except ValueError:
            # If parsing fails, assume not expired
            pass
    c.execute("UPDATE promo_codes SET used = TRUE WHERE code = ?", (code,))
    c.execute("INSERT OR IGNORE INTO promoted_users (user_id) VALUES (?)", (user_id,))
    conn.commit()
    conn.close()
    return True

def is_promoted(user_id):
    conn = sqlite3.connect('messages.db')
    c = conn.cursor()
    c.execute("SELECT 1 FROM promoted_users WHERE user_id = ?", (user_id,))
    row = c.fetchone()
    conn.close()
    return row is not None

def demote_user(user_id):
    conn = sqlite3.connect('messages.db')
    c = conn.cursor()
    c.execute("DELETE FROM promoted_users WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()

def reset_message_ids():
    try:
        conn = sqlite3.connect('messages.db', timeout=10)
        c = conn.cursor()
        c.execute("UPDATE sqlite_sequence SET seq = 0 WHERE name = 'messages'")
        conn.commit()
        conn.close()
        return True
    except sqlite3.OperationalError as e:
        if "database is locked" in str(e):
            return False
        else:
            raise
