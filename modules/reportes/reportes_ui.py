# ============================================================
# modules/reportes/reportes_ui.py — Módulo de Reportes PDF
# Sistema de Gestión Clínica "Salud Total"
# ============================================================
import streamlit as st
import pandas as pd
from datetime import date
from database.connection import execute_query
from utils.auth import require_auth, has_any_role
from utils.pdf_generator import (
    generar_pdf_historia_clinica,
    generar_pdf_receta,
    generar_pdf_reporte_gestion,
)


def render_reportes():
    """Renderizar módulo de reportes PDF de procesos y gestión."""
    require_auth()
    st.title("📄 Reportes")

    tab1, tab2 = st.tabs(["📋 Reportes de Procesos", "📊 Reportes de Gestión"])

    with tab1: _render_reportes_procesos()
    with tab2:
        if has_any_role("ADMINISTRADOR", "MEDICO", "CONTADOR"):
            _render_reportes_gestion()
        else:
            st.warning("Sin permisos para reportes de gestión.")


def _get_clinica_info() -> dict:
    """Obtener información de la clínica desde parámetros del sistema."""
    rows = execute_query("""
        SELECT clave, valor FROM clinica.parametros_sistema
        WHERE clave LIKE 'CLINICA_%'
    """)
    info = {r["clave"].replace("CLINICA_","").lower(): r["valor"] for r in rows}
    return {
        "nombre":    info.get("nombre", "Clínica Salud Total"),
        "direccion": info.get("direccion", ""),
        "telefono":  info.get("telefono", ""),
        "email":     info.get("email", ""),
        "ruc":       info.get("ruc", ""),
    }


# ─────────────────────────────────────────────────────────────
# REPORTES DE PROCESOS
# ─────────────────────────────────────────────────────────────

def _render_reportes_procesos():
    st.subheader("📋 Reportes de Procesos Clínicos")

    rep_sel = st.selectbox("Seleccionar Reporte", [
        "📋 Historia Clínica Individual",
        "💊 Receta Médica",
        "📅 Listado de Citas por Período",
        "🔬 Resultados de Exámenes",
    ])

    clinica_info = _get_clinica_info()

    if rep_sel == "📋 Historia Clínica Individual":
        _reporte_historia_clinica(clinica_info)
    elif rep_sel == "💊 Receta Médica":
        _reporte_receta(clinica_info)
    elif rep_sel == "📅 Listado de Citas por Período":
        _reporte_citas_periodo(clinica_info)
    elif rep_sel == "🔬 Resultados de Exámenes":
        _reporte_examenes(clinica_info)


def _reporte_historia_clinica(clinica_info: dict):
    """Generar PDF de historia clínica completa de un paciente."""
    st.markdown("#### Historia Clínica Individual")
    dni_hc = st.text_input("DNI o N° HC del Paciente", key="rep_hc_dni")

    if not dni_hc:
        return

    pac = execute_query("""
        SELECT p.*, COALESCE(s.nombre,'Particular') AS seguro
        FROM clinica.pacientes p
        LEFT JOIN clinica.seguros s ON s.id = p.seguro_id
        WHERE p.dni = :b OR p.numero_hc = :b
        LIMIT 1
    """, {"b": dni_hc.upper()})

    if not pac:
        st.warning("Paciente no encontrado.")
        return

    paciente = pac[0]
    st.success(f"👤 {paciente['nombre']} {paciente['apellido_pat']} — HC: {paciente['numero_hc']}")

    hist = execute_query("""
        SELECT * FROM clinica.historias_clinicas WHERE paciente_id = :pid
    """, {"pid": paciente["id"]})

    consultas = execute_query("""
        SELECT co.fecha_atencion, co.motivo, co.tratamiento,
               m.nombre || ' ' || m.apellido AS medico,
               STRING_AGG(cie.codigo || ' ' || cie.descripcion, ', ') AS diagnostico
        FROM clinica.consultas co
        JOIN clinica.medicos m ON m.id = co.medico_id
        LEFT JOIN clinica.diagnosticos d ON d.consulta_id = co.id
        LEFT JOIN clinica.mantenedor_cie10 cie ON cie.id = d.cie10_id
        WHERE co.paciente_id = :pid
        GROUP BY co.id, m.nombre, m.apellido
        ORDER BY co.fecha_atencion DESC
        LIMIT 10
    """, {"pid": paciente["id"]})

    if st.button("📄 Generar PDF Historia Clínica", type="primary"):
        with st.spinner("Generando PDF..."):
            pdf = generar_pdf_historia_clinica(
                paciente=paciente,
                historia=hist[0] if hist else {},
                consultas=consultas,
                clinica_info=clinica_info,
            )
        st.download_button(
            "⬇️ Descargar Historia Clínica",
            data=pdf,
            file_name=f"HC_{paciente['numero_hc']}_{paciente['apellido_pat']}.pdf",
            mime="application/pdf",
            use_container_width=True,
        )


