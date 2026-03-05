# ============================================================
# modules/mantenedores/mant_ui.py — Módulo de Mantenedores
# Sistema de Gestión Clínica "Salud Total"
# ============================================================
import streamlit as st
import pandas as pd
from database.connection import execute_query, get_db
from utils.audit_logger import log_action
from utils.auth import require_auth, has_any_role
from sqlalchemy import text


def render_mantenedores():
    """Renderizar módulo de tablas maestras del sistema."""
    require_auth()
    if not has_any_role("ADMINISTRADOR"):
        st.error("🔒 Solo el Administrador puede gestionar los mantenedores.")
        return

    st.title("🔧 Mantenedores — Tablas Maestras")

    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "🏥 Especialidades",
        "💊 Medicamentos",
        "🔬 CIE-10",
        "🛡️ Seguros",
        "💰 Servicios / Tarifarios",
        "⚙️ Parámetros del Sistema",
    ])

    with tab1: _render_especialidades()
    with tab2: _render_medicamentos()
    with tab3: _render_cie10()
    with tab4: _render_seguros()
    with tab5: _render_servicios_tarifarios()
    with tab6: _render_parametros()


# ─────────────────────────────────────────────────────────────
# Especialidades
# ─────────────────────────────────────────────────────────────

def _render_especialidades():
    st.subheader("🏥 Especialidades Médicas")

    rows = execute_query("""
        SELECT id, codigo, nombre, descripcion, activo FROM clinica.especialidades
        ORDER BY nombre
    """)
    if rows:
        df = pd.DataFrame(rows)
        df["activo"] = df["activo"].map({True: "✅", False: "❌"})
        st.dataframe(df.drop("id", axis=1), use_container_width=True, hide_index=True)

    st.divider()
    with st.form("form_esp", clear_on_submit=True):
        col1, col2, col3 = st.columns([1, 3, 1])
        with col1: codigo = st.text_input("Código *", max_chars=10)
        with col2: nombre = st.text_input("Nombre *")
        with col3: activo = st.checkbox("Activo", value=True)
        desc = st.text_area("Descripción", height=60)

        if st.form_submit_button("➕ Agregar Especialidad", use_container_width=True):
            if not codigo or not nombre:
                st.error("❌ Código y nombre son requeridos.")
            else:
                try:
                    with get_db() as db:
                        db.execute(text("""
                            INSERT INTO clinica.especialidades (codigo, nombre, descripcion, activo, created_by)
                            VALUES (:cod, :nom, :desc, :act, :uid)
                        """), {"cod": codigo.upper(), "nom": nombre, "desc": desc,
                               "act": activo, "uid": st.session_state.user.get("id")})
                    log_action("INSERT", "MANTENEDORES", "clinica.especialidades")
                    st.success(f"✅ Especialidad '{nombre}' agregada.")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Error (¿código duplicado?): {e}")


# ─────────────────────────────────────────────────────────────
# Medicamentos
# ─────────────────────────────────────────────────────────────

