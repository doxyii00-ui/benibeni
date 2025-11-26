# update_admin.py

import psycopg
import bcrypt

# Ustaw swoje dane połączenia z bazą
DB_HOST = "localhost"       # lub adres Twojego serwera
DB_PORT = 5432
DB_NAME = "nazwa_bazy"
DB_USER = "uzytkownik"
DB_PASSWORD = "haslo_bazy"

# Nowe hasło admina
NEW_ADMIN_PASSWORD = "MangoMango67"

def update_admin_password():
    try:
        # Połączenie z bazą
        with psycopg.connect(
            host=DB_HOST,
            port=DB_PORT,
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD
        ) as conn:
            with conn.cursor() as cur:
                # Tworzymy hash hasła bcrypt
                hashed_pw = bcrypt.hashpw(NEW_ADMIN_PASSWORD.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

                # Sprawdzamy czy użytkownik już istnieje
                cur.execute("SELECT id FROM users WHERE username = %s", ("mamba",))
                result = cur.fetchone()
                
                if result:
                    # Aktualizujemy hasło
                    cur.execute(
                        "UPDATE users SET password = %s WHERE username = %s",
                        (hashed_pw, "mamba")
                    )
                    print("Hasło admina zostało zaktualizowane!")
                else:
                    # Tworzymy nowego admina
                    cur.execute(
                        "INSERT INTO users (username, password, has_access, is_admin) VALUES (%s, %s, %s, %s)",
                        ("mamba", hashed_pw, True, True)
                    )
                    print("Admin 'mamba' został utworzony!")

                conn.commit()
    except Exception as e:
        print("Wystąpił błąd:", e)

if __name__ == "__main__":
    update_admin_password()