def _reporte_receta(clinica_info: dict):
    """Generar PDF de receta médica por ID de consulta."""
    st.markdown("#### Receta Médica")
    cons_id = st.number_input("ID de Consulta", min_value=1, key="rep_receta_cons")

    if not cons_id:
        return

    cons = execute_query("""
        SELECT co.id, co.fecha_atencion,
               p.nombre || ' ' || p.apellido_pat AS pac_nombre,
               p.dni, p.numero_hc,
               m.nombre AS med_nombre, m.apellido AS med_apellido,
               m.cmp, e.nombre AS especialidad
        FROM clinica.consultas co
        JOIN clinica.pacientes p ON p.id = co.paciente_id
        JOIN clinica.medicos m ON m.id = co.medico_id
        JOIN clinica.especialidades e ON e.id = m.especialidad_id
        WHERE co.id = :cid
    """, {"cid": cons_id})

    if not cons:
        st.warning("Consulta no encontrada.")
        return

    c = cons[0]
    presc = execute_query("""
        SELECT mm.nombre_generico AS medicamento, mm.presentacion,
               pr.dosis, pr.frecuencia, pr.duracion, pr.instrucciones
        FROM clinica.prescripciones pr
        JOIN clinica.mantenedor_medicamentos mm ON mm.id = pr.medicamento_id
        WHERE pr.consulta_id = :cid
        ORDER BY pr.id
    """, {"cid": cons_id})

    if not presc:
        st.warning("Esta consulta no tiene prescripciones registradas.")
        return

    st.success(f"📋 Consulta #{cons_id} — {c['pac_nombre']} | Dr. {c['med_nombre']} {c['med_apellido']}")
    st.dataframe(pd.DataFrame(presc), use_container_width=True, hide_index=True)

    if st.button("📄 Generar PDF Receta Médica", type="primary"):
        with st.spinner("Generando PDF..."):
            pdf = generar_pdf_receta(
                paciente={"nombre": c["pac_nombre"], "dni": c["dni"],
                           "apellido_pat": "", "numero_hc": c["numero_hc"]},
                medico={"nombre": c["med_nombre"], "apellido": c["med_apellido"],
                         "cmp": c["cmp"], "especialidad": c["especialidad"]},
                prescripciones=presc,
                clinica_info=clinica_info,
            )
        st.download_button(
            "⬇️ Descargar Receta",
            data=pdf,
            file_name=f"Receta_{cons_id}_{c['pac_nombre'].replace(' ','_')}.pdf",
            mime="application/pdf",
            use_container_width=True,
        )


