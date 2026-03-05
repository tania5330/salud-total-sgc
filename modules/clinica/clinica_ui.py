# ============================================================
# modules/clinica/clinica_ui.py — Módulo de Atención Médica
# Sistema de Gestión Clínica "Salud Total"
# ============================================================
import streamlit as st
import pandas as pd
from datetime import date, datetime
from database.connection import execute_query, get_db
from utils.audit_logger import log_action
from utils.auth import require_auth, has_any_role
from sqlalchemy import text


def render_clinica():
    """Renderizar módulo de atención clínica (consultas, diagnósticos, recetas, exámenes)."""
    require_auth()
    if not has_any_role("ADMINISTRADOR", "MEDICO", "ENFERMERA"):
        st.error("🔒 Acceso restringido al personal médico.")
        return

    st.title("🩺 Atención Médica")

    tab1, tab2, tab3, tab4 = st.tabs([
        "📋 Cola de Atención",
        "✍️ Registrar Consulta",
        "💊 Prescripciones",
        "🔬 Exámenes Solicitados",
    ])

    with tab1:
        _render_cola_atencion()
    with tab2:
        _render_form_consulta()
    with tab3:
        _render_prescripciones()
    with tab4:
        _render_examenes()


# ─────────────────────────────────────────────────────────────
# Cola de atención del día
# ─────────────────────────────────────────────────────────────

def _render_cola_atencion():
    """Listar citas confirmadas del día para atender."""
    st.subheader("📋 Cola de Atención — Hoy")

    col1, col2 = st.columns([2, 1])
    with col1:
        fecha_sel = st.date_input("Fecha", value=date.today(), key="cola_fecha")
    with col2:
        medicos = execute_query("""
            SELECT m.id, m.nombre || ' ' || m.apellido AS nombre_med
            FROM clinica.medicos m WHERE m.activo = TRUE ORDER BY m.nombre
        """)
        med_opts = {"Todos": None} | {m["nombre_med"]: m["id"] for m in medicos}
        med_sel = st.selectbox("Filtrar por médico", list(med_opts.keys()), key="cola_med")

    params = {"fecha": fecha_sel}
    med_filter = ""
    if med_opts.get(med_sel):
        med_filter = "AND c.medico_id = :mid"
        params["mid"] = med_opts[med_sel]

    citas = execute_query(f"""
        SELECT c.id AS cita_id,
               c.hora_inicio, c.hora_fin,
               p.nombre || ' ' || p.apellido_pat AS paciente,
               p.dni, p.numero_hc,
               m.nombre || ' ' || m.apellido AS medico,
               c.motivo_consulta, c.estado,
               CASE WHEN co.id IS NOT NULL THEN '✅ Atendida' ELSE '⏳ Pendiente' END AS consulta_estado
        FROM clinica.citas c
        JOIN clinica.pacientes p ON p.id = c.paciente_id
        JOIN clinica.medicos m ON m.id = c.medico_id
        LEFT JOIN clinica.consultas co ON co.cita_id = c.id
        WHERE c.fecha_cita = :fecha
          AND c.estado IN ('PROGRAMADA','CONFIRMADA','ATENDIDA')
          {med_filter}
        ORDER BY c.hora_inicio
    """, params)

    if not citas:
        st.info("No hay citas programadas para esta fecha.")
        return

    df = pd.DataFrame(citas)
    st.dataframe(df[["hora_inicio","paciente","dni","numero_hc","medico","motivo_consulta","estado","consulta_estado"]],
                 use_container_width=True, hide_index=True)

    # Selección para iniciar atención
    st.divider()
    st.markdown("**Iniciar atención para una cita:**")
    cita_ids = {f"#{c['cita_id']} — {c['paciente']} ({c['hora_inicio']})": c["cita_id"] for c in citas}
    cita_sel = st.selectbox("Seleccionar cita", list(cita_ids.keys()), key="cita_sel_cola")

    if st.button("🚀 Iniciar Atención", type="primary"):
        st.session_state["cita_activa"] = cita_ids[cita_sel]
        st.session_state["page"] = "clinica"
        st.session_state["clinica_tab"] = 1  # Ir a tab de registro
        st.success(f"✅ Cita #{cita_ids[cita_sel]} lista para atender. Ir a la pestaña 'Registrar Consulta'.")


