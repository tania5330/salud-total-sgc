# ============================================================
# modules/pacientes/pacientes_ui.py
# ============================================================
import streamlit as st
import pandas as pd
from database.connection import execute_query, get_db
from utils.audit_logger import log_action
from utils.auth import require_auth, has_any_role
from sqlalchemy import text
from datetime import date


def render_pacientes():
    """Renderizar módulo completo de gestión de pacientes."""
    require_auth()
    st.title("👥 Gestión de Pacientes")

    tab1, tab2, tab3 = st.tabs(["🔍 Buscar / Listar", "➕ Nuevo Paciente", "📋 Historia Clínica"])

    with tab1:
        _render_lista_pacientes()
    with tab2:
        if has_any_role("ADMINISTRADOR", "RECEPCIONISTA", "MEDICO"):
            _render_form_nuevo_paciente()
        else:
            st.warning("No tiene permisos para registrar pacientes.")
    with tab3:
        _render_historia_clinica()


def _render_lista_pacientes():
    """Búsqueda avanzada y listado paginado de pacientes."""
    col1, col2, col3 = st.columns([3, 2, 1])
    with col1:
        busqueda = st.text_input("🔍 Buscar por nombre, DNI o N° HC", key="pac_busqueda")
    with col2:
        estado_filtro = st.selectbox("Estado", ["Todos", "Activos", "Inactivos"])
    with col3:
        st.write("")
        st.write("")
        buscar = st.button("Buscar", use_container_width=True)

    # Construir query con filtros
    where_clauses = []
    params = {}
    if busqueda:
        where_clauses.append("""
            (p.dni ILIKE :busq OR p.numero_hc ILIKE :busq
             OR (p.nombre || ' ' || p.apellido_pat) ILIKE :busq)
        """)
        params["busq"] = f"%{busqueda}%"
    if estado_filtro == "Activos":
        where_clauses.append("p.activo = TRUE")
    elif estado_filtro == "Inactivos":
        where_clauses.append("p.activo = FALSE")

    where_sql = ("WHERE " + " AND ".join(where_clauses)) if where_clauses else ""

    rows = execute_query(f"""
        SELECT p.id, p.numero_hc, p.dni,
               p.nombre || ' ' || p.apellido_pat || ' ' || COALESCE(p.apellido_mat,'') AS nombre_completo,
               p.fecha_nacimiento,
               DATE_PART('year', AGE(p.fecha_nacimiento))::INT AS edad,
               p.sexo, p.telefono, p.email,
               COALESCE(s.nombre, 'Particular') AS seguro,
               p.activo
        FROM clinica.pacientes p
        LEFT JOIN clinica.seguros s ON s.id = p.seguro_id
        {where_sql}
        ORDER BY p.apellido_pat, p.nombre
        LIMIT 200
    """, params)

    if rows:
        df = pd.DataFrame(rows)
        df["activo"] = df["activo"].map({True: "✅ Activo", False: "❌ Inactivo"})
        st.dataframe(df.drop("id", axis=1), use_container_width=True, hide_index=True)
        st.caption(f"📊 {len(rows)} paciente(s) encontrado(s)")
    else:
        st.info("No se encontraron pacientes con los filtros aplicados.")


