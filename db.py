# db.py
import psycopg
from psycopg.rows import dict_row


def get_db():
    conn = psycopg.connect("dbname=mydb user=myuser password=mypass")
    return conn

def init_db(app):
    # tutaj możesz stworzyć tabele przy starcie aplikacji
    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS documents (
                id SERIAL PRIMARY KEY,
                user_id INT,
                name TEXT,
                surname TEXT,
                pesel TEXT
            );
        """)