# ─────────────────────────────────────────────────────────────
# Formulario de consulta médica
# ─────────────────────────────────────────────────────────────

def _render_form_consulta():
    """Registrar consulta médica completa con diagnóstico CIE-10."""
    st.subheader("✍️ Registrar Consulta Médica")

    # Buscar paciente para la consulta
    col1, col2 = st.columns([2, 1])
    with col1:
        busq_pac = st.text_input("Buscar paciente por DNI o N° HC", key="cons_busq_pac")
    with col2:
        cita_id_input = st.number_input("O ingresar ID de Cita", min_value=0, value=0, key="cons_cita_id")

    # Si viene de cola de atención
    if st.session_state.get("cita_activa"):
        cita_id_input = st.session_state["cita_activa"]
        st.info(f"📋 Cita activa: #{cita_id_input}")

    paciente_data = None
    cita_data = None

    # Buscar por cita
    if cita_id_input > 0:
        rows = execute_query("""
            SELECT c.id AS cita_id, c.paciente_id, c.medico_id,
                   c.motivo_consulta, c.hora_inicio,
                   p.nombre || ' ' || p.apellido_pat AS pac_nombre,
                   p.dni, p.numero_hc, p.fecha_nacimiento,
                   DATE_PART('year', AGE(p.fecha_nacimiento))::INT AS edad,
                   p.grupo_sanguineo,
                   m.nombre || ' ' || m.apellido AS med_nombre,
                   e.nombre AS especialidad
            FROM clinica.citas c
            JOIN clinica.pacientes p ON p.id = c.paciente_id
            JOIN clinica.medicos m ON m.id = c.medico_id
            JOIN clinica.especialidades e ON e.id = m.especialidad_id
            WHERE c.id = :cid
        """, {"cid": cita_id_input})
        if rows:
            cita_data = rows[0]
            paciente_data = cita_data

    # Buscar por DNI o HC
    elif busq_pac:
        rows = execute_query("""
            SELECT p.id AS paciente_id, p.nombre || ' ' || p.apellido_pat AS pac_nombre,
                   p.dni, p.numero_hc, p.fecha_nacimiento,
                   DATE_PART('year', AGE(p.fecha_nacimiento))::INT AS edad,
                   p.grupo_sanguineo
            FROM clinica.pacientes p
            WHERE (p.dni = :b OR p.numero_hc = :b) AND p.activo = TRUE
            LIMIT 1
        """, {"b": busq_pac.upper()})
        if rows:
            paciente_data = rows[0]

    if not paciente_data:
        st.warning("Ingrese un ID de cita o busque al paciente para continuar.")
        return

    # Mostrar info del paciente
    col_a, col_b, col_c, col_d = st.columns(4)
    with col_a: st.metric("Paciente", paciente_data["pac_nombre"])
    with col_b: st.metric("DNI", paciente_data["dni"])
    with col_c: st.metric("N° HC", paciente_data["numero_hc"])
    with col_d: st.metric("Edad", f"{paciente_data.get('edad','')} años")

    # Cargar antecedentes relevantes
    hist = execute_query("""
        SELECT alergias, medicamentos_habituales FROM clinica.historias_clinicas
        WHERE paciente_id = :pid
    """, {"pid": paciente_data["paciente_id"]})

    if hist and hist[0]["alergias"]:
        st.warning(f"⚠️ **ALERGIAS:** {hist[0]['alergias']}")

    st.divider()

    with st.form("form_consulta", clear_on_submit=False):
        st.markdown("#### 📝 Datos de la Consulta")
        col1, col2 = st.columns(2)
        with col1:
            motivo = st.text_area("Motivo de consulta *", height=80,
                                   value=cita_data.get("motivo_consulta","") if cita_data else "")
            anamnesis = st.text_area("Anamnesis", height=100)
            examen_fisico = st.text_area("Examen Físico", height=100)
        with col2:
            tratamiento = st.text_area("Tratamiento / Plan Terapéutico", height=80)
            indicaciones = st.text_area("Indicaciones al Paciente", height=100)
            sin_prox = st.checkbox("Sin fecha de próximo control", value=False)
            prox_control = None
            if not sin_prox:
                prox_control = st.date_input("Próximo Control", value=date.today(), min_value=date.today())

        st.markdown("#### 🩺 Signos Vitales")
        sv1, sv2, sv3, sv4, sv5, sv6 = st.columns(6)
        with sv1: temp = st.number_input("Temp. °C", 30.0, 45.0, 36.5, 0.1)
        with sv2: pa = st.text_input("P.A.", placeholder="120/80")
        with sv3: fc = st.number_input("F.C. /min", 30, 250, 72)
        with sv4: spo2 = st.number_input("SpO2 %", 50, 100, 98)
        with sv5: peso = st.number_input("Peso kg", 1.0, 300.0, 70.0, 0.1)
        with sv6: talla = st.number_input("Talla cm", 30.0, 250.0, 165.0, 0.5)

        st.markdown("#### 🔬 Diagnóstico CIE-10")
        # Buscar diagnóstico
        cie_busq = st.text_input("Buscar código o descripción CIE-10")
        diagnosticos_sel = []

        if cie_busq:
            cie_rows = execute_query("""
                SELECT id, codigo, descripcion FROM clinica.mantenedor_cie10
                WHERE codigo ILIKE :b OR descripcion ILIKE :b
                LIMIT 20
            """, {"b": f"%{cie_busq}%"})
            if cie_rows:
                cie_opts = {f"{r['codigo']} — {r['descripcion']}": r["id"] for r in cie_rows}
                cie_sel = st.multiselect("Seleccionar diagnóstico(s)", list(cie_opts.keys()))
                tipo_diag = st.radio("Tipo", ["DEFINITIVO", "PRESUNTIVO"], horizontal=True)
                diagnosticos_sel = [(cie_opts[c], tipo_diag) for c in cie_sel]

        estado = st.selectbox("Estado de la Consulta",
                               ["EN_PROCESO", "FINALIZADA", "DERIVADA"])

        # Selección de médico si no proviene de una cita
        med_id_manual = None
        if not cita_data:
            med_rows = execute_query("""
                SELECT m.id, m.nombre || ' ' || m.apellido AS nombre_med
                FROM clinica.medicos m WHERE m.activo=TRUE ORDER BY m.nombre
            """)
            med_opts = {m["nombre_med"]: m["id"] for m in med_rows} if med_rows else {}
            if med_opts:
                med_label = st.selectbox("Médico responsable *", list(med_opts.keys()))
                med_id_manual = med_opts[med_label]

        if st.form_submit_button("💾 Guardar Consulta", use_container_width=True, type="primary"):
            if not motivo:
                st.error("❌ El motivo de consulta es requerido.")
            elif not cita_data and not med_id_manual:
                st.error("❌ Debe seleccionar el médico responsable.")
            else:
                _guardar_consulta({
                    "cita_id":    cita_data["cita_id"] if cita_data else None,
                    "paciente_id": paciente_data["paciente_id"],
                    "medico_id":  cita_data["medico_id"] if cita_data else med_id_manual,
                    "motivo": motivo, "anamnesis": anamnesis,
                    "examen_fisico": examen_fisico, "tratamiento": tratamiento,
                    "indicaciones": indicaciones, "prox_control": prox_control,
                    "temperatura": temp, "presion_arterial": pa,
                    "frecuencia_cardiaca": fc, "saturacion_o2": spo2,
                    "peso_kg": peso, "talla_cm": talla,
                    "estado": estado,
                    "diagnosticos": diagnosticos_sel,
                })


