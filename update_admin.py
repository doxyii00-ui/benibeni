import os
import psycopg
import bcrypt
from dotenv import load_dotenv

load_dotenv()

# Pobieramy dane do połączenia z bazy
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")

# Nowe hasło dla admina
NEW_ADMIN_PASSWORD = "MangoMango67"  # <-- ustaw tu swoje hasło

# Funkcja generująca hash zgodny z bcrypt
def generate_bcrypt_hash(password: str) -> str:
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
    return hashed.decode("utf-8")

hashed_password = generate_bcrypt_hash(NEW_ADMIN_PASSWORD)

# Aktualizacja admina w bazie
with psycopg.connect(
    host=DB_HOST, port=DB_PORT, dbname=DB_NAME, user=DB_USER, password=DB_PASSWORD
) as conn:
    with conn.cursor() as cur:
        # Sprawdź czy admin istnieje
        cur.execute("SELECT id FROM admins WHERE username = 'mamba'")
        if cur.rowcount == 0:
            # Tworzymy admina jeśli nie istnieje
            cur.execute(
                "INSERT INTO admins (username, password) VALUES (%s, %s)",
                ("mamba", hashed_password)
            )
            print("Admin 'mamba' utworzony.")
        else:
            # Nadpisujemy hasło
            cur.execute(
                "UPDATE admins SET password = %s WHERE username = 'mamba'",
                (hashed_password,)
            )
            print("Hasło admina 'mamba' zaktualizowane.")

print("Gotowe! Teraz możesz się zalogować używając nowego hasła.")
