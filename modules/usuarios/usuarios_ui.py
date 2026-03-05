# ============================================================
# modules/usuarios/usuarios_ui.py — Módulo de Usuarios y Perfiles
# Sistema de Gestión Clínica "Salud Total"
# ============================================================
import streamlit as st
import pandas as pd
from database.connection import execute_query, get_db
from utils.auth import require_auth, has_any_role, hash_password
from utils.audit_logger import log_action
from sqlalchemy import text


def render_usuarios():
    """Renderizar módulo de gestión de usuarios y perfiles."""
    require_auth()
    st.title("👤 Usuarios y Perfiles")

    tab1, tab2, tab3 = st.tabs([
        "👥 Listado de Usuarios",
        "➕ Nuevo Usuario",
        "🔑 Mi Perfil",
    ])

    with tab1:
        if has_any_role("ADMINISTRADOR"):
            _render_lista_usuarios()
        else:
            st.warning("Sin permisos para ver el listado de usuarios.")
    with tab2:
        if has_any_role("ADMINISTRADOR"):
            _render_form_nuevo_usuario()
        else:
            st.warning("Sin permisos para crear usuarios.")
    with tab3:
        _render_mi_perfil()


# ─────────────────────────────────────────────────────────────
# Listado de usuarios
# ─────────────────────────────────────────────────────────────

def _render_lista_usuarios():
    """CRUD de usuarios con asignación de roles."""
    st.subheader("👥 Usuarios del Sistema")

    usuarios = execute_query("""
        SELECT u.id, u.username, u.nombre || ' ' || u.apellido AS nombre_completo,
               u.email, u.activo,
               u.ultimo_acceso::TEXT AS ultimo_acceso,
               COALESCE(STRING_AGG(r.nombre, ', '), 'Sin rol') AS roles
        FROM seguridad.usuarios u
        LEFT JOIN seguridad.usuario_roles ur ON ur.usuario_id = u.id
        LEFT JOIN seguridad.roles r ON r.id = ur.rol_id
        GROUP BY u.id
        ORDER BY u.nombre
    """)

    if not usuarios:
        st.info("No hay usuarios registrados.")
        return

    df = pd.DataFrame(usuarios)
    df["activo"] = df["activo"].map({True: "✅ Activo", False: "❌ Inactivo"})
    st.dataframe(df.drop("id", axis=1), use_container_width=True, hide_index=True)
    st.caption(f"📊 {len(usuarios)} usuario(s) registrado(s)")

    st.divider()
    st.markdown("**Editar roles / estado de un usuario:**")
    filtro_user = st.text_input("🔍 Buscar usuario por nombre o username", key="user_edit_filter")
    candidatos = execute_query("""
        SELECT u.id, u.username, u.nombre, u.apellido
        FROM seguridad.usuarios u
        ORDER BY u.nombre
    """)
    opciones = {f"{u['username']} — {u['nombre']} {u['apellido']} (ID:{u['id']})": u["id"]
                for u in candidatos if (not filtro_user or filtro_user.lower() in f"{u['username']} {u['nombre']} {u['apellido']}".lower())}
    if not opciones:
        st.info("Ingrese un filtro para buscar usuarios.")
        return
    user_id_sel = opciones[st.selectbox("Seleccionar usuario", list(opciones.keys()), key="user_edit_select")]

    if user_id_sel:
        user_info = execute_query("""
            SELECT u.id, u.username, u.nombre, u.apellido, u.email, u.activo,
                   ARRAY_AGG(r.nombre) FILTER (WHERE r.nombre IS NOT NULL) AS roles_actuales
            FROM seguridad.usuarios u
            LEFT JOIN seguridad.usuario_roles ur ON ur.usuario_id = u.id
            LEFT JOIN seguridad.roles r ON r.id = ur.rol_id
            WHERE u.id = :uid
            GROUP BY u.id
        """, {"uid": user_id_sel})

        if not user_info:
            st.warning("Usuario no encontrado.")
            return

        u = user_info[0]
        st.info(f"Editando: **{u['username']}** — {u['nombre']} {u['apellido']}")

        todos_roles = execute_query("SELECT id, nombre FROM seguridad.roles ORDER BY nombre")
        roles_actuales = u["roles_actuales"] or []

        col1, col2 = st.columns(2)
        with col1:
            roles_sel = st.multiselect(
                "Roles asignados",
                options=[r["nombre"] for r in todos_roles],
                default=roles_actuales,
                key="roles_edit",
            )
        with col2:
            nuevo_estado = st.radio(
                "Estado", ["Activo", "Inactivo"],
                index=0 if u["activo"] else 1,
                horizontal=True,
                key="estado_edit",
            )

        col_a, col_b = st.columns(2)
        with col_a:
            if st.button("💾 Guardar Cambios", type="primary", use_container_width=True):
                try:
                    with get_db() as db:
                        # Actualizar estado
                        db.execute(text("""
                            UPDATE seguridad.usuarios
                            SET activo=:act, updated_at=NOW()
                            WHERE id=:uid
                        """), {"act": nuevo_estado == "Activo", "uid": user_id_sel})

                        # Eliminar roles actuales y reasignar
                        db.execute(text("""
                            DELETE FROM seguridad.usuario_roles WHERE usuario_id=:uid
                        """), {"uid": user_id_sel})

                        for rol_nombre in roles_sel:
                            db.execute(text("""
                                INSERT INTO seguridad.usuario_roles (usuario_id, rol_id)
                                SELECT :uid, id FROM seguridad.roles WHERE nombre=:nom
                            """), {"uid": user_id_sel, "nom": rol_nombre})

                    log_action("UPDATE", "USUARIOS", "seguridad.usuarios", user_id_sel,
                               datos_despues={"roles": roles_sel, "activo": nuevo_estado})
                    st.success("✅ Usuario actualizado.")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Error: {e}")

        with col_b:
            if st.button("🔄 Resetear Contraseña", use_container_width=True):
                nueva_pass = f"Salud@{user_id_sel:04d}"
                try:
                    with get_db() as db:
                        db.execute(text("""
                            UPDATE seguridad.usuarios
                            SET password_hash=:ph, updated_at=NOW()
                            WHERE id=:uid
                        """), {"ph": hash_password(nueva_pass), "uid": user_id_sel})
                    log_action("UPDATE", "USUARIOS", "seguridad.usuarios", user_id_sel)
                    st.success(f"✅ Contraseña reseteada a: **{nueva_pass}** (cambiar en el próximo login)")
                except Exception as e:
                    st.error(f"❌ Error: {e}")