def _guardar_consulta(data: dict):
    """Persistir consulta y diagnósticos en BD."""
    try:
        with get_db() as db:
            r = db.execute(text("""
                INSERT INTO clinica.consultas
                    (cita_id, paciente_id, medico_id, motivo, anamnesis,
                     examen_fisico, tratamiento, indicaciones, prox_control,
                     temperatura, presion_arterial, frecuencia_cardiaca,
                     saturacion_o2, peso_kg, talla_cm, estado)
                VALUES
                    (:cita_id, :pac_id, :med_id, :motivo, :anamnesis,
                     :examen, :trat, :indic, :prox,
                     :temp, :pa, :fc, :spo2, :peso, :talla, :estado)
                RETURNING id
            """), {
                "cita_id": data["cita_id"], "pac_id": data["paciente_id"],
                "med_id": data["medico_id"], "motivo": data["motivo"],
                "anamnesis": data["anamnesis"], "examen": data["examen_fisico"],
                "trat": data["tratamiento"], "indic": data["indicaciones"],
                "prox": data["prox_control"], "temp": data["temperatura"],
                "pa": data["presion_arterial"], "fc": data["frecuencia_cardiaca"],
                "spo2": data["saturacion_o2"], "peso": data["peso_kg"],
                "talla": data["talla_cm"], "estado": data["estado"],
            })
            cons_id = r.fetchone()[0]

            # Insertar diagnósticos
            for cie_id, tipo in data["diagnosticos"]:
                db.execute(text("""
                    INSERT INTO clinica.diagnosticos (consulta_id, cie10_id, tipo)
                    VALUES (:cid, :cie, :tipo)
                """), {"cid": cons_id, "cie": cie_id, "tipo": tipo})

            # Actualizar estado de cita si corresponde
            if data["cita_id"]:
                db.execute(text("""
                    UPDATE clinica.citas SET estado='ATENDIDA', updated_at=NOW()
                    WHERE id=:cid
                """), {"cid": data["cita_id"]})

        log_action("INSERT", "CLINICA", "clinica.consultas", cons_id,
                   datos_despues={"paciente_id": data["paciente_id"]})

        # Guardar ID de consulta en sesión para agregar prescripciones
        st.session_state["consulta_activa"] = cons_id
        st.session_state.pop("cita_activa", None)

        st.success(f"✅ Consulta registrada correctamente. ID: **{cons_id}**")
        st.info("💊 Puede agregar prescripciones en la pestaña 'Prescripciones'.")
    except Exception as e:
        st.error(f"❌ Error al guardar consulta: {e}")