def _reporte_citas_periodo(clinica_info: dict):
    """Listado de citas por período y médico en PDF."""
    st.markdown("#### Listado de Citas por Período")
    col1, col2, col3 = st.columns(3)
    with col1: f_desde = st.date_input("Desde", value=date.today().replace(day=1), key="rep_cit_d")
    with col2: f_hasta = st.date_input("Hasta", value=date.today(), key="rep_cit_h")
    with col3:
        medicos = execute_query("SELECT id, nombre || ' ' || apellido AS nom FROM clinica.medicos WHERE activo=TRUE ORDER BY nombre")
        med_opts = {"Todos": None} | {m["nom"]: m["id"] for m in medicos}
        med_sel = st.selectbox("Médico", list(med_opts.keys()), key="rep_cit_med")

    params = {"fd": f_desde, "fh": f_hasta}
    med_f = ""
    if med_opts.get(med_sel):
        med_f = "AND c.medico_id = :mid"
        params["mid"] = med_opts[med_sel]

    datos = execute_query(f"""
        SELECT c.fecha_cita::TEXT AS fecha, c.hora_inicio::TEXT AS hora,
               p.nombre || ' ' || p.apellido_pat AS paciente,
               p.dni,
               m.nombre || ' ' || m.apellido AS medico,
               e.nombre AS especialidad, c.estado
        FROM clinica.citas c
        JOIN clinica.pacientes p ON p.id = c.paciente_id
        JOIN clinica.medicos m ON m.id = c.medico_id
        JOIN clinica.especialidades e ON e.id = m.especialidad_id
        WHERE c.fecha_cita BETWEEN :fd AND :fh {med_f}
        ORDER BY c.fecha_cita, c.hora_inicio
    """, params)

    if not datos:
        st.info("No hay citas en el período seleccionado.")
        return

    st.dataframe(pd.DataFrame(datos), use_container_width=True, hide_index=True)
    st.caption(f"Total: {len(datos)} citas")

    resumen = {
        "Período": f"{f_desde} al {f_hasta}",
        "Total Citas": len(datos),
        "Atendidas": sum(1 for d in datos if d["estado"] == "ATENDIDA"),
        "Canceladas": sum(1 for d in datos if d["estado"] == "CANCELADA"),
        "No-show": sum(1 for d in datos if d["estado"] == "NO_SHOW"),
    }

    if st.button("📄 Exportar a PDF", type="primary"):
        with st.spinner("Generando PDF..."):
            pdf = generar_pdf_reporte_gestion(
                titulo="Reporte de Citas Médicas",
                subtitulo=f"Período: {f_desde} al {f_hasta}",
                datos=datos,
                columnas=["fecha","hora","paciente","dni","medico","especialidad","estado"],
                clinica_info=clinica_info,
                resumen=resumen,
            )
        st.download_button(
            "⬇️ Descargar PDF",
            data=pdf,
            file_name=f"citas_{f_desde}_{f_hasta}.pdf",
            mime="application/pdf",
            use_container_width=True,
        )


def _reporte_examenes(clinica_info: dict):
    """Reporte de resultados de exámenes por paciente."""
    st.markdown("#### Resultados de Exámenes")
    dni_ex = st.text_input("DNI del Paciente", key="rep_exam_dni")

    if not dni_ex:
        return

    datos = execute_query("""
        SELECT ex.tipo_examen, ex.nombre_examen, ex.estado,
               ex.resultado, ex.fecha_resultado::TEXT AS fecha_resultado,
               co.fecha_atencion::TEXT AS fecha_solicitud,
               m.nombre || ' ' || m.apellido AS medico_solicitante
        FROM clinica.examenes_solicitados ex
        JOIN clinica.consultas co ON co.id = ex.consulta_id
        JOIN clinica.medicos m ON m.id = co.medico_id
        JOIN clinica.pacientes p ON p.id = co.paciente_id
        WHERE p.dni = :dni
        ORDER BY ex.id DESC
    """, {"dni": dni_ex})

    if not datos:
        st.info("No se encontraron exámenes para este paciente.")
        return

    st.dataframe(pd.DataFrame(datos), use_container_width=True, hide_index=True)

    if st.button("📄 Exportar a PDF", type="primary"):
        pac = execute_query("SELECT nombre || ' ' || apellido_pat AS nom FROM clinica.pacientes WHERE dni=:d", {"d": dni_ex})
        nombre_pac = pac[0]["nom"] if pac else dni_ex
        with st.spinner("Generando PDF..."):
            pdf = generar_pdf_reporte_gestion(
                titulo=f"Resultados de Exámenes — {nombre_pac}",
                subtitulo=f"DNI: {dni_ex}",
                datos=datos,
                columnas=["tipo_examen","nombre_examen","estado","fecha_solicitud","medico_solicitante","resultado"],
                clinica_info=clinica_info,
            )
        st.download_button(
            "⬇️ Descargar PDF",
            data=pdf,
            file_name=f"examenes_{dni_ex}.pdf",
            mime="application/pdf",
            use_container_width=True,
        )


# ─────────────────────────────────────────────────────────────
# REPORTES DE GESTIÓN
# ─────────────────────────────────────────────────────────────

def _render_reportes_gestion():
    st.subheader("📊 Reportes de Gestión y Gerenciales")

    rep_sel = st.selectbox("Seleccionar Reporte", [
        "📊 Atenciones por Especialidad",
        "👨‍⚕️ Productividad Médica",
        "💰 Reporte Financiero",
        "🦠 Reporte Epidemiológico",
    ])

    clinica_info = _get_clinica_info()

    if rep_sel == "📊 Atenciones por Especialidad":
        _reporte_atenciones_especialidad(clinica_info)
    elif rep_sel == "👨‍⚕️ Productividad Médica":
        _reporte_productividad(clinica_info)
    elif rep_sel == "💰 Reporte Financiero":
        _reporte_financiero(clinica_info)
    elif rep_sel == "🦠 Reporte Epidemiológico":
        _reporte_epidemiologico(clinica_info)


