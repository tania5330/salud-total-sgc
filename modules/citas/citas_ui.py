# ============================================================
# modules/citas/citas_ui.py
# ============================================================
import streamlit as st
import pandas as pd
from datetime import date, time, timedelta
from database.connection import execute_query, get_db
from utils.audit_logger import log_action
from utils.auth import require_auth, has_any_role
from sqlalchemy import text


def render_citas():
    require_auth()
    st.title("📅 Gestión de Citas Médicas")
    tab1, tab2, tab3 = st.tabs(["📆 Agenda del Día", "➕ Nueva Cita", "📊 Listado de Citas"])

    with tab1: _render_agenda_dia()
    with tab2:
        if has_any_role("ADMINISTRADOR","RECEPCIONISTA","MEDICO"):
            _render_form_nueva_cita()
        else:
            st.warning("Sin permisos para crear citas.")
    with tab3: _render_listado_citas()


def _render_agenda_dia():
    """Vista de agenda del día con citas por médico."""
    col1, col2 = st.columns([2, 1])
    with col1:
        fecha_sel = st.date_input("Fecha", value=date.today())
    with col2:
        medicos = execute_query("""
            SELECT m.id, m.nombre || ' ' || m.apellido AS nombre_med
            FROM clinica.medicos m WHERE m.activo=TRUE ORDER BY m.nombre
        """)
        med_opts = {"Todos": None} | {m["nombre_med"]: m["id"] for m in medicos}
        med_sel = st.selectbox("Médico", list(med_opts.keys()))

    params = {"fecha": fecha_sel}
    med_filter = ""
    if med_opts[med_sel]:
        med_filter = "AND c.medico_id = :med_id"
        params["med_id"] = med_opts[med_sel]

    citas = execute_query(f"""
        SELECT c.hora_inicio, c.hora_fin,
               p.nombre || ' ' || p.apellido_pat AS paciente,
               p.dni, m.nombre || ' ' || m.apellido AS medico,
               e.nombre AS especialidad,
               c.motivo_consulta, c.estado
        FROM clinica.citas c
        JOIN clinica.pacientes p ON p.id = c.paciente_id
        JOIN clinica.medicos m ON m.id = c.medico_id
        LEFT JOIN clinica.especialidades e ON e.id = m.especialidad_id
        WHERE c.fecha_cita = :fecha {med_filter}
        ORDER BY c.hora_inicio
    """, params)

    if citas:
        # Colorear por estado
        estado_colors = {
            "PROGRAMADA": "🔵", "CONFIRMADA": "🟢", "ATENDIDA": "✅",
            "CANCELADA": "🔴", "NO_SHOW": "🟡"
        }
        df = pd.DataFrame(citas)
        df["estado"] = df["estado"].map(lambda x: f"{estado_colors.get(x,'')} {x}")
        st.dataframe(df, use_container_width=True, hide_index=True)
        st.caption(f"📊 {len(citas)} cita(s) para el {fecha_sel.strftime('%d/%m/%Y')}")
    else:
        st.info("No hay citas programadas para esta fecha.")