# ─────────────────────────────────────────────────────────────
# Prescripciones médicas
# ─────────────────────────────────────────────────────────────

def _render_prescripciones():
    """Agregar prescripciones médicas a una consulta."""
    st.subheader("💊 Prescripciones Médicas")

    # Seleccionar consulta
    cons_id = st.session_state.get("consulta_activa", 0)
    cons_manual = st.number_input("ID de Consulta", min_value=0,
                                   value=int(cons_id), key="presc_cons_id")
    if cons_manual > 0:
        cons_id = cons_manual

    if not cons_id:
        st.info("Ingrese el ID de la consulta para agregar prescripciones.")
        return

    # Verificar que la consulta existe
    cons = execute_query("""
        SELECT co.id, p.nombre || ' ' || p.apellido_pat AS paciente,
               m.nombre || ' ' || m.apellido AS medico,
               co.fecha_atencion
        FROM clinica.consultas co
        JOIN clinica.pacientes p ON p.id = co.paciente_id
        JOIN clinica.medicos m ON m.id = co.medico_id
        WHERE co.id = :cid
    """, {"cid": cons_id})

    if not cons:
        st.warning("Consulta no encontrada.")
        return

    c = cons[0]
    st.success(f"📋 Consulta #{cons_id} — **{c['paciente']}** | Dr. {c['medico']} | {str(c['fecha_atencion'])[:10]}")

    # Prescripciones existentes
    presc_existentes = execute_query("""
        SELECT pr.id, mm.nombre_generico AS medicamento,
               mm.presentacion, pr.dosis, pr.frecuencia,
               pr.duracion, pr.instrucciones
        FROM clinica.prescripciones pr
        JOIN clinica.mantenedor_medicamentos mm ON mm.id = pr.medicamento_id
        WHERE pr.consulta_id = :cid
        ORDER BY pr.id
    """, {"cid": cons_id})

    if presc_existentes:
        st.markdown("**Prescripciones actuales:**")
        df = pd.DataFrame(presc_existentes)
        st.dataframe(df.drop("id", axis=1), use_container_width=True, hide_index=True)

    st.divider()
    st.markdown("**Agregar medicamento:**")

    # Buscar medicamento
    med_busq = st.text_input("Buscar medicamento", key="med_busq")
    if not med_busq:
        return

    meds = execute_query("""
        SELECT id, nombre_generico, nombre_comercial, presentacion, concentracion, via_admin
        FROM clinica.mantenedor_medicamentos
        WHERE nombre_generico ILIKE :b OR nombre_comercial ILIKE :b
        LIMIT 20
    """, {"b": f"%{med_busq}%"})

    if not meds:
        st.warning("No se encontraron medicamentos. Puede que necesite agregarlos en Mantenedores.")
        return

    med_opts = {
        f"{m['nombre_generico']} — {m['presentacion'] or ''} {m['concentracion'] or ''}": m["id"]
        for m in meds
    }

    with st.form("form_prescripcion", clear_on_submit=True):
        med_sel = st.selectbox("Medicamento", list(med_opts.keys()))
        col1, col2, col3 = st.columns(3)
        with col1: dosis = st.text_input("Dosis *", placeholder="ej: 500mg")
        with col2: frecuencia = st.text_input("Frecuencia *", placeholder="ej: cada 8 horas")
        with col3: duracion = st.text_input("Duración", placeholder="ej: 7 días")
        instrucciones = st.text_area("Instrucciones especiales", height=60)

        if st.form_submit_button("➕ Agregar Prescripción", use_container_width=True):
            if not dosis or not frecuencia:
                st.error("❌ Dosis y frecuencia son requeridas.")
            else:
                try:
                    with get_db() as db:
                        db.execute(text("""
                            INSERT INTO clinica.prescripciones
                                (consulta_id, medicamento_id, dosis, frecuencia, duracion, instrucciones)
                            VALUES (:cid, :mid, :dosis, :freq, :dur, :instr)
                        """), {
                            "cid": cons_id, "mid": med_opts[med_sel],
                            "dosis": dosis, "freq": frecuencia,
                            "dur": duracion, "instr": instrucciones,
                        })
                    log_action("INSERT", "CLINICA", "clinica.prescripciones", cons_id)
                    st.success("✅ Prescripción agregada.")
                except Exception as e:
                    st.error(f"❌ Error: {e}")