def _reporte_atenciones_especialidad(clinica_info: dict):
    st.markdown("#### Atenciones Mensuales por Especialidad")
    col1, col2 = st.columns(2)
    with col1: mes = st.number_input("Mes", 1, 12, date.today().month)
    with col2: año = st.number_input("Año", 2020, 2030, date.today().year)

    datos = execute_query("""
        SELECT e.nombre AS especialidad,
               COUNT(*) AS total_citas,
               COUNT(*) FILTER (WHERE c.estado='ATENDIDA') AS atendidas,
               COUNT(*) FILTER (WHERE c.estado='CANCELADA') AS canceladas,
               COUNT(*) FILTER (WHERE c.estado='NO_SHOW') AS noshow,
               ROUND(COUNT(*) FILTER (WHERE c.estado='ATENDIDA') * 100.0
                     / NULLIF(COUNT(*),0), 1) AS pct_asistencia
        FROM clinica.citas c
        JOIN clinica.medicos m ON m.id = c.medico_id
        JOIN clinica.especialidades e ON e.id = m.especialidad_id
        WHERE EXTRACT(MONTH FROM c.fecha_cita) = :mes
          AND EXTRACT(YEAR  FROM c.fecha_cita) = :year
        GROUP BY e.nombre
        ORDER BY atendidas DESC
    """, {"mes": mes, "year": año})

    _mostrar_y_exportar(
        datos=datos,
        columnas=["especialidad","total_citas","atendidas","canceladas","noshow","pct_asistencia"],
        titulo="Reporte Mensual de Atenciones por Especialidad",
        subtitulo=f"Mes {mes:02d}/{año}",
        clinica_info=clinica_info,
        resumen={
            "Mes/Año": f"{mes:02d}/{año}",
            "Total Especialidades": len(datos),
            "Total Citas": sum(d["total_citas"] for d in datos),
        },
        filename=f"atenciones_esp_{mes:02d}_{año}.pdf",
    )


def _reporte_productividad(clinica_info: dict):
    st.markdown("#### Productividad Médica")
    col1, col2 = st.columns(2)
    with col1: f_desde = st.date_input("Desde", value=date.today().replace(day=1), key="prod_d")
    with col2: f_hasta = st.date_input("Hasta", value=date.today(), key="prod_h")

    datos = execute_query("""
        SELECT m.nombre || ' ' || m.apellido AS medico,
               e.nombre AS especialidad,
               COUNT(DISTINCT c.id)  AS total_citas,
               COUNT(DISTINCT co.id) AS consultas_realizadas,
               COUNT(DISTINCT pr.id) AS prescripciones,
               COUNT(DISTINCT ex.id) AS examenes_solicitados
        FROM clinica.medicos m
        JOIN clinica.especialidades e ON e.id = m.especialidad_id
        LEFT JOIN clinica.citas c ON c.medico_id = m.id
            AND c.fecha_cita BETWEEN :fd AND :fh AND c.estado='ATENDIDA'
        LEFT JOIN clinica.consultas co ON co.medico_id = m.id
            AND co.fecha_atencion::DATE BETWEEN :fd AND :fh
        LEFT JOIN clinica.prescripciones pr ON pr.consulta_id = co.id
        LEFT JOIN clinica.examenes_solicitados ex ON ex.consulta_id = co.id
        WHERE m.activo = TRUE
        GROUP BY m.id, e.nombre
        ORDER BY consultas_realizadas DESC
    """, {"fd": f_desde, "fh": f_hasta})

    _mostrar_y_exportar(
        datos=datos,
        columnas=["medico","especialidad","total_citas","consultas_realizadas",
                  "prescripciones","examenes_solicitados"],
        titulo="Reporte de Productividad Médica",
        subtitulo=f"Período: {f_desde} al {f_hasta}",
        clinica_info=clinica_info,
        resumen={"Período": f"{f_desde} al {f_hasta}", "Médicos activos": len(datos)},
        filename=f"productividad_{f_desde}_{f_hasta}.pdf",
    )