def _render_medicamentos():
    st.subheader("💊 Medicamentos")

    busq = st.text_input("🔍 Buscar medicamento", key="med_mant_busq")
    params = {}
    where = ""
    if busq:
        where = "WHERE nombre_generico ILIKE :b OR nombre_comercial ILIKE :b"
        params["b"] = f"%{busq}%"

    rows = execute_query(f"""
        SELECT id, nombre_generico, nombre_comercial, presentacion,
               concentracion, via_admin, activo
        FROM clinica.mantenedor_medicamentos
        {where}
        ORDER BY nombre_generico LIMIT 100
    """, params)

    if rows:
        df = pd.DataFrame(rows)
        df["activo"] = df["activo"].map({True: "✅", False: "❌"})
        st.dataframe(df.drop("id", axis=1), use_container_width=True, hide_index=True)
        st.caption(f"{len(rows)} medicamento(s)")

    st.divider()
    st.markdown("**Agregar Medicamento:**")
    with st.form("form_med", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            nom_gen  = st.text_input("Nombre Genérico *")
            nom_com  = st.text_input("Nombre Comercial")
            present  = st.text_input("Presentación", placeholder="ej: Tableta, Jarabe, Ampolla")
        with col2:
            concent  = st.text_input("Concentración", placeholder="ej: 500mg, 250mg/5ml")
            via      = st.selectbox("Vía de Administración",
                                     ["Oral", "IV", "IM", "SC", "Tópica", "Inhalatoria", "Otro"])
            activo_m = st.checkbox("Activo", value=True)

        if st.form_submit_button("➕ Agregar Medicamento", use_container_width=True):
            if not nom_gen:
                st.error("❌ El nombre genérico es requerido.")
            else:
                try:
                    with get_db() as db:
                        db.execute(text("""
                            INSERT INTO clinica.mantenedor_medicamentos
                                (nombre_generico, nombre_comercial, presentacion,
                                 concentracion, via_admin, activo)
                            VALUES (:ng, :nc, :pres, :conc, :via, :act)
                        """), {"ng": nom_gen, "nc": nom_com, "pres": present,
                               "conc": concent, "via": via, "act": activo_m})
                    log_action("INSERT", "MANTENEDORES", "clinica.mantenedor_medicamentos")
                    st.success(f"✅ Medicamento '{nom_gen}' agregado.")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Error: {e}")


# ─────────────────────────────────────────────────────────────
# CIE-10
# ─────────────────────────────────────────────────────────────

def _render_cie10():
    st.subheader("🔬 Clasificación CIE-10")

    busq = st.text_input("🔍 Buscar código o descripción", key="cie_busq")
    params = {}
    where = ""
    if busq:
        where = "WHERE codigo ILIKE :b OR descripcion ILIKE :b"
        params["b"] = f"%{busq}%"

    rows = execute_query(f"""
        SELECT codigo, descripcion, categoria, activo
        FROM clinica.mantenedor_cie10
        {where}
        ORDER BY codigo LIMIT 100
    """, params)

    if rows:
        df = pd.DataFrame(rows)
        df["activo"] = df["activo"].map({True: "✅", False: "❌"})
        st.dataframe(df, use_container_width=True, hide_index=True)
        st.caption(f"{len(rows)} código(s) — Mostrando máx. 100 resultados")

    st.divider()
    st.markdown("**Agregar Código CIE-10:**")
    with st.form("form_cie", clear_on_submit=True):
        col1, col2, col3 = st.columns([1, 4, 2])
        with col1: codigo_cie = st.text_input("Código *", max_chars=10)
        with col2: desc_cie   = st.text_input("Descripción *")
        with col3: cat_cie    = st.text_input("Categoría", placeholder="ej: Respiratorio")

        if st.form_submit_button("➕ Agregar Código"):
            if not codigo_cie or not desc_cie:
                st.error("❌ Código y descripción son requeridos.")
            else:
                try:
                    with get_db() as db:
                        db.execute(text("""
                            INSERT INTO clinica.mantenedor_cie10 (codigo, descripcion, categoria)
                            VALUES (:cod, :desc, :cat)
                        """), {"cod": codigo_cie.upper(), "desc": desc_cie, "cat": cat_cie})
                    log_action("INSERT", "MANTENEDORES", "clinica.mantenedor_cie10")
                    st.success(f"✅ Código {codigo_cie.upper()} agregado.")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Error (¿código duplicado?): {e}")


# ─────────────────────────────────────────────────────────────
# Seguros
# ─────────────────────────────────────────────────────────────

def _render_seguros():
    st.subheader("🛡️ Seguros Médicos y Convenios")

    rows = execute_query("""
        SELECT s.id, s.nombre, t.nombre AS tipo, s.ruc, s.contacto,
               s.telefono, s.email, s.activo
        FROM clinica.seguros s
        LEFT JOIN clinica.tipos_seguro t ON t.id = s.tipo_id
        ORDER BY s.nombre
    """)
    if rows:
        df = pd.DataFrame(rows)
        df["activo"] = df["activo"].map({True: "✅", False: "❌"})
        st.dataframe(df.drop("id", axis=1), use_container_width=True, hide_index=True)

    st.divider()
    tipos = execute_query("SELECT id, nombre FROM clinica.tipos_seguro WHERE activo=TRUE ORDER BY nombre")
    if not tipos:
        st.warning("⚠️ Primero agregue tipos de seguro. Use la opción de abajo.")

    tipo_opts = {t["nombre"]: t["id"] for t in tipos} if tipos else {}

    with st.form("form_seguro", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            nom_seg  = st.text_input("Nombre del Seguro *")
            tipo_seg = st.selectbox("Tipo", list(tipo_opts.keys()) if tipo_opts else ["—"])
            ruc      = st.text_input("RUC", max_chars=11)
        with col2:
            contacto = st.text_input("Persona de Contacto")
            telefono = st.text_input("Teléfono")
            email    = st.text_input("Email")

        if st.form_submit_button("➕ Agregar Seguro", use_container_width=True):
            if not nom_seg or not tipo_opts:
                st.error("❌ Nombre y tipo son requeridos.")
            else:
                try:
                    with get_db() as db:
                        db.execute(text("""
                            INSERT INTO clinica.seguros
                                (nombre, tipo_id, ruc, contacto, telefono, email)
                            VALUES (:nom, :tid, :ruc, :cont, :tel, :email)
                        """), {"nom": nom_seg, "tid": tipo_opts.get(tipo_seg),
                               "ruc": ruc, "cont": contacto,
                               "tel": telefono, "email": email})
                    log_action("INSERT", "MANTENEDORES", "clinica.seguros")
                    st.success(f"✅ Seguro '{nom_seg}' agregado.")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Error: {e}")

    st.divider()
    st.markdown("**Agregar Tipo de Seguro:**")
    with st.form("form_tipo_seg", clear_on_submit=True):
        nom_tipo = st.text_input("Nombre del Tipo *", placeholder="ej: EPS, SOAT, Particular")
        desc_tipo = st.text_input("Descripción")
        if st.form_submit_button("➕ Agregar Tipo"):
            if not nom_tipo:
                st.error("❌ Nombre requerido.")
            else:
                try:
                    with get_db() as db:
                        db.execute(text("""
                            INSERT INTO clinica.tipos_seguro (nombre, descripcion)
                            VALUES (:nom, :desc)
                        """), {"nom": nom_tipo, "desc": desc_tipo})
                    st.success(f"✅ Tipo '{nom_tipo}' agregado.")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Error: {e}")


# ─────────────────────────────────────────────────────────────
# Servicios y Tarifarios
# ─────────────────────────────────────────────────────────────

def _render_servicios_tarifarios():
    st.subheader("💰 Servicios y Tarifarios")

    tab_a, tab_b = st.tabs(["🏥 Servicios", "💵 Tarifarios"])

    with tab_a:
        servicios = execute_query("""
            SELECT s.id, s.codigo, s.nombre, s.tipo_servicio,
                   e.nombre AS especialidad, s.activo
            FROM clinica.servicios s
            LEFT JOIN clinica.especialidades e ON e.id = s.especialidad_id
            ORDER BY s.tipo_servicio, s.nombre
        """)
        if servicios:
            df = pd.DataFrame(servicios)
            df["activo"] = df["activo"].map({True: "✅", False: "❌"})
            st.dataframe(df.drop("id", axis=1), use_container_width=True, hide_index=True)

        st.divider()
        esp_rows = execute_query("SELECT id, nombre, codigo FROM clinica.especialidades WHERE activo=TRUE ORDER BY nombre")
        esp_opts = {"Ninguna": None} | {e["nombre"]: e["id"] for e in esp_rows}
        esp_code_by_id = {e["id"]: e["codigo"] for e in esp_rows}

        with st.form("form_servicio", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                cod_svc  = st.text_input("Código (vacío = autogenerado)", max_chars=20)
                nom_svc  = st.text_input("Nombre *")
                tipo_svc = st.selectbox("Tipo",
                    ["CONSULTA","PROCEDIMIENTO","LABORATORIO","IMAGEN","HOSPITALIZACION","OTRO"])
            with col2:
                esp_svc  = st.selectbox("Especialidad (opcional)", list(esp_opts.keys()))
                desc_svc = st.text_area("Descripción", height=68)

            if st.form_submit_button("➕ Agregar Servicio", use_container_width=True):
                if not nom_svc:
                    st.error("❌ El nombre es requerido.")
                else:
                    try:
                        # Autogenerar código si no se ingresó
                        final_code = cod_svc.strip().upper() if cod_svc else None
                        if not final_code:
                            prefix_map = {
                                "CONSULTA": "CONS", "PROCEDIMIENTO": "PROC",
                                "LABORATORIO": "LAB", "IMAGEN": "IMG",
                                "HOSPITALIZACION": "HOSP", "OTRO": "OTR",
                            }
                            pref = prefix_map.get(tipo_svc, "OTR")
                            esp_id = esp_opts.get(esp_svc)
                            esp_code = esp_code_by_id.get(esp_id, "GENE") if esp_id else "GENE"
                            base = f"{pref}-{esp_code}"
                            # Buscar sufijos existentes y generar siguiente
                            existentes = execute_query("""
                                SELECT codigo FROM clinica.servicios
                                WHERE codigo LIKE :base || '%'
                            """, {"base": base})
                            usados = set()
                            for r in existentes:
                                cod = r["codigo"]
                                if len(cod) > len(base):
                                    suf = cod[len(base):]
                                    suf = suf.strip().lstrip("-")
                                    if suf.isdigit():
                                        usados.add(int(suf))
                            nxt = 1
                            while nxt in usados:
                                nxt += 1
                            final_code = f"{base}{nxt:02d}"

                        with get_db() as db:
                            db.execute(text("""
                                INSERT INTO clinica.servicios
                                    (codigo, nombre, tipo_servicio, especialidad_id, descripcion)
                                VALUES (:cod, :nom, :tipo, :eid, :desc)
                            """), {"cod": final_code, "nom": nom_svc, "tipo": tipo_svc,
                                   "eid": esp_opts.get(esp_svc), "desc": desc_svc})
                        log_action("INSERT", "MANTENEDORES", "clinica.servicios")
                        st.success(f"✅ Servicio '{nom_svc}' agregado con código {final_code}.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ Error (¿código duplicado?): {e}")

    with tab_b:
        tarifarios = execute_query("""
            SELECT t.id, s.codigo, s.nombre AS servicio,
                   COALESCE(seg.nombre, 'Particular') AS seguro,
                   t.precio, t.vigente_desde, t.vigente_hasta, t.activo
            FROM clinica.tarifarios t
            JOIN clinica.servicios s ON s.id = t.servicio_id
            LEFT JOIN clinica.seguros seg ON seg.id = t.seguro_id
            ORDER BY s.nombre, seg.nombre
        """)
        if tarifarios:
            df = pd.DataFrame(tarifarios)
            df["activo"] = df["activo"].map({True: "✅", False: "❌"})
            st.dataframe(df.drop("id", axis=1), use_container_width=True, hide_index=True)

        st.divider()
        svc_rows = execute_query("SELECT id, codigo || ' — ' || nombre AS label FROM clinica.servicios WHERE activo=TRUE ORDER BY nombre")
        seg_rows = execute_query("SELECT id, nombre FROM clinica.seguros WHERE activo=TRUE ORDER BY nombre")
        svc_opts = {s["label"]: s["id"] for s in svc_rows}
        seg_opts = {"Particular (sin seguro)": None} | {s["nombre"]: s["id"] for s in seg_rows}

        from datetime import date
        with st.form("form_tarifa", clear_on_submit=True):
            col1, col2, col3, col4 = st.columns(4)
            with col1: svc_t = st.selectbox("Servicio *", list(svc_opts.keys()))
            with col2: seg_t = st.selectbox("Seguro", list(seg_opts.keys()))
            with col3: precio_t = st.number_input("Precio S/ *", min_value=0.0, step=1.0)
            with col4: vig_desde = st.date_input("Vigente desde", value=date.today())

            if st.form_submit_button("➕ Agregar Tarifa", use_container_width=True):
                if precio_t <= 0:
                    st.error("❌ El precio debe ser mayor a 0.")
                else:
                    try:
                        with get_db() as db:
                            db.execute(text("""
                                INSERT INTO clinica.tarifarios
                                    (servicio_id, seguro_id, precio, vigente_desde, created_by)
                                VALUES (:sid, :secid, :precio, :vd, :uid)
                            """), {"sid": svc_opts[svc_t], "secid": seg_opts.get(seg_t),
                                   "precio": precio_t, "vd": vig_desde,
                                   "uid": st.session_state.user.get("id")})
                        log_action("INSERT", "MANTENEDORES", "clinica.tarifarios")
                        st.success("✅ Tarifa agregada correctamente.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ Error: {e}")


# ─────────────────────────────────────────────────────────────
# Parámetros del sistema
# ─────────────────────────────────────────────────────────────

def _render_parametros():
    st.subheader("⚙️ Parámetros del Sistema")
    st.info("💡 Modifique los parámetros globales del sistema con cuidado. Los cambios son inmediatos.")

    params = execute_query("""
        SELECT clave, valor, descripcion, tipo_dato
        FROM clinica.parametros_sistema
        ORDER BY clave
    """)

    if not params:
        st.warning("No hay parámetros configurados.")
        return

    # Agrupar por prefijo para mejor presentación
    grupos = {}
    for p in params:
        prefijo = p["clave"].split("_")[0]
        grupos.setdefault(prefijo, []).append(p)

    for prefijo, items in grupos.items():
        with st.expander(f"⚙️ {prefijo}", expanded=prefijo == "CLINICA"):
            for param in items:
                col1, col2, col3 = st.columns([2, 3, 1])
                with col1:
                    st.markdown(f"**{param['clave']}**")
                    st.caption(param.get("descripcion",""))
                with col2:
                    nuevo_val = st.text_input(
                        "Valor", value=param["valor"],
                        key=f"param_{param['clave']}",
                        label_visibility="collapsed"
                    )
                with col3:
                    st.write("")
                    if st.button("💾", key=f"save_param_{param['clave']}",
                                  help="Guardar este parámetro"):
                        try:
                            with get_db() as db:
                                db.execute(text("""
                                    UPDATE clinica.parametros_sistema
                                    SET valor=:val, updated_at=NOW(), updated_by=:uid
                                    WHERE clave=:clave
                                """), {"val": nuevo_val, "uid": st.session_state.user.get("id"),
                                       "clave": param["clave"]})
                            log_action("UPDATE", "MANTENEDORES", "clinica.parametros_sistema",
                                       param["clave"])
                            st.success(f"✅ {param['clave']} actualizado.")
                        except Exception as e:
                            st.error(f"❌ Error: {e}")