def _render_form_nueva_cita():
    """Formulario de nueva cita con validación de disponibilidad."""
    st.subheader("Agendar Nueva Cita")

    medicos = execute_query("""
        SELECT m.id, m.nombre || ' ' || m.apellido || ' — ' || e.nombre AS label
        FROM clinica.medicos m
        JOIN clinica.especialidades e ON e.id = m.especialidad_id
        WHERE m.activo=TRUE ORDER BY m.nombre
    """)
    med_opts = {m["label"]: m["id"] for m in medicos}

    # Cargar horarios para visualizar disponibilidad
    horarios = []
    if medicos:
        med_id_tmp = med_opts[list(med_opts.keys())[0]]
    else:
        med_id_tmp = None

    with st.form("form_cita", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            dni_pac   = st.text_input("DNI del Paciente *")
            med_label = st.selectbox("Médico *", list(med_opts.keys()))
            fecha_c   = st.date_input("Fecha *",
                                       min_value=date.today(),
                                       max_value=date.today() + timedelta(days=60))
        with col2:
            dur_min   = st.number_input("Duración (min)", min_value=10, max_value=120, value=30, step=5)
            hora_ini  = st.time_input("Hora Inicio *", value=time(8, 0))
            # hora_fin calculada según duración
            from datetime import datetime as _dt, timedelta as _td
            hi_dt = _dt.combine(fecha_c, hora_ini)
            hora_fin_calc = (hi_dt + _td(minutes=int(dur_min))).time()
            hora_fin  = st.time_input("Hora Fin", value=hora_fin_calc, disabled=True)
            motivo    = st.text_area("Motivo de Consulta", height=80)

        # Visualizar horario disponible para el día/médico seleccionado
        dia_sem = (fecha_c.weekday() + 0) % 7  # 0=Lunes
        horarios = execute_query("""
            SELECT hora_inicio::TEXT AS hi, hora_fin::TEXT AS hf, duracion_cita_min
            FROM clinica.horarios_medicos
            WHERE medico_id=:mid AND dia_semana=:d AND activo=TRUE
            ORDER BY hora_inicio
        """, {"mid": med_opts[med_label], "d": dia_sem})
        if horarios:
            st.caption("🕐 Horarios disponibles para el día seleccionado")
            st.table(pd.DataFrame(horarios).rename(columns={"hi":"Inicio","hf":"Fin","duracion_cita_min":"Duración (min)"}))

        if st.form_submit_button("📅 Agendar Cita", use_container_width=True):
            # Buscar paciente
            pac = execute_query("SELECT id, nombre, apellido_pat FROM clinica.pacientes WHERE dni=:dni AND activo=TRUE",
                                {"dni": dni_pac})
            if not pac:
                st.error("❌ Paciente no encontrado con ese DNI.")
                return
            # Validación de rango dentro de horario médico
            if not horarios:
                st.error("❌ Error: programación de cita fuera del horario médico disponible, por favor ingrese un horario válido.")
                return
            dentro = False
            for h in horarios:
                hi = _dt.strptime(h["hi"], "%H:%M:%S").time()
                hf = _dt.strptime(h["hf"], "%H:%M:%S").time()
                if hora_ini >= hi and hora_fin <= hf:
                    dentro = True
                    break
            if not dentro:
                st.error("❌ Error: programación de cita fuera del horario médico disponible, por favor ingrese un horario válido.")
                return

            _guardar_cita({
                "pac_id":   pac[0]["id"],
                "med_id":   med_opts[med_label],
                "fecha":    fecha_c,
                "hora_ini": hora_ini,
                "hora_fin": hora_fin,
                "motivo":   motivo,
            })


def _guardar_cita(data: dict):
    """Guardar nueva cita verificando solapamiento."""
    # Verificar solapamiento manualmente antes de insertar
    conflicto = execute_query("""
        SELECT id FROM clinica.citas
        WHERE medico_id = :mid AND fecha_cita = :fecha
          AND estado NOT IN ('CANCELADA','NO_SHOW')
          AND NOT (:hf <= hora_inicio OR :hi >= hora_fin)
    """, {"mid": data["med_id"], "fecha": data["fecha"],
          "hi": data["hora_ini"], "hf": data["hora_fin"]})

    if conflicto:
        st.error("❌ El médico ya tiene una cita en ese horario. Por favor elija otro horario.")
        return

    try:
        with get_db() as db:
            r = db.execute(text("""
                INSERT INTO clinica.citas
                    (paciente_id, medico_id, fecha_cita, hora_inicio, hora_fin,
                     motivo_consulta, created_by)
                VALUES (:pid, :mid, :fc, :hi, :hf, :mot, :uid)
                RETURNING id
            """), {
                "pid": data["pac_id"], "mid": data["med_id"],
                "fc": data["fecha"], "hi": data["hora_ini"], "hf": data["hora_fin"],
                "mot": data["motivo"], "uid": st.session_state.user.get("id"),
            })
            cita_id = r.fetchone()[0]

        log_action("INSERT", "CITAS", "clinica.citas", cita_id, datos_despues=data)
        st.success(f"✅ Cita agendada exitosamente. ID: **{cita_id}**")
    except Exception as e:
        st.error(f"❌ Error al agendar cita: {e}")


def _render_listado_citas():
    """Listado filtrable de citas con opción de cambiar estado."""
    col1, col2, col3 = st.columns(3)
    with col1:
        f_desde = st.date_input("Desde", value=date.today().replace(day=1))
    with col2:
        f_hasta = st.date_input("Hasta", value=date.today())
    with col3:
        estado_f = st.multiselect("Estado", ["PROGRAMADA","CONFIRMADA","ATENDIDA","CANCELADA","NO_SHOW"],
                                   default=["PROGRAMADA","CONFIRMADA"])

    params = {"fd": f_desde, "fh": f_hasta}
    est_filter = ""
    if estado_f:
        est_filter = f"AND c.estado IN ({','.join([repr(e) for e in estado_f])})"

    citas = execute_query(f"""
        SELECT c.id, c.fecha_cita, c.hora_inicio,
               p.nombre || ' ' || p.apellido_pat AS paciente, p.dni,
               m.nombre || ' ' || m.apellido AS medico,
               c.estado, c.motivo_consulta
        FROM clinica.citas c
        JOIN clinica.pacientes p ON p.id = c.paciente_id
        JOIN clinica.medicos m ON m.id = c.medico_id
        WHERE c.fecha_cita BETWEEN :fd AND :fh {est_filter}
        ORDER BY c.fecha_cita DESC, c.hora_inicio
        LIMIT 500
    """, params)

    if citas:
        df = pd.DataFrame(citas)
        st.dataframe(df, use_container_width=True, hide_index=True)
        st.caption(f"Total: {len(citas)} cita(s)")
    else:
        st.info("No se encontraron citas con los filtros seleccionados.")