def _reporte_financiero(clinica_info: dict):
    st.markdown("#### Reporte Financiero")
    col1, col2 = st.columns(2)
    with col1: f_desde = st.date_input("Desde", value=date.today().replace(day=1), key="fin_d")
    with col2: f_hasta = st.date_input("Hasta", value=date.today(), key="fin_h")

    datos = execute_query("""
        SELECT f.numero_factura,
               f.fecha_emision::TEXT AS fecha,
               p.nombre || ' ' || p.apellido_pat AS paciente,
               COALESCE(seg.nombre,'Particular') AS seguro,
               f.subtotal::TEXT AS subtotal,
               f.igv::TEXT AS igv,
               f.total::TEXT AS total,
               f.estado
        FROM clinica.facturas f
        JOIN clinica.pacientes p ON p.id = f.paciente_id
        LEFT JOIN clinica.seguros seg ON seg.id = f.seguro_id
        WHERE f.fecha_emision::DATE BETWEEN :fd AND :fh
          AND f.estado != 'ANULADA'
        ORDER BY f.fecha_emision
    """, {"fd": f_desde, "fh": f_hasta})

    total_general = sum(float(d["total"]) for d in datos)
    pendientes    = sum(float(d["total"]) for d in datos if d["estado"] == "PENDIENTE")
    pagadas       = sum(float(d["total"]) for d in datos if d["estado"] == "PAGADA")

    _mostrar_y_exportar(
        datos=datos,
        columnas=["numero_factura","fecha","paciente","seguro","subtotal","igv","total","estado"],
        titulo="Reporte Financiero",
        subtitulo=f"Período: {f_desde} al {f_hasta}",
        clinica_info=clinica_info,
        resumen={
            "Total Facturado": f"S/ {total_general:,.2f}",
            "Cobrado": f"S/ {pagadas:,.2f}",
            "Pendiente": f"S/ {pendientes:,.2f}",
            "Num. Facturas": len(datos),
        },
        filename=f"financiero_{f_desde}_{f_hasta}.pdf",
    )


def _reporte_epidemiologico(clinica_info: dict):
    st.markdown("#### Reporte Epidemiológico — Diagnósticos Frecuentes")
    col1, col2 = st.columns(2)
    with col1: f_desde = st.date_input("Desde", value=date.today().replace(day=1), key="epi_d")
    with col2: f_hasta = st.date_input("Hasta", value=date.today(), key="epi_h")

    datos = execute_query("""
        SELECT cie.codigo, cie.descripcion, cie.categoria,
               COUNT(*) AS total_casos,
               COUNT(DISTINCT co.paciente_id) AS pacientes_afectados
        FROM clinica.diagnosticos d
        JOIN clinica.mantenedor_cie10 cie ON cie.id = d.cie10_id
        JOIN clinica.consultas co ON co.id = d.consulta_id
        WHERE co.fecha_atencion::DATE BETWEEN :fd AND :fh
        GROUP BY cie.codigo, cie.descripcion, cie.categoria
        ORDER BY total_casos DESC
        LIMIT 50
    """, {"fd": f_desde, "fh": f_hasta})

    _mostrar_y_exportar(
        datos=datos,
        columnas=["codigo","descripcion","categoria","total_casos","pacientes_afectados"],
        titulo="Reporte Epidemiológico",
        subtitulo=f"Diagnósticos más frecuentes — {f_desde} al {f_hasta}",
        clinica_info=clinica_info,
        resumen={
            "Período": f"{f_desde} al {f_hasta}",
            "Diagnósticos distintos": len(datos),
            "Total casos": sum(d["total_casos"] for d in datos),
        },
        filename=f"epidemiologico_{f_desde}_{f_hasta}.pdf",
    )


def _mostrar_y_exportar(datos, columnas, titulo, subtitulo,
                         clinica_info, resumen, filename):
    """Helper: mostrar tabla de datos y botón de exportar a PDF."""
    if not datos:
        st.info("No hay datos para el período seleccionado.")
        return

    df = pd.DataFrame(datos)
    st.dataframe(df, use_container_width=True, hide_index=True)
    st.caption(f"📊 {len(datos)} registro(s)")

    if st.button(f"📄 Exportar '{titulo}' a PDF", type="primary"):
        with st.spinner("Generando PDF..."):
            pdf = generar_pdf_reporte_gestion(
                titulo=titulo,
                subtitulo=subtitulo,
                datos=datos,
                columnas=columnas,
                clinica_info=clinica_info,
                resumen=resumen,
            )
        st.download_button(
            "⬇️ Descargar PDF",
            data=pdf,
            file_name=filename,
            mime="application/pdf",
            use_container_width=True,
        )
