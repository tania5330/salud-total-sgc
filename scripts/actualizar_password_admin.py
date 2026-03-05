# ============================================================
# scripts/actualizar_password_admin.py
# Genera el hash y actualiza la contraseña del admin en la BD.
# Necesita DATABASE_URL en .env (o variables DB_*) o como argumento.
# Uso: python scripts/actualizar_password_admin.py "MiNuevaContraseña"
#      python scripts/actualizar_password_admin.py
# ============================================================
import sys
import os

# Añadir la raíz del proyecto al path para importar config y database
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

import bcrypt
from sqlalchemy import create_engine, text

BCRYPT_ROUNDS = 12


def get_database_url():
    url = os.getenv("DATABASE_URL") or os.getenv("POSTGRES_URL") or os.getenv("POSTGRESQL_URL")
    if url and url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql+psycopg2://", 1)
    if not url:
        host = os.getenv("DB_HOST", "localhost")
        port = os.getenv("DB_PORT", "5432")
        name = os.getenv("DB_NAME", "salud_total")
        user = os.getenv("DB_USER", "postgres")
        pwd = os.getenv("DB_PASSWORD", "")
        from urllib.parse import quote_plus
        cred = f"{quote_plus(user)}:{quote_plus(pwd)}@" if user or pwd else ""
        url = f"postgresql+psycopg2://{cred}{host}:{port}/{name}"
    return url


def main():
    if len(sys.argv) > 1:
        password = sys.argv[1]
    else:
        password = input("Nueva contraseña para el usuario admin: ").strip()
    if not password:
        print("No se ingresó contraseña.")
        sys.exit(1)

    hash_str = bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=BCRYPT_ROUNDS)).decode()
    url = get_database_url()

    try:
        engine = create_engine(url)
        with engine.begin() as conn:
            r = conn.execute(
                text("UPDATE seguridad.usuarios SET password_hash = :h WHERE username = 'admin'"),
                {"h": hash_str},
            )
            if r.rowcount == 0:
                print("No existe un usuario 'admin' en seguridad.usuarios.")
                sys.exit(1)
        print("Contraseña del usuario 'admin' actualizada correctamente.")
    except Exception as e:
        print("Error al conectar o actualizar:", e)
        sys.exit(1)


if __name__ == "__main__":
    main()
