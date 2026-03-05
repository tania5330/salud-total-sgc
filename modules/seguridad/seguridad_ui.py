# ============================================================
# modules/seguridad/seguridad_ui.py — Módulo de Seguridad y Auditoría
# Sistema de Gestión Clínica "Salud Total"
# ============================================================
import streamlit as st
import pandas as pd
from datetime import date, timedelta
from database.connection import execute_query, get_db
from utils.auth import require_auth, has_any_role
from utils.audit_logger import log_action
from sqlalchemy import text


def render_seguridad():
    """Renderizar módulo de seguridad, logs de auditoría y sesiones."""
    require_auth()
    if not has_any_role("ADMINISTRADOR"):
        st.error("🔒 Acceso restringido. Solo Administradores pueden acceder a este módulo.")
        return

    st.title("🔐 Seguridad y Auditoría")

    tab1, tab2, tab3 = st.tabs([
        "📋 Log de Auditoría",
        "👥 Sesiones Activas",
        "📊 Estadísticas de Seguridad",
    ])

    with tab1: _render_log_auditoria()
    with tab2: _render_sesiones_activas()
    with tab3: _render_estadisticas_seguridad()


# ─────────────────────────────────────────────────────────────
# Log de Auditoría
# ─────────────────────────────────────────────────────────────

def _render_log_auditoria():
    st.subheader("📋 Registro de Auditoría")

    col1, col2, col3, col4 = st.columns(4)
    with col1: f_desde = st.date_input("Desde", value=date.today() - timedelta(days=7), key="aud_d")
    with col2: f_hasta = st.date_input("Hasta", value=date.today(), key="aud_h")
    with col3:
        usuarios = execute_query("SELECT DISTINCT username FROM auditoria.log_auditoria ORDER BY username")
        user_opts = ["Todos"] + [u["username"] for u in usuarios if u["username"]]
        user_sel = st.selectbox("Usuario", user_opts)
    with col4:
        modulos = execute_query("SELECT DISTINCT modulo FROM auditoria.log_auditoria ORDER BY modulo")
        mod_opts = ["Todos"] + [m["modulo"] for m in modulos]
        mod_sel = st.selectbox("Módulo", mod_opts)

    params = {"fd": f_desde, "fh": f_hasta}
    where_extra = ""
    if user_sel != "Todos":
        where_extra += " AND l.username = :uname"
        params["uname"] = user_sel
    if mod_sel != "Todos":
        where_extra += " AND l.modulo = :modulo"
        params["modulo"] = mod_sel

    logs = execute_query(f"""
        SELECT l.id, l.fecha_hora::TEXT AS fecha_hora,
               COALESCE(l.username, 'sistema') AS usuario,
               l.accion, l.modulo, l.tabla,
               COALESCE(l.registro_id, '—') AS registro_id,
               l.ip_address
        FROM auditoria.log_auditoria l
        WHERE l.fecha_hora::DATE BETWEEN :fd AND :fh
        {where_extra}
        ORDER BY l.fecha_hora DESC
        LIMIT 500
    """, params)

    if not logs:
        st.info("No hay registros de auditoría para los filtros aplicados.")
        return

    df = pd.DataFrame(logs)
    # Colorear por acción
    accion_icons = {"INSERT": "🟢", "UPDATE": "🟡", "DELETE": "🔴", "SELECT": "🔵"}
    df["accion"] = df["accion"].map(lambda x: f"{accion_icons.get(x,'')} {x}")

    st.dataframe(df.drop("id", axis=1), use_container_width=True, hide_index=True)
    st.caption(f"📊 {len(logs)} registro(s) encontrado(s) — Mostrando últimos 500")

    # Detalle de un registro
    st.divider()
    log_id = st.number_input("Ver detalle del registro ID", min_value=1, key="log_detail_id")
    if log_id:
        detalle = execute_query("""
            SELECT * FROM auditoria.log_auditoria WHERE id = :lid
        """, {"lid": log_id})
        if detalle:
            d = detalle[0]
            col_a, col_b = st.columns(2)
            with col_a:
                st.markdown("**Datos Anteriores:**")
                if d.get("datos_antes"):
                    st.json(d["datos_antes"])
                else:
                    st.text("— Sin datos anteriores —")
            with col_b:
                st.markdown("**Datos Nuevos:**")
                if d.get("datos_despues"):
                    st.json(d["datos_despues"])
                else:
                    st.text("— Sin datos nuevos —")


# ─────────────────────────────────────────────────────────────
# Sesiones Activas
# ─────────────────────────────────────────────────────────────

