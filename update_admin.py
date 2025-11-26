#!/usr/bin/env python3
import os
import psycopg
import bcrypt
from dotenv import load_dotenv

load_dotenv()

DB_URL = os.environ.get('DATABASE_URL')
ADMIN_USERNAME = 'mamba'
ADMIN_PASSWORD = 'MangoMango67'  # Twoje nowe hasło

if not DB_URL:
    raise ValueError("DATABASE_URL not set")

hashed = bcrypt.hashpw(ADMIN_PASSWORD.encode(), bcrypt.gensalt()).decode()

with psycopg.connect(DB_URL) as conn:
    with conn.cursor() as cur:
        # Nadpisz lub utwórz admina
        cur.execute('''
            INSERT INTO users (username, password, has_access, is_admin)
            VALUES (%s, %s, TRUE, TRUE)
            ON CONFLICT (username)
            DO UPDATE SET password = EXCLUDED.password, has_access = TRUE, is_admin = TRUE
        ''', (ADMIN_USERNAME, hashed))
        conn.commit()

print("Admin user reset successfully!")
