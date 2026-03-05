# ============================================================
# modules/dashboard/dashboard_ui.py
# ============================================================
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from database.connection import execute_query
from utils.auth import require_auth
from datetime import date


def render_dashboard():
    require_auth()
    st.title("📊 Dashboard — Salud Total")
    st.caption(f"Actualizado: {date.today().strftime('%d/%m/%Y')}")

    # ── KPIs ──────────────────────────────────────────────
    k1, k2, k3, k4, k5 = st.columns(5)
    kpis = _get_kpis()

    with k1:
        st.metric("👥 Total Pacientes", kpis["total_pacientes"],
                  f"+{kpis['nuevos_mes']} este mes")
    with k2:
        st.metric("📅 Citas Hoy",       kpis["citas_hoy"],
                  f"{kpis['tasa_asistencia']}% asistencia")
    with k3:
        st.metric("✅ Atendidos Hoy",   kpis["atendidos_hoy"])
    with k4:
        st.metric("💰 Ingresos del Mes", f"S/ {kpis['ingresos_mes']:,.2f}",
                  f"{'↑' if kpis['variacion'] >= 0 else '↓'} {abs(kpis['variacion']):.1f}%")
    with k5:
        st.metric("🚫 No-show Mes",      kpis["noshow_mes"])

    st.divider()

    # ── Fila 1: Citas + Ingresos ───────────────────────────
    col1, col2 = st.columns(2)
    with col1:
        _chart_citas_semana()
    with col2:
        _chart_ingresos_mes()

    # ── Fila 2: Diagnósticos + Distribución pacientes ──────
    col3, col4 = st.columns(2)
    with col3:
        _chart_top_diagnosticos()
    with col4:
        _chart_distribucion_edad()

    # ── Fila 3: Ocupación especialidades ──────────────────
    _chart_ocupacion_especialidades()


def _get_kpis() -> dict:
    """Calcular todos los KPIs del dashboard en una función."""
    rows = execute_query("""
        SELECT
            (SELECT COUNT(*) FROM clinica.pacientes WHERE activo=TRUE) AS total_pacientes,
            (SELECT COUNT(*) FROM clinica.pacientes
             WHERE DATE_TRUNC('month', created_at) = DATE_TRUNC('month', NOW())) AS nuevos_mes,
            (SELECT COUNT(*) FROM clinica.citas WHERE fecha_cita = CURRENT_DATE) AS citas_hoy,
            (SELECT COUNT(*) FROM clinica.citas
             WHERE fecha_cita = CURRENT_DATE AND estado='ATENDIDA') AS atendidos_hoy,
            (SELECT COALESCE(SUM(total),0) FROM clinica.facturas
             WHERE DATE_TRUNC('month', fecha_emision) = DATE_TRUNC('month', NOW())
               AND estado != 'ANULADA') AS ingresos_mes,
            (SELECT COALESCE(SUM(total),0) FROM clinica.facturas
             WHERE DATE_TRUNC('month', fecha_emision) = DATE_TRUNC('month', NOW() - INTERVAL '1 month')
               AND estado != 'ANULADA') AS ingresos_mes_ant,
            (SELECT COUNT(*) FROM clinica.citas
             WHERE DATE_TRUNC('month', fecha_cita) = DATE_TRUNC('month', NOW())
               AND estado='NO_SHOW') AS noshow_mes
    """)
    k = rows[0] if rows else {}

    citas_hoy  = k.get("citas_hoy", 0) or 0
    atend_hoy  = k.get("atendidos_hoy", 0) or 0
    ing_mes    = float(k.get("ingresos_mes", 0) or 0)
    ing_ant    = float(k.get("ingresos_mes_ant", 0) or 1)
    variacion  = ((ing_mes - ing_ant) / ing_ant * 100) if ing_ant else 0
    tasa       = round(atend_hoy / citas_hoy * 100) if citas_hoy else 0

    return {
        "total_pacientes": k.get("total_pacientes", 0),
        "nuevos_mes":      k.get("nuevos_mes", 0),
        "citas_hoy":       citas_hoy,
        "atendidos_hoy":   atend_hoy,
        "tasa_asistencia": tasa,
        "ingresos_mes":    ing_mes,
        "variacion":       variacion,
        "noshow_mes":      k.get("noshow_mes", 0),
    }