def _render_sesiones_activas():
    st.subheader("👥 Sesiones Activas")

    sesiones = execute_query("""
        SELECT s.id, u.username, u.nombre || ' ' || u.apellido AS nombre,
               s.ip_address, s.creado_en::TEXT AS inicio,
               s.expira_en::TEXT AS expira, s.activo
        FROM seguridad.sesiones s
        JOIN seguridad.usuarios u ON u.id = s.usuario_id
        WHERE s.activo = TRUE AND s.expira_en > NOW()
        ORDER BY s.creado_en DESC
    """)

    if sesiones:
        df = pd.DataFrame(sesiones)
        df["activo"] = df["activo"].map({True: "🟢 Activa", False: "🔴 Cerrada"})
        st.dataframe(df.drop("id", axis=1), use_container_width=True, hide_index=True)
        st.caption(f"🟢 {len(sesiones)} sesión(es) activa(s)")

        # Forzar cierre de sesión
        st.divider()
        st.markdown("**Forzar cierre de sesión:**")
        ses_id = st.text_input("UUID de Sesión a cerrar", key="ses_close_id")
        if st.button("🚫 Cerrar Sesión", type="secondary"):
            if ses_id:
                try:
                    with get_db() as db:
                        db.execute(text("""
                            UPDATE seguridad.sesiones SET activo=FALSE
                            WHERE id=:sid::UUID
                        """), {"sid": ses_id})
                    log_action("UPDATE", "SEGURIDAD", "seguridad.sesiones", ses_id)
                    st.success("✅ Sesión cerrada forzosamente.")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Error: {e}")
    else:
        st.info("No hay sesiones activas en este momento.")

    # Limpiar sesiones expiradas
    if st.button("🧹 Limpiar Sesiones Expiradas", type="secondary"):
        try:
            with get_db() as db:
                r = db.execute(text("""
                    DELETE FROM seguridad.sesiones
                    WHERE activo=FALSE OR expira_en < NOW()
                    RETURNING id
                """))
                cantidad = len(r.fetchall())
            log_action("DELETE", "SEGURIDAD", "seguridad.sesiones")
            st.success(f"✅ {cantidad} sesión(es) expirada(s) eliminada(s).")
        except Exception as e:
            st.error(f"❌ Error: {e}")


# ─────────────────────────────────────────────────────────────
# Estadísticas de seguridad
# ─────────────────────────────────────────────────────────────

def _render_estadisticas_seguridad():
    """Métricas y gráficos de actividad del sistema."""
    import plotly.express as px

    st.subheader("📊 Estadísticas de Actividad")

    col1, col2, col3, col4 = st.columns(4)

    # KPIs de seguridad
    stats = execute_query("""
        SELECT
            (SELECT COUNT(*) FROM auditoria.log_auditoria
             WHERE fecha_hora >= NOW() - INTERVAL '24 hours') AS acciones_24h,
            (SELECT COUNT(*) FROM auditoria.log_auditoria
             WHERE fecha_hora >= NOW() - INTERVAL '24 hours'
               AND accion='DELETE') AS eliminaciones_24h,
            (SELECT COUNT(DISTINCT usuario_id) FROM auditoria.log_auditoria
             WHERE fecha_hora >= NOW() - INTERVAL '24 hours') AS usuarios_activos_hoy,
            (SELECT COUNT(*) FROM seguridad.usuarios WHERE activo=TRUE) AS total_usuarios
    """)
    s = stats[0] if stats else {}

    with col1: st.metric("⚡ Acciones (24h)",   s.get("acciones_24h", 0))
    with col2: st.metric("🗑️ Eliminaciones (24h)", s.get("eliminaciones_24h", 0))
    with col3: st.metric("👤 Usuarios Activos Hoy", s.get("usuarios_activos_hoy", 0))
    with col4: st.metric("👥 Total Usuarios", s.get("total_usuarios", 0))

    st.divider()

    col_a, col_b = st.columns(2)

    with col_a:
        # Acciones por módulo (últimos 30 días)
        por_modulo = execute_query("""
            SELECT modulo, accion, COUNT(*) AS total
            FROM auditoria.log_auditoria
            WHERE fecha_hora >= NOW() - INTERVAL '30 days'
            GROUP BY modulo, accion
            ORDER BY total DESC LIMIT 30
        """)
        if por_modulo:
            df = pd.DataFrame(por_modulo)
            fig = px.bar(df, x="modulo", y="total", color="accion",
                         title="Acciones por Módulo (30 días)",
                         labels={"total": "Cantidad", "modulo": "Módulo"},
                         color_discrete_map={
                             "INSERT": "#27ae60", "UPDATE": "#f39c12",
                             "DELETE": "#e74c3c", "SELECT": "#3498db"
                         })
            fig.update_layout(height=320, margin=dict(t=40, b=20))
            st.plotly_chart(fig, use_container_width=True)

    with col_b:
        # Actividad por usuario (últimos 7 días)
        por_usuario = execute_query("""
            SELECT username, COUNT(*) AS acciones
            FROM auditoria.log_auditoria
            WHERE fecha_hora >= NOW() - INTERVAL '7 days'
              AND username IS NOT NULL
            GROUP BY username
            ORDER BY acciones DESC LIMIT 10
        """)
        if por_usuario:
            df2 = pd.DataFrame(por_usuario)
            fig2 = px.bar(df2, x="acciones", y="username", orientation="h",
                          title="Top 10 Usuarios más Activos (7 días)",
                          labels={"acciones": "Acciones", "username": "Usuario"},
                          color_discrete_sequence=["#1a5276"])
            fig2.update_layout(height=320, margin=dict(t=40, b=20))
            st.plotly_chart(fig2, use_container_width=True)

    # Actividad diaria (últimas 2 semanas)
    actividad_diaria = execute_query("""
        SELECT fecha_hora::DATE AS fecha, accion, COUNT(*) AS total
        FROM auditoria.log_auditoria
        WHERE fecha_hora >= NOW() - INTERVAL '14 days'
        GROUP BY fecha_hora::DATE, accion
        ORDER BY fecha
    """)
    if actividad_diaria:
        df3 = pd.DataFrame(actividad_diaria)
        fig3 = px.line(df3, x="fecha", y="total", color="accion",
                       title="Actividad Diaria del Sistema (14 días)",
                       labels={"total": "Cantidad", "fecha": "Fecha"},
                       color_discrete_map={
                           "INSERT": "#27ae60", "UPDATE": "#f39c12",
                           "DELETE": "#e74c3c", "SELECT": "#3498db"
                       })
        fig3.update_layout(height=280, margin=dict(t=40, b=20))
        st.plotly_chart(fig3, use_container_width=True)