# ─────────────────────────────────────────────────────────────
# Exámenes solicitados
# ─────────────────────────────────────────────────────────────

def _render_examenes():
    """Solicitar y actualizar resultados de exámenes."""
    st.subheader("🔬 Exámenes Solicitados")

    tab_a, tab_b = st.tabs(["➕ Solicitar Examen", "📊 Actualizar Resultados"])

    with tab_a:
        cons_id = st.number_input("ID de Consulta", min_value=0, key="exam_cons_id")
        if cons_id <= 0:
            st.info("Ingrese el ID de la consulta.")
            return
        cons = execute_query("""
            SELECT co.id, co.fecha_atencion::TEXT AS fecha,
                   p.nombre || ' ' || p.apellido_pat AS paciente,
                   m.nombre || ' ' || m.apellido AS medico
            FROM clinica.consultas co
            JOIN clinica.pacientes p ON p.id = co.paciente_id
            JOIN clinica.medicos m ON m.id = co.medico_id
            WHERE co.id = :cid
        """, {"cid": cons_id})
        if not cons:
            st.error("❌ Consulta no encontrada. Verifique el ID.")
            return
        cinfo = cons[0]
        st.success(f"📋 Consulta #{cons_id} — {cinfo['paciente']} | Dr. {cinfo['medico']} | {cinfo['fecha']}")

        with st.form("form_examen", clear_on_submit=True):
            tipo = st.selectbox("Tipo de Examen", ["LABORATORIO", "IMAGEN", "OTRO"])
            nombre = st.text_input("Nombre del examen *", placeholder="ej: Hemograma completo")
            indicaciones = st.text_area("Indicaciones / Instrucciones", height=80)
            urgente = st.checkbox("⚠️ Urgente")

            if st.form_submit_button("📋 Solicitar Examen", use_container_width=True):
                if not nombre:
                    st.error("❌ El nombre del examen es requerido.")
                else:
                    try:
                        with get_db() as db:
                            db.execute(text("""
                                INSERT INTO clinica.examenes_solicitados
                                    (consulta_id, tipo_examen, nombre_examen, indicaciones, urgente)
                                VALUES (:cid, :tipo, :nom, :indic, :urg)
                            """), {"cid": cons_id, "tipo": tipo, "nom": nombre,
                                   "indic": indicaciones, "urg": urgente})
                        log_action("INSERT", "CLINICA", "clinica.examenes_solicitados", cons_id)
                        st.success(f"✅ Examen '{nombre}' solicitado correctamente.")
                    except Exception as e:
                        st.error(f"❌ Error: {e}")

    with tab_b:
        st.markdown("**Buscar exámenes pendientes por paciente:**")
        dni_exam = st.text_input("DNI del Paciente", key="exam_dni")
        if not dni_exam:
            return

        examenes = execute_query("""
            SELECT ex.id, ex.nombre_examen, ex.tipo_examen, ex.urgente,
                   ex.estado, ex.indicaciones, ex.resultado,
                   co.fecha_atencion::TEXT AS fecha
            FROM clinica.examenes_solicitados ex
            JOIN clinica.consultas co ON co.id = ex.consulta_id
            JOIN clinica.pacientes p ON p.id = co.paciente_id
            WHERE p.dni = :dni AND ex.estado != 'COMPLETADO'
            ORDER BY ex.id DESC
        """, {"dni": dni_exam})

        if not examenes:
            st.info("No hay exámenes pendientes para este paciente.")
            return

        for ex in examenes:
            with st.expander(f"{'⚠️' if ex['urgente'] else '🔬'} [{ex['tipo_examen']}] {ex['nombre_examen']} — {ex['estado']}"):
                resultado = st.text_area("Resultado", value=ex.get("resultado","") or "",
                                          key=f"res_{ex['id']}", height=80)
                if st.button("💾 Guardar Resultado", key=f"btn_res_{ex['id']}"):
                    try:
                        with get_db() as db:
                            db.execute(text("""
                                UPDATE clinica.examenes_solicitados
                                SET resultado=:res, estado='COMPLETADO',
                                    fecha_resultado=NOW(), updated_at=NOW()
                                WHERE id=:id
                            """), {"res": resultado, "id": ex["id"]})
                        log_action("UPDATE", "CLINICA", "clinica.examenes_solicitados", ex["id"])
                        st.success("✅ Resultado guardado.")
                    except Exception as e:
                        st.error(f"❌ Error: {e}")
