# ============================================================
# modules/personal/personal_ui.py — Módulo de Personal Médico
# Sistema de Gestión Clínica "Salud Total"
# ============================================================
import streamlit as st
import pandas as pd
from database.connection import execute_query, get_db
from utils.audit_logger import log_action
from utils.auth import require_auth, has_any_role
from sqlalchemy import text


def render_personal():
    """Renderizar módulo de gestión de personal médico y administrativo."""
    require_auth()
    if not has_any_role("ADMINISTRADOR"):
        st.error("🔒 Acceso restringido. Solo el Administrador puede gestionar el personal.")
        return

    st.title("👨‍⚕️ Personal Médico")

    tab1, tab2, tab3 = st.tabs([
        "👥 Listado de Médicos",
        "➕ Registrar Médico",
        "🕐 Horarios de Atención",
    ])

    with tab1: _render_lista_medicos()
    with tab2: _render_form_nuevo_medico()
    with tab3: _render_horarios()


# ─────────────────────────────────────────────────────────────
# Listado de médicos
# ─────────────────────────────────────────────────────────────

def _render_lista_medicos():
    """Listado filtrable de médicos con indicadores de productividad."""
    col1, col2 = st.columns([3, 1])
    with col1:
        busqueda = st.text_input("🔍 Buscar por nombre, DNI o CMP", key="med_busq")
    with col2:
        esp_rows = execute_query("SELECT id, nombre FROM clinica.especialidades WHERE activo=TRUE ORDER BY nombre")
        esp_opts = {"Todas": None} | {e["nombre"]: e["id"] for e in esp_rows}
        esp_sel = st.selectbox("Especialidad", list(esp_opts.keys()))

    params = {}
    where = []
    if busqueda:
        where.append("(m.nombre ILIKE :b OR m.apellido ILIKE :b OR m.dni ILIKE :b OR m.cmp ILIKE :b)")
        params["b"] = f"%{busqueda}%"
    if esp_opts.get(esp_sel):
        where.append("m.especialidad_id = :eid")
        params["eid"] = esp_opts[esp_sel]

    where_sql = ("WHERE " + " AND ".join(where)) if where else ""

    medicos = execute_query(f"""
        SELECT m.id, m.cmp, m.dni,
               m.nombre || ' ' || m.apellido AS nombre_completo,
               e.nombre AS especialidad,
               m.telefono, m.email, m.activo,
               COUNT(DISTINCT c.id) AS total_citas_mes
        FROM clinica.medicos m
        LEFT JOIN clinica.especialidades e ON e.id = m.especialidad_id
        LEFT JOIN clinica.citas c ON c.medico_id = m.id
            AND DATE_TRUNC('month', c.fecha_cita) = DATE_TRUNC('month', NOW())
            AND c.estado = 'ATENDIDA'
        {where_sql}
        GROUP BY m.id, e.nombre
        ORDER BY m.nombre
    """, params)

    if not medicos:
        st.info("No se encontraron médicos con los filtros aplicados.")
        return

    df = pd.DataFrame(medicos)
    df["activo"] = df["activo"].map({True: "✅ Activo", False: "❌ Inactivo"})
    df.rename(columns={"total_citas_mes": "Consultas este mes"}, inplace=True)
    st.dataframe(df.drop("id", axis=1), use_container_width=True, hide_index=True)
    st.caption(f"📊 {len(medicos)} médico(s) registrado(s)")

    # Edición rápida de estado con buscador
    st.divider()
    st.markdown("**Cambiar estado de un médico:**")
    nombres = {f"{m['nombre_completo']} — {m['especialidad']} (ID:{m['id']})": m["id"] for m in medicos}
    filtro = st.text_input("Filtrar por nombre", key="med_estado_filtro")
    opciones = [k for k in nombres.keys() if (filtro.lower() in k.lower())] if filtro else list(nombres.keys())
    med_sel_label = st.selectbox("Seleccionar Médico", opciones, key="med_estado_sel")
    med_id_edit = nombres[med_sel_label] if opciones else None
    new_estado = st.radio("Nuevo estado", ["Activo", "Inactivo"], horizontal=True)

    if st.button("💾 Actualizar Estado") and med_id_edit:
        try:
            with get_db() as db:
                db.execute(text("""
                    UPDATE clinica.medicos SET activo=:act, updated_at=NOW()
                    WHERE id=:id
                """), {"act": new_estado == "Activo", "id": med_id_edit})
            log_action("UPDATE", "PERSONAL", "clinica.medicos", med_id_edit)
            st.success("✅ Estado actualizado.")
        except Exception as e:
            st.error(f"❌ Error: {e}")


