# ============================================================
# scripts/generar_hash_password.py
# Genera un hash bcrypt para actualizar la contraseña del admin en la BD.
# Uso: python scripts/generar_hash_password.py
#      python scripts/generar_hash_password.py "MiNuevaContraseña"
# ============================================================
import sys
import bcrypt

# Mismo valor que en config (12)
BCRYPT_ROUNDS = 12


def main():
    if len(sys.argv) > 1:
        password = sys.argv[1]
    else:
        password = input("Escriba la nueva contraseña para el usuario admin: ").strip()
        if not password:
            print("No se ingresó contraseña.")
            sys.exit(1)

    salt = bcrypt.gensalt(rounds=BCRYPT_ROUNDS)
    hash_str = bcrypt.hashpw(password.encode(), salt).decode()

    print("\n--- Hash generado (copie todo entre las comillas) ---")
    print(hash_str)
    print("---\n")
    print("SQL para actualizar en la BD (reemplace EL_HASH por el de arriba):")
    print("UPDATE seguridad.usuarios SET password_hash = '" + hash_str + "' WHERE username = 'admin';")
    print()


if __name__ == "__main__":
    main()
