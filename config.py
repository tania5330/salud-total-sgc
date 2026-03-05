# ============================================================
# config.py — Configuración central del sistema
# ============================================================
import os
from dotenv import load_dotenv
from urllib.parse import quote_plus

load_dotenv()

# URL directa para despliegues (Render, etc.)
_raw_database_url = (
    os.getenv("DATABASE_URL")
    or os.getenv("POSTGRES_URL")
    or os.getenv("POSTGRESQL_URL")
)

# Leer desde Streamlit Secrets si está disponible
if not _raw_database_url:
    try:
        import streamlit as st
        if "DATABASE_URL" in st.secrets:
            _raw_database_url = st.secrets["DATABASE_URL"]
    except Exception:
        pass

# ── Base de datos ──────────────────────────────────────────
DB_CONFIG = {
    "host":     os.getenv("DB_HOST", "localhost"),
    "port":     int(os.getenv("DB_PORT", 5432)),
    "database": os.getenv("DB_NAME", "salud_total"),
    "user":     os.getenv("DB_USER", "postgres"),
    "password": os.getenv("DB_PASSWORD", ""),
}

if _raw_database_url:
    if _raw_database_url.startswith("postgres://"):
        _raw_database_url = _raw_database_url.replace(
            "postgres://", "postgresql+psycopg2://", 1
        )
    if "render.com" in _raw_database_url and "sslmode" not in _raw_database_url:
        _raw_database_url += "?sslmode=require" if "?" not in _raw_database_url else "&sslmode=require"
    DATABASE_URL = _raw_database_url
else:
    _user = quote_plus(DB_CONFIG["user"]) if DB_CONFIG["user"] else ""
    _pwd  = quote_plus(DB_CONFIG["password"]) if DB_CONFIG["password"] else ""
    _cred = f"{_user}:{_pwd}@" if _user or _pwd else ""
    DATABASE_URL = (
        f"postgresql+psycopg2://{_cred}"
        f"{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}"
    )

# ── Seguridad ──────────────────────────────────────────────
SECRET_KEY       = os.getenv("SECRET_KEY") or None
if not SECRET_KEY:
    try:
        import streamlit as st
        SECRET_KEY = st.secrets.get("SECRET_KEY", None)
    except Exception:
        SECRET_KEY = None
if not SECRET_KEY:
    SECRET_KEY = "cambia-este-secreto-en-produccion"
JWT_ALGORITHM    = "HS256"
JWT_EXPIRE_HOURS = int(os.getenv("JWT_EXPIRE_HOURS", 8))
BCRYPT_ROUNDS    = 12

# ── Aplicación ─────────────────────────────────────────────
APP_NAME    = "Salud Total — Sistema de Gestión Clínica"
APP_VERSION = "1.0.0"
DEBUG       = os.getenv("DEBUG", "false").lower() == "true"

# ── Backup ─────────────────────────────────────────────────
BACKUP_DIR = os.getenv("BACKUP_DIR", "./backups")

# ── Paginación ─────────────────────────────────────────────
PAGE_SIZE = 20