def _render_form_nuevo_paciente():
    """Formulario de registro de nuevo paciente con validación de duplicados."""
    st.subheader("Registrar Nuevo Paciente")

    with st.form("form_paciente", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            dni      = st.text_input("DNI / Documento *", max_chars=20)
            nombre   = st.text_input("Nombres *")
            ap_pat   = st.text_input("Apellido Paterno *")
            ap_mat   = st.text_input("Apellido Materno")
            fec_nac  = st.date_input("Fecha de Nacimiento *",
                                      min_value=date(1900,1,1), max_value=date.today())
            sexo     = st.selectbox("Sexo *", ["M - Masculino", "F - Femenino", "O - Otro"])
        with col2:
            grupo_s  = st.selectbox("Grupo Sanguíneo",
                                     ["—","A+","A-","B+","B-","AB+","AB-","O+","O-"])
            telefono = st.text_input("Teléfono")
            email    = st.text_input("Email")
            direccion= st.text_area("Dirección", height=68)
            distrito = st.text_input("Distrito")

        col3, col4 = st.columns(2)
        with col3:
            st.subheader("Contacto de Emergencia")
            cont_emerg  = st.text_input("Nombre contacto")
            tel_emerg   = st.text_input("Teléfono contacto")
        with col4:
            st.subheader("Seguro Médico")
            seguros = execute_query("SELECT id, nombre FROM clinica.seguros WHERE activo=TRUE ORDER BY nombre")
            seg_opts = {s["nombre"]: s["id"] for s in seguros}
            seg_sel  = st.selectbox("Seguro", ["Particular"] + list(seg_opts.keys()))
            poliza   = st.text_input("N° Póliza")

        submitted = st.form_submit_button("💾 Registrar Paciente", use_container_width=True)

        if submitted:
            # Validaciones
            errores = []
            if not dni:     errores.append("DNI es requerido")
            if not nombre:  errores.append("Nombre es requerido")
            if not ap_pat:  errores.append("Apellido Paterno es requerido")

            if errores:
                for e in errores:
                    st.error(f"❌ {e}")
            else:
                # Verificar duplicado por DNI
                existe = execute_query(
                    "SELECT id FROM clinica.pacientes WHERE dni=:dni", {"dni": dni}
                )
                if existe:
                    st.error(f"❌ Ya existe un paciente registrado con DNI: {dni}")
                else:
                    _guardar_paciente({
                        "dni": dni, "nombre": nombre, "ap_pat": ap_pat, "ap_mat": ap_mat,
                        "fec_nac": fec_nac, "sexo": sexo[0], "grupo_s": grupo_s if grupo_s != "—" else None,
                        "telefono": telefono, "email": email, "direccion": direccion,
                        "distrito": distrito, "cont_emerg": cont_emerg, "tel_emerg": tel_emerg,
                        "seguro_id": seg_opts.get(seg_sel), "poliza": poliza,
                    })


def _guardar_paciente(data: dict):
    """Persistir nuevo paciente en BD y crear historia clínica vacía."""
    try:
        with get_db() as db:
            # Generar número de HC automático
            res = db.execute(text("""
                SELECT COALESCE(MAX(CAST(REPLACE(numero_hc, 'HC-', '') AS INTEGER)), 0) + 1
                AS siguiente FROM clinica.pacientes
            """)).fetchone()
            numero_hc = f"HC-{res[0]:06d}"

            row = db.execute(text("""
                INSERT INTO clinica.pacientes
                    (dni, numero_hc, nombre, apellido_pat, apellido_mat,
                     fecha_nacimiento, sexo, grupo_sanguineo, telefono, email,
                     direccion, distrito, seguro_id, numero_poliza,
                     contacto_emergencia, telefono_emergencia,
                     created_by)
                VALUES
                    (:dni, :hc, :nom, :ap, :am, :fn, :sx, :gs, :tel, :email,
                     :dir, :dist, :seg, :pol, :ce, :te,
                     :uid)
                RETURNING id
            """), {
                "dni": data["dni"], "hc": numero_hc,
                "nom": data["nombre"], "ap": data["ap_pat"], "am": data["ap_mat"],
                "fn": data["fec_nac"], "sx": data["sexo"], "gs": data["grupo_s"],
                "tel": data["telefono"], "email": data["email"],
                "dir": data["direccion"], "dist": data["distrito"],
                "seg": data["seguro_id"], "pol": data["poliza"],
                "ce": data["cont_emerg"], "te": data["tel_emerg"],
                "uid": st.session_state.user.get("id"),
            })
            pac_id = row.fetchone()[0]

            # Crear historia clínica vacía
            db.execute(text("""
                INSERT INTO clinica.historias_clinicas (paciente_id)
                VALUES (:pid)
            """), {"pid": pac_id})

        log_action("INSERT", "PACIENTES", "clinica.pacientes", pac_id,
                   datos_despues={"dni": data["dni"], "numero_hc": numero_hc})
        st.success(f"✅ Paciente registrado correctamente. N° HC: **{numero_hc}**")
    except Exception as e:
        st.error(f"❌ Error al guardar paciente: {e}")


def _render_historia_clinica():
    """Visualizar y editar historia clínica de un paciente."""
    busq = st.text_input("Buscar paciente por DNI o N° HC", key="hc_busq")
    if not busq:
        return

    rows = execute_query("""
        SELECT p.id, p.numero_hc, p.dni,
               p.nombre || ' ' || p.apellido_pat AS nombre_completo,
               h.antecedentes_personales, h.antecedentes_familiares,
               h.alergias, h.medicamentos_habituales, h.cirugias_previas
        FROM clinica.pacientes p
        LEFT JOIN clinica.historias_clinicas h ON h.paciente_id = p.id
        WHERE p.dni = :b OR p.numero_hc = :b
        LIMIT 1
    """, {"b": busq.upper()})

    if not rows:
        st.warning("Paciente no encontrado.")
        return

    pac = rows[0]
    st.success(f"📋 **{pac['nombre_completo']}** — HC: {pac['numero_hc']} | DNI: {pac['dni']}")

    with st.expander("✏️ Editar Antecedentes", expanded=True):
        with st.form("form_hc"):
            ant_p = st.text_area("Antecedentes Personales", value=pac.get("antecedentes_personales","") or "")
            ant_f = st.text_area("Antecedentes Familiares",  value=pac.get("antecedentes_familiares","") or "")
            alerg = st.text_area("Alergias",                 value=pac.get("alergias","") or "")
            meds  = st.text_area("Medicamentos Habituales",  value=pac.get("medicamentos_habituales","") or "")
            ciru  = st.text_area("Cirugías Previas",         value=pac.get("cirugias_previas","") or "")

            if st.form_submit_button("💾 Guardar Historia Clínica"):
                try:
                    with get_db() as db:
                        db.execute(text("""
                            UPDATE clinica.historias_clinicas
                            SET antecedentes_personales=:ap, antecedentes_familiares=:af,
                                alergias=:al, medicamentos_habituales=:mh, cirugias_previas=:cp,
                                updated_at=NOW(), updated_by=:uid
                            WHERE paciente_id=:pid
                        """), {"ap": ant_p, "af": ant_f, "al": alerg, "mh": meds, "cp": ciru,
                               "uid": st.session_state.user.get("id"), "pid": pac["id"]})
                    log_action("UPDATE", "HISTORIA_CLINICA", "clinica.historias_clinicas", pac["id"])
                    st.success("✅ Historia clínica actualizada.")
                except Exception as e:
                    st.error(f"❌ Error: {e}")