# ─────────────────────────────────────────────────────────────
# Crear nuevo usuario
# ─────────────────────────────────────────────────────────────

def _render_form_nuevo_usuario():
    st.subheader("➕ Registrar Nuevo Usuario")

    todos_roles = execute_query("SELECT id, nombre, descripcion FROM seguridad.roles ORDER BY nombre")

    with st.form("form_usuario", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            username = st.text_input("Usuario (login) *", max_chars=50)
            nombre   = st.text_input("Nombres *")
            apellido = st.text_input("Apellidos *")
        with col2:
            email     = st.text_input("Email *")
            password  = st.text_input("Contraseña inicial *", type="password")
            password2 = st.text_input("Confirmar Contraseña *", type="password")

        roles_sel = st.multiselect(
            "Roles *",
            options=[r["nombre"] for r in todos_roles],
            help="Seleccione uno o más roles para este usuario",
        )

        st.caption("La contraseña debe tener al menos 8 caracteres.")

        if st.form_submit_button("💾 Crear Usuario", use_container_width=True, type="primary"):
            errores = []
            if not username:  errores.append("Usuario requerido")
            if not nombre:    errores.append("Nombres requeridos")
            if not apellido:  errores.append("Apellidos requeridos")
            if not email:     errores.append("Email requerido")
            if not password:  errores.append("Contraseña requerida")
            if password != password2: errores.append("Las contraseñas no coinciden")
            if len(password) < 8:     errores.append("La contraseña debe tener al menos 8 caracteres")
            if not roles_sel:         errores.append("Seleccione al menos un rol")

            if errores:
                for e in errores: st.error(f"❌ {e}")
            else:
                # Verificar duplicados
                existe_user  = execute_query("SELECT id FROM seguridad.usuarios WHERE username=:u", {"u": username})
                existe_email = execute_query("SELECT id FROM seguridad.usuarios WHERE email=:e", {"e": email})

                if existe_user:
                    st.error(f"❌ El usuario '{username}' ya existe.")
                elif existe_email:
                    st.error(f"❌ El email '{email}' ya está registrado.")
                else:
                    _crear_usuario({
                        "username": username, "nombre": nombre,
                        "apellido": apellido, "email": email,
                        "password": password, "roles": roles_sel,
                    })


def _crear_usuario(data: dict):
    """Persistir nuevo usuario y asignar roles."""
    try:
        with get_db() as db:
            r = db.execute(text("""
                INSERT INTO seguridad.usuarios
                    (username, email, password_hash, nombre, apellido, created_by)
                VALUES (:user, :email, :ph, :nom, :ape, :uid)
                RETURNING id
            """), {
                "user": data["username"], "email": data["email"],
                "ph": hash_password(data["password"]),
                "nom": data["nombre"], "ape": data["apellido"],
                "uid": st.session_state.user.get("id"),
            })
            nuevo_id = r.fetchone()[0]

            for rol_nombre in data["roles"]:
                db.execute(text("""
                    INSERT INTO seguridad.usuario_roles (usuario_id, rol_id)
                    SELECT :uid, id FROM seguridad.roles WHERE nombre=:nom
                """), {"uid": nuevo_id, "nom": rol_nombre})

        log_action("INSERT", "USUARIOS", "seguridad.usuarios", nuevo_id,
                   datos_despues={"username": data["username"], "roles": data["roles"]})
        st.success(f"✅ Usuario **{data['username']}** creado con roles: {', '.join(data['roles'])}")
    except Exception as e:
        st.error(f"❌ Error al crear usuario: {e}")


# ─────────────────────────────────────────────────────────────
# Mi Perfil
# ─────────────────────────────────────────────────────────────

def _render_mi_perfil():
    """Permitir al usuario editar sus propios datos y contraseña."""
    user = st.session_state.get("user", {})
    user_id = user.get("id")

    st.subheader("🔑 Mi Perfil")

    datos = execute_query("""
        SELECT u.id, u.username, u.nombre, u.apellido, u.email,
               u.ultimo_acceso::TEXT AS ultimo_acceso,
               COALESCE(STRING_AGG(r.nombre, ', '), 'Sin rol') AS roles
        FROM seguridad.usuarios u
        LEFT JOIN seguridad.usuario_roles ur ON ur.usuario_id = u.id
        LEFT JOIN seguridad.roles r ON r.id = ur.rol_id
        WHERE u.id = :uid
        GROUP BY u.id
    """, {"uid": user_id})

    if not datos:
        st.warning("No se pudo cargar el perfil.")
        return

    d = datos[0]

    col1, col2 = st.columns([1, 2])
    with col1:
        # Avatar basado en iniciales
        iniciales = f"{d['nombre'][0]}{d['apellido'][0]}".upper()
        st.markdown(f"""
            <div style="width:80px;height:80px;border-radius:50%;
                        background:linear-gradient(135deg,#1a5276,#2980b9);
                        display:flex;align-items:center;justify-content:center;
                        font-size:28px;font-weight:bold;color:white;margin-bottom:1rem">
                {iniciales}
            </div>
        """, unsafe_allow_html=True)
        st.metric("Roles", d["roles"])
        st.metric("Último acceso", (d.get("ultimo_acceso","—") or "—")[:16])

    with col2:
        with st.form("form_perfil"):
            nom_edit = st.text_input("Nombres",  value=d["nombre"])
            ape_edit = st.text_input("Apellidos", value=d["apellido"])
            email_edit = st.text_input("Email",  value=d["email"])

            if st.form_submit_button("💾 Actualizar Datos", use_container_width=True):
                try:
                    with get_db() as db:
                        db.execute(text("""
                            UPDATE seguridad.usuarios
                            SET nombre=:nom, apellido=:ape, email=:email,
                                updated_at=NOW()
                            WHERE id=:uid
                        """), {"nom": nom_edit, "ape": ape_edit,
                               "email": email_edit, "uid": user_id})
                    # Actualizar session_state
                    st.session_state.user["nombre"]  = nom_edit
                    st.session_state.user["apellido"] = ape_edit
                    log_action("UPDATE", "USUARIOS", "seguridad.usuarios", user_id)
                    st.success("✅ Perfil actualizado.")
                except Exception as e:
                    st.error(f"❌ Error: {e}")

    st.divider()
    st.markdown("**Cambiar Contraseña:**")
    with st.form("form_pass_change", clear_on_submit=True):
        pass_act   = st.text_input("Contraseña Actual", type="password")
        pass_nueva = st.text_input("Nueva Contraseña",  type="password")
        pass_conf  = st.text_input("Confirmar Nueva",   type="password")

        if st.form_submit_button("🔒 Cambiar Contraseña", use_container_width=True):
            from utils.auth import verify_password
            hash_actual = execute_query(
                "SELECT password_hash FROM seguridad.usuarios WHERE id=:uid",
                {"uid": user_id}
            )
            if not hash_actual or not verify_password(pass_act, hash_actual[0]["password_hash"]):
                st.error("❌ La contraseña actual es incorrecta.")
            elif pass_nueva != pass_conf:
                st.error("❌ Las nuevas contraseñas no coinciden.")
            elif len(pass_nueva) < 8:
                st.error("❌ La nueva contraseña debe tener al menos 8 caracteres.")
            else:
                try:
                    with get_db() as db:
                        db.execute(text("""
                            UPDATE seguridad.usuarios
                            SET password_hash=:ph, updated_at=NOW()
                            WHERE id=:uid
                        """), {"ph": hash_password(pass_nueva), "uid": user_id})
                    log_action("UPDATE", "USUARIOS", "seguridad.usuarios", user_id)
                    st.success("✅ Contraseña actualizada correctamente.")
                except Exception as e:
                    st.error(f"❌ Error: {e}")