def _chart_citas_semana():
    """Gráfico de barras: evolución de citas por día en los últimos 30 días."""
    data = execute_query("""
        SELECT fecha_cita::TEXT AS fecha,
               COUNT(*) FILTER (WHERE estado='ATENDIDA')  AS atendidas,
               COUNT(*) FILTER (WHERE estado='CANCELADA') AS canceladas,
               COUNT(*) FILTER (WHERE estado='NO_SHOW')   AS noshow
        FROM clinica.citas
        WHERE fecha_cita >= CURRENT_DATE - 29
        GROUP BY fecha_cita ORDER BY fecha_cita
    """)
    if data:
        df = pd.DataFrame(data)
        fig = px.bar(df, x="fecha", y=["atendidas","canceladas","noshow"],
                     title="📅 Citas — Últimos 30 días",
                     labels={"value":"Cantidad","fecha":"Fecha","variable":"Estado"},
                     color_discrete_map={"atendidas":"#27ae60","canceladas":"#e74c3c","noshow":"#f39c12"},
                     barmode="stack")
        fig.update_layout(height=320, margin=dict(t=40, b=20))
        st.plotly_chart(fig, use_container_width=True)


def _chart_ingresos_mes():
    """Gráfico de línea: ingresos diarios del mes actual."""
    data = execute_query("""
        SELECT DATE(fecha_emision) AS fecha,
               SUM(total) AS ingresos
        FROM clinica.facturas
        WHERE DATE_TRUNC('month', fecha_emision) = DATE_TRUNC('month', NOW())
          AND estado != 'ANULADA'
        GROUP BY DATE(fecha_emision) ORDER BY fecha
    """)
    if data:
        df = pd.DataFrame(data)
        df["ingresos"] = df["ingresos"].astype(float)
        fig = px.area(df, x="fecha", y="ingresos",
                      title="💰 Ingresos del Mes (S/)",
                      labels={"ingresos": "S/", "fecha": "Fecha"},
                      color_discrete_sequence=["#2980b9"])
        fig.update_layout(height=320, margin=dict(t=40, b=20))
        st.plotly_chart(fig, use_container_width=True)


def _chart_top_diagnosticos():
    """Gráfico de barras horizontales: top 10 diagnósticos CIE-10."""
    data = execute_query("""
        SELECT cie.codigo, cie.descripcion, COUNT(*) AS total
        FROM clinica.diagnosticos d
        JOIN clinica.mantenedor_cie10 cie ON cie.id = d.cie10_id
        WHERE d.created_at >= NOW() - INTERVAL '90 days'
        GROUP BY cie.codigo, cie.descripcion
        ORDER BY total DESC LIMIT 10
    """)
    if data:
        df = pd.DataFrame(data)
        df["etiqueta"] = df["codigo"] + " — " + df["descripcion"].str[:35]
        fig = px.bar(df, x="total", y="etiqueta", orientation="h",
                     title="🩺 Top 10 Diagnósticos (90 días)",
                     labels={"total":"Casos","etiqueta":""},
                     color="total", color_continuous_scale="Blues")
        fig.update_layout(height=350, margin=dict(t=40, b=20), showlegend=False)
        st.plotly_chart(fig, use_container_width=True)


def _chart_distribucion_edad():
    """Gráfico de histograma: distribución de pacientes por grupo etario y sexo."""
    data = execute_query("""
        SELECT DATE_PART('year', AGE(fecha_nacimiento))::INT AS edad, sexo
        FROM clinica.pacientes WHERE activo=TRUE
    """)
    if data:
        df = pd.DataFrame(data)
        df["grupo"] = pd.cut(df["edad"],
                             bins=[0,10,18,30,45,60,75,120],
                             labels=["0-10","11-18","19-30","31-45","46-60","61-75","76+"])
        resumen = df.groupby(["grupo","sexo"]).size().reset_index(name="cantidad")
        fig = px.bar(resumen, x="grupo", y="cantidad", color="sexo",
                     title="👥 Distribución por Edad y Sexo",
                     labels={"cantidad":"Pacientes","grupo":"Grupo Etario"},
                     color_discrete_map={"M":"#2980b9","F":"#e91e8c","O":"#8e44ad"},
                     barmode="group")
        fig.update_layout(height=320, margin=dict(t=40, b=20))
        st.plotly_chart(fig, use_container_width=True)


def _chart_ocupacion_especialidades():
    """Gráfico de dona: distribución de citas por especialidad en el mes."""
    data = execute_query("""
        SELECT e.nombre AS especialidad, COUNT(*) AS citas
        FROM clinica.citas c
        JOIN clinica.medicos m ON m.id = c.medico_id
        JOIN clinica.especialidades e ON e.id = m.especialidad_id
        WHERE DATE_TRUNC('month', c.fecha_cita) = DATE_TRUNC('month', NOW())
        GROUP BY e.nombre ORDER BY citas DESC
    """)
    if data:
        df = pd.DataFrame(data)
        fig = px.pie(df, values="citas", names="especialidad",
                     title="🏥 Ocupación por Especialidad — Mes Actual",
                     hole=0.4,
                     color_discrete_sequence=px.colors.qualitative.Set3)
        fig.update_layout(height=350, margin=dict(t=40, b=20))
        st.plotly_chart(fig, use_container_width=True)