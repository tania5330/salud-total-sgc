# ============================================================
# utils/auth.py — Autenticación JWT + bcrypt
# ============================================================
import bcrypt
import jwt
from datetime import datetime, timedelta
from typing import Optional
import streamlit as st
from config import SECRET_KEY, JWT_ALGORITHM, JWT_EXPIRE_HOURS, BCRYPT_ROUNDS
from database.connection import execute_query


def hash_password(plain: str) -> str:
    """Generar hash bcrypt de una contraseña en texto plano."""
    salt = bcrypt.gensalt(rounds=BCRYPT_ROUNDS)
    return bcrypt.hashpw(plain.encode(), salt).decode()


def verify_password(plain: str, hashed: str) -> bool:
    """Verificar contraseña contra su hash almacenado."""
    return bcrypt.checkpw(plain.encode(), hashed.encode())


def create_token(user_id: int, username: str, roles: list) -> str:
    """Generar JWT con expiración configurable."""
    payload = {
        "sub":      str(user_id),
        "username": username,
        "roles":    roles,
        "exp":      datetime.utcnow() + timedelta(hours=JWT_EXPIRE_HOURS),
        "iat":      datetime.utcnow(),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=JWT_ALGORITHM)


def decode_token(token: str) -> Optional[dict]:
    """Decodificar y validar JWT. Retorna payload o None si es inválido/expirado."""
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


def authenticate_user(username: str, password: str) -> Optional[dict]:
    """Autenticar usuario contra BD. Retorna dict del usuario o None."""
    rows = execute_query("""
        SELECT u.id, u.username, u.email, u.nombre, u.apellido,
               u.password_hash, u.activo,
               array_agg(r.nombre) AS roles
        FROM seguridad.usuarios u
        LEFT JOIN seguridad.usuario_roles ur ON ur.usuario_id = u.id
        LEFT JOIN seguridad.roles r ON r.id = ur.rol_id
        WHERE u.username = :username AND u.activo = TRUE
        GROUP BY u.id
    """, {"username": username})

    if not rows:
        return None
    user = rows[0]
    if not verify_password(password, user["password_hash"]):
        return None
    return user


def require_auth():
    """Guard de autenticación para páginas protegidas. Redirige al login si no hay sesión."""
    if "user" not in st.session_state or not st.session_state.user:
        st.error("🔒 Sesión no iniciada. Por favor ingrese al sistema.")
        st.stop()


def has_role(role: str) -> bool:
    """Verificar si el usuario actual tiene un rol específico."""
    user = st.session_state.get("user", {})
    return role in (user.get("roles") or [])


def has_any_role(*roles) -> bool:
    """Verificar si el usuario actual tiene al menos uno de los roles dados."""
    return any(has_role(r) for r in roles)