# ─────────────────────────────────────────────────────────────
# Formulario de registro de médico
# ─────────────────────────────────────────────────────────────

def _render_form_nuevo_medico():
    """Formulario de registro de nuevo médico."""
    st.subheader("Registrar Nuevo Médico")

    esp_rows = execute_query("SELECT id, nombre FROM clinica.especialidades WHERE activo=TRUE ORDER BY nombre")
    esp_opts = {e["nombre"]: e["id"] for e in esp_rows}

    usuarios = execute_query("""
        SELECT u.id, u.username || ' — ' || u.nombre || ' ' || u.apellido AS label
        FROM seguridad.usuarios u
        LEFT JOIN clinica.medicos m ON m.usuario_id = u.id
        WHERE m.id IS NULL AND u.activo = TRUE
        ORDER BY u.nombre
    """)
    usr_opts = {"Sin vincular": None} | {u["label"]: u["id"] for u in usuarios}

    with st.form("form_medico", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            nombre   = st.text_input("Nombres *")
            apellido = st.text_input("Apellidos *")
            dni      = st.text_input("DNI *", max_chars=20)
            cmp      = st.text_input("N° CMP (Colegio Médico) *", max_chars=20)
        with col2:
            esp_sel  = st.selectbox("Especialidad *", list(esp_opts.keys()))
            telefono = st.text_input("Teléfono")
            email    = st.text_input("Email")
            usr_sel  = st.selectbox("Vincular a usuario del sistema", list(usr_opts.keys()))

        if st.form_submit_button("💾 Registrar Médico", use_container_width=True, type="primary"):
            errores = []
            if not nombre:   errores.append("Nombres requerido")
            if not apellido: errores.append("Apellidos requerido")
            if not dni:      errores.append("DNI requerido")
            if not cmp:      errores.append("CMP requerido")

            if errores:
                for e in errores: st.error(f"❌ {e}")
            else:
                # Verificar duplicados
                existe_dni = execute_query("SELECT id FROM clinica.medicos WHERE dni=:d", {"d": dni})
                existe_cmp = execute_query("SELECT id FROM clinica.medicos WHERE cmp=:c", {"c": cmp})

                if existe_dni:
                    st.error(f"❌ Ya existe un médico con DNI: {dni}")
                elif existe_cmp:
                    st.error(f"❌ Ya existe un médico con CMP: {cmp}")
                else:
                    _guardar_medico({
                        "nombre": nombre, "apellido": apellido, "dni": dni,
                        "cmp": cmp, "esp_id": esp_opts[esp_sel],
                        "telefono": telefono, "email": email,
                        "usuario_id": usr_opts.get(usr_sel),
                    })


def _guardar_medico(data: dict):
    """Persistir nuevo médico en BD."""
    try:
        with get_db() as db:
            r = db.execute(text("""
                INSERT INTO clinica.medicos
                    (nombre, apellido, dni, cmp, especialidad_id,
                     telefono, email, usuario_id, created_by)
                VALUES (:nom, :ape, :dni, :cmp, :eid, :tel, :email, :uid, :cby)
                RETURNING id
            """), {
                "nom": data["nombre"], "ape": data["apellido"],
                "dni": data["dni"], "cmp": data["cmp"],
                "eid": data["esp_id"], "tel": data["telefono"],
                "email": data["email"], "uid": data["usuario_id"],
                "cby": st.session_state.user.get("id"),
            })
            med_id = r.fetchone()[0]

        log_action("INSERT", "PERSONAL", "clinica.medicos", med_id,
                   datos_despues={"nombre": data["nombre"], "cmp": data["cmp"]})
        st.success(f"✅ Médico registrado correctamente. ID: **{med_id}**")
    except Exception as e:
        st.error(f"❌ Error al registrar médico: {e}")


# ─────────────────────────────────────────────────────────────
# Horarios de atención
# ─────────────────────────────────────────────────────────────

def _render_horarios():
    """Gestionar horarios de atención por médico."""
    st.subheader("🕐 Horarios de Atención")

    medicos = execute_query("""
        SELECT m.id, m.nombre || ' ' || m.apellido || ' (' || e.nombre || ')' AS label
        FROM clinica.medicos m
        JOIN clinica.especialidades e ON e.id = m.especialidad_id
        WHERE m.activo = TRUE ORDER BY m.nombre
    """)
    if not medicos:
        st.warning("No hay médicos registrados.")
        return

    med_opts = {m["label"]: m["id"] for m in medicos}
    med_sel = st.selectbox("Seleccionar Médico", list(med_opts.keys()))
    med_id = med_opts[med_sel]

    # Mostrar horarios actuales
    horarios = execute_query("""
        SELECT id, dia_semana, hora_inicio, hora_fin, duracion_cita_min, activo
        FROM clinica.horarios_medicos
        WHERE medico_id = :mid ORDER BY dia_semana, hora_inicio
    """, {"mid": med_id})

    DIAS = {0: "Lunes", 1: "Martes", 2: "Miércoles", 3: "Jueves",
            4: "Viernes", 5: "Sábado", 6: "Domingo"}

    if horarios:
        df = pd.DataFrame(horarios)
        df["dia_semana"] = df["dia_semana"].map(DIAS)
        df["activo"] = df["activo"].map({True: "✅", False: "❌"})
        st.dataframe(df.drop("id", axis=1), use_container_width=True, hide_index=True)
    else:
        st.info("Este médico no tiene horarios registrados.")

    st.divider()
    st.markdown("**Agregar / Modificar Horario:**")

    with st.form("form_horario", clear_on_submit=True):
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            dia = st.selectbox("Día", list(DIAS.values()))
        with col2:
            import datetime
            h_ini = st.time_input("Hora Inicio", value=datetime.time(8, 0))
        with col3:
            h_fin = st.time_input("Hora Fin", value=datetime.time(17, 0))
        with col4:
            dur_cita = st.number_input("Duración cita (min)", min_value=10,
                                        max_value=120, value=30, step=5)

        if st.form_submit_button("💾 Guardar Horario", use_container_width=True):
            if h_fin <= h_ini:
                st.error("❌ La hora de fin debe ser posterior a la de inicio.")
            else:
                dia_num = list(DIAS.keys())[list(DIAS.values()).index(dia)]
                try:
                    with get_db() as db:
                        # Upsert: si ya existe ese día, actualizar
                        db.execute(text("""
                            INSERT INTO clinica.horarios_medicos
                                (medico_id, dia_semana, hora_inicio, hora_fin, duracion_cita_min)
                            VALUES (:mid, :dia, :hi, :hf, :dur)
                            ON CONFLICT DO NOTHING
                        """), {"mid": med_id, "dia": dia_num,
                               "hi": h_ini, "hf": h_fin, "dur": dur_cita})
                    log_action("INSERT", "PERSONAL", "clinica.horarios_medicos", med_id)
                    st.success(f"✅ Horario del {dia} guardado.")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Error: {e}")
