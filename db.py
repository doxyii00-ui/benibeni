import os
import psycopg
from psycopg.rows import dict_row

DATABASE_URL = os.environ.get("DATABASE_URL")

def get_db():
    try:
        conn = psycopg.connect(DATABASE_URL, row_factory=dict_row)
        return conn
    except psycopg.OperationalError as e:
        print("Błąd połączenia z bazą:", e)
        raise

def init_db():
    conn = get_db()
    cur = conn.cursor()
    
    # Tabela użytkowników
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        );
    """)
    
    # Tabela wygenerowanych dokumentów
    cur.execute("""
        CREATE TABLE IF NOT EXISTS generated_documents (
            id SERIAL PRIMARY KEY,
            user_id INT REFERENCES users(id),
            content TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    
    # Sprawdź admina
    cur.execute("SELECT * FROM users WHERE username='mamba';")
    if cur.rowcount == 0:
        cur.execute("INSERT INTO users (username, password) VALUES (%s, %s);", ("mamba", "mypass"))
    
    conn.commit()
    cur.close()
    conn.close()
    print("✓ Database initialized successfully!")
