# ============================================================
# utils/audit_logger.py — Registro automático de auditoría
# ============================================================
import json
import logging
from database.connection import get_db
import streamlit as st
from sqlalchemy import text

logger = logging.getLogger(__name__)


def log_action(
    accion: str,
    modulo: str,
    tabla: str = None,
    registro_id=None,
    datos_antes: dict = None,
    datos_despues: dict = None,
):
    """
    Registrar acción de usuario en log de auditoría.
    Llamar en cada operación CRUD exitosa.
    """
    user = st.session_state.get("user", {})
    try:
        with get_db() as db:
            db.execute(text("""
                INSERT INTO auditoria.log_auditoria
                    (usuario_id, username, accion, modulo, tabla,
                     registro_id, datos_antes, datos_despues)
                VALUES
                    (:uid, :uname, :accion, :modulo, :tabla,
                     :rid, :antes::jsonb, :despues::jsonb)
            """), {
                "uid":     user.get("id"),
                "uname":   user.get("username", "sistema"),
                "accion":  accion,
                "modulo":  modulo,
                "tabla":   tabla,
                "rid":     str(registro_id) if registro_id else None,
                "antes":   json.dumps(datos_antes) if datos_antes else None,
                "despues": json.dumps(datos_despues) if datos_despues else None,
            })
    except Exception as e:
        # No propagar error de auditoría para no interrumpir operación principal
        logger.warning(f"Error al registrar auditoría: {e}")