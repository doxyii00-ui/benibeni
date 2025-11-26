#!/usr/bin/env python3
import os
import psycopg
import bcrypt
from dotenv import load_dotenv

load_dotenv()

DB_URL = os.environ.get('DATABASE_URL')
if not DB_URL:
    raise ValueError("DATABASE_URL not set")

ADMIN_USERNAME = 'mamba'
ADMIN_PASSWORD = 'MangoMango67'  # nowe hasło

hashed = bcrypt.hashpw(ADMIN_PASSWORD.encode(), bcrypt.gensalt()).decode()

conn = psycopg.connect(DB_URL)
cur = conn.cursor()

# Sprawdź, czy admin istnieje
cur.execute('SELECT id FROM users WHERE username=%s', (ADMIN_USERNAME,))
row = cur.fetchone()

if row:
    cur.execute('UPDATE users SET password=%s, has_access=TRUE, is_admin=TRUE WHERE username=%s', (hashed, ADMIN_USERNAME))
    print(f"Admin '{ADMIN_USERNAME}' updated with new password")
else:
    cur.execute('INSERT INTO users (username, password, has_access, is_admin) VALUES (%s, %s, TRUE, TRUE)', (ADMIN_USERNAME, hashed))
    print(f"Admin '{ADMIN_USERNAME}' created")

conn.commit()
cur.close()
conn.close